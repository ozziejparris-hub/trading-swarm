# NEG_RESOLVED Pattern — Hybrid Taker/Maker Traders (2026-06-08)
## Source
Internal analysis of vgregoire/polymarket-users external dataset
## Summary
Six traders flagged as NEG_RESOLVED (high pnl_taker_politics but negative pnl_resolved_politics) were investigated. Pattern explained: these traders run both directional taker operations AND market-making operations in politics markets. Their taker P&L is positive ($52K-$114K) but their maker P&L is deeply negative (-$103K to -$214K), resulting in net negative resolved P&L.

Key diagnostic: implied_open_position_gap = pnl_taker_politics + pnl_maker_politics - pnl_resolved_politics ≈ $0 for 4/6 traders, confirming all positions are settled — this is NOT a dataset cutoff artefact.

These traders have genuine directional skill on taker trades. Their maker losses are from a separate market-making operation. For geo_elo purposes (accuracy-based, not P&L-based), their taker trades should score correctly.

## Action
Four traders added to manual_watchlist (Veythoris, Lioren, Sylvaren, anonymous). Two traders with large implied open position gaps ($54K-$66K) deferred — positions not fully settled.

Filter recommendation: when screening for LEGENDARY candidates, use pnl_taker_politics > threshold rather than pnl_resolved_politics > threshold. Resolved P&L can be negative for genuinely skilled taker traders who also run loss-making market-making operations.
## Verified
Yes — internal analysis, implied gap calculation confirms pattern
