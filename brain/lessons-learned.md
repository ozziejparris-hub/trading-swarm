# System Lessons Learned
Updated weekly by training-librarian-agent.
This document grows more valuable every week.

---

## Principles Established
*(things the system knows to be true based on evidence)*

- 2026-05-05: QUALIFIED ELO consensus (all ELO-tracked traders)
  shows 82% directional accuracy at n=67 resolved markets.
  +32pp above 50% random baseline. HIGH confidence. This is
  the strongest empirically validated signal in the system.
  (Source: feedback-loop-agent run #3, performance-analyst 2026-05-05)

- 2026-05-07: Geopolitics category shows 92.3% directional accuracy
  (n=13) — the highest-confidence market category. Elections shows
  only 46.7% (n=15) — apply active skepticism to Elections signals.
  (Source: signal-agent category flags from feedback-loop-agent)

- 2026-04-27: RQ0.1 passed — ELO leaderboard is clean. 36 wash
  trading suspects, 0 in top-50 leaderboard, 0.1% of elite traders
  affected. Contamination is negligible.

- 2026-04-27: RQ0.2 passed — No automated accounts distorting the
  elite leaderboard. Three bot types classified: SPEED_ARBITRAGE
  (exclude from signals), NEWS_PROCESSING (caution), SYSTEMATIC_RESEARCH
  (high value — keep). NEAR_RESOLUTION bots (buy at 98-99c before
  settlement) classified separately — structural not predictive edge,
  do not follow their positions.

- 2026-04-27: STR-001 structural finding — Polymarket legendary traders
  are predominantly LP-structured: 78% of markets have 3+ legendary
  traders on BOTH YES and NO sides. This is the defining structural
  fact about signal detection in this system. Any signal definition
  must filter for exclusive directional conviction, not mere presence.

- 2026-05-04: Exit timing pattern established — 91% of top wallet
  exits happen before market resolution. Average exit captures 73%
  of max potential profit. Primary trigger: 3x normal volume in a
  10-minute window. Secondary: price target at ~85% of estimated gap.
  Add volume spike monitoring to pre-resolution signals.

---

## Strategy Insights
*(what worked, what failed, and why)*

- 2026-04-27 FAILED: STR-001 — Elite Convergence Signal (as-defined).
  56.1% accuracy, threshold 60%. ROOT CAUSE: definition required 3+
  legendary traders entering same side, but did NOT require exclusivity.
  In 78% of markets, legendary traders were split across both sides —
  paired signals produce exactly 50% by construction. The signal was
  measuring LP participation, not directional conviction.
  Do NOT retry without pre-registered STR-001b with exclusive convergence
  filter (3+ on one side AND <3 on opposite side). See:
  brain/failed-experiments/STR-001-as-defined-2026-04-27.md

- 2026-04-27 POSITIVE SUB-SIGNALS from STR-001 failure:
  30-90 day horizon: 84.6% (n=13); ELO 3000+ only: 75% (n=4);
  Exclusive single-side convergence: 100% (n=5 small);
  Dominant-side selection on split markets: 65.2% (n=23 — needs pre-reg).

- 2026-05-07 ADVANCING: STR-003 — Single Legendary Directional Signal.
  YES 61.1% (n=18), NO 77.8% (n=9) at 95% directional threshold.
  Both exceed 60% criterion. Now EXPERIMENTAL. Key design principle:
  the 95% directional threshold (single trader holds ≥95% of their
  capital in one direction on a market) filters LPs effectively,
  selecting only traders with genuine conviction rather than hedged
  market-making positions. 1/1 resolved signal correct (Ramaswamy NO).

- 2026-05-08 PRE-REGISTERED: STR-004 — Capital-Weighted Legendary
  Aggregate Signal. Founding validation case: Russia/Ukraine ceasefire
  market showing 48.7pp divergence between legendary capital weighting
  (55.7% YES) and market price (7% YES). Resolves June 30 2026.
  Complements STR-003: fires on mixed-position legendary traders
  where STR-003 would miss them (no single 95%+ directional trader).

- 2026-05-05: Sports markets at 52% accuracy for systematic approaches.
  Geopolitics and macro are where edge exists. Category filter must
  exclude sports in Phase 6. (Source: research-directions.md)

---

## Calibration Findings
*(measured accuracy of ELO predictions by tier and category)*

- None yet — awaiting Phase 1 Brier score calibration.

- 2026-03-16: Baseline Brier scores established.
  897 traders have calibration data. Range: 0.08-0.89.
  388 traders excellent (< 0.10) — superforecaster
  territory per Tetlock. 489 good (0.10-0.20).
  This is the Phase 1 baseline for quant-research-agent
  to improve upon.

---

## System Architecture Lessons
*(what we learned about how the system itself works)*

- Pre-registration protocol prevents compute waste on
  weak hypotheses. Established during build phase.
- Immune system must verify outputs independently —
  agents will confidently report completion on empty files.
- Feedback.json must be read before every task or agents
  repeat identical failures indefinitely.

- 2026-05-01: ELO calibration drift — legendary trader count grew
  28x after ELO modifier activation (15 → 432 legendary, ELO>2175).
  Absolute ELO thresholds become unreliable if the score distribution
  shifts. When modifiers are activated or weights change, the legendary
  threshold must be anchored to a consistent percentile (top ~0.03%),
  not an absolute ELO number. Prior research conclusions may be
  invalidated if modifier activation inflated scores uniformly.
  Investigating before June 1 RQ1.1 rerun. (Performance-analyst flag)

- 2026-05-04: Research-scout self-correction protocol established.
  Must check feedback.json scout_cycles.discarded BEFORE filing any
  finding. Papers were filed and removed multiple times (SCI paper
  2604.27041 discarded 4+ cycles; ForesightFlow filed in error twice).
  Root cause: filing without checking prior history. Protocol fix:
  history check is a pre-condition, not an afterthought. The scout
  now catches most of these before commit, but the pattern recurs.

- 2026-04-29: Information feedback paradox (from Galanis 2026) —
  using past accuracy as hard weights in signal confidence scoring
  WORSENS information aggregation quality. ELO scores should feed
  into signal confidence as soft Bayesian priors only, not hard
  multipliers. This affects feedback-loop-agent weight design.

- 2026-05-07: Claude Agent SDK native subagents/hooks/checkpoints
  shipped (confirmed by research-scout). This independently validates
  the trading swarm's multi-agent architecture — the SDK has converged
  on the same pattern. When Phase 3+ redesign occurs, review whether
  native SDK subagent features can replace hand-rolled orchestrator
  components.

- 2026-03-16: Behavioral scores (kelly_alignment_score,
  patience_score, timing_score) were silently failing
  due to Windows encoding bug (non-ASCII market titles
  crashing CSV write without utf-8 flag). Always specify
  encoding='utf-8' on all file writes. Fix: line 915
  of trading_behavior_analysis.py.

- 2026-03-16: Correlation matrix was computing 84M pairs
  daily and freezing the observer. Fixed with 7-day TTL
  cache + trader cap (flagged traders with local trade
  rows only = 2,396 traders, 2.87M pairs). 96.6%
  reduction in compute.

- 2026-03-16: composite_skill_score.py could not be
  called per-trader at scale (13K traders) because
  UnifiedELOSystem.__init__ triggers expensive loaders.
  Fixed by bulk SQL approach reading directly from DB
  instead of instantiating the full ELO stack.

- 2026-03-16: CalibrationAnalyzer had two attribute
  bugs (num_predictions vs total_predictions,
  avg_actual_prob vs actual_win_rate) that silently
  returned empty results. Always test analysis scripts
  with explicit output checks before integrating.

---

## What We Tried That Did Not Work
*(permanent record — never delete entries)*

- 2026-04-27: STR-001 — Elite Convergence Signal (as-defined).
  FAILED. 56.1% accuracy. The "convergence" definition was structurally
  broken — it was measuring Polymarket legendary traders being present
  in a market, not taking exclusive directional positions. LPs hold
  both sides. Any convergence metric that counts traders without
  checking for opposing positions on the same wallet will hit this flaw.
  Do not retry without exclusivity filter pre-registered as STR-001b.
  Full analysis: brain/failed-experiments/STR-001-as-defined-2026-04-27.md

- 2026-04-26: RQ1.1 first run — INCONCLUSIVE (not a failure, sample
  size failure). r=+0.175, p=0.52, n=16. Period 2 had only 25 days
  of resolved markets — insufficient for meaningful inference. The
  correct action is to wait for June 1 rerun with 60+ days of Period 2
  data. The near-zero correlation result was expected, not surprising.
  Do not treat this as evidence that ELO has no predictive validity.

- 2026-04-26: RQ3.2 first run — INCONCLUSIVE. Only 4 qualifying
  markets after filters. Methodology may need reframing — rather than
  testing ELO-weighted ensemble vs market price across all traders,
  test single highly-directional legendary traders (95% threshold)
  vs market price, extending RQ2.2 methodology to outcome prediction.
  Pre-registered for June 2026 follow-up.

---

## Open Questions
*(things the system does not yet know but needs to)*

- What is the actual Brier score of ELO-based predictions
  across resolved markets? (Phase 1 research target — RQ1.1 June 1)
- Which ELO tier is best calibrated by market category?
  (Geopolitics 92.3% is known; Economics unknown at n=4; Elections 46.7%)
- Does the ELO calibration drift (28x legendary count) explain
  RQ1.1's near-zero result, or was that genuinely a sample size issue?
  (Critical to answer before June 1 rerun — quant-research-agent task)
- Are legendary ELO modifiers the root cause of the 28x count inflation,
  or is it new trader entry at elevated scores? (Must be answered first)
- Does the exclusive convergence approach (STR-001b) actually outperform
  the market price? (Requires pre-registered hypothesis from quant-research)
- What is the Brier score of STR-003 on actual outcome prediction
  (not just price movement)? RQ2.2 extended window pre-registered June 2026.
- Does the Forecasting Economy dataset (polymonitor.club, 943M fill records)
  provide materially better signal coverage than our position-level tracking?
  (Research-scout finding, pending Oscar review)
- Does Gemma 4 MTP drafter mode provide 2-3x speedup on Tier 1/2 on
  the Radeon 780M Vulkan backend? (Urgent benchmark — Ollama 0.23.1-rc0)
- Does local DeepSeek V4-Flash inference (Q2 GGUF, 71GB) fit in the UM890
  Pro's available RAM headroom? (Oscar decision pending on local sovereignty)

- Does low-trade-count high-ELO (e.g. ELO 3500, 4 trades)
  predict outcomes better than high-trade-count moderate-ELO
  (e.g. ELO 3347, 2273 trades, $9.7M profit)?
  Test in RQ1.1 — stratify by trade count.
  (Observed: 0xb442 vs 0xbf79, March 16 2026)
