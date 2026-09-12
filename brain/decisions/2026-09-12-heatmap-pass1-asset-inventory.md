# Heatmap Pass 1 of 5 — Asset Inventory

**Date:** 2026-09-12
**Scope:** inventory only — what exists and what it is proven to do. No ranking, no
combinations, no external research, no promise-assessment. Those are passes 2-5.

---

## Sweep scope (read this before trusting anything below as complete)

**Decision docs.** All decision-doc history lives in
`/home/parison/trading-swarm/brain/decisions/` — first-repo has **no** `brain/decisions/`
directory at all (confirmed empty/nonexistent). **244** dated `.md` files there, spanning
**2026-03-19 → 2026-09-11**, plus two undated `archive/MASTER_HANDOVER_*.md` files
(2026-03-17, 2026-05-20) and a `gate-sets-2026-09-01/` data subdirectory (not a decision
doc — a relevance-classifier gate-set data artifact, not opened this pass, see Residual).

Of the 244+2, **24 were read in depth** this pass: all 7 reachable MASTER_HANDOVERs
(archive 2026-03-17, and 2026-06-10, 2026-08-15, 2026-09-05, 2026-09-06 from the main
directory — 2026-05-20 archive not read), the two FABLE cross-repo audits
(2026-07-07, 2026-07-10), and 15 more selected by grepping all 244 files for a fixed
marker set (CONDEMNED, defect, zero caller, never used/read/exercised, shelved, inert,
abandoned, PROVEN, VALIDATED, and named-asset strings) and prioritizing the
highest-hit-density and most-recent documents. **189 of 244 files hit at least one
marker**; the full per-file hit list was produced but is not reproduced here. **~220 of
244 were not read even in excerpt** — this is the largest coverage gap in this pass.
Three large primary pre-registrations in particular are known only via handover
restatement, not read directly: `2026-09-05-copy-trade-decay-prereg.md` (1065 lines),
`2026-08-21-discovery-gap-closure-prereg.md` (1883 lines — the result-of-record's own
founding document), `2026-09-06-directional-skill-persistence-prereg.md` (665 lines).

**Code.** first-repo `scripts/` (147 files), `monitoring/` (38), `analysis/` (26),
top-level only — **211 files**, all swept for docstring/purpose + caller-count via
repo-wide grep. `scripts/archive/` (67), `scripts/quick_fixes/` (3),
`scripts/simulation/` (15) — **85 files explicitly not read** (treated as archive/one-off,
see Residual). trading-swarm `scripts/` (6) and `orchestrator/` top-level (4) also swept
— **221 files total**. `orchestrator/permissions/` and `orchestrator/task_templates/`
(trading-swarm) not swept. `tests/` not inventoried file-by-file as its own asset class,
only cross-referenced from the code it validates.

**Database.** All **63 tables** in `data/polymarket_tracker.db` audited: row count,
key columns, writer file(s), reader file(s), scheduled-vs-one-off character, last-write
freshness where a timestamp column exists.

**Safety check (stop condition).** `metric_v2f_oos_result` sha256 verified unchanged
throughout this pass, both before and after the DB audit:
`021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`. No writes were made
to the database or to any production table during this sweep.

**Method note.** The 43 one-off `metric_v2*`/`layer0*` pre-registration/findings/amendment
tables are grouped into two summary entries rather than 43 individual ones (D9, D10)
because the DB audit found them to share one pattern exactly: each is written solely by
its own generating script, with no programmatic reader, by design — a one-time
output-of-record for a pre-registered statistical test, queried ad hoc by a human for a
decision doc. This is explicitly **not** the same failure mode as `elo_snapshots` (B5
below) and the two are not to be conflated. The two exceptions that ARE reused by later
scripts (`metric_v2f_oos_result`, `metric_v2f_intersection_cohort`) get their own entries.

---

## Class 1 — DATA

### D1. `trades` table
**Location:** `data/polymarket_tracker.db`, table `trades`.
**What it is:** The raw trade tape — every recorded buy/sell, per trader, per market,
with price and timestamp.
**Capability statement:** Answers what a specific trader bought or sold, at what price,
and when, for any market in the database — the substrate every skill/edge measurement in
the project is built on.
**Validation status:** PROVEN as the base ingestion layer — live 15-minute polling
(`monitoring/monitor.py`, per `CLAUDE.md`), 13,703,185 rows.
**Coverage:** 13,703,185 rows. Known collection gap: 2026-04-07 → 2026-04-18 (near-zero
collection, 1-6 trades/day vs 500+ normal), flagged not deleted — `markets.trade_gap_flag
= 1` for markets resolving during that window (250 flagged as of the 08-16
reproducibility audit: 166 April-gap + 84 O-37-quarantine).
**Used for:** every downstream skill/edge/ELO measurement in the project.
**Never used for:** N/A — foundational table.
**Known limits:** `is_taker` column has zero maker-side rows database-wide (621,350
labeled trades, all `is_taker=1`) — likely structural (a CLOB taker's wallet sends the
settling transaction; a resting maker order may never generate one of its own), root
cause not established (`MASTER_HANDOVER_2026-09-05.md` §6).

### D2. `positions` table
**Location:** `data/polymarket_tracker.db`, table `positions`; writers
`monitoring/position_tracker.py`, `monitoring/background_pnl_worker.py`.
**What it is:** FIFO-matched trader positions aggregated from the trade tape.
**Capability statement:** Answers a trader's closed/open position-level P&L and entry
price for any (trader, market) pair.
**Validation status:** PROVEN — `analysis/pit_positions.py`'s point-in-time
reconstruction validated against it at 1.2M items, zero unexplained divergence
(`MASTER_HANDOVER_2026-08-15.md` §5).
**Coverage:** 9,083,987 rows.
**Used for:** every position-level skill/edge measurement (v2-v2f lineage, directional
skill, copy-trade decay).
**Never used for:** recovering orphan-SELL markets (see known limits).
**Known limits:** Orphan SELL trades with no matching BUY are silently dropped
(`monitoring/position_tracker.py:330`) — 166 markets as of 2026-08-19, status
MATERIAL-OPEN (not fixed): affects who qualifies for a cohort but, for the v2f cohort
specifically, cannot touch the edge of anyone who does qualify (verified: 100%
pre-split by construction). Two specific traders remain UNKNOWABLE-status for
qualification (`MASTER_HANDOVER_2026-08-15.md` §6 item 8).

### D3. `markets` table
**Location:** `data/polymarket_tracker.db`, table `markets`.
**What it is:** Market metadata: category, resolution status/date/outcome, and (for
migrated writers) resolution provenance columns.
**Capability statement:** Answers a market's category, resolution status, and resolution
provenance (source/timestamp/detail) — where the canonical write path has been adopted.
**Validation status:** PARTIAL — `trg_resolved_no_unresolve` trigger verified live and
non-tautologically (inside rolled-back transactions); only 3 of 13 originally-mapped
resolution writers have migrated to the canonical path (see O5 below).
**Coverage:** 845,414 rows.
**Used for:** every market-level filter/population definition in the project.
**Never used for:** N/A — foundational table.
**Known limits:** `category` is `'Unknown'` on 99.9% of sweep-resolved markets
(214,155/214,413) — the classifier meant to fix this is abandoned pending a formal
decision (§3.11(a) per memory); `resolution_date` has ~11% logically-impossible values
(O-36), `tape_end` used as the validated workaround instead; 195,625/214,413 (91.2%) of
sweep-resolved markets are permanently invisible to
`requeue_resolved_market_traders.py`'s `last_checked`-gated query because
`mark_market_resolved()` never sets that column — NOT FIXED, affects 8,077 open
positions across 1,983 traders (`MASTER_HANDOVER_2026-09-05.md` §6).

### D4. `order_book_snapshots` (B4)
**Location:** `data/polymarket_tracker.db`, table `order_book_snapshots`.
**What it is:** Daily order-book capture for a subset of markets.
**Capability statement:** Answers a market's bid/ask order-book state at capture time —
used for STR-002/STR-003 signal-market fill simulation.
**Validation status:** PROVEN live — liveness summary guards against silent-empty
capture (`MASTER_HANDOVER_2026-08-15.md` §5).
**Coverage:** 5,384 rows, 366 markets — 3.57% of Geopolitics+Elections markets (per
`2026-09-05-canonical-skill-metric-design.md` §4), disjoint from the directional-skill
cohort.
**Used for:** STR-002/STR-003 signal-market fill simulation.
**Never used for:** any skill/edge metric to date — explicitly excluded from the
canonical skill metric design's components (§4 of that doc) for coverage reasons; would
be an upgrade path if coverage ever broadened.

### D5. `event_cluster_labels` (B5)
**Location:** `data/polymarket_tracker.db`, table `event_cluster_labels`.
**What it is:** A single snapshot (2026-07-24) labeling which markets belong to the same
real-world event.
**Capability statement:** Answers whether two markets are the same underlying event —
enables event-level rather than market-level analysis.
**Validation status:** PROVEN — 3 structural checks passed (0 merge errors across 3,343
clusters), external audit found 0 false splits (O-46 cleared).
**Coverage:** 4,712/4,712 rows; `neg_risk` native grouping covers 40.1% (1,891
markets/522 groups), remainder (143 markets) hand-labeled, all standalone.
**Used for:** `scripts/verify_dilution_guard.py`, `scripts/own_market_calibration.py`,
`scripts/trader_skill_metric_v2b.py`.
**Never used for:** anything beyond those 3 scripts; single frozen snapshot, never
refreshed since 2026-07-24 — new markets since then are not clustered.

### D6. `backtest_population_snapshots`
**Location:** `data/polymarket_tracker.db`, table `backtest_population_snapshots`.
**What it is:** A single frozen population snapshot (`bt_pop_2025-11-01_v1`, 4,712
markets) generated by the canonical `backtest_window_sql()` (see V4).
**Capability statement:** Defines a fixed, reproducible reference population of markets
as of a given window, for other measurements to match against.
**Validation status:** PROVEN — generated by the validated canonical function.
**Coverage:** 4,712 rows, single snapshot.
**Used for:** `tests/test_backtest_window_population.py`.
**Never used for:** re-snapshotting at a later date — this is the only snapshot that
exists.

### D7. `metric_v2f_oos_result` — the result of record
**Location:** `data/polymarket_tracker.db`, table `metric_v2f_oos_result` (2 rows).
**What it is:** The pinned, permanent out-of-sample test of the project's core thesis.
**Capability statement:** Answers — as of 2026-08-21, permanently, by explicit decision —
whether skilled traders' market-relative edge is distinguishable from zero
out-of-sample, for the cohort defined at `T_split=2026-04-01`.
**Validation status:** PROVEN as a record (pinned by Oscar's explicit decision
2026-08-21, verified untouched by any 2026-09-06 write, `generator_commit eaeabbc`).
The *result itself*: cohort mean edge **+0.0316**, CI **[−0.0088, +0.0710]**, n=3,032
positions (148 qualifying, 120 surviving); placebo +0.0127, CI [−0.0210, +0.0461].
**Verdict: NULL — CI does not exclude zero — but directionally positive and
underpowered, not evidence against the thesis** (`MASTER_HANDOVER_2026-08-15.md` §2).
**Coverage:** n=3,032 positions / 120 traders, T_split=2026-04-01.
**Used for:** the project's headline thesis test; the anchor every later arc
(directional skill, copy-trade decay, own-market calibration) is framed against.
**Never used for:** recomputation — it is frozen by decision, not because it can't be
rerun.
**Known limits:** the placebo underpinning its interpretation was built with the
pre-fix, non-deterministic `match_control()` (see V6) and is **not reconstructable**
from its recorded seed — this does not change the pinned result, but means the
placebo comparison cannot be independently reproduced today.

### D8. `metric_v2f_intersection_cohort`
**Location:** `data/polymarket_tracker.db`, table `metric_v2f_intersection_cohort`
(295 rows).
**Capability statement:** Answers exactly which 295 trader addresses constitute the
Objective-1 cohort superset feeding the result of record.
**Validation status:** PROVEN as a persisted membership list (unlike Objective 2, whose
148/120/148 trader addresses were never persisted — a gap named in
`MASTER_HANDOVER_2026-08-15.md` §6 item 9, meaning the headline result's own exact
population cannot be diffed against a later re-run at the same granularity D8 offers
for Objective 1).
**Used for:** `scripts/own_market_calibration.py`, `scripts/copy_trade_decay_diagnostic.py`,
`scripts/capture_predrain_objective2_membership.py`,
`scripts/characterize_orphan_sell_scope.py`,
`scripts/characterize_legendary_overlap_recompute.py`,
`scripts/characterize_no_fifo_close_markets.py`.
**Never used for:** anything requiring the Objective-2 (post-split) population, which
was never persisted at this granularity.

### D9. `metric_v2` → `v2f` lineage: pre-registration / findings / amendment tables
**Location:** `data/polymarket_tracker.db` — 41 tables:
`metric_v2_calibration_curve`, `metric_v2_comparison_findings`,
`metric_v2_pre_registration`, `metric_v2_trader_results`, `metric_v2b_amendment`,
`metric_v2b_findings`, `metric_v2b_gate_results`, `metric_v2b_trader_results`,
`metric_v2b_weighting_comparison`, `metric_v2c_amendment`, `metric_v2c_findings`,
`metric_v2c_placebo`, `metric_v2c_tradeoff_curve`, `metric_v2d_amendment`,
`metric_v2d_cohort_sanity`, `metric_v2d_findings`, `metric_v2d_gate_results`,
`metric_v2d_threshold_candidates`, `metric_v2d_turnover`, `metric_v2e_amendment`,
`metric_v2e_correction_sweep`, `metric_v2e_coverage_simulation`, `metric_v2e_findings`,
`metric_v2e_threshold_candidates`, `metric_v2f_amendment`, `metric_v2f_cost_floor`,
`metric_v2f_findings`, `layer0_position_results`, `layer0_pre_registration`,
`layer0_stratum_summary`, `layer0b_calibration_curve`, `layer0b_pre_registration`,
`layer0b_stratum_summary`, `layer0c_calibration_curve`, `layer0c_pre_registration`,
`layer0c_stratum_summary`, `price_convention_audit_elo_comparison`,
`price_convention_audit_paired_price_tests`, `price_convention_audit_pre_registration`,
`geo_elo_derivation_audit`, `geo_elo_derivation_audit_findings`.
**What it is:** The full audit trail of six successive skill-metric iterations
(v2 → v2b → v2c → v2d → v2e → v2f) plus the Layer 0/0b/0c precursor lineage and two
independent audit trails (price-convention, geo_elo-derivation), each written solely by
its own one-off generating script.
**Capability statement:** Each table answers a specific, already-closed question about
one iteration's design/gate/findings — e.g. `metric_v2d_gate_results` answers whether
that iteration's threshold candidates passed its pre-registered gate. Collectively they
are the reproducibility record of how the project arrived at `metric_v2f_oos_result`.
**Validation status:** N/A (these are records of already-completed one-off tests, not
instruments to validate) — largest table `layer0_position_results` at 341,865 rows,
last write 2026-08-15.
**Coverage:** varies per table, see raw DB audit for individual counts.
**Used for:** the historical reconstruction of the v2f lineage; `layer0c_*` feeds
`layer0c_corrected_metric.py`.
**Never used for:** any live/scheduled process — none of these 41 tables has a
programmatic reader outside its own generating script; this is working-as-designed
(see Method note above), not the `elo_snapshots` failure pattern.
**Known limits:** `price_convention_audit_*` (3 of the 41, up to 8,021 rows) have zero
readers found anywhere, last generated 2026-08-15 — pure audit trail.

### D10. Layer 0 exploratory / dilution-guard family
**Location:** `directional_skill_pit_exploratory_membership`,
`directional_skill_pit_exploratory_result`, `dilution_guard_signals`,
`dilution_guard_signals_guard_diffs`, `str002_signals`, `insider_signals`,
`insider_clusters`, `trader_categories`, `elo_shadow`, `relevance_slug_staging`.
**Capability statement:** Each answers a narrow, named question tied to one arc
(directional-skill exploratory edge, dilution-guard verification, STR-002/STR-003
signals, insider-activity detection, category classification, the comprehensive-ELO-bug
dry-run delta, relevance-classifier staging).
**Validation status:** UNEVEN — see known limits; not uniformly validated.
**Coverage / freshness:**
- `str002_signals`: 227 rows, last write 2026-09-04.
- `elo_shadow`: 53,380 rows, last write 2026-07-14, read by 3 one-off
  dry-run/delta scripts tied to the comprehensive-ELO-bug project.
- `relevance_slug_staging`: 70,253 rows, last write 2026-09-01.
- `trader_categories`: 7,518 rows, writer `analysis/analysis_scheduler.py` (name
  implies scheduled) but **last write 2026-03-30** — over 5 months stale; 2 readers
  still exist.
- `insider_signals` / `insider_clusters`: writer `scripts/detect_insider_activity.py`
  last wrote signals 2026-05-02 (4+ months stale); `insider_clusters` has only 1 row
  ever. **`insider_signals`/`insider_clusters` are actively read by
  `monitoring/system_observer.py`, which is live** — a live component polling tables
  nothing has fed in 4+ months.
- `dilution_guard_signals` (7 rows) / `dilution_guard_signals_guard_diffs` (63 rows):
  the only file referencing either anywhere in both repos is
  `scripts/verify_dilution_guard.py` — presumed self-contained writer+reader, but the
  exact write statement was not confirmed this pass (method gap, see Residual).
**Used for:** each table's own named one-off arc.
**Never used for:** anything beyond that arc, except the `insider_signals`/
`insider_clusters` live-read noted above.
**Known limits:** the `insider_signals` live-read-of-stale-data pattern is the clearest
second instance, beyond `elo_snapshots`, of a live consumer polling a dead pipeline —
flagged here, not diagnosed further (out of scope for Pass 1).

### D11. External dataset: `vgregoire/polymarket-users` parquets
**Location:** external, referenced in `2026-09-06-external-dataset-scoping-and-prereg-amendment.md`.
**What it is:** Per-trader, whole-history aggregate statistics from an external
Polymarket dataset.
**Capability statement:** Could answer trader-level aggregate stats (e.g. win rate,
volume) for the population as of before 2026-03-29, as an external cross-check.
**Validation status:** N/A — scoped and explicitly rejected for the one purpose it was
evaluated for.
**Coverage:** whole-history per-trader aggregates only; **no per-position records at any
granularity**; coverage ends **2026-03-29**.
**Used for:** nothing yet — evaluated once, found unusable for its intended purpose.
**Never used for:** increasing N on the directional-skill persistence test — verdict
**NO**, for two independently sufficient reasons: no per-position granularity, and
coverage ends before `T_split` (2026-04-01) regardless of granularity.
**Known limits:** as above — structurally unable to support any position-level or
post-2026-03-29 measurement.

---

## Class 2 — VALIDATED INSTRUMENTS

### V1. `analysis/pit_geo_elo.py` — point-in-time geo_elo reconstruction
**Location:** first-repo `analysis/pit_geo_elo.py`; validation harness
`scripts/validate_pit_geo_elo.py`.
**What it does:** Reconstructs what `geo_elo`/`geo_elo_active` would have been computed
as, as of any historical point in time.
**Capability statement:** Answers, for a point-in-time-correct (PIT-legal) cohort
definition, what a trader's geo-ELO state was at any past date — avoiding look-ahead
leakage.
**Validation status:** PROVEN — 3,229/3,229 exact match vs production-at-now
(`MASTER_HANDOVER_2026-08-15.md` §5). **By design, faithfully reproduces `geo_elo`'s own
bugs** — this is a PIT-correctness tool, not a fix for the condemned scoring formula
(C1).
**Coverage:** 3,229/3,229 validated positions.
**Used for:** the directional-skill PIT-legal pool (5,732 traders,
`MASTER_HANDOVER_2026-09-06.md` §3.2).
**Never used for:** automated regression — `validate_pit_geo_elo.py` itself has zero
callers found anywhere, so nothing re-checks this proof stays true as the codebase
changes.

### V2. `analysis/pit_positions.py` — point-in-time position reconstruction
**Location:** first-repo `analysis/pit_positions.py`; validation harness
`scripts/validate_pit_positions.py`.
**Capability statement:** Answers what a trader's position state (open/closed,
FIFO-matched) was at any historical point in time.
**Validation status:** PROVEN — 1.2M items, zero unexplained divergence
(`MASTER_HANDOVER_2026-08-15.md` §5).
**Used for:** PIT-legal cohort construction across the directional-skill and v2f arcs.
**Never used for:** automated regression — same caveat as V1, zero further callers on
the validation harness itself.

### V3. `monitoring/price_history.py` — `price_at()` / `resolve_token_id()`
**Location:** first-repo `monitoring/price_history.py`; test
`tests/test_price_history_price_at.py`.
**Capability statement:** Answers what a market's price was at any given timestamp — for
use as an entry/exit/delayed-copy price in edge measurements.
**Validation status:** PARTIAL — all 5 edge cases proven on the primary CLOB source;
cross-source stratified agreement only **73.1%** (vs a 90% pre-registered bar),
characterized as **primary-with-fallback**, not strong-primary
(`MASTER_HANDOVER_2026-08-15.md` §5).
**Coverage:** primary CLOB source, cross-checked on a stratified sample at 73.1%
agreement.
**Used for:** `scripts/copy_trade_decay_diagnostic.py` (delay-curve measurement),
`scripts/own_market_calibration.py` (price-weighted calibration), `backtest_window_sql()`
population definition.
**Known limits:** age/liquidity-dependent; specifically degrades for old/thin markets.

### V4. `column_definitions.py` — `backtest_window_sql()` / canonical backtest population
**Location:** first-repo `monitoring/column_definitions.py` §6.
**Capability statement:** Defines, deterministically, which markets qualify for a
backtest population as of a given split date — `tape_end`-anchored, half-open intervals,
INNER JOIN so zero-trade markets drop structurally.
**Validation status:** PROVEN as the canonical definition, adopted project-wide after
O-36/O-45; frozen reference snapshot `bt_pop_2025-11-01_v1` (D6).
**Known limits:** **the v2f pipeline itself does not call this function** — it computes
`tape_end` independently and anchors on `positions` rather than `markets`/`trades`,
producing a 254-market symmetric difference vs the canonical population at `T_split`
(6,842 canonical vs 6,588 v2f-implicit). Characterized as PERSISTENT-BOUNDED
(pending-resolution component, 88→103→92, non-monotonic) and MATERIAL-OPEN (no-FIFO-close
component, 166→161→161) — neither touches the measured out-of-sample edge, for different
reasons, but both remain open, unfixed as of the most recent handover read
(`MASTER_HANDOVER_2026-08-15.md` §6 item 8).

### V5. Two-way trader×market clustered bootstrap / cap5 weighting / EB-shrinkage
**Location:** not a standalone module — implemented inline/duplicated across ≥18 scripts
(`trader_skill_metric_v2*.py`, `directional_skill_*.py`, `layer0b/0c_*.py`,
`own_market_calibration.py`, `skilled_presence_causal_test.py`,
`copy_trade_decay_diagnostic.py`, `track2_ci_power_diagnostic.py`, and others).
**Capability statement:** Produces a statistically valid confidence interval for a
mean-edge-type statistic under trader×market cross-clustering, using cap5 weighting
(each (trader, market) pair weighted `min(n_positions, 5)`) and empirical-Bayes
shrinkage toward the population mean.
**Validation status:** PROVEN — nominal coverage check, 5.56% vs nominal 5% target
(`MASTER_HANDOVER_2026-08-15.md` §1). cap5 itself was chosen because `sigma2_between` is
exactly zero for market/log/sqrt/cap3 weighting and only turns on at cap5 — the clean
knee.
**Used for:** every metric_v2-lineage CI, `own_market_calibration.py`, directional-skill
and copy-trade-decay diagnostics.
**Known limits:** **no single canonical library file exists** — this is convention,
reimplemented per-script, not shared code; a correctness fix in one site does not
propagate to the other ~17.

### V6. `match_control()` / `match_markets()` — matched placebo-cohort construction
**Location:** first-repo `scripts/trader_skill_metric_v2f.py:279` and
`scripts/skilled_presence_causal_test.py`; test
`tests/test_match_control_determinism.py`.
**Capability statement:** Constructs a matched comparison/placebo cohort (matched on
position count, market breadth, activity period — NOT edge-selected) against a treatment
cohort, for null-comparison in edge/skill measurements.
**Validation status:** PARTIAL, with a dated fix. **Was not determined solely by its
`seed` argument until 2026-09-06** (first-repo `42b14fc`): `cohort_traders`/
`elig_traders` are Python sets, iterated directly before shuffling, so output depended
on process-level `PYTHONHASHSEED`, randomized fresh per process by default. Fixed via
`sorted()` in place of raw set iteration at both order-dependent points; proven by
`tests/test_match_control_determinism.py` (8 fresh-process runs across varying
`PYTHONHASHSEED`, asserted identical). **This is the second named mechanism (alongside
background-backfill drift) behind the 2026-08-16 UNREPRODUCIBLE verdict.**
**Critical caveat:** every placebo built **before** the fix — explicitly including the
2026-08-15 result-of-record placebo (D7) and the 2026-09-06 exploratory placebo — is
**not reconstructable** from its recorded seed and was **not** recomputed, overwritten,
or otherwise touched.
**Used for:** `metric_v2f_oos_result`'s placebo, the 2026-09-06 exploratory edge
measurement, `skilled_presence_causal_test.py`.
**Never used for:** re-deriving the pre-fix placebos — explicitly declined.

### V7. Directional-skill harness (Gómez-Cram randomized-direction sign-flip benchmark)
**Location:** distributed across the 2026-09-06 directional-skill script family
(first-repo, exact module names not individually confirmed this pass — see Residual).
**Capability statement:** Answers whether a cohort of traders calls the *direction* of
an event better than chance, holding their actual markets/timing/prices/sizes fixed and
randomizing only buy/sell direction — isolating directional skill from execution/timing
skill.
**Validation status:** PROVEN, with a specific positive result.
- Null calibration: per-trader classification well-calibrated at ~5% under a
  zero-skill-by-construction population (`2026-09-06-directional-skill-null-calibration.md`,
  first-repo `f3cb201`).
- REPS-BH effect isolation: falsified the hypothesis that the BH=0 zero-skill result was
  a `REPS`-driven artifact — exactly zero in all 36 tested cells (3 synthetic draws × 4
  REPS values × 3 groups), zero spread.
- Real run (Amendment 2026-09-06b, outcome A1×B2): persistence rate **37.0%
  BH-adjusted, CI [0.2945, 0.4521]** (146-trader pre-split-BH-skilled cohort) vs
  **18.6%, CI [0.1549, 0.2175]** (607-trader comparison group) — gap holds across all 5
  pre-specified activity strata (11-27pp higher in every one).
**Coverage:** 5,732 PIT-legal classifiable traders; 753 with ≥10 post-split resolved
positions; 146 cohort / 607 comparison.
**Used for:** the 2026-09-06 directional-skill persistence test.
**Never used for:** source-of-profit decomposition (component b of the restated
3-part thesis) or capturability (component c — that's the copy-trade-decay question,
D-adjacent); Components 2/3 (absolute/relative earliness) of the canonical skill metric
design remain untested (`MASTER_HANDOVER_2026-09-06.md` §9).
**Known limits:** clearing the formal A1 null (fixed at exactly 0%) is a low bar by
construction — the substantive evidence is the ~2x separation, not the formal
classification alone. Secondary comparison against Gómez-Cram's external 44% benchmark
is unresolved (CI straddles it — expected at N=146, not a failure). No trader×market
clustering in the pooled aggregate test (caveat carried forward, not fixed). ~0.00067
p-value floor at 1,500 reps with ~15% of traders pinned.

### V8. `scripts/own_market_calibration.py` — price-weighted market calibration slope
**Location:** first-repo `scripts/own_market_calibration.py`.
**Capability statement:** Answers whether the market's own price is a calibrated
probability at a given lead-time-to-resolution, price-weighted (not entry-weighted),
for the canonical Geo/Elec population.
**Validation status:** PROVEN as a working instrument — produced a specific,
reproducible result (logistic recalibration slope >1 at every tested lead time, falling
from ~1.29 near resolution to ~1.14 at days-to-weeks out). The instrument's own
integrity check (`metric_v2f_oos_result` sha256) is built into its stop condition.
**Coverage:** 9,739 canonical Geo/Elec markets.
**Used for:** the own-market calibration premise test (2026-09-10, first-repo `b81e2f6`
/ trading-swarm `bdaa5b4`).
**Known limits:** anchors lead-time on `tape_end` (O-36 workaround), inheriting that
anchor's own limits; deviations from calibration found were concentrated at price
extremes (~1-2pp, cost-floor scale, not large-effect) — a null-leaning result, not a
defect in the tool itself.

---

## Class 3 — BUILT BUT NEVER EXERCISED

### B1. `analysis/composite_skill_score.py`
**Location:** first-repo `analysis/composite_skill_score.py` (906 lines); sole entry
point `UnifiedELOSystem.get_composite_skill_score()` in
`analysis/unified_elo_system.py:4047`; a duplicate copy exists in
`docs/elo_system_reference.py` (also uncalled).
**What it would do:** An 8-dimension, 100-point composite skill score (ELO, forecasting
calibration, execution quality via regret analysis, consistency, behavioral profile,
network independence, contrarian bonus, copy-trader penalty).
**Capability statement (if exercised):** Would answer a trader's blended skill rank
across 8 named dimensions in one 0-100 score.
**Validation status:** UNVALIDATED / dead. Added commit `b11b42d`, 2025-12-05.
`get_composite_skill_score()` has **zero callers anywhere in either repo** (exhaustive
grep, `2026-09-05-canonical-skill-metric-design.md` §0).
**Contradiction found (flagged per task instructions):** the archive
`MASTER_HANDOVER_server-pre-setup-1.md` (2026-03-17) shows Phase 3b composite scores
**ACTIVE with real output** — 13,021 traders scored — several months after the module's
2025-12-05 addition. Its caller was removed at an **undated point between March and
September 2026**; the exact decommission commit is not established by anything read this
pass.
**Never used for:** anything since (at least) some point pre-September 2026; explicitly
**not** reused in the canonical skill metric replacement design — "flagged, explicitly
out of scope — not reused, not repaired; named here specifically so it is not
'discovered' again as if new" (`2026-09-05-canonical-skill-metric-design.md` §5).
**Known limits:** explicitly cited as "the exact pattern the M6 precedent warned
about" — i.e. a recognized recurring failure mode in this project (build a composite,
lose its caller), not a one-off.

### B2. `elo_snapshots` table
**Location:** `data/polymarket_tracker.db`, table `elo_snapshots`; writer
`scripts/snapshot_elo_scores.py` (a live `daily_maintenance.py` step).
**What it is:** A daily historical snapshot of every Pool C trader's geo-ELO state.
**Capability statement (if exercised):** Could answer a Pool C trader's
geo_elo/geo_elo_active/tier trajectory at any of 70 recorded historical dates.
**Validation status:** UNVALIDATED as a live-consumed asset — the data itself is
internally audited [V] (`2026-09-11-elo-tier-causal-test-and-elo-snapshots-inventory.md`
Part 2), but nothing in the live pipeline reads it.
**Coverage:** 232,536 rows, 70 distinct dates, 2026-06-11 → 2026-09-11 (93 calendar
days), **NOT continuous — 7 gaps**, largest 15 days (2026-07-24 → 2026-08-08, which
subsumes two previously-named outage dates and more). 6,149 distinct traders ever
snapshotted; median 46 / mean 37.8 snapshots per trader; 3,547 (58%) have ≥30 recorded
points. `bot_type` is 100% NULL by construction (Pool C membership requires
`bot_type IS NULL`, so a bot-flagged trader can never appear). `comprehensive_elo`:
0.32% (747/232,536) sit at the exact schema default 1500.0 — the rest are "not obviously
uncomputed" but "has a value" is not proof of "was computed."
**Used for:** written daily, but read only by two **dormant** one-off scripts —
`scripts/verify_dilution_guard.py` (real query, validates a position/tier reconstruction
against 30 recorded dates) and `scripts/validate_pit_geo_elo.py` (real queries, dated
2026-07-21) — neither is in `daily_maintenance.py` or crontab. **Zero references found
in the trading-swarm repo.**
**Never used for:** anything in the live pipeline. This is the canonical instance of
"written daily, nothing live reads it."

### B3. `timing_score` / `calculate_timing_quality`
**Location:** first-repo, computed weekly; role split across two contexts.
**What it is:** A relative entry-percentile computation for a trader's position, per
market.
**Capability statement:** Answers how early a trader entered a position relative to
other participants in the same market (peer-ranking, not resolution-timeline).
**Validation status:** PARTIAL — live and computed weekly (98.6% clean for the
2026-09-05 handover's cohort), but its original consumption role (an ELO-bonus
contributor) is dead — **inert since `W_BEH=0`** (Stage 0b, 2026-07-12).
**Coverage:** 98.6% clean for the reference cohort measured.
**Used for:** historically, the ELO behavioral bonus (now inert, see B5).
**Never used for (as of this pass):** its **repurposed** role as "relative earliness,"
component 3 of the proposed canonical skill metric (`analysis/skill_signal.py`, "naming
for review, not a commitment") — designed but that module does not yet exist; the
function itself is reused as-is, not rewritten, but not yet wired into anything live in
that new role.
**Known limits:** per the canonical metric design's own assessment, whether "relative
earliness" and "absolute earliness" (a separate, untested component) are empirically
redundant for this population is an explicitly reasoned-not-tested judgment (§3 of
`2026-09-05-canonical-skill-metric-design.md`).

### B4. ELO behavioral bonus (`calculate_behavioral_elo_bonus`)
**Location:** first-repo, kelly=40/patience=30/timing=30 weighting, ±100pt range.
**Capability statement (if exercised):** Would adjust a trader's comprehensive ELO by up
to ±100 points based on Kelly-criterion alignment, patience, and timing quality.
**Validation status:** UNVALIDATED-as-live — dormant, never called by current writers,
inert since `W_BEH=0` (2026-07-12).
**Used for:** historically produced ELO adjustments before the weight was zeroed.
**Never used for:** anything currently — `W_BEH=0` means it contributes zero regardless
of the underlying scores' values.

### B5. `kelly_alignment_score`, `patience_score` (columns + writers)
**Location:** first-repo, live write path (columns still written weekly).
**Capability statement (if exercised):** Would measure Kelly-criterion sizing
discipline and patience (holding-period behavior) as skill-adjacent signals.
**Validation status:** TESTED AND FOUND NULL — distinct from a CONDEMNED defect. Stage
0b found these null/negligible as ELO contributors; neither Della Vedova nor Gómez-Cram
motivates a sizing-discipline or trading-frequency dimension as operative for the
restated thesis (`2026-09-05-canonical-skill-metric-design.md` §3).
**Used for:** the (now-zeroed) ELO behavioral bonus, historically.
**Never used for:** the canonical skill metric replacement — explicitly excluded from
its minimum component set, by name, with reasoning given.
**Known limits:** columns/writers are untouched (still computed) even though nothing
reads them meaningfully now — live-write, effectively-dead-consumption.

### B6. `behavioral_modifier` composite (consistency × diversification × style × activity)
**Location:** first-repo, ELO modifier pipeline.
**Capability statement (if exercised):** Would blend four behavioral dimensions into one
ELO multiplier.
**Validation status:** UNVALIDATED-as-live — dormant, `W_BEH=0`.
**Used for:** historically, ELO computation.
**Never used for:** anything currently in effect; distinct from and unrelated to the
three behavioral *score* columns (B4/B5) — not part of the canonical metric design at
all.

### B7. `is_taker` / `transaction_hash` maker-taker detection
**Location:** first-repo, two independent writer scripts with maker/taker branching
logic.
**Capability statement (if exercised):** Would distinguish liquidity-providing (maker)
from liquidity-consuming (taker) trades — a genuine, independent execution-quality
dimension not currently expressible by any live metric.
**Validation status:** UNVALIDATED — the branching code exists and explicitly supports
writing a maker (`0`) label on a confirmed match, but **has never fired**: zero
maker-side rows exist database-wide (621,350 labeled trades, all `is_taker=1`).
**Coverage:** 0% maker coverage.
**Used for:** nothing — no maker rows exist to use.
**Never used for:** any execution-quality measurement; explicitly excluded from the
canonical skill metric design for this reason (§4 of that doc).
**Known limits:** likely structural (CLOB taker sends the settling transaction; a
resting maker order may never generate its own), but **root cause not established** —
would require inspecting live Polygon receipts, not attempted by any doc read this pass.

### B8. `scripts/run_relevance_gate.py`
**Location:** first-repo `scripts/run_relevance_gate.py`.
**What its own docstring claims:** the formal validation gate for the relevance
classifier.
**Capability statement (if exercised):** Would formally validate the relevance
classifier's precision/recall against a held-out gate set.
**Validation status:** UNCLEAR. Zero programmatic callers found in either repo. A gate
result **does exist** in prior project history (2026-09-03: precision PASS, recall FAIL
at 90.35%, all 6 cells — a per-memory record, not independently re-confirmed this pass)
— whether this specific script produced that result, or it was run by hand, or by a
different mechanism, was not established this pass.
**Never used for (established this pass):** nothing — its call/run status beyond the
one known 2026-09-03 result is unconfirmed.

### B9. `scripts/measure_prefilter_coverage.py`
**Location:** first-repo `scripts/measure_prefilter_coverage.py`.
**Capability statement (if exercised):** Would measure what fraction of relevant
markets `monitoring/relevance_prefilter.py` actually lets through.
**Validation status:** UNVALIDATED-as-currently-run — zero callers found.
**Never used for:** any documented coverage figure found this pass.

### B10. `analysis/weighted_consensus_system.py`
**Location:** first-repo `analysis/weighted_consensus_system.py`.
**What it is:** its own module docstring reads "⚠️ DEPRECATED: This module is being
replaced by `unified_elo_system.py`."
**Capability statement (if it still functions):** Would compute a weighted-consensus
score across some prior formulation.
**Validation status:** UNVALIDATED / contradictory status — **deprecated by its own
docstring, yet still has 5 callers**, including `unified_elo_system.py` itself and
`monitoring/elo_bridge.py`. Deprecated-but-still-imported; not resolved by this pass.

---

## Class 4 — CONDEMNED

### C1. `geo_elo` / `geo_elo_active`
**Location:** first-repo, computed in `_compute_geo_elo` and related trade-evaluation
code; still **written live daily** via `scripts/update_geo_elo.py`, a scheduled
`daily_maintenance.py` step.
**What it claims to do:** Rate a trader's geopolitical-market skill via an ELO-style
scoring system, feeding the LEGENDARY tier ladder (C2).
**Defect (5 independently confirmed, `MASTER_HANDOVER_2026-08-15.md` §1):**
1. **SIGN ERROR.** `expected = 1.0 − price`, but `price` already equals P(the traded
   outcome wins) for *both* sides — confirmed empirically by pairing Yes/No trades
   within 60 seconds and finding they sum to 1.000 ± 0.001. No-side trades are scored
   against the probability of the outcome they bet *against*. The module's own docstring
   embeds the same error, which is why prior code-vs-spec validation passed.
2. **IMPROPER SCORING RULE.** A zero-skill trader buying favoured No positions earns
   expected `2·price − 1 > 0` per trade for zero edge — not exotic, since ~71% of these
   markets resolve No and volume clusters on favourites; LEGENDARY may have
   substantially selected for favourite-betting No traders rather than skill.
3. **SELL CONTAMINATION.** 35.7% of the qualifying population (88,927 rows) folded in
   under `trade_evaluator.py`'s inverted win-condition — no side filter anywhere in
   `_fetch_qualifying_trades`.
4. **DOUBLE-COUNTING.** 52.3% of (trader, market) pairs have more than one qualifying
   trade (86.3% of all qualifying trades, median 2, max 642) — the K-schedule counted
   decision *fragments*, not decisions.
5. **UNCALIBRATED PARAMETERS.** K-schedule (32/24/16), start rating 1500, ratchet
   150/step, `MIN_TRADES=5`, decay half-life 180 days, and the tier ladder
   1000/1400/1800/2175 have no calibration record; 2175/1800 were copied from the
   discredited `comprehensive_elo` system (C3); 1000/1400 don't appear before a June-22
   consolidation commit that claimed to lift them "exactly from source scripts" —
   verified inaccurate.
**Explicitly not one bug:** the sign error alone is NOT the dominant driver of rank
disagreement (corr = 0.088 position-weighted, 0.112 cap5) — several independently broken
mechanisms, which is why the response was a full rebuild (the metric-design arc, V5-V8),
not a patch.
**Status:** CONDEMNED but still operationally live — `update_geo_elo.py` continues to
run daily as of this session (confirmed in this session's own 2026-09-12
start-of-session check, log line `[geo_elo] incremental — 2026-09-12T06:02:50Z`).

### C2. LEGENDARY tier ladder (`geo_elo_active >= 2175`, NEAR_LEGENDARY, etc.)
**Location:** `monitoring/column_definitions.py` (`derive_tier()`,
`LEGENDARY_GATE_WHERE`: `geo_elo_active >= 2175 AND geo_accuracy_pool = 1 AND
research_excluded = 0 AND bot_type IS NULL`).
**Defect:** built directly on C1's condemned score; its own thresholds (2175/1800) are
part of C1's defect #5 (uncalibrated, copied from `comprehensive_elo`).
**Additional finding (not part of the original condemnation, found later):** overlap
with the replacement metric's equivalent tier — corrected figure **3/10 (30.0%)** as of
**2026-08-18T19:25:10Z** (superseding an inflated 15/81 figure measured against the
wrong, non-canonical gate) — **70% of the canonical LEGENDARY tier is absent from the
new metric's cohort**, on a small (n=10) and structurally unstable sample
(`MASTER_HANDOVER_2026-08-15.md` §1, corrected 2026-08-18).
**Further finding, 2026-09-11:** LEGENDARY, NEAR_LEGENDARY, and Pool C **all three fail**
as ELO-tier conditioning variables in a later calibration test — i.e. beyond the
condemned scoring mechanics, these tiers do not usefully condition later analyses either
(`2026-09-11-elo-tier-causal-test-and-elo-snapshots-inventory.md`, headline).

### C3. `comprehensive_elo`
**Location:** first-repo, `analysis/unified_elo_system.py` and related; column also
present (99.68% non-default) in `elo_snapshots`.
**Status: NUANCED — two independently true facts, not a single teardown like C1.**
1. **The write-path/plumbing was hardened and validated**: the ELO-arc migration
   (RQ-CONTESTED-001) reached "Stage 3 SHIPPED + dry-run VALIDATED" 2026-07-15/16, a
   single-writer architecture landed.
2. **The formula itself carries a flagged, unresolved defect**: "an analogous
   sign-error pattern... still open and live-affecting"
   (`MASTER_HANDOVER_2026-08-15.md` §6 item 5) — named but **not root-caused or
   detailed to the same specificity as C1** in anything read this pass. This pass
   cannot supply a defect citation as precise as C1's five-item list — flagged
   honestly rather than overclaimed.
**Do not treat identically to C1** — the plumbing is validated even though the formula
defect remains open.

### C4. `calibration_analysis.py`
**Location:** first-repo, named alongside C3.
**Defect:** flagged as carrying "an analogous sign-error pattern" to C1/C3, "out of
scope all session, still open and live-affecting"
(`MASTER_HANDOVER_2026-08-15.md` §6 item 5). Same caveat as C3: not independently
root-caused or detailed by anything read this pass.

---

## Class 5 — OPERATIONAL INFRASTRUCTURE

### O1. `failure_age` tracking + accepted-failures register
**Location:** first-repo `scripts/audit_invariants.py` and related; tests
`tests/test_audit_invariants_failure_age.py` (20/20 passing),
`tests/test_failure_age_tracking.py` (41/41 passing).
**What it does:** Governs whether a detected invariant violation escalates to a
Telegram alert or is silently suppressed as already-known/accepted, gated on how long
the violation has persisted.
**Capability statement:** Not a measurement — decides whether a fact that's already
been observed needs to be re-surfaced.
**Validation status:** PROVEN live — confirmed operating correctly in this session's own
2026-09-12 start-of-session check: the canonical-drift step exited 1 with exactly 1
violation, register-suppressed, no Telegram alert, matching documented expected
behavior.
**Used for:** `daily_maintenance.py` step 8 (canonical drift), the geo/elec pending
backlog alert.

### O2. Canonical resolution write path
**Location:** first-repo `monitoring/resolution_writer.py`'s `mark_market_resolved()`,
3 provenance columns (`resolution_evidence_source`, `resolution_recorded_at`,
`resolution_evidence_detail`), `trg_resolved_no_unresolve` trigger,
`check_resolution_write_atomicity` invariant (Tier 0/OBSERVE).
**Capability statement:** Not a measurement — writes a market's resolution with
provenance through one auditable chokepoint, and guarantees (via a DB trigger) that a
resolved market can never be un-resolved.
**Validation status:** PARTIAL. Trigger verified live and non-tautologically (inside
rolled-back transactions). Stages 0-2 shipped; **only 3 of 13 originally-mapped
market-resolution writers have migrated**; Stages 3-6 (comparator's harder branches —
cross-rank overwrite, same-rank disagreement) essentially unexercised in production —
cross-rank overwrite has fired **zero times across 210,000+ accepted writes to date**,
in tension with the design's own prediction it should be routine at scale (two candidate
explanations remain live, neither chosen, `MASTER_HANDOVER_2026-09-05.md` §5).
**Known defect:** `mark_market_resolved()` never sets `last_checked` (7 of the 9
non-canonical writers it replaced did) — **195,625 of 214,413 (91.2%) sweep-resolved
markets are permanently stranded** from `requeue_resolved_market_traders.py`'s
`last_checked`-gated query, affecting 8,077 open positions across 1,983 traders.
**NOT FIXED** as of the most recent handover read (`MASTER_HANDOVER_2026-09-05.md` §6).

### O3. Pre-registration + amendment + falsifiable-test discipline
**Location:** methodology, evidenced across the corpus rather than one file.
**Capability statement:** Not a measurement — the standing practice of committing
success criteria and thresholds before seeing results, which is what makes the
project's PROVEN claims (V5-V8, D7) trustworthy rather than post-hoc.
**Validation status:** PROVEN as an adhered-to practice, not just an aspiration —
concrete evidence: the directional-skill persistence pre-registration was amended twice,
**both amendments committed before any real result existed, git-provably**
(`7743740` → `a4b6494` → `7ae1845`); when the S8 gate's own prerequisite failed
(synthetic-cohort denominator of 6, below the documented floor of 10), it was
**"Reported and halted, exactly as the pre-registration required"** rather than
worked around (`MASTER_HANDOVER_2026-09-06.md` §3 step 7); the metric_v2 lineage
itself is six successive pre-registered, amended iterations (D9).

### O4. Telegram alert gating (Tier system)
**Location:** first-repo `scripts/audit_invariants.py` Tier 0/1/2/3 severity levels;
test `tests/test_telegram_alert_gating.py` (7/7 passing).
**Capability statement:** Not a measurement — decides which detected conditions are
worth interrupting a human for.
**Validation status:** PROVEN live — confirmed operating in this session's 2026-09-12
check (only the geo/elec pending-backlog alert type fires; others silenced-reversibly).

### O5. `flock` guard on the database backup wrapper
**Location:** first-repo backup cron wrapper.
**Capability statement:** Not a measurement — prevents the backup and a concurrent
sweep/maintenance process from corrupting or starving each other.
**Validation status:** PROVEN — verified with a negative control (the same
blocked-run scenario replayed against the pre-guard commit, which correctly ran the
backup anyway despite a held lock, proving the test depends on the guard); 27 assertions
across 5 scenarios, including a demonstrated (not merely asserted) SIGKILL-survival
case.
**Known limits:** **8 of the 9 cron wrappers remain unguarded**;
`run_daily_maintenance.sh` is named the next, highest-priority target (runs 2-10h
daily against a growing window) — not yet implemented as of the most recent handover
read.

### O6. Tier-3 agent pause discipline
**Location:** trading-swarm cron configuration.
**Capability statement:** Not a measurement — a reversible governance mechanism for
disabling low-value autonomous Claude-credit agents without losing the ability to
re-enable them.
**Validation status:** PROVEN as executed — 5 agents (`code-hygiene`,
`training-librarian`, `performance-analyst`, `signal-agent`, `trader-intelligence`)
disabled 2026-08-31, commented out (not deleted), with a dated block and full re-enable
procedure recorded (`138c03b`). Combined with two earlier pauses
(`research-scout`, `integration-test-agent`), the swarm's scheduled autonomous Claude
footprint is zero as of that commit.

### O7. Test suite (`run_tests.py`)
**Location:** first-repo, root.
**Capability statement:** Not a measurement of the trading thesis — keeps the validated
instruments' proofs (V3's `price_history` test, V4's `backtest_window_population` test,
V6's `match_control_determinism` test, and others) trustworthy over time as the
codebase changes.
**Validation status:** PROVEN operating — confirmed today (2026-09-12): 26/26 files
passing, 339,919/339,919 individual tests.
**Known limits:** covers the instruments that have dedicated test files; several
validated instruments (V1, V2, V5) rely on one-off validation harness scripts instead
of a standing test in this suite, and those harnesses have zero callers (see V1/V2 known
limits) — meaning their PROVEN status is not continuously re-checked by this suite.

### O8. Result-of-record integrity guard (sha256 pinning)
**Location:** convention, applied to `metric_v2f_oos_result` specifically
(`scripts/own_market_calibration.py` and others check the hash as a stop condition
before writing).
**Capability statement:** Not a measurement — a change-detection guard ensuring a
decision-carrying artifact (D7) cannot be silently altered by later work.
**Validation status:** PROVEN as a working pattern — this pass itself used the same
check as a stop condition and found the hash unchanged throughout.
**Known limits:** applied to exactly one table (`metric_v2f_oos_result`); no evidence
found this pass that the same pinning discipline is applied to any other
decision-carrying artifact.

### O9. `monitor_state` / `monitoring_status` (operational KV tables)
**Location:** `data/polymarket_tracker.db`.
**Capability statement:** Not a skill measurement — small live key-value tables the
monitoring loop uses to track its own run state.
**Validation status:** PROVEN live — `monitor_state` (1 row, writer
`monitoring/database.py`), `monitoring_status` (1 row, writer `monitoring/monitor.py`,
5 readers).

---

## Residual — items that could not be given a capability statement this pass

- **`gate-sets-2026-09-01/` data directory** (`labels.csv`, `manifest.json`,
  `set_a/b/c.csv`, spotcheck files, trading-swarm `brain/decisions/`) — a
  relevance-classifier gate-set data artifact; not opened or assessed this pass.
- **`dilution_guard_signals` / `dilution_guard_signals_guard_diffs` write mechanism** —
  the exact write statement inside `scripts/verify_dilution_guard.py` was not confirmed;
  presumed self-contained writer+reader but not verified (see D10).
- **`elo_formula_audit.py` / `elo_formula_audit_findings` /
  `elo_formula_audit_pre_registration`** — tables exist, generating script found with
  zero callers, tied to the comprehensive-ELO-bug project by name only; not
  independently deep-dived this pass.
- **`scripts/archive/` (67 files), `scripts/quick_fixes/` (3), `scripts/simulation/`
  (15)** in first-repo — 85 files, zero read.
- **`orchestrator/permissions/`, `orchestrator/task_templates/`** (trading-swarm) — not
  swept; likely configuration/prompt assets, not capability code, but unconfirmed.
- **Individual `trader_skill_metric_v2` / `v2b` / `v2c` / `v2d` / `v2e` scripts** — each
  has callers (2-24, per the code sweep) but is not individually itemized as its own
  asset entry above; they are represented collectively via D9 and the V5-V8 instruments
  they implement, not as standalone capability entries.
- **~220 of 244 decision docs** not read even in excerpt — including three large primary
  pre-registrations (copy-trade-decay, discovery-gap-closure, directional-skill-persistence)
  known only via handover restatement. Anything named *only* in those documents is not
  captured in this inventory.
- **`docs/elo_system_reference.py`** — a 4,250-line stale duplicate of the 4,572-line
  live `analysis/unified_elo_system.py`; flagged as existing, not assessed as a distinct
  asset (it duplicates B1's dead entry point, nothing more established).

---

## Contradictions found (both citations given, not resolved here)

1. **`composite_skill_score.py`'s status over time** — archive
   `MASTER_HANDOVER_server-pre-setup-1.md` (2026-03-17) shows it ACTIVE with real output
   (13,021 traders scored) months after its 2025-12-05 addition, but
   `2026-09-05-canonical-skill-metric-design.md` §0 finds zero callers as of 2026-09-05.
   It was live, then its caller was removed at an undated point in between — not
   established by this pass. See B1.
2. **`comprehensive_elo`'s status** — the ELO-arc migration treats it as a target that
   reached "Stage 3 SHIPPED + dry-run VALIDATED" (write-path/plumbing), while
   `MASTER_HANDOVER_2026-08-15.md` §6 separately flags its formula with an unresolved
   sign-error analog. Both true simultaneously — see C3.
3. **`elo_snapshots`' 2026-09-11 inventory vs. O-39** — O-39 (overhang ledger, ~2026-07-06)
   found `elo_snapshots.geo_elo` frozen-stale since 2026-06-18 due to a then-standing
   ELO recalc freeze; the 2026-09-11 inventory audits readers/gaps/schema, a different
   question, and doesn't re-flag that specific staleness. Complementary, not
   conflicting — both about B2's table, different angles.

---

## What this pass did NOT do (by design, per scope)

No ranking, scoring, or promise assessment of any asset above. No proposed combinations
or next questions. No external research. No inventory of what has been ruled out beyond
the CONDEMNED class. Nothing was modified, written to a production table, or restarted.
