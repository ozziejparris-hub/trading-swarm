# Research Synthesis — External Literature Review
**Date:** 2026-06-16
**Context:** End-of-session research scan covering most relevant areas of active build.

---

## KEY FINDINGS

### 1. Core thesis validated — hard numbers now exist
Multiple independent 2026 studies confirm the foundation:
- Only ~3% of Polymarket traders drive price discovery (arXiv 2605.02287, Gomez-Cram et al.)
- The remaining 97% provide liquidity but lose in aggregate to the informed minority
- Skill vs luck separation via 10,000 coin-flip simulations — many apparent winners regress
- Yale SOM study (Theis Jensen et al.): "small group of informed traders drive prices and
  take home a large portion of profits"

Implication: our LEGENDARY pool (18 clean traders, ~0.6% of Pool C) is MORE selective
than the empirical 3% skill threshold. We may be over-filtering — ELITE (203 traders,
~7% of Pool C) may contain genuine skill worth monitoring in research context.
ELITE alert suppression is correct; ELITE research inclusion is correct.

### 2. "Smart money divergence" is weaker than "informed flow"
Research challenge to STR-002/STR-003 framing: the signal should not be
"smart trader disagrees with market" (intelligence), but rather
"informed trader is positioned" (information — timing + microstructure).

A skilled trader diverging from market consensus could still be a "smart person
losing money" (common failure mode in prediction markets per SwapHunt/Coinmonks 2026).
What makes divergence informative is whether the trader has INFORMATION, not just a VIEW.
This is detectable through timing and order-flow imbalance, not through ELO alone.

### 3. Informed-flow detection is the highest-value build direction
Harvard paper (2026): $143M+ in profits from traders with insider information on Polymarket
(200,000+ suspicious bets, Feb 2024–Feb 2026). The Iran example: anonymous account made
~$550K betting on US strikes hours before they occurred.

VPIN (Easley, López de Prado, O'Hara): measures buy/sell volume imbalance within
standardized buckets — when informed traders are active they arrive on one side;
VPIN >0.7 sustained = elevated informed-flow probability.

Connection to our build: we have SCL-009 order books, Polygon maker/taker detection,
and ILS framework (ForesightFlow, arXiv 2605.00493). The pieces exist. The shift from
"smart-money copy" to "informed-flow detection" is the highest-value architectural
direction for the system. NOT building today — see DEFERRED section.

### 4. Kelly sizing — literature confirms Phase 7 deferral is correct
"To confidently apply Kelly, a trader needs thousands of trades to validate the edge —
but systematic strategies generating a handful of signals per month make statistical
significance harder to achieve." (Kelly Criterion practical guides, 2025/2026)

We have 4 thesis-cell signals. Kelly now would be actively dangerous.
Fractional Kelly (quarter-Kelly) is the right parameter choice when we eventually size.
Market-as-Kelly-bettor paper: fractional Kelly behaves like full-Kelly with beliefs
weighted between own estimate and market. This supports our signal+market-price framework.

### 5. Brier score — use log-likelihood instead
See: brain/strategy-notes/calibration-metric-decision-2026-06-16.md
DECIDED: log-likelihood for all calibration layer scoring, not Brier.

---

## DECISIONS MADE TODAY

✅ **DONE — Log-likelihood over Brier for calibration layer (Phase 6)**
Documented in calibration-metric-decision-2026-06-16.md. Applies when
Phase 6 calibration layer is built. Cheap to decide now, prevents a
systematic error in a near-resolved-heavy signal distribution.

✅ **DONE — ELITE retained in research pool (confirmed, not just assumed)**
203 ELITE (comprehensive ELO ≥2000) + 22 NEAR_LEGENDARY (geo 1800-2174)
traders are confirmed in the research pool. Alert suppression (LEGENDARY-only)
does not affect research inclusion. Full ELO spectrum available for analysis.

---

## DEFERRED BUILDS (July or later, require proper pre-registration)

⏳ **DEFERRED — Informed-flow / VPIN signal**
Rationale: major architectural build, needs dedicated session + proper RQ
pre-registration before any implementation. We just proved why unvalidated
signals are dangerous (STR-002 QUALIFIED noise). Build in July after pre-
registration. Uses: SCL-009 order books + Polygon maker/taker + ILS framework.
Potential pre-registration: RQ-VPIN-001 "Does VPIN-elevated order flow in the
pre-registration window predict STR-003 signal accuracy?"

⏳ **DEFERRED — Sign-randomization skill validation**
Method: simulate each LEGENDARY trader's bets 10,000 times with coin-flip
directions; only traders who consistently outperform are confirmed skilled.
More rigorous than ELO alone. Pre-register as validation RQ before July 1 wave.
Would strengthen LEGENDARY designation and counter the regression-to-mean risk.
Directly implements the Gomez-Cram et al. methodology.

⏳ **DEFERRED — Fractional Kelly parameter**
Parameter choice (quarter-Kelly) already locked in Phase 7 deferral notes.
No implementation needed; just confirming the literature supports this choice.

---

## SOURCES
- arXiv 2605.02287 (Gomez-Cram et al.): 3% of traders drive price discovery
- Yale Insights / Theis Jensen et al.: "wisdom of the few" prediction market study
- SwapHunt/Coinmonks (June 2026): why smart people lose in prediction markets
- Harvard paper (2026): $143M informed-trading profits on Polymarket
- Easley, López de Prado, O'Hara (2011/2012): VPIN and flow toxicity
- arXiv 2605.00493 (Nechepurenko): ForesightFlow / ILS framework
- arXiv physics/0401046: Brier score problems, log-likelihood as alternative
- Kelly Criterion practical guides (2025/2026): fractional Kelly + backtest risks
- arXiv 2201.6655: Kelly bettors and prediction market learning rates
