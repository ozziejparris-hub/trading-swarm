# 2026-09-09 — Geo pending-results drain: EXECUTED (step 3 of 3)

**Outcome: SUCCESS. All 24,390 `check_pending_geo` rows evaluated
(12,376 won / 12,014 lost / 0 invalid). `check_pending_geo`: 24,390 → 0.
Every verification passed. `metric_v2f_oos_result` byte-identical throughout.
Daily maintenance paused for the drain, un-paused after. Monitor and observer
ran untouched the whole time. The falsifiable test recovers the pre-drain
baselines from the manifest alone.**

Approved by Oscar 2026-09-09. Steps 1 (`7ae0f2a` ingest fix) and 2
(`281c0f9` baseline capture) preceded this.

Artifacts: `first-repo:data/characterizations/geo_drain_execution_20260909T203310Z/`
(shard logs, post-drain + scratch-reverted recomputes, recompute scripts,
control outputs). Pre-drain crontab: `…/crontab.pre_drain_20260909T202800Z.bak`.

---

## Scoping decision (recorded per the task)

**The drain is judged by the manifest-restore falsifiable test on Objective 1
and Objective 2, plus the 92/161 controls staying put.** The directional
persistence populations (753 twice-classifiable / 146 cohort / 607 comparison)
are **explicitly OUT OF SCOPE for drain verification** — they drift ~±20
traders per 3 days from routine daily maintenance
(`evaluate_new_trader_results` + resolutions + category backfill): 5,732 →
5,751 between 2026-09-06 and 2026-09-09 with no drain run
(`2026-09-09-predrain-baseline-capture.md`, `cdd09aa`). They cannot serve as a
stable reference, so they were neither re-run nor diffed here, per Oscar's
option 2.

---

## Part 1 — pre-flight (all passed)

| # | check | result |
|---|---|---|
| 1 | Backup exists / readable / integrity | `backups/markets_20260909_200015.db`, 20,707,409,920 bytes, `PRAGMA integrity_check` → **`ok`** (re-run this session, ~4 min) |
| 2 | `metric_v2f_oos_result` sha256 | **`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`** — matches the step-2 capture exactly. Nothing wrote it. |
| 3 | Live `check_pending_geo` | **24,390** — zero drift from capture (24,390) |
| 4 | Daily maintenance paused | `crontab -l` line 3 (`0 6 * * *  run_daily_maintenance.sh`) prefixed with `#DRAIN-PAUSE-20260909 ` via `crontab - < <edited>`; diff confirms **only that one line changed**; no `daily_maintenance` process running. Pre-drain crontab saved to `data/characterizations/crontab.pre_drain_20260909T202800Z.bak`. **Un-pause** = `crontab - < <that file>` (done in Part 5). Note: the file-argument form `crontab <file>` was refused in this environment (setuid path restriction); the stdin form `crontab - < <file>` works. |
| 5 | Monitor + observer running | `polymarket-monitoring` **active**, `polymarket-observer` **active** — NOT stopped. `pnl_worker` heartbeat current (~16 s cadence). |

Nothing else writes concurrently: the only other scheduled DB writers are the
03:00 UTC backup (already ran, 03:23Z) and the Sunday-only ELO timer / sweep
(today is Wednesday). The live monitor + background workers keep running by
design — verified safe below.

---

## Part 2 — drain in 5 shards (`--limit 5000`, detached, confirmed complete)

Drain window **20:29:35Z → 20:33:10Z** (~3.5 min wall, ~75 s of script runtime).

| shard | found | won | lost | **invalid** | traders (`geo_resolved_trades_count`) | elapsed | `check_pending_geo` after | lock contention | monitor |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 5,000 | 2,462 | 2,538 | **0** | 1,073 | ~9 s | 19,390 (−5,000) | **none** | heartbeat unbroken |
| 2 | 5,000 | 2,693 | 2,307 | **0** | 347 | ~15 s | 14,390 (−5,000) | **none** | heartbeat unbroken |
| 3 | 5,000 | 2,350 | 2,650 | **0** | 258 | ~15 s | 9,390 (−5,000) | **none** | heartbeat unbroken |
| 4 | 5,000 | 2,453 | 2,547 | **0** | 141 | ~15 s | 4,390 (−5,000) | **none** | heartbeat unbroken |
| 5 | **4,390** | 2,418 | 1,972 | **0** | 182 | ~20 s | **0** (−4,390) | **none** | heartbeat unbroken |
| **total** | **24,390** | **12,376** | **12,014** | **0** | — | — | **0** | — | — |

- **invalid = 0 in every shard** — matches the dry-run prediction. The 12,376 /
  12,014 won/lost split is **exactly** the geo-backfill-wiring dry run's
  prediction (`2026-09-09-geo-backfill-wiring-decision.md`).
- **No batch error, no rollback, no retry** in any shard log. Every batch
  printed `Batch committed`.
- Shard 5 found 4,390 (< the 5,000 limit) — expected, it drained the remainder.
  No shard found *fewer than expected for its position* — the pending count
  fell by exactly the shard size each time (5,000/5,000/5,000/5,000/4,390).
  **Zero rows were drained by other paths during the window** (maintenance
  paused; the step-1 ingest fix only touches future inserts).
- **Write-lock contention: none.** `monitoring.log` shows **0** `database is
  locked` / rollback / `ERROR` / `CRITICAL` entries during the entire drain
  window (verified by line-offset marker before each shard). The `pnl_worker`
  batch heartbeat held its ~16 s cadence straight through:
  20:29:25 → 20:29:42 → 20:29:58 → 20:30:15 → … → 20:33:xx, no gap.
  (An earlier alarm of "5,440 lock errors" was a false positive — an `awk`
  range filter matched untimestamped Python-traceback lines from months of log
  history; the last real lock error in the file is dated **2026-09-07 06:01**,
  during that day's maintenance run.)
- `metric_v2f_oos_result` sha256 re-checked after every shard: `021be40a…`
  every time.

---

## Part 3 — verification (in order)

### Controls first (the canaries) — BOTH PASS

| control | pre-drain baseline | post-drain | verdict |
|---|---|---|---|
| **92-market pending-resolution** (`characterize_pending_resolution_inconsistency.py` `pending_inconsistency_count`) | 98 | **0** | ✅ **did not grow** (the required condition). Clearing pending trades moves markets out of the "all-entry-trades-pending" definition — 98 → 0 is the correct direction. `canonical_population` 7,330→7,330, `v2f_population` 7,067→7,165, `symmetric_diff` 263→165 (markets moved into the "has evaluated trades" population). |
| **161 no-FIFO-close** (`characterize_no_fifo_close_markets.py` `no_fifo_close_count`) | 165 | **165** | ✅ **exactly unchanged.** Cohort overlap 7 traders / 25 rows / 20 markets — also unchanged. Disjoint mechanism, as expected. |

### In-scope populations

**`check_pending_geo`: 24,390 → 0.** Fell by exactly the total drained
(24,390). Geo/elec resolved non-gap trades are now `won` (385,824) / `lost`
(350,839), **zero pending**.

**`metric_v2f_oos_result`: sha256 `021be40a…` — unchanged.** Full `.dump` diff
against the step-2 snapshot: **identical**. The +0.0316 result of record is
untouched. Nothing wrote it (no `--persist` run anywhere).

**`metric_v2f_intersection_cohort` (295, persisted table): byte-identical** to
the step-2 snapshot (`.dump` diff). The drain does not write this table.
*Recomputed* Objective-1 intersection (`full_population_cohort` →
sig95 ∧ shrunk_mean ≥ 0.02): **post-drain n = 450**, scratch-reverted
(= pre-drain) **n = 431**. The persisted 295 is a frozen 2026-08-15 snapshot;
the 295→431 gap is ~3.5 weeks of maintenance drift, not the drain. **Isolated
drain effect (post-drain 450 vs scratch-reverted 431): +24 entered, −5 left,
426 stable.** All 24 entrants are manifest traders; 3 of the 5 leavers are
manifest traders, the other 2 (`0x741a4410…`, `0xf3011142…`) move because
`full_population_cohort` uses a **pooled** within-trader variance and
empirical-Bayes shrinkage — adding the drained positions shifts those global
parameters and nudges two borderline non-manifest traders out. Both revert
when the manifest reverts (falsifiable test below), so they are drain-caused,
not unaccounted.

**Objective-2 cohort / placebo** — re-ran `capture_predrain_objective2_membership.py`:

| arm | pre-drain | post-drain | entered | left | stable | in manifest |
|---|---|---|---|---|---|---|
| elig_pool (`n_pairs ≥ 10`) | 2,894 | 3,004 | **+110** | 0 | 2,894 | 110/110 (all pre-split position-entry) |
| cohort (`intersection`) | 172 | 180 | **+8** | 0 | 172 | 5/8 directly; 3 via pooled-parameter shift |
| placebo (`match_control`) | 172 | 180 | 26 | 18 | 154 | 7 entrants / 2 leavers directly; the rest are greedy-match reshuffle |

New point estimates (both CIs still span zero, pre and post):
- cohort `measure_oos`: gap 0.027822 → **0.026383**, n_pos 3,981 → 4,058,
  n_surv 143 → 149
- placebo `measure_oos`: gap 0.019890 → **0.020277**, n_pos 2,813 → 2,813,
  n_surv 125 → 129

The placebo churn (26 in / 18 out) and the 3 non-manifest cohort entrants are
**second-order consequences of the manifest flips**: `match_control` is a
greedy 1:1 nearest-neighbour match, so a larger eligible pool + 8 new cohort
members needing matches re-shuffles the whole assignment (deterministic at
seed 42, but not a per-trader mapping); and `compute_cap5_metric`'s pooled
variance / EB shrinkage shift with the added positions. The falsifiable test
confirms every one of these reverts with the manifest.

**Trader-state** — diff of the full 194,724-row dump vs the step-2 baseline:

| column | traders changed | direction |
|---|---|---|
| `geo_resolved_trades_count` | **1,996** | **all increased, 0 decreased** — exactly the 1,996 distinct manifest traders |
| `geo_elo` | **0** | unchanged |
| `geo_elo_active` | **0** | unchanged |
| `geo_accuracy_pool` (Pool C) | **0** | unchanged |
| `resolved_trades_count` (general) | **0** | unchanged ✅ (nothing scheduled recomputes it) |
| `research_excluded` | **0** | unchanged ✅ |

0 traders added / removed. The drain's **direct** write footprint is precisely
`trades.trade_result` (24,390 rows) + `traders.geo_resolved_trades_count`
(1,996 traders, all increases). `geo_elo` / Pool C recompute is deferred to the
next `update_geo_elo` run (daily step 9, 06:00 UTC) — **expected**, flagged
here so the 06:00 log is not misread.

---

## Part 4 — the falsifiable test

Scratch copy of the **post-drain** production DB (SQLite online-backup API,
20.7 GB, `integrity_check` = `ok`). Set `trade_result` back to `'pending'` for
**exactly the 24,390 manifest `trade_id`s** (all 24,390 were non-pending in the
scratch copy beforehand — confirming the drain fully evaluated them; all 24,390
pending afterward; scratch `check_pending_geo` = 24,390, = pre-drain baseline).
Then re-ran the Objective-2 capture, the Objective-1 intersection recompute,
and both controls against the scratch DB.

| baseline | scratch-reverted result | recovered? |
|---|---|---|
| Objective-2 `elig_pool` (2,894 traders) | 2,894, **ordered-identical trader list**, symdiff 0 | ✅ |
| Objective-2 cohort (172 traders) | 172, **ordered-identical**, symdiff 0 | ✅ |
| Objective-2 placebo (172 traders) | 172, **ordered-identical**, symdiff 0 | ✅ |
| cohort `measure_oos` (gap 0.027822, CI, n_pos 3,981, n_surv 143) | **byte-identical** | ✅ |
| placebo `measure_oos` (gap 0.019890, CI, n_pos 2,813, n_surv 125) | **byte-identical** | ✅ |
| 92-pop control (98) | **98** (+ `canonical_population` 7,330, `v2f_population` 7,067, `symmetric_diff` 263 — all match pre-drain) | ✅ |
| 161-pop control (165) | **165** | ✅ |
| Objective-1 intersection | 431 (the isolation reference for the +24/−5 drain effect above) | ✅ (reference established) |

**PASS. The pre-drain baselines are recovered from the manifest alone.** Every
downstream change — including the greedy-match placebo reshuffle and the
pooled-parameter nudges to non-manifest traders — is fully reversible by
reverting the 24,390 manifest rows. The drain touched nothing the manifest
does not capture.

---

## Part 5 — normal operation restored

- Daily maintenance **un-paused**: `crontab - < crontab.pre_drain_20260909.bak`.
  `crontab -l` is now **byte-identical to the pre-drain backup** (diff = no
  difference). Line 3 active again: `0 6 * * *  …/run_daily_maintenance.sh`.
- Next `daily_maintenance` fire: **06:00 UTC** (unchanged schedule). No
  maintenance process running now.
- `polymarket-monitoring` **active**, `polymarket-observer` **active** — never
  stopped, heartbeat current throughout.
- 20 GB scratch DB deleted; disk 1.1 TB free.

### System left in this state
- `check_pending_geo` = **0**; geo/elec resolved non-gap trades: 385,824 won /
  350,839 lost / 0 pending.
- `traders.geo_resolved_trades_count` up for 1,996 traders (all increases).
- `metric_v2f_oos_result` unchanged (`021be40a…`); `metric_v2f_intersection_cohort`
  table unchanged.
- **Anticipated at the next 06:00 maintenance run:** `update_geo_elo` (step 9)
  will bootstrap/recompute `geo_elo` and re-gate Pool C for the affected
  traders — this is the intended downstream settlement, not a regression.
  `audit_invariants` (step 7) `check_pending_geo` should read at or near 0
  (a within-cycle sawtooth is possible per its known design).
- `backfill_trade_results_geo.py` is **still not wired** into
  `daily_maintenance.py` — that is separate follow-up work
  (`2026-09-09-geo-backfill-wiring-decision.md` recommended `--limit 200` as a
  daily top-up *after* this drain; deciding/wiring it is not part of this task).

---

## What was NOT determined

- **The next-maintenance `geo_elo` / Pool C movement.** Predicted (affected
  traders' `geo_elo` recomputed, some crossing `geo_resolved_trades_count ≥ 10`
  into Pool C) but not run here — maintenance was paused, and this task does not
  run `update_geo_elo`. First observable at the 06:00 UTC run.
- **Whether `comprehensive_elo` shifts on Sunday.** Only `analysis/pit_geo_elo.py`
  among analysis modules reads `trade_result`; whether the Sunday
  `recalculate_comprehensive_elo.py` path reaches the flipped rows was not
  traced (carried over from `2026-09-09-geo-drain-blast-radius.md`).
- **The true magnitude of the Objective-1 intersection's routine drift.** The
  295 persisted snapshot is 2026-08-15; the scratch-reverted recompute (431) is
  the 2026-09-09 pre-drain value, but no committed pre-drain Objective-1
  recompute exists, so the 295→431 gap is attributed to "maintenance drift" by
  elimination (the drain effect is isolated at +24/−5), not measured
  per-cause.
- **General `resolved_trades_count` under a future manual stats recompute.**
  Unchanged now (nothing scheduled recomputes it), but the underlying trade
  rows moved, so a future `recalculate_trader_stats.py` / `reconcile_trader_aggregates.py`
  run would raise it for the ~1,996 traders and could then move Pool B
  (`research_excluded`). Latent, not triggered.
- **Materiality of the Objective-2 point-estimate shift** (cohort gap 0.027822
  → 0.026383) to any downstream decision — both CIs span zero before and after;
  significance unchanged, but the effect on a hypothetical re-measured
  headline was not assessed (out of scope — the +0.0316 result of record is
  frozen).

---

*Generated 2026-09-09. Production writes: `trades.trade_result` (24,390 rows,
pending → won/lost) and `traders.geo_resolved_trades_count` (1,996 traders,
increases) via `scripts/backfill_trade_results_geo.py --limit 5000` ×5, no
`--persist`. Crontab edited (maintenance pause) and restored byte-identical.
No monitor/observer/guard/threshold/constant touched. No twice-classifiable or
persistence script run. `metric_v2f_oos_result` sha256
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e` — verified
unchanged at every checkpoint. Falsifiable test: pre-drain baselines recovered
from the manifest alone.*
