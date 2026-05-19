# RQ-LH-001: Lifecycle Heuristic for Insider Detection on Geopolitics Markets
## Pre-Registration Date
2026-05-19

## Research Question
Can a behavioural lifecycle heuristic — adapted from Gomez-Cram et al. (2026) — identify 
accounts on Polymarket whose single-event geopolitics trading pattern is consistent with 
informed trading (insider knowledge)?

## Hypothesis
Accounts meeting all four criteria below will show statistically higher win rates and profit 
than single-market geopolitics traders who do not meet the timing criterion:
1. Traded in exactly one geopolitics market (category: Geopolitics, Global Politics, 
   Elections, Ukraine & Russia)
2. That market is now resolved
3. Total volume in that market >= $1,000
4. Realized profit >= $1,000
5. First trade in our DB occurred within 30 days of market resolution date
   (using earliest trade timestamp as proxy for account creation — true creation 
   date unavailable from API)

## Data Available
- trades table: 1,011,882 geopolitics trades, Aug 2025 to May 2026
- 2,773 traders with exactly one geopolitics market in our DB
- 174 candidates meeting volume + profit criteria on resolved markets
- Limitation: first_seen and MIN(trade timestamp) are monitor-capture dates, 
  not true Polymarket account creation dates. True creation dates unavailable 
  from Data API. This weakens the timing criterion but does not invalidate it — 
  a trader whose first recorded trade is immediately before a specific event 
  still exhibits the behavioural signature.

## Methodology
Phase 1 — Run heuristic on existing data:
  Query traders matching all 5 criteria above
  For each: record market, profit, timing gap, ELO score
  Output: candidate list with full details

Phase 2 — Compare against non-qualifying single-market traders:
  Control group: single-market geopolitics traders meeting criteria 1-4 
  but NOT criterion 5 (first trade > 30 days before resolution)
  Compare: win rates, profit distributions, ELO distributions

Phase 3 — Cross-reference against ELO pool:
  Are any candidates already in the legendary tier?
  Are any candidates already excluded as bots?
  Do any candidates appear in multiple event clusters?

## Success Criteria
The heuristic is considered validated if:
- Candidate group has statistically higher profit than control group (p < 0.05)
- At least 10 candidates identified with profit >= $5,000
- Win rate of candidates exceeds 70% (matching paper's 69.9% benchmark)

## Failure Criteria  
The heuristic is considered uninformative if:
- Fewer than 10 candidates identified
- No statistically significant profit difference vs control group
- Candidates are predominantly already-known bots or LP artifacts

## Expected Output
- brain/agent-outputs/quant-research/LH-001/lifecycle_candidates.csv
- brain/agent-outputs/quant-research/LH-001/lh001_methodology.md
- findings.json entry with confidence level based on results

## Source
Adapted from: Gomez-Cram et al. (2026), "Prediction Market Accuracy: Crowd Wisdom 
or Informed Minority?" SSRN 6617059. Van Dyke DOJ indictment (April 2026) provides 
external validation that the lifecycle pattern identifies real insider trading.

## Owner
quant-research-agent (implementation), Oscar (approval before deployment to signal pipeline)

## Status
PRE-REGISTERED — awaiting implementation
