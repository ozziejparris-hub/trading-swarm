#!/usr/bin/env python3
"""
orchestrator/agent_failure_notifier.py

Closes the spawn_agent.sh silent-failure gap named in the tier-2.5 scoping
document (a1db987): a Claude-backed (Tier 3/4) agent run that hits a
session/rate limit, a CLI/network/auth error, or returns nothing usable used
to be marked "completed", silently deleted from the registry, and never
alerted on. A fork hit exactly this on 2026-09-19 at 13:24 and only failed
loudly because it happened to be interactive.

This module is called ONCE, synchronously, from spawn_agent.sh's own cleanup
step for a single already-finished agent run (never polled, never scheduled,
never invoked by the orchestrator or cron). It does not retry and does not
re-enable anything paused. It only decides:
  1. what actually happened to this one run (classify_output), and
  2. what the registry should say, and whether a human needs to see it.

Age-tracking and register-gating reuse monitoring.failure_age (first-repo,
imported unmodified — it is stdlib-only by design, exactly so a consumer
like this can import it safely). State and the accepted-failures register
are kept LOCAL to trading-swarm (brain/spawn_agent_failure_state.json,
orchestrator/accepted_failures.json) rather than sharing first-repo's copies:
these are two operationally distinct systems (agent-orchestration failures
vs. first-repo DB-invariant violations) and conflating their review queues
would make the "not everything that fires is worth reading" property
failure_age exists to provide harder to reason about, not easier.

See brain/decisions/2026-09-20-spawn-agent-silent-failure-fix.md for the
full rationale, the failure-mode inventory that motivated this, and the
verification transcript.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path("/home/parison/trading-swarm")
REGISTRY_FILE = BASE_DIR / "orchestrator" / "agent_registry.json"
STATE_FILE = BASE_DIR / "brain" / "spawn_agent_failure_state.json"
REGISTER_FILE = BASE_DIR / "orchestrator" / "accepted_failures.json"
ENV_FILE = Path("/home/parison/.env_trading")

sys.path.insert(0, "/home/parison/trading-swarm")
sys.path.insert(0, "/home/parison/projects/first-repo")
from orchestrator.json_safety import (  # noqa: E402
    CorruptJSONError,
    atomic_write_json,
    json_lock,
    load_json_or_raise,
)
from monitoring import failure_age as fa  # noqa: E402

# Matches the actual 2026-09-19 13:24 message ("You've hit your session
# limit ... resets 1:40pm (UTC) (error type rate_limit, HTTP 429)") plus the
# generic phrasing Anthropic/the CLI use for the same condition. Deliberately
# broad on wording, narrow on subject (rate/session limits only) so it does
# not swallow unrelated errors into the wrong bucket.
RATE_LIMIT_RE = re.compile(
    r"session limit|rate[_ -]?limit|HTTP\D{0,4}429",
    re.IGNORECASE,
)

AGENT_OUTPUT_MARKER = "=== Agent Output ===\n"


# ---------------------------------------------------------------------------
# classification — pure, no I/O
# ---------------------------------------------------------------------------

def classify_output(claude_exit_code: int, agent_output: str) -> str:
    """
    Decide the true outcome of one Claude CLI invocation. Order matters:
    a rate-limit message takes priority even if, incidentally, the exit code
    was 0 or the message was the only thing printed (both observed in the
    wild) — it must never be lumped in with a generic crash or a plain empty
    result, per the task's explicit requirement that it be distinguishable
    from both.

      "rate_limited"  — the session/rate-limit signature is present, however
                         the process otherwise behaved.
      "empty_output"  — nothing usable was printed and it wasn't a rate
                         limit (covers a clean exit that produced nothing,
                         which exit-code checks alone cannot see).
      "cli_error"     — the CLI reported a non-zero exit and printed
                         *something*, but not the rate-limit signature
                         (network failure, auth expiry, model unavailable,
                         or any other API/CLI error with its own wording).
      "completed"     — exit 0 and non-empty output. The only outcome that
                         keeps the old "completed" registry behaviour.
    """
    if RATE_LIMIT_RE.search(agent_output):
        return "rate_limited"
    if not agent_output.strip():
        return "empty_output"
    if claude_exit_code != 0:
        return "cli_error"
    return "completed"


def read_agent_output_section(log_file) -> str:
    """
    Everything spawn_agent.sh's tee wrote AFTER the '=== Agent Output ==='
    marker it stamps into the log before the model runs. Reading only this
    section (not the whole file) matters: the file also contains the full
    injected prompt, which is never empty even when the model produced
    nothing, so scanning the whole file would defeat the empty-output check
    entirely.
    """
    p = Path(log_file)
    if not p.exists():
        return ""
    text = p.read_text(errors="replace")
    idx = text.find(AGENT_OUTPUT_MARKER)
    if idx == -1:
        # Marker missing (unexpected) — fail safe by treating the whole file
        # as the output rather than as empty, so we under- rather than
        # over-report.
        return text
    return text[idx + len(AGENT_OUTPUT_MARKER):]


# ---------------------------------------------------------------------------
# registry — locked read-modify-write, shared file with orchestrator.py
# ---------------------------------------------------------------------------

def mark_completed(task_id: str) -> None:
    """Unchanged historical behaviour for a genuine success: the task is
    removed from active_tasks entirely. (Previously this happened via an
    unconditional, unlocked read/write in spawn_agent.sh's inline cleanup
    script; now routed through the same json_lock/atomic_write_json
    orchestrator.py itself uses for this file, closing a pre-existing
    concurrent-write race as a side effect — not a behaviour change.)"""
    with json_lock(REGISTRY_FILE):
        try:
            registry = load_json_or_raise(REGISTRY_FILE, default=lambda: {"active_tasks": []})
        except CorruptJSONError as e:
            print(f"[agent_failure_notifier] {e} — leaving registry untouched", file=sys.stderr)
            return
        registry["active_tasks"] = [
            t for t in registry.get("active_tasks", []) if t["id"] != task_id
        ]
        atomic_write_json(REGISTRY_FILE, registry)


def mark_attention_required(task_id: str, failure_kind: str, claude_exit_code: int):
    """
    The new terminal state: neither 'completed' (nothing usable happened)
    nor a crash (the run *did* finish — this is not the dead-tmux-session
    case orchestrator.py's immune system already handles). The task stays
    IN active_tasks, visible, with enough detail to act on. get_running_tasks()
    only ever selects status == 'running', so leaving this status behind
    cannot confuse the orchestrator's own polling.

    Returns the task dict (for the caller to build the alert without a
    second registry read), or None if the task_id was not found.
    """
    with json_lock(REGISTRY_FILE):
        try:
            registry = load_json_or_raise(REGISTRY_FILE, default=lambda: {"active_tasks": []})
        except CorruptJSONError as e:
            print(f"[agent_failure_notifier] {e} — leaving registry untouched", file=sys.stderr)
            return None
        found = None
        for t in registry.get("active_tasks", []):
            if t["id"] == task_id:
                t["status"] = "attention_required"
                t["failure_kind"] = failure_kind
                t["claude_exit_code"] = claude_exit_code
                t["detected_at"] = datetime.now(timezone.utc).isoformat()
                found = dict(t)
                break
        atomic_write_json(REGISTRY_FILE, registry)
        return found


# ---------------------------------------------------------------------------
# delivery
# ---------------------------------------------------------------------------

def _load_env() -> dict:
    """.env_trading isn't exported by cron/tmux's parent shell any more than
    it is for first-repo's audit_invariants.py (see that file's note on the
    same problem) — read it directly rather than assuming it's inherited."""
    env = dict(os.environ)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    return env


def send_telegram(message: str, env: dict) -> bool:
    """
    Minimal, dependency-free sender using the existing 'agents' bot
    (TELEGRAM_AGENTS_TOKEN + TELEGRAM_CHAT_ID — the same pair
    orchestrator.py's send_telegram(bot="agents") already uses for
    per-agent notices). Deliberately NOT importing orchestrator.py's
    send_telegram: that function returns None unconditionally, and
    failure_age.mark_reported's contract requires calling it ONLY after a
    *confirmed* send — orchestrator.send_telegram cannot tell us that.
    """
    token = env.get("TELEGRAM_AGENTS_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("[agent_failure_notifier] Telegram credentials not set — skipping alert.",
              file=sys.stderr)
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except (urllib.error.URLError, OSError) as exc:
        print(f"[agent_failure_notifier] Telegram send failed: {exc}", file=sys.stderr)
        return False


def notify_failure(task_id: str, agent_type: str, description: str, failure_kind: str,
                    claude_exit_code: int, log_file: str, *, env: dict | None = None,
                    sender=None) -> bool:
    """
    Age-track the failure_kind (NOT the task_id — see the module docstring
    and the decision doc for why a coarse key is what makes this quiet on a
    burst of identical failures) through monitoring.failure_age, and send a
    Telegram message only when evaluate() says something changed. Returns
    True iff a message was actually sent.

    sender defaults to None (resolved to the module-level send_telegram at
    call time, not at import time) so tests can monkeypatch
    agent_failure_notifier.send_telegram and have handle_agent_run's calls
    pick it up, exactly like patching any other module-level dependency.
    """
    if sender is None:
        sender = send_telegram
    now = datetime.now(timezone.utc)
    key = f"spawn_agent::{failure_kind}"

    state = fa.load_state(STATE_FILE)
    new_state, classification = fa.reconcile(state, [key], now)
    register = fa.load_register(REGISTER_FILE)
    decision = fa.evaluate(classification, register, new_state, now)

    message = fa.render_message("spawn_agent.sh — agent run needs attention",
                                 decision, new_state, now, STATE_FILE)
    sent = False
    if message:
        detail = (
            f"\n\ntask: {task_id}\nagent: {agent_type}\n"
            f"exit code: {claude_exit_code}\nlog: {log_file}\n"
            f"{description[:200]}"
        )
        sent = sender(message + detail, env if env is not None else _load_env())
        if sent:
            fa.mark_reported(new_state, decision, now)

    fa.save_state(STATE_FILE, new_state, now, check="spawn_agent.sh — agent run needs attention")
    return sent


# ---------------------------------------------------------------------------
# entry point used by spawn_agent.sh
# ---------------------------------------------------------------------------

def handle_agent_run(task_id: str, claude_exit_code: int, log_file: str) -> str:
    """
    The single call spawn_agent.sh's cleanup step makes. Returns the
    classification string for logging; all side effects (registry write,
    possible Telegram send) happen here.
    """
    output = read_agent_output_section(log_file)
    kind = classify_output(claude_exit_code, output)

    if kind == "completed":
        mark_completed(task_id)
        return kind

    task = mark_attention_required(task_id, kind, claude_exit_code)
    if task is None:
        print(f"[agent_failure_notifier] task {task_id} not found in registry "
              f"— cannot record {kind}", file=sys.stderr)
        return kind

    notify_failure(
        task_id,
        task.get("agent", "unknown"),
        task.get("description", ""),
        kind,
        claude_exit_code,
        log_file,
    )
    return kind


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: agent_failure_notifier.py <task_id> <claude_exit_code> <log_file>",
              file=sys.stderr)
        sys.exit(2)
    _, _task_id, _exit_code_s, _log_file = sys.argv
    try:
        _exit_code = int(_exit_code_s)
    except ValueError:
        _exit_code = -1
    outcome = handle_agent_run(_task_id, _exit_code, _log_file)
    print(f"[agent_failure_notifier] {_task_id}: {outcome}")
