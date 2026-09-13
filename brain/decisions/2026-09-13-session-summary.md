# Session Summary — 2026-09-13 (Server Setup 18)

Documentation only. Every commit hash and figure below was checked against
its source this session. first-repo `main`, trading-swarm `master`.

**One discrepancy flagged up front, per instruction not to reconcile
silently:** this summary's source brief referred to "Thursday's killed
run." The killed run was 2026-09-12, which is a **Saturday**
(`date -d "2026-09-12" +%A`), not a Thursday. The date and the underlying
facts about that run (see below) are otherwise unaffected — the summary
below uses the correct day.

---

## HEADLINE — the box held overnight, an observer bug was found and half-fixed, and a documentation sweep found the project's own map of itself was wrong in sixteen places

**The wall-socket move held for one clean night** — the first data
point, not proof. **Today's Sunday maintenance run completed in ~8
hours, the fastest of four Sunday runs on record, with no sign of
catching up** from Saturday's power-loss-killed run. The day's work
then moved through five committed pieces, each building on the last:
diagnosing a recurring observer fault (four symptoms, one mechanism),
fixing the memory-leak half of it (the burst-loop half remains live),
sweeping the whole codebase for the same "built, never connected"
pattern that produced it (24 known instances now, verdict: systemic),
correcting `CLAUDE.md` — the document that governs every session — where
that sweep found it wrong (16 claims, not the 4 expected), auditing
`daily_maintenance.py` end to end for the first time (the Saturday crash
left nothing inconsistent; a live pagination bug was doing daily,
silent damage instead), and fixing that pagination bug with a
quantified before/after. **The single most consequential correction
cuts against the day's own instinct to distrust the documentation**:
`CLAUDE.md` said a research input was disabled and neutral; it was not,
and the record now says so.

---

## INFRASTRUCTURE STATE

**The box stayed up cleanly overnight — one clean night, first evidence
consistent with the wall-socket fix, not conclusive on its own.** Boot
record: a single boot since the 2026-09-12 13:07 recovery, still running
through today's work.

**Today's Sunday maintenance run: 06:00:01 → 13:59:23, ~7h59m.**
Confirmed against `logs/daily_maintenance.log` in an earlier task today
and re-confirmed in the `daily_maintenance.py` audit (trading-swarm
`8a597b2`): this is the **fastest of four Sunday runs on record**
(prior three: ~9.16h, ~12.3h, ~10.75h). **No catch-up burden** from the
Saturday (2026-09-12) run that was killed mid-step by the power loss —
the audit traced this precisely (see below): the crashed step's own
idempotent design meant Sunday's run did not need to do, and did not
do, any extra work to compensate.

---

## THE OBSERVER: A RECURRING FAULT, DIAGNOSED, HALF-FIXED

**What was previously read as a one-off turned out to be recurring.**
The burst-flush anomaly in `polymarket-observer`'s health-check counter
— seen once before the 09-12 crash and read then as a possible
precursor, not diagnosed — was found this session to be an ongoing
pattern: **21 distinct burst events** across the post-reboot window (not
94, correcting an earlier same-day miscount that conflated intra-burst
microsecond timestamps with distinct events), with **1,122
`generic_error` lines** clustered at the same timestamps as those
bursts.

**Diagnosis (trading-swarm `db82c9b`): all four symptoms — the bursts,
the errors, the memory growth, and the recurring SIGTERM hangs on
shutdown — trace to one mechanism, plus one separate, compounding bug.**

- The errors are real: `database is locked` contention hitting
  `pnl_worker` and `monitoring.monitor`, confirmed against
  `logs/monitoring.log` directly — retried and skipped by design, not
  lost.
- The burst is a genuine runaway, not a logging/buffering artifact:
  `HealthChecker.check_all()` makes roughly 11 synchronous
  `sqlite3.connect(timeout=30.0)` calls from inside `async def`
  coroutines, with no thread-executor offload. One lock wait can block
  the entire single-threaded asyncio event loop for up to 30 real
  seconds; every `asyncio.sleep(60)` timer that was due during that
  block then fires in a pile-up the instant the loop frees up. The
  burst rate roughly quadrupled during the day's 3h40m
  leaderboard-discovery maintenance step, consistent with heavier DB
  write contention during that window.
- The same mechanism plausibly explains the SIGTERM hangs (recorded on
  2026-09-07 and again just before the 09-12 crash, never previously
  diagnosed): the registered signal handler is a trivial, non-blocking
  flag flip, but it cannot run while the interpreter is inside a
  blocking C-level call, and systemd's `TimeoutStopSec=30` sits right on
  top of SQLite's own 30-second busy timeout — a race the handler can
  lose. **Plausible, not proven** — no hang occurred live during this
  session to confirm it directly.
- **The memory growth is a separate, independent bug that the burst
  feeds, not the same bug**: `ErrorParser.error_history` and
  `error_groups` grow unbounded — every detected error is retained for
  the process's lifetime. `clear_old_errors()` exists, is correctly
  implemented, and is called from nowhere in the codebase.

**Fix committed (first-repo `eabc323`; trading-swarm `f5c2bab`
documents it): one call to `clear_old_errors()`, added to the 60-second
health-check loop, deliberately not the 2-second log-monitor loop** (the
latter would rebuild the same structures needlessly often for a 24-hour
retention window). Tests include a genuine non-tautology
demonstration — the same `ErrorParser` instance shown growing to 500
entries without the call, then dropping to zero with it, on the same
object. **The fix is inert until the observer restarts, which was not
done this session.**

**A second unbounded accumulator was found during verification and left
unfixed, by explicit direction**: `TelegramHealthBot.last_alert_time`,
keyed on an unbounded space of error signatures, with no eviction path
at all (not merely uncalled — no method exists to call). Reported in
both the diagnosis and fix documents; scoped out of the fix itself.

**Stated expectation for after a restart, so there is something to check
against**: RSS should plateau within roughly a 24-hour window's worth of
accumulated errors rather than continuing to track process uptime (the
pre-fix pattern: 11.6 GB after ~2h16m of uptime on 2026-09-07, versus
168-250 MB fresh). Still climbing linearly over multiple days after a
restart would mean either the fix isn't reaching the live instance, or
`last_alert_time` matters more to the total than expected.

---

## THE BUILT-NEVER-CONNECTED SWEEP — THE DAY'S LARGEST FINDING

**Verdict: systemic, not coincidental** (trading-swarm `c45fb45`).
Starting from six named instances (three already known from an earlier
inventory pass, three found earlier the same day), a bounded sweep —
explicitly not covering `scripts/` at function granularity, the
project's largest single code surface — found **14 new instances**,
for **24 distinct disconnections now on record**, found through three
unrelated search strategies (accidental discovery, a systematic
zero-caller sweep of under half the codebase, and a step-by-step
consumer check of one pipeline).

**Shape distribution**: 2 written-never-read, 1 read-never-written, 15
built-with-a-lost-caller, 6 guards-that-cannot-fire.

**The named mechanism, not merely observed but confirmed by four
independent recurrences**: when this codebase redesigns or rewrites a
capability, the old implementation gets routed around rather than
deleted, and nothing structural — no lint rule, no caller-count test, no
dead-code check — ever catches the orphan. Four unrelated parts of the
codebase show exactly this story: a composite trader-skill scorer
superseded by an inline reimplementation elsewhere; a trader-statistics
"comprehensive" replacement that was written and never wired in while
the old path stayed live; an entire Telegram interactive-bot family
orphaned by a January 2026 send-only redesign; and an AI-monitoring
capability orphaned when one monitoring entrypoint superseded another.

**Shape 4 (guards that cannot fire) is smaller — 6 of 24 — but more
dangerous per instance**, driven by a different mechanism: a
human-facing reference (a docstring's claim, a health-check's label,
`CLAUDE.md`'s own text) points at something that stopped being true, and
nothing automated ever re-verifies it.

**The biggest single finding**: `CLAUDE.md`'s own claim that the system
"runs AI-powered health monitoring via Mistral/Ollama" has **no live
implementation anywhere**, across two independent dead attempts —
`monitoring/ai_analyzer.py`'s `AIAnalyzer` (zero callers found anywhere)
and a second, separate Ollama/Mistral integration inside
`monitoring/main.py` (dead because `main.py` itself is not the live
monitoring entrypoint — see below).

No active data loss and no guard found to have already failed against
something that actually happened.

---

## THE CLAUDE.MD CORRECTION

Following directly from the sweep: **16 claims addressed in total (15
corrected as factually wrong, 1 relabeled as dormant intent) — not the
4 the task named going in** (first-repo `7513b04`; trading-swarm
`76372a1` documents it).

**The most consequential corrections**:
- `monitoring/main.py` was named as the live monitor orchestrator; it
  is not — `scripts/start_monitoring.py` imports
  `monitoring.main_telegram_safe`, confirmed by direct read.
  `monitoring/main.py` is referenced by exactly one file in either
  repo, an archived test.
- `monitoring/telegram_bot.py` was named as the send-only Telegram
  path; its only class, `TelegramNotifier`, is the dead old
  interactive/polling bot from before the January 2026 redesign. The
  actual live send-only class, `TelegramHealthBot`, lives in
  `monitoring/telegram_health_bot.py`.
- Every documented row count was stale by 2-9x: traders 87,063+ (actual
  198,699), markets 220K+ (actual 878,646), positions 1,064K+ (actual
  9,661,891). Documented DB size ~1.6 GB (April 2026) against an actual
  **~21 GB** today.

**One correction cuts the other way, and matters for the research
thread, not just for hygiene.** `CLAUDE.md` stated: "Timing quality is
intentionally disabled — the `created_at` column doesn't exist in the
markets table; all traders receive a neutral timing score." A direct
query today (`SELECT timing_score, COUNT(*) FROM traders GROUP BY
timing_score`) shows **34,906 distinct values across 44,652 traders**
with a score — only **8,670** sit at the neutral 0.5. The computation
was reworked at some point to route around the missing column using
existing trade data instead, and produces real, varied output today.
`timing_score` is Component 3 of the canonical skill metric design, and
"relative earliness" is directly relevant to the execution-timing
question that sits at the top of yesterday's heatmap shortlist
(2026-09-12 session summary, item 1). **Anyone who read the
documentation instead of querying the data would have concluded this
research input did not exist.**

**Oscar's direction, which governed the fix and is recorded here because
it shaped what was and wasn't touched**: the local-LLM and agentic
elements are dormant intent, not dead weight. The server's original
purpose was local agents running research and coding work through the
day; that is still wanted, planned for a dedicated session, and expected
to live mainly in trading-swarm. **Nothing relating to it was deleted,
deprecated, or marked abandoned** — three places in `CLAUDE.md` (the
opening description, the Services table, the architecture diagram) now
carry a `[DORMANT INTENT]` marker with pointers to both existing (dead)
implementations, so a future session can pick the work up rather than
rediscover it.

---

## THE DAILY_MAINTENANCE AUDIT — FIRST WHOLE-PIPELINE REVIEW

(trading-swarm `8a597b2`.)

**The 2026-09-12 (Saturday) crash left nothing inconsistent — established
directly, not assumed.** It died inside step 12,
`backfill_transaction_hashes.py` (Pool C tier), at trader `[3527/4482]`.
That step commits per row, immediately, and gates its match on
`transaction_hash IS NULL` — every row committed before the crash stayed
correctly persisted, and the ~955 traders never reached were simply
reprocessed the next day along with everyone else, since the step
re-fetches its full trader list from scratch on every run regardless of
the prior day's outcome. **The recovery came entirely from idempotency,
not from any resume mechanism — there is none, confirmed by reading
`daily_maintenance.py`'s `main()` directly, not inferred from behavior.**
No document anywhere states a process-level resume was ever a design
intent.

**No overlap has ever occurred.** A strict state-machine pass over the
full log — **87 "Starting" and 87 "Finished" markers, perfectly
paired**, across 106 days of continuous history — found zero cases of a
new run starting before the previous one's completion marker. A raw
substring count found 93 "Starting" occurrences, not 87; the extra 6 are
a buffering/log-ordering artifact (a prior day's per-trader progress
line glued onto the next day's "Starting" line with no intervening
newline), not real overlaps. **The flock guard named in
`MASTER_HANDOVER_2026-09-05` as the highest-priority target remains
absent, confirmed still true today** — and remains worth having as a
precaution given the box's own history (the backup wrapper's flock guard
exists specifically because of a real 2026-08-25/26 stuck-run incident),
not because of any observed live problem here.

**The earlier characterization of the logging gap was wrong, and this
audit corrects it.** Two separate points in this session's own earlier
work stated that `daily_maintenance.py`'s step runner captures and
discards each step's stdout. Reading `run_step()` directly shows it does
not — `subprocess.run()` is called with no `capture_output` argument at
all, so each child's stdout is inherited, not discarded. What actually
happens: the parent's own `print()` calls are block-buffered and
long-lived, while each short-lived child flushes its own, much smaller
buffer at its own process exit — so a step's genuine output can land
**physically earlier in the log file than the header that logically
precedes it**. Confirmed concretely, not just theorized: today's step 22
output (`"Fetching pending trades..."` / `"Found 51 pending trades to
evaluate."`) exists in the log **~1,900 lines before** the
`"--- Step: Evaluate geo/elec pending results ---"` header it belongs
to. Nothing is lost; the log is simply unreliable for a human scanning
top-to-bottom.

---

## THE PAGINATION FIX — THE DAY'S MOST CONCRETE RESULT

(first-repo `2815ce9`; trading-swarm `e2753a9` documents it.)

**Quantified**: `backfill_market_categories.py` paginated with SQL
`OFFSET` over `WHERE category='Unknown'` — a result set that shrinks
every time a row gets classified within a run — while its checkpoint
advanced by the raw batch size fetched, not by how many rows actually
left the set. **20,564 of 30,315 keyword-matching Unknown markets —
67.8% of the addressable backlog — were already permanently
unreachable**, on ordinary successful runs, not only after crashes.
Worse on failure paths: an Ollama-call or commit failure advanced the
offset by the full batch size while zero rows left the set, guaranteeing
those rows were skipped with no classification attempt ever made.

**Fixed with keyset pagination on `market_id`** (the table's stable
`TEXT PRIMARY KEY`, confirmed to be a content-hash string, not
sequential). **Recorded for the record: chat-Claude's own suggested
approach — "always take the first N rows, no offset at all" — was
considered and rejected**, not adopted at face value: with a
content-hash key and a ~40% historical skip rate, that approach could
converge to endlessly re-evaluating the same permanently-Unknown rows
sitting at low hash values and never reach the rest of the backlog.
**One addition beyond what either party specified**: a wraparound that
resets the cursor to the beginning once it exhausts the current matching
set, since a newly created market can sort to any hash position,
including behind wherever the cursor currently sits — closing a gap
pure forward-only pagination would otherwise carry indefinitely.

**Verified with a live `--limit 20` run against production** (the one
directed exception to this run of tasks' otherwise read-only default):
10 markets classified, 10 correctly skipped, and all 20 confirmed drawn
from the previously-unreachable range by matching the new cursor
position against a list of the first 30 keyword-matching market IDs
captured before the run.

**The honest effect, stated without softening**: throughput is
unchanged — `daily_maintenance.py`'s `--limit 50` for this step was not
touched, and this fix was never going to make the step faster, only
correct about which rows it reaches. Clearing the current snapshot of
the addressable (keyword-matching) subset at that rate is **~606 days**
— large, but now genuinely finite rather than partly permanent, which is
the entire gain. The **30,305** keyword-matching rows remaining are
themselves a small subset of **864,515** unfiltered `category='Unknown'`
markets database-wide; this script was never able to touch the larger
number and still cannot.

---

## OPEN THREADS CARRIED FORWARD

- **The observer restart** — required to make today's pruning fix live;
  not done this session. Its last four restarts each hung on SIGTERM and
  needed a SIGKILL.
- **The blocking `sqlite3.connect(timeout=30.0)` calls inside async
  coroutines** — the last live fault from today's diagnosis, undiagnosed
  only in the sense that the remedy is unchosen, not in the sense that
  the mechanism is unclear.
- **`TelegramHealthBot.last_alert_time`** — no eviction path, found and
  left unfixed by explicit direction.
- **The arrival rate of new keyword-matching `Unknown` markets** —
  unmeasured, so whether the category backlog shrinks net of new
  arrivals, or merely stops permanently stranding rows, is not known.
- **The relevance-classifier §3.10 adjudication and blind spot-check** —
  outstanding since the 2026-09-03 gate result; **ten days**, the oldest
  open item carried into today.
- **Telegram token rotation** — still undecided, sequence recorded in
  the 2026-09-12 session summary, not executed.
- **The 195,625-of-214,413 stranded-markets remediation**
  (`mark_market_resolved()` never setting `last_checked`) — measurable,
  undecided.
- **24 known disconnections** — deletion deferred until a path forward
  is chosen; this sweep characterized, it did not remediate.
- **The methodology-extraction pass** (reading Mitts & Ofir's and
  Gómez-Cram's actual methods rather than their reported findings) —
  named in this task's brief as deferred from earlier today and still
  the intended next research step. **Flagged, not silently affirmed**:
  no commit in either repository before this session's own first commit
  today (14:57 UTC) documents this pass or its deferral; it is recorded
  here as stated, not independently verified against a committed source.
- **`scripts/` at function granularity** — the largest surface the
  built-never-connected sweep did not cover; the most likely place a
  future pass finds more of the same pattern.

---

## What this document does NOT do

No verdict on what to do next. The built-never-connected verdict
(systemic) and the pagination quantification (67.8% of the addressable
backlog permanently unreachable) are stated above exactly as their
source documents state them, not softened for this summary.
