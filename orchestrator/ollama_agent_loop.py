#!/usr/bin/env python3
"""
Ollama Agentic Loop Wrapper (Option A)

Provides tool-calling infrastructure for local LLM agents running via the
Ollama REST API. Implements a controlled loop with per-agent tool allowlists,
safety-checked file/DB access, and structured logging.

Exit codes:
  0 — clean completion (model returned no tool calls)
  1 — max iterations exceeded
  2 — max time exceeded
  3 — unrecoverable setup/tool failure
  4 — Ollama API unreachable
"""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

MAX_ITERATIONS = 50
WARN_ITERATIONS = 30
MAX_SECONDS = 3600
OLLAMA_API_URL = "http://localhost:11434/api/chat"
OLLAMA_TIMEOUT_S = 600  # per-call socket timeout

READ_PREFIX = "/home/parison/"
WRITE_PREFIX = "/home/parison/trading-swarm/"
SIZE_CAP = 50 * 1024  # 50KB

ENV_FILE = Path.home() / ".env_trading"

# Module-level Telegram rate-limit state
_tg_last_call_ts: float = 0.0
_tg_recent: dict[str, float] = {}  # message → last-sent timestamp

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

log = logging.getLogger("ollama_loop")


def _setup_logging(log_file: str | None) -> None:
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stderr),
    ]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    log.setLevel(logging.INFO)
    for h in handlers:
        h.setFormatter(fmt)
        log.addHandler(h)


# ─────────────────────────────────────────────
# ENV FILE READER
# ─────────────────────────────────────────────

def _load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip().removeprefix("export").strip()
            val = val.strip().strip('"').strip("'")
            env[key] = val
    return env


# ─────────────────────────────────────────────
# TOOL: read_file
# ─────────────────────────────────────────────

def tool_read_file(path: str) -> str | dict:
    if not path.startswith(READ_PREFIX):
        return {"error": f"path must start with {READ_PREFIX!r}"}
    p = Path(path)
    if not p.exists():
        return {"error": f"file not found: {path}"}
    if not p.is_file():
        return {"error": f"not a regular file: {path}"}
    size = p.stat().st_size
    with open(p, errors="replace") as f:
        content = f.read(SIZE_CAP)
    if size > SIZE_CAP:
        content += f"\n\n[TRUNCATED: file is {size} bytes; only first {SIZE_CAP} bytes shown]"
    return content


# ─────────────────────────────────────────────
# TOOL: write_file
# ─────────────────────────────────────────────

def tool_write_file(path: str, content: str) -> dict:
    if not path.startswith(WRITE_PREFIX):
        return {"error": f"path must start with {WRITE_PREFIX!r}"}
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# TOOL: append_to_json_array
# ─────────────────────────────────────────────

def tool_append_to_json_array(path: str, array_key: str, entry: dict) -> dict:
    if not isinstance(entry, dict):
        return {"error": "entry must be a dict"}
    if not path.startswith(WRITE_PREFIX):
        return {"error": f"path must start with {WRITE_PREFIX!r}"}

    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch(exist_ok=True)
    except Exception as e:
        return {"error": f"cannot prepare file: {e}"}

    for attempt in range(3):
        fh = None
        try:
            fh = open(p, "r+b")
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if fh:
                fh.close()
            if attempt < 2:
                time.sleep(1)
                continue
            return {"error": "could not acquire file lock after 3 attempts"}
        except Exception as e:
            if fh:
                fh.close()
            return {"error": str(e)}

        try:
            raw = fh.read()
            data = json.loads(raw) if raw.strip() else {}
            if not isinstance(data, dict):
                return {"error": "JSON root is not an object"}
            arr = data.get(array_key, [])
            if not isinstance(arr, list):
                return {"error": f"'{array_key}' is not an array in the JSON"}
            arr.append(entry)
            data[array_key] = arr
            fh.seek(0)
            fh.truncate()
            fh.write(json.dumps(data, indent=2).encode())
            return {"ok": True, "array_length": len(arr)}
        except Exception as e:
            return {"error": str(e)}
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            fh.close()

    return {"error": "failed after 3 lock attempts"}


# ─────────────────────────────────────────────
# TOOL: run_sql
# ─────────────────────────────────────────────

_SQL_WRITE_RE = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b", re.IGNORECASE
)


def tool_run_sql(db_path: str, query: str, params: list | None = None) -> dict:
    if params is None:
        params = []
    if _SQL_WRITE_RE.match(query):
        return {"error": "only read-only SELECT queries are permitted"}
    if not db_path.startswith(READ_PREFIX):
        return {"error": f"db_path must start with {READ_PREFIX!r}"}

    def _execute() -> dict:
        con = sqlite3.connect(db_path, timeout=30)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        con.row_factory = sqlite3.Row
        try:
            cur = con.execute(query, params)
            # Fetch one extra to detect truncation
            batch = cur.fetchmany(101)
            truncated = len(batch) > 100
            rows = [dict(r) for r in batch[:100]]
            result: dict = {"rows": rows, "count": len(rows)}
            if truncated:
                result["truncated"] = True
            return result
        finally:
            con.close()

    try:
        return _execute()
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            log.warning("run_sql: DB locked, retrying after 30s")
            time.sleep(30)
            try:
                return _execute()
            except sqlite3.OperationalError as e2:
                return {"error": f"DB still locked after retry: {e2}"}
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# TOOL: send_telegram
# ─────────────────────────────────────────────

def tool_send_telegram(message: str, bot: str) -> dict:
    global _tg_last_call_ts, _tg_recent

    if bot not in ("agents", "orchestrator"):
        return {"error": "bot must be 'agents' or 'orchestrator'"}

    env = _load_env_file(ENV_FILE)
    token_key = f"TELEGRAM_{bot.upper()}_TOKEN"
    token = env.get(token_key, "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not token:
        return {"error": f"missing {token_key} in ~/.env_trading"}
    if not chat_id:
        return {"error": "missing TELEGRAM_CHAT_ID in ~/.env_trading"}

    # Per-session deduplication (60s window)
    now = time.time()
    last_sent = _tg_recent.get(message, 0.0)
    if now - last_sent < 60:
        return {"error": "duplicate suppressed: identical message sent within 60s"}

    # Rate limit: minimum 1.5s between any calls
    elapsed = now - _tg_last_call_ts
    if elapsed < 1.5:
        time.sleep(1.5 - elapsed)

    def _post() -> int:
        payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status

    try:
        _post()
        _tg_last_call_ts = time.time()
        _tg_recent[message] = _tg_last_call_ts
        return {"ok": True}
    except urllib.error.HTTPError as e:
        if e.code == 429:
            log.warning("send_telegram: HTTP 429 rate limit, retrying after 2s")
            time.sleep(2)
            try:
                _post()
                _tg_last_call_ts = time.time()
                _tg_recent[message] = _tg_last_call_ts
                return {"ok": True}
            except Exception as e2:
                return {"error": f"HTTP 429 retry failed: {e2}"}
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# TOOL: run_shell
# ─────────────────────────────────────────────

_SHELL_WHITELIST: list[list[str]] = [
    ["tmux", "ls", "-F", "#{session_name}"],
    ["bash", "/home/parison/trading-swarm/ci/run_ci.sh"],
]


def tool_run_shell(command: list) -> dict:
    if command not in _SHELL_WHITELIST:
        return {"error": f"command not in whitelist: {command!r}"}
    try:
        result = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {"stdout": result.stdout, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "command timed out after 60s"}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# TOOL REGISTRY
# ─────────────────────────────────────────────

TOOL_FUNCTIONS: dict[str, object] = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "append_to_json_array": tool_append_to_json_array,
    "run_sql": tool_run_sql,
    "send_telegram": tool_send_telegram,
    "run_shell": tool_run_shell,
}

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a file from disk and return its text content. "
                "Files larger than 50 KB are truncated with a notice. "
                "Path must start with /home/parison/."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write text content to a file, creating parent directories if needed. "
                "Path must start with /home/parison/trading-swarm/."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute destination path.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full text content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_to_json_array",
            "description": (
                "Atomically append a dict entry to a named array in a JSON file. "
                "Uses an exclusive file lock to prevent concurrent write corruption. "
                "Path must start with /home/parison/trading-swarm/."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the JSON file.",
                    },
                    "array_key": {
                        "type": "string",
                        "description": "Top-level key whose value is the array to append to.",
                    },
                    "entry": {
                        "type": "object",
                        "description": "Dict to append to the array.",
                    },
                },
                "required": ["path", "array_key", "entry"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": (
                "Execute a read-only SQL SELECT query against a SQLite database. "
                "INSERT/UPDATE/DELETE/DROP/CREATE/ALTER queries are rejected. "
                "Returns up to 100 rows. db_path must start with /home/parison/."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "db_path": {
                        "type": "string",
                        "description": "Absolute path to the SQLite database file.",
                    },
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query to run.",
                    },
                    "params": {
                        "type": "array",
                        "items": {},
                        "description": "Positional parameters for parameterised queries (optional).",
                    },
                },
                "required": ["db_path", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_telegram",
            "description": (
                "Send a Telegram message via a configured bot. "
                "bot must be 'agents' or 'orchestrator'. "
                "Identical messages within 60 s are suppressed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Text to send.",
                    },
                    "bot": {
                        "type": "string",
                        "description": "Which bot to use: 'agents' or 'orchestrator'.",
                    },
                },
                "required": ["message", "bot"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Run a whitelisted shell command. "
                "Only two commands are permitted: "
                "['tmux', 'ls', '-F', '#{session_name}'] and "
                "['bash', '/home/parison/trading-swarm/ci/run_ci.sh']."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command as a list of strings.",
                    },
                },
                "required": ["command"],
            },
        },
    },
]


# ─────────────────────────────────────────────
# TOOL DISPATCHER
# ─────────────────────────────────────────────

def _dispatch(name: str, args: dict, allowed: list[str]) -> str:
    """Call a tool and return its result serialised to a string for the LLM."""
    if name not in allowed:
        return json.dumps({"error": f"tool '{name}' not permitted for this agent type"})
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        result = fn(**args)
    except TypeError as e:
        return json.dumps({"error": f"bad arguments for {name}: {e}"})
    if isinstance(result, str):
        return result
    return json.dumps(result)


# ─────────────────────────────────────────────
# FALLBACK JSON TOOL-CALL PARSER
# ─────────────────────────────────────────────

# Patterns for models that embed tool calls in text content rather than using
# the structured tool_calls field (e.g., some Ollama models in reasoning mode).
_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_INLINE_RE = re.compile(r'\{[^{}]*"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{', re.DOTALL)


def _fallback_parse(content: str) -> dict | None:
    """
    Try to extract a tool call from free-text content.
    Returns {"name": str, "arguments": dict} or None.
    """
    candidates: list[str] = []

    # Check fenced code blocks first
    for m in _FENCE_RE.finditer(content):
        candidates.append(m.group(1))

    # Check for inline JSON objects containing "name" and "arguments"
    for m in _INLINE_RE.finditer(content):
        # Walk forward to find the matching closing brace
        start = m.start()
        depth = 0
        for i, ch in enumerate(content[start:]):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(content[start : start + i + 1])
                    break

    # Also try the whole content as JSON
    candidates.append(content.strip())

    for raw in candidates:
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        # Direct format: {"name": "...", "arguments": {...}}
        if "name" in obj and isinstance(obj.get("arguments"), dict):
            return {"name": obj["name"], "arguments": obj["arguments"]}
        # Wrapped format: {"function": {"name": "...", "arguments": {...}}}
        fn = obj.get("function")
        if isinstance(fn, dict) and "name" in fn:
            return {"name": fn["name"], "arguments": fn.get("arguments", {})}

    return None


# ─────────────────────────────────────────────
# OLLAMA API CALL
# ─────────────────────────────────────────────

def _call_ollama(model: str, messages: list, tools: list) -> dict:
    payload = json.dumps(
        {"model": model, "messages": messages, "tools": tools, "stream": False}
    ).encode()
    req = urllib.request.Request(
        OLLAMA_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_S) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        raise ConnectionError(f"Ollama API unreachable at {OLLAMA_API_URL}: {e}") from e


# ─────────────────────────────────────────────
# AGENTIC LOOP
# ─────────────────────────────────────────────

def run_loop(
    model: str,
    prompt: str,
    allowed_tools: list[str],
    task_id: str,
) -> int:
    active_tool_defs = [
        t for t in TOOL_DEFINITIONS if t["function"]["name"] in allowed_tools
    ]
    messages: list[dict] = [{"role": "user", "content": prompt}]

    start_ts = time.time()
    iteration = 0
    tools_called = 0
    tool_call_log: list[str] = []

    log.info(
        f"[{task_id}] loop start — model={model} "
        f"allowed_tools={allowed_tools} max_iter={MAX_ITERATIONS}"
    )

    while True:
        # ── time guard ──
        elapsed = time.time() - start_ts
        if elapsed > MAX_SECONDS:
            log.error(f"[{task_id}] max time ({MAX_SECONDS}s) exceeded")
            _summarise(task_id, iteration, tools_called, tool_call_log, "max_time_exceeded")
            return 2

        # ── iteration guard ──
        if iteration >= MAX_ITERATIONS:
            log.warning(f"[{task_id}] max iterations ({MAX_ITERATIONS}) reached")
            _summarise(task_id, iteration, tools_called, tool_call_log, "max_iterations_exceeded")
            return 1

        if iteration == WARN_ITERATIONS:
            log.warning(
                f"[{task_id}] iteration {WARN_ITERATIONS} reached — "
                f"approaching limit of {MAX_ITERATIONS}"
            )

        iteration += 1
        log.info(f"[{task_id}] iteration {iteration}/{MAX_ITERATIONS} (elapsed {elapsed:.0f}s)")

        # ── call Ollama ──
        try:
            response = _call_ollama(model, messages, active_tool_defs)
        except ConnectionError as e:
            log.error(f"[{task_id}] {e}")
            _summarise(task_id, iteration, tools_called, tool_call_log, "ollama_unreachable")
            return 4

        msg = response.get("message", {})
        role = msg.get("role", "assistant")
        content = msg.get("content") or ""
        raw_tool_calls: list[dict] = msg.get("tool_calls") or []

        # ── append assistant turn to history (no null fields) ──
        assistant_msg: dict = {"role": role, "content": content}
        if raw_tool_calls:
            assistant_msg["tool_calls"] = raw_tool_calls
        messages.append(assistant_msg)

        # ── fallback: detect tool call embedded in text content ──
        if not raw_tool_calls and content:
            parsed = _fallback_parse(content)
            if parsed:
                log.info(
                    f"[{task_id}] fallback parser found tool call in text content: "
                    f"{parsed['name']}"
                )
                raw_tool_calls = [{"function": parsed}]

        # ── no tool calls → model is done ──
        if not raw_tool_calls:
            log.info(f"[{task_id}] clean completion (no tool calls in response)")
            if content:
                preview = content[:400] + ("..." if len(content) > 400 else "")
                log.info(f"[{task_id}] final output preview: {preview}")
            _summarise(task_id, iteration, tools_called, tool_call_log, "clean_completion")
            return 0

        # ── process tool calls ──
        for tc in raw_tool_calls:
            fn_info: dict = tc.get("function", tc)
            tool_name: str = fn_info.get("name", "")
            raw_args = fn_info.get("arguments", {})

            # Some models serialise arguments as a JSON string
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except json.JSONDecodeError as e:
                    error_payload = json.dumps(
                        {"error": f"malformed JSON in tool arguments: {e}"}
                    )
                    log.warning(
                        f"[{task_id}] malformed args for '{tool_name}' — "
                        f"returning error to model"
                    )
                    messages.append({"role": "tool", "content": error_payload})
                    continue

            if not isinstance(raw_args, dict):
                error_payload = json.dumps(
                    {"error": f"arguments must be a JSON object, got {type(raw_args).__name__}"}
                )
                messages.append({"role": "tool", "content": error_payload})
                continue

            tools_called += 1
            tool_call_log.append(tool_name)

            # Log call with summarised args (never log full file content)
            args_summary = {
                k: (str(v)[:100] + "…" if len(str(v)) > 100 else v)
                for k, v in raw_args.items()
            }
            log.info(f"[{task_id}] tool_call: {tool_name}({args_summary})")

            result_str = _dispatch(tool_name, raw_args, allowed_tools)

            result_bytes = len(result_str.encode())
            is_error = result_str.startswith('{"error"')
            status = "error" if is_error else "ok"
            log.info(
                f"[{task_id}] tool_result: {tool_name} → {status} ({result_bytes} bytes)"
            )

            messages.append({"role": "tool", "content": result_str})

    # unreachable
    return 0


def _summarise(
    task_id: str,
    iterations: int,
    tools_called: int,
    tool_log: list[str],
    reason: str,
) -> None:
    counts = dict(Counter(tool_log))
    log.info(
        f"[{task_id}] SUMMARY — "
        f"iterations={iterations} tools_called={tools_called} "
        f"exit_reason={reason!r} tool_breakdown={counts}"
    )


# ─────────────────────────────────────────────
# PERMISSIONS LOADER
# ─────────────────────────────────────────────

def _load_permissions(permissions_file: str, agent_type: str) -> list[str]:
    p = Path(permissions_file)
    if not p.exists():
        log.error(f"permissions file not found: {permissions_file}")
        return []
    try:
        data = json.loads(p.read_text())
    except Exception as e:
        log.error(f"failed to parse permissions file: {e}")
        return []
    tools: list[str] = data.get(agent_type, [])
    if not tools:
        log.warning(f"no tool permissions defined for agent type: {agent_type!r}")
    return tools


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Ollama agentic loop wrapper with tool-calling and per-agent allowlists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--model", required=True, help="Ollama model name (e.g. qwen3-coder:30b-a3b-q4_K_M)")
    p.add_argument("--prompt-file", required=True, help="Path to assembled prompt file")
    p.add_argument("--task-id", required=True, help="Task ID for logging")
    p.add_argument("--agent-type", required=True, help="Agent type for allowlist lookup")
    p.add_argument("--log-file", default=None, help="Path to log file (optional)")
    p.add_argument(
        "--permissions-file",
        default="orchestrator/agent_tool_permissions.json",
        help="Path to agent_tool_permissions.json",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()
    _setup_logging(args.log_file)

    # Load prompt
    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        log.error(f"prompt file not found: {args.prompt_file}")
        sys.exit(3)
    prompt = prompt_path.read_text()

    # Load allowlist
    allowed_tools = _load_permissions(args.permissions_file, args.agent_type)
    if not allowed_tools:
        log.error(
            f"no tools permitted for agent type '{args.agent_type}' — cannot proceed"
        )
        sys.exit(3)

    log.info(
        f"ollama_agent_loop starting — "
        f"task={args.task_id} agent={args.agent_type} model={args.model} "
        f"allowed_tools={allowed_tools}"
    )

    exit_code = run_loop(
        model=args.model,
        prompt=prompt,
        allowed_tools=allowed_tools,
        task_id=args.task_id,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
