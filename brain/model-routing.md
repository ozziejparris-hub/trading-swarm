# Model Routing Strategy

Last updated: 2026-03-19
Updated by: Oscar (Server Pre-Setup Chat 2)
Next review: when server has been live 4 weeks

---

## Purpose

This document is the authoritative source of truth for which
model tier each agent uses and why. It governs two things:

1. `scripts/spawn_agent.sh` — which tier flag to pass when
   spawning any agent manually
2. `orchestrator/orchestrator.py` — the AGENT_TIER_DEFAULTS
   dict, which must mirror the decisions made here

If you change a tier assignment, update both this file
and the dict in orchestrator.py. They must stay in sync.

Agents should read this file before any task involving
model selection decisions. The orchestrator injects it
into every agent prompt via the spawn script.

---

## The Four-Tier Architecture

```
Tier 1 — Ollama/Mistral          (local, free)
Tier 2 — Qwen3-Coder-Next        (local, free after hardware)
Tier 2.5 — Claude Haiku 4.5      ($1/$5 per MTok)
Tier 3 — Claude Sonnet 4.6       ($3/$15 per MTok)
Tier 4 — Claude Opus 4.6         ($5/$25 per MTok, escalation only)
```

The routing logic is simple: use the lowest tier that
can reliably do the job. Tier 3 is the default for
anything ambiguous. Never use Tier 4 as a first attempt.

---

## Confirmed Pricing (March 2026)

```
Model                    Input           Output
────────────────────────────────────────────────
Mistral (Ollama)         Free            Free
Qwen3-Coder-Next         Free (local)    Free (local)
Claude Haiku 4.5         $1.00/MTok      $5.00/MTok
Claude Sonnet 4.6        $3.00/MTok      $15.00/MTok
Claude Opus 4.6          $5.00/MTok      $25.00/MTok
────────────────────────────────────────────────

MTok = million tokens

Prompt caching discount: up to 90% on repeated context
Batch API discount:      50% on both input and output

Note: Sonnet 4.6 and Opus 4.6 have a 1M token context
window with standard pricing (no long-context surcharge
as of March 14 2026). This matters for quant-research
tasks that load large sections of brain/ alongside data.
```

---

## Per-Agent Routing Decisions

### Tier 1 — Ollama/Mistral

**Assigned to:**
- Orchestrator immune system health loop (10-minute cycles)
- Log watching and registry consistency checks
- The `check_agents.sh` and `verify_output.sh` scripts

**Why Tier 1 for these:**
These tasks require near-zero reasoning. The immune system
is checking whether sessions are alive and files are
non-empty. Pattern matching on text. Speed matters more
than intelligence. Running Sonnet on a tmux `has-session`
check would be absurd cost for zero benefit.

**Spawn command:**
```bash
./scripts/spawn_agent.sh <task_id> <agent_type> 1 "<description>"
```

---

### Tier 2 — Qwen3-Coder-Next (local)

**Assigned to:**
- signal-agent (database queries, pattern matching, signals.json writes)
- code-hygiene-agent (dead code scan, duplicate detection, security scan)
- training-librarian-agent (file audits, consistency checks, taxonomy)

**Why Tier 2 for these:**
All three have well-defined tasks with clear inputs and
outputs. Signal-agent queries SQLite and writes JSON —
the task structure is fixed and repeatable. Code-hygiene
runs regex patterns across files. Training-librarian
compares file contents against templates. None require
multi-step statistical reasoning or reading across
large, ambiguous codebases simultaneously.

Qwen3-Coder-Next runs locally on the server's hardware
(128GB RAM), making these tasks completely free after
the server arrives. It has a 256K context window and
achieves >70% on SWE-bench Verified — sufficient for
these well-scoped tasks.

**Hardware requirement:**
Qwen3-Coder-Next target: 14B or 32B parameter version at Q4
quantisation (~10-20GB RAM). The UM890 Pro (96GB DDR5) handles
this comfortably with RAM to spare for concurrent processes.
The 80B MoE version is deferred until larger hardware is available.

**Spawn command:**
```bash
./scripts/spawn_agent.sh <task_id> <agent_type> 2 "<description>"
```

---

### Tier 2.5 — Claude Haiku 4.5

**Assigned to:**
- integration-test-agent (6 structured test suites, every Sunday)
- research-scout-agent (daily scan, filter, file pattern)

**Why Tier 2.5 for these:**

*Integration-test-agent:* runs 6 structured test suites
with fixed logic — signal bus checks, file existence,
JSON validity, registry consistency, CI pipeline,
brain directory integrity. The task is bounded and
well-defined, but it needs reliable tool use and
clean structured output. Anthropic's reliability
guarantees matter here because a silently wrong
integration test report is worse than no report.
At $1/$5 per MTok it costs a fraction of Sonnet.

*Research-scout-agent:* daily scanning, filtering,
and filing from fixed Tier 1 sources. The task
requires judgment about relevance but operates
on a fixed template with defined output format.
Sonnet is overkill for reading arXiv abstracts
and deciding whether they match 6 domain criteria.
Haiku 4.5 achieves 73.3% on SWE-bench Verified —
sufficient for structured filtering work.

**Why not Tier 2 (local) for these:**
Integration-test output is safety-critical — a missed
failure cascades silently. The Anthropic model guarantee
and tool-use reliability of Haiku is worth the small
cost here. Research-scout runs daily; at Haiku pricing
the daily cost is negligible while the consistency
improvement over a local model is meaningful.

**Spawn command:**
```bash
./scripts/spawn_agent.sh <task_id> <agent_type> 2.5 "<description>"
```

---

### Tier 3 — Claude Sonnet 4.6

**Assigned to:**
- quant-research-agent (Phase 1-5 research questions)
- backtest-agent (DSR, PBO, 7-sins validation)
- market-builder-agent (multi-file API connectors, error design)
- market-intelligence-agent (domain analysis, signal routing)
- performance-analyst-agent (trend analysis, recommendations)
- orchestrator main loop (context window, routing, agent spawning)

**Why Tier 3 for these:**

*Quant-research-agent:* Statistical reasoning on subtle
points fails with weaker models. RQ1.1 (ELO persistence),
RQ3.2 (crowd vs elite divergence) require reading across
the research-directions file, reference library sections,
and database outputs simultaneously while reasoning about
statistical validity. Sonnet 4.6 at 79.6% SWE-bench is
the minimum reliable floor for this.

*Backtest-agent:* Must understand Deflated Sharpe Ratio,
Probability of Backtest Overfitting, the 7 sins of
backtesting, and Lopez de Prado's CPCV methodology —
then apply them to code it hasn't seen before. This
is complex multi-file reasoning against a rich reference
library. A false approval is the most expensive mistake
in the system. Sonnet is the minimum.

*Market-builder-agent:* Multi-file API connector work
with production-quality error handling and reconnection
logic. Requires reasoning across API documentation,
existing database schemas, and system conventions
simultaneously.

*Performance-analyst-agent:* Trend analysis across
six metric categories, cross-referencing findings
with reference library citations, producing specific
actionable recommendations. Requires reading multiple
weeks of agent outputs and identifying patterns.

*Orchestrator:* Reads brain/priorities.md, signals.json,
feedback.json, and agent_registry.json every cycle.
Needs enough context window and reasoning to route
signals correctly and make sensible escalation decisions.

**Cost note:** Sonnet 4.6 is priced identically to
Sonnet 4.5 ($3/$15 per MTok) but scores 79.6% on
SWE-bench vs 77.2% for 4.5. Always use 4.6.

**Expected cost split:**
~15-20% of total token spend. Agents run complex tasks
with substantive output. Budget accordingly.

**Spawn command:**
```bash
./scripts/spawn_agent.sh <task_id> <agent_type> 3 "<description>"
```

---

### Tier 4 — Claude Opus 4.6 (escalation only)

**Assigned to:**
- Any task that failed Tier 3 validation three times
- Genuine architectural design decisions
- Tasks Oscar explicitly flags as requiring maximum capability

**What counts as escalation:**
A task has failed Tier 3 three times means exactly that:
the orchestrator has respawned the agent twice already
and it failed both times. On the third failure, the task
moves to Opus. Not before.

"Architecture decision" means: restructuring the agent
system itself, redesigning the signal bus, major changes
to the orchestrator loop. Not "this is a hard coding task."

**What does NOT count as escalation:**
- A task being complex or taking a long time
- Oscar feeling uncertain about an approach
- Quant research questions (these belong at Tier 3)
- Any task where Sonnet hasn't been tried first

**Why this matters:**
Opus 4.6 costs $5/$25 per MTok — 5x Sonnet's output price.
Unnecessary Opus usage at scale would dominate the cost
budget. The 3-failure gate exists to ensure Opus is
used only when Sonnet has genuinely reached its limit,
not as a first resort for anything difficult.

**Spawn command:**
```bash
./scripts/spawn_agent.sh <task_id> <agent_type> 4 "<description>"
```

---

## Complete Assignment Reference

```
Agent                    Tier   Model                    Reason
─────────────────────────────────────────────────────────────────────
Immune system checks     1      Ollama/Mistral           Pattern match
Log watching             1      Ollama/Mistral           Pattern match
signal-agent             2      Qwen3-Coder-Next         Well-defined
code-hygiene-agent       2      Qwen3-Coder-Next         Mechanical
training-librarian       2      Qwen3-Coder-Next         Structured
integration-test         2.5    Claude Haiku 4.5         Reliability
research-scout           2.5    Claude Haiku 4.5         Daily cadence
quant-research           3      Claude Sonnet 4.6        Stats reasoning
backtest-agent           3      Claude Sonnet 4.6        Multi-file valid
market-builder           3      Claude Sonnet 4.6        API multi-file
market-intelligence      3      Claude Sonnet 4.6        Domain analysis
performance-analyst      3      Claude Sonnet 4.6        Trend analysis
orchestrator             3      Claude Sonnet 4.6        Context window
escalation (any)         4      Claude Opus 4.6          3x Sonnet fail
─────────────────────────────────────────────────────────────────────
```

---

## Expected Cost Split

Based on system design and agent cadences:

```
Tier 1 (Ollama/Mistral):      ~40-50% of requests, $0 cost
Tier 2 (Qwen3-Coder-Next):    ~30-40% of requests, $0 cost
Tier 2.5 (Haiku 4.5):         ~5-10% of requests, ~$1/$5 per MTok
Tier 3 (Sonnet 4.6):          ~15-20% of requests, ~$3/$15 per MTok
Tier 4 (Opus 4.6):            ~1-5% of requests, ~$5/$25 per MTok
```

The majority of token spend flows from Tier 3. Quant-research
and backtest-agent produce the longest outputs and run the
most frequently among paid agents. Monitor these two agents
first when reviewing weekly costs.

---

## Cost Reduction Techniques

**Prompt caching (up to 90% reduction on input):**
The orchestrator injects priorities.md, model-routing.md,
and the agent template into every prompt. These are
identical across runs. Enable prompt caching on all
Tier 2.5, 3, and 4 calls once the server is live.
The reference library sections injected by quant-research
are large and stable — caching them reduces cost dramatically.

**Batch API (50% reduction on both input and output):**
Performance-analyst and training-librarian run on a weekly
schedule with no latency requirement. These are prime
candidates for the Batch API once volume justifies it.
Do not batch signal-agent or orchestrator — these are
latency-sensitive.

---

## Model Strings for Claude Code

For use in `scripts/spawn_agent.sh` and any code that
calls Claude directly:

```
claude-haiku-4-5-20251001   ← Tier 2.5
claude-sonnet-4-6            ← Tier 3
claude-opus-4-6              ← Tier 4
```

The Haiku string includes a date suffix (`20251001`) because
Haiku 4.5 was versioned differently from the Sonnet/Opus
4.6 family. Use these exact strings. Do not use older
strings (claude-sonnet-4-5, claude-opus-4-5) — those
refer to the previous generation.

---

## Watch List — Future Routing Changes

These developments may warrant tier reassignments.
research-scout-agent should flag these when they mature:

**Llama 4 Scout (available now — test on server arrival):**
Open-weight MoE model, 109B total / 17B active parameters.
At Q4 quantisation needs ~55GB RAM — potentially runnable on
UM890 Pro's 96GB DDR5 via Ollama CPU inference. If response
time is under 10 seconds for simple tasks, replaces Mistral
at Tier 1 with significantly better capability at zero cost.
Test immediately on server setup before committing to Mistral.
Command: ollama pull llama4:scout
Benchmark: time echo "Is this session alive?" | ollama run llama4:scout

**Gemini 3.1 Pro (cloud, evaluate for Tier 3 cost reduction):**
Leads 13 of 16 major benchmarks. Input pricing $2.00/MTok vs
Sonnet's $3.00/MTok — 33% cheaper at comparable capability.
Not open-weight so sovereignty requirements still apply for
Polymarket system agents. For trading swarm API-driven agents
(quant-research, backtest, orchestrator) evaluate as Tier 3
alternative once system is live and weekly API costs are known.
Blocked until 4 weeks of live cost data available.

**Claude Mythos (released April 7 — gated, Tier 4 candidate):**
Released April 7 to 50 organisations under Project Glasswing.
93.9% SWE-bench Verified, 94.6% GPQA Diamond — best available.
Pricing when public: $25 input / $125 output per MTok.
At that price: Tier 4 escalation only, replaces Opus 4.6.
Not publicly available yet — monitor for general release.

**GPT-6 (released April 14 — evaluate for Tier 4):**
Released April 14. $2.50 input / $12 output per MTok.
40%+ capability improvement over GPT-5.4 at flat pricing.
At $12/MTok output vs Opus $25/MTok — meaningfully cheaper
for comparable capability. Evaluate as Tier 4 alternative
once public benchmarks vs Mythos are clearer.

**Gemma 4 31B (released April 2 — test on server):**
Apache 2.0, free open weights. Outperforms Llama 4 Maverick
on math, reasoning, and coding at 31B parameters.
Potentially runnable on UM890 Pro. Test alongside Llama 4
Scout on server setup — may replace or supplement Tier 2.

**DeepSeek V4 (imminent — most important watch item):**
Reuters confirmed weeks away as of April 3. 1T total / 32B
active parameters, Apache 2.0, $0.14-0.30 per MTok.
If benchmarks hold: replaces Sonnet at Tier 3 at 10x lower
cost. Highest priority model routing change of Q2 2026.
Halt all Tier 3 cost optimisation decisions until V4 drops.

**DeepSeek V4 (anticipated 2026):**
Leaked benchmarks suggest 80%+ SWE-bench Verified with
open weights. If released open-weight and localizable
on the server hardware, it becomes a candidate to
replace or supplement Qwen3-Coder-Next at Tier 2 —
potentially handling tasks currently routed to Sonnet.
Do not act until independently verified benchmarks
exist. Leaked benchmarks have historically been optimistic.

**MiniMax M2.7 open-weight release:**
Currently proprietary and cloud-only. If released as
open weights, its benchmark parity with Sonnet 4.6
at significantly lower cost makes it a Tier 2.5 or
Tier 3 candidate. Blocked currently by sovereignty
requirements — Chinese-hosted API fails data governance.
Open weights would remove that blocker.
Update April 2026: M2.7 claims Anthropic-compatible API
(drop-in replacement, no code changes needed), native
tool use with agentic loop, and 95% cheaper than Opus.
Workflow engine implementations emerging. If open-weight
released, priority evaluation — compatible API means
zero integration cost. Sovereignty blocker remains
until open weights confirmed.

**Qwen3-Coder-480B quantised locally:**
Deferred — requires ~250GB RAM, not viable on current hardware
(96GB UM890 Pro). Revisit if hardware is upgraded in 2027.
Continue monitoring Unsloth for 32B quantisation improvements
which are viable on current hardware.

---

## Routing Change Protocol

Before changing any tier assignment in this document:

1. State the specific reason — which benchmark or
   observed failure justifies the change
2. Update this file with the new assignment and rationale
3. Update AGENT_TIER_DEFAULTS in orchestrator/orchestrator.py
   to match
4. Update the tier flag in any scheduled spawn commands
5. Log the decision in brain/decisions/ with date and reason
6. Run CI to confirm nothing breaks

Never change tier assignments based on cost alone.
The tier must be capable of doing the job reliably.
Saving $2/week on a task that then fails silently
costs more than $2 to fix.

---

## Quick Reference

```
Task requires near-zero reasoning, pattern matching?
→ Tier 1 (Ollama/Mistral, free)

Task is well-defined with clear inputs and outputs,
runs frequently, mechanical in nature?
→ Tier 2 (Qwen3-Coder-Next, free)

Task needs Anthropic reliability, runs on a schedule,
bounded scope but judgment required?
→ Tier 2.5 (Claude Haiku 4.5, $1/$5 per MTok)

Task requires complex multi-file reasoning, statistical
validity, reading across reference library simultaneously?
→ Tier 3 (Claude Sonnet 4.6, $3/$15 per MTok)

Task has failed Tier 3 three times OR is genuinely
architectural in scope?
→ Tier 4 (Claude Opus 4.6, $5/$25 per MTok)
```
