"""
test_json_safety.py
Tests for orchestrator/json_safety.py — the shared primitives every
brain/*.json writer in this repo (and, separately, first-repo's mirror
module) is built on: signals.json, feedback.json, agent_registry.json,
contract_violation_state.json, findings.json, and any brain/ file written
through ollama_agent_loop.py's agent tools.

This is the foundational module for the whole atomicity-siblings fix
(9f7c257 and everything that followed it) — a bug here breaks every caller
at once, so it gets the most direct coverage. Per-caller tests (registry,
feedback, contract-violation state, the ollama_agent_loop tools) live in
test_brain_writers_atomicity.py and only need to prove they actually route
through these primitives, not re-prove the primitives themselves.

Non-tautological anchors: (b) and (c) each replicate a plausible pre-fix
pattern verbatim and prove it produces the bad outcome on the same
fixture, before proving json_safety.py doesn't.

Run: python3 -m pytest tests/test_json_safety.py -v
"""

import json
import multiprocessing
import time
from pathlib import Path

import pytest

from orchestrator.json_safety import (
    CorruptJSONError,
    atomic_write_json,
    atomic_write_text,
    json_lock,
    load_json_or_raise,
    load_json_tolerant,
)


# ─────────────────────────────────────────────
# (a) load_json_or_raise — missing vs corrupt
# ─────────────────────────────────────────────

def test_missing_file_returns_default_value(tmp_path):
    target = tmp_path / "x.json"
    assert load_json_or_raise(target, default={"a": 1}) == {"a": 1}


def test_missing_file_calls_default_factory(tmp_path):
    target = tmp_path / "x.json"
    assert load_json_or_raise(target, default=lambda: {"a": 2}) == {"a": 2}


def test_missing_file_defaults_to_empty_dict_if_no_default_given(tmp_path):
    target = tmp_path / "x.json"
    assert load_json_or_raise(target) == {}


def test_existing_valid_file_loads_normally(tmp_path):
    target = tmp_path / "x.json"
    target.write_text(json.dumps({"real": "data"}))
    assert load_json_or_raise(target, default={"a": 1}) == {"real": "data"}


def test_corrupt_file_raises_and_backs_up_untouched(tmp_path):
    target = tmp_path / "x.json"
    corrupt = '{"a": [1, 2, '
    target.write_text(corrupt)

    with pytest.raises(CorruptJSONError):
        load_json_or_raise(target, default={})

    # Original untouched — no reinit, no patch.
    assert target.read_text() == corrupt
    backups = list(tmp_path.glob("x.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == corrupt


def test_corrupt_file_error_names_the_path(tmp_path):
    target = tmp_path / "x.json"
    target.write_text("{not json")
    with pytest.raises(CorruptJSONError) as exc_info:
        load_json_or_raise(target)
    assert str(target) in str(exc_info.value)


# ─────────────────────────────────────────────
# (a2) load_json_tolerant — the deliberate, narrow exception
# ─────────────────────────────────────────────

def test_tolerant_missing_file_returns_default(tmp_path):
    target = tmp_path / "x.json"
    assert load_json_tolerant(target, default={"alerted": {}}) == {"alerted": {}}


def test_tolerant_corrupt_file_does_not_raise_and_backs_up(tmp_path):
    target = tmp_path / "x.json"
    corrupt = "{broken"
    target.write_text(corrupt)

    result = load_json_tolerant(target, default=lambda: {"alerted": {}})

    assert result == {"alerted": {}}
    # Still backed up (forensic trail), still untouched in place — the only
    # difference from load_json_or_raise is that this doesn't raise.
    assert target.read_text() == corrupt
    assert list(tmp_path.glob("x.json.corrupt-*"))


# ─────────────────────────────────────────────
# (b) atomic_write_json / atomic_write_text — crash mid-write
# ─────────────────────────────────────────────

def _old_unsafe_write_json(filepath, data):
    """Verbatim replica of the pre-fix pattern this whole fix chain exists
    to kill: open(path, 'w') truncates immediately, then json.dump streams
    into the now-empty file. An interrupt after truncation, before dump
    completes, leaves the original gone."""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def test_interrupted_atomic_write_leaves_original_intact(tmp_path, monkeypatch):
    target = tmp_path / "x.json"
    target.write_text(json.dumps({"original": True}))
    original_bytes = target.read_bytes()

    import orchestrator.json_safety as js

    def _boom(*a, **kw):
        raise OSError("simulated crash mid-write")

    monkeypatch.setattr(js.json, "dump", _boom)

    with pytest.raises(OSError, match="simulated crash"):
        atomic_write_json(target, {"new": "data"})

    assert target.read_bytes() == original_bytes
    assert json.loads(target.read_text()) == {"original": True}
    # No orphaned temp file left behind.
    assert list(tmp_path.glob(f".{target.name}.*.tmp")) == []


def test_old_unsafe_write_CORRUPTS_original_under_same_injected_failure(tmp_path, monkeypatch):
    """Non-tautological anchor: the exact pre-fix pattern really does
    destroy the original under the same failure the new code survives."""
    target = tmp_path / "x.json"
    target.write_text(json.dumps({"original": True}))

    import orchestrator.json_safety as js

    def _boom(*a, **kw):
        raise OSError("simulated crash mid-write")

    monkeypatch.setattr(js.json, "dump", _boom)

    with pytest.raises(OSError):
        _old_unsafe_write_json(target, {"new": "data"})

    # open(path, "w") already truncated to zero bytes before dump was even
    # called — the crash leaves a zero-byte, unparseable file.
    assert target.stat().st_size == 0
    with pytest.raises(json.JSONDecodeError):
        json.loads(target.read_text())


def test_atomic_write_json_rolls_bak_forward(tmp_path):
    target = tmp_path / "x.json"
    target.write_text(json.dumps({"gen": 1}))
    atomic_write_json(target, {"gen": 2})
    bak = tmp_path / "x.json.bak"
    assert bak.exists()
    assert json.loads(bak.read_text()) == {"gen": 1}
    assert json.loads(target.read_text()) == {"gen": 2}


def test_atomic_write_json_no_bak_when_keep_bak_false(tmp_path):
    target = tmp_path / "x.json"
    target.write_text(json.dumps({"gen": 1}))
    atomic_write_json(target, {"gen": 2}, keep_bak=False)
    assert not (tmp_path / "x.json.bak").exists()


def test_atomic_write_text_is_crash_safe_too(tmp_path, monkeypatch):
    target = tmp_path / "note.md"
    target.write_text("original content")
    original = target.read_bytes()

    import orchestrator.json_safety as js

    def _boom(*a, **kw):
        raise OSError("simulated crash")

    # atomic_write_text writes via f.write(), not json.dump — patch that.
    real_fdopen = js.os.fdopen

    def _patched_fdopen(*a, **kw):
        fh = real_fdopen(*a, **kw)
        real_write = fh.write

        def _write(*a2, **kw2):
            raise OSError("simulated crash mid-write")

        fh.write = _write
        return fh

    monkeypatch.setattr(js.os, "fdopen", _patched_fdopen)

    with pytest.raises(OSError):
        atomic_write_text(target, "new content")

    assert target.read_bytes() == original
    assert list(tmp_path.glob(f".{target.name}.*.tmp")) == []


def test_atomic_write_json_creates_parent_dirs(tmp_path):
    target = tmp_path / "nested" / "deep" / "x.json"
    atomic_write_json(target, {"a": 1})
    assert json.loads(target.read_text()) == {"a": 1}


# ─────────────────────────────────────────────
# (c) json_lock — locking and cross-process serialization
# ─────────────────────────────────────────────

def test_lock_path_is_a_sidecar_not_the_target(tmp_path):
    target = tmp_path / "x.json"
    target.write_text("{}")
    with json_lock(target):
        lock_file = tmp_path / "x.json.lock"
        assert lock_file.exists()
        # Target itself is untouched by locking alone.
        assert target.read_text() == "{}"


def test_lock_path_resolves_symlinks_and_relative_components(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    target = real_dir / "x.json"
    target.write_text("{}")

    link_dir = tmp_path / "link"
    link_dir.symlink_to(real_dir)
    via_symlink = link_dir / "x.json"
    via_dotdot = tmp_path / "real" / ".." / "real" / "x.json"

    # Both spellings of the same file must produce the identical lock path.
    from orchestrator.json_safety import _lock_path
    assert _lock_path(via_symlink) == _lock_path(target)
    assert _lock_path(via_dotdot) == _lock_path(target)


def _locked_appender(path_str, idx, n_iters):
    """Runs in a child process: repeatedly does a locked read-modify-write,
    the same pattern every real caller (write_signal, log_feedback, ...)
    uses. Any failure to serialize shows up as a lost update or a torn
    (unparseable) file."""
    import orchestrator.json_safety as js
    path = Path(path_str)
    for _ in range(n_iters):
        with js.json_lock(path):
            data = js.load_json_or_raise(path, default=lambda: {"items": []})
            data["items"].append(idx)
            js.atomic_write_json(path, data)


def test_concurrent_locked_writers_do_not_interleave_or_lose_updates(tmp_path):
    target = tmp_path / "x.json"
    atomic_write_json(target, {"items": []})

    n_procs = 8
    n_iters = 10
    ctx = multiprocessing.get_context("fork")
    procs = [
        ctx.Process(target=_locked_appender, args=(str(target), i, n_iters))
        for i in range(n_procs)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert p.exitcode == 0

    data = json.loads(target.read_text())
    assert len(data["items"]) == n_procs * n_iters, (
        "a lost update means writes interleaved instead of serializing"
    )


def _blocking_holder(path_str, hold_seconds, started_evt):
    import orchestrator.json_safety as js
    path = Path(path_str)
    with js.json_lock(path):
        started_evt.set()
        time.sleep(hold_seconds)


def test_json_lock_blocks_second_caller_until_first_releases(tmp_path):
    """Proves LOCK_EX is actually exclusive and blocking (not LOCK_NB with
    a silent give-up): a second acquirer must wait for the holder's sleep
    to finish, not skip its turn."""
    target = tmp_path / "x.json"
    ctx = multiprocessing.get_context("fork")
    started = ctx.Event()
    hold_seconds = 1.5

    holder = ctx.Process(target=_blocking_holder, args=(str(target), hold_seconds, started))
    t_launch = time.monotonic()
    holder.start()
    assert started.wait(timeout=5), "holder never acquired the lock"

    with json_lock(target):
        elapsed_since_launch = time.monotonic() - t_launch

    holder.join(timeout=10)
    assert elapsed_since_launch >= hold_seconds * 0.8, (
        f"acquired the lock after only {elapsed_since_launch:.2f}s, before the "
        f"{hold_seconds}s holder released it — not actually blocking"
    )
