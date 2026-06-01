# Performance Analyst Weekly Decision Record — 2026-06-01

**Date:** 2026-06-01
**Author:** performance-analyst-agent (run 5)
**Type:** Formal decision record

---

## Decision 1 — Legendary Tier (comprehensive_elo) Accuracy Below Random — Screen Via RQ0.2

**Trigger:** 30-day directional accuracy for Legendary tier (comprehensive_elo > 2175)
in the explicit clean pool has fallen to 35.92% (n=119 market-trader pairs) — worse than
random (50%). Previous week was 46% (May 25 feedback-loop run). Two consecutive weeks
below random baseline.

**Finding:** New accounts with comprehensive_elo > 3000 and low resolved_trades_count
(min 20) have entered the explicit clean pool this week. Specifically: 0x2aacd459 at
ELO 3325 with only 20 resolved trades. The ELO cap formula (1500 + resolved × 150)
allows ELO 4500 for 20 resolved trades — this trader passes the cap but shows the
profile of a potential artefact (extreme ELO, minimal track record).

**Context:** Prior ARB_BOT exclusion event (May 6 2026): 111 coordinated arb wallets
clustered at ELO 3308–3315 were excluded. Current clean pool max ELO is 3325 — close
to the old ARB_BOT cluster range. The leaderboard discovery event (May 24 session)
introduced new accounts that were flagged as NOT YET in the clean pool (fail
resolved_trades_count≥20). One week later, they have reached the threshold.

**Decision:** RQ0.2 must be run before the July 1 RQ1.1 rerun to screen these new
entrants. If cluster patterns emerge, apply ARB_BOT exclusion before the RQ1.1 run.
Do NOT run RQ1.1 on July 1 without first completing RQ0.2.

**Action owner:** Oscar (RQ0.2 decision) + quant-research-agent (execution)

---

## Decision 2 — geo_elo Is Now the Authoritative Accuracy Metric

**Trigger:** geo_elo Pool C shows 86.36% accuracy / Brier 0.1222 on geopolitics/elections
markets (n=22, 30d). This is within the "good" threshold (0.10–0.20 per Tetlock) and
well below the system target of < 0.20. comprehensive_elo is performing near-random (Brier
0.2354 on all binary markets, 35.92% accuracy for the Legendary tier).

**Decision:** For weekly reporting and Phase 5 gate tracking, geo_elo Pool C accuracy
on geopolitics/elections markets is the primary accuracy metric. comprehensive_elo metrics
are reported as secondary/diagnostic. The single-number Brier we target is geo_elo 30d.

**Implication for Phase 5 Gate 2:** The 2026-06-01-GEO-ELO-ACCURACY-001 finding (HIGH
confidence, n=22, 86.36%) counts toward the Gate 2 requirement of 3 HIGH confidence
findings with n≥20. Combined with 2026-05-07-ELO-QUALIFIED-002 (n=57), that is 2/3.
One more HIGH confidence finding from the feedback-loop Run 8 would complete Gate 2.

---

## Decision 3 — STR-003 Signal Detection Reset Acknowledged

**Trigger:** STR-003 migrated from comprehensive_elo to geo_elo criteria (May 31 2026).
Previous signals (STR003-001 through STR003-004) are now invalid under new criteria.
June 1 signal-agent run (08:00 UTC) is the first scan with new filters.

**Decision:** The reset is correct and necessary. comprehensive_elo-based signals showed
1/2 historical accuracy (50%) and were producing signals from traders with thin track
records (ELO 3323, 1 resolved trade in some cases). The geo_elo migration is the right
direction. The 2-week gap in signal production (May 25 to June 1+) is acceptable cost
for moving to a more reliable qualifier.

**Next milestone:** Monitor June 1 signal-agent output. If 0 qualifying signals after
2 consecutive Monday runs, review geo_elo threshold (currently ≥ 2175 for LEGENDARY).
Consider relaxing to ≥ 1800 (ELITE geo_elo) if LEGENDARY is too restrictive.
