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

- 2026-05-13: QUALIFIED ELO consensus (≥1200 ELO, clean 493-trader pool)
  directional accuracy improved to 92% (n=12, 7-day window) from 82%
  at n=67 (30-day window May 5). Edge is real and strengthening.
  The 92.3% Geopolitics figure is corroborated by this broader metric.
  (Source: performance-analyst 2026-05-13)

- 2026-05-13: Directional accuracy ≠ probabilistic calibration. The system
  can be 92% directionally correct while showing Brier 0.3128 (worse than
  random) in the same period. These measure different things. Directional
  accuracy is the right metric for binary prediction signals. Brier score
  is the right metric for probability calibration. Do not conflate them —
  especially when Brier is computed on LP-contaminated positions.
  (Source: performance-analyst 2026-05-13, Flag 2)

- 2026-05-13: ELITE tier accuracy (ELO≥1800) is unreliable at low sample
  count. This week: 33% (n=3). Two weeks ago: 100% (n=4). Small n produces
  wild swings that carry no statistical signal. Do not report or act on
  ELITE tier accuracy when n < 10. QUALIFIED tier (n≥12) is the minimum
  reliable floor. (Source: performance-analyst 2026-05-13)

---

- 2026-05-23: Research pool SQL filter in reference files should document the methodology,
  not embed a specific trader count. Counts age quickly — the 493 figure written to
  polymarket-market-structure.md on May 16 was already stale by May 18 (pool at 104 due
  to script regression). Reference files should say "run explicit filter to get current
  authoritative count" not "returns 493 as of May 13."
  (Source: performance-analyst 2026-05-18, training-librarian 2026-05-23)

- 2026-05-30: STR-003 concurrent criterion is structurally incompatible with validated
  traders. All 21 geo_elo LEGENDARY traders with ≥10 resolved trades have 15–1,626
  concurrent markets — the max-2 filter captures "focused conviction" as a style, not
  as a validation-grade trader characteristic. Experienced portfolio traders hold hundreds
  of simultaneous positions by nature. Fix: change concurrent check from
  `total_concurrent_markets` to `concurrent_open_geo_markets` (a trader holding 500
  crypto markets is not disqualified from a focused geopolitics conviction).
  (Source: signal-agent 2026-05-25, swarm-assessment 2026-05-29)

- 2026-05-30: geo_elo LEGENDARY pool is dormant. All 21 LEGENDARY traders (geo_elo ≥ 2175,
  ≥10 resolved geo trades) stopped trading 2025-12-31. They are Haley-2027 specialists
  with no active 2026 market positions. STR-003 cannot fire a LEGENDARY signal until 2026
  geopolitics markets resolve and new traders score into the LEGENDARY tier via accumulated
  geo_elo. Expected timeline: Q3 2026 as Putin market (~June), ceasefire variants, and
  other 2026 geo markets resolve.
  (Source: signal-agent 2026-05-25, swarm-assessment 2026-05-29)

- 2026-05-30: Phase 5 gate 1 cleared — feedback-loop-agent has completed 8 weekly runs
  as of 2026-05-25. The ≥4 weekly runs gate is the first of four Phase 5 gates. Of the
  remaining three, none are met: findings.json has HIGH-confidence ELO findings but no
  signal_direction_accuracy type; STR-002 has 0 resolved markets; RQ1.1 deferred to
  July 1 and RQ3.2 data timeline is July–September 2026.
  (Source: swarm-assessment 2026-05-29)

- 2026-06-05: Phase 5 Gate 2 cleared — findings.json now contains 3+ HIGH-confidence
  findings. Run #10 added RQ-CONTESTED-001 (QUALIFIED 66.3%, n=101) and Pool C geo
  70.7% (n=444), tipping the count past the gate-2 threshold. Remaining gates: STR-002
  accuracy ≥60% across ≥10 markets (0 resolved); RQ1.1 and RQ3.2 both passed (both
  deferred to Q3 2026). Earliest Phase 5 entry remains Q3 2026.
  (Source: feedback-loop-agent Run #10, 2026-06-05)

- 2026-06-03: ELO consensus substantially outperforms market price on contested markets
  (entry_price 0.35–0.65, ≥3 ELO-tracked traders). LEGENDARY: 79.2%, ELITE: 81.4%,
  QUALIFIED: 69.6% vs market baseline 50.3%. Edge: +28.9/+31.1/+19.3pp respectively.
  This is the strongest alpha evidence to date — a direct comparison of ELO-weighted
  consensus against market price on the same markets. Priority: time-series stability
  check across 2024–2026 before treating as a deployable signal.
  (Source: feedback-loop-agent findings, 2026-06-03-ELO-VS-MARKET-001)

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

- 2026-05-21 CONDITIONAL_PASS: LH-001 — Lifecycle Heuristic Insider Detection.
  Pooled p=0.0160 (one-tailed MWU, n=59 candidates vs n=90 control). Neither
  event individually significant (Haley p=0.1087, Iran p=0.4818). V1 "Haley
  p=0.0000" was a market-scale confound — Haley profits are ~10× Iran profits,
  so comparing Haley lifecycle traders against a mixed Haley+Iran control inflated
  the apparent p-value. Effect size r=0.208 (small-medium). N=2 events is
  insufficient for deployment as a trading signal. DEPLOY AS WATCHLIST TRIGGER ONLY
  via insider_signals table (7 existing detections). Do not promote until 5+ distinct
  events validated. (Source: backtest-agent v2 2026-05-21)

- 2026-05-08 PRE-REGISTERED: STR-004 — Capital-Weighted Legendary
  Aggregate Signal. Founding validation case: Russia/Ukraine ceasefire
  market showing 48.7pp divergence between legendary capital weighting
  (55.7% YES) and market price (7% YES). Resolves June 30 2026.
  Complements STR-003: fires on mixed-position legendary traders
  where STR-003 would miss them (no single 95%+ directional trader).

- 2026-05-08 FOUNDING CASE FAILED: STR-004 Russia/Ukraine ceasefire
  market resolved NO on 2026-05-08. 8 legendary traders, $1.74M,
  55.7% YES — crowd at 7% was correct. STR-004 accuracy: 0/1. This
  is the first data point, not a stop criterion (stop at <50% over
  10 markets). Key investigation question: do geopolitics markets
  with very low crowd prices (<10%) attract LP-structured yes bets
  as hedges rather than genuine directional conviction? The capital-
  weighting may not neutralise mixed positions in asymmetric markets.
  Status: EXPERIMENTAL, one data point, continue to next validation.
  (Source: performance-analyst 2026-05-13, Flag 4)

- 2026-05-05: Sports markets at 52% accuracy for systematic approaches.
  Geopolitics and macro are where edge exists. Category filter must
  exclude sports in Phase 6. (Source: research-directions.md)

- 2026-05-30: STR-003 anti-arb filter identified. geo_elo LEGENDARY
  traders with the highest win rates are predominantly arb traders
  buying near-certainty outcomes ($0.95+), not directional insiders.
  These traders buy YES at 95c-99c before settlement — structural edge,
  not informational. Entry_price filter 0.10–0.80 is required to
  distinguish genuine directional conviction from arb/near-resolution
  harvesting. Pre-registration required before implementing this filter
  in production signal criteria. (Source: session 2026-05-29, swarm
  assessment; documented in strategy-registry.md STR-003 notes)

- 2026-05-30: RQ3.2 re-framed and re-pre-registered (2026-05-29).
  The original RQ3.2 (all ELO-weighted ensemble vs market price) was
  INCONCLUSIVE — only 4 qualifying markets after filters, sample size
  failure. New framing: geo_elo LEGENDARY consensus (3+ traders, same
  direction, geopolitics/elections) vs market price. This tests the
  wisdom-of-crowd effect within the LEGENDARY tier specifically.
  Data accumulation timeline: July–September 2026 as 2026 geo markets
  resolve and new traders earn LEGENDARY geo_elo.
  (Source: rq3-2-preregistration-2026-05-29.md)

- 2026-06-05: RQ-CONTESTED-001 PASS — QUALIFIED tier achieves 66.3%
  accuracy on 2026 contested markets (n=101), 11.1pp above 55.2% market
  baseline. LEGENDARY tier only 49.2% (below random) — comprehensive_elo
  contamination confirmed. This is the first formally approved HIGH finding
  of the signal_direction_accuracy type. ELITE: 64.3% (n=98). The LEGENDARY
  underperformance reinforces the case for geo_elo over comprehensive_elo
  as the qualifying metric for STR-003.
  (Source: feedback-loop-agent Run #10, 2026-06-05-CONTESTED-ACCURACY-2026-001)

---

## Calibration Findings
*(measured accuracy of ELO predictions by tier and category)*

- 2026-06-03: ELO vs Market Price on contested markets (entry_price 0.35–0.65,
  ≥3 ELO-tracked traders per market, excluding Sports/Crypto/Entertainment):
  LEGENDARY: 79.2%, ELITE: 81.4%, QUALIFIED: 69.6%. Market baseline: 50.3%.
  Edges of +28.9pp, +31.1pp, +19.3pp. Pool: research_excluded=0, bot_type IS NULL.
  Action: run time-series stability check (2024–2026) before treating as deployable.
  (Source: 2026-06-03-ELO-VS-MARKET-001)

- 2026-06-05: Pool C geo/elections full-year accuracy: 70.7% (n=444 resolved 2026
  markets). Extends prior 30-day finding — the 70%+ signal is durable across the
  full 2026 dataset, not a short-window artifact.
  (Source: 2026-06-05-POOL-C-GEO-FULL-2026-001)

- None yet — Brier score calibration via RQ1.1 deferred to July 2026.

- 2026-03-16: Baseline Brier scores established.
  897 traders have calibration data. Range: 0.08-0.89.
  388 traders excellent (< 0.10) — superforecaster
  territory per Tetlock. 489 good (0.10-0.20).
  This is the Phase 1 baseline for quant-research-agent
  to improve upon.

---

## System Architecture Lessons
*(what we learned about how the system itself works)*

- 2026-05-23: CLOB V2 went live April 28 2026 — V1 SDKs and V1-signed orders are no longer
  supported. Polymarket is migrating collateral from USDC.e to pUSD (ERC-20, Polygon, backed
  1:1 by USDC). GET /markets/keyset max limit is now 100 (was higher). POST /submit no longer
  returns transactionHash. Any agent using the Polymarket CLOB API must use V2 signing.
  market-builder-agent template needs updating before any deployment.
  (Source: research-scout pending-review 2026-05-19-17-polymarket-exchange-upgrade-clob-v2)

- 2026-05-23: feedback.json corruption: research-scout-agent overwrote brain/feedback.json
  with a scout cycle summary object (full overwrite: {"scout_cycles_completed": 15, ...}).
  All approved, rejected, data_integrity_gates keys were destroyed. Restored from git d529c0a.
  Root cause: template DoD item "feedback.json updated with cycle summary" does not specify
  append-only semantics. The scout wrote its summary as a top-level overwrite rather than
  appending to the scout_cycles array. Second consecutive corruption incident (May 12: empty,
  May 17: full overwrite). Template fix is required — see template audit flags this week.
  (Source: performance-analyst 2026-05-18, Flag 3)

- 2026-05-23: Clean pool collapse: update_research_exclusions.py set research_excluded=0 for
  7,748 traders who lack the ≥20 resolved trades criterion, collapsing the explicit clean pool
  from 493 to 104 in 5 days (May 13 → May 18). The flag inflation was not gradual (604→7852)
  — it happened in one script run. All agent research queries must use the FULL explicit filter:
  `research_excluded=0 AND resolved_trades>=20 AND bot_suspect=0 AND wash_trade_suspect=0`.
  Do not spawn quant-research-agent, feedback-loop-agent, or signal-agent without briefing on
  this discrepancy. (Source: performance-analyst 2026-05-18, Flag 1)

- 2026-05-23: New ELO cluster: 39 traders above ELO 3500 appeared by May 18 (max ELO 4305
  vs 3471 May 13). Same structural signature as ARB_BOT cluster excluded May 6 (111 traders,
  ELO 3308–3315). RQ0 gate due June 13 should be brought forward. If any of the 39 traders
  are in the 104-trader explicit clean pool, they could contaminate signal generation.
  (Source: performance-analyst 2026-05-18, Flag 2)

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

- 2026-05-13: Research pool discrepancy uncovered — live DB query
  `WHERE research_excluded=0` returns 604 traders, but integration-
  health.json authoritative pool is 493. 111 traders have the flag
  set to 0 without meeting the explicit criteria (resolved_trades≥20,
  bot_suspect=0, wash_trade_suspect=0). Root cause: set-eligible
  logic in update_research_exclusions.py differs from reverse-
  exclusion logic. Until code-hygiene fixes this, agents must add
  explicit criteria to research queries alongside research_excluded=0.
  (Source: performance-analyst 2026-05-13, Flag 3)

- 2026-05-15: MiniMax M2.7 open-weight release confirmed (MIT license).
  GGUF (UD-Q2_K_XL, 75.3GB) fits UM890 Pro's 96GB DDR5. Claims
  Anthropic-compatible API (zero integration cost), native tool use,
  95% cheaper than Opus. Sovereignty blocker removed — open weights
  mean no Chinese-hosted API required. Pending Oscar benchmark
  decision per priorities.md May 2026 action items. Do not deploy
  without benchmarking 3 Tier 2.5 tasks first.
  (Source: pending-review 2026-05-15-01)

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

- 2026-06-06: Two findings in findings.json have empty summary fields
  (2026-06-01-GEO-ELO-ACCURACY-001, 2026-06-03-ELO-VS-MARKET-001). The
  detail blocks are present and correct, but the summary string is empty.
  The ELO-VS-MARKET-001 finding is particularly important (LEGENDARY 79.2%,
  ELITE 81.4% on contested markets). When populating findings.json, the
  `summary` field must be filled before the entry can be consumed by agents
  that read only the summary. Code-hygiene-agent should add a schema
  validation step: any finding with `confidence = "HIGH"` and an empty
  `summary` string should fail the immune system check.

- 2026-06-06: STR003-005 and STR003-006 (Peru presidential election, June 7)
  are logically contradictory — both are YES signals, but both Keiko Fujimori
  and Rafael López Aliaga cannot win the same election. The generating trader
  (geo_elo_active 3580, #1 in pool) holds YES positions on both candidates
  simultaneously, apparently as a "one of them will win" hedge rather than
  a directional conviction play. This exposes a gap in STR-003: the 95%
  directional threshold applies per-market (trader holds ≥95% in YES on
  each individual market) but does not check mutual exclusivity across markets.
  A signal-agent or backtest-agent pre-filter should detect when two active
  STR-003 YES signals are from the same election and flag as conflicting.
  Outcome of both signals scores June 7: only one can be correct.

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

- 2026-05-08: STR-004 founding case (Russia/Ukraine ceasefire) —
  capital-weighted legendary aggregate (55.7% YES, 8 traders, $1.74M)
  predicted YES. Crowd at 7% was correct. Market resolved NO.
  n=1 — stop criterion is <50% over 10 markets, so strategy continues.
  But this failure raises a specific question: does capital weighting
  fail in very asymmetric markets where crowd price is very low (<10%)
  because legendary YES holders may be hedging or expressing
  asymmetric conviction rather than prediction? To investigate before
  next STR-004 signal is acted on. (Source: performance-analyst May 13)

- 2026-06-05: LH-001 blocking item 2 FAILS — all 7 insider_signals
  records scored (score_insider_signals.py): 4/7 correct (57.1%),
  below the 60% accuracy threshold. LH-001 remains CONDITIONAL_PASS /
  watchlist trigger only. Blocking item 2 is not cleared. Do not
  promote to EXPERIMENTAL until blocking items 1 (5+ distinct events,
  p<0.05 event-level), 2 (≥60% on resolved insider_signals), and 3
  (Gamma API wallet creation date confirmed) are all cleared.
  n=7 is also too small — 57.1% vs 60% threshold is within noise at
  this sample size. Continue tracking as new insider_signals resolve.
  (Source: feedback-loop-agent Run #10, 2026-06-05)

---

## Open Questions
*(things the system does not yet know but needs to)*

- What is the actual Brier score of ELO-based predictions
  across resolved markets? (Phase 1 research target — RQ1.1 deferred to July 1 2026;
  n=10 qualifying traders vs 30 required minimum)
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

- Does capital-weighting in STR-004 fail in asymmetric markets
  (crowd price <10%) where legendary YES positions may be hedges
  rather than directional conviction? Investigate before STR-004
  second validation case. (Raised by STR-004 founding case failure
  May 2026)

- Does PMXT's Parquet archive (tick-level data, 13K+ resolved markets)
  materially improve backtest quality over local DB position data?
  (Pending Oscar review of 2026-05-12-08-pmxt-unified-prediction-market-sdk)

- Does resolution-zone orderbook thinning (YES/NO depth ratio in
  final 24h) predict resolution direction? New RQ candidate from
  polymarket-resolution-zone-price-dynamics paper (May 12). Needs
  pre-registration before any test.

- Can the ForesightFlow Information Leakage Score (arXiv 2605.00493) be used
  by market-builder-agent to filter for high-signal markets? Pending Oscar review
  of research-scout pending-review item (May 19). Would complement ELO ranking
  with a market-level quality signal.

- Does the insider detection methodology from arXiv 2605.02287 (3.14% skilled winners,
  69.9% win rate) improve ELO pool construction? Could sharpen signal generation by
  selecting confirmed skilled insiders or filtering adversarial actors. Directly relevant
  to RQ3.2. Pending Oscar review of research-scout pending-review item (May 19).

- Are the 39 new traders above ELO 3,500 (May 18) coordinated ARB_BOTs or legitimate
  new entrants? Must answer before any signal generation from the ELO 3,500+ range.
  Bring RQ0 forward from June 13. (Performance-analyst Flag 2, May 18)

- Does the ELO vs Market Price edge on contested markets (LEGENDARY 79.2%, ELITE 81.4%,
  2026-06-03) hold across 2024–2026 independently, or is it driven by one strong year?
  Run time-series stability check across yearly cohorts before treating as deployable.
  (Raised by 2026-06-03-ELO-VS-MARKET-001 action_recommendation)

- Do the STR003-005/006 Peru signals (same trader, YES on both Keiko and López Aliaga)
  resolve in a way that informs the "one of two candidates" hedge pattern? If the winning
  candidate's YES bet scores correctly, it suggests the signal has value even for
  multi-candidate hedges; if both are wrong (both lose), the strategy is exploiting
  price inefficiency in a different way than the 95% directional conviction thesis assumes.
  **ANSWERED 2026-06-13:** Both signals wrong (0/2). Neither Keiko nor López Aliaga won.
  The "one of them will win" hedge produced two wrong signals — this is the worst outcome.
  The trader was hedging against the market, not predicting; the market was correct.

- What is the mutual exclusivity rate among STR-003 YES signals? How often does the same
  trader hold YES positions on multiple mutually exclusive outcomes in the same event?
  This affects how signal accuracy is calculated for multi-outcome electoral markets.

---

## Lessons added 2026-06-13

### Strategy Insights
- 2026-06-13 STR003-005/006 FAILED: Peru presidential election signals (June 7 resolution). Both
  signals WRONG — 0/2 correct. Root cause: geo_elo top trader held YES on both Keiko Fujimori AND
  López Aliaga simultaneously (both-candidates hedge). The 95% directional threshold applies
  per-market and doesn't detect mutual exclusivity at the election level. STR-003 running accuracy
  after 4 resolved signals: 1/4 (25%). n=4 is below the stop criterion (10 signals), continue
  accumulating. Key lesson: a geo_elo 3,580 (#1 in pool) trader can still produce structurally
  worthless signals in multi-candidate elections. The mutual exclusivity check is essential.
  (Source: findings 2026-06-13-STR003-ACC-004, research-directions compounding notes)

### System Architecture Lessons
- 2026-06-13: Integration contract Section 9 validated against live DB — all metrics pass.
  clean_pool=18,759 (threshold 15,000), true_research_pool=3,837 (threshold 3,000),
  pool_c=2,851, legendary_clean=18. DB pool is growing: research pool +837 above minimum.
  No contract violations. (Source: training-librarian Responsibility 10, 2026-06-13)

- 2026-06-13: market-builder CLOB V2 fix confirmed present (week-4 open issue resolved).
  The template now includes a ⚠️ warning block at line 14 covering all 5 V2 breaking
  changes (V1 signing deprecated, pUSD collateral, keyset max=100, no transactionHash,
  EIP-712 domain version bump). Any market-builder-agent spawned from the current template
  will be correctly warned. (Source: training-librarian template audit 2026-06-13)

- 2026-06-13: SCI (Signal Credibility Index) live in positions scan as annotation-only.
  First positions scan with SCI (June 9): 5 markets reported, all MEDIUM or LOW tier.
  No HIGH conviction signals (≥4 LEGENDARY, gap ≥30pt) in the current scan. MIXED_SIGNAL:
  China tariff market (both_sides_ratio=0.443) — flag for Oscar review.
  (Source: 2026-06-09-positions-scan.json, RQ-SCI-001 pre-registration)

### Open Questions (updated)
- Closed: STR003-005/006 Peru outcome confirmed (see Strategy Insights above).
- Still open: What is the mutual exclusivity rate among STR-003 YES signals?
- Urgent: RQ0 monthly gate due 2026-06-13 — 39 traders above ELO 3,500 still unclassified (May 18 flag).

---

## Lessons added 2026-06-20

### System Architecture Lessons
- 2026-06-20: Integration contract v2.11 codified the single-writer principle as the canonical governance layer for all traders table aggregate columns. Layer 1 columns (total_trades, successful_trades, total_volume, win_rate, specialisation_ratio, and all position-derived columns: total_invested, avg_roi, realized_pnl, open_positions, closed_positions) are now owned exclusively by reconcile_trader_aggregates.py. Any agent or script writing these columns directly creates a competing writer — this was the root cause of months of recurring data inconsistencies. Route all aggregate writes through reconcile_trader_aggregates.py or coordinate explicitly. (Source: contract v2.11, 2026-06-18 session #38)

- 2026-06-20: True_research_pool nearly doubled in one week (3,837 on 2026-06-13 → 7,836 on 2026-06-20). Extraordinary growth rate. Likely caused by backfill of resolved_trades_count for traders added via vgregoire external_seed (195 traders, SCL-006) now crossing the 20-resolved-trades threshold as the backfill pipeline processes historical trades. Section 9 expected values in integration-contract.md are now significantly stale. Oscar should investigate root cause and update contract numbers. (Source: training-librarian Responsibility 10, 2026-06-20 vs 2026-06-13)

- 2026-06-20: Contract version drift risk. Signal-agent June 15 report referenced contract v2.9 (2026-06-13) while the live contract is v2.12 (2026-06-18). The 3-version gap includes breaking changes: datetime format standard (Section 16, affects all ingestion paths), STR-002 dual-role architecture (Section 17), column authority registry (Section 18). Agents should read the contract version header at startup and log it in their cycle reports. A check against schema-change-log.md last entry would catch this automatically. (Source: signal-agent 2026-06-15-08-signal-report.md vs integration-contract.md v2.12)

### Strategy Insights
- 2026-06-20: LEGENDARY dormancy pattern — for 3 consecutive weekly cycles (June 1, 8, 15), 6 of the top 16 qualifying LEGENDARY traders (geo_elo_active 2503–2897, combined P&L ~$34M+, 1,876–2,028 geo resolved trades) have zero open positions in active geo/elections markets. The system's highest-ELO cohort is completely inactive. Possible interpretations: (1) low-conviction environment in current geopolitics, (2) Polymarket platform fatigue for high-capital traders, (3) positions not being captured by DB coverage. Monitor post-June 30 resolution cluster for re-engagement. If dormancy continues into July, treat as a structural signal that the current market set has no LEGENDARY conviction opportunities. (Source: signal-agent 2026-06-01, 2026-06-08, 2026-06-15 reports)

### Calibration Findings
- 2026-06-15: ELO weekly calibration snapshot (feedback-loop-agent 2026-06-15): LEGENDARY 73% (n=22), ELITE 60% (n=30), QUALIFIED 77% (n=48) across non-sports resolved markets. QUALIFIED outperforming LEGENDARY at the weekly snapshot level, which is consistent with small-n noise at LEGENDARY (22 markets). The authoritative calibration finding remains 2026-06-03-ELO-VS-MARKET-001: LEGENDARY 79.2%, ELITE 81.4% on genuinely contested (0.35–0.65 price band) markets, n=746 — a larger, better-controlled sample.

### Open Questions (updated)
- New URGENT: What caused true_research_pool to nearly double from 3,837 (June 13) to 7,836 (June 20)? Root cause needed before using pool stats for ongoing validation.
- June 30 resolution cluster: STR003-004 (Putin NO, not scorable — trader fails LEGENDARY threshold), STR003-007 (Iran NO, non-scorable), STR003-008 (Ukraine security guarantee NO, scorable). STR003-008 will be STR-003's 5th resolved signal and first with VOLUME_SPECIALIST-weighted scoring.
- Stale Polymarket prices: June 15 scan showed 7/8 (87.5%) of signal markets had stale API prices. If structural, the positions scan is providing minimal weekly intelligence. Investigate API refresh cadence.

---

## Lessons added 2026-06-27

### System Architecture Lessons
- 2026-06-27: pool_c (geo_accuracy_pool=1) dropped 40% in one week (3,660 on June 20 → 2,155 on June 27), breaching the Section 9 contract threshold of 2,500. The geo_accuracy_pool flag appears to have been reset or reassigned for a large batch of traders. Contract violation signal written to signals.json. Root cause unknown — Oscar to investigate before next signal generation run. (Source: training-librarian Responsibility 10, 2026-06-27)

- 2026-06-27: Daily STR003-ACC-004 scoring creates 7+ stale entries per week in findings.json (10 entries needed cleanup this run). The score_str003_signals script writes a new entry every day even when the count hasn't changed. A deduplication check at write time would prevent accumulation: only write if sample_size or value has changed since the last entry. (Source: training-librarian Responsibility 7, 2026-06-27)

- 2026-06-27: Integration contract v2.13 (2026-06-23) — Tier-1 definitions-module complete. monitoring/column_definitions.py is now the canonical source for all covered column definitions. Tier-2 scope (13 read-side scripts) is next milestone. Agents referencing Section 18.3 will find the definitions module live and authoritative. (Source: integration-contract.md Section 8 v2.13)

### Calibration Findings
- 2026-06-22: ELO weekly calibration snapshot (feedback-loop-agent 2026-06-22): LEGENDARY 51% (n=37), ELITE 49% (n=41), QUALIFIED 63% (n=57). QUALIFIED holds above 60% threshold. LEGENDARY and ELITE near random on unfiltered weekly snapshot — consistent with finding that contested-market filter (0.35–0.65 price band) is required to show their edge. Do not act on unfiltered LEGENDARY/ELITE weekly numbers.

### Positions Scan (June 22)
- 2026-06-27: Iran regime fall by June 30 (5 LEGENDARY NO, gap=45.3pt, CLEAN) is the strongest open conviction signal resolving within 7 days. SCI=LOW because entry_timing_alpha=0 (no early-entry bonus). Signal is likely registered as STR003. Four Iran-adjacent markets show both_sides_ratio > 0.35 (MIXED_SIGNAL): another-country-strikes-Iran rank 6 (0.379), US-Iran ceasefire rank 7 (0.488), Trump announcement rank 29 (0.378), Marseille mayor rank 31 (0.400). These markets have LEGENDARY traders on both sides — do not treat as directional signals.

### Open Questions (updated)
- Resolved? True_research_pool growth from June 20 (7,836) is still unexplained — needs Oscar investigation.
- URGENT: What caused pool_c to drop from 3,660 to 2,155 in one week? (New as of June 27)
- June 30 resolution cluster: STR003-007 (Iran regime NO), STR003-008 (Ukraine security guarantee NO). Score immediately after resolution.
- LEGENDARY dormancy: Post-June 30 cluster is the next test of whether LEGENDARY traders re-engage.
