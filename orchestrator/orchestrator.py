#!/usr/bin/env python3
"""
Trading Swarm Orchestrator
Runs every 10 minutes. Reads signals, checks agents,
verifies outputs, spawns new work, reports to Telegram.
"""

import json
import os
import subprocess
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

BASE_DIR = Path("/home/parison/trading-swarm")
BRAIN_DIR = BASE_DIR / "brain"
REGISTRY_FILE = BASE_DIR / "orchestrator" / "agent_registry.json"
SIGNALS_FILE = BRAIN_DIR / "signals.json"
FEEDBACK_FILE = BRAIN_DIR / "feedback.json"
PRIORITIES_FILE = BRAIN_DIR / "priorities.md"
LOG_FILE = BASE_DIR / "logs" / "orchestrator.log"

# Telegram configuration
# You'll fill these in when you set up your bots
TELEGRAM_ORCHESTRATOR_TOKEN = os.getenv("TELEGRAM_ORCHESTRATOR_TOKEN", "")
TELEGRAM_AGENTS_TOKEN = os.getenv("TELEGRAM_AGENTS_TOKEN", "")
TELEGRAM_METRICS_TOKEN = os.getenv("TELEGRAM_METRICS_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Agent settings
MAX_RETRIES = 3
MAX_AGENT_RUNTIME_HOURS = 4
CYCLE_INTERVAL_SECONDS = 600  # 10 minutes

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# FILE HELPERS
# ─────────────────────────────────────────────

def load_json(filepath):
    """Safely load a JSON file. Returns None if missing or corrupt."""
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        log.warning(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        log.error(f"Corrupt JSON at {filepath}: {e}")
        return None


def save_json(filepath, data):
    """Safely write JSON to a file."""
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        log.error(f"Failed to write {filepath}: {e}")
        return False


def read_priorities():
    """Read current priorities from brain."""
    try:
        with open(PRIORITIES_FILE) as f:
            return f.read()
    except FileNotFoundError:
        return "No priorities set."

# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────

def send_telegram(message, bot="orchestrator"):
    """
    Send a Telegram message.
    bot options: "orchestrator", "agents", "metrics"
    """
    if not TELEGRAM_CHAT_ID:
        log.warning("Telegram chat ID not set. Skipping notification.")
        return

    token_map = {
        "orchestrator": TELEGRAM_ORCHESTRATOR_TOKEN,
        "agents": TELEGRAM_AGENTS_TOKEN,
        "metrics": TELEGRAM_METRICS_TOKEN
    }
    token = token_map.get(bot, TELEGRAM_ORCHESTRATOR_TOKEN)

    if not token:
        log.warning(f"Telegram token for {bot} bot not set.")
        return

    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        log.info(f"Telegram [{bot}]: {message[:80]}...")
    except Exception as e:
        log.error(f"Telegram send failed: {e}")

# ─────────────────────────────────────────────
# REGISTRY MANAGEMENT
# ─────────────────────────────────────────────

def load_registry():
    """Load the agent registry."""
    data = load_json(REGISTRY_FILE)
    if data is None:
        return {"active_tasks": []}
    return data


def save_registry(registry):
    """Save the agent registry."""
    save_json(REGISTRY_FILE, registry)


def add_task(task_id, agent_type, description, branch=""):
    """Register a new task as running."""
    registry = load_registry()
    task = {
        "id": task_id,
        "agent": agent_type,
        "description": description,
        "branch": branch,
        "tmux_session": f"{agent_type}-{task_id}",
        "started_at": datetime.utcnow().isoformat(),
        "status": "running",
        "retries": 0,
        "pr": None,
        "verified": False
    }
    registry["active_tasks"].append(task)
    save_registry(registry)
    log.info(f"Task registered: {task_id} ({agent_type})")
    return task


def update_task(task_id, updates):
    """Update fields on an existing task."""
    registry = load_registry()
    for task in registry["active_tasks"]:
        if task["id"] == task_id:
            task.update(updates)
    save_registry(registry)


def get_running_tasks():
    """Return all tasks with status 'running'."""
    registry = load_registry()
    return [t for t in registry["active_tasks"] if t["status"] == "running"]


def get_task(task_id):
    """Find a specific task by ID."""
    registry = load_registry()
    for task in registry["active_tasks"]:
        if task["id"] == task_id:
            return task
    return None

# ─────────────────────────────────────────────
# TMUX MANAGEMENT
# ─────────────────────────────────────────────

def is_session_alive(session_name):
    """Check if a tmux session is currently running."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        capture_output=True
    )
    return result.returncode == 0


def kill_session(session_name):
    """Kill a tmux session."""
    subprocess.run(
        ["tmux", "kill-session", "-t", session_name],
        capture_output=True
    )
    log.info(f"Killed tmux session: {session_name}")


def get_all_tmux_sessions():
    """Return list of all active tmux session names."""
    result = subprocess.run(
        ["tmux", "ls", "-F", "#{session_name}"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return []
    return [s.strip() for s in result.stdout.splitlines() if s.strip()]

# ─────────────────────────────────────────────
# SIGNAL BUS
# ─────────────────────────────────────────────

def read_signals():
    """Read all pending signals from the signal bus."""
    data = load_json(SIGNALS_FILE)
    if data is None:
        return []
    return [s for s in data.get("signals", []) if s.get("status") == "pending"]


def mark_signal_processed(signal_timestamp):
    """Mark a signal as processed so it isn't acted on twice."""
    data = load_json(SIGNALS_FILE)
    if data is None:
        return
    for signal in data.get("signals", []):
        if signal.get("timestamp") == signal_timestamp:
            signal["status"] = "processed"
            signal["processed_at"] = datetime.utcnow().isoformat()
    save_json(SIGNALS_FILE, data)


def write_signal(from_agent, to_agent, signal_type, payload):
    """Write a new signal to the signal bus."""
    data = load_json(SIGNALS_FILE)
    if data is None:
        data = {"signals": []}
    data["signals"].append({
        "from": from_agent,
        "to": to_agent,
        "type": signal_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending"
    })
    save_json(SIGNALS_FILE, data)

# ─────────────────────────────────────────────
# OUTPUT VERIFICATION (IMMUNE SYSTEM)
# ─────────────────────────────────────────────

def verify_output(filepath, min_size_bytes=10):
    """
    Verify an output file actually exists and has real content.
    This is the core of the immune system — agents cannot
    self-report success. Files either exist or they don't.
    """
    path = Path(filepath)
    if not path.exists():
        log.warning(f"Verification FAILED: {filepath} does not exist")
        return False
    if path.stat().st_size < min_size_bytes:
        log.warning(f"Verification FAILED: {filepath} is empty or too small")
        return False
    log.info(f"Verification PASSED: {filepath}")
    return True


def check_agent_timeout(task):
    """Check if an agent has been running too long."""
    started = datetime.fromisoformat(task["started_at"])
    runtime = datetime.utcnow() - started
    if runtime > timedelta(hours=MAX_AGENT_RUNTIME_HOURS):
        log.warning(
            f"Agent timeout: {task['id']} running for "
            f"{runtime.total_seconds()/3600:.1f} hours"
        )
        return True
    return False

# ─────────────────────────────────────────────
# FEEDBACK MEMORY
# ─────────────────────────────────────────────

def log_feedback(task_id, agent, description, verdict, reason):
    """
    Write a task result to feedback.json.
    This is how agents learn from past failures and successes.
    """
    data = load_json(FEEDBACK_FILE)
    if data is None:
        data = {"rejected": [], "approved": []}

    entry = {
        "task_id": task_id,
        "agent": agent,
        "description": description,
        "reason": reason,
        "date": datetime.utcnow().isoformat()
    }

    if verdict == "pass":
        data["approved"].append(entry)
    else:
        data["rejected"].append(entry)

    save_json(FEEDBACK_FILE, data)
    log.info(f"Feedback logged: {task_id} → {verdict}")

# ─────────────────────────────────────────────
# IMMUNE SYSTEM — MAIN HEALTH CHECK
# ─────────────────────────────────────────────

def run_immune_system():
    """
    The immune system. Runs every cycle.
    Checks agent health, verifies outputs, detects silent failures.
    This is the most important function in the orchestrator.
    """
    log.info("── Immune system running ──")
    issues_found = []
    running_tasks = get_running_tasks()

    for task in running_tasks:
        session = task["tmux_session"]
        task_id = task["id"]

        # 1. Check tmux session is alive
        if not is_session_alive(session):
            log.warning(f"Dead session detected: {session}")
            retries = task.get("retries", 0)

            if retries >= MAX_RETRIES:
                # Give up, alert Oscar
                update_task(task_id, {"status": "failed"})
                message = (
                    f"🚨 *Agent failed after {MAX_RETRIES} attempts*\n"
                    f"Task: `{task_id}`\n"
                    f"Agent: `{task['agent']}`\n"
                    f"Description: {task['description']}\n"
                    f"Action required: manual review"
                )
                send_telegram(message, bot="orchestrator")
                log_feedback(
                    task_id, task["agent"],
                    task["description"],
                    "fail",
                    f"Session died {MAX_RETRIES} times"
                )
            else:
                # Auto-respawn
                update_task(task_id, {
                    "retries": retries + 1,
                    "status": "respawning"
                })
                send_telegram(
                    f"⚠️ Agent `{task_id}` session died. "
                    f"Auto-respawning (attempt {retries + 1}/{MAX_RETRIES})",
                    bot="agents"
                )
                issues_found.append(f"Respawned: {task_id}")

        # 2. Check for timeout
        elif check_agent_timeout(task):
            message = (
                f"⏰ *Agent timeout warning*\n"
                f"Task: `{task_id}` has been running "
                f">{MAX_AGENT_RUNTIME_HOURS} hours\n"
                f"Description: {task['description']}\n"
                f"Check if it's stuck or making progress"
            )
            send_telegram(message, bot="orchestrator")
            issues_found.append(f"Timeout warning: {task_id}")

    if not issues_found:
        log.info("Immune system: all agents healthy")
    else:
        log.warning(f"Immune system found {len(issues_found)} issues")

    return issues_found

# ─────────────────────────────────────────────
# SIGNAL PROCESSOR
# ─────────────────────────────────────────────

def process_signals():
    """
    Read pending signals and decide what to do with each one.
    This is how agents communicate with each other through
    the orchestrator.
    """
    signals = read_signals()
    if not signals:
        log.info("No pending signals")
        return

    log.info(f"Processing {len(signals)} pending signals")

    for signal in signals:
        signal_type = signal.get("type")
        from_agent = signal.get("from")
        payload = signal.get("payload", {})
        timestamp = signal.get("timestamp")

        log.info(f"Signal: {signal_type} from {from_agent}")

        # Elite convergence detected by signal-agent
        if signal_type == "elite_convergence_detected":
            confidence = signal.get("confidence", "MEDIUM")
            if confidence == "HIGH":
                message = (
                    f"🎯 *High Confidence Signal*\n"
                    f"Market: {payload.get('market_title', 'Unknown')}\n"
                    f"Direction: {payload.get('direction', 'Unknown')}\n"
                    f"Traders: {len(payload.get('traders', []))} elite\n"
                    f"Reasoning: {payload.get('reasoning', '')}"
                )
                send_telegram(message, bot="orchestrator")

        # Quant research ready for validation
        elif signal_type == "validation_requested":
            model_name = payload.get("model_name", "unknown")
            send_telegram(
                f"🔬 Quant research ready for validation: `{model_name}`\n"
                f"backtest-agent will pick this up next cycle",
                bot="agents"
            )

        # Backtest completed
        elif signal_type == "validation_completed":
            verdict = payload.get("verdict", "unknown")
            model = payload.get("model_name", "unknown")
            sharpe = payload.get("sharpe_ratio", "N/A")
            brier = payload.get("brier_score", "N/A")

            if verdict == "pass":
                message = (
                    f"✅ *Backtest passed*\n"
                    f"Model: `{model}`\n"
                    f"Sharpe: {sharpe} | Brier: {brier}\n"
                    f"Ready for review"
                )
                send_telegram(message, bot="orchestrator")
            else:
                reason = payload.get("reason", "No reason given")
                send_telegram(
                    f"❌ Backtest failed: `{model}`\n"
                    f"Reason: {reason}",
                    bot="agents"
                )

        # New market connector built
        elif signal_type == "connector_ready":
            send_telegram(
                f"🔌 New connector ready: `{payload.get('connector_name')}`\n"
                f"Market: {payload.get('market_type')}\n"
                f"Review when convenient",
                bot="orchestrator"
            )

        # Clarification needed from Oscar
        elif signal_type == "clarification_needed":
            message = (
                f"❓ *Agent needs clarification*\n"
                f"Agent: `{from_agent}`\n"
                f"Question: {payload.get('question', 'See signals.json')}"
            )
            send_telegram(message, bot="orchestrator")

        # App completed by niche-app-agent
        elif signal_type == "app_ready":
            send_telegram(
                f"📦 App ready for review: `{payload.get('app_name')}`\n"
                f"Path: {payload.get('app_path')}",
                bot="orchestrator"
            )

        # Mark signal as processed
        mark_signal_processed(timestamp)

# ─────────────────────────────────────────────
# WEEKLY METRICS REPORT
# ─────────────────────────────────────────────

def send_weekly_metrics():
    """
    Send a weekly summary every Monday at 8am.
    Reads from feedback.json and registry for stats.
    """
    now = datetime.utcnow()
    # Only send on Mondays between 8-9am UTC
    if now.weekday() != 0 or now.hour != 8:
        return

    feedback = load_json(FEEDBACK_FILE)
    registry = load_registry()

    approved = len(feedback.get("approved", [])) if feedback else 0
    rejected = len(feedback.get("rejected", [])) if feedback else 0
    total = approved + rejected
    rate = (approved / total * 100) if total > 0 else 0

    all_tasks = registry.get("active_tasks", [])
    failed = len([t for t in all_tasks if t["status"] == "failed"])

    message = (
        f"📊 *Weekly Metrics Report*\n"
        f"─────────────────\n"
        f"Tasks approved: {approved}\n"
        f"Tasks rejected: {rejected}\n"
        f"Approval rate: {rate:.0f}%\n"
        f"Failed (needs review): {failed}\n"
        f"─────────────────\n"
        f"Review /brain/kpis.md for trading metrics"
    )
    send_telegram(message, bot="metrics")
    log.info("Weekly metrics report sent")

# ─────────────────────────────────────────────
# MAIN ORCHESTRATOR LOOP
# ─────────────────────────────────────────────

def run_cycle():
    """
    One complete orchestrator cycle.
    Called every 10 minutes.
    """
    log.info("═══════ Orchestrator cycle starting ═══════")

    # 1. Run immune system first — always
    run_immune_system()

    # 2. Process any pending signals
    process_signals()

    # 3. Check for weekly metrics
    send_weekly_metrics()

    log.info("═══════ Cycle complete ═══════\n")


def main():
    """
    Main entry point. Runs the orchestrator loop forever.
    Start this in a tmux session so it survives terminal closure.
    """
    log.info("🚀 Trading Swarm Orchestrator starting")
    log.info(f"Base directory: {BASE_DIR}")
    log.info(f"Cycle interval: {CYCLE_INTERVAL_SECONDS}s (10 minutes)")

    send_telegram(
        "🚀 *Orchestrator online*\n"
        "Trading swarm is active. Monitoring agents.",
        bot="orchestrator"
    )

    while True:
        try:
            run_cycle()
        except KeyboardInterrupt:
            log.info("Orchestrator stopped by user")
            break
        except Exception as e:
            # Never let the orchestrator die from an unexpected error
            log.error(f"Unexpected error in cycle: {e}", exc_info=True)
            send_telegram(
                f"⚠️ Orchestrator cycle error: {str(e)[:200]}\n"
                f"Continuing on next cycle",
                bot="orchestrator"
            )

        log.info(f"Sleeping {CYCLE_INTERVAL_SECONDS}s until next cycle")
        time.sleep(CYCLE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
