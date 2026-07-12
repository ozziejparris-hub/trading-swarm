"""
test_brain_writers_atomicity.py
Per-caller coverage for the atomicity-siblings fix (follows 9f7c257 and
tests/test_json_safety.py, which covers the shared primitives directly).

These tests don't re-prove locking/atomicity mechanics — that's
test_json_safety.py's job — they prove each CALLER actually routes through
those primitives correctly:
  - orchestrator.py: agent_registry.json (add_task/update_task/
    get_running_tasks/get_task), feedback.json (log_feedback),
    contract_violation_state.json (_check_and_record_violation)
  - orchestrator/ollama_agent_loop.py: tool_write_file,
    tool_append_to_json_array (used for every brain/ file a Tier-2/2.5
    agent writes, not just signals.json)

Key distinction under test: agent_registry.json and feedback.json hold
valuable state (running tasks / accumulated learning history) and must
RAISE on a corrupt read, same as signals.json. contract_violation_state.json
is a disposable rate-limit cache and is deliberately TOLERANT (reinitializes
rather than blocking the alert pipeline over a corrupt dedup cache) — both
still atomic and locked.

Run: python3 -m pytest tests/test_brain_writers_atomicity.py -v
"""

import json
from pathlib import Path

import pytest

import orchestrator.orchestrator as orch
import orchestrator.ollama_agent_loop as loop
from orchestrator.json_safety import CorruptJSONError


# ─────────────────────────────────────────────
# fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def registry_path(tmp_path, monkeypatch):
    p = tmp_path / "agent_registry.json"
    monkeypatch.setattr(orch, "REGISTRY_FILE", p)
    return p


@pytest.fixture
def feedback_path(tmp_path, monkeypatch):
    p = tmp_path / "feedback.json"
    monkeypatch.setattr(orch, "FEEDBACK_FILE", p)
    return p


@pytest.fixture
def violation_path(tmp_path, monkeypatch):
    p = tmp_path / "contract_violation_state.json"
    monkeypatch.setattr(orch, "CONTRACT_VIOLATION_STATE_FILE", p)
    return p


# ─────────────────────────────────────────────
# agent_registry.json — valuable state, RAISE on corrupt
# ─────────────────────────────────────────────

def test_add_task_then_update_task_round_trips(registry_path):
    orch.add_task("t1", "signal-agent", "test task")
    orch.update_task("t1", {"status": "failed"})

    data = json.loads(registry_path.read_text())
    assert len(data["active_tasks"]) == 1
    assert data["active_tasks"][0]["status"] == "failed"


def test_add_task_bootstraps_missing_file(registry_path):
    assert not registry_path.exists()
    task = orch.add_task("t1", "signal-agent", "desc")
    assert task["id"] == "t1"
    assert json.loads(registry_path.read_text())["active_tasks"][0]["id"] == "t1"


def test_add_task_raises_and_does_not_write_on_corrupt_registry(registry_path):
    corrupt = '{"active_tasks": [1, 2, '
    registry_path.write_text(corrupt)

    with pytest.raises(CorruptJSONError):
        orch.add_task("t1", "signal-agent", "desc")

    # Never patched over — untouched, forensic copy made.
    assert registry_path.read_text() == corrupt
    assert list(registry_path.parent.glob("agent_registry.json.corrupt-*"))


def test_get_running_tasks_degrades_gracefully_on_corrupt_registry(registry_path):
    """Read-only hot path (every immune-system cycle) must not crash the
    whole 10-minute loop over a corrupt registry — unlike add_task/
    update_task, which must refuse to write."""
    registry_path.write_text('{"active_tasks": [1, 2, ')

    result = orch.get_running_tasks()

    assert result == []
    # Still untouched — read-only degradation, not a silent patch-and-write.
    assert registry_path.read_text() == '{"active_tasks": [1, 2, '


def test_get_task_degrades_gracefully_on_corrupt_registry(registry_path):
    registry_path.write_text('{"active_tasks": [1, 2, ')
    assert orch.get_task("t1") is None


def test_concurrent_add_task_calls_do_not_lose_updates(registry_path):
    """add_task holds the lock across its whole read-modify-write — two
    calls in sequence (simulating what would otherwise be a lost update if
    load_registry()+save_registry() were two separate lock acquisitions)
    must both land."""
    for i in range(5):
        orch.add_task(f"t{i}", "signal-agent", "desc")
    data = json.loads(registry_path.read_text())
    assert len(data["active_tasks"]) == 5
    assert {t["id"] for t in data["active_tasks"]} == {f"t{i}" for i in range(5)}


# ─────────────────────────────────────────────
# feedback.json — accumulated history, RAISE on corrupt
# ─────────────────────────────────────────────

def test_log_feedback_appends_pass_and_fail_to_correct_buckets(feedback_path):
    orch.log_feedback("t1", "signal-agent", "desc", "pass", "worked")
    orch.log_feedback("t2", "signal-agent", "desc", "fail", "broke")

    data = json.loads(feedback_path.read_text())
    assert len(data["approved"]) == 1
    assert len(data["rejected"]) == 1
    assert data["approved"][0]["task_id"] == "t1"
    assert data["rejected"][0]["task_id"] == "t2"


def test_log_feedback_raises_and_does_not_write_on_corrupt_file(feedback_path):
    corrupt = '{"approved": [1, '
    feedback_path.write_text(corrupt)

    with pytest.raises(CorruptJSONError):
        orch.log_feedback("t1", "signal-agent", "desc", "pass", "worked")

    assert feedback_path.read_text() == corrupt


def test_log_feedback_bak_rolls_forward(feedback_path):
    orch.log_feedback("t1", "a", "d", "pass", "r")
    orch.log_feedback("t2", "a", "d", "pass", "r")
    bak = feedback_path.parent / "feedback.json.bak"
    assert bak.exists()
    assert len(json.loads(bak.read_text())["approved"]) == 1


# ─────────────────────────────────────────────
# contract_violation_state.json — disposable cache, TOLERANT on corrupt
# ─────────────────────────────────────────────

def test_check_and_record_violation_first_call_not_rate_limited(violation_path):
    rate_limited = orch._check_and_record_violation("agent:rule:resource")
    assert rate_limited is False
    data = json.loads(violation_path.read_text())
    assert "agent:rule:resource" in data["alerted"]


def test_check_and_record_violation_second_call_within_24h_is_suppressed(violation_path):
    orch._check_and_record_violation("k")
    rate_limited = orch._check_and_record_violation("k")
    assert rate_limited is True


def test_check_and_record_violation_does_not_raise_on_corrupt_file(violation_path):
    """Deliberately tolerant, unlike registry/feedback — this is a pure
    dedup cache and corruption here must not block the alert pipeline."""
    violation_path.write_text("{not json at all")

    rate_limited = orch._check_and_record_violation("k")

    assert rate_limited is False  # treated as a fresh cache, alert proceeds
    # File was reinitialized (this is the ONE deliberate exception to
    # never-reinit-on-corrupt) — but the corrupt state was still backed up.
    data = json.loads(violation_path.read_text())
    assert "k" in data["alerted"]
    assert list(violation_path.parent.glob("contract_violation_state.json.corrupt-*"))


def test_check_and_record_violation_race_is_closed(violation_path):
    """The pre-fix code checked and recorded in two separate,
    un-atomic-together calls (_violation_rate_limited then, later,
    _record_violation_alert) — a TOCTOU window where two concurrent
    violations for the same key could both see 'not rate limited'. The
    merged function holds the lock across check-and-set, so calling it
    N times for the same key sequentially must only ever report
    not-rate-limited on the first call."""
    results = [orch._check_and_record_violation("k") for _ in range(5)]
    assert results == [False, True, True, True, True]


# ─────────────────────────────────────────────
# ollama_agent_loop.py tools — shared by every Tier-2/2.5 agent, many files
# ─────────────────────────────────────────────

@pytest.fixture
def write_root(tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "WRITE_ROOT", tmp_path.resolve())
    return tmp_path


def test_tool_append_to_json_array_creates_and_appends(write_root):
    target = write_root / "signals.json"
    r1 = loop.tool_append_to_json_array(str(target), "signals", {"a": 1})
    r2 = loop.tool_append_to_json_array(str(target), "signals", {"a": 2})

    assert r1 == {"ok": True, "array_length": 1}
    assert r2 == {"ok": True, "array_length": 2}
    assert json.loads(target.read_text())["signals"] == [{"a": 1}, {"a": 2}]


def test_tool_append_to_json_array_locks_a_sidecar_not_the_target(write_root):
    target = write_root / "signals.json"
    loop.tool_append_to_json_array(str(target), "signals", {"a": 1})
    assert (write_root / "signals.json.lock").exists()


def test_tool_append_to_json_array_refuses_corrupt_file(write_root):
    target = write_root / "signals.json"
    corrupt = "{not json"
    target.write_text(corrupt)

    result = loop.tool_append_to_json_array(str(target), "signals", {"a": 1})

    assert "error" in result
    assert "corrupt" in result["error"].lower()
    assert target.read_text() == corrupt  # untouched, not reinitialized
    assert list(write_root.glob("signals.json.corrupt-*"))


def test_tool_append_to_json_array_rejects_non_dict_entry(write_root):
    result = loop.tool_append_to_json_array(str(write_root / "x.json"), "arr", ["not", "a", "dict"])
    assert "error" in result


def test_tool_append_to_json_array_rejects_path_outside_write_root(write_root):
    outside = Path("/etc/passwd")
    result = loop.tool_append_to_json_array(str(outside), "arr", {"a": 1})
    assert "error" in result
    assert "escapes" in result["error"]


def test_tool_write_file_is_atomic_on_crash(write_root, monkeypatch):
    target = write_root / "report.md"
    target.write_text("original")

    import orchestrator.json_safety as js

    def _boom(*a, **kw):
        raise OSError("simulated crash")

    real_fdopen = js.os.fdopen

    def _patched_fdopen(*a, **kw):
        fh = real_fdopen(*a, **kw)
        fh.write = _boom
        return fh

    monkeypatch.setattr(js.os, "fdopen", _patched_fdopen)

    result = loop.tool_write_file(str(target), "new content")

    assert "error" in result
    assert target.read_text() == "original"


def test_tool_write_file_rejects_path_outside_write_root(write_root):
    result = loop.tool_write_file("/etc/passwd", "pwned")
    assert "error" in result
    assert "escapes" in result["error"]
