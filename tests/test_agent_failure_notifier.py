"""
test_agent_failure_notifier.py

Tests for orchestrator/agent_failure_notifier.py — the fix for
spawn_agent.sh's silent session-limit failure (a run that hits an API error,
including but not limited to a session/rate limit, used to be marked
"completed" and vanish from the registry with no alert).

See brain/decisions/2026-09-20-spawn-agent-silent-failure-fix.md for the
full failure-mode inventory and the manual verification transcript this
suite formalizes.

Run: python3 -m pytest tests/test_agent_failure_notifier.py -v
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orchestrator import agent_failure_notifier as afn


# ─────────────────────────────────────────────
# fixtures
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_paths(tmp_path, monkeypatch):
    """Every test gets its own registry/state/register files — never the
    real ones. autouse so a forgotten fixture can't accidentally touch
    production files."""
    registry = tmp_path / "agent_registry.json"
    registry.write_text(json.dumps({"active_tasks": []}))
    state = tmp_path / "spawn_agent_failure_state.json"
    register = tmp_path / "accepted_failures.json"

    monkeypatch.setattr(afn, "REGISTRY_FILE", registry)
    monkeypatch.setattr(afn, "STATE_FILE", state)
    monkeypatch.setattr(afn, "REGISTER_FILE", register)
    return {"registry": registry, "state": state, "register": register}


def seed_task(registry_path: Path, task_id="t1", agent="quant-research", status="running"):
    registry = json.loads(registry_path.read_text())
    registry["active_tasks"].append({
        "id": task_id,
        "agent": agent,
        "description": "test task",
        "branch": f"feat/{task_id}",
        "tmux_session": f"{agent}-{task_id}",
        "model": "claude-sonnet-4-6 (Tier 3)",
        "tier": "3",
        "worktree": f"/tmp/trading-swarm-worktrees/{task_id}",
        "log": f"/tmp/{task_id}.log",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "retries": 0,
        "pr": None,
        "verified": False,
    })
    registry_path.write_text(json.dumps(registry, indent=2))


class FakeSender:
    """Records every call; lets a test force success or failure without
    touching the network."""
    def __init__(self, succeed=True):
        self.succeed = succeed
        self.calls = []

    def __call__(self, message, env):
        self.calls.append(message)
        return self.succeed


# ─────────────────────────────────────────────
# classify_output — pure function, the core of Part 1/2
# ─────────────────────────────────────────────

REAL_SESSION_LIMIT_TEXT = (
    "Agent terminated early due to an API error: You've hit your session "
    "limit · resets 1:40pm (UTC) (error type rate_limit, HTTP 429)"
)


def test_classify_real_session_limit_message_as_rate_limited():
    # The exact text from the 2026-09-19 13:24 event.
    assert afn.classify_output(1, REAL_SESSION_LIMIT_TEXT) == "rate_limited"


def test_classify_rate_limit_even_with_exit_zero():
    # Observed in the wild: some CLI error paths still exit 0. The
    # rate-limit signature must win regardless of exit code.
    assert afn.classify_output(0, REAL_SESSION_LIMIT_TEXT) == "rate_limited"


def test_classify_clean_empty_output_as_empty_output():
    assert afn.classify_output(0, "") == "empty_output"
    assert afn.classify_output(0, "   \n  \n") == "empty_output"


def test_classify_nonzero_exit_with_no_rate_limit_text_as_cli_error():
    # Stand-ins for network failure / auth expiry / model unavailability:
    # none of these say "session limit" or "429", but all return non-zero.
    for msg in [
        "Error: fetch failed (ECONNRESET)",
        "Please re-authenticate: your session has expired",
        "Error: model 'claude-sonnet-4-6' is not available",
        "unexpected token in JSON response",
    ]:
        assert afn.classify_output(1, msg) == "cli_error", msg


def test_classify_genuine_success_as_completed():
    assert afn.classify_output(0, "Here is the analysis you requested...\n"
                                   "1. Finding A\n2. Finding B\n") == "completed"


def test_classify_nonzero_exit_but_real_output_present_is_not_completed():
    # A run that DID produce substantial output but the CLI still reported
    # failure (e.g. a post-processing step failed after the model replied)
    # must not be silently trusted just because there's text.
    assert afn.classify_output(1, "partial analysis before the crash...") == "cli_error"


# ─────────────────────────────────────────────
# read_agent_output_section
# ─────────────────────────────────────────────

def test_reads_only_content_after_the_marker(tmp_path):
    log = tmp_path / "t1.log"
    log.write_text("=== Agent Prompt ===\nSOME INJECTED PROMPT TEXT\n"
                    "=== Agent Output ===\nthe real output\n")
    assert afn.read_agent_output_section(log) == "the real output\n"


def test_missing_marker_falls_back_to_whole_file(tmp_path):
    log = tmp_path / "t1.log"
    log.write_text("no marker here at all")
    assert afn.read_agent_output_section(log) == "no marker here at all"


def test_missing_log_file_is_empty_output(tmp_path):
    assert afn.read_agent_output_section(tmp_path / "does_not_exist.log") == ""


# ─────────────────────────────────────────────
# registry writes
# ─────────────────────────────────────────────

def test_mark_completed_removes_task_from_active_tasks(isolated_paths):
    seed_task(isolated_paths["registry"], task_id="t1")
    afn.mark_completed("t1")
    registry = json.loads(isolated_paths["registry"].read_text())
    assert registry["active_tasks"] == []


def test_mark_attention_required_keeps_task_visible_with_detail(isolated_paths):
    seed_task(isolated_paths["registry"], task_id="t1")
    task = afn.mark_attention_required("t1", "rate_limited", 1)
    registry = json.loads(isolated_paths["registry"].read_text())
    assert len(registry["active_tasks"]) == 1
    stored = registry["active_tasks"][0]
    assert stored["status"] == "attention_required"
    assert stored["status"] not in ("completed", "failed")  # neither bucket
    assert stored["failure_kind"] == "rate_limited"
    assert stored["claude_exit_code"] == 1
    assert "detected_at" in stored
    assert task["id"] == "t1"


def test_mark_attention_required_missing_task_returns_none(isolated_paths):
    assert afn.mark_attention_required("nonexistent", "rate_limited", 1) is None


# ─────────────────────────────────────────────
# notify_failure — the alert-gating behaviour
# ─────────────────────────────────────────────

def test_first_rate_limit_alerts_and_marks_reported(isolated_paths):
    sender = FakeSender(succeed=True)
    sent = afn.notify_failure("t1", "quant-research", "desc", "rate_limited", 1,
                               "/tmp/t1.log", env={}, sender=sender)
    assert sent is True
    assert len(sender.calls) == 1
    assert "spawn_agent" in sender.calls[0].lower() or "attention" in sender.calls[0].lower()


def test_repeat_of_same_failure_kind_does_not_alert_again(isolated_paths):
    # This is the burst-suppression property: five agents all hitting the
    # same session limit inside one window must not page five times.
    sender = FakeSender(succeed=True)
    afn.notify_failure("t1", "quant-research", "d1", "rate_limited", 1,
                        "/tmp/t1.log", env={}, sender=sender)
    afn.notify_failure("t2", "signal-agent", "d2", "rate_limited", 1,
                        "/tmp/t2.log", env={}, sender=sender)
    afn.notify_failure("t3", "backtest-agent", "d3", "rate_limited", 1,
                        "/tmp/t3.log", env={}, sender=sender)
    assert len(sender.calls) == 1, "only the first occurrence of a still-ongoing kind should alert"


def test_different_failure_kinds_each_alert_once(isolated_paths):
    sender = FakeSender(succeed=True)
    afn.notify_failure("t1", "a", "d", "rate_limited", 1, "/tmp/t1.log", env={}, sender=sender)
    afn.notify_failure("t2", "a", "d", "empty_output", 0, "/tmp/t2.log", env={}, sender=sender)
    afn.notify_failure("t3", "a", "d", "cli_error", 1, "/tmp/t3.log", env={}, sender=sender)
    assert len(sender.calls) == 3


def test_send_failure_does_not_mark_reported_so_next_run_retries(isolated_paths):
    failing_sender = FakeSender(succeed=False)
    sent = afn.notify_failure("t1", "a", "d", "rate_limited", 1, "/tmp/t1.log",
                               env={}, sender=failing_sender)
    assert sent is False

    working_sender = FakeSender(succeed=True)
    sent2 = afn.notify_failure("t2", "a", "d", "rate_limited", 1, "/tmp/t2.log",
                                env={}, sender=working_sender)
    assert sent2 is True, "an unconfirmed send must not be treated as already reported"


# ─────────────────────────────────────────────
# handle_agent_run — the full path spawn_agent.sh's cleanup step calls
# ─────────────────────────────────────────────

def test_full_path_session_limit_is_recorded_failed_and_alerts(isolated_paths, tmp_path, monkeypatch):
    """Verification (1): simulate a session-limit response end to end."""
    seed_task(isolated_paths["registry"], task_id="t1")
    log = tmp_path / "t1.log"
    log.write_text(f"=== Agent Prompt ===\nprompt\n=== Agent Output ===\n{REAL_SESSION_LIMIT_TEXT}\n")

    sender = FakeSender(succeed=True)
    monkeypatch.setattr(afn, "send_telegram", sender)

    outcome = afn.handle_agent_run("t1", 1, str(log))

    assert outcome == "rate_limited"
    registry = json.loads(isolated_paths["registry"].read_text())
    assert len(registry["active_tasks"]) == 1
    assert registry["active_tasks"][0]["status"] == "attention_required"
    assert registry["active_tasks"][0]["status"] != "completed"
    assert len(sender.calls) == 1


def test_full_path_clean_exit_empty_output_is_recorded_failed_and_alerts(isolated_paths, tmp_path, monkeypatch):
    """Verification (2): simulate a clean run (exit 0) with empty output."""
    seed_task(isolated_paths["registry"], task_id="t1")
    log = tmp_path / "t1.log"
    log.write_text("=== Agent Prompt ===\nprompt\n=== Agent Output ===\n")

    sender = FakeSender(succeed=True)
    monkeypatch.setattr(afn, "send_telegram", sender)

    outcome = afn.handle_agent_run("t1", 0, str(log))

    assert outcome == "empty_output"
    registry = json.loads(isolated_paths["registry"].read_text())
    assert registry["active_tasks"][0]["status"] == "attention_required"
    assert len(sender.calls) == 1


def test_full_path_genuine_success_completes_and_does_not_alert(isolated_paths, tmp_path, monkeypatch):
    """Verification (3) — the one that matters most: a real successful run
    must still be recorded as completed and must NOT alert."""
    seed_task(isolated_paths["registry"], task_id="t1")
    log = tmp_path / "t1.log"
    log.write_text("=== Agent Prompt ===\nprompt\n=== Agent Output ===\n"
                    "Analysis complete. Created PR #42 with the requested changes.\n")

    sender = FakeSender(succeed=True)
    monkeypatch.setattr(afn, "send_telegram", sender)

    outcome = afn.handle_agent_run("t1", 0, str(log))

    assert outcome == "completed"
    registry = json.loads(isolated_paths["registry"].read_text())
    assert registry["active_tasks"] == [], "a genuine success is still removed, exactly as before"
    assert len(sender.calls) == 0, "a genuine success must never alert"


@pytest.mark.parametrize("exit_code,output,expected", [
    (1, "Error: fetch failed (network unreachable)", "cli_error"),         # network failure
    (1, "Please run /login — your credentials have expired", "cli_error"), # auth expiry
    (1, "Error: model 'claude-opus-4-9' not found", "cli_error"),          # model unavailable
])
def test_full_path_other_failure_modes_are_all_caught(isolated_paths, tmp_path, monkeypatch,
                                                        exit_code, output, expected):
    """Verification (4): the other Part-1 failure modes go through the same
    non-'completed' path and alert, not just the rate-limit case."""
    seed_task(isolated_paths["registry"], task_id="t1")
    log = tmp_path / "t1.log"
    log.write_text(f"=== Agent Prompt ===\nprompt\n=== Agent Output ===\n{output}\n")

    sender = FakeSender(succeed=True)
    monkeypatch.setattr(afn, "send_telegram", sender)

    outcome = afn.handle_agent_run("t1", exit_code, str(log))

    assert outcome == expected
    registry = json.loads(isolated_paths["registry"].read_text())
    assert registry["active_tasks"][0]["status"] == "attention_required"
    assert len(sender.calls) == 1


def test_handle_agent_run_missing_task_id_does_not_crash(isolated_paths, tmp_path, monkeypatch):
    # No seed_task() call — the registry is empty. This must not raise even
    # though there's nothing to update.
    log = tmp_path / "ghost.log"
    log.write_text("=== Agent Output ===\nsome error text HTTP 429\n")
    sender = FakeSender(succeed=True)
    monkeypatch.setattr(afn, "send_telegram", sender)

    outcome = afn.handle_agent_run("ghost-task", 1, str(log))
    assert outcome == "rate_limited"
    assert len(sender.calls) == 0, "nothing to alert about if the task record itself is gone"
