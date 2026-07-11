"""
test_signals_atomicity.py
Tests for the signal-bus atomicity fix in orchestrator/orchestrator.py
(Fable swarm audit, Area 1.3).

brain/signals.json holds the accumulated, irreplaceable STR-003 signal
record (str003_signals etc). The pre-fix code had three compounding holes:

  1. UNLOCKED — save_json()/load_json() had no fcntl lock at all, so
     concurrent writers (orchestrator + agents) could interleave.
  2. NON-ATOMIC — save_json() did `open(path, "w")` + `json.dump()` straight
     into the target file. open(..., "w") truncates immediately, so a
     kill/crash/power-cut mid-write left a truncated/corrupt file. (We've
     had 3 power cuts on this box — this isn't hypothetical.)
  3. DESTRUCTIVE ON CORRUPT READ (the worst one) — load_json() returned
     None for BOTH "file missing" and "file corrupt" (JSONDecodeError).
     write_signal() couldn't tell the difference and collapsed either case
     to `data = {"signals": []}` — silently wiping pending/rescan_log/
     str003_signals/active_signals the moment a corrupt read was next
     touched by a write. A single corruption event = permanent data loss.

The fix: signals_lock() (fcntl exclusive lock) + atomic_write_json()
(write-temp, fsync, os.replace) + load_signals_or_raise() (raises
CorruptSignalsFileError and backs up the corrupt file instead of ever
returning a fresh skeleton for anything but a genuinely-missing file).

Tests (b) and (c) are non-tautological: each replicates the EXACT pre-fix
logic verbatim and proves it produces the bad outcome (truncated file /
silent wipe) on the same fixture, before proving the new code doesn't.

Run: python3 -m pytest tests/test_signals_atomicity.py -v
"""

import json
import multiprocessing
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import orchestrator.orchestrator as orch
from orchestrator.orchestrator import (
    CorruptSignalsFileError,
    atomic_write_json,
    load_signals_or_raise,
    signals_lock,
    write_signal,
    mark_signal_processed,
    read_signals,
)


BASELINE = {
    "signals": [
        {"from": "signal-agent", "to": "orchestrator", "type": "str002_hit",
         "payload": {}, "timestamp": "2026-07-01T00:00:00", "status": "processed"},
    ],
    "pending": [],
    "rescan_log": [{"date": "2026-07-01", "note": "weekly rescan"}],
    "str003_signals": [
        {"signal_id": "STR003-007", "market_title": "Will the Iranian regime fall by June 30?",
         "outcome_correct": 1, "registered_at": "2026-06-09"},
    ],
    "active_signals": [],
}


@pytest.fixture
def signals_paths(tmp_path, monkeypatch):
    """Point the module's signals.json/.lock/.bak at an isolated tmp dir."""
    sig = tmp_path / "signals.json"
    lock = tmp_path / "signals.json.lock"
    bak = tmp_path / "signals.json.bak"
    monkeypatch.setattr(orch, "SIGNALS_FILE", sig)
    monkeypatch.setattr(orch, "SIGNALS_LOCK_FILE", lock)
    monkeypatch.setattr(orch, "SIGNALS_BAK_FILE", bak)
    return sig, lock, bak


def _write_baseline(path):
    path.write_text(json.dumps(BASELINE, indent=2))


# ─────────────────────────────────────────────
# (a) normal writes still work
# ─────────────────────────────────────────────

def test_normal_write_appends_and_preserves_other_keys(signals_paths):
    sig, _, _ = signals_paths
    _write_baseline(sig)

    write_signal("signal-agent", "orchestrator", "str003_new", {"market_id": "0xabc"})
    write_signal("performance-analyst", "orchestrator", "pool_c_alert", {"count": 5})

    data = json.loads(sig.read_text())
    assert len(data["signals"]) == 3  # 1 baseline + 2 new
    assert data["signals"][-1]["type"] == "pool_c_alert"
    assert data["signals"][-2]["type"] == "str003_new"
    assert all(s["status"] == "pending" for s in data["signals"][-2:])

    # untouched
    assert data["str003_signals"] == BASELINE["str003_signals"]
    assert data["rescan_log"] == BASELINE["rescan_log"]


def test_mark_signal_processed_updates_in_place(signals_paths):
    sig, _, _ = signals_paths
    _write_baseline(sig)
    write_signal("signal-agent", "orchestrator", "str003_new", {"market_id": "0xabc"})
    ts = json.loads(sig.read_text())["signals"][-1]["timestamp"]

    mark_signal_processed(ts)

    data = json.loads(sig.read_text())
    matched = [s for s in data["signals"] if s.get("timestamp") == ts]
    assert matched[0]["status"] == "processed"
    assert "processed_at" in matched[0]


def test_missing_file_bootstraps_fresh_skeleton_not_an_error(signals_paths):
    """A genuinely missing file (first run) is NOT the corrupt-read case —
    it's fine to start from a skeleton here."""
    sig, _, _ = signals_paths
    assert not sig.exists()
    write_signal("signal-agent", "orchestrator", "str003_new", {})
    data = json.loads(sig.read_text())
    assert len(data["signals"]) == 1


def test_bak_rolls_forward_on_successful_write(signals_paths):
    sig, _, bak = signals_paths
    _write_baseline(sig)
    assert not bak.exists()
    write_signal("signal-agent", "orchestrator", "str003_new", {})
    assert bak.exists()
    # .bak holds the PRE-write state (the last known-good, one generation back)
    assert json.loads(bak.read_text()) == BASELINE


# ─────────────────────────────────────────────
# (b) ATOMICITY — interrupted write leaves the ORIGINAL intact
# ─────────────────────────────────────────────

def _old_save_json(filepath, data):
    """Verbatim replica of the PRE-FIX save_json(): open(path, 'w') truncates
    immediately, then json.dump streams into the now-empty file. If dump is
    interrupted partway, the truncation already happened — original is gone."""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def test_interrupted_write_leaves_original_intact_new_code(signals_paths, monkeypatch):
    sig, _, _ = signals_paths
    _write_baseline(sig)
    original_bytes = sig.read_bytes()

    def _boom(*a, **kw):
        raise OSError("simulated crash mid-write (power cut)")

    # Interrupt inside json.dump — after the temp file is created but before
    # it's ever renamed onto the real path.
    monkeypatch.setattr(orch.json, "dump", _boom)

    with pytest.raises(OSError, match="simulated crash"):
        atomic_write_json(sig, {"signals": ["new", "data"]})

    # The ORIGINAL file must be byte-for-byte untouched.
    assert sig.read_bytes() == original_bytes
    assert json.loads(sig.read_text()) == BASELINE

    # No leftover temp file.
    leftovers = list(sig.parent.glob(f".{sig.name}.*.tmp"))
    assert leftovers == [], f"orphaned temp file(s) left behind: {leftovers}"


def test_interrupted_write_CORRUPTS_original_under_OLD_code(signals_paths, monkeypatch):
    """Non-tautological anchor: prove the exact pre-fix save_json() pattern
    really does destroy the original under the same injected failure that
    the new atomic_write_json() survives above."""
    sig, _, _ = signals_paths
    _write_baseline(sig)

    def _boom(*a, **kw):
        raise OSError("simulated crash mid-write (power cut)")

    monkeypatch.setattr(orch.json, "dump", _boom)

    with pytest.raises(OSError):
        _old_save_json(sig, {"signals": ["new", "data"]})

    # open(path, "w") already truncated the file to zero bytes before dump
    # was even called — the crash leaves a ZERO-BYTE, unparseable file.
    assert sig.stat().st_size == 0
    with pytest.raises(json.JSONDecodeError):
        json.loads(sig.read_text())


# ─────────────────────────────────────────────
# (c) CORRUPT-READ SAFETY — never silently reinitialize
# ─────────────────────────────────────────────

def _old_load_json(filepath):
    """Verbatim replica of the PRE-FIX load_json()."""
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _old_write_signal(filepath, from_agent, to_agent, signal_type, payload):
    """Verbatim replica of the PRE-FIX write_signal()."""
    data = _old_load_json(filepath)
    if data is None:
        data = {"signals": []}
    data["signals"].append({
        "from": from_agent, "to": to_agent, "type": signal_type,
        "payload": payload, "timestamp": "irrelevant", "status": "pending",
    })
    _old_save_json(filepath, data)


def test_old_code_SILENTLY_WIPES_str003_signals_on_corrupt_read(tmp_path):
    """Non-tautological anchor: prove the bug was real. Same corrupt fixture
    the new-code test below uses; the OLD write_signal() destroys the
    accumulated str003_signals record without any error or warning."""
    sig = tmp_path / "signals.json"
    sig.write_text('{"signals": [1, 2, ')  # truncated / unparseable

    _old_write_signal(sig, "signal-agent", "orchestrator", "str003_new", {})

    data = json.loads(sig.read_text())
    # The bug: str003_signals (and everything else) is just GONE, no trace,
    # no error — replaced with a fresh skeleton containing only the new write.
    assert "str003_signals" not in data
    assert data == {"signals": [
        {"from": "signal-agent", "to": "orchestrator", "type": "str003_new",
         "payload": {}, "timestamp": "irrelevant", "status": "pending"}
    ]}


def test_new_code_REFUSES_to_wipe_corrupt_file(signals_paths):
    sig, _, _ = signals_paths
    corrupt_content = '{"signals": [1, 2, '  # same truncated/unparseable fixture
    sig.write_text(corrupt_content)

    with pytest.raises(CorruptSignalsFileError):
        write_signal("signal-agent", "orchestrator", "str003_new", {})

    # The original corrupt file is left EXACTLY as it was — not reinitialized,
    # not patched, not touched at all. A human can inspect/recover it.
    assert sig.read_text() == corrupt_content

    # A forensic backup was made of the corrupt state.
    backups = list(sig.parent.glob("signals.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == corrupt_content


def test_read_signals_does_not_raise_or_destroy_on_corrupt_file(signals_paths):
    """The read-only path must not crash the 10-minute orchestrator cycle,
    and — like the write path — must never touch/reinitialize the file."""
    sig, _, _ = signals_paths
    corrupt_content = '{"signals": [1, 2, '
    sig.write_text(corrupt_content)

    result = read_signals()

    assert result == []
    assert sig.read_text() == corrupt_content  # untouched, no reinit


def test_mark_signal_processed_does_not_write_on_corrupt_file(signals_paths):
    sig, _, _ = signals_paths
    corrupt_content = '{"signals": [1, 2, '
    sig.write_text(corrupt_content)

    mark_signal_processed("2026-07-01T00:00:00")  # must not raise, must not write

    assert sig.read_text() == corrupt_content


# ─────────────────────────────────────────────
# (d) LOCKING — concurrent writes don't interleave or lose data
# ─────────────────────────────────────────────

def _concurrent_writer(sig_path_str, lock_path_str, bak_path_str, idx):
    """Runs in a child process. Re-points the module's paths explicitly
    (portable across 'fork'/'spawn'/'forkserver' start methods) then writes
    one signal through the real, locked write path."""
    import orchestrator.orchestrator as orch_child
    orch_child.SIGNALS_FILE = Path(sig_path_str)
    orch_child.SIGNALS_LOCK_FILE = Path(lock_path_str)
    orch_child.SIGNALS_BAK_FILE = Path(bak_path_str)
    orch_child.write_signal("worker", "orchestrator", "concurrency_probe", {"idx": idx})


def test_concurrent_writers_do_not_interleave_or_lose_data(signals_paths):
    sig, lock, bak = signals_paths
    _write_baseline(sig)

    N = 15
    ctx = multiprocessing.get_context("fork")
    procs = [
        ctx.Process(target=_concurrent_writer, args=(str(sig), str(lock), str(bak), i))
        for i in range(N)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert p.exitcode == 0, f"worker process failed (exitcode={p.exitcode})"

    # File must still parse cleanly — proves no torn/interleaved writes.
    data = json.loads(sig.read_text())

    probes = [s for s in data["signals"] if s.get("type") == "concurrency_probe"]
    assert len(probes) == N, (
        f"expected {N} concurrent writes to all land, got {len(probes)} "
        f"— a lost update means writes interleaved instead of serializing"
    )
    assert sorted(p["payload"]["idx"] for p in probes) == list(range(N))

    # The one pre-existing baseline signal must still be there too.
    assert len(data["signals"]) == N + 1
    assert data["str003_signals"] == BASELINE["str003_signals"]
