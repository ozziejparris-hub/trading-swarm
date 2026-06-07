# Who Profits from Prediction Markets? Execution, not Information (Della Vedova, February 2026)
## Source
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6191618
## Domain
ssrn.com / academic paper
## Summary
Analysis of 222M trades decomposed into directional component (predicting winner) and execution component (entry price vs final value). Critical finding: retail traders pick winners 51.3% of the time yet LOSE money. Automated traders achieve near-random accuracy yet earn $133M. Directional and execution components share less than 1% of variance — they are nearly independent. Execution timing (entering at favourable prices) dominates profitability. No trader type beats price-implied accuracy benchmark.

Five trader types classified: Bot (>50 trades/day or >1,000 total), Sophisticated (>$10K volume, diversified, >30 active days), Active Retail (10-1,000 trades), Casual (2-9 trades), One-shot (exactly 1 trade).

Note: 25% of Polymarket historical volume is wash trading (peaked at 60% in Dec 2024), per Columbia University 2025 analysis.
## Action
IMPORTANT — challenges our system's core assumption. Our geo_elo measures directional accuracy (outcome prediction). If execution timing dominates profitability rather than directional accuracy, our signal may be tracking skilled forecasters who still lose money due to poor entry timing. HOWEVER: our geo_elo LEGENDARY pool achieves 79.6% accuracy vs 51.3% retail baseline — this cohort likely falls in the paper's "Sophisticated" category where execution effects may differ. Pre-register as RQ-EXEC-001 to test whether our Pool C accuracy advantage persists after controlling for entry timing.
## Verified
Yes — QuantPedia summary confirmed, CXO Advisory analysis confirmed, Marginal Revolution discussion confirmed.
