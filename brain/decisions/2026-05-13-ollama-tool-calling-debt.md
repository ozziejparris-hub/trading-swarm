# Architectural Debt — Ollama Tool Calling

Date: 2026-05-13
Raised by: Oscar (signal-agent Tier 2.5 experiment)

## The Problem
Ollama models invoked via stdin (spawn_agent.sh Tiers 1/2/2.5) can only
produce text output. They cannot execute tools, write files, query SQLite,
or send Telegram messages. This makes them unsuitable for action-taking
agents — only reasoning/classification tasks where a Python wrapper handles
all I/O.

## Discovery
signal-agent was moved to Tier 2.5 (Qwen3-Coder 30B-A3B) on 2026-05-13
after a benchmark showed clean JSON reasoning output. The benchmark tested
isolated reasoning only — not file I/O or DB execution. When run as a full
agent cycle, Qwen3-Coder produced a correct-looking report in text but
wrote zero files and executed zero SQL. The April 2026 signal runs that
produced real output used claude-sonnet-4-6 (Tier 3, Claude CLI with tools).

## The Fix Required
To use Ollama models for action-taking agents, one of two architectures
is needed:

OPTION A — Ollama REST API + tool calling:
  Call POST http://localhost:11434/api/chat with a tools[] array defining
  available functions (read_file, write_file, run_sql, send_telegram).
  Build a Python agentic loop that:
  1. Sends prompt + tool definitions to Ollama API
  2. Receives tool_call responses
  3. Executes the tool and returns results
  4. Loops until the model signals completion
  Qwen3-Coder natively supports this format.

OPTION B — Python wrapper with LLM reasoning step only:
  Python script handles all I/O directly (DB queries, file writes,
  Telegram). Only calls Ollama for the reasoning/classification step:
  "Here are the positions I found — which qualify as signals?"
  Model outputs a decision, Python acts on it.
  Similar to how feedback-loop-agent works (pure Python, no LLM for I/O).

## Recommendation
Option B is simpler and more reliable for well-defined tasks.
Option A is more flexible and reusable across multiple agents.

If Option A is implemented, signal-agent would be the right first
candidate — its tool requirements are well-defined (SQLite read,
file write, Telegram send).

## Priority
LOW — signal-agent works correctly at Tier 3 (Sonnet). Implement only
if Tier 3 API costs become a concern or if local-only operation is
required for sovereignty reasons.

## Affected Agents
Current Tier 1/2 agents (immune system, log watching) are classification
tasks with no file I/O — they are correctly assigned.
Any future agent requiring real actions must be Tier 3+ until this
debt is resolved.
