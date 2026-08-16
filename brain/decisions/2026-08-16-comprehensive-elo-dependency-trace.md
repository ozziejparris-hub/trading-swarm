# comprehensive_elo / calibration_analysis.py — Dependency Trace vs. the 2026-08-15 OOS Thesis Result

**Task type:** read-only dependency trace. No code was modified, patched, or "fixed." Any
issues found (e.g. the v2 pipeline's lack of a `research_excluded` filter) are reported
as observations only and left exactly as found.

**Question traced:** does `comprehensive_elo`, or any column/table it writes, or any
output of `calibration_analysis.py`, feed INTO the inputs of the 2026-08-15 OOS thesis
result (cohort mean edge +0.0316, CI [-0.0088, +0.0710], n=3,032 positions, 148
qualifying / 120 surviving traders, T_split=2026-04-01)?

---

## VERDICT: **NO CONTACT**

No path from `comprehensive_elo`, any column/table its writer paths populate, or any
output of `calibration_analysis.py`, reaches any of the five trace targets (positions
FIFO aggregation, `backtest_window_sql()`/canonical backtest population, the T_split
cohort qualification path, the placebo matching, or `trader_skill_metric_v2*.py` /
`layer0c_corrected_metric.py`).

One genuine, confirmed causal path was found and traced to ground — `comprehensive_elo`
→ `traders.bot_type` → `traders.research_excluded` — but `research_excluded` (and every
other `traders` column comprehensive_elo touches) is never read by any of the five
targets. This is reported in full below, not rounded down silently.

---

## STEP (a): What `comprehensive_elo`'s writer paths actually WRITE

Read, not inferred from names. The canonical atomic writer:

**`monitoring/database.py:30-95`, function `write_elo_result`:**
```
monitoring/database.py:72:    conn.execute("""
monitoring/database.py:73:        UPDATE traders
monitoring/database.py:74:        SET comprehensive_elo = ?,
monitoring/database.py:75:            base_category_elo = ?,
monitoring/database.py:76:            behavioral_modifier = ?,
monitoring/database.py:77:            advanced_modifier = ?,
monitoring/database.py:78:            pnl_modifier = ?,
monitoring/database.py:79:            kelly_alignment_score = ?,
monitoring/database.py:80:            patience_score = ?,
monitoring/database.py:81:            timing_score = ?,
monitoring/database.py:82:            elo_last_updated = ?
monitoring/database.py:83:        WHERE address = ?
monitoring/database.py:84:    """, (...))
```
Docstring (lines 39-47) confirms this is deliberately the SOLE writer: "Atomic
full-column-set write for comprehensive_elo ... Writes ALL of comprehensive_elo,
base_category_elo, behavioral_modifier, advanced_modifier, pnl_modifier,
kelly_alignment_score, patience_score, timing_score, and elo_last_updated in ONE
UPDATE, every time. No caller may write a subset of these columns some other way."

**Confirmed write-target column set (all on `traders`):** `comprehensive_elo`,
`base_category_elo`, `behavioral_modifier`, `advanced_modifier`, `pnl_modifier`,
`kelly_alignment_score`, `patience_score`, `timing_score`, `elo_last_updated`.

**Callers of `write_elo_result` (grep, `select:write_elo_result` class, not name-only —
verified each is an actual call site, not a comment):**
```
monitoring/elo_bridge.py:590:        from .database import write_elo_result
monitoring/elo_bridge.py:643:                write_elo_result(
scripts/apply_full_elo_modifiers.py:71:from monitoring.database import write_elo_result
scripts/apply_full_elo_modifiers.py:276:        write_elo_result(
scripts/writer_a_dry_run.py:11: (dry-run copy of the same call, to a scratch DB copy)
scripts/dry_run_stage3.py:11: (references write_elo_result's canonical space-sep format)
```
`monitoring/elo_bridge.py` = Writer A (live). `scripts/apply_full_elo_modifiers.py` =
Writer B (live). Both funnel through the single atomic writer above — confirmed no
other write path exists to any of these nine columns outside `archive/` and `tests/`
(full grep in Step (b) below).

**Schema confirmation** (`sqlite3 data/polymarket_tracker.db ".schema traders"`):
```
comprehensive_elo REAL DEFAULT 1500
base_category_elo REAL DEFAULT 1500
elo_last_updated TIMESTAMP DEFAULT NULL
elo_period1_cutoff REAL DEFAULT NULL
geo_elo REAL DEFAULT NULL
geo_elo_active REAL
CREATE INDEX idx_traders_comprehensive_elo ON traders(comprehensive_elo DESC)
```
`comprehensive_elo` and `geo_elo` are **confirmed distinct columns**. `scripts/
update_geo_elo.py` (the geo_elo writer) has zero references to `comprehensive_elo` or
`calibration_analysis` (`grep -n "comprehensive_elo\|calibration_analysis"
scripts/update_geo_elo.py` → no output). The two systems are structurally independent
at the writer level.

### `calibration_analysis.py` — write targets: **NONE (confirmed)**

All four `cursor.execute()` calls in the file are `SELECT`-only (`analysis/
calibration_analysis.py:144,434,506,1047` — verified by reading each query in full).
Search for any write class:
```
grep -n "to_csv|to_sql|savefig|json.dump|open(.*['\"]w|\.to_json|INSERT INTO|UPDATE " analysis/calibration_analysis.py
→ 639:            plt.savefig(filepath, ...)   (PNG chart, human-viewed file)
→ 682:            plt.savefig(filepath, ...)
→ 729:            plt.savefig(filepath, ...)
→ 783:            plt.savefig(filepath, ...)
→ 956:        with open(output_file, 'w', ...)  (text report, human-viewed file)
```
No `INSERT`, no `UPDATE`, no `to_sql`. `calibration_analysis.py` writes only PNG plots
and a text report — no DB table, no artifact any other script reads programmatically.
Its only live consumers are as an imported CLASS (`CalibrationAnalyzer`), traced next.

---

## STEP (b): Consumers of the write-target columns — full enumeration

**Search classes covered:**
1. Direct name grep for the 8 write-target columns, both repos, `*.py`, excluding
   `archive/` (name-match class).
2. Read of every `UPDATE traders SET` statement touching these columns (write-statement
   class, not name-only).
3. `SELECT *` + positional/dict access: checked explicitly — `monitoring/database.py`
   uses `SELECT *` at one call site (`get_trader_trades`, line ~144 in that file's
   trades-table method, unrelated table) but no `SELECT * FROM traders` followed by
   positional/dict access into any of the 9 columns was found anywhere in the codebase.
   `analysis/calibration_analysis.py`, `analysis/unified_elo_system.py`, and the five
   trace-target files were individually checked for this pattern — none present.
4. Dynamic column construction (f-string column lists): checked in every SQL string
   read for this trace (`write_elo_result`, `apply_full_elo_modifiers.py`, `elo_bridge.
   py`, all `trader_skill_metric_v2*.py` queries, `column_definitions.py`,
   `update_research_exclusions.py`) — all use explicit, static column lists. No dynamic
   construction found that could smuggle a comprehensive_elo-family column into a query
   that doesn't name it directly.
5. Views/materialised tables built on top of `traders`: none found — no `CREATE VIEW`
   referencing `traders` exists in the repo (`grep -rn "CREATE VIEW" --include="*.py" .`
   → no output).

**Full first-repo file list** (54 files, `grep -rlE
"comprehensive_elo|base_category_elo|behavioral_modifier|advanced_modifier|
pnl_modifier|kelly_alignment_score|patience_score|timing_score" --include="*.py" .`,
`archive/` excluded):
```
analysis/analysis_scheduler.py
analysis/comprehensive_elo_formula.py
analysis/correlation_matrix.py
analysis/trading_behavior_analysis.py
analysis/unified_elo_system.py
brain/agent-outputs/quant-research/RQ1.1/rq1_1_elo_persistence.py
docs/database_reference.py
docs/elo_system_reference.py
monitoring/background_backfill_worker.py
monitoring/database.py
monitoring/diagnostics.py
monitoring/elo_bridge.py
monitoring/system_observer.py
monitoring/telegram_elo_bot.py
paper_trading/signal_generator.py
scripts/add_watched_trader.py
scripts/apply_full_elo_modifiers.py
scripts/audit_invariants.py
scripts/compute_elo_shadow.py
scripts/detect_arb_bots.py
scripts/dry_run_stage3.py
scripts/hydrate_stub_markets.py
scripts/legendary_positions_scan.py
scripts/pre_resolution_intelligence.py
scripts/recalculate_comprehensive_elo.py
scripts/reconcile_trader_aggregates.py
scripts/resolve_legendary_markets.py
scripts/signal_credibility.py
scripts/simulation/analyze_predictions.py
scripts/simulation/analyze_simulation_correlation.py
scripts/simulation/backtest_strategy.py
scripts/simulation/calculate_elo_simple.py
scripts/simulation/verify_elo_rankings.py
scripts/simulation/view_markets.py
scripts/snapshot_elo_scores.py
scripts/trader_skill_metric_v2b.py   <- comment-only, see below
scripts/trader_skill_metric_v2c.py   <- comment-only, see below
scripts/trader_skill_metric_v2d.py   <- comment-only, see below
scripts/trader_skill_metric_v2e.py   <- comment-only, see below
scripts/trader_skill_metric_v2.py    <- comment-only, see below
scripts/update_research_exclusions.py
scripts/validate_stage1_equivalence.py
scripts/verify_elo_correctness.py
scripts/verify_elo_recalculation.py
scripts/view_trader_rankings.py
scripts/writer_a_dry_run.py
tests/test_behavioral_integration.py
tests/test_comprehensive_elo_formula_equivalence.py
tests/test_comprehensive_elo_formula_golden.py
tests/test_comprehensive_elo_formula_properties.py
tests/test_data_source_write_paths.py
tests/test_manual_research_exclusion_override.py
tests/_writer_b_reference.py
test_trend_analysis.py
```
**trading-swarm file list** (5 files):
```
brain/agent-outputs/quant-research/RQ2.2/rq2_2_entry_timing.py
brain/agent-outputs/quant-research/RQ3.2/rq3_2_crowd_vs_elite.py
orchestrator/ollama_agent_loop.py
scripts/run_feedback_loop_agent.py
tests/test_write_allowlist_exact_match.py
```

**Critical sub-check — the five `trader_skill_metric_v2*.py` files' actual references
to `comprehensive_elo` (the only reason they appeared in the grep above):**
```
scripts/trader_skill_metric_v2.py:122:  decision -- those come after this metric is trusted. comprehensive_elo /
scripts/trader_skill_metric_v2b.py:121: decision. comprehensive_elo / calibration_analysis.py remains out of scope.
scripts/trader_skill_metric_v2c.py:102: membership untouched. No threshold derivation, no cutover. comprehensive_elo
scripts/trader_skill_metric_v2d.py:53:  (derivation audit: 2175/1800 traced to a discredited comprehensive_elo
scripts/trader_skill_metric_v2d.py:92:  membership untouched. No cutover decision. comprehensive_elo /
scripts/trader_skill_metric_v2e.py:90:  membership untouched. No cutover. comprehensive_elo / calibration_analysis.py
```
Every one of these is inside the pre-registration docstring, explicitly declaring
`comprehensive_elo`/`calibration_analysis.py` **out of scope**. Confirmed by reading
each full docstring (not just the matched line) — none is a live code reference, import,
or SQL fragment. Cross-checked against the imports of all six v2 scripts (`grep -n
"^import\|^from" scripts/trader_skill_metric_v2*.py`) — every import resolves to numpy/
pandas/sqlite3/argparse/stdlib or another `scripts.trader_skill_metric_v2*` module in
the same chain. **Zero import of `comprehensive_elo_formula`, `calibration_analysis`,
`unified_elo_system`, `elo_bridge`, or `apply_full_elo_modifiers` anywhere in the v2
chain.**

**Traced-to-ground summary of every consumer class found:**

| Consumer | What it does with comprehensive_elo-family columns | Reaches (1)-(5)? |
|---|---|---|
| `monitoring/elo_bridge.py`, `scripts/apply_full_elo_modifiers.py` | Writer A/B — compute and write the columns | N/A (this IS the source) |
| `scripts/detect_arb_bots.py`, `scripts/pre_resolution_intelligence.py`, `paper_trading/signal_generator.py`, `monitoring/telegram_elo_bot.py`, `monitoring/system_observer.py`, `monitoring/diagnostics.py`, `scripts/view_trader_rankings.py`, `scripts/snapshot_elo_scores.py`, `scripts/signal_credibility.py`, dashboards/simulation scripts | Read `comprehensive_elo` for display, alerting, or independent (non-thesis) simulation/backtest work | No — all read-only display/alert/simulation consumers; none writes to `positions`, `markets.trade_gap_flag`, `markets.category`, or `trades.trade_result` (the columns the five targets actually read), and none is imported by any of the five targets |
| `analysis/trading_behavior_analysis.py` | Computes `kelly_alignment_score`/`patience_score`/`timing_score` **feeding INTO** comprehensive_elo (upstream of it, not downstream) | No — wrong direction, and doesn't touch positions/markets/trades independent of that upstream role |
| `analysis/correlation_matrix.py` | Reads `comprehensive_elo >= 1500 OR total_trades >= 30` as a filter for its own (separate) correlation report | No — standalone report, no write path back to (1)-(5) |
| `scripts/reconcile_trader_aggregates.py` | Reconciliation/audit script, references the 8 columns in a comment describing "Layer 2 (ELO chain)" | No — no UPDATE/INSERT to positions/markets/trades found in this file |
| `scripts/hydrate_stub_markets.py` | Writes to `markets` (resolution_date, end_date, resolved, winning_outcome, category, title) from API data — **zero** comprehensive_elo-family reference in this file (grep confirmed empty) | No — file matched the broader "elo" scan for unrelated reasons; re-grepped specifically for the 8 columns, zero hits |
| **`scripts/update_research_exclusions.py`** | **Real, confirmed path — see below** | **Reaches `traders.research_excluded`, but `research_excluded` is never read by (1)-(5) — traced to ground below** |
| `brain/agent-outputs/quant-research/RQ1.1/rq1_1_elo_persistence.py` (first-repo, "June 2026 rerun") | Reads `comprehensive_elo` (line 290, 376) for **display only** in its output Markdown table; its actual correlation statistic uses `elo_period1_cutoff` exclusively (function docstring, line 284: "Uses elo_period1_cutoff exclusively") | No — writes only to `rq1_1_rerun_june2026.json`/`.md` and `trading-swarm/brain/signals.json`; none of these files is read by any of the five targets (confirmed: no file-read of RQ1.1 outputs or `signals.json` anywhere in the v2 chain) |
| trading-swarm `RQ2.2`, `RQ3.2`, `orchestrator/ollama_agent_loop.py`, `run_feedback_loop_agent.py` | Independent quant-research/orchestrator scripts connecting read-only to the DB (`run_feedback_loop_agent.py:12`: "Database: READ ONLY — never writes to polymarket_tracker.db") | No — confirmed no `UPDATE`/`INSERT` to `positions`/`markets`/`trades` in any of these four files |
| `docs/elo_system_reference.py`, `docs/database_reference.py` | Static reference copies | No — confirmed zero imports of either file anywhere in the codebase (`grep -rn "from docs.elo_system_reference\|import docs\."` → no output); dead/reference-only |
| `tests/*` | Test fixtures/mocks | Out of scope — test-only schemas, not live data paths |

### The one real path, traced fully: `comprehensive_elo` → `bot_type` → `research_excluded`

`scripts/update_research_exclusions.py:54-64` (`LP_ARTIFACT_TIER1B_TAG_SQL`):
```sql
UPDATE traders
SET bot_type = 'LP_ARTIFACT'
WHERE bot_type IS NULL
  AND research_excluded = 0
  AND comprehensive_elo < 700
  AND address IN (SELECT trader_address FROM positions GROUP BY trader_address
                   HAVING COUNT(position_id) > 500 AND COUNT(DISTINCT market_id) < 3)
```
`scripts/update_research_exclusions.py:75-84` (`ARB_BOT_TAG_SQL`): same shape, gated on
`comprehensive_elo BETWEEN 1500 AND 3500`.

`scripts/update_research_exclusions.py:137-146` (`EXCLUDE_SQL`):
```sql
UPDATE traders
SET research_excluded = 1
WHERE research_excluded = 0
  AND (resolved_trades_count < 20 OR resolved_trades_count IS NULL
       OR bot_suspect = 1 OR wash_trade_suspect = 1
       OR bot_type IN ('LP_ARTIFACT', 'THIN_SAMPLE_ARTIFACT', 'ARB_BOT'))
```
So: `comprehensive_elo` genuinely determines `bot_type` for some traders, and
`bot_type IN ('LP_ARTIFACT', 'ARB_BOT')` genuinely sets `research_excluded = 1`. This is
a real, live, two-hop causal path from `comprehensive_elo` into a population-eligibility
column used broadly across the project (per CLAUDE.md: "Always filter research queries
with `AND tr.research_excluded = 0`").

**But it does not reach the five targets.** Checked explicitly:
```
grep -n "research_excluded" scripts/trader_skill_metric_v2*.py scripts/layer0c_corrected_metric.py monitoring/position_tracker.py monitoring/column_definitions.py
→ monitoring/column_definitions.py:126:    f"\n  AND research_excluded = 0"
→ monitoring/column_definitions.py:131:RESEARCH_CLEAN_WHERE = "research_excluded = 0"
(no matches in any trader_skill_metric_v2*.py, layer0c_corrected_metric.py, or position_tracker.py)
```
`research_excluded` appears only inside `monitoring/column_definitions.py`'s
**geo_elo/Pool-C infrastructure** (`RESEARCH_CLEAN_WHERE`, `POOL_C_GATE_WHERE`,
`derive_tier`) — not inside `backtest_window_sql()`, and the v2 pipeline never imports
`monitoring.column_definitions` at all (`grep -n "column_definitions"
scripts/trader_skill_metric_v2*.py scripts/layer0c_corrected_metric.py` → no output).

Read in full, every SQL query that actually produces the OOS thesis result confirms
this directly:

`scripts/trader_skill_metric_v2.py:185-196` (`load_entries`, the primary population for
the whole v2 chain):
```sql
SELECT p.position_id, p.trader_address, p.market_id, p.outcome,
       p.entry_avg_price, p.entry_timestamp, t.trade_result
FROM positions p
JOIN markets m ON m.market_id = p.market_id
JOIN trades t ON t.trade_id = json_extract(p.entry_trade_ids, '$[0]')
WHERE m.category IN ('Geopolitics', 'Elections')
  AND p.entry_avg_price IS NOT NULL
  AND t.trade_result IN ('won', 'lost')
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)
```
No `JOIN traders`. No `research_excluded`, `bot_type`, or `comprehensive_elo` filter.

`scripts/trader_skill_metric_v2f.py:236-247` (`build_presplit_cohort`, the exact query
that builds the 148-trader pre-split cohort for the OOS test) and `:315-330`
(`measure_oos`, the exact query behind both the +0.0316 cohort result and the placebo):
identical shape — `positions JOIN markets JOIN trades`, filtered on `category`,
`entry_avg_price IS NOT NULL`, `trade_result IN ('won','lost')`, `trade_gap_flag`. No
`traders` table join in either query. The only `traders` table touch anywhere in
`trader_skill_metric_v2f.py` is:
```
scripts/trader_skill_metric_v2f.py:380:    legendary = set(r[0] for r in conn.execute("SELECT address FROM traders WHERE geo_elo >= 2175"))
```
— used exclusively to print an overlap count (`:382-385`) against the already-computed
`intersection_traders` set; it does not filter, narrow, or modify `intersection_traders`,
`oos_cohort`, or `control_cohort` anywhere (verified by reading `main()` end to end —
`legendary` is referenced nowhere else in the file). And this is `geo_elo`, not
`comprehensive_elo`, regardless.

`monitoring/position_tracker.py` (target 1, the FIFO aggregation that produces the
`positions` table these queries read): `grep -n "research_excluded|comprehensive_elo|
bot_type|bot_suspect|geo_elo" monitoring/position_tracker.py monitoring/monitor.py` →
**no output**. The FIFO logic imports only `from monitoring.database import Database`
(for the connection helper) and processes every trade unconditionally — no trader-level
ELO or exclusion filter at position-construction time either.

`monitoring/column_definitions.py`'s `backtest_window_sql()` (target 2, lines 476-495):
```python
return f"""
    WITH tape_end AS ({BACKTEST_WINDOW_TAPE_END_CTE})
    SELECT m.market_id, m.title, m.condition_id, m.resolution_date, te.tape_end
    FROM markets m
    JOIN tape_end te ON te.market_id = m.market_id
    WHERE {BACKTEST_WINDOW_BASE_WHERE}
      AND te.tape_end >= :window_start{end_clause}
"""
```
Reads only `markets` + a `trades`-derived tape_end CTE. No `traders` join. (Also: v2f's
own tape_end computation, `build_tape_end_map` in `scripts/trader_skill_metric_v2d.py:
268-273`, is a separate self-contained `MAX(trades.timestamp) GROUP BY market_id` query
— it does not call `backtest_window_sql()` at all, so target 2's canonical population
infrastructure was not even used as an input to the OOS result in practice, on top of
containing no comprehensive_elo/calibration_analysis reference itself.)

`scripts/layer0c_corrected_metric.py`: `grep -n "JOIN traders|FROM traders|traders\."` →
only a local pandas variable literally named `traders` (categorical codes on a
DataFrame column, `:187,191`), not a SQL table reference. Zero DB-level `traders` table
access in this file.

`positions` and `markets` table schemas checked directly for any baked-in
ELO/calibration column that could carry contamination invisibly:
```
sqlite3 data/polymarket_tracker.db ".schema positions" | grep -iE "elo|calibrat|modifier|score"  →  (no output)
sqlite3 data/polymarket_tracker.db ".schema markets"   | grep -iE "elo|calibrat|modifier|score"  →  difficulty_score REAL
```
`markets.difficulty_score` exists but is not selected by `backtest_window_sql()`,
`load_entries`, `build_presplit_cohort`, or `measure_oos` (confirmed by the full query
text above) — irrelevant to this trace regardless of its own derivation.

---

## STEP (e): The June 22 consolidation commit — actual diff read

Identified via `git log --oneline --since="2026-06-15" --until="2026-06-25" -- 
scripts/update_geo_elo.py analysis/comprehensive_elo_formula.py
analysis/unified_elo_system.py` and cross-referenced against trading-swarm's
`2026-06-22-session-summary.md`: the commit is **`17f8d62`**, `Mon Jun 22 17:38:58 2026`,
"feat: add monitoring/column_definitions.py — canonical column definitions (contract
18.5.1)".

`git show 17f8d62 --stat`:
```
monitoring/column_definitions.py | 367 +++++++++++++++++++++++++++++++++++++++
 1 file changed, 367 insertions(+)
```
Single new file, 367 lines, nothing else touched. Full commit message: "Includes:
GEO_RESOLVED_TRADES_COUNT_SQL ..., threshold constants (GEO_ELO_LEGENDARY=2175,
POOL_C_MIN_RESOLVED_TRADES=10, etc.), POOL_C_GATE_WHERE ..., LEGENDARY_GATE_WHERE using
geo_elo_active (not geo_elo), refresh_pool_c() atomic helper, and pure functions
compute_win_rate / compute_geo_elo_active / derive_tier lifted exactly from their
respective source scripts." **No mention of `comprehensive_elo` or
`calibration_analysis.py` anywhere in the commit message or the diff.**

Read the file's actual content added by this commit (definitions section,
`monitoring/column_definitions.py:88-93,104-131,147-274`): `GEO_ELO_POOL_SANITY_FLOOR`,
`GEO_ELO_LEGENDARY`, `GEO_ELO_NEAR_LEGENDARY`, `GEO_ELO_ELITE`, `GEO_ELO_QUALIFIED`,
`POOL_C_MIN_RESOLVED_TRADES`, `POOL_C_GATE_WHERE`, `LEGENDARY_GATE_WHERE`,
`compute_win_rate`, `compute_geo_elo_active`, `derive_tier`, `refresh_pool_c` — every
one of these is geo_elo/Pool-C-scoped. Zero `comprehensive_elo` or
`calibration_analysis` symbol anywhere in this commit's content.

**The shared-file finding (not a comprehensive_elo finding, noted for completeness):**
`backtest_window_sql()` (target 2) was added to this **same file** by a later commit,
`8470e8b` "feat: canonical backtest-window population (tape_end, not resolution_date) —
B5 repointed" (`git log --oneline --follow -- monitoring/column_definitions.py`). So
`monitoring/column_definitions.py` does contain both geo_elo-tier constants (from
17f8d62) and `backtest_window_sql()` (from 8470e8b) side by side in one file — but
neither of those was ever `comprehensive_elo`- or `calibration_analysis.py`-related to
begin with, and (as shown above) the v2f pipeline doesn't even call
`backtest_window_sql()` — it computes tape_end independently. **No shared code path,
shared constant, or shared eligibility filter between the comprehensive_elo system and
the new metric's pipeline was introduced by this commit or exists today.**

---

## UNRESOLVED paths

None. Every consumer of every comprehensive_elo-family write target was traced to a
concrete stopping point: either a read-only display/report/simulation consumer with no
write-back to `positions`/`markets.trade_gap_flag`/`markets.category`/`trades.
trade_result`, or the one real `research_excluded` path, which was traced into
`monitoring/column_definitions.py`'s geo_elo/Pool-C infrastructure and confirmed absent
from every one of the five target files' actual SQL. `calibration_analysis.py` has no
write targets at all, closing that half of the question independently of the
comprehensive_elo trace.

---

*Trace performed 2026-08-16, read-only, no files modified. Prompted by the 2026-08-15
master handover's Section 6.5 flag ("comprehensive_elo / calibration_analysis.py:
analogous sign-error pattern flagged, out of scope all session, STILL OPEN and
live-affecting") — this trace establishes that "live-affecting" (true, for the
project's live monitoring/alerting/tiering surfaces) does not extend to "affects the
2026-08-15 OOS thesis result," which is a fully separate, self-contained computation.*
