# Decision Record — Pool C Decline Investigation

**Date:** 2026-06-29
**Raised by:** performance-analyst-agent (run 8)
**Severity:** HIGH
**Status:** CLOSED — ARTIFACT (investigated 2026-06-29, no bug found)

---

## Observation

Pool C (geo_accuracy_pool=1) has declined 41% from its June 20 peak:

| Date | Pool C | Source |
|------|--------|--------|
| Jun 15 | 2,875 | integration-test + signal-agent rescan |
| Jun 20 | 3,660 | integration-test Jun 20 report |
| Jun 27 | 2,155 | training-librarian Section 9 check |
| Jun 29 | 2,157 | performance-analyst Section 9 query |

Alert threshold: 2,500. Currently 13.7% below threshold and holding at ~2,157 for 2 days.

## Impact

- Pool C is the basis for STR-003 signal qualification and all geo_elo accuracy validation
- LEGENDARY clean count (16) may decline further if Pool C shrinks
- July 1 research questions (RQ-POOL-QUALITY-001, RQ-SECTOR-001, RQ-EXEC-001) all depend on Pool C integrity
- The validated Pool C full-2026 accuracy (70.7%, n=444) was computed when Pool C was ~2,875 — its validity on the current smaller pool is unconfirmed

## Root Cause Hypothesis

Unknown. The decline started between Jun 20 and Jun 27 — coincides with:
- training-librarian weekly run Jun 27 (detected but did not identify cause)
- Regular daily maintenance continuing throughout

Possible causes:
1. `update_research_exclusions.py` changed qualification logic or thresholds
2. `update_geo_elo.py` setting more NULL geo_elo_active values
3. Bot detection excluding previously-qualifying traders
4. `geo_directionality_score` recalculation excluding traders who dropped below 0.7 threshold (not required for Pool C, but if directionality=NULL triggers exclusion)

## Recommended Investigation Query

```sql
-- Compare currently-excluded vs previously-included Pool C traders
SELECT 
  COUNT(CASE WHEN geo_accuracy_pool = 0 AND geo_elo IS NOT NULL THEN 1 END) as excluded_with_geo_elo,
  COUNT(CASE WHEN geo_accuracy_pool = 0 AND geo_elo IS NOT NULL 
               AND geo_resolved_trades_count >= 5 THEN 1 END) as excluded_5plus_geo_trades,
  COUNT(CASE WHEN geo_accuracy_pool = 0 AND geo_elo IS NOT NULL 
               AND geo_resolved_trades_count >= 5
               AND geo_directionality_score IS NOT NULL THEN 1 END) as excluded_full_criteria,
  COUNT(CASE WHEN geo_accuracy_pool = 0 AND geo_elo IS NOT NULL
               AND geo_resolved_trades_count >= 5
               AND geo_directionality_score IS NOT NULL
               AND bot_type IS NULL 
               AND wash_trade_suspect = 0 
               AND bot_suspect = 0 THEN 1 END) as excluded_clean
FROM traders;
```

## Action Required

Oscar to run the investigation query above against first-repo DB. If thousands of traders meet Pool C criteria but have `geo_accuracy_pool=0`, something in the daily maintenance pipeline changed the pool qualification. Compare recent daily maintenance logs:

```bash
tail -100 /home/parison/projects/first-repo/logs/daily_maintenance.log | grep -E "pool_c|geo_accuracy|research_exclusion"
```

## Non-Action Items

- Do NOT manually set geo_accuracy_pool=1 without understanding root cause
- The previous contract violation (Jun 8, legendary_base) was self-correcting — this one is not

---

## Resolution (2026-06-29)

**ARTIFACT — no pool bug.** Investigated via elo_snapshots table and live gate query.

Key findings:
- `stored geo_accuracy_pool=1` = 2,185; live canonical gate = 2,185; **gap = 0**. Nothing is being wrongly excluded.
- The "3,660 peak" (June 20) was measured during the re-inflation period when `update_research_exclusions.py` was running with the old `>=5` gate (pre-session-#39 fix). It was never a legitimate Pool C count.
- The June 18 snapshot showed 4,333 because it captured the pre-session-#38 state where `geo_resolved_trades_count` stored total trades (not distinct markets). The 2,191 "dropped" traders now have 3–9 distinct geo markets (correctly below the >=10 threshold). 98.9% of dropouts fail solely on `geo_resolved_trades_count < 10`.
- The cliff on June 22–23 was session #39 applying the canonical fix. Pool C has grown cleanly since: 1,961 → 2,185 over six days at ~45/day.

**Action taken:** Alert threshold recalibrated.
- `integration-contract.md` Section 9: `pool_c` expected `≈ 2,851 → ≈ 2,185`, alert `< 2,500 → < 1,700`
- `integration-contract.md` Section 10.2: Pool C size `≈ 2,851 → ≈ 2,185`
- `training-librarian-agent.md`: runtime check min `2500 → 1700`

Threshold logic: 1,700 is 261 below the post-fix minimum (1,961 on June 23) — a real alarm requires losing 485+ traders from today's pool. This distinguishes a genuine data-integrity failure from normal variation.
