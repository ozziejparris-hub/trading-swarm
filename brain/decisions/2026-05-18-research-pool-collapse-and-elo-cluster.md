# Decision Record — 2026-05-18: Research Pool Collapse and New ELO Cluster

**Date:** 2026-05-18  
**Recorded by:** performance-analyst-agent (run 3)  
**Status:** OPEN — requires Oscar action

---

## Issue 1: Research Pool Collapse (493 → 104)

### What happened

The explicit clean pool (`research_excluded=0 AND resolved_trades_count>=20 AND bot_suspect=0 AND wash_trade_suspect=0`) has dropped from 493 traders (May 13) to 104 traders (May 18).

The `research_excluded=0` raw count has simultaneously jumped from 604 to 7,852. This means `update_research_exclusions.py` is now setting `research_excluded=0` for 7,748 traders who fail the `resolved_trades_count>=20` criterion.

### Diagnostic evidence

```sql
-- Run May 18 against polymarket_tracker.db
SELECT COUNT(*),
  SUM(CASE WHEN resolved_trades_count >= 20 THEN 1 ELSE 0 END),
  SUM(CASE WHEN resolved_trades_count < 20 THEN 1 ELSE 0 END)
FROM traders WHERE research_excluded = 0;
-- Result: 7852 | 104 | 7748
```

### Impact

- Phase 5 Gate 2 progress is blocked until the pool is fixed
- Any agent using `WHERE research_excluded=0` without the explicit filter runs against junk data
- All accuracy statistics computed after May 13 must be treated as suspect unless using the explicit 4-criterion filter
- The one valid HIGH confidence finding (`2026-05-07-ELO-QUALIFIED-002`) was computed with 493 traders — its validity is unaffected (computed before this regression)

### Required action

Oscar to inspect `first-repo/scripts/update_research_exclusions.py`. The "set eligible" block should only clear `research_excluded` for traders with `resolved_trades_count >= 20 AND bot_suspect = 0 AND wash_trade_suspect = 0`. Currently it appears to be applying a looser criterion (possibly just `resolved_trades_count > 0` or similar).

### Workaround until fixed

All research agents must use the explicit 4-criterion filter:
```sql
WHERE research_excluded = 0
  AND resolved_trades_count >= 20
  AND bot_suspect = 0
  AND wash_trade_suspect = 0
```
Brief any spawned agents with this note before running.

---

## Issue 2: New High-ELO Cluster (ELO > 3,500)

### What happened

Max ELO jumped from 3,471.3 (May 13) to 4,305.1 (May 18). Live query confirms 39 traders with `comprehensive_elo > 3500 AND research_excluded = 0`.

### Precedent

May 6 ARB_BOT exclusion removed 111 traders with ELO 3,308–3,315 — coordinated arbitrage wallets from Nov 2025 geopolitics markets. Their ELO was a measurement artefact from high-volume coordinated positioning, not genuine forecasting skill. The same structural pattern (tight ELO cluster above the previous max) applies here.

### Impact

- The legendary tier count inflated from 142 to 235 (partly from the pool inflation bug, partly from the new cluster)
- If these 39 traders enter the explicit clean pool, their inflated ELO would bias QUALIFIED tier accuracy calculations
- STR-003 and STR-004 signal generation reads from legendary traders — arb bots at ELO 4,305 could generate false signals

### Required action

Run RQ0.2 (bot detection) on first-repo targeting traders with `comprehensive_elo > 3500`. Check for:
1. Same-market entry clustering (multiple wallets entering same side within minutes)
2. Uniform position sizing
3. Entry timestamps tightly correlated across wallets

The RQ0.2 gate is officially due 2026-06-13, but this anomaly warrants an early run. Recommend bringing it forward to this week.

---

## Issue 3: feedback.json Corruption (Resolved This Session)

### What happened

`brain/feedback.json` was overwritten by research-scout-agent (Qwen3-Coder 30B-A3B, Tier 2.5) with a scout cycle summary. The agent's task template contains a path routing bug causing it to write to `brain/feedback.json` instead of its own output directory.

### Resolution

Restored from git `d529c0a` (docs: backtest-agent RQ0 data integrity gates 2026-05-13) in this session. Confirmed structure: `approved=4, rejected=1`.

### Required action

Fix the research-scout-agent task template in `orchestrator/task_templates/`. The agent should:
- Write cycle summaries to `brain/agent-outputs/research-scout/` or `brain/research-scout/pending-review/`
- If updating feedback.json at all, only append to the `scout_cycles` array key — never use `json.dump()` to overwrite the whole file

This is two consecutive corruptions (May 12: empty, May 17: overwritten). If not fixed, it will corrupt feedback.json every daily cycle.

---

## Prior related decision

See `brain/decisions/2026-05-05-elo-calibration-drift-investigation.md` for the May 5 ELO pool integrity investigation that first identified the research_excluded discrepancy (111 traders at that time).
