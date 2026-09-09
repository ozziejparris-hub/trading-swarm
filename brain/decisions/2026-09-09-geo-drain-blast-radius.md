# 2026-09-09 — Blast-radius audit: the geo pending-results drain

**Read-only audit. No drain, no writes, no wiring.** One write only:
`git rm scripts/compare_trade_evaluators.py` (Oscar-approved retirement, first-repo
`bbca45f`) — see §0.

Basis: `2026-09-09-geo-backfill-wiring-decision.md` (first-repo `28d898b`). The drain
mechanics are settled. This establishes **what changes downstream** and **whether any
subset is consequence-free**.

Tags: **[V]** verified this session (query/file:line given), **[I]** inferred.
Live counts drift; figures are 2026-09-09.

---

## ⛔ STOP CONDITION 1 MET — report and halt

**Part 1 and Part 3 both find the drain would materially change pre-split cohort
definitions.** Per the task's stop rule this makes the drain a **research decision
requiring its own pre-registration, not a maintenance operation.** No verdict on
whether to run it — that is Oscar's. The specifics:

- **8,350** of the 24,390 pending rows sit in **1,898 markets whose `tape_end` is
  before T_split (2026-04-01)** — i.e. inside the canonical pre-split backtest
  population (`backtest_window_sql`). **[V]**
- **4,997** of those pre-split rows are the **entry trade** (`positions.entry_trade_ids[0]`)
  of a geo/elec position, across **737 distinct traders**. Flipping them
  `pending→won/lost` feeds directly into `build_presplit_cohort()` — the Objective-2
  cohort/placebo selector. **[V]**
- **The PIT-legal classifiable population (5,732) grows by ~131 traders** (SQL bound:
  5,751 → 5,882, +2.3%) — 131 traders cross the `n≥M_CHOSEN=10` pre-split bar. Zero
  can leave (the drain only adds `won/lost`). **[V]**
- **Twice-classifiable eligibility grows by ~+43** (SQL bound 1,042 → 1,085). **[V]**
- **5 traders in the persisted 295-row `metric_v2f_intersection_cohort`** (Objective-1)
  have pre-split inputs changed; **13** if post-split flips are included. Membership of
  that persisted table *could* change on a re-run. **[V]**

**STOP CONDITION 2 (a consumer writes to a result-of-record table): NOT met.** No
scheduled consumer of `trades.trade_result` writes to `metric_v2f_oos_result` or
`metric_v2f_intersection_cohort`. Those are written only by an explicit
`trader_skill_metric_v2f.py --persist` run, which is manual and Oscar-gated. The
drain, and every cron/maintenance path it feeds, leaves the +0.0316 result of record
byte-for-byte unchanged. What the drain changes is **what a re-measurement would
return** (§3).

---

## §0 — Retirement of `compare_trade_evaluators.py`

`git rm`'d this task (first-repo `bbca45f`, pushed). One-shot pre-repoint convergence
gate for `8cfeb8e`; the second implementation it compared no longer exists; import
broken since 2026-08-19. Ongoing regression guard is `verify_geo_backfill_repoint.py`.
Full reasoning: `2026-09-09-compare-trade-evaluators-retire.md` (trading-swarm `53b8514`).
No rewrite, no import fix — deleted.

---

## Part 1 — where the 24,390 rows sit relative to T_split

T_split = **2026-04-01 00:00:00**. Pending set = `trade_result='pending' AND
markets.resolved=1 AND gap-clean AND category IN ('Geopolitics','Elections')` =
**24,390 rows / 2,889 markets / 1,996 traders** (`check_pending_geo` predicate). **[V]**

### 1a. By trade timestamp (entry-time anchor)

| bucket | rows | share |
|---|---|---|
| trade ts **before** T_split | **10,372** | 42.5% |
| trade ts **on/after** T_split | **14,018** | 57.5% |

Range 2023-08-02 → 2026-09-04, 0 NULL. **Not overwhelmingly post-split.**

Monthly (trade ts), abbreviated: **[V]**
```
2023: 11    2024-H1: ~55   2024-H2: ~1,600  2025-H1: ~1,475  2025-H2: ~2,850
2026-01: 1,410  02: 1,141  03: 2,592  04: 3,553  05: 4,456  06: 5,607
2026-07: 243   08: 153    09: 6
```
Bulk is 2026-01→2026-06 (18,725 rows, 77%); a long thin tail to 2023. The sharp
drop after 2026-06 is the daily-evaluator gap boundary — recent trades on recently-
resolved markets still get caught by other paths; the older backlog does not.

### 1b. By market `tape_end` (the PIT-correct anchor the thesis uses)

`tape_end` = `MAX(trades.timestamp)` per market. `backtest_window_sql` and
`build_presplit_cohort` both classify pre/post on `tape_end`, **not** entry time.

| bucket | pending rows | markets |
|---|---|---|
| `tape_end` **≤ T_split** (pre-split pop) | **8,350** | 1,898 |
| `tape_end` **> T_split** (post-split pop) | 16,040 | 991 |

Markets-by-`tape_end` month: a long tail from 2023-10, ~57 markets/month through
2025, rising to 279 (2026-03) / 339 (2026-05), then 81 / 42 / 5 for 2026-07/08/09. **[V]**

### 1c. Position-entry subset (what the thesis harness actually joins on)

Every thesis consumer joins `trades t ON t.trade_id = json_extract(p.entry_trade_ids,'$[0]')`
`AND t.trade_result IN ('won','lost')`. So only a pending row that **is a position's
first entry trade** can change a positions-based consumer.

| | position-entry pending rows | traders | markets |
|---|---|---|---|
| pre-split `tape_end` | **4,997** | **737** | 1,788 |
| post-split `tape_end` | 6,665 | 1,319 | 920 |
| **total** | **11,662** | — | — |

The other **12,728** pending rows are not any position's `entry_trade_ids[0]`
(additional entries, exit trades, or trades with no reconstructed position). Those
still count toward `trades`-level aggregates — `geo_resolved_trades_count`,
`update_geo_elo`, `trader_statistics` win-rate — but not the positions harness.

### 1d. Verdict for Part 1

**The rows are NOT overwhelmingly post-split.** 8,350 pending rows in 1,898
pre-split-`tape_end` markets; 4,997 are position entry trades across 737 traders.
The blast radius does **not** collapse to the post-split window. The pre-split
cohort machinery is in scope. → STOP CONDITION 1.

---

## Part 2 — consumers of `trades.trade_result`

Enumerated across both repos (`grep -rn trade_result --include=*.py`). Filter
`trade_result IN ('won','lost')` (pending excluded) is the universal pattern, so a
`pending→won/lost` flip **adds** rows to nearly every consumer.

### 2a. Scheduled (automatic propagation after a drain)

| consumer | schedule | what it computes | drain effect |
|---|---|---|---|
| `audit_invariants.py` `check_pending_geo` | daily step 7 | the backlog gauge itself | count drops by the drained amount (that is the point) |
| `reconcile_geo_resolved_counts.py` | daily steps 6 & 22 | recomputes `traders.geo_resolved_trades_count` = `COUNT(DISTINCT market_id)` won/lost geo | **rises** for the ~1,996 affected traders |
| `update_geo_elo.py` | daily step 9 | bootstraps `geo_elo` for traders newly having qualifying geo trades (`:82-87`); recomputes `geo_elo` for traders whose qualifying count now exceeds stored (`:101-110`); writes `geo_elo`,`geo_elo_active`,`geo_resolved_trades_count` (`:293`); `refresh_pool_c()` (`:218,331`) | **`geo_elo` recomputed** for affected traders; **Pool C (`geo_accuracy_pool`) re-gated** — traders crossing `geo_resolved_trades_count ≥ 10` (`POOL_C_MIN_RESOLVED_TRADES`) **enter Pool C** |
| `evaluate_new_trader_results.py` | daily step 21 | flagged/watched pending evaluator; also `SET resolved_trades_count` (`:72`) for the traders it touches | overlaps the drain only for flagged traders; recomputes general `resolved_trades_count` **only** for its own flagged/watched population |
| `apply_full_elo_modifiers.py` | daily step 24 | reads `resolved_trades_count` for gating (`:131-141`); operates on `comprehensive_elo` | indirect — sees whatever `resolved_trades_count`/ELO the steps above left |
| `snapshot_elo_scores.py` | daily step 27 | writes `elo_snapshots` (date, `geo_elo`,`geo_elo_active`,`comprehensive_elo`,tier) | the **next daily snapshot captures the shifted `geo_elo`/tier** — a time series, not a frozen result |
| `recalculate_comprehensive_elo.py` | **Sunday 03:00** (`run_sunday_elo.sh`) | full comprehensive-ELO recompute | **[I]** among `analysis/*.py` only `pit_geo_elo.py` reads `trade_result` directly; whether the Sunday recompute path reaches flipped rows was **not** established here (see "what was not determined") |
| `monitoring/database.py`, `trader_statistics.py` | live monitor | win/loss tallies, `win_rate` | live-path, recomputes from `trade_result` as trades resolve; drain-flipped rows fold in on next touch |

**`resolved_trades_count` (general, all-category) — the Pool B / `research_excluded`
gate (`update_research_exclusions.py` `resolved_trades_count >= 20`).** The drain
updates **`geo_resolved_trades_count` only**, never the general column. Nothing
scheduled recomputes general `resolved_trades_count` for the non-flagged population
(`recalculate_trader_stats.py` and `reconcile_trader_aggregates.py` are **not** in
`daily_maintenance.py` or `crontab`). So **Pool B / `research_excluded` is not
automatically moved by the drain** — it becomes a *latent* change that a future
`recalculate_trader_stats.py` run would realize. **[V]**

### 2b. Manual only (change on next re-run, never automatically)

`trader_skill_metric_v2f.py` / `v2.py` (Objectives 1 & 2; result-of-record on
`--persist`), all `directional_skill_*.py` (PIT-legal pool, twice-classifiable,
persistence test, diagnostic, null-calibration, reps-bh), `verify_dilution_guard.py`,
`analysis/pit_geo_elo.py` + `validate_pit_geo_elo.py`, `layer0_forward_accuracy.py`,
`layer0b_deconfound.py`, `calibrate_composite_threshold.py`,
`track2_ci_power_diagnostic.py`, `discovery_gap_thesis_intersection.py`,
`elo_formula_audit.py`, `geo_elo_derivation_audit.py`, all `characterize_*.py`,
`recalculate_trader_stats.py`, `reconcile_trader_aggregates.py`,
`backfill_trade_results.py`, trading-swarm `geo_elo_oos_validation.py`. **[V]**

### 2c. Structurally unaffected

- The **92-market pending-resolution population** and the **161 no-FIFO-close
  population** — disjoint mechanisms (orphan SELLs / all-entry-pending market
  definition), confirmed in `2026-08-19-pending-invariant-regression.md`. The
  no-FIFO-close count should stay **exactly** unchanged; a move there would signal
  something unexpected.
- `metric_v2f_oos_result`, `metric_v2f_intersection_cohort`, `metric_v2f_findings`,
  `metric_v2f_consensus_result`, `directional_skill_pit_exploratory_result/membership`
  — **no writer runs without an explicit manual invocation**. The stored +0.0316 is
  immutable regardless of the drain.

### 2d. Which consumers would give a different answer

**Different after the drain (automatically, next maintenance/Sunday):**
`check_pending_geo`, `geo_resolved_trades_count`, `geo_elo`/`geo_elo_active`,
`geo_accuracy_pool` (Pool C membership), `elo_snapshots` (next snapshot),
possibly `comprehensive_elo` (unresolved).

**Different only on a manual re-run:** every thesis measurement in §2b — most
consequentially `build_presplit_cohort` → Objective-2 cohort/placebo,
`directional_skill_pit_legal_pool` → the 5,732, `directional_skill_twice_classifiable`
→ 753/146/607.

**Structurally unaffected:** the 92 and 161 populations; general `resolved_trades_count`
/ Pool B (until a manual stats recompute); all frozen result-of-record tables.

---

## Part 3 — the thesis measurements specifically

All figures are SQL **bounds** on the *classifiable* inputs (won/lost entry trades,
`tape_end` split, `n≥10`). They do **not** re-run the bootstrap/skill tests, so they
bound — not predict — membership change. "CC's 2 placebo survivors" refers to
`2026-08-19-pending-invariant-regression.md` Q6 (`0x54b5eacb…`, `0x5cfd8811…`).

| population | persisted? | current | after drain (bound) | Δ | can leave? |
|---|---|---|---|---|---|
| **PIT-legal classifiable (5,732)** — `n≥10` pre-split positions | JSON artifact only | 5,751 (my count) | **5,882** | **+131 traders enter** | no |
| **twice-classifiable (753)** — classifiable pre & post | JSON artifact only | 1,042 (loose bound) | **1,085** | **≈ +43** | no |
| **persistence cohort (146) / comparison (607)** | JSON artifact only | 146 / 607 | not derivable without re-run | bounded above by the +131 / +43; BH-skill test would re-sort membership | cohort: yes (a member could fall out if new positions lower their pre-split skill signal) |
| **Objective-2 cohort (148 qualifying / 120 surviving)** | **NOT persisted** | 120 | not derivable without re-run | 737 traders' `build_presplit_cohort` inputs change: **90 already ≥10 (stats shift), 131 cross into ≥10, 516 stay <10 (inert)** | yes |
| **Objective-2 matched placebo (110)** | **NOT persisted** | 110 | not derivable without re-run | `match_control` pool (`elig_pool`, `n_pairs≥10`) gains ≥131 members and 221 members' profiles shift → **different greedy match → different placebo set** | yes |
| **Objective-1 `metric_v2f_intersection_cohort` (295)** | **YES (PK trader)** | 295 | not derivable without re-run | **5 members pre-split-affected; 13 affected incl. post-split.** Membership *could* change on a re-run | yes |

### Detail: `metric_v2f_intersection_cohort` (295) — the pre-split-affected members

`0x3e887528098ca040fa89f832bce604d99987df66`,
`0x6bcc22657cb3ffbcc3fe5bd018f037057f35f8b2`,
`0xac163cc68039474d4060c2ac750b3d6a70fa4f44`,
`0x3f216ba174ce77d2b891cf3a2c4747ca06cf3bce`,
`0xc97b0b2a2547bb3ed57167092ef8a6e816c347e5`. **[V]**
(`0x6bcc2265…` and `0xc97b0b2a…` are 2 of the 3 pre-split-cohort traders named in the
08-19 regression doc — consistent.)

### Detail: `directional_skill_pit_exploratory_membership` (2026-09-06 groups, persisted)

| group | size | pre-split-affected | any-affected |
|---|---|---|---|
| raw_cohort | 711 | 5 | 8 |
| raw_placebo | 711 | 16 | 18 |
| bh_cohort | 504 | 3 | 6 |
| bh_placebo | 504 | 12 | 14 |
**[V]** — placebo arms are more exposed than cohort arms, on both sides.

### The result of record (+0.0316) and a re-measurement

The stored `metric_v2f_oos_result` (`cohort` gap 0.03160, CI [−0.0088, 0.0710],
n=3,032/120; `placebo` 0.01271, n=2,569/110) **is permanent and is never recomputed**
(Oscar, 2026-08-21). The drain does not touch it.

**But a future re-measurement of the same quantity would change**, through two
independent channels:
1. **Pre-split (membership):** +131 traders into `elig_pool`, 221 members' `n_pairs`/
   `ci_lo_t`/`shrunk_mean` shifted → `intersection` (cohort) and `match_control`
   (placebo) both re-sort.
2. **Post-split (measured positions):** `measure_oos` loads each retained trader's
   post-split positions with `trade_result IN ('won','lost')`. **6,665** post-split
   position-entry pending rows across 1,319 traders would newly enter — directly
   moving `n_positions`, `point_gap`, and the CI for whatever cohort/placebo set is
   measured.

So a second figure measured after the drain would be measured against a **moved
baseline**, and would not be comparable to +0.0316 as a like-for-like re-test unless
the pre-drain state is reconstructed first (§5).

### The asymmetry (as the task asks)

- **Objective 1** — `metric_v2f_intersection_cohort` is persisted at trader level.
  After a drain + re-run, an exact membership diff is possible: which of the 295
  left, which entered. **Verifiable.**
- **Objective 2** — cohort (148/120) and placebo (110) membership **was never
  persisted** (named in MASTER_HANDOVER as the mechanism behind the 2026-08-16
  UNREPRODUCIBLE verdict; `characterize_no_fifo_close_markets.py:228`: "no persisted
  membership snapshot as of 2026-08-18"). After a drain, **there is no way to
  establish what the pre-drain cohort/placebo were** — only the 295-superset proxy.
  **Not verifiable after the fact unless persisted first (§5).**
- **PIT-legal / twice-classifiable / persistence** — exist only as `--json-out`
  artifacts. Diffable **iff** the pre-drain artifacts are regenerated and archived
  now, and re-generated after. Otherwise lost.

---

## Part 4 — can it be separated?

### Candidate A — drain only post-T_split (`tape_end > T_split`) rows

Covers **16,040 rows** (6,665 position-entry, 1,319 traders). Leaves **8,350
pre-split rows** pending. **The remainder GROWS:** **72% of the pre-split pending
rows are `background_backfill` provenance** (6,043 / 8,350) — old trades on
long-resolved pre-split markets, ingested "today" for newly-discovered traders and
hard-coded `trade_result='pending'` by `background_backfill_worker.py`. That channel
is live and unbounded (the geo-backfill decision doc: 106 new traders in one 24 h
window). Post-split-only is **not** a stable partition — it leaves a growing,
thesis-relevant pre-split remainder. **Rejected.**

### Candidate B — drain only rows in markets outside `backtest_window_sql()`'s population

**Empty set.** Within resolved, gap-clean, geo/elec markets, every market's `tape_end`
falls in either the pre-split window (`VERY_EARLY..T_split`) or the post-split window
(`T_split..open`). There is no geo/elec subset outside the canonical population. **[V]**
**Not a separation.**

### Candidate C — drain only rows for traders outside every named cohort

The named cohorts are small (295 persisted; 146/607/120/110 not persisted). Excluding
their rows is possible in principle for the 295, impossible to do reliably for the
un-persisted 148/120/110/146/607 (you cannot exclude a set you cannot enumerate).
And even a perfect exclusion leaves Candidate A's growing pre-split remainder and
still shifts the **5,732 PIT-legal classifiable** population (a selection *pool*, not
a cohort — its 131 new entrants are by definition "outside every named cohort" today).
**Does not achieve consequence-free.**

### Candidate D — drain only rows that cannot move a trader past a threshold

Of the 737 pre-split-affected traders: **516 stay < M_CHOSEN=10** pre-split
classifiable even after the drain → their flips are **inert** for Objective-2
eligibility and the 5,732. Draining **only their rows** = **1,142 pre-split
position-entry rows** (+ their non-position rows) + all 16,040 post-split rows.

But: (i) it leaves the 221 threshold-relevant traders' pre-split rows (90 already
≥10, 131 crossing) pending — exactly the rows that matter; (ii) those + new
`background_backfill` arrivals keep the remainder growing; (iii) the post-split half
(16,040) still moves `measure_oos` for 1,319 traders including cohort/placebo members
(§3). **Reduces but does not eliminate** thesis impact, and leaves a growing
remainder.

### Verdict for Part 4

**No clean separation exists.** Every partition that spares the thesis populations
leaves a pre-split remainder that (a) is thesis-relevant and (b) grows via the
`background_backfill` ingest channel. Per the task's own caution, **a partial drain
with a growing remainder is plausibly worse than either extreme** — it perturbs the
measurements *and* fails to stop the bleed *and* makes the eventual full reconciliation
harder because the population will have moved twice.

The only genuinely consequence-free-for-the-thesis action is: **drain nothing on the
pre-split side until a pre-registration covers it**, and separately fix the ingest
hard-code (`background_backfill_worker.py`, out of scope here — see the geo-backfill
decision doc §4) so the pre-split remainder stops growing.

---

## Part 5 — verification (propose only)

### Persist BEFORE any drain (this is the 2026-08-16 lesson)

1. **Raw drain manifest.** `SELECT trade_id, trader_address, market_id, timestamp,
   trade_result, data_source FROM trades WHERE <check_pending_geo predicate>` →
   timestamped CSV/JSON under `data/characterizations/`. Plus the derived
   `position_id` list (the 11,662 entry-trade hits) and each row's pre/post-split-by-
   `tape_end` label. Without this the "what did it touch" question is unanswerable
   afterward.
2. **Objective-2 cohort + placebo membership.** Run `trader_skill_metric_v2f.py`
   **without `--persist`**, capture `build_presplit_cohort()['elig_pool']`,
   `['intersection']`, the `match_control()` output, and `measure_oos` per-trader
   position lists for both arms → JSON artifact. This is the snapshot that was never
   taken.
3. **PIT-legal / twice-classifiable / persistence.** Re-run
   `directional_skill_pit_legal_pool.py`, `directional_skill_twice_classifiable_population.py`,
   `directional_skill_persistence_test.py` to fresh `--json-out` artifacts and
   **commit them** (git, trading-swarm `brain/agent-outputs/`), tagged "pre-drain
   baseline".
4. **Persisted tables snapshot.** Copy `metric_v2f_intersection_cohort`,
   `metric_v2f_oos_result`, `directional_skill_pit_exploratory_membership/result`,
   `backtest_population_snapshots` rows to a dated backup table or dump.
5. **Full DB backup** — `scripts/backup_database.py` (WAL-safe online backup +
   `PRAGMA integrity_check`), per CLAUDE.md.
6. **Trader-state baseline.** `SELECT address, geo_elo, geo_elo_active,
   geo_resolved_trades_count, geo_accuracy_pool, resolved_trades_count,
   research_excluded FROM traders` → dated dump, for the 1,996 affected + a control
   sample.

### Measure AFTER, and what "unchanged" must look like

| population / value | query / script | expected if the drain did only what's intended |
|---|---|---|
| `check_pending_geo` | `characterize_pending_invariant_regression.py` | drops by exactly the drained row count (won+lost+invalid); invalid≈0 |
| 92-market pending-resolution pop | `characterize_pending_resolution_inconsistency.py` | **does not grow** (clearing pending can only move markets out) |
| 161 no-FIFO-close pop | `characterize_no_fifo_close_markets.py` | **exactly unchanged** — disjoint mechanism; any move = investigate |
| `metric_v2f_intersection_cohort` (295) | diff persisted table vs re-run | membership diff limited to the 13 affected addresses ± their neighbours; the 282 unaffected members **unchanged** |
| `metric_v2f_oos_result` stored row | `SELECT * ` | **byte-identical** (never recomputed) — if it changed, something ran `--persist` |
| Objective-2 re-measurement (cohort/placebo gap) | `trader_skill_metric_v2f.py` no-persist, vs the §5.2 baseline | gap moves; **the move must be fully attributable** to the manifest rows (recompute cohort/placebo on the pre-drain `trade_result` values from the manifest and confirm you recover the baseline) |
| PIT-legal classifiable | `directional_skill_pit_legal_pool.py` vs baseline artifact | grows by ~131; the 131 entrants are all traders whose manifest rows pushed them ≥10 — enumerable and checkable one by one |
| twice-classifiable / persistence cohort / comparison | respective scripts vs baseline artifacts | deltas within the §3 bounds; every entrant/leaver traceable to manifest rows |
| general `resolved_trades_count` / Pool B | `SELECT` vs §5.6 dump | **unchanged** until a deliberate `recalculate_trader_stats.py`; if it moved, an unscheduled stats recompute ran |
| `geo_elo` / Pool C | `SELECT` vs §5.6 dump | changes confined to the 1,996 affected traders + Pool C entrants crossing `geo_resolved_trades_count≥10`; **no unaffected trader's `geo_elo` moves** |
| `elo_snapshots` | compare pre/post snapshot dates | tier changes only for affected traders |

### The falsifiable "it did only what was intended" test

Reconstruct the pre-drain state by taking the current DB and setting
`trade_result='pending'` (in a scratch copy / CTE, not production) for exactly the
manifest `trade_id`s, re-run every §5.2–5.3 script, and confirm you recover the
committed baselines within tolerance. If you cannot recover the baseline from the
manifest alone, the drain touched something the manifest does not capture — halt.

---

## What was NOT determined

- **Exact Objective-2 cohort/placebo membership change.** Bounded (737 inputs change;
  90 stats-shift, 131 cross, 516 inert), not computed — that needs a
  `build_presplit_cohort()` + `match_control()` re-run, out of scope for a read-only
  audit. The `match_control` greedy match is sensitive to any `elig_pool` change, so
  even the 90 "stats-shift" traders can flip the placebo set.
- **Whether `recalculate_comprehensive_elo.py` (Sunday) reaches flipped rows.** Only
  `analysis/pit_geo_elo.py` among `analysis/*.py` references `trade_result`; the
  Sunday recompute's actual read path into `comprehensive_elo` was not traced. If it
  does, `comprehensive_elo` and the Sunday `elo_snapshots` shift automatically too.
- **My SQL population bounds vs the scripts' exact numbers.** PIT-legal: my 5,751 vs
  the documented 5,732 (boundary `<` vs `≤` on `tape_end`, live drift, and the
  scripts' `entry_avg_price`/harness filters I approximated). Twice-classifiable: my
  1,042 is a loose `n≥10 both sides` bound, not the 753 (which adds the BH-skill
  classification). Directions and magnitudes hold; absolute post-drain counts need
  the real scripts.
- **The 12,728 non-position-entry pending rows' downstream reach.** They don't touch
  the positions harness; they do feed `geo_resolved_trades_count` / `update_geo_elo`
  / win-rate. Their per-consumer effect was not separately quantified.
- **Materiality in dollars / positions** for the affected cohort members (how much of
  each trader's footprint the pending rows represent). Row counts only.
- **`resolution_date` vs `tape_end` disagreement** for the 1,898 pre-split markets
  (the project's known LATE-biased detection bug, O-36) — this audit anchors on
  `tape_end` throughout, per the canonical definition, and did not cross-check
  `resolution_date`.
- **Whether `verify_dilution_guard.py` / `dilution_guard_signals` would shift** — it
  consumes `trade_result` and `tape_end` but is unscheduled; not quantified.

---

*Generated 2026-09-09. Sources: live read-only queries against
`data/polymarket_tracker.db` (20 GB); `scripts/backfill_trade_results_geo.py`,
`scripts/directional_skill_pit_legal_pool.py`, `scripts/trader_skill_metric_v2f.py`
(`build_presplit_cohort`/`match_control`/`measure_oos`),
`scripts/persist_directional_skill_pit_exploratory.py`,
`monitoring/column_definitions.py` (`backtest_window_sql`,
`BACKTEST_WINDOW_*`, `POOL_C_*`, `GEO_RESOLVED_TRADES_COUNT_SQL`),
`scripts/update_geo_elo.py`, `scripts/update_research_exclusions.py`,
`scripts/daily_maintenance.py` STEPS, `scripts/run_sunday_elo.sh`, `crontab -l`;
persisted tables `metric_v2f_intersection_cohort`, `metric_v2f_oos_result`,
`directional_skill_pit_exploratory_membership/result`, `backtest_population_snapshots`;
`2026-09-09-geo-backfill-wiring-decision.md`, `2026-08-19-pending-invariant-regression.md`,
`2026-08-19-geo-backfill-wiring-prereg.md`, `2026-09-06-directional-skill-persistence-test-run-2.md`,
`2026-09-06-directional-skill-exploratory-custody.md`. One write: `git rm
scripts/compare_trade_evaluators.py` (first-repo `bbca45f`). No drain, no wiring, no
production write.*
