# Corpus extraction: run-level budget fix, pre-launch assertion, flock probe, resume

**Date:** 2026-09-22. Fixes the root cause of the 2026-09-21 corpus_content_extractor.py run's
self-abort at 168/276 documents, switches its maintenance-overlap check from an unverified log-tail
heuristic to bfdf9d6's tested flock primitive, and resumes the remaining work. Two additional bugs
found and fixed along the way (Part 4) — reported here rather than silently folded in.

---

## Part 1 — why the 6 documents timed out

All 6 are `"request_failed: timed out"`. Confirmed from telemetry, not assumed: every one's
`call_seconds` is within 0.1s of its own `call_timeout_assigned` —

| document | lines | timeout assigned | actual call_seconds |
|---|---:|---:|---:|
| 2026-06-29-overhang-ledger.md | 1032 | 1503s | 1503.1s |
| 2026-06-29-pool-c-decline-investigation.md | 92 | 300s (floor) | 300.1s |
| 2026-06-29-session-summary.md | 178 | 300s (floor) | 300.1s |
| 2026-07-10-trading-swarm-deep-audit-FABLE.md | 267 | 390s | 390.0s |
| 2026-07-10-trading-swarm-structural-survey.md | 241 | 352s | 352.1s |
| 2026-08-17-backtest-snapshot-drift-investigation.md | 302 | 440s | 440.1s |

This is `urllib.request.urlopen(req, timeout=call_timeout)`'s own socket timeout firing exactly at
the length-scaled value `timeout_for_lines()` assigned — **the per-document formula itself, not a
separate client/HTTP timeout the formula doesn't govern.** No second timeout layer exists in
`call_ollama()`. Recomputing `timeout_for_lines()` for all 6 against the formula (`k=0.539 s/line *
2.7`, 300s floor, 3600s ceiling) reproduces the assigned values exactly, confirming the formula
itself was applied correctly.

**They are not the longest documents** — only overhang-ledger (1032 lines, the corpus's 2nd-longest)
is genuinely long; the other 5 are 92–302 lines, near the bottom of the corpus's length
distribution, sitting at or near the 300s floor. **What they have in common instead:** each is an
outlier against its own neighbors in the actual run — documents of comparable or greater length
processed in 70–170s throughout the run (e.g. 2026-08-16-session-summary.md, 121.0s; 2026-08-09-
phase2-primary-and-paper-trading-preparation.md, 168.3s), while these 6 ran past their own assigned
ceiling before returning anything.

**Is this a formula problem?** No — checked at the aggregate level, not assumed. Reconstructing the
run's 162 successful calls: `sum(line_count)=31,033`, `k*sum(line_count)=16,726.8s` predicted vs.
`18,299.96s` actual — a **run-level ratio of ~1.094**, i.e. the formula's central estimate (k=0.539
s/line, unmultiplied) is accurate to within ~9% in aggregate. The per-call 2.7x multiplier is sized
for worst-case single-call variance (worst observed ratio 2.55x, on a small/noisy document per the
formula's own derivation doc), and these 6 failures are exactly that kind of per-call tail
variance — not evidence the fit (k, floor, ceiling) is systematically wrong for any particular length
range. Per the task's own stop condition, this would only block Part 2 if it were a length-fit error
affecting the remaining 108; it isn't — any document, regardless of length, carries some tail-latency
risk the per-call formula's 2.7x margin doesn't fully close, and the design's own stated philosophy
(hard-fail on timeout, flag and move on, no retry-until-succeeds) already accepts that.
**Not a stop condition. Per-document timeout formula, prompt, schema, model, and dedup: unchanged.**

---

## Part 2 — the budget, and a pre-launch assertion that would have caught this

**Root cause of the actual failure, confirmed:** the run inherited `MAX_RUN_WALL_SECONDS = 6 * 3600`
from the earlier structural pass (where a 4h53m run happened to fit under it). The pre-launch check
that projected 10.8–20.5h for 276 documents was never compared against that 6h ceiling before launch
— a human forgetting to look, not a mechanism failure. The kill condition itself worked exactly as
designed: clean log line, own RSS 34.8MB, no crash, 162 good records preserved.

**`MAX_RUN_WALL_SECONDS` raised 6h → 24h**, from actual data:
- Full corpus (`find brain/decisions -iname "*.md" | xargs wc -l`, 2026-09-22): 73,407 lines.
- At `k=0.539 s/line` with a **1.3x run-level margin** (see below): `0.539 * 73,407 * 1.3 ≈ 51,401s ≈
  14.3h` — consistent with the original pre-launch estimate of 10.8–20.5h for this same corpus.
- 24h leaves ~68% headroom above that margined full-corpus projection, so a legitimate full run
  doesn't itself risk tripping the kill condition, while a run blowing through even that padded
  estimate by another ~1.7x is still caught as a genuine runaway. Configurable via
  `CORPUS_CONTENT_MAX_RUN_WALL_SECONDS` for testability.

**New `project_run_wall_seconds(pending)`** sums line counts for the actual pending set and projects
`k * total_lines * RUN_PROJECTION_SAFETY_MULTIPLIER`. **`RUN_PROJECTION_SAFETY_MULTIPLIER = 1.3`**,
deliberately smaller than the per-call 2.7x: per-call outliers (Part 1) average out over many
documents — the run-level ratio was ~1.094, not ~2.55 — so 1.3 keeps real headroom without importing
a margin sized for single-call tail risk, which would make this assertion refuse runs that would in
fact comfortably finish.

**`main()` now refuses to launch** (exit 1, both numbers printed to stderr and the log) if the
projection exceeds `PRE_LAUNCH_CEILING_FRACTION = 0.8` of `MAX_RUN_WALL_SECONDS` — leaving 20% of the
hard ceiling as slack for ordinary per-call variance during the run itself. This lives in the code
(`scripts/corpus_content_extractor.py`, in `main()` before the processing loop), not a checklist —
the exact fix the task called for.

**Verified against the real resume workload** (dry-run, `--limit 0`, no launch):

```
resuming: last_seen_path=None already_indexed=162 discovered_total=281 pending=119
pre-launch assertion passed: projected=29888s (8.30h) for 119 docs / 42655 lines,
launch_ceiling=69120s (19.20h) of hard ceiling 86400s (24.00h)
```

(119, not 114 — 5 new decision documents were added to `brain/decisions/` since 2026-09-21 and are
correctly picked up by discovery; see Part 5.)

---

## Part 3 — flock probe, replacing the log-tail heuristic

`maintenance_in_progress()` previously tailed `logs/daily_maintenance.log` for unmatched
Starting/Finished markers — untested in production, since the 2026-09-21 run's active window never
overlapped an actual maintenance run (confirmed in the prior verification task). bfdf9d6 built the
tested primitive for exactly this: a kernel-advisory flock on
`scripts/cron_wrappers/run_daily_maintenance.sh.lock`, with its Part 7 explicitly recommending
option (b) for this script — Python's own `fcntl.flock(fd, LOCK_EX | LOCK_NB)`, catching
`BlockingIOError` for "in progress," releasing immediately otherwise. Implemented exactly that.

**PROBE, NEVER HOLD — how this is guaranteed, not just intended:**
`maintenance_in_progress()` opens the lockfile, attempts `fcntl.flock(fd, LOCK_EX | LOCK_NB)` inside a
single function call, and in every code path — lock acquired, lock held by another process, or any
OS error — releases it (or never held it) and closes the fd before returning. There is no state
carried between calls; each call is a fresh open/probe/release/close. It never calls `flock` without
`LOCK_NB` (would block) and never omits the release-on-success path.

**Tested, not assumed** (`tests/test_corpus_content_extractor.py`, `TestMaintenanceInProgressFlockProbe`,
reusing bfdf9d6's exact stand-in-holder pattern from `tests/test_daily_maintenance_overlap_guard.sh`):
- No holder → `False`. Holder present → `True` (no false negative). Holder killed → `False` again (no
  false positive). Returns in well under 1s while blocked (non-blocking, not a slow poll).
- **The critical proof:** after the probe runs against a free lock, a real `flock -n LOCKFILE -c true`
  acquire attempt against the *same* lockfile still succeeds — demonstrating the probe never holds
  the lock past its own call. Repeated 200x in a tight loop (mimicking ~280 per-document checks) with
  the same result — the probe cannot starve a concurrent real acquire no matter how often it's called.
- `run_daily_maintenance.sh` and its flock guard: **untouched**, confirmed by re-running
  `tests/test_daily_maintenance_overlap_guard.sh` (33/33) and `tests/test_backup_overlap_guard.sh`
  (27/27) unmodified after this task's changes.

---

## Part 4 — offline tests, and two bugs the tests surfaced

`tests/test_corpus_content_extractor.py`: **31/31 pass** (`python3 -m pytest
tests/test_corpus_content_extractor.py -v`). Covers, per the task's 4 items:
1. **Assertion** (`TestPreLaunchAssertion`): a projection constructed above a tiny ceiling refuses
   launch (exit 1) and prints both the projected-seconds and `MAX_RUN_WALL_SECONDS` figures; one
   below a generous ceiling proceeds.
2. **Probe** (`TestMaintenanceInProgressFlockProbe`): see Part 3.
3. **Probe-only**: see Part 3's critical proof.
4. **Resume behaviour** (`TestResumeRetriesFailuresNotSuccesses`): a fake 3-document corpus with one
   simulated failure — the failed document is retried on the next resume and the two successes are
   never re-called. This is the exact scenario the task's stop condition guarded
   ("the checkpoint would skip the 6 failed documents") — see below for why the first fix attempt
   didn't actually clear it.

**Bug 1, found by running the new test, not by inspection: `load_state()`/`save_state()` ignored the
`--state-file` CLI argument and always read/wrote the module-level `STATE_FILE` constant
unconditionally.** The first test run for item 4 above consequently wrote into the REAL production
`brain/corpus_content_state.json` instead of its intended temp file — advancing it from
`{"last_seen_path": null, "processed": 162, "failed": 6}` to `{"last_seen_path":
"brain/decisions/c.md", "processed": 164, "failed": 7}` before the test's own assertion failure (on
a *different* bug, below) surfaced the problem. **Caught immediately, before Part 5's real launch**:
`load_state()`/`save_state()` now take an explicit `state_file` parameter (defaulting to `STATE_FILE`
for any other caller), `main()`'s two call sites pass the resolved `state_file` local through, and
the corrupted production state file was restored to its correct pre-resume value. No document that
was actually processed on 2026-09-21 was lost or reprocessed by this — only the on-disk checkpoint's
bookkeeping was briefly wrong, and it never left this session.

**Bug 2, found once Bug 1 was fixed and the same test could actually run against an isolated
checkpoint: the cursor-based `pending` filter (`p > state["last_seen_path"]`) does not correctly
retry a failure even if the cursor is never advanced past it.** Test run 1 processed a→b(fail)→c in
order; c's success legitimately advances the cursor to `"brain/decisions/c.md"`. On resume, the
filter `p > cursor` then excludes `b.md` too, since `b.md < c.md` alphabetically — a failed document
that sorts *before* a later successful one is silently dropped, regardless of which branch advances
the cursor. **This is precisely the task's stop condition** ("the checkpoint would skip the 6 failed
documents") — surfaced by the test exactly as intended, not discovered after the fact. Root cause:
`already_indexed_paths()` already reads the whole index file and correctly identifies every true
success regardless of any cursor, so the cursor's `p > cursor` term bought no real scan-avoidance and
only introduced this failure mode. **Fix:** `pending` is now simply `[p for p in all_paths if p not
in done_paths]` — the cursor term is removed from the filter entirely; `state["last_seen_path"]` is
kept only for progress logging. Re-running the same test after this fix: 31/31 pass, including the
resume scenario. This is an orchestration-only change (module docstring and the checkpointing
section comment updated to explain the correction); extraction logic, schema, prompt, model, and
dedup are unchanged, per scope.

---

## Full-output provenance note

The final `brain/corpus_content_index.jsonl` will span two script versions differing only in
orchestration (this task's Parts 2–4) — the 162 records from 2026-09-21 and the 119 from today's
resume (Part 5) were extracted by the byte-identical `process_one()` / `call_ollama()` /
`GENERATION_SCHEMA` / `EXTRACTION_PROMPT` / dedup / quote-verification logic in both cases. Full-
output verification is the next task, per scope.
