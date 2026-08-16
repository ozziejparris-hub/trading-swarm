# Canonical Infrastructure Reconnaissance — 2026-08-16

**Task type:** read-only reconnaissance. Nothing was modified, refactored, or fixed.
Drift found is documented and left in place.

**Trigger:** the v2f metric pipeline computes `tape_end` independently rather than
calling `backtest_window_sql()`, despite that function being the canonical, validated
population definition. This raised the question of whether the same "one intended
definition, multiple divergent implementations" failure shape (the reason the ELO arc
existed at all) is recurring elsewhere, and whether anything would actually catch it.

---

## SUMMARY TABLE

| # | Item | Contract (from code) | Consumers | Bypasses found | Enforcement |
|---|------|----------------------|-----------|-----------------|-------------|
| 1 | `monitoring/column_definitions.py` (6 sections: SQL fragments, gate constants, pure functions, atomic DB helper, data provenance, backtest window) | Single source for geo_elo/Pool-C definitions, tier derivation, data_source provenance, and `backtest_window_sql()`. Explicit in its own docstring: "Any change to a column definition, gate threshold, or tier boundary is made HERE and nowhere else." | Repointed: `update_geo_elo.py`, `update_research_exclusions.py`, `audit_invariants.py`, `snapshot_elo_scores.py`, `backfill_trade_results_geo.py`, `reconcile_geo_resolved_counts.py`, `b5_population.py`, `snapshot_backtest_population.py`, `pit_geo_elo.py` (constants only), + others (13 Tier-2 scripts per commit history) | **Section 6 (`backtest_window_sql`)**: bypassed by `analysis/pit_geo_elo.py` (own tape_end temp table, textually identical CTE — verified) and by `scripts/trader_skill_metric_v2d.py`/`v2f.py` (own `build_tape_end_map`, filtered variant — verified to diverge on population, see below). **compute_win_rate/derive_tier**: no bypass found. | **Partial, two-tier.** The `GEO_ELO_*` threshold constants and Pool-C gate SQL ARE structurally enforced (`scripts/check_canonical_definitions.py`, AST-based, wired into `daily_maintenance.py` Step "Canonical definitions drift", non-blocking Telegram alert). **Section 6 (`backtest_window_sql`) is NOT covered by that guard at all** — confirmed by reading the guard's regex/AST rules, which only match `geo_elo[_active] >= N` and Pool-C SQL shapes, never `tape_end`/`MAX(timestamp)` patterns. |
| 2 | Canonical ELO module: `analysis/comprehensive_elo_formula.py` (`compute_comprehensive_elo`, pure fn) + `monitoring/database.py:write_elo_result` (atomic writer) | Pure formula function owns the P&L gain/behavioral gain/damping/cap math; the writer owns "all 9 ELO columns written together, every time, by every caller." | `monitoring/elo_bridge.py` (Writer A), `scripts/apply_full_elo_modifiers.py` (Writer B), `scripts/writer_a_dry_run.py`, `scripts/dry_run_stage3.py` | None found — full trace confirmed in a prior session's dependency trace (2026-08-16-comprehensive-elo-dependency-trace.md) that no other write path to these 9 columns exists outside `archive/`/`tests/`. | `tests/test_comprehensive_elo_formula_equivalence.py`, `_golden.py`, `_properties.py` exist and would fail on a divergent reimplementation — but only if someone runs `run_tests.py` (see item 4: not automatically invoked anywhere). |
| 3 | `scripts/simulation/_sim_db_guard.py` | "Refuse to write to the production DB unless `--allow-production-write` is explicitly passed." Applies only if the writer script calls `assert_safe_to_write()`. | 13 of 14 `scripts/simulation/*.py` files import it (`analyze_predictions.py`, `analyze_simulation_correlation.py`, `backtest_strategy.py`, `calculate_elo_simple.py`, `compare_systems.py`, `optimize_parameters.py`, `run_full_pipeline.py`, `seed_production_data.py`, `seed_test_data.py`, `validate_realism.py`, `verify_elo_rankings.py`, `view_markets.py`) | `scripts/simulation/simulation_observer.py` does not import it — but verified it also contains zero DB connection / UPDATE / INSERT code at all, so it needs no guard. No genuine bypass found. | **Convention-only.** No test enumerates `scripts/simulation/*.py` and asserts each writer calls `assert_safe_to_write`. A new writer script that forgets to import the guard would not be caught by anything. |
| 4 | `run_tests.py` | "Discover `tests/test_*.py`, run each as a subprocess, exit non-zero if any fails." Own comment: "this is what gates pre-commit / CI." | Referenced by `scripts/daily_maintenance.py:91` (as a path variable, `repo_root / "run_tests.py"` — see below for what it's actually used for) and `tests/_writer_b_reference.py` (comment only) | N/A — it is the runner, not a definition to bypass | **Not enforced at all.** No `.pre-commit-config.yaml`, no `.git/hooks/pre-commit` (only unused samples present), no `.github/workflows/`. `daily_maintenance.py`'s reference to `run_tests.py` is NOT a step in `STEPS` — need to check what it's used for (see note below). It is a manually-invoked tool; its own docstring's claim that it "gates pre-commit/CI" is **aspirational, not actual** — no mechanism currently invokes it automatically. |
| 5 | Integration contract between repos, `brain/integration-contract.md` | "Authoritative reference for any agent/script reading or writing the `traders` table" (first-repo copy) / "single source of truth for what first-repo exposes ... any agent that queries first-repo MUST follow this contract" (trading-swarm copy) | Read by convention by any agent/session working cross-repo; no programmatic consumer found | **The two repos' copies are not the same document and have diverged badly — this is itself the largest drift finding in this recon**, see dedicated section below | **None.** No test compares the contract's documented state (e.g. `daily_maintenance.py`'s step list in Section 7) against the actual current step list. No script validates the contract against live schema. |
| 6 | `backtest_population_snapshots` / `bt_pop_2025-11-01_v1` | A frozen, versioned snapshot of `backtest_window_sql()`'s output at a point in time, keyed by `snapshot_id`, carrying `sql_version` so a stale-definition snapshot is identifiable. Intended for consumers needing a population that does NOT move (B5 labelling, B3 splits). | `scripts/build_event_cluster_labels.py` (actual JOIN, B5 clustering), `scripts/snapshot_backtest_population.py` (writer) | None found that should use it and don't — `trader_skill_metric_v2b.py` and `layer0_forward_accuracy.py` reference it only in comments explicitly declaring they use full/live history INSTEAD (a documented, deliberate choice, not an accidental bypass) | No test verifies the snapshot's `sql_version` still matches the current `BACKTEST_WINDOW_SQL_VERSION` at query time (both currently `"1"`, verified, so no live violation — but nothing would catch a future silent mismatch beyond the version being *recorded*, not *checked*). |
| 7 | `event_cluster_labels` (B5 clustering output) | Cluster assignment (`cluster_id`, `label_type`, `reasoning`) for every one of the 4,712 markets in `bt_pop_2025-11-01_v1`, keyed by `(snapshot_id, market_id)` | `scripts/verify_dilution_guard.py`, `scripts/trader_skill_metric_v2b.py` | None found | No automated re-validation found; this was externally audited once (per prior session notes, 0 false splits) but that was a one-off manual pass, not a standing check. |
| 8 | `analysis/pit_geo_elo.py`, `analysis/pit_positions.py`, `monitoring/price_history.py:price_at()` | PIT geo_elo/position reconstruction reusing production matching/formula code by import, not reimplementation (explicit design principle, stated in both modules' docstrings: "This module does NOT reimplement..."). `price_at()`: "last CLOB price point at-or-before T," raises only on caller misconfiguration. | `pit_geo_elo`: `scripts/verify_dilution_guard.py`, `scripts/layer0_forward_accuracy.py`, `scripts/validate_pit_geo_elo.py`, `analysis/pit_positions.py`. `pit_positions`: `scripts/verify_dilution_guard.py`. `price_at`: `tests/test_price_history_price_at.py`, `scripts/verify_dilution_guard.py`. | `pit_geo_elo.py` itself bypasses `column_definitions.BACKTEST_WINDOW_TAPE_END_CTE` for its own tape_end temp table (see item 1) — but `pit_positions.py` correctly reuses `pit_geo_elo`'s copy rather than making a third one. `price_at()`: no bypass found — other CLOB-calling scripts hit a different endpoint (`/markets/{condition_id}` for metadata/resolution, not `/prices-history`) for a different purpose. `scripts/b2_price_history_probe.py` calls `/prices-history` directly, but it is the pre-existing validation probe that `price_at()` was built to formalize, not a live parallel implementation. | `scripts/validate_pit_geo_elo.py`, `scripts/validate_pit_positions.py` exist as one-off validation scripts (previously run and reported: 3,229/3,229 and 1.2M items, zero unexplained divergence — per prior session record) but are not wired to run automatically or repeatedly; they are point-in-time validation artifacts, not standing regression tests. |

---

## OTHER CANONICAL/AUTHORITATIVE MODULES DISCOVERED (beyond the inventory)

Searched both repos for docstring/comment/naming signals ("canonical", "authoritative",
"single source", "do not reimplement", "source of truth").

- **`scripts/check_canonical_definitions.py`** — the drift guard itself. Its own docstring
  scopes it explicitly to geo_elo thresholds and Pool-C SQL only — it does not claim
  broader coverage, so its narrow scope (missing Section 6) is not mislabeling, just a
  real gap nobody has since closed.
- **`json_safety.py`** — exists as two deliberately-separate, hand-synchronized files:
  `first-repo/scripts/json_safety.py` and `trading-swarm/orchestrator/json_safety.py`.
  Its own docstring states the canonical property explicitly is NOT shared code — it's
  that both files derive the same lock-path string, so an `fcntl.flock()` in one process
  and one in the other lock the same inode. This is the **one item in this whole recon
  with a real, structural, drift-detecting test**: `trading-swarm/tests/
  test_cross_repo_lock.py::test_both_repos_derive_the_identical_lock_path` imports BOTH
  copies and asserts their `_lock_path()` outputs are equal, plus runs actual concurrent
  multiprocess writers from both "repos" and asserts no lost updates. It is invoked via
  `python3 -m pytest tests/test_cross_repo_lock.py -v` — manually, per its own docstring;
  no CI or cron wiring found for it either.
- **`brain/integration-contract.md` Section 18** (trading-swarm copy) — describes a
  "single-writer principle" and "column authority registry" governance layer for the
  `traders` table (37 governed columns classified into governance classes), introduced
  2026-06-18. This is itself a canonical-infrastructure claim, but it lives only in prose
  in a Markdown file — no script enforces "only one writer per governed column."
  `reconcile_trader_aggregates.py` is named as the intended single writer for Layer-1
  aggregate columns, but nothing prevents a new script from writing `total_trades` etc.
  directly.
- **`monitoring/column_definitions.py`'s Section 5 (data provenance)** claims `data_source`
  enums are canonical and that "harness checks enforce membership post-migration" — the
  harness check referenced is presumably part of `audit_invariants.py`; not independently
  verified in this pass (out of the requested inventory scope) but flagged as a claim
  worth checking in a future recon if data_source drift is ever suspected.

No other modules were found using "canonical"/"authoritative"/"source of truth"/"do not
reimplement" language in a way that designates them as a single-source definition beyond
the above.

---

## THE SPECIFIC QUESTION: `backtest_window_sql()` vs. the v2f pipeline's population

**Method:** ran both actual SQL definitions read-only against the live production DB
(`sqlite3 -readonly`), anchored at the same real boundary the OOS thesis test used
(`T_split = 2026-04-01 00:00:00`), and diffed the resulting market-ID sets directly (not
inferred from reading the code).

**Query A — canonical** (`backtest_window_sql`'s actual WHERE/JOIN shape, window_end =
T_split, matching its own `<` semantics):
```sql
WITH tape_end AS (SELECT market_id, MAX(timestamp) AS tape_end FROM trades GROUP BY market_id)
SELECT m.market_id
FROM markets m JOIN tape_end te ON te.market_id = m.market_id
WHERE m.resolved = 1
  AND m.category IN ('Geopolitics','Elections')
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
  AND te.tape_end < '2026-04-01 00:00:00'
```
Result: **6,842 markets**.

**Query B — v2f's actual implicit population** (the exact WHERE clause from
`build_presplit_cohort` in `scripts/trader_skill_metric_v2f.py:236-247`, projected to
distinct `market_id`, using its own `<=` semantics on `tape_end`):
```sql
WITH tape_end AS (SELECT market_id, MAX(timestamp) AS tape_end FROM trades GROUP BY market_id)
SELECT DISTINCT p.market_id
FROM positions p
JOIN markets m ON m.market_id = p.market_id
JOIN trades t ON t.trade_id = json_extract(p.entry_trade_ids, '$[0]')
JOIN tape_end te ON te.market_id = p.market_id
WHERE m.category IN ('Geopolitics', 'Elections')
  AND p.entry_avg_price IS NOT NULL
  AND t.trade_result IN ('won', 'lost')
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
  AND te.tape_end <= '2026-04-01 00:00:00'
```
Result: **6,588 markets**.

**Symmetric difference: 254 markets, entirely one-directional.**
```
comm -23 canonical_markets.txt v2f_implicit_markets.txt | wc -l   → 254   (canonical-only)
comm -13 canonical_markets.txt v2f_implicit_markets.txt | wc -l   →   0   (v2f-only)
comm -12 canonical_markets.txt v2f_implicit_markets.txt | wc -l   → 6,588 (shared)
```
The v2f population is a **strict subset** of the canonical population — nothing appears
in v2f's set that isn't also in the canonical set.

**Boundary condition — determined empirically, not inferred, by inspecting all 254
markets:**

1. **Interval closure (`<` vs `<=`) contributes ZERO markets.** Checked directly: no
   market has `tape_end` exactly equal to `2026-04-01 00:00:00` (`SELECT COUNT(*) FROM
   tape_end WHERE tape_end = '2026-04-01 00:00:00'` → `0`). The two queries' differing
   end-boundary operators are a real code-level discrepancy but have no observable effect
   on this population as of today's data.
2. **166 of 254 markets (65.4%): zero-position handling / join semantics.** These markets
   are resolved, category-matched, trade-gap-clean, and have at least one trade (so they
   qualify for `tape_end` under the canonical INNER JOIN on `trades`) — but have **zero
   rows in the `positions` table at all**. `backtest_window_sql()` is anchored on the
   `markets`+`trades` tables only and has no dependency on `positions`; v2f's query is
   anchored on `positions` (via `positions JOIN markets JOIN trades`), so a market that
   never had a FIFO position constructed for it (verified: these are mostly 1-2-trade
   markets, e.g. `0x00b2eb5d...` has exactly 1 trade and no position) silently disappears
   from v2f's population. This is exactly the "zero-trade market handling" class of
   boundary condition anticipated by the task, except it is **zero-position**, not
   zero-trade — these markets have trades, just no FIFO-closed position.
3. **88 of 254 markets (34.6%): a `markets.resolved` vs. `trades.trade_result`
   consistency gap.** These markets have positions, but every position's entry trade has
   `trade_result = 'pending'`, even though `markets.resolved = 1`. `backtest_window_sql()`
   only checks `m.resolved = 1` and has no opinion on `trade_result`; v2f's query requires
   `t.trade_result IN ('won','lost')` and excludes these outright. This means `markets.
   resolved` and the entry trade's `trade_result` can disagree — the market-level flag
   says resolved, the trade-level outcome field says pending — for 88 markets in this
   population, which is itself a latent data-consistency finding independent of the
   canonical-vs-bypass question (reported here, not investigated further — out of scope
   for this recon).

**Practical read:** the two definitions agree on 96.3% of the canonical population
(6,588 / 6,842) as of today's data, and 100% of v2f's own population is a verified subset
of canonical — so this specific divergence has not (as far as this trace can tell)
produced a market in v2f's OOS cohort that canonical would have excluded. But the
agreement is a product of today's data, not a structural guarantee: nothing prevents
`backtest_window_sql()`'s WHERE clause or `BACKTEST_WINDOW_BASE_WHERE` from changing
(the module's own comment instructs "CHANGING THIS WHERE CLAUSE? Bump
BACKTEST_WINDOW_SQL_VERSION") without v2d's/v2f's independent `build_tape_end_map`
implementation ever being touched or even reviewed — there is no test tying the two
together (confirmed: `tests/test_backtest_window_population.py` compares the canonical
query only against the frozen snapshot and an old resolution_date-based method; it never
references `pit_geo_elo.py` or any `trader_skill_metric_v2*.py` file).

---

## ALL BYPASSES FOUND, RANKED BY VERIFICATION STATUS

**Shown to disagree (verified against real data):**
1. `scripts/trader_skill_metric_v2d.py:268-273` (`build_tape_end_map`, consumed by
   `v2f.py`) vs. `monitoring/column_definitions.py`'s `backtest_window_sql()` — 254-market
   symmetric difference on the actual production DB, fully characterized above (join
   semantics + a `resolved`/`trade_result` consistency gap; interval-closure difference
   present in code but empirically inert today).

**Shown to agree (verified, not just plausible):**
2. `analysis/pit_geo_elo.py:69-73` (`_ensure_tape_end_temp_table`'s CTE text) vs.
   `monitoring/column_definitions.py:451-453` (`BACKTEST_WINDOW_TAPE_END_CTE`) — both are
   `SELECT market_id, MAX(timestamp) AS tape_end FROM trades GROUP BY market_id`,
   character-for-character identical SQL text (direct comparison of the two string
   literals, not merely "looks similar"). This is a textual reimplementation, not a
   divergent one — same source, same syntax, just not imported from the shared constant.

**Not a bypass on inspection (checked, ruled out):**
3. `scripts/b2_price_history_probe.py` hits the `/prices-history` CLOB endpoint directly
   — but it is the historical validation probe `price_history.py:price_at()` was built
   from, not a parallel live implementation; sequencing checked via the module's own
   design-doc references, not assumed.
4. `scripts/simulation/simulation_observer.py` doesn't call `_sim_db_guard`, but has zero
   DB connection code — not a writer, needs no guard.
5. `scripts/trader_skill_metric_v2b.py` / `layer0_forward_accuracy.py` mention
   `bt_pop_2025-11-01_v1` only to say they deliberately do NOT use it (full history
   instead) — a documented choice, not an unnoticed gap.

---

## STRUCTURALLY ENFORCED vs. CONVENTION-ONLY

**Structurally enforced (something would fail/alert on drift):**
- geo_elo/Pool-C threshold constants and gate SQL — `check_canonical_definitions.py`,
  AST-based, wired into `daily_maintenance.py` (non-blocking Telegram alert on drift).
- The comprehensive_elo pure formula — `tests/test_comprehensive_elo_formula_*.py` exist
  and would catch a divergent reimplementation, **conditional on `run_tests.py` actually
  being run** (see below — it is not automatic).
- The cross-repo `json_safety.py` lock-path identity — `test_cross_repo_lock.py` imports
  both files and asserts equality, **conditional on someone running pytest manually**.
- `backtest_window_sql()` vs. its own frozen snapshot and vs. the old resolution_date
  method — `tests/test_backtest_window_population.py`, **conditional on `run_tests.py`**.

**Convention-only (nothing would catch drift):**
- `backtest_window_sql()` (Section 6) vs. any independent tape_end reimplementation
  elsewhere in the codebase — **this is the gap the task's trigger finding pointed at,
  and it is confirmed real**: `check_canonical_definitions.py` doesn't cover it, and
  `test_backtest_window_population.py` doesn't compare against `pit_geo_elo.py` or the
  `trader_skill_metric_v2*.py` chain.
- `_sim_db_guard.py` adoption across `scripts/simulation/*.py` — no enumeration test.
- The integration contract's accuracy against live state (both repos' copies) — no test
  at all.
- `backtest_population_snapshots`'s `sql_version` staying consistent with the live
  `BACKTEST_WINDOW_SQL_VERSION` at read time — recorded, never checked.
- `event_cluster_labels`' continued validity — validated once, manually, not on a
  standing cadence.

**The deeper structural fact underlying all of the above:** even the items with real
tests (`run_tests.py`'s `tests/test_*.py` suite) are enforced **only when a human runs
`run_tests.py` manually**. There is no pre-commit hook (only unused sample hooks present
in `.git/hooks/`), no `.github/workflows/`, no `.pre-commit-config.yaml` in either repo.
`daily_maintenance.py` runs `check_canonical_definitions.py` automatically every day, but
that is the only canonical-definition check with a genuinely automatic trigger; everything
else in this recon requires deliberate, manual invocation.

---

## THE INTEGRATION CONTRACT: DRIFT FINDING (item 5, expanded)

The two repos each have a `brain/integration-contract.md`, and they are **not the same
document, not cross-linked, and both stale relative to current state**:

| | first-repo copy | trading-swarm copy |
|---|---|---|
| Version | v1.4 | v2.13 |
| Length | 275 lines | 1,413 lines |
| Scope | `traders` table schema only | Full cross-repo contract: connection pattern, query filters, research pools, ELO tiers, active strategies, daily maintenance schedule, structural-break dates, canonical agent definitions, trader archetypes, temporal state layer, signal registration, order-book infra, backup infra, datetime format standard, STR-002 design, data provenance/column-authority registry |
| Last commit | `8232cff`, 2026-05-25 (83 days before this recon) | `e4a8da7`, 2026-06-29 (48 days before this recon) |

**Confirmed concrete staleness in the larger (trading-swarm) copy:** its Section 7
documents `daily_maintenance.py` as a 19-20 step process (Steps 0–16, 19, 20, plus two
Post steps). The actual current `scripts/daily_maintenance.py` (read directly) has **29
steps**, including several with no mention anywhere in the contract: "Reconcile geo
resolved counts [pre-audit]" and "[post-eval]", "Integrity audit (pre-ELO gate)" (a
**blocking** gate that hard-aborts ELO writes on Tier-1 CRITICAL — exactly the kind of
thing an "authoritative" operational contract should document), "Canonical definitions
drift", "Backfill market categories", "Fetch new market resolutions", "Register/Enrich/
Score STR-002 signals", "Resolve LEGENDARY trader markets", and "Detect counter-signals".
None of these appear in the contract's Section 7 step list.

The contract's Section 10.1 also states `geo_elo_active`/`comprehensive_elo` tier
thresholds and explicitly warns "No proven edge on contested markets... Do NOT use for
signal generation" for `comprehensive_elo` — but neither repo's contract copy mentions
the 2026-08-15 finding that `geo_elo` itself (not just `comprehensive_elo`) has a
confirmed sign error and is "unfit for purpose" (per this session's other work,
`2026-08-15-skill-metric-rebuild.md`). An agent reading only the integration contract
today would not learn that the north star changed.

---

*Recon performed 2026-08-16, read-only. All SQL comparisons run via `sqlite3 -readonly`
or a `mode=ro` URI connection against the live production DB — no writes were possible or
attempted. No files modified.*
