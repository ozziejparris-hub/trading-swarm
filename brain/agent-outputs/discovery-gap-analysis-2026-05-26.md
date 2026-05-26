# Trader Discovery Gap Analysis — 2026-05-26

Audit of current discovery mechanisms against the Mitts/Ofir (2022)
composite-score approach to insider/informed-trader detection.

---

## Q1: Market-Resolution Sweeps

**No.** There is no mechanism that sweeps all participants from a market when it resolves.

`monitor.py` calls `self.analyzer.check_market_resolutions()` every 10 cycles (~2.5 h)
to detect newly-resolved markets and update the `resolved` flag in the `markets` table.
This is a bookkeeping step — it does not fetch all traders who participated in the
just-resolved market to discover new wallets.

`discover_leaderboard_traders.py` sweeps the top N markets by trade count over the last
90 days, but:
- It is run manually (or could be scheduled), not triggered by resolution events.
- It targets active/recent markets, not newly-resolved ones.
- By the time a market appears in a resolution sweep it may already be cold (API returns
  fewer trades for old, closed markets).

**Gap**: A resolution-triggered sweep — "market just closed, pull all participants and
evaluate them" — does not exist.

---

## Q2: New-Wallet Detection Within 30 Days of Resolution

**No dedicated mechanism.**

Two partial signals exist:

| Mechanism | What it does | Why it falls short |
|---|---|---|
| `pre_resolution_intelligence.py` | Scans markets resolving within 7 days; compares smart-money positioning vs. market price to flag divergence | Looks at *known* traders only — does not discover new wallets |
| `detect_insider_activity.py` | Flags fresh wallets (≤90 days in DB) making large bets at low odds | Time-window is absolute (last 2 h lookback per cycle), not relative to resolution date; triggers on any geo market, not specifically near-resolution ones |

Neither system answers the question: "Who is a wallet that first appeared specifically in
the 30-day window before this market resolves, with a bet on the winning side?"  That
intersection — new wallet × near-resolution timing × correct direction — is the
Mitts/Ofir core detection unit and is absent here.

---

## Q3: insider_signals Table — Contents and Population

**Schema** (`detect_insider_activity.py:94-128`):

```
insider_signals:
  id, detected_at, market_id, market_title, outcome,
  trader_address, username, position_size, entry_price,
  wallet_age_days, markets_count, trade_timestamp, pattern, alerted

insider_clusters:
  id, detected_at, market_id, market_title, outcome,
  wallet_count, combined_size, window_start, window_end, alerted
```

**How populated**: `_insider_detection_loop()` in `system_observer.py` (line 3234)
calls `detect_individual_signals()` and `detect_cluster_signals()` every 15 minutes
with a 2-hour lookback window. Results are written via `save_signals()`.

**Individual signal criteria** (all five must hold):
1. Wallet's `first_seen` in DB ≤ 90 days ago (default; docstring says "30 days" but
   parameter default is `wallet_age_days=90`)
2. Single-bet position > $2,000
3. Market price at entry < $0.35 (low-odds entry on the winning/unexpected side)
4. Trader has traded in ≤ 2 markets total in our DB
5. Market title passes geopolitics keyword filter

A stronger sub-pattern triggers at position ≥ $10,000 with (price ≤ 0.90 or size ≥ $50,000).

**Cluster criteria**: 3+ fresh wallets (same `wallet_age_days` cutoff) on the same
outcome/market within any 6-hour window, each with position > $1,000.

The `alerted` flag prevents re-sending on observer restart; seeds from DB on startup.

**Important**: The table captures *detection-time* anomalies only. It does not link back
to whether the bet was profitable at resolution. There is no retroactive scoring of
signals against outcomes.

---

## Q4: Prospective Discovery Logic

**No.** There is no mechanism that finds traders *before* they have a track record.

Current discovery channels and their minimum requirements:

| Channel | Trigger | Minimum track record required |
|---|---|---|
| Live feed (`check_for_new_trades`) | 15-min poll | Trader must already be `is_flagged=1` — only monitors known traders |
| Leaderboard sweep (`discover_leaderboard_traders.py`) | Manual / scheduled | 3+ geo markets, 10+ trades, $1,000+ volume |
| Manual watchlist (`add_watched_trader.py`) | Human decision | None — but a human must identify the trader first |
| Insider detection (`detect_insider_activity.py`) | 15-min, 2h lookback | None for the signal itself, but trader must have already traded in our market universe so a trade appears in our `trades` table |
| Backfill worker (`background_backfill_worker.py`) | Triggered after leaderboard discovery | Backfills history for zero-trade traders, but they must already be in the `traders` table |

A first-trade insider is only catchable if:
- They trade in a market the monitoring loop is currently watching (the live feed pulls
  500 recent trades from all markets, not just geopolitics), AND
- The trade appears in the 2-hour lookback window of the insider detector.

Once caught by the insider detector the wallet gets written to `insider_signals` but
is NOT automatically added to `traders` as a monitored entity. There is no pipeline
from `insider_signals` → `traders` for follow-up tracking.

---

## Q5: Gaps vs. Mitts/Ofir Composite Score

Mitts & Ofir (2022) build a 5-dimensional composite score from:

| Dimension | Mitts/Ofir definition | Our status |
|---|---|---|
| **Cross-sectional bet size** | Trade size relative to *concurrent market volume* — how large is this bet compared to all bets placed in this market this day | **ABSENT**. We track absolute dollar size, not relative to market liquidity. The insider detector uses fixed thresholds ($2k, $5k, $10k) not cross-market percentile rank. |
| **Within-trader bet size** | Trade size relative to the *same trader's historical bets* — is this unusual for THIS wallet | **ABSENT**. No "baseline bet size per trader" feature exists. A trader who normally bets $200 and now bets $15,000 is invisible to us unless they cross the fixed threshold. |
| **Profitability** | ROI on resolved positions | **PRESENT** (partial). ELO and P&L tracking cover this, but only for traders already in our `traders` table with a trade history. Prospective/new wallets have no P&L record at detection time. |
| **Pre-event timing** | Days before resolution the bet was placed; early-entry on the correct side scores highest | **PARTIAL**. `pre_resolution_intelligence.py` flags smart money in 7-day windows. The ELO system does not include a timing dimension. No feature is computed as "days before resolution" per trade across the full trader pool. |
| **Directional concentration** | Does the trader consistently pick the same outcome (high conviction) vs. hedge across outcomes | **ABSENT**. We track `outcome` per trade but do not compute a Herfindahl or concentration ratio measuring directional consistency across markets. |

### Additional structural gaps

1. **No resolution-triggered discovery**: Mitts/Ofir could, in principle, scan all
   participants of a market on resolution day. We have no equivalent.

2. **No backward link from signal to outcome**: `insider_signals` are never scored
   against resolution results. We cannot audit whether our insider flags were right.

3. **Wallet-age proxy is coarse**: Using "first seen in our DB" as wallet age conflates
   new participants on Polymarket with old Polymarket participants who simply hadn't
   traded in our tracked universe. A wallet that has traded crypto markets for 2 years
   but just entered geopolitics would look "fresh" to us.

4. **Minimum-trades barrier for ELO entry**: Traders need 10+ trades before the
   leaderboard discovery flags them; 3+ geo markets before ELO is meaningful. Mitts/Ofir
   capture informed traders on their *first* bet in the event. We would miss a 1-trade
   insider unless they hit the fixed-threshold insider detector.

5. **No cross-market positional fingerprinting**: Mitts/Ofir look at whether a trader's
   positioning pattern (direction × timing) is abnormally correlated with resolution
   outcomes across *multiple independent events*. We have no cross-market directional
   consistency metric.

---

## Summary Table

| Capability | Have it | Quality |
|---|---|---|
| Post-resolution market sweep | No | — |
| New-wallet detection within 30d of resolution | No | — |
| Absolute bet-size anomaly | Yes (insider detector) | Coarse fixed thresholds |
| Cross-sectional bet-size (vs market volume) | No | — |
| Within-trader bet-size anomaly | No | — |
| Profitability (ROI/P&L) | Yes | Good for known traders |
| Pre-resolution timing feature | Partial | 7-day window, known traders only |
| Directional concentration metric | No | — |
| Prospective discovery (before track record) | No | — |
| Signal-to-outcome retroactive scoring | No | — |
