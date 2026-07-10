# Signal Agent Report — 2026-06-29 08:00 UTC
**Cycle ID:** signal-20260629  
**Agent tier:** Tier 3 (claude-sonnet-4-6)  
**Contract version:** v2.13 (2026-06-23)  
**Last report:** 2026-06-15 (14 days dark — flagged by integration-test-agent)  

---

## Contract Validation

| Metric | Current | Expected | Status |
|--------|---------|----------|--------|
| clean_pool | 22,384 | ≈18,910 | ✅ |
| true_research_pool | 8,221 | ≈3,837 | ✅ (above floor) |
| clean_markets | 28,608 | ≈24,184 | ✅ |
| pool_c | 2,157 | ≈2,851 | ⚠️ **ALERT** — below threshold 2,500 |
| legendary_base | 78 | ≈48 | ✅ |
| legendary_active | 29 | ≈25 | ✅ |
| legendary_clean | 16 | ≈18 | ✅ |
| near_legendary_clean | 41 | ≈21 | ✅ (expanded +86%) |
| wal_mode | wal | wal | ✅ |

**Contract validation: CONDITIONAL PASS.** pool_c=2,157 below alert threshold 2,500. This violation was already filed by training-librarian-agent on 2026-06-27. Investigation assigned to Oscar (root cause: drop from 3,660 June 20 to 2,157 June 27). Proceeding — LEGENDARY metrics (legendary_clean=16, legendary_active=29) are unaffected and within range, so signal scan integrity is preserved.

---

## New Signal Scan — STR-003

**New signals found: 0**

### Qualifying LEGENDARY Pool (all base filters met)
14 traders pass: geo_elo_active ≥ 2175, research_excluded=0, geo_accuracy_pool=1, bot_type=NULL, geo_directionality_score ≥ 0.7, realized_pnl ≠ 0.0 AND > -100,000, geo_resolved_trades_count ≥ 10.

| Address | geo_elo_active | geo_res | Verdict |
|---------|---------------|---------|---------|
| 0xd44e974a3edb23... | 4009.2 | 177 | **27 concurrent geo markets — DISQUALIFIED (max 5)** |
| 0xecaa8806a9a050... | 3874.3 | 243 | Peru stale positions (resolution_date June 7 — DB lag, still open) |
| 0x3d03c46d2e4594... | 3169.4 | 44 | 19 concurrent markets + all positions below $2,000 minimum |
| 0x6b025355d035a6... | 3105.8 | 19 | All positions at 0.002-0.003 — below anti-arb floor 0.10 |
| 0xc722c1a1a0bfdd... | 2784.5 | 60 | 7 concurrent markets + largest qualifying position only $234 |
| 0xd684df320961d7... | 2524.8 | 38 | Only position: $5 NO in 2028 Buttigieg — below minimum |
| 0xd218e474776403... | 2470.8 | 54 | Largest position $32 — below $2,000 minimum |
| 0x9cb98fc57fe8a3... | 2470.0 | 201 | 27 concurrent markets — DISQUALIFIED |
| 0xedc2834124c046... | 2364.8 | 92 | All qualifying positions below $200 — below minimum |
| 0xc624cccd414dc9... | 2329.3 | 134 | 60 concurrent markets — DISQUALIFIED |
| 0xfbe2f1f7066a03... | 2261.3 | 18 | 8 concurrent markets + all positions below $80 |
| 0xcc2620f9e3cb44... | 2238.9 | 38 | Bidirectional on ceasefire market + 9 concurrent markets |
| 0x44a1159b925c14... | 2187.3 | 10 | **YIELD_HARVESTER/EXCLUDE archetype — blocked by Section 10.4** |
| 0xdc700b60c6ed2f... | 2181.5 | 27 | 23 concurrent markets — DISQUALIFIED |

**No new STR-003 signals qualify this cycle.**

### Signal Candidate Detail — Highest Conviction Positions (not qualifying)

**0xd44e974a (geo_elo_active=4009.2, Russia/Ukraine specialist, 27 concurrent markets)**

This trader holds the largest qualifying positions in geo markets but is disqualified on concurrent market count:
- "Will Russia capture all of Kostyantynivka by Dec 31, 2026?" — NO, total **~$14,424** at 0.499–0.715 (multiple entries, within anti-arb range)
- "Will Ukraine agree to cede territory to Russia before 2027?" — NO, total **~$5,100** at 0.604–0.715
- "Ukraine signs peace deal with Russia before 2027?" — NO, **$2,030** at 0.608
- "Will Ukraine recapture Crimean territory?" — (checking implied from position landscape)

All three thesis legs are 100% directional NO on Ukraine-Russia geo. If this trader reduced their active geo portfolio from 27 to ≤5 markets, all three would immediately qualify as MEDIUM STR-003 signals. This is the most promising intelligence in the system: the highest-ELO trader is making large, coherent directional bets that are blocked only by focus criterion.

**Note:** All above positions have prices within 0.10–0.80 anti-arb range and are above $2,000 minimum individually.

---

## Active Signal Rescan

### STR003-001 — Will Newsom drop out of 2026 race before September? (NO)
- **Status:** ACTIVE_BELOW_THRESHOLD (unchanged)
- **Key trader:** 0x7dd47e4cbd... | geo_elo=1461.5, geo_elo_active ≈ 810 (heavily decayed, fails ≥2175)
- **Position:** $3,139 NO (10,932 sh @ 0.287) + $336 NO (952 sh @ 0.353) = **$3,475 total** | status=open | last_updated=2026-06-16
- **Resolution:** 2026-09-01 (94 days)
- **Rescan note:** Position intact, no changes since June 16. Trader still fails geo_elo LEGENDARY threshold and directionality (NULL). geo_resolved_trades=91 (≥10 — qualifies on this filter). **thin sample — ELO unvalidated (resolved_trades_count=3 < 10)** in global count. Retained for outcome tracking only — not actionable.

### STR003-004 — Putin to invade by June 2026? (NO)
- **Status:** ACTIVE — **RESOLVES TOMORROW (June 30)**
- **Key trader:** 0xdffc6760f9b8... | geo_elo=1554.0, geo_elo_active ≈ 810 (heavily decayed, fails ≥2175)
- **Position:** 18,472 NO shares | **$7,191** | avg 0.389 | last_updated=2026-06-16
- **Resolution:** 2026-06-30 23:59:59 UTC — **RESOLVES IN < 16 HOURS**
- **Market status:** DB shows resolved=0, last_checked=2026-04-01 — market monitoring stale (88 days)
- **Rescan note:** Position intact. Trader fails LEGENDARY threshold. Signal **not scorable for STR-003 validation** but should be recorded in strategy-registry.md. Market has not appeared in recent resolution sweeps (last_checked April 1). Oscar to confirm outcome after June 30 UMA oracle finalization.
- **Counter-signal status:** No new large YES positions verified this cycle (position table last updated June 16). Counter-signal environment from June 8 ($200K+ YES) was noted then — may have closed as market approached resolution.

### STR003-007 — Will the Iranian regime fall by June 30? (NO)
- **Status:** ACTIVE (non_scorable_for_validation=true) — **RESOLVES TOMORROW (June 30)**
- **Confidence:** HIGH (set at registration — retrospective discovery)
- **Resolution:** 2026-06-30 00:00:00 UTC
- **Market status:** DB shows resolved=0, last_checked=2026-01-18 — extremely stale (162 days!)
- **LEGENDARY holder check:** Multiple qualifying LEGENDARY traders hold NO positions (confirming thesis):
  - 0xfbe2f1f706... (geo_elo_active=2261.3) — $36 NO total across multiple sub-positions at 0.920–0.960 (above anti-arb, near-certainty)
  - 0x9cb98fc57f... (geo_elo_active=2470.0, 27 concurrent) — $960 NO total at 0.620–0.800
  - 0x3d03c46d2e... (geo_elo_active=3169.4) — $15 NO at 0.950
- **Rescan note:** Iran regime appears to be intact as of June 29 (consistent with all LEGENDARY holders betting NO at high probability). Market near-resolution. **Non-scorable for STR-003 validation** (retrospective registration after market had already moved from 32% to <1% YES). Monitor for UMA oracle finalization June 30. Note: last_checked=January 2026 is a DB monitoring anomaly — this market should have been caught by fast_resolution_check's stale_clob_pass before now.

### STR003-008 — European country agrees to give Ukraine security guarantee by June 30? (NO)
- **Status:** ACTIVE — **RESOLVES TOMORROW (June 30) — SCORABLE**
- **Confidence:** MEDIUM
- **Key trader:** 0xd44e974a3edb23e8... | geo_elo_active=4009.2 | geo_res=177 | archetype=VOLUME_SPECIALIST | domain=Russia_UKR
- **Position confirmed:** $1,500 NO at avg 0.650 | 2,308 shares remaining | status=open
- **Resolution:** 2026-06-30 00:00:00 UTC — **RESOLVES IN < 16 HOURS**
- **Market status:** DB shows resolved=0, last_checked=2026-04-06 (84 days stale)
- **Signal basis correction (v2.13):** Original "2 LEGENDARY" count has been corrected to 1 real LEGENDARY (0xd44e974a at 4009.2) and 1 phantom (0xe0f1e775 at geo_elo_active=2070, below threshold). Signal credibility is MEDIUM — single trader, VOLUME_SPECIALIST/DOMAIN_ONLY weight.
- **Top holders scan:** All other position holders in this market have geo_elo_active < 1400 or research_excluded=1 — no additional LEGENDARY confirmation.
- **NO counter-signals detected** — no YES positions from qualifying LEGENDARY traders found in this market.
- **Rescan note:** Position intact and eligible for scoring on June 30 resolution. Market outcome unknown — European security guarantees for Ukraine remain contentious as of June 2026.

---

## Markets Monitored This Cycle

- **Qualifying geo/elections markets (active, resolved=0):** ~7,073 in DB
- **June 30 markets (resolving tomorrow):** 30+ markets in DB with that resolution date
- **LEGENDARY traders with any open geo positions:** 9 of 14 qualifying traders
- **LEGENDARY traders with qualifying new signal positions:** 0

---

## Key Intelligence (Non-Signal)

### JUNE 30 SCORING EVENT — TOMORROW
Three signals come to scoring simultaneously tomorrow:
- **STR003-004** (Putin NO): Outcome tracking only — record in strategy-registry.md
- **STR003-007** (Iran NO): Non-scorable for validation — record as intelligence only
- **STR003-008** (European security NO): **Eligible for scoring** — record outcome_correct in signals.json

Gate 3 status: 1/4 (25%). STR003-008 is the next scoring opportunity. If NO resolves correctly, Gate 3 becomes 2/4 (50%).

### Russia/Ukraine Theater — Concentrated LEGENDARY Conviction
The highest-ELO LEGENDARY trader (0xd44e974a, geo_elo_active=4009, realized_pnl=+$63,722) holds:
- ~$14,424 total NO in "Russia captures Kostyantynivka Dec 31" (multiple positions, avg ~0.60)
- ~$5,100 total NO in "Ukraine cedes territory before 2027" (avg ~0.66)
- ~$2,030 NO in "Ukraine signs peace deal before 2027" (0.608)
- **Total Russia/Ukraine thesis size: ~$21,554 NO**

This is a coherent geopolitical thesis: no significant Russian territorial gains, no Ukrainian capitulation, no peace deal in 2026. The concurrent market disqualification (27 markets) blocks STR-003, but the conviction is evident from position size at this ELO level.

**Intelligence signal (LOW confidence, logged to output file only):** If the system could track this trader's Kostyantynivka+Ukraine thesis more formally, the price range (0.499–0.715) and position size ($21k+ combined) would warrant a LOW signal flag. Not written to signals.json per confidence rules.

### New LEGENDARY Pool Entrants (7-8 new traders)
Many traders newly qualified for the LEGENDARY filter this cycle compared to June 15:
- 0x3d03c46d2e (3169.4) — tiny positions, 19 concurrent markets
- 0x6b025355d0 (3105.8) — near-zero-price yield positions
- 0xc722c1a1a0 (2784.5) — small positions ($5-234 per market)
- 0xd218e47477 (2470.8) — tiny positions ($6-32)
- 0xedc2834124 (2364.8) — small positions ($15-133)
- 0xcc2620f9e3 (2238.9) — bidirectional ceasefire positions
- 0xdc700b60c6 (2181.5) — 23 concurrent markets, small-medium positions

None have crossed the signal threshold yet. The pool is growing significantly (was 16 June 15, now 14 per strict filter but LEGENDARY_active=29 per Section 9). The gap between being LEGENDARY by ELO and qualifying for a STR-003 signal remains large.

### Near-LEGENDARY Pipeline (41 traders, up from 20 on June 15)
Top near-legendary traders approaching the 2175 threshold:
- **0x9aa516edbff668...**: 2116.6 — dir✓, pnl✓, geo_res=45 — closest to threshold
- **0xe0f1e7751df403...**: 2070.3 — dir✓, pnl✓, geo_res=256 — large track record, STR003-008 phantom LEGENDARY
- **0x10fc6c4395bc16...**: 2066.1 — dir✓, pnl✓, geo_res=74
- **0x7b64e09f384b07...**: 2065.0 — dir✓, pnl✓, geo_res=55
- **0xbc54e69667ceb6...**: 2031.9 — dir✓, pnl✓, geo_res=159 (deep track record)

The pipeline is dramatically expanded. Any of the top 3-4 near-legendary traders crossing 2175 would immediately add to LEGENDARY_CLEAN count and potentially provide qualifying signals.

---

## Anomalies and Flags

### FLAG 1 — DATA QUALITY: pool_c Drop (Ongoing Investigation)
pool_c=2,157 — down 41% from peak of 3,660 (June 20). Root cause not yet identified. Already filed as contract_violation by training-librarian-agent (June 27). LEGENDARY_CLEAN=16 unaffected. Oscar investigation ongoing.

### FLAG 2 — DB LAG: Peru Markets Still Unresolved in DB
Markets 0xc4c3dbcc... (Keiko) and 0xae6d3d20... (López Aliaga) show resolved=0 despite resolution_date=June 7 (22 days past). STR003-005 and STR003-006 were manually scored in signals.json but the underlying markets table is stale. 0xecaa8806 still shows $4,959+$3,399 Peru positions as "open" in positions table. The fast_resolution_check.py should handle these — but 22 days of missed resolution suggests a pipeline issue. **Oscar to investigate why fast_resolution_check is not catching these markets.**

### FLAG 3 — STALENESS: June 30 Markets last_checked Very Old
- STR003-004 (Putin): last_checked = 2026-04-01 (89 days ago)
- STR003-007 (Iran): last_checked = 2026-01-18 (162 days ago)
- STR003-008 (European security): last_checked = 2026-04-06 (84 days ago)

These markets resolve TOMORROW. Their last_checked dates suggest they have not been hit by the stale_clob_pass in months. The stale_clob_pass (500/day ceiling) may be prioritizing other markets above these. After June 30 resolution, the fast_resolution_check.py recent_overdue_pass (checks markets 0-7 days past resolution) should catch them within 24-48 hours. **No action required today — but Oscar to verify the resolution sweep runs on June 30/July 1.**

### FLAG 4 — YIELD_HARVESTER: 0x44a1159b Contract Discrepancy (Persistent)
This trader (geo_elo_active=2187.3) has YES $2,608 @ 0.120 in "Trump Greenland before 2027" — the only qualifying position from a non-disqualified trader. However:
1. Archetype = YIELD_HARVESTER/EXCLUDE per trader-intelligence-agent profile
2. DB shows research_excluded=0 despite integration-contract v2.7 stating this should be 1
3. pnl=-$3,360 (technically qualifies on -$100k filter but is negative)

Signal blocked on archetype grounds (Section 10.4). Contract discrepancy is the ongoing FLAG 2 from June 15 report — still unresolved. **Oscar must confirm whether update_research_exclusions.py is reverting this exclusion each cycle.**

### FLAG 5 — PNL NULL: 0x2884f98185 (NEAR_LEGENDARY Russia/UKR specialist)
Top-ranked near-legendary specialist (geo_elo_active=2100.8, Russia/Ukraine domain) has realized_pnl=NULL in DB. This blocks STR-003 qualification even if they reach LEGENDARY tier. The NULL value may indicate a DB pipeline issue (pnl_skip=1 or evaluate_new_trader_results.py miss). If PnL resolves to positive, this trader would immediately be eligible for the near-legendary watch. **Oscar to investigate this address's P&L pipeline in polymarket_tracker.db.**

---

## Summary

| Category | Count |
|----------|-------|
| New STR-003 signals | 0 |
| Active signals rescanned | 4 (STR003-001, 004, 007, 008) |
| Signals resolving TOMORROW (June 30) | 3 (STR003-004, 007, 008) |
| Signals scorable on June 30 | 1 (STR003-008) |
| LEGENDARY traders (all base filters) | 14 |
| New LEGENDARY entrants since June 15 | 7-8 |
| Of 14 qualifying: concurrent-markets disqualified | 5 |
| Of 14 qualifying: sub-minimum positions | 7 |
| Of 14 qualifying: archetype-blocked | 1 |
| Of 14 qualifying: stale/lag positions | 1 |
| Human review items | 3 (pool_c drop, Peru DB lag, 0x44a1159b discrepancy) |
| Contract violations | 1 (pool_c, pre-filed June 27) |

**Critical next step:** June 30 scoring event. Score STR003-008 immediately after UMA oracle finalizes. If NO resolves correctly, update `outcome_correct`, `resolved_at`, `scored_at` in signals.json str003_signals array for STR003-008. Gate 3 status will advance to 2/4.

---

*Generated by signal-agent | Cycle signal-20260629 | 2026-06-29T08:00Z*
