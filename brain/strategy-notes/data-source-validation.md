# Data Source Validation Notes

## Trade Direction Inference — VALIDATED (2026-04-28)
Paper: "Anatomy of a Decentralized Prediction Market" 
arXiv:2604.24366

Finding: Order-book WebSocket direction inference is only
59% accurate vs on-chain OrderFilled ground truth.

Our system status: CLEAN
- monitor.py lines 624/627 use outcome/side from 
  Data API /trades endpoint
- Data API returns actual executed trades with outcome 
  populated from on-chain settlement
- We are NOT using order-book WebSocket inference
- Direction accuracy is not affected by this finding

Other findings from this paper to note:
- Longshot contracts have premium spreads — adjust 
  Kelly sizing for low-probability markets
- Order book depth decays near resolution — relevant 
  for exit timing in Phase 4+
- Wash trading is low (~1% self-counterparty) — 
  validates light wash-trade filtering approach
