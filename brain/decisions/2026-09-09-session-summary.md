# Session Summary — 2026-09-09 (Server Setup 14)

## HEADLINE — a production data change was made

**24,390 Geopolitics/Elections trade rows moved from `trade_result='pending'`
to `won`/`lost` (12,376 won / 12,014 lost / 0 invalid). 1,996 traders'
`traders.geo_resolved_trades_count` increased.** This was a deliberate,
Oscar-approved write to production research data — not maintenance, not
hygiene. It changes the population that every pre-split cohort computation
draws from.

**Dated boundary: any Objective-1 or Objective-2 measurement taken on or after
2026-09-09 is on a different population than one taken before.** A future
reader must not diff a post-2026-09-09 cohort / placebo / eligible-pool count
against a pre-2026-09-09 one and attribute the difference to anything but this
drain plus routine maintenance drift. The three prior HEADs to anchor against:
pre-drain state = first-repo `281c0f9` and its committed baseline artifacts;
post-drain state = first-repo `399898e` / `eee49ee`.

The frozen result of record — `metric_v2f_oos_result` (cohort gap **+0.0316**,
CI [−0.0088, +0.0710], n = 3,032 / 120; placebo +0.0127, n = 2,569 / 110) — is
**byte-identical before and after** (sha256
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`, re-checked
at every shard and at session end). Nothing wrote it. What the drain changes is
what a *re-measurement* of that quantity would now return.

This session did not touch the directional-skill thesis, the execution
dimension, or any open research question. `MASTER_HANDOVER_2026-09-06.md`
(`6c3ce36`) remains the entry point and is not superseded.

---

## THE ARC IN SEQUENCE

first-repo `main`, trading-swarm `master`. Every commit hash and figure below
was checked against its source this session.

### 1. Progression check — read-only opener, no commit

Checked system status and thesis position; found no thesis movement. Re-surfaced
one standing item: the `last_checked`-stranding defect's headline figures
(**8,077 open positions / 1,983 distinct traders**, on 195,625 / 214,413
markets) remain **(c) unreproducible by construction** — the two 2026-08-30
source docs are doc-only, no committed query, no persisted ID list.

**Discrepancy flagged, not reconciled:** the task prompt places this finding —
and "a committed script with persisted ID lists now exists" — in *today's*
arc. It is **2026-09-07 (Server Setup 13)** work: the committed replacement
script is `first-repo 52cfa39` ("feat: committed, self-checking stranded-markets
characterization script", 2026-09-07 17:07), the decision doc is
`2026-09-07-stranded-markets-figure-reconciliation.md`, and it is recorded as
arc-step-2 of the 09-07 summary. That session's *fresh* measurement was
216,499 clob-resolved markets / 196,764 stranded / 8,831 open positions — a
different set from the retired "8,077 / 1,983." Today's progression check
produced no commit and, as far as the repo and this session's context show,
added nothing to that finding beyond re-flagging it. If a distinct 09-09
artifact exists it is not in git.

### 2. `discover_leaderboard_traders.py` Sunday-runtime check — read-only, no commit

Verdict: **not degrading.** The "283% growth" flag (Sunday runtime 4,883 s →
18,714 s, 2026-08-16 → 2026-08-23) was a **bounce off an outlier low**: 08-16
was the all-time-minimum run (1,345 new candidates; every run's cost is
≈ 3.5 s × candidates, r ≈ 0.999). Full history: 08-30 hit a new peak
(30,256 s, 8,636 candidates), 09-06 fell back to 23,444 s. No secular trend; no
run has ever hit the 36,000 s / 10 h budget; the one non-completion ever
(2026-05-31, SIGKILL) predates that budget. Not on any thesis path. Findings
delivered in-reply only.

### 3. `compare_trade_evaluators.py` retired

- Recommendation doc: `trading-swarm 53b8514`
  (`2026-09-09-compare-trade-evaluators-retire.md`, 19:07).
- `git rm`: `first-repo bbca45f` (19:21, executed inside the blast-radius task
  after Oscar approved).

The script's import (`from scripts.backfill_trade_results_geo import
evaluate_trade`) has been broken since the 2026-08-19 repoint `8cfeb8e`
removed that function. Its purpose — comparing two win/loss implementations —
died with the repoint (there is now one). An import-only fix is impossible
(the removed function had a 3-scalar signature the call site is written for)
and would be a tautology. Nothing else imports the symbol. The ongoing
regression guard is `verify_geo_backfill_repoint.py`.

### 4. Geo-backfill wiring assessment — **HALT**

`trading-swarm 28d898b` (`2026-09-09-geo-backfill-wiring-decision.md`). No
first-repo commit — nothing was wired.

Part 1 cleared: `backfill_trade_results_geo.py` is batched (1,000/commit),
idempotent, uses the canonical `TradeEvaluator`, has `--limit`, no
`last_checked` coupling. Part 2 tripped **STOP CONDITION 3**: the `--dry-run`
found **24,390** pending rows and would evaluate all of them —
**won 12,376 / lost 12,014 / invalid 0, N = 1,996 traders affected**, leaving
**0** pending. That is a **one-run drain**, not a daily top-up; a drain is a
different operation with different risk (research-population change, burst-load
history), so wiring was not performed. Recommended, as a proposal, a
post-drain `--limit 200` daily top-up positioned as a new step 22 between
"Evaluate new trader results" and "Reconcile geo resolved counts [post-eval]".

### 5. Blast-radius audit — **HALT**

`trading-swarm ebdf1f1` (`2026-09-09-geo-drain-blast-radius.md`);
`first-repo bbca45f` (the retirement above).

**STOP CONDITION 1 met** — the drain would materially change pre-split cohort
definitions:

- **8,350** of the 24,390 pending rows sit in **1,898 markets whose `tape_end`
  is before T_split (2026-04-01)** — inside the canonical pre-split backtest
  population. **4,997** of those are the entry trade of a geo/elec position,
  across **737 distinct traders**.
- **PIT-legal classifiable population (5,732) projected to grow ~+131** (SQL
  bound 5,751 → 5,882). Objective-2 `build_presplit_cohort` inputs change for
  737 traders: **90 already ≥ M_CHOSEN=10 (stats shift), 131 cross into ≥10,
  516 stay < 10 (inert)**.
- **5 of the 295 traders in the persisted `metric_v2f_intersection_cohort`
  (Objective 1) are pre-split-affected; 13 including post-split flips.**

**STOP CONDITION 2 NOT met**: no *scheduled* consumer of `trades.trade_result`
writes to `metric_v2f_oos_result` or `metric_v2f_intersection_cohort` — those
are written only by a manual `trader_skill_metric_v2f.py --persist`.

Part 4 (separability): **no clean partition exists.** Every subset that spares
the thesis leaves a pre-split remainder that keeps growing —
**72 % of the pre-split pending rows are `background_backfill` provenance
(6,043 / 8,350)**: old trades on long-resolved markets, ingested for
newly-discovered traders. A partial drain leaving a growing remainder is
plausibly worse than either extreme.

### 6. Ingest fix — `background_backfill_worker.py`

`first-repo 7ae0f2a`; `trading-swarm 08f3f79`
(`2026-09-09-background-backfill-ingest-evaluation.md`).

`_process_trader_sync` now does **one batch lookup** (chunked at 900, on a
short-lived read connection closed before the write connection — write-txn
shape unchanged) of `markets.resolved` / `winning_outcome`, and for a trade on
an already-resolved market with a usable outcome writes the real `won`/`lost`
via the canonical `TradeEvaluator.evaluate_trade()` instead of the hard-coded
`'pending'`. Market absent / unresolved / NULL-or-`unknown` outcome / an
`invalid` verdict still write `'pending'`. **Future inserts only** — `INSERT OR
IGNORE` cannot touch an existing row. New test file (29 checks: correctness vs
the evaluator, non-tautology, no-existing-row-changed); `run_tests.py` 23/23.

Effect: **~99 % of the current pending rows are in markets that already exist
in `markets`**, so the dominant inflow channel stops at source; the residual
is transient (resolution-lag rows that clear when a market resolves + an
evaluator runs). The live-monitor `polymarket_api` ingest path (~40 % of the
backlog) is **unchanged and correct** — those trades legitimately precede
resolution; they clear when an evaluator touches them. The existing 24,390
backlog is untouched (that is the drain).

### 7. Pre-drain baseline capture — **HALT**

`first-repo 281c0f9`; `trading-swarm cdd09aa`
(`2026-09-09-predrain-baseline-capture.md`). Read-only except a `git rm` from
step 3.

**STOP CONDITION met — the population had already moved.**
`directional_skill_pit_legal_pool.py` re-run fresh: `n_clearing_min`
(the "5,732") = **5,751 (+19)** vs the committed 2026-09-06 figure, **with no
drain run** — driven by routine daily maintenance
(`evaluate_new_trader_results` + resolutions + category backfill). It was
already 5,751 in this morning's blast-radius run (predates `7ae0f2a`).
`directional_skill_twice_classifiable_population.py` **hard-STOPs** on its
`EXPECTED_CLASSIFIABLE = 5732` guard (exit 1), so the fresh 753 / 146 / 607
populations and the fresh persistence test could not be produced.

Captured despite the halt (complete for the drain's scope):

- **Backup** `backups/markets_20260909_200015.db` — `PRAGMA integrity_check` =
  `ok`, 213 s, `flock` on the cron lock in play. Backup `trades` count = live
  = 13,627,405.
- **Drain manifest** — 24,390 rows = live `check_pending_geo` exactly, one row
  per trade_id, each with `position_id`(s) and a pre/post-split-by-`tape_end`
  label.
- **Objective-2 cohort / placebo membership: 172 / 172** — via
  `build_presplit_cohort()` / `match_control()` / `measure_oos()` at seed 42,
  with per-trader post-split position lists. **This had NEVER been persisted —
  it is the named mechanism behind the 2026-08-16 UNREPRODUCIBLE verdict.**
  Proven **byte-identical across two separate processes** (`PYTHONHASHSEED`
  randomized each; `match_control` deterministic since `first-repo 42b14fc`,
  2026-09-06, which sorts every set-derived sequence). `metric_v2f_oos_result` sha256 identical
  before and after the capture. **This was the only opportunity — after the
  drain the pre-drain cohort and placebo could not be reconstructed by any
  means.**
- Six persisted-table dumps (`metric_v2f_*`, `directional_skill_pit_exploratory_*`,
  `backtest_population_snapshots`), each with a row count and sha256.
- **Full `traders` state dump — 194,724 rows** (`address, geo_elo,
  geo_elo_active, geo_resolved_trades_count, geo_accuracy_pool,
  resolved_trades_count, research_excluded`). Baseline aggregates:
  geo_elo set 11,151; `geo_resolved_trades_count > 0` → 32,144;
  **`geo_accuracy_pool = 1` (Pool C) → 4,276**; `resolved_trades_count ≥ 20`
  → 30,003; `research_excluded = 0` → 39,658.
- Disjoint controls: **92-market pending-resolution = 98**; **161 no-FIFO-close
  = 165**.

### 8. Drain executed

`first-repo 399898e` + `eee49ee`; `trading-swarm 37954a9`
(`2026-09-09-geo-drain-execution.md`). Oscar-approved, **option-2 scoping**.

Pre-flight all passed (backup integrity `ok`; oos_result sha256 `021be40a…`;
live `check_pending_geo` = 24,390 — zero drift; daily maintenance paused by
commenting one crontab line, verified only that line changed; monitor +
observer active).

Five shards, `backfill_trade_results_geo.py --limit 5000`, each detached
(`nohup … & disown`) and confirmed complete before the next:

| shard | found | won | lost | invalid | traders | `check_pending_geo` after |
|---|---|---|---|---|---|---|
| 1 | 5,000 | 2,462 | 2,538 | **0** | 1,073 | 19,390 |
| 2 | 5,000 | 2,693 | 2,307 | **0** | 347 | 14,390 |
| 3 | 5,000 | 2,350 | 2,650 | **0** | 258 | 9,390 |
| 4 | 5,000 | 2,453 | 2,547 | **0** | 141 | 4,390 |
| 5 | 4,390 | 2,418 | 1,972 | **0** | 182 | **0** |
| **total** | **24,390** | **12,376** | **12,014** | **0** | — | **0** |

Won/lost split = the dry-run prediction exactly. No batch error, no rollback,
no retry. **Zero write-lock contention** — no `database is locked` / `ERROR` /
`CRITICAL` in `monitoring.log` during the 20:29:35Z → 20:33:10Z window;
`pnl_worker` heartbeat held its ~16 s cadence unbroken. `oos_result` sha256
re-checked after every shard. Shard 5 found 4,390 (< limit) — expected, the
remainder; no shard was starved by another path (maintenance paused; the
ingest fix touches only future inserts).

### 9. Verification (in order)

**Controls first (canaries):**
- **92-market pending-resolution: 98 → 0** — did **not** grow (the required
  condition). Clearing pending trades moves markets out of the
  "all-entry-trades-pending" definition; 0 is the correct direction.
- **161 no-FIFO-close: 165 → 165** — exactly unchanged. Disjoint mechanism.

**In-scope:**
- `check_pending_geo`: **24,390 → 0**.
- `metric_v2f_oos_result`: `.dump` diff against the step-2 snapshot —
  **identical**.
- `metric_v2f_intersection_cohort` (295, persisted table): `.dump` diff —
  **byte-identical** (the drain does not write it). *Recomputed* Objective-1
  intersection: post-drain 450 vs scratch-reverted 431 → **isolated drain
  effect +24 entered / −5 left** (the 295→431 gap is ~3.5 weeks of maintenance
  drift; the 295 is a frozen 2026-08-15 snapshot).
- **Trader-state diff (194,724 rows):** only `geo_resolved_trades_count`
  changed — **1,996 traders, all increases, 0 decreases** = exactly the
  manifest traders. `geo_elo` (0), `geo_elo_active` (0), `geo_accuracy_pool`
  (0), **`resolved_trades_count` (0)**, **`research_excluded` (0)** — all
  unchanged. 0 traders added / removed.
- **Objective-2 recompute:** `elig_pool` 2,894 → **3,004 (+110, 0 left)**;
  cohort 172 → **180 (+8, 0 left)**; placebo 172 → 180 (**26 in / 18 out**).
  `measure_oos` gaps: cohort 0.02782 → 0.02638, placebo 0.01989 → 0.02028 —
  both CIs still span zero, pre and post.

**The falsifiable test (Part 4):** a scratch copy of the *post-drain* DB
(`integrity_check` = `ok`), with exactly the 24,390 manifest `trade_id`s set
back to `'pending'`, then re-run:
- Objective-2 `elig_pool` / `cohort` / `placebo` trader lists —
  **ordered-identical to the pre-drain baseline, symdiff 0**; both
  `measure_oos` results **byte-identical**.
- 92-pop → **98**; 161-pop → **165** — pre-drain baselines recovered.

**Every downstream change reverts with the manifest** — including the
placebo's 26-in / 18-out greedy-match reshuffle and two non-manifest Objective-1
traders nudged out by the pooled within-trader-variance / EB-shrinkage shift.
Nothing moved that the 24,390 manifest rows do not account for.

### 10. Normal operation restored

Daily maintenance un-paused (`crontab -l` now byte-identical to the pre-drain
backup). Monitor + observer active throughout, never stopped. 20 GB scratch DB
deleted.

---

## THE DECISION AND ITS REASONING — why a population-changing write was judged acceptable

Recorded in full because a future reader will ask.

1. **The population was already drifting, not stable.** `n_clearing_min`
   (PIT-legal classifiable) went **5,732 → 5,751** between 2026-09-06 and
   2026-09-09 with no drain run, from routine daily maintenance. The choice
   was never *stable vs changed* — it was **change-once-and-measure vs
   drift-continuously-and-never-measure**.
2. **Every cohort the drain perturbs belongs to a question already answered.**
   The pre-split-edge result is falsified / null; the directional selector is
   null; the persistence test is complete (A1×B2). Re-measuring those is
   already on the do-not-do list, so a shifted re-measurement baseline costs
   nothing in flight.
3. **The backlog was a biased hole, not noise.** 131 pre-split traders sit
   outside the eligible pool *only because their trades were never evaluated*,
   and the gap is correlated with discovery recency — 72 % of the pre-split
   pending rows are `background_backfill` provenance, i.e. the histories of
   recently-discovered traders. That is precisely the population the discovery
   pipeline exists to widen; leaving it unevaluated is a systematic
   undercount, not random missingness.
4. **The timing window was clean.** The prior arc closed 2026-09-06; the next
   has not started. Nothing was in flight that a population change would
   disturb.
5. **Option-2 scoping (Oscar's decision, recorded):** the drain is judged by
   the manifest-restore falsifiable test on Objectives 1 and 2, plus the
   92 / 161 controls staying put. The **directional persistence populations
   (753 / 146 / 607) are explicitly out of scope** for drain verification —
   they drift ~±20 traders per 3 days from routine maintenance and cannot
   serve as a stable reference — so they were neither re-run nor diffed.

---

## WHAT WENT RIGHT METHODOLOGICALLY

- **Three separate HALTs fired correctly before any write** — the wiring
  assessment (STOP 3: one-run drain), the blast-radius audit (STOP 1:
  pre-split cohorts affected), and the baseline capture (STOP: population
  already moved). Each stopped on a pre-registered stop condition and handed
  the decision up, rather than proceeding on judgment.
- **The drain ran sharded with per-shard verification**, not one pass — five
  `--limit 5000` runs, each detached and confirmed complete, each followed by
  a `check_pending_geo` / lock-contention / monitor-heartbeat / oos_result
  check before the next.
- **The falsifiable test passed.** Reverting the manifest in a scratch copy
  recovered every baseline byte-for-byte, including the second-order effects
  (the placebo reshuffle; two non-manifest traders moved by pooled-variance
  shifts). This is the strongest available evidence that the change is fully
  accounted for.
- **A "5,440 lock errors" alarm during the drain was correctly diagnosed as a
  false positive** — an `awk` range filter (`$0 >= "2026-09-09 20:29:00"`) was
  matching untimestamped Python-traceback lines (`sqlite3.OperationalError:
  database is locked`) from months of log history, which sort lexically after
  the date string. The last *real* lock error in `monitoring.log` is dated
  **2026-09-07 06:01**. Diagnosed rather than acted on.
- **Objective 2's membership was captured before it became unrecoverable.**
  The 2026-08-16 UNREPRODUCIBLE verdict exists precisely because that
  membership was never persisted; this session persisted it (172 / 172,
  reproducible from seed) in the last window where it could be.

---

## WHAT WAS FOUND ALONG THE WAY, AND IS NOW KNOWN

- The stranded-markets **8,077 / 1,983** figure is **(c) unreproducible** — no
  committed script, no persisted membership, predicates never stated. A
  committed, self-checking replacement script and persisted ID lists now exist
  — **`first-repo 52cfa39`, 2026-09-07** (see the Discrepancies section).
- **`background_backfill_worker.py`'s hard-coded `'pending'` was the dominant
  inflow** to the geo/elections pending backlog. Fixed at source (`7ae0f2a`):
  backfilled trades on already-resolved markets are now evaluated at insert.
- **The live-monitor ingest path (`polymarket_api`) also writes `'pending'`,
  but correctly** — those trades precede resolution; they clear when an
  evaluator runs. Not a leak; not touched.
- **`EXPECTED_CLASSIFIABLE = 5732` (plus `EXPECTED_RAW_SURVIVORS = 711`,
  `EXPECTED_BH_SURVIVORS = 504`) in `directional_skill_twice_classifiable_population.py`
  is a hard-coded guard asserting equality against a live, drifting
  population** — exit 1 on any mismatch. It is the same class of anti-pattern
  the `test_backtest_window_population.py` count-assertion removal
  (`f415faa`, 2026-09-07) addressed. Ordering: the guard was written first
  (`1d34ced`, 2026-09-06) — it is a **pre-existing instance**, not a
  regression after the anti-pattern was named (see Discrepancies). It blocked
  the fresh persistence baseline this session.

---

## DISCREPANCIES BETWEEN THIS SESSION'S PROMPT AND REPO STATE

Flagged per the task's own instruction, not silently reconciled.

- **The "progression check → defect figure flagged as irreproducible" arc
  step, and "a committed script with persisted ID lists now exists," are
  2026-09-07 (Server Setup 13) work, not today's.** Commit `first-repo
  52cfa39` (2026-09-07 17:07); doc `2026-09-07-stranded-markets-figure-reconciliation.md`;
  recorded as arc-step-2 of the 09-07 summary. Today's progression check was
  read-only, produced no commit, and — per the repo and this session's
  context — added nothing new. The prompt reads as if this were produced
  today; it was not.
- **"131 pre-split traders excluded from the eligible pool" mixes two
  populations.** The **+131** is the blast-radius audit's *projected* growth of
  the **PIT-legal classifiable population** (`directional_skill_pit_legal_pool.py`
  `n_clearing_min`, bound 5,751 → 5,882) — a pre-drain projection, never
  measured post-drain because that population is out of scope. The **measured**
  post-drain change to the Objective-2 `build_presplit_cohort` eligible pool
  (`n_pairs ≥ 10`) was **+110** (2,894 → 3,004, 0 left). Different definitions;
  same direction. The prompt's phrasing is close enough to be right in spirit
  but the exact figure belongs to a different population than "the eligible
  pool."
- **"This is a research-population change" is exact for the *inputs* to
  Objectives 1 & 2 and the persistence populations; it is NOT true of the
  result of record.** `metric_v2f_oos_result` (+0.0316) is byte-identical
  before and after and was never at risk — no `--persist` ran. What changed is
  what a *re-measurement* would return. A future reader should not read
  "population change" as "the +0.0316 moved."
- **"EXPECTED_CLASSIFIABLE … the same anti-pattern removed … two days ago, in
  new code."** The guard is in `1d34ced` (2026-09-06); the
  `test_backtest_window_population.py` count-assertion removal is `f415faa`
  (2026-09-07). So the guard predates the removal by a day — "recent code," not
  "new code written after the anti-pattern was named." The substance (a
  hard-coded count assertion against a drifting live population, now proven to
  break) is unchanged.

---

## OPEN THREADS CARRIED FORWARD, EACH WITH WHAT WOULD SETTLE IT

- **`backfill_trade_results_geo.py` is still unwired into `daily_maintenance.py`.**
  Without it, the transient resolution-lag rows accumulate again, slowly. The
  geo-backfill wiring decision (`28d898b`) proposed `--limit 200` as a daily
  top-up positioned as step 22; that limit now applies to a *finite* arrival
  rate because the ingest fix (`7ae0f2a`) stopped the dominant channel.
  Settles when: someone wires it (a small edit + a registration test) or
  records a decision that the residual inflow is acceptable unmanaged.
- **`update_geo_elo` will recompute `geo_elo` and re-gate Pool C at the next
  06:00 UTC maintenance run.** This is expected settlement, not a regression:
  the drain raised `geo_resolved_trades_count` for 1,996 traders; some will
  cross `≥ 10` into Pool C. **Watch Pool C's size against the baseline
  4,276.** Settles when: the 06:00 run is observed and the new Pool C count is
  recorded.
- **General `resolved_trades_count` / Pool B (`research_excluded`) is latent.**
  Unchanged now (nothing scheduled recomputes it for the non-flagged
  population), but the underlying trade rows moved — a future manual
  `recalculate_trader_stats.py` / `reconcile_trader_aggregates.py` run would
  raise it for the ~1,996 traders and could then move Pool B. Settles when:
  someone runs a full stats recompute (and records the Pool B delta) or
  decides not to.
- **Whether Sunday's `recalculate_comprehensive_elo.py` reaches the flipped
  rows is untraced.** Only `analysis/pit_geo_elo.py` among analysis modules
  reads `trade_result` directly; whether the Sunday recompute path invokes it
  was not established. Settles when: someone traces the Sunday ELO call graph
  for a `trade_result` read.
- **The execution dimension (Components 2 and 3) is untouched** — still the
  live thesis thread. Settles when: it is picked up (out of scope all
  session).
- **The relevance-classifier gate adjudication is still outstanding** (Oscar's
  formal call on the 2026-09-03 recall-FAIL / §3.11(a) abandon question).
  Settles when: Oscar adjudicates.

---

## A NOTE ON VERIFICATION

Every commit hash, figure, and file:line in this summary was checked against
its source this session: `git log` for hashes and dates; the eight
`2026-09-09-*.md` decision docs for the per-step figures; live `sqlite3`
queries were **not** re-run for this summary (documentation only) — the
drained state (`check_pending_geo = 0`, 12,376 / 12,014 / 0,
`geo_resolved_trades_count` for 1,996 traders, oos_result sha256 `021be40a…`)
is quoted from `2026-09-09-geo-drain-execution.md` and the shard `.out.txt`
files under `first-repo:data/characterizations/geo_drain_execution_20260909T203310Z/`.
Where the prompt's framing diverged from what the repo records, the divergence
is in the Discrepancies section, not reconciled away. No verdict on what to do
next; the wiring, the Pool C watch, and the stats recompute are named as open
threads, not recommendations.

---

*Server Setup 14. Production writes this session: `trades.trade_result`
(24,390 rows, pending → won/lost) and `traders.geo_resolved_trades_count`
(1,996 traders, increases), via `backfill_trade_results_geo.py --limit 5000`
× 5. Crontab edited (maintenance pause) and restored byte-identical. No
`--persist` anywhere; no monitor / observer / guard / threshold / EXPECTED_*
constant touched. `metric_v2f_oos_result` sha256
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e` verified
unchanged at every checkpoint.*
