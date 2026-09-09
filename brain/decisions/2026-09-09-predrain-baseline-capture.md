# 2026-09-09 — Pre-drain baseline capture (step 2 of 3): ⛔ STOP

**Outcome: HALTED. The persistence test does not reproduce its committed
2026-09-06 result, and the fresh directional baselines cannot be captured —
the population has already moved (+19 PIT-legal classifiable traders,
5,732 → 5,751) between 2026-09-06 and 2026-09-09 with NO drain having run.**

Per the task's stop rule this is a finding: *the drain is not the first thing
to have changed the population*. The baseline is therefore **incomplete** and
step 3 (the drain) must not proceed on it.

Read-only throughout. Two new read-only capture scripts added (first-repo 281c0f9)
(`scripts/capture_predrain_geo_drain_manifest.py`,
`scripts/capture_predrain_objective2_membership.py`). No trade / trader /
market row modified. `--persist` never passed. **`metric_v2f_oos_result`
sha256 `021be40a…` — byte-identical at session start and session end.**

Basis: `2026-09-09-geo-drain-blast-radius.md` (ebdf1f1) Part 5. Step 1 (ingest
fix) is first-repo `7ae0f2a`.

---

## The finding (why this halts)

**[V]** `directional_skill_pit_legal_pool.py` re-run fresh, 2026-09-09:

| metric | 2026-09-06 committed | 2026-09-09 fresh | Δ |
|---|---|---|---|
| n_presplit_markets | 7,297 | 7,330 | **+33** |
| n_presplit_positions | 204,963 | 205,548 | **+585** |
| n_traders_any_presplit_position | 18,478 | 18,481 | +3 |
| **n_clearing_min (the "5,732")** | **5,732** | **5,751** | **+19** |
| raw_skilled | 1,494 | 1,507 | +13 |
| bh_skilled | 1,178 | 1,191 | +13 |
| bh_survived | 504 | 510 | +6 |

**[V]** `directional_skill_twice_classifiable_population.py` **hard-STOPs**
(`EXPECTED_CLASSIFIABLE = 5732`, `scripts/…:41,81-83`): *"[STOP] classifiable
count 5751 != Part B's reported 5732 -- contradicts the Part B doc."* Exit 1.
So the fresh **753 / 146 / 607** populations and the fresh persistence test
**cannot be produced** — the chain is guard-blocked.

**[V]** Persistence test re-run against the **frozen 2026-09-06 input JSONs**
(populations read from the committed artifacts, not recomputed):

| quantity | committed 2026-09-06 | re-run 2026-09-09 (frozen inputs) | reproduces? |
|---|---|---|---|
| `real_persistence_ci` (cohort) | 0.3699 [0.2945, 0.4521] n=146 | 0.3699 [0.2945, 0.4521] n=146 | ✅ **yes** — but only because cohort BH classification is *read from* Part B's frozen data |
| cohort raw / bh skilled | 63 / 54 | 63 / 54 | ✅ |
| comparison raw / bh skilled | 154 / 113 | **153 / 117** | ❌ |
| `real_comparison_ci` | 0.1862 [0.1549, 0.2175] | **0.1928 [0.1614, 0.2241]** | ❌ moved |
| S4 aggregate cohort point_gap / n_pairs | 0.011526 / 3,025 | **0.011904 / 3,039** | ❌ moved |
| S4 aggregate comparison point_gap / n_pairs | 0.020983 / 10,827 | **0.020772 / 10,867** | ❌ moved |
| named outcome cell | A1 × B2 | A1 × B2 | ✅ (verdict unchanged) |

Even with membership frozen, the comparison group's BH classification and the
S4 aggregate `n_pairs` have drifted — because those are recomputed from the
current DB (`load_post_split_positions` → post-split positions with
`trade_result IN ('won','lost')`), and more post-split rows have flipped
pending → won/lost over the 3 days.

**Driver (diagnosed, [V]):** routine daily-maintenance pipeline over 2026-09-07
→ 09-09 — `evaluate_new_trader_results.py` (flagged-trader pending evaluator,
daily step 21), `fast_resolution_check.py` landing new resolutions, category
backfill reclassifying markets. 8 pre-split geo/elec markets have
`resolution_recorded_at >= 2026-09-06`. **Not** today's step-1 ingest fix:
`n_clearing_min` was already **5,751** in this morning's blast-radius run
(ebdf1f1), which predates `7ae0f2a`'s deploy, and it is unchanged at 5,751 now
— the +19 step landed sometime in the 09-06→09-09 window and is currently
stable, not still climbing.

---

## Ordered checklist — what was captured, what was not

| # | item | status | artifact |
|---|---|---|---|
| **1** | **WAL-safe backup** | ✅ **PASS** | `backups/markets_20260909_200015.db` (`8999bd9c…`) |
| **2** | **drain manifest** | ✅ done | `data/characterizations/predrain_geo_drain_manifest_20260909T200756Z.json` (`bd0b4374…`) |
| **3** | **Objective-2 cohort/placebo membership** | ✅ done + reproducibility-proven | `…/predrain_objective2_membership_20260909T200842Z.json` (`4e063b41…`) + reproduction run `…T200951Z.json` (`08db7d67…`) |
| **4** | **fresh directional baselines** | ⛔ **BLOCKED** — pit_legal_pool captured; twice_classifiable + persistence_test guard-blocked by the 5,732 mismatch | pit_legal_pool: `…/predrain_directional_skill_pit_legal_pool_20260909T201031Z.json` (`e69646b7…`); frozen-input persistence re-run: `…/predrain_persistence_test_frozen0906inputs_20260909T201536Z.json` (`0a37ebdc…`) |
| **5** | **persisted-table snapshots** | ✅ done (6 tables) | `data/characterizations/predrain_table_snapshots_20260909T201245Z/` — `metric_v2f_intersection_cohort.sql` (295 rows, `46652139…`), `metric_v2f_oos_result.sql` (2, `0b320296…`), `metric_v2f_findings.sql` (2, `b87a35f4…`), `directional_skill_pit_exploratory_result.sql` (4, `26d0bce6…`), `directional_skill_pit_exploratory_membership.sql` (2,430, `afa75c02…`), `backtest_population_snapshots.sql` (4,712, `ad68be80…`) |
| **6** | **trader-state baseline** | ✅ done (full table, 194,724 rows) | `data/characterizations/predrain_trader_state_20260909T201256Z.csv` (`562ae75b…`) |
| **7** | **disjoint-population controls** | ✅ done | `…/pending_resolution_inconsistency_20260909T201350Z.json` (`e656dc3e…`); `…/no_fifo_close_markets_20260909T201444Z.json` (`793ef6b0…`) |

### 1 — Backup (PASS, per the stop rule its integrity check must pass — it did)

- Path: `/home/parison/projects/first-repo/backups/markets_20260909_200015.db`
- Size: **19,748.1 MB** (`scripts/backup_database.py` report) / 20,707,409,920 bytes on disk
- `scripts/backup_database.py`'s built-in `PRAGMA integrity_check` → **`ok`**
  (the script prints `[OK]` and exits 0 only on `'ok'`; exit code **0**).
- **Independent re-verify** (`sqlite3 <backup> "PRAGMA integrity_check"`) →
  **`ok`**. Backup `trades` row count = live `trades` row count = **13,627,405**
  (exact).
- Duration: START 2026-09-09T20:00:15Z → END 20:03:48Z = **213 s (~3m33s)**.
- **flock guard in play:** the run was wrapped in `flock -n 200` on
  `run_database_backup.sh.lock` — the *same* lock the cron wrapper
  `run_database_backup.sh` uses. Confirmed the wrapper's guard by reading it
  (`flock -n 200`, non-blocking → skip-and-log on contention;
  `2026-08-26-backup-guard-and-scheduling.md`). No cron backup was running
  (last completed 2026-09-09T03:23:58Z); current time ~20:00 UTC, next cron
  fire 03:00 UTC — no collision window.

### 2 — Drain manifest

`predrain_geo_drain_manifest_20260909T200756Z.json` — one row per pending
trade_id, each with `trade_id, trader_address, market_id, timestamp,
trade_result, data_source`, the derived `position_id(s)` where the trade is a
position's `entry_trade_ids[0]`, and a `split_side` (`pre_split` /
`post_split`) by market `tape_end` vs T_split.

- **manifest_rows = 24,390 = distinct pending trade_ids = live `check_pending_geo`
  = 24,390** (asserted equal; **matches**).
- distinct traders 1,996; distinct markets 2,889.
- position-entry rows 11,661; **1 trade** is `entry_trade_ids[0]` of 2 positions
  (captured in `position_ids`).
- pre_split 8,350 (4,997 position-entry); post_split 16,040 (6,664).

### 3 — Objective-2 cohort / placebo membership (the snapshot never taken)

`predrain_objective2_membership_20260909T200842Z.json`, via
`build_presplit_cohort()` / `match_control()` / `measure_oos()` imported
unchanged from `trader_skill_metric_v2f.py`, SEED=42.

- **elig_pool** (n_pairs ≥ M_CHOSEN=10): **2,894 traders** (full list + per-trader
  n_pairs / ci_lo_t / shrunk_mean where present).
- **cohort** (`intersection`: sig95 ∧ shrunk_mean ≥ 0.02): **172 traders** (full
  list). `measure_oos`: point_gap **0.027822**, CI [−0.005012, 0.062007],
  n_positions **3,981**, n_surviving_traders **143**. Per-trader post-split
  position lists captured (market_id, outcome, entry_avg_price, entry_timestamp,
  trade_result, won).
- **placebo** (`match_control`, seed 42): **172 traders** (full list).
  `measure_oos`: point_gap **0.019890**, CI [−0.016872, 0.055596],
  n_positions **2,813**, n_surviving_traders **125**. Per-trader post-split
  positions captured.
- **Reproducibility:** the capture was run **twice** in separate processes
  (`PYTHONHASHSEED` unset / randomized each). elig_pool (2,894), cohort (172),
  placebo (172): **byte-identical membership, symdiff 0**; identical measure_oos
  gaps. `match_control()` is deterministic since first-repo `42b14fc`
  (`sorted()` on every set-derived sequence) — confirmed. `PYTHONHASHSEED`
  recorded in the artifact as `unset`.
- **oos_result guard:** stored `metric_v2f_oos_result` sha256 **identical
  before and after** the capture, inside the script and independently
  (`021be40a…` at session start and end). The frozen result of record —
  cohort `3032 / 120 / 0.0315983581`, placebo `2569 / 110 / 0.0127065403`,
  spec `SKILLV2F-2026-08-15-v1`, commit `eaeabbc` — is untouched.

**Note on 172 vs the "148 / 120":** the captured cohort (172) is larger than
the 2026-08-15 result-of-record cohort (120) and the 2026-08-19 "155 / 126".
This is the *expected* drift of an un-persisted population over weeks of live
data — precisely why this snapshot had to be taken. The 172 is the correct
pre-drain comparand; the +0.0316 result of record is a permanent frozen
artifact, not a live quantity, and a re-measurement would be measured against
this 172-cohort baseline.

### 5 — Persisted-table snapshots

Six `.dump` files (re-loadable INSERT statements) under
`predrain_table_snapshots_20260909T201245Z/`, each with a recorded row count
and sha256 (table above).

### 6 — Trader-state baseline

Full `traders` dump, **194,724 rows** (not a sample), columns `address,
geo_elo, geo_elo_active, geo_resolved_trades_count, geo_accuracy_pool,
resolved_trades_count, research_excluded`. Baseline aggregates for the future
diff: geo_elo set 11,151; geo_elo_active set 11,151;
geo_resolved_trades_count > 0 → 32,144; geo_accuracy_pool = 1 (Pool C) →
4,276; resolved_trades_count ≥ 20 → 30,003; research_excluded = 0 → 39,658.

### 7 — Disjoint-population controls (must NOT move after the drain)

| population | committed-doc value | **2026-09-09 pre-drain baseline** |
|---|---|---|
| 92-market pending-resolution (`characterize_pending_resolution_inconsistency.py` `pending_inconsistency_count`) | ~92 (series 88→103→92) | **98** — canonical_pop 7,330, v2f_pop 7,067, symdiff 263 |
| 161 no-FIFO-close (`characterize_no_fifo_close_markets.py` `no_fifo_close_count`) | ~161 | **165** — cohort overlap 7 traders / 25 rows / 20 markets |

Both already sit a few above their last-doc values (consistent with the same
maintenance-driven drift). These are the recorded pre-drain baselines; after
any drain the 92-pop must **not grow** and the 161-pop must be **exactly
unchanged**.

---

## Is the blast-radius Part 5 falsifiable test now possible?

The test: *restore the manifest rows to `pending` in a scratch copy, re-run
every baseline script, confirm the committed baselines are recovered.*

**Partially.**

- ✅ **Possible for**: `check_pending_geo` count; the Objective-1
  `metric_v2f_intersection_cohort` (295, persisted + snapshotted); the
  Objective-2 cohort/placebo (172/172, now captured with per-trader positions
  and proven reproducible from SEED); `metric_v2f_oos_result` (frozen, hashed);
  `pit_legal_pool` (fresh baseline captured); trader-state
  (geo_elo/Pool C/geo_resolved_trades_count); the 92 and 161 controls.
- ❌ **NOT possible for the 753 / 146 / 607 persistence populations.**
  `directional_skill_twice_classifiable_population.py` and the fresh
  `directional_skill_persistence_test.py` are hard-blocked by
  `EXPECTED_CLASSIFIABLE = 5732` while the live population is 5,751. No
  committed fresh baseline for these exists as of this capture, and one cannot
  be produced without changing that guard. The frozen-input persistence re-run
  (`…frozen0906inputs…`) shows the comparison arm and S4 aggregate have already
  drifted independent of any drain, so even it is not a stable reference.

**Net:** the falsifiable test can verify the manifest, Objective 1, Objective 2,
and trader-state effects of a drain. It **cannot** verify the drain's effect on
the persistence populations, because those are already moving on a
2–3-day timescale from routine maintenance and their tooling refuses to run
off the 09-06 pin.

---

## Recommendation (Oscar's call — not executed)

Do **not** run the drain against this baseline. Two ways forward:

1. **Re-pin, then capture-and-drain in a tight window.** Update the committed
   `directional_skill_pit_legal_pool` / `twice_classifiable` /
   `persistence_test` reference artifacts and their `EXPECTED_*` guards to the
   current 5,751-based state, re-run the full directional chain fresh to
   establish a **new committed baseline**, then re-run this capture and the
   drain back-to-back (same maintenance day, ideally with daily maintenance
   paused) so maintenance drift cannot be confused with drain effect.
2. **Scope the drain's success criterion to the manifest only.** Accept that
   the directional populations drift ~±20 per 3 days from
   `evaluate_new_trader_results` + resolutions + category backfill, treat that
   as baseline noise, and judge the drain solely by the falsifiable
   manifest-restore test on Objectives 1 & 2 + the 92/161 controls staying
   put. The persistence populations would then be explicitly out of scope for
   drain verification.

Either way, the ingest fix (`7ae0f2a`) already stops the *dominant* inflow, so
there is no urgency forcing the drain onto a shaky baseline.

---

## What was NOT determined

- **The exact date the 5,732 → 5,751 step landed** (somewhere 2026-09-06 →
  2026-09-09-morning; stable since). Not decomposed per daily-maintenance run —
  `trades` has no `updated_at`, so which run flipped which pre-split pending
  rows is not reconstructable.
- **Whether any of the +585 newly-classifiable pre-split positions came from
  step-1's ingest evaluation.** The population was already 5,751 during the
  pre-`7ae0f2a` blast-radius run, so the ingest fix is not the *cause* of the
  5,732→5,751 step; but `background_backfill` inserts since deploy that landed
  won/lost on pre-split geo/elec markets (86,735 such rows total, timestamp of
  evaluation not stored) cannot be individually attributed.
- **The fresh 753 / 146 / 607 values and fresh persistence CIs.** Guard-blocked;
  not produced. The frozen-input re-run gives cohort persistence 0.3699 (reads
  frozen), comparison 0.1928 (drifted from 0.1862), S4 cohort n_pairs 3,039
  (from 3,025).
- **Materiality of the drift to the A1×B2 verdict.** The named outcome cell is
  unchanged (A1×B2) in the frozen-input re-run, but a fresh run could differ;
  not established.
- **Whether the 92-pop (98) and 161-pop (165) current values are themselves
  drift since their last committed characterization** or within normal
  non-monotonic noise — the doc's own series (88→103→92) suggests the latter,
  but not confirmed for this specific reading.

---

*Generated 2026-09-09. Read-only capture. Artifacts under
`data/characterizations/` (committed) and `backups/` (not committed — 20 GB).
Scripts: `scripts/capture_predrain_geo_drain_manifest.py`,
`scripts/capture_predrain_objective2_membership.py` (new, read-only),
`scripts/backup_database.py`, `scripts/directional_skill_pit_legal_pool.py`,
`scripts/directional_skill_twice_classifiable_population.py`,
`scripts/directional_skill_persistence_test.py`,
`scripts/characterize_pending_resolution_inconsistency.py`,
`scripts/characterize_no_fifo_close_markets.py`,
`scripts/trader_skill_metric_v2f.py`. `metric_v2f_oos_result` sha256
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e` unchanged
session start → end. No `--persist`. No drain. No row modified.*
