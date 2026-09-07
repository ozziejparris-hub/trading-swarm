# Session Summary — 2026-09-07 (Server Setup 13)

## THEME

Today was not thesis work. `MASTER_HANDOVER_2026-09-06.md` (`6c3ce36`)
remains the entry point for a new instance and is **not** superseded —
nothing today moved the directional-skill thesis, the execution
dimension, or any research question. This document records how the
system got into its current state, not where the thesis stands.

The whole session closed one gap: **the distance between a finding
existing and that finding reaching a person.** Four independent
instances of the same failure were found and fixed:

1. **An unreproducible defect figure with no committed script behind
   it.** The `last_checked`-stranding headline numbers (195,625/214,413
   markets, 8,077 open positions, 1,983 traders) came from two doc-only
   commits with no query, no script, no persisted membership.
2. **A guard detecting real violations for ~11 weeks whose alert never
   fired.** `check_canonical_definitions.py` exited 1 every day since
   `419d223` (2026-06-24, 75 days) with 7 genuine hardcoded-threshold
   violations — and never once reached Telegram, because it read
   credentials with bare `os.getenv` and cron does not export
   `.env_trading`'s unexported assignments to the Python child.
3. **A channel so noisy that nothing in it was read.** The observer
   sent ~160 hourly reports and 28 six-hourly diagnostic reports per
   week, most carrying nothing new, plus two chronic stale CRITICALs (a
   deliberately-deleted file, ~57 days; a structurally-impossible "ELO
   coverage: 290.3%").
4. **A chronically-red test that turned out not to be testing what
   everyone assumed.** `test_backtest_window_population.py`'s five
   failing assertions do not call `backtest_window_sql()` at all — they
   compare a frozen 2026-07-24 snapshot against a live legacy query kept
   only as a before/after foil.

Naming the fourth failure's anti-pattern did not prevent it from
recurring in new code the same session — see "What went wrong."

---

## THE ARC IN SEQUENCE

Each step: what it produced, and its commit(s). first-repo `main`,
trading-swarm `master`.

1. **Progression check.** Read-only session opener — checked system
   status and where the thesis stood, found no thesis movement, and
   surfaced the two chronic red items (canonical-drift check,
   backtest-population test) that became the day's work. No commit
   (information-gathering only, per session discipline); no standalone
   artifact.

2. **Stranded-markets figure reconciliation.** Verdict: the recorded
   8,077-position / 1,983-trader figure is **(c) unreproducible by
   construction** — the two 2026-08-30 source docs (`9041ab8`,
   `96be474`) are doc-only, with no committed query and no persisted
   ID list, and the "open position" / "affected trader" predicates are
   not stated anywhere. Shipped a committed, parameterised,
   self-checking replacement script; fresh measurement: 216,499
   clob-resolved markets, 196,764 stranded (90.9%), 8,831 open
   positions, **1,168** distinct affected traders, all backed by a
   persisted JSON artifact with full membership. The trader-count path
   594 → 1,983 → 1,168 (up, then down) was left **[U] undetermined** —
   no tested predicate variant reproduces 1,983, and no 2026-08-30
   membership snapshot exists to diff against, so a methodology
   difference and genuine churn cannot be distinguished; reported as
   such, not resolved into the more plausible story.
   (first-repo `52cfa39`, trading-swarm `434e5ec`.)

3. **Canonical enforcement — Part 1 diagnosis, STOP.** The task asked
   for a four-part build (canonical-call adherence check,
   decision-document reproducibility check, wiring). Part 1 diagnosed
   `check_canonical_definitions.py`'s chronic failure and found it is a
   **real canonical violation, not a stale rule** — 7 genuine hardcoded
   `geo_elo >= 2175` bypasses across 6 `trader_skill_metric_v2*.py`
   scripts plus `characterize_legendary_overlap_recompute.py:84`;
   `GEO_ELO_LEGENDARY = 2175.0` has not drifted, so the literals happen
   to agree with the constant — exactly the silent-drift risk the check
   exists to catch. The task's own stop condition ("Part 1 finds a real
   violation → that is a finding for Oscar before anything is built on
   top of it") triggered. Parts 2–4 not attempted. Also root-caused,
   as a distinct bug, the `load_dotenv()` gap that had kept the alert
   silent for 11 weeks. (trading-swarm `2b44cb2`.)

4. **Telegram alert audit.** Read-only inventory of every Telegram
   sender across both repos. No stop condition — every finding is
   either noise or a stale/deliberate condition, not a new live
   incident. Findings: `check_canonical_definitions.py` is the **only**
   sender with the missing-self-load gap (every other bare-`os.getenv`
   sender runs under systemd, whose `EnvironmentFile=` needs no
   `export`, or hand-rolls its own loader); the hourly report's gate
   (`metrics.get("status")`) checks a key `_collect_metrics()` never
   sets, so it can never suppress; the diagnostic report is
   ungated (28/week, exactly 168h ÷ 6h); the `integrate_behavioral_elo.py`
   CRITICAL has fired for ~57 days about a file deliberately deleted
   `2026-07-12` (`61adaf5`); "ELO coverage: 290.3%" is
   194,415 / 66,972 — an all-traders numerator (schema `DEFAULT 1500`)
   over a ≥30-trade denominator, structurally always > 100%.
   (trading-swarm `c3d8c6c`.)

5. **Telegram remediation — bug-only channel.** Implemented the audit's
   fixes: hourly gate key corrected and extracted to a testable static
   method; diagnostic report gated on `CRITICAL` **and** a
   numeric-normalised finding-set change, persisted to a flat state
   file; duplicate CRITICAL message removed; `load_dotenv()` added to
   `check_canonical_definitions.py` (matching `audit_invariants.py:1001`)
   plus a violation-signature change gate; the two stale CRITICALs
   retired (`integrate_behavioral_elo.py` existence check removed after
   verifying the other four entries still exist; ELO-coverage line
   removed from the message body); unconditional daily/weekly digests
   commented out (reversible, dated, ledgered). New
   `tests/test_telegram_alert_gating.py`. `polymarket-observer.service`
   **not restarted** — flagged as Oscar's call. (first-repo `51e3b74`,
   trading-swarm `1836cf1`.)

6. **Six canonical violations fixed.** Replaced the hardcoded
   `geo_elo >= 2175` SQL literal in the legendary-overlap diagnostic of
   `v2, v2b, v2c, v2d, v2e, v2f` with an f-string interpolating
   `cd.GEO_ELO_LEGENDARY` (`import monitoring.column_definitions as cd`
   added to each). Behaviour-preserving (option a): predicate stays on
   `geo_elo`, not the canonical `geo_elo_active` gate; only `2175 →
   2175.0`; verified against the live DB — both forms select the
   identical 89 addresses, zero symmetric difference. Reduced the check
   from 7 violations to 1. The 7th
   (`characterize_legendary_overlap_recompute.py:84`) was classified
   DORMANT and left for Oscar's call among three options (fix the
   literal / exempt in the checker / leave). (first-repo `f63dd5a`,
   trading-swarm `463ad75`.)

7. **Failure-age tracking + accepted-failures register.** New
   stdlib-only `monitoring/failure_age.py`: per-finding `first_seen` /
   `last_seen` in the state file, age computed from the timestamp not
   file mtime, survives restarts; robust to missing / corrupt /
   pre-age-schema state (reseeds with today's date +
   `age_unknown_at_first_seen`, never back-dates); a finding that
   disappears then returns gets a fresh `first_seen`. New
   `config/accepted_failures.json` — **seeded empty** — where a failing
   check *with* a current entry is EXPECTED (no alert, still tracked),
   *without* one is UNEXPECTED (alerts), *past* `review_by` re-alerts
   once per day as "review due". Never written by any code path. Wired
   into the two checks that already persisted state
   (`check_canonical_definitions.py` — this **replaced** `51e3b74`'s
   signature gate — and `system_observer.py`'s diagnostic report, whose
   `CRITICAL`-only gate and no-all-clear behaviour were preserved). New
   `tests/test_failure_age_tracking.py` (38 assertions). Not extended to
   any other check. (first-repo `f6a8b88`, trading-swarm `8091190`.)

8. **Register entry added.** One entry, Oscar's decision, recorded: the
   sole remaining canonical violation — finding key
   `canonical_definitions :: scripts/characterize_legendary_overlap_recompute.py ::
   Python comparison geo_elo_active >= 2175 — replace with cd.GEO_ELO_*
   constant` — accepted with `accepted_by: Oscar`, `accepted_on:
   2026-09-07`, `review_by: 2026-10-15`. The `finding_key` was read from
   `finding_keys()` directly rather than transcribed (a near-miss key
   silently fails to suppress), then verified to work:
   `check_canonical_definitions.py` now tracks the finding in the state
   file and produces no message. Exit code stays 1 by design; the
   daily-maintenance step is non-blocking, so that is a WARNING line, not
   a page. (first-repo `f882a86`.)

9. **Backtest-population test diagnosis.** Established that
   `test_backtest_window_population.py`'s five failing assertions (T2,
   T2b, T2c, T2d, T2f) **do not call `backtest_window_sql()`** — they
   compare the frozen snapshot `bt_pop_2025-11-01_v1` (4,712 rows, all
   `generated_at = 2026-07-24T18:54:00Z`, `sql_version = '1'`) against a
   live `resolution_date`-based query kept only as a before/after foil.
   Each of the four deltas explained individually on `backups/markets_*.db`
   evidence: the live `old` set grew +746 freeze→now, entirely additive
   (`left old: 0`). The `-2` (T2b 54→52) is a set difference
   contracting, **not a population shrinking** — two 2026 New Mexico
   Governor primary markets had a NULL `resolution_date` backfilled from
   `end_date` between 2026-07-24 and 2026-08-11, moving them from
   `snapshot − old` into `snapshot ∩ old`. A hidden +649 (in-window
   markets that resolved after the freeze) is why T2f's identity broke.
   Verdict: **the canonical function is correct and unchanged**
   (VERSION "1", no commit in a month, Section 6 self-test passes, frozen
   snapshot a clean subset of live output — 0 of 4,712 dropped);
   authoritative call **(a)**, the test's hardcoded expectations are
   stale. No STOP condition. (trading-swarm `00aeb93`.)

10. **Backtest-population test fix.** Implemented Part 4 of the
    diagnosis as approved. Removed T2 / T2b / T2c / T2d and their
    constants (`SNAPSHOT_AGREE_WITH_OLD = 4658`,
    `SNAPSHOT_FALSE_NEGATIVES = 54`, `SNAPSHOT_ZERO_TRADE = 555`,
    `SNAPSHOT_FALSE_POSITIVES = 573`) and T2f — every one an equality
    against a `frozen ⊕ live` composite that drifts by construction;
    **not re-baselined** (that only postpones an identical failure,
    which `cfbc1cd` already did once). Two comments left at the removal
    sites recording why and citing the diagnosis. Added T1c —
    `snapshot ⊆ canonical_live`, naming the dropped `market_id`s on
    failure — demonstrated non-tautological against an in-memory DB
    across three drop mechanisms (re-categorised, `trade_gap_flag`, no
    trades) before being trusted. T4/T5 verified byte-identical to HEAD.
    Assertion count 24 → 20; the file passes 20/20. (first-repo
    `f415faa`.)

---

## DECISIONS OSCAR TOOK, AND THE REASONING — DISTINGUISHED FROM FINDINGS

Everything in the arc above is a finding — a number, a diagnosis, a
mechanism. The items below are decisions: points where a choice was made
among live alternatives.

**To fix `match_control()`-style defects rather than freeze them —
yesterday's precedent applied again.** The 2026-09-06 session established
the pattern: a genuine implementation defect that is *understood* gets
fixed, not quarantined behind a flag, even mid-arc. Today it was applied
twice — the six `v2*` canonical bypasses were fixed in place rather than
suppressed in the checker (step 6, option a), and the backtest test's
stale assertions were removed and replaced with a working invariant
rather than skip-listed (step 10). The alternative in both cases was to
mark the failure "known" and move on; that alternative was declined
because the failures were diagnosed, not merely observed.

**To make Telegram a bug-only channel — silence as the default.** The
standard set: Telegram carries only messages Oscar would act on, and
silence means nothing needs attention. This is a policy choice, not a
technical one — the audit (step 4) found no single broken component so
much as an accumulation of informational sends that had buried the
actionable ones. The remediation (step 5) enforced the policy: gate
everything, pause the pure digests, retire alerts about deliberate
states. The deliberate limitation accepted alongside it — recovering
from CRITICAL produces no "all clear" — was the task's literal spec, and
is recorded as a known tradeoff, not an oversight.

**To accept the dormant `characterize_legendary_overlap_recompute.py`
violation into the register with a 2026-10-15 review date.** The
reasoning: the script is a dormant single-use characterisation tool (its
only run was 2026-08-18), and its `< 2175` comparison is a deliberate
probe of the *legacy* raw-`geo_elo` LEGENDARY notion — audit-trail
evidence behind a corrected overlap figure — not gate logic that
drifted. Accepting it lets the check go green without pretending the
disposition question (fix the literal / exempt in the checker / leave)
is settled; the `review_by` date forces that choice within ~5 weeks.

**To deliberately NOT register `test_backtest_window_population.py`.**
This is the more instructive of the two register decisions. That test
covers `backtest_window_sql()`, the canonical population function that
§6.8 of `MASTER_HANDOVER_2026-08-15` records production scripts as
routinely bypassing — so a permanently-accepted failure there would mean
no signal if the function genuinely broke. It had **not been diagnosed**
at the time the register was built. Registering it then would have
converted "we haven't looked" into "we've decided it's acceptable" — the
exact silent-tolerance failure the register exists to make impossible.
It was left noisy until diagnosed (step 9), then fixed (step 10), which
is the outcome the non-registration protected.

---

## WHAT WENT RIGHT METHODOLOGICALLY

- **The Part 1 stop condition fired correctly and stopped the
  enforcement build.** The task was a four-part build; Part 1 was
  instructed to diagnose first and halt if the chronic failure turned
  out to be a real violation rather than a stale rule. It was a real
  violation, and the build stopped there — no canonical-call adherence
  check, no reproducibility check, no wiring was layered on top of an
  unresolved finding. The three later pieces of enforcement work
  (Telegram remediation, the `v2*` fixes, failure-age tracking) were each
  scoped and commissioned as separate tasks, each with its own decision
  doc, rather than continued from the halted build.

- **The stranded-markets reconciliation returned verdict (c)
  unreproducible and said so.** Four candidate predicates were tested
  against the live DB; none reproduced 1,983. Rather than pick the
  nearest (`open + partially_closed` → 1,364) or the most narratively
  satisfying (organic trader churn, plausible given position
  concentration), the doc recorded **[U] undetermined** and shipped a
  script that persists full membership so the question cannot recur in
  this form.

- **The backtest diagnosis disproved chat-Claude's own framing rather
  than inheriting it.** The task prompt asserted the `54 → 52` shrink
  was "the most informative" delta and that "a population defined by an
  accumulating condition should not shrink — find out what left it." The
  diagnosis established there is no accumulating population there:
  `false_negatives = snapshot − old` is a set difference with a frozen
  minuend and a growing subtrahend, which contracts by construction as
  `old` absorbs frozen members. The two markets that "left" were traced
  to a `resolution_date` backfill, but the framing that a shrink implied
  an anomaly was shown to be wrong, not carried through.

- **The new subset assertion was demonstrated to fail before being
  trusted.** T1c was run against an in-memory DB with a snapshot market
  forced out of the canonical result three different ways
  (re-categorisation, `trade_gap_flag`, zero trades); each produced a
  `[FAIL]` naming the dropped id, and the clean case produced `[PASS]`.
  A test that cannot fail is not a test — this project has been bitten
  twice by diffs proving no reachable behaviour, and that check was run
  here before the assertion was committed.

---

## WHAT WENT WRONG — stated plainly, not softened

**A decision document asserted the `load_dotenv()` gap was unfixed when
it had been fixed hours earlier in the very commit that document cited
as its starting HEAD.** `2026-09-07-canonical-violations-part2-fix.md`
(header: "HEAD at start: `51e3b74`") stated in its closing section that
`check_canonical_definitions.py`'s `load_dotenv()` credential gap was
"still unfixed; out of scope here." That was wrong: `51e3b74` — the
exact commit the document cites as its starting point — had already
added `from dotenv import load_dotenv; load_dotenv("/home/parison/.env_trading")`
to `send_telegram_alert()`. `git log -S load_dotenv --
scripts/check_canonical_definitions.py` returns only `51e3b74`. The
premise came from the framing of the predecessor task (the Part 1 STOP
doc, written before `51e3b74` landed) and was carried into the closing
section without being checked against `51e3b74`'s actual diff. This is
**at least the fourth recorded instance** of the project's standing
lesson — *"Chat-Claude's premises enter the record and must be verified,
not inherited"* (`MASTER_HANDOVER_2026-09-05.md` §8). Corrected by a
dated in-place amendment during the failure-age-tracking task, with a
Part 5 note in that task's own doc; the two substantive parts of the
part-2 doc (the LIVE/DORMANT classification and the equivalence-preserving
fix) are unaffected.

**`test_failure_age_tracking.py:308` hard-asserts the accepted-failures
register equals `{"entries": {}}`. It broke when the register entry was
added the same session. This is the same anti-pattern the backtest work
diagnosed and removed the same evening — an equality assertion against
mutable state — reintroduced independently, in new code.** The assertion
`r.check("12d the committed register is present and seeded EMPTY",
real_register == {"entries": {}})` was committed at 19:06 in `f6a8b88`.
The register entry was added at 19:12 in `f882a86`, six minutes later,
and `12d` has been red ever since — caught by the full-suite run in this
session's backtest-fix task (`test_failure_age_tracking.py`: 38 tests,
37 passed). **Record this as the session's most instructive failure:
naming an anti-pattern does not prevent it.** Two members of the same
class ("equality assertion against a value that legitimately changes")
were live in the codebase at the same time today — one being removed
from `test_backtest_window_population.py`, one being written into
`test_failure_age_tracking.py`.

*Discrepancy with the task prompt, flagged not reconciled:* the prompt
describes this anti-pattern as one "the backtest work removed hours
earlier." By commit timestamps it was the reverse order — the bad
assertion landed at 19:06 (`f6a8b88`), **before** the backtest diagnosis
that named the anti-pattern (`00aeb93`, 19:29) and before the removal
commit (`f415faa`, 19:42). The reintroduction preceded the diagnosis by
~23 minutes; it was not a regression after a fix but a parallel
occurrence in overlapping work. The substance of the lesson is
unchanged, and arguably sharper: the two happened at essentially the
same time.

---

## DISCREPANCIES BETWEEN THIS SESSION'S PROMPT AND REPO STATE

Flagged per the task's own instruction, not silently reconciled.

- **"7 canonical violations resolved" is imprecise.** Six of the seven
  were fixed by code (`f63dd5a` — the `v2*` scripts). The seventh
  (`characterize_legendary_overlap_recompute.py:84`, dormant) was **not
  fixed** — it was accepted into the register (`f882a86`) with an open
  disposition and a 2026-10-15 review date. All seven were addressed;
  not all seven were resolved.

- **The `load_dotenv()` ordering** — see the second "What went wrong"
  paragraph above. The prompt's "removed hours earlier" does not match
  the commit graph.

- **"11.6 GB memory peak and SIGTERM hang on restart — observed twice
  today"** — verified against `journalctl -u polymarket-observer` (no
  committed artifact carries this). The **SIGTERM hang did occur twice**:
  `18:23:35` and `19:09:29`, both `State 'stop-sigterm' timed out.
  Killing.` → `Main process exited, code=killed, status=9/KILL` →
  `Failed with result 'timeout'` (these line up with the observer
  restarts needed to load `51e3b74` and `f6a8b88`). The **11.6 G memory
  peak applies to the first stop only** — the long-lived process
  (`Consumed 2h 16min 3.059s CPU time, 11.6G memory peak`). The second
  stop's process had been alive ~45 minutes and peaked at 378.9 M. The
  observer is currently up (since `19:09:29`, 168 MB). Neither hang was
  investigated.

- **"Progression check"** — no committed artifact; it was a read-only
  session opener with no commit, consistent with the "no thesis
  movement" theme.

---

## OPEN THREADS CARRIED FORWARD, EACH WITH WHAT WOULD SETTLE IT

- **`test_failure_age_tracking.py:308` needs its assertion loosened.**
  It currently requires `fa.load_register() == {"entries": {}}`, which
  fails the moment the register is used for its purpose. What would
  settle it: replace the equality with a shape / per-entry-validity
  check (every entry has the five required fields, `review_by` parses,
  no unexpected top-level keys) — assert the register is *well-formed*,
  not *empty*. Not done here; out of scope of every task today, and the
  register / `failure_age.py` were explicitly off-limits in the task
  that found it.

- **The observer's 11.6 GB memory peak and SIGTERM hang on restart.**
  Observed twice today (§Discrepancies). What would settle it:
  identifying what the observer holds that does not release on SIGTERM
  (the in-memory `PerformanceMonitor.metrics_history`, an unclosed DB
  cursor, an asyncio task that ignores cancellation) and whether the
  11.6 G is a leak or a working-set that grows unbounded with uptime. Not
  investigated.

- **Failure-age tracking is wired to two checks only**
  (`check_canonical_definitions.py`, `system_observer.py`'s diagnostic
  report). The failure-age doc names **`audit_invariants.py` as the
  highest-value next target** — it sends a REGRESSION-tier invariant list
  every daily-maintenance run, and whether it re-sends the same
  regressions identically each day was left unassessed by the Telegram
  remediation. What would settle it: wrap `audit_invariants.py`'s alert
  path in the same reconcile/evaluate/render flow, keyed on invariant
  name. `run_tests.py` per-file (ideally per-assertion) keys and
  `daily_maintenance.py` per-step exits are the other named candidates.

- **The execution dimension (Components 2 and 3 of the canonical
  skill-metric design)** — absolute and relative earliness, proposed
  2026-09-05, still the live thesis thread, untouched today. What would
  settle it: a separately pre-registered execution-vs-edge test on a
  population not itself pre-selected on direction. This is where the
  2026-09-06 cross-arc pattern points.

- **The relevance-classifier gate adjudication.** The 2026-09-03 gate
  passed precision and failed recall (90.35%, all six cells); the
  2026-09-04 diagnostic found ~79% genuine classifier miss. Oscar's
  formal adjudication (§3.11(a) abandon vs. continue) is still
  outstanding. What would settle it: that adjudication.

- **The stranded-markets remediation decision.** The defect's current
  scope is now measurable from a committed script with persisted
  membership (196,764 stranded markets, 8,831 open positions, 1,168
  affected traders). Whether to remediate, and how to batch it safely,
  is undecided — explicitly out of scope of the reconciliation task,
  Oscar's call. What would settle it: a remediation-safety assessment
  and a batching plan.

---

## A NOTE ON VERIFICATION

Every commit hash and figure in this document was checked against its
committed source or against `journalctl` before inclusion, not restated
from the task prompt — today itself produced a fourth instance of the
failure that happens when that check is skipped. The three places the
checking changed what this document says are recorded explicitly in
§Discrepancies: the "7 resolved" count, the `load_dotenv()` commit
ordering, and the scope of the "11.6 GB" figure.

No verdict on what to do next is stated here. Every open thread above is
carried forward as a thread, not a recommendation.
