# Fable Strategic Briefing — System State Index
**Prepared: 2026-06-11 for strategic roadmap analysis**

This is an INDEX to the system's truth. Verify claims against the actual files.
Do not take this summary at face value — cross-reference everything.

## YOUR TASK
Map the complete strategic picture of this Polymarket trading intelligence system,
then design the roadmap forward. You have repo access — VERIFY the state yourself.

## CRITICAL ANALYTICAL INSTRUCTION
The raw signal scorecard (STR-003: 1 correct / 3 wrong) is MISLEADING if read naively.
Each signal fired at a point in time. The system's CAPABILITIES have changed dramatically
across June 2026. Before judging any strategy's performance, build a TIMELINE:
- When did each signal fire? (check registered_at / signal_date in signals.json)
- What infrastructure existed at that point? (read session summaries chronologically)
- Was the failure something we've since built a solution for?

Cross-reference signal failure dates against infrastructure build dates. Assess whether
the scorecard reflects the CURRENT system or a PREVIOUS version of it.

## WHERE THE TRUTH LIVES

### Session history (chronological capability evolution)
brain/decisions/2026-05-26 through 2026-06-11 session summaries
Read these IN ORDER to see how the system evolved.

### Current strategy state
brain/strategy-registry.md — strategy statuses
brain/signals.json — all STR-003 signals with registered_at dates
brain/findings.json — 51 findings, 18 HIGH with n>=20

### Pre-registered research (the forward pipeline)
brain/strategy-notes/ — all RQ pre-registrations with rerun dates

### Infrastructure built (verify build dates via git log)
- signal_credibility.py (SCS) — built 2026-06-09
- legendary_positions_scan.py — built 2026-06-09
- trader profiles (37) — built 2026-06-10
- trader-intelligence-agent — built 2026-06-10
- sync_trade_categories.py — built 2026-06-10
- elo_snapshots temporal layer — built 2026-06-11
- run_trader_profiling.py — built 2026-06-10

### The integration contract (system bible)
brain/integration-contract.md v2.8 — canonical definitions, all sections

## KEY ARCHITECTURAL FACTS (verify these)
- LEGENDARY = geo_elo_active >= 2175 AND geo_accuracy_pool=1 AND clean
- Pool C: 2,848 traders (was 402 before June 10 category sync)
- 4 trader archetypes: GENUINE_FORECASTER (4), DOMAIN_SPECIALIST (13),
  YIELD_HARVESTER (17), VOLUME_SPECIALIST (3)
- Raw ELO is a POOR signal quality proxy — archetype × domain matters
- elo_snapshots gives point-in-time trader state from 2026-06-11 forward

## PHASE 5 GATES
Gate 1 (feedback-loop 4+ runs): MET
Gate 2 (3+ HIGH findings n>=20): MET — 18 qualifying
Gate 3 (STR-002 pre-res >=60% on 10+ markets): NOT MET — no scoring loop exists
Gate 4 (RQ1.1 + RQ3.2 passed): NOT MET — both need rerun with current data

## KNOWN OPEN PROBLEMS (verify and assess)
1. STR-002 has no outcome scoring mechanism — Gate 3 cannot be met without building one
2. RQ1.1 rerun overdue (was June 1) — now has elo_snapshots data it lacked before
3. RQ3.2 rerun needed — much more data since April
4. Counter-signal detection designed but not built (waiting on snapshot history)
5. Signal schema bifurcated (001-006 vs 007-009 formats) — partially canonicalised
