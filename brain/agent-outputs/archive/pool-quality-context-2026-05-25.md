# Pool Quality — Historical Context
**Date:** 2026-05-25  
**Purpose:** Synthesise everything decided or discovered about monitored pool quality, trader selection criteria, and the pool-size-vs-quality tension, to inform what RQ-GEO-ELO-001 should actually do.

---

## Q1 — Has "quality over quantity" been formally decided?

**No. It has never been formally stated as a principle.**

The closest event is a single line in the May 24 session summary (Server Setup 10):
> "Pool pruning strategy — 11,975 traders is too many, need quality threshold — future session"

That is the first and only explicit statement that pool size is a problem. It is listed as next-session priority #4, not a resolved decision. No target pool size, no pruning criteria, no implementation date has been set.

What has happened organically is a two-tier system:
- **Monitored pool** (`is_flagged=1`): broad, used for live signal generation. Grows continuously via leaderboard discovery.
- **Research pool** (explicit 4-criterion filter): strict, used for ELO validation and academic analysis.

The distinction between these two tiers has evolved through bug fixes and workarounds rather than a deliberate architectural decision.

---

## Q2 — Are there existing quality thresholds for pool entry?

**Yes — but they apply to different layers inconsistently.**

### Entry into the monitored pool
`discover_leaderboard_traders.py` (the primary growth engine):
```
MIN_GEO_MARKETS = 3     # must have traded 3+ distinct geopolitics markets
MIN_TRADES      = 10    # minimum trade count
MIN_VOLUME      = $1,000 # minimum total volume
```

`promote_high_pnl_traders.py` (daily maintenance step 2):
```sql
WHERE realized_pnl > 50000
  AND bot_type IS NULL
  AND wash_trade_suspect = 0
  AND bot_suspect = 0
```

### Entry into the research pool
The authoritative clean pool requires all four criteria simultaneously:
```sql
WHERE research_excluded = 0
  AND resolved_trades_count >= 20
  AND bot_suspect = 0
  AND wash_trade_suspect = 0
```
This is enforced by explicit query construction — NOT by a single flag. The `research_excluded` flag alone is unreliable (see Q1 context: a bug in `update_research_exclusions.py` caused it to match 7,852 traders when only 104 met the ≥20 resolved trades criterion).

### ELO tier thresholds
These are thresholds applied AFTER a trader is in the pool:
- LEGENDARY: comprehensive_elo > 2175
- ELITE: comprehensive_elo > 1800  
- QUALIFIED: comprehensive_elo ≥ 1200

**Critical gap:** There is no minimum resolved-trade requirement for entry into the monitored pool. A trader with 10 total trades and 1 resolved trade can be in the monitored pool and appear in ELO tier calculations.

---

## Q3 — Has pool pruning ever been discussed or implemented?

**Discussed once (May 24), never implemented.**

Prior events that are related but distinct from pruning:
- **May 6 (inferred from May 5 decision doc):** 111 ARB_BOT traders removed from ELO calculations when the bot exclusion was upgraded. These were coordinated arbitrage wallets whose ELO was a measurement artefact. This was exclusion-from-analysis, not removal from the pool.
- **April 30 audit:** `update_research_exclusions.py` bug corrected — 857 traders correctly flagged as research-eligible vs earlier inflated counts of 9,993 and 6,829. This was a flag correction, not a pool size reduction.
- **May 18:** Research pool dropped from 493 to 104 due to a regression in `update_research_exclusions.py` setting `research_excluded=0` for 7,748 traders who lack ≥20 resolved trades. Workaround issued; root cause not yet fixed.

None of these constitute pruning in the sense of removing traders from `is_flagged=1`. The monitored pool has only ever grown.

---

## Q4 — What was the original intent of leaderboard discovery?

**To capture specific high-quality traders missed by organic monitoring — not to grow the pool indefinitely.**

From the `discover_leaderboard_traders.py` docstring (verbatim):
> "This captures low-frequency high-conviction traders like Magamyman who trade rarely but in large size across our target markets."

The script was designed to find traders who:
1. Are active in geopolitics markets specifically
2. Trade infrequently but at scale (Magamyman archetype)
3. Are invisible to the live feed because they enter positions between 15-minute monitoring cycles or in markets the monitor doesn't scan in real time

**What actually happened:**

| Date | Pool size | Event |
|------|-----------|-------|
| ≤2026-05-17 | ~1,412 | Pre-discovery baseline |
| 2026-05-18 | ~7,876 | First Sunday leaderboard discovery run (+6,464 traders) |
| 2026-05-20 | ~7,900 | Stable post-discovery |
| 2026-05-24 | ~11,975 | After second Sunday discovery run (+4,075 traders) |

The pool grew 748% in one week. The Sunday maintenance step now takes 7.4 hours, with leaderboard discovery consuming 6.3h of that — the script is scanning far more markets and traders than the --limit 100 parameter implies (the limit appears to control per-market API batching, not total trader additions).

This growth was not the original intent. The script's minimum thresholds (3 geo markets, 10 trades, $1k volume) are permissive enough to admit a large fraction of Polymarket's active geopolitics participant base.

---

## Q5 — How does this context change what RQ-GEO-ELO-001 should actually do?

RQ-GEO-ELO-001 as pre-registered proposes computing `geo_elo` from resolved geopolitics trades on the clean pool, then testing whether category-conditioned ELO restores the LEGENDARY accuracy above 60%. The pre-registration is methodologically sound but needs three adjustments given pool quality context:

### Adjustment 1 — Enforce a geo-trade minimum for geo_elo inclusion

The pre-registration computes `geo_elo` for any trader with at least one resolved geopolitics trade. With 11,975 monitored traders and only 11.8% having ELO behavioral coverage, a large fraction of the pool has thin or zero geopolitics trade history. A trader with 1 resolved geopolitics trade will get a highly volatile `geo_elo` that has no predictive validity.

**Recommended addition:** Add `geo_resolved_trades_count >= 10` as a minimum for a trader to receive a `geo_elo` tier assignment. Traders below this threshold get `geo_elo = NULL` and are excluded from tier accuracy counts. This mirrors the existing `resolved_trades_count >= 20` threshold in the research pool but applied to the geopolitics subset.

### Adjustment 2 — Exclude the new high-ELO cluster (ELO > 3,500)

The May 18 decision doc identified 39 traders with `comprehensive_elo > 3500` appearing after the Sunday discovery run. The previous cluster at ELO 3,308–3,315 was confirmed as ARB_BOT coordinated arbitrage and removed in May 6 maintenance. The new cluster has the same structural pattern (tight ELO band above previous max, appearing after a leaderboard discovery event).

RQ0.2 bot detection is due (overdue since May 13) specifically for this cluster. Until it runs, **exclude traders with comprehensive_elo > 3,500 AND bot_type IS NULL from geo_elo tier assignment** as a precautionary measure. These traders would otherwise dominate the LEGENDARY tier and potentially corrupt Phase 2 accuracy results.

### Adjustment 3 — Treat pool pruning as a prerequisite, or run concurrently

The pre-registration reads the live clean pool from `integration-health.json` and applies the 4-criterion filter. This is correct. However, the research pool currently has an unresolved bug (`update_research_exclusions.py` miscounting — 104 clean vs expected ~500+). If this bug is unresolved when RQ-GEO-ELO-001 runs, Phase 2 accuracy results will be computed against a degraded pool.

**Recommended sequencing:**
1. Fix `update_research_exclusions.py` to correctly enforce `resolved_trades_count >= 20` (May 18 open item — Oscar's action)
2. Run RQ0.2 bot detection on ELO > 3,500 cluster
3. Then run RQ-GEO-ELO-001

If pool pruning (May 24 priority #4) happens before RQ-GEO-ELO-001 runs, geo_elo will be computed on a cleaner, smaller pool — which will improve the quality of the accuracy measurement. The two tasks should be coordinated.

### What RQ-GEO-ELO-001 does NOT need to change

- The hypothesis itself is correctly motivated — category pollution is the documented cause of the LEGENDARY tier inversion, sourced from two handover documents and the Nechepurenko paper
- The Phase 2 accuracy check methodology is correct
- The 60% threshold for LEGENDARY geo_elo accuracy is the right pass criterion (Phase 5 gate)
- The pre-registration's stipulation to "read pool size live, never hardcode" is exactly right given the instability documented above

---

## Summary Table

| Question | Answer |
|----------|--------|
| "Quality over quantity" formally decided? | No — flagged once (May 24) as future work |
| Quality thresholds for pool entry? | Yes but inconsistent: monitored pool (soft: 3 geo markets, 10 trades, $1k), research pool (strict: ≥20 resolved trades + bot/wash exclusions), high-P&L route (>$50K) |
| Pool pruning discussed? | Yes — May 24, once, as future priority. Never implemented. |
| Original intent of leaderboard discovery? | Find specific low-frequency high-conviction traders — NOT grow the pool indefinitely. Intent has been exceeded by 748% growth in one week. |
| RQ-GEO-ELO-001 implications? | Add geo_resolved_trades_count >= 10 minimum; exclude ELO > 3,500 cluster pending bot audit; fix update_research_exclusions.py bug first. Core hypothesis unchanged. |

---

*Written: 2026-05-25*  
*Sources: brain/decisions/ (all 16 files), findings.json (all entries), strategy-registry.md, research-directions.md, brain/agent-outputs/elo-accuracy-gap-context-2026-05-25.md, scripts/discover_leaderboard_traders.py, scripts/promote_high_pnl_traders.py*
