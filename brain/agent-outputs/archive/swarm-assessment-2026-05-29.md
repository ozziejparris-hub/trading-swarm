# Swarm Readiness Assessment — Pre-STR-003
**Date:** 2026-05-29
**Assessor:** Claude Code (Sonnet 4.6)
**Scope:** Signal pipeline, agent health, research queue, infrastructure readiness

---

## 1. Signal Pipeline — STR-003 Blockers

**Current status: EXPERIMENTAL — cannot fire a real signal.**

Blockers in order of severity:

### Blocker 1 — Concurrent markets criterion is structurally incompatible (CRITICAL)
Signal-agent's 2026-05-25 rescan found **all 21 verified LEGENDARY traders (≥10 resolved geo trades) disqualified** by holding 15–1,626 concurrent markets. The focus criterion was designed to filter LP/market-makers, but LEGENDARY traders by nature hold large portfolios. STR-003 as written cannot fire on any trader who has been in the market long enough to hold a significant ELO.

Fix: change the concurrent market check from `total_concurrent_markets` to `concurrent_open_geo_markets`. A trader holding 500 crypto markets is not disqualified from having a focused bet on a geopolitics market.

**This is deprioritised (per 2026-05-28 session) because the pool is dormant, but it must be resolved before the first LEGENDARY signal can fire.**

### Blocker 2 — geo_elo LEGENDARY pool is dormant
All 21 geo_elo LEGENDARY traders (≥10 resolved geo trades, geo_elo ≥ 2175) stopped trading **December 31, 2025**. They are Haley-2027 specialists. Zero are active in 2026 markets.

The 62 traders promoted via the resolution sweep (2026-05-28) are new entrants. Until they accumulate 5+ resolved geo trades and earn geo_elo tiers, STR-003 has no qualified signal source.

**Expected unblock:** as 2026 geo markets resolve (next cluster: Putin invasion market ~June 2026, ceasefire variants throughout Q2–Q3).

### Blocker 3 — geo_elo OOS validation is inconclusive, not complete
RQ-GEO-ELO-003 result: LEGENDARY OOS accuracy 9.4%, but this is **2 traders, 1 market** (Russia-Ukraine ceasefire Q2 2026). The failure condition fired but is statistically meaningless. QUALIFIED OOS at 58.7% (4 markets, 167 trades) is the most reliable OOS estimate — 15pp degradation from in-sample 73.7%, but still above baseline.

Advancing STR-003 to PENDING_VALIDATION requires OOS LEGENDARY accuracy ≥55% across 5+ distinct markets. Current: 1 market.

**Expected unblock:** 20+ OOS geo markets resolving in 2026–Q3.

### Blocker 4 — Active signal backing traders have thin samples
The 4 current signals in signals.json (Newsom NO, UN Security Council NO, Fed NO, Putin NO) are backed by traders with **only 1–4 resolved geo trades** each. geo_elo is not meaningful at this depth. These are MEDIUM confidence, not LEGENDARY.

### Blocker 5 — Two signals awaiting decisions
- **Signal 2 (UN Security Council):** flagged for stale-market exclusion policy — open since 2026-05-18. Oscar decision outstanding.
- **Signal 4 (Putin invasion):** resolves ~June 2026. Need outcome recording in strategy-registry.md.

### Summary
STR-003 cannot fire until: (a) Blocker 1 (concurrent criterion) is fixed, (b) active LEGENDARY geo traders emerge from 2026 market resolutions. Both are data-accumulation problems, not architectural failures. The earliest realistic STR-003 live signal is Q3 2026 if new geo markets resolve and new traders score into LEGENDARY tier.

---

## 2. Agent Health

### Running correctly
| Agent | Evidence |
|-------|----------|
| **feedback-loop-agent** | Run #8 completed 2026-05-25. Cron active. 8 runs > Phase 5 gate of 4. |
| **daily_maintenance.py** | Last run 2026-05-29T06:45:37. integration-health contract_valid: true. clean_pool: 11,983. |
| **signal-agent** | Last rescan 2026-05-25. 4 signals rescanned, 2 confirmed, 2 flagged. No crash evidence. |
| **orchestrator** | Running. contract_violation spam fixed 2026-05-28. No current alerts. |

### Stuck / silently stale
| Agent | Status | Issue |
|-------|--------|-------|
| **backtest-agent (backtest-lh001-v3-20260521)** | `respawning`, retries: 1 | Started 2026-05-21 — 8 days in registry. LH-001 v2 validation completed same day per signals.json and strategy-registry.md. This task is **likely superseded** — the work it was dispatched to do was already completed. Registry entry is stale. |
| **quant-research (geo-elo-001-20260525)** | `respawning`, retries: 1 | Started 2026-05-25 — 4 days in registry. The geo_elo work completed in the same session per 2026-05-25/26 summaries. This task is **also likely stale** — the output (geo_elo column populated for 435 traders) already exists. |

Both stale tasks should be manually closed in agent_registry.json (`status: "completed"`) to prevent the orchestrator cycling on them. The work was done via manual session, not via spawned agent.

### Low-quality output risk
- **feedback-loop-agent:** Run 8 produced `sample_size: 0` for signal accuracy (0 resolved signals). The finding is technically correct but signals the system is not accumulating outcomes. The finding quality degrades each week this persists — the agent is doing its job but there is nothing for it to measure.

---

## 3. Research Pipeline

### Pre-registered tasks, in recommended run order

**1. RQ1.1 — ELO persistence across periods (July 1, 2026)**
- Script: `rq1_1_elo_persistence.py` — ready and validated
- Current: n=10 (< 30 minimum). Gate fires correctly, rescheduled to July 1.
- Phase 5 gate. No action needed until July 1.
- Risk: Period 2 (April–June) may still be thin. Extend to September 1 as pre-planned.

**2. STR-003 OOS accumulation (passive, ongoing)**
- 6 OOS markets so far. Target: 20+ with LEGENDARY representation in 5+ distinct markets.
- No action needed — data accumulates as 2026 geo markets resolve.
- Watch: Putin invasion market resolving ~June 2026. If LEGENDARY traders were active there, this adds to the OOS pool.

**3. RQ3.2 pre-registration — elite consensus vs market price**
- Phase 5 gate. **Not yet pre-registered.** No pre-registration file found in `brain/strategy-notes/`.
- quant-research-agent needs to write the hypothesis. Oscar needs to approve.
- Should run after RQ1.1 since they share the "do elite traders add value" theme.
- Priority: HIGH — blocks Phase 5 gate.

**4. LH-001 expansion (passive, event-driven)**
- Needs 5+ additional independent geopolitics events beyond Haley and Iran.
- Passive — triggers when new qualifying events appear in DB.
- Currently blocked by sparse event coverage. Not a near-term task.

**5. STR-001b validation (passive, waiting for data)**
- 0 qualifying signals historically. Exclusive convergence filter (3+ same side, <2 opposing) almost never fires.
- Very low priority. STR-003 and STR-004 have superseded as the better signal designs.

**6. STR-004 accumulation (passive)**
- Founding case resolved NO (n=1). Need 9 more resolved signals before conclusions.
- Passive — accumulates as new markets resolve. No action.

---

## 4. Pre-STR-003 Infrastructure Work (Do Now)

These are the highest-leverage improvements to make *before* the first LEGENDARY signal appears, so the system is ready to act correctly.

### Fix 1 — Concurrent criterion: total → geo-specific (HIGH PRIORITY)
Change signal-agent's STR-003 qualification logic from `concurrent_markets ≤ N` to `concurrent_open_geo_markets ≤ N`. This unblocks the strategy from its current structural incompatibility. Without this, every LEGENDARY trader who emerges will be immediately disqualified.

This was deprioritised on 2026-05-28 because the pool is currently dormant. But the new cohort from the resolution sweep (62 traders) will start accumulating geo trades in Q2–Q3. Fix this now, before they qualify.

### Fix 2 — Automated STR-003 signal outcome scoring (HIGH PRIORITY)
`score_insider_signals.py` exists for insider_signals. There is **no equivalent for STR-003 signals in signals.json**. The 4 current signals (Newsom, UN Security Council, Fed, Putin) will resolve at some point with no automated outcome recording.

Build `scripts/score_str003_signals.py`:
- Reads signals.json for STR-003 entries
- Checks Gamma API for resolution status and outcome
- Writes `outcome_correct`, `resolved_at`, `accuracy_at_resolution` back to signals.json
- Appends a HIGH-confidence finding to findings.json once n ≥ 10 resolved

Add to `daily_maintenance.py` step 2d.

### Fix 3 — Stale market cleanup (MEDIUM)
5 of 7 concurrent markets for Signal 3's key trader are 2025/template stale markets. These inflate the concurrent market count and contribute to disqualification. Stale cleanup was flagged on 2026-05-25 as "still outstanding." Completing this reduces false negatives.

### Fix 4 — geo_elo incremental update trigger (MEDIUM)
The resolution sweep promotes new traders to Pool C but does not automatically calculate their geo_elo. Currently geo_elo calculation is manual (done via CC session). As 62 newly-promoted traders accumulate geo trades, each one needs geo_elo scored to be STR-003-eligible.

Add to `daily_maintenance.py`: for traders with `geo_elo IS NULL` and `resolved_geo_trades_count ≥ 5`, run the geo_elo calculation and update the `traders.geo_elo` column.

### Fix 5 — Oscar decision on Signal 2 stale-market exclusion (LOW — Oscar action)
Signal 2 (UN Security Council NO) has been awaiting a policy decision since 2026-05-18. Set a clear policy: stale markets (unresolved since 2025 or template) are excluded from concurrent market count for STR-003 focus criterion. Document in integration-contract.md.

---

## 5. Single Most Important Gap

**There is no automated signal-to-outcome tracking loop for STR-003.**

When a STR-003 signal fires (a LEGENDARY geo trader at 95%+ directional conviction), the signal is filed in signals.json. Currently:
- The market resolves (captured by resolution_sweep.py and daily_maintenance)
- The outcome is **not** automatically compared against the signal direction
- findings.json is **not** updated with forward accuracy
- The strategy stays EXPERIMENTAL indefinitely

This is the single thing that would make the system most effective when signals start firing. Every signal that resolves without automated scoring is:
1. A lost data point toward the 20-signal minimum required for validation
2. A lost input to findings.json (currently 0 HIGH-confidence signal_direction_accuracy findings)
3. A lost feedback cycle for the strategy's self-improvement

The `score_insider_signals.py` pattern (built 2026-05-26) already does exactly this for insider signals. Extending it to STR-003 signals in signals.json is a small engineering task with outsized impact.

**Without it:** STR-003 fires, markets resolve, and the swarm learns nothing. With it: the strategy either accumulates evidence toward ACTIVE status or trips its stop criterion early — both are the correct outcomes.

---

## Phase 5 Gate Status

| Gate | Status | Notes |
|------|--------|-------|
| feedback-loop-agent ≥ 4 weekly runs | **MET** | Run #8 completed 2026-05-25 |
| findings.json ≥ 3 HIGH-confidence | **MET** | Multiple HIGH-confidence ELO findings (2026-05-25). But none are signal_direction_accuracy type. |
| STR-002 pre-resolution accuracy ≥60% across 10+ markets | **NOT MET** | STR-002 at 0 resolved markets (EXPERIMENTAL since 2026-03-28) |
| RQ1.1 AND RQ3.2 both passed | **NOT MET** | RQ1.1 deferred to July 1. RQ3.2 not pre-registered. |

**None of the four gates are fully clear.** Earliest Phase 5 entry: Q3 2026 at the earliest (contingent on RQ1.1 July result, RQ3.2 pre-registration and run, STR-002 accumulating 10+ resolved markets).
