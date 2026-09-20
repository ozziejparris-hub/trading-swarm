# spawn_agent.sh's silent session-limit failure — fixed

**Date:** 2026-09-20
**Trigger:** tier-2.5 scoping doc (`2026-09-19-tier25-supervisory-agent-scoping.md`,
commit `a1db987`) named this as blocking: a Claude-backed `spawn_agent.sh` run
that hits Claude's session limit exits clean, is marked `"completed"` in the
registry, and produces silent zero output with no alert. Not hypothetical — a
fork hit exactly this on 2026-09-19 at 13:24 and failed loudly only because it
happened to be interactive:

> Agent terminated early due to an API error: You've hit your session limit ·
> resets 1:40pm (UTC) (error type rate_limit, HTTP 429)

Spawned instead of run interactively, that run would have been recorded as a
success. No further Claude-backed agent work was to land on top of this until
it was closed.

**Scope:** failure detection only. No agent, prompt, model, tier, orchestrator,
or crontab was touched. No production table was written. Nothing paused was
re-enabled (see "What this does not fix" at the end).

---

## Part 1 — the mechanism, precisely

### How `spawn_agent.sh` invokes Claude and what it captured

Tiers 3/4 (Claude CLI, the only tiers that can hit a session/rate limit) ran,
before this fix, as (`scripts/spawn_agent.sh`, the tmux command chain):

```bash
unset ANTHROPIC_API_KEY && $MODEL_CMD "$(cat $PROMPT_FILE)" 2>&1 | tee -a $LOG_FILE; \
rm -f $PROMPT_FILE; \
python3 $CLEANUP_FILE $TASK_ID >> $LOG_FILE 2>&1; \
( git ... merge ... ) >> $LOG_FILE 2>&1; \
rm -f $CLEANUP_FILE; tmux kill-session -t $SESSION_NAME
```

where `$MODEL_CMD` for Tier 3 is:

```bash
MODEL_CMD="claude --model claude-sonnet-4-6 --dangerously-skip-permissions -p"
```

Both stdout and stderr (`2>&1`) were piped into `tee -a $LOG_FILE`, which
appends everything to the per-task log **and** echoes it into the tmux pane.
So the model's raw output — success or error text — always reached
`$LOG_FILE`, appended after a `=== Agent Output ===` marker the script writes
just before the model runs.

### How it decided an agent "completed"

It didn't decide anything. Every statement in the chain above is joined with
`;`, not `&&`, so **nothing downstream of the model command is conditional
on what it did**. The pipeline's own exit status (which bash sets from the
*last* command in a pipe — `tee`, which itself essentially always exits 0) is
never even read into a variable. The very next thing that runs,
unconditionally, is the cleanup script:

```python
# CLEANUP_EOF, as it existed before this fix
for t in registry['active_tasks']:
    if t['id'] == task_id:
        t['status'] = 'completed'
        break
with open(registry_path, 'w') as f:
    json.dump(registry, f, indent=2)
registry['active_tasks'] = [t for t in registry['active_tasks'] if t['id'] != task_id]
with open(registry_path, 'w') as f:
    json.dump(registry, f, indent=2)
```

This checks **only** that a task with that ID exists. Not exit code. Not
output length. Not output content. It sets `status = 'completed'`, writes
that, then immediately deletes the entry from `active_tasks` and writes
again — so even a *genuine* success left no lasting "completed" record in the
registry; the task simply stopped appearing. The registry's only knowledge
of what happened lives in the log file, which nothing reads back.

### Where the registry lives, what it records, what marked success

`orchestrator/agent_registry.json`, shape `{"active_tasks": [...]}`. On
spawn, `spawn_agent.sh` appends a full record (`id`, `agent`, `description`,
`branch`, `tmux_session`, `model`, `tier`, `worktree`, `log`, `started_at`,
`status: "running"`, `retries: 0`, `pr: null`, `verified: false`). "Success"
was defined entirely by the cleanup script above: task ID found → completed
→ deleted. There was no other definition anywhere.

### Does the session-limit response reach the script's exit path at all?

**Yes — it reaches the log file. It never reaches a decision.** The quoted
2026-09-19 13:24 message is exactly the kind of text `tee` would capture into
`$LOG_FILE`'s `=== Agent Output ===` section. But since nothing after the
pipe inspects `$?`/`${PIPESTATUS[0]}` or the captured text, the message being
present in the log changed nothing about what the script did next. This
rules out the first STOP CONDITION (the fix does not belong "elsewhere" —
it belongs exactly at this pipe).

### Does `orchestrator.py`'s own "immune system" already catch this?

No, and understanding why matters for not duplicating or fighting it.
`orchestrator.py::run_immune_system()` only inspects
`get_running_tasks()`, which is:

```python
def get_running_tasks():
    ...
    return [t for t in registry["active_tasks"] if t["status"] == "running"]
```

and its only two checks are "is the tmux session dead while status is still
`running`" (a session that was killed out from under the command — network
drop, `kill -9`, machine reboot) and "has it been running longer than
`MAX_AGENT_RUNTIME_HOURS` (4)". Both require the task to still be sitting in
`active_tasks` with `status == "running"` when the orchestrator's 10-minute
poll lands. But `spawn_agent.sh`'s own chain **always** runs its cleanup step
and kills the tmux session itself, synchronously, immediately after the model
command returns — whether or not that return was an error. By the time the
orchestrator could poll, the task is already gone. The orchestrator's immune
system and `spawn_agent.sh`'s own completion path check two disjoint failure
classes: **"the session died before cleanup could run"** (orchestrator's
job) vs. **"cleanup ran, but on a Claude CLI call that failed"** (nobody's
job, until now). This also confirms the second STOP CONDITION doesn't apply:
changing what the registry says about a *finished* run doesn't touch how the
orchestrator detects a *dead* one.

### The full failure-mode inventory

Every one of these returns control to the shell (rather than hanging) with
some exit code and some captured text, and every one was, before this fix,
indistinguishable from success:

| Failure mode | What actually happens | Old behavior |
|---|---|---|
| **Session/rate limit** (the reported case) | CLI exits, prints `"...hit your session limit...(error type rate_limit, HTTP 429)"` | Recorded completed |
| **Network failure** | CLI exits non-zero, prints a fetch/connection error | Recorded completed |
| **Auth expiry** | CLI exits non-zero, prints a re-auth prompt/error | Recorded completed |
| **Model unavailable** | CLI exits non-zero, prints "model not found"/deprecation error | Recorded completed |
| **Any other API/CLI error that returns** | CLI exits non-zero, prints its own error text | Recorded completed |
| **A clean exit that produces nothing** (belt-and-suspenders case; not observed yet but structurally identical) | CLI exits 0, nothing usable printed | Recorded completed |
| **Timeout / hung session** | CLI never returns; cleanup never runs | *Different* signature — task stays `status: "running"` forever, invisible to `get_running_tasks()`'s dead-session check only because the session is (correctly) still alive, and `MAX_AGENT_RUNTIME_HOURS` timeout **should** eventually catch it via the orchestrator, assuming the orchestrator process itself is up. Not the bug asked about here, but a related visibility gap worth naming: it doesn't fail silently, it just fails slowly. Out of scope for this fix. |
| **Worktree merge failure** (post-completion step) | `git merge` fails after cleanup already ran | Already partially handled — logged as "MERGE FAILED... branch preserved" — but irrelevant to registry status, since by then the task is already marked completed and deleted regardless of merge outcome. Not touched by this fix (out of scope: "does not change what agents do"; the merge step's own error handling is unrelated to run-outcome classification). |

The common root cause behind every row except the last two: **the cleanup
step's only test was "does this task ID exist", never "did this task ID's
run produce anything real."**

---

## Part 2 — the fix

Principle applied: *a run that produced no usable output must not be
recorded as completed, whatever its exit code.*

### 1. Capture the real exit code (`scripts/spawn_agent.sh`)

```bash
unset ANTHROPIC_API_KEY && $MODEL_CMD "$(cat $PROMPT_FILE)" 2>&1 | tee -a $LOG_FILE; \
_claude_exit=${PIPESTATUS[0]}; \
rm -f $PROMPT_FILE; \
python3 $CLEANUP_FILE $TASK_ID $_claude_exit $LOG_FILE >> $LOG_FILE 2>&1; \
...
```

`${PIPESTATUS[0]}` is the Claude CLI's own exit code, not `tee`'s. Confirmed
the tmux pane's shell is bash (`getent passwd parison` → `/bin/bash`,
`$SHELL` → `/bin/bash`), so this is safe. Tiers 1/2/2.5 (Ollama, not
Claude-backed, cannot hit this class of failure) are untouched — their
cleanup call still passes only `$TASK_ID`.

### 2. Classify before recording anything (`orchestrator/agent_failure_notifier.py`, new)

```python
def classify_output(claude_exit_code: int, agent_output: str) -> str:
    if RATE_LIMIT_RE.search(agent_output):
        return "rate_limited"
    if not agent_output.strip():
        return "empty_output"
    if claude_exit_code != 0:
        return "cli_error"
    return "completed"
```

`agent_output` is read from `$LOG_FILE`, but **only the content after the
`=== Agent Output ===` marker** — the file also contains the full injected
prompt, which is never empty even when the model produced nothing, so
scanning the whole file would have defeated the empty-output check entirely.
The rate-limit check runs first and wins regardless of exit code, so it can
never collapse into "cli_error" (a plain crash) or "empty_output" (a genuine
empty result) — the task's explicit requirement that it be its own,
distinguishable outcome.

`RATE_LIMIT_RE` matches `session limit`, `rate[_ -]?limit`, and
`HTTP\D{0,4}429` case-insensitively — broad enough to catch the exact
2026-09-19 wording and its likely variants, narrow enough (subject-scoped to
rate/session limits) not to swallow unrelated errors.

### 3. A registry state that is neither "completed" nor a crash

```python
def mark_attention_required(task_id, failure_kind, claude_exit_code):
    ...
    t['status'] = 'attention_required'
    t['failure_kind'] = failure_kind        # "rate_limited" | "empty_output" | "cli_error"
    t['claude_exit_code'] = claude_exit_code
    t['detected_at'] = ...
```

The task **stays in `active_tasks`**, visible, instead of being deleted. This
cannot confuse `orchestrator.py`'s immune system: `get_running_tasks()`
filters on `status == "running"` only, so `attention_required` is invisible
to it by construction — no orchestrator change needed or made. A genuine
completion (`classify_output` returns `"completed"`) still goes through
`mark_completed()`, which reproduces the exact old behavior: removed from
`active_tasks` entirely.

Both registry writes were also moved onto this repo's existing
`orchestrator/json_safety.py` primitives (`json_lock`, `load_json_or_raise`,
`atomic_write_json`) — the same ones `orchestrator.py` itself uses for this
file. The old cleanup script read/wrote the registry with no locking at all,
racing against `orchestrator.py`'s own locked writes to the same file. This
is incidental correctness riding along with the required change (same file,
same write), not scope creep — it does not change what any agent does.

### 4. Reaching a human — assessment of `monitoring/failure_age.py`

Assessed and used, with one deliberate adaptation.

`failure_age.py`'s model — age-track a set of "finding keys" across runs,
gate alerts through `config/accepted_failures.json`, stay quiet on anything
already reported and still true — is designed for a *periodically
re-evaluated* check (like `audit_invariants.py`, run daily, re-deriving "what
is failing right now" from scratch each time). `spawn_agent.sh`'s failure is
event-driven, one-shot, and per-task: there's no periodic re-check to ever
observe a key's absence and declare it "resolved."

Rather than force a poor fit, the adaptation is in what the **key** is: keys
are `spawn_agent::{failure_kind}` — coarse, by *kind*, not by task ID. This
means:

- The **first** `rate_limited` failure (or `empty_output`, or `cli_error`)
  alerts.
- Every subsequent failure of the **same kind**, before anything resolves it,
  is classified `"ongoing"` by `failure_age.reconcile()` and, per
  `evaluate()`'s rule that an already-reported ongoing finding only appears
  in `ongoing_context` (which alone never triggers a send —
  `Decision.should_send` is `bool(report_new or review_due or resolved)`),
  **does not re-alert**. This happened unprompted in first-draft testing: a
  three-task rate-limit burst produced exactly one Telegram send, confirming
  the burst-suppression property that the task's Test 3 concern (`"this
  project has a documented history of alerts nobody reads"`) is specifically
  about.
- The register (`orchestrator/accepted_failures.json`, new, read-only from
  this module's side — nothing here ever writes to it) is available for
  Oscar to explicitly accept a `failure_kind` for a bounded window, exactly
  as it works for `check_canonical_definitions.py` today.
- **Known, accepted limitation:** because there's no periodic re-check, a
  `"resolved"` message (failure_age's other alert type) will never fire for
  this consumer — once a `failure_kind` has been reported, later successful
  runs never call this code path at all (only failures do), so there's
  nothing to observe the key's disappearance. For a one-off event this isn't
  a real loss (there's no "still-failing condition" to announce the end of),
  but it's worth naming as a place this integration is not a full-fidelity
  use of the module.

State and the register are kept **local to trading-swarm**
(`brain/spawn_agent_failure_state.json`, `orchestrator/accepted_failures.json`)
rather than sharing first-repo's copies. These are two operationally
distinct systems — agent-orchestration failures vs. first-repo DB-invariant
violations — and merging their review queues would make "not everything that
fires is worth reading" harder to reason about for both, not easier.
`monitoring/failure_age.py` itself is imported unmodified, exactly as its own
docstring invites ("stdlib only... any consumer can import this safely").

Delivery uses a small dependency-free Telegram sender reusing the existing
`TELEGRAM_AGENTS_TOKEN` / `TELEGRAM_CHAT_ID` pair `orchestrator.py`'s own
`send_telegram(bot="agents")` already uses for per-agent notices — **not**
by importing `orchestrator.send_telegram` itself, because that function
returns `None` unconditionally and `failure_age.mark_reported`'s contract
requires calling it only after a *confirmed* send. The new sender returns a
real boolean from the HTTP call.

**Residual coupling risk, named rather than hidden:** `agent_failure_notifier.py`
imports `monitoring.failure_age` from first-repo, which — because
`monitoring/__init__.py` eagerly imports `Database`, `PolymarketClient`, and
`TraderAnalyzer` — pulls in more of first-repo than `failure_age.py` alone
needs. If that import ever breaks (a missing dependency, a first-repo
refactor), the notifier's own `except Exception` in `spawn_agent.sh`'s
cleanup call logs the failure to `$LOG_FILE` but — being unable to write the
registry or send an alert — reproduces a milder version of the exact bug
this doc fixes. This is a real, understood trade-off of reusing the module
across repos rather than duplicating it (the same trade-off `json_safety.py`
explicitly declined to make for itself, keeping hand-synced sibling copies
instead — see that file's own docstring). Not fixed here; flagged for
whoever next touches this file.

---

## Part 3 — verification (demonstrated, not asserted)

23 tests added to `tests/test_agent_failure_notifier.py`. This repo has no
`run_tests.py` — that name belongs to first-repo's custom, non-pytest
subprocess-based runner (`run_tests.py`'s own docstring: "Discovers all
tests/test_*.py files, runs each as a subprocess..."). trading-swarm's own
existing tests are ordinary pytest files, and every one of them documents
its own invocation in its header as `python3 -m pytest tests/test_X.py -v` —
**not** bare `pytest`. That distinction turned out to matter: the checked-in
`ci/run_tests.sh` wrapper invokes bare `pytest "$TESTS_DIR"` (absolute path,
no `-m`), and bare `pytest` does not add the repo root to `sys.path` the way
`python3 -m pytest` does. Confirmed this is a **pre-existing** bug, unrelated
to this change: `test_json_safety.py`, `test_brain_writers_atomicity.py`, and
`test_cross_repo_lock.py` — none of them touched here — fail the exact same
`ModuleNotFoundError: No module named 'orchestrator'` under `ci/run_tests.sh`
today. Not fixed here (out of scope: this task is about `spawn_agent.sh`
failure detection, not CI plumbing) but flagged for the record.

Ran via the method this repo's own tests document and that actually works:

```
$ cd /home/parison/trading-swarm && python3 -m pytest tests/ -v
...
======================= 147 passed, 28 warnings in 5.83s =======================
```

All 147 pass — the pre-existing 124 plus the 23 new ones. The 28 warnings are
pre-existing `datetime.utcnow()` deprecation notices in `orchestrator.py`,
unrelated to this change.

### The four required demonstrations

Run against a real `handle_agent_run()` call, a throwaway registry/state/
register (never production files), and a fake (non-network) Telegram sender
that records what it would have sent:

**(1) Simulated session-limit response** — `claude_exit=1`, output = the
exact 2026-09-19 13:24 message:

```
outcome classified as: 'rate_limited'
registry: status='attention_required' failure_kind='rate_limited' exit=1
alert sent: True
```

Telegram body that would have gone out:
```
spawn_agent.sh — agent run needs attention — 2026-09-20

tracking (age unknown)  rate_limited — counting from 2026-09-20

state: .../state.json

task: demo-1
agent: quant-research
exit code: 1
log: .../demo-1.log
demo task
```

**(2) Simulated clean run, empty output** — `claude_exit=0`, output = `""`:

```
outcome classified as: 'empty_output'
registry: status='attention_required' failure_kind='empty_output' exit=0
alert sent: True
```

**(3) Simulated GENUINE successful run — the one that matters most** —
`claude_exit=0`, output = real multi-line task output:

```
outcome classified as: 'completed'
registry: REMOVED from active_tasks (registry empty)
alert sent: False
```

Still recorded as completed, exactly as before. **No Telegram message was
sent.** A fix that flags everything is as useless as one that flags nothing
— this is the check that proves it doesn't.

**(4) The other Part-1 failure modes** — network failure, auth expiry, model
unavailable, each `claude_exit=1` with its own distinct error text, each
checked against a fresh state file (isolating "is this kind caught" from the
burst-suppression property already covered by
`test_repeat_of_same_failure_kind_does_not_alert_again`):

```
[network]  outcome: 'cli_error'  registry: attention_required  alert sent: True
[auth]     outcome: 'cli_error'  registry: attention_required  alert sent: True
[model]    outcome: 'cli_error'  registry: attention_required  alert sent: True
```

All four demonstrations passed. Full transcript (including the unmodified
first run, which incidentally proved burst suppression by producing only one
alert across a 3-task rate-limit sequence before the fix above isolated each
case) is reproducible from `tests/test_agent_failure_notifier.py`, which
formalizes all four plus the burst-suppression and send-failure-retry cases
as permanent regression tests.

---

## Part 4 — what this does not fix

Explicit, per the task's instruction:

- **This makes a failed agent run visible. It does not re-enable any agent.**
  The seven paused Claude-backed jobs — verified against the live crontab —
  **stay paused**: two paused 2026-07-15 for the token-bleed audit
  (`research-scout`, `integration-test-agent`) and five paused 2026-08-31 for
  the Claude-credit shutdown (`code-hygiene-agent`, `training-librarian-agent`,
  `performance-analyst-agent`, `signal-agent`, `trader-intelligence-agent`).
  Nothing in this change touches crontab, the orchestrator's scheduling, or
  any pause flag.
- **It does not retry.** A task marked `attention_required` sits there; no
  code path re-spawns it, and `MAX_RETRIES`/auto-respawn logic in
  `orchestrator.py` is untouched and does not apply to this status (it only
  ever looks at `status == "running"`).
- **It does not resume.** No partial output is salvaged or continued from.
- **It does not change tier routing, model selection, or any agent's
  prompt/template.** `orchestrator/task_templates/*.md`,
  `brain/model-routing.md`, and every `MODEL_CMD`/tier case in
  `spawn_agent.sh` are byte-identical to before this change except for the
  `${PIPESTATUS[0]}` capture and the extra cleanup argument.
- **It does not fix the timeout/hung-session gap** named in the Part 1
  inventory (a `spawn_agent.sh` run that never returns is a different,
  slower-to-manifest problem than the one this task named).
- **It does not fix `ci/run_tests.sh`'s pre-existing bare-`pytest` /
  `orchestrator` import bug**, found incidentally while verifying this fix.

## Note on the auto-push hook

`~/trading-swarm/.git/hooks/post-commit` fires automatically on any commit
touching `brain/decisions/`, per its own comment ("Installed 2026-09-19 at
Oscar's request"). This document lives in `brain/decisions/`, so committing
it pushed `master` to `origin` automatically, as expected — not worked
around, per instruction.
