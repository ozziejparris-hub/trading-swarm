-- STR-004 Signal Scan Query — Capital-Weighted Legendary Aggregate
-- Pre-registered: 2026-05-08
-- Strategy: brain/strategy-registry.md → STR-004
--
-- PURPOSE:
--   Identify unresolved markets where legendary traders collectively hold
--   a capital-weighted position that diverges from the crowd market price
--   by >= 20 percentage points.
--
-- IMPORTANT — MARKET PRICE:
--   Market price (current YES price) is NOT stored in our DB.
--   The scan below calculates yes_capital, no_capital, legendary_yes_pct
--   per market, but divergence_pp cannot be computed without market_price.
--
--   At scan time, signal-agent MUST:
--   1. Run this query to get candidate markets and legendary_yes_pct
--   2. Fetch current YES price for each market from Polymarket Gamma API:
--      GET https://gamma-api.polymarket.com/markets?id=<market_id>
--      (field: .markets[0].outcomePrices[0] for YES price)
--   3. Compute: divergence_pp = legendary_yes_pct - market_price_yes * 100
--   4. Fire signal only if abs(divergence_pp) >= 20
--
-- This two-step approach is required because Polymarket prices are
-- real-time and not stored in our static DB snapshot.
-- ---------------------------------------------------------------------------

WITH legendary_traders AS (
    -- Qualifying legendary trader pool (mirrors integration-contract.md criteria)
    SELECT
        trader_address,
        elo_score,
        resolved_trades_count
    FROM traders
    WHERE
        elo_score > 2175
        AND research_excluded = 0
        AND resolved_trades_count >= 20
        AND bot_type IS NULL
),

market_positions AS (
    -- Aggregate legendary capital per market, per outcome side
    -- Uses the positions table which tracks current open exposure
    SELECT
        p.market_id,
        SUM(CASE WHEN p.outcome = 'YES' THEN p.amount ELSE 0 END) AS yes_capital,
        SUM(CASE WHEN p.outcome = 'NO'  THEN p.amount ELSE 0 END) AS no_capital,
        COUNT(DISTINCT p.trader_address) AS legendary_trader_count,
        SUM(p.amount) AS total_legendary_capital
    FROM positions p
    INNER JOIN legendary_traders lt ON p.trader_address = lt.trader_address
    -- Only include positions on unresolved markets
    INNER JOIN markets m ON p.market_id = m.id
    WHERE
        m.resolved = 0          -- unresolved markets only
        AND m.active = 1        -- market must be live
        AND p.amount > 0        -- ignore zero-value positions
    GROUP BY p.market_id
),

filtered_markets AS (
    -- Apply STR-004 minimum thresholds (pre-price-fetch filter)
    SELECT
        mp.market_id,
        m.question                          AS market_title,
        m.end_date_iso                      AS resolution_date,
        mp.yes_capital,
        mp.no_capital,
        mp.legendary_trader_count,
        mp.total_legendary_capital,
        ROUND(
            mp.yes_capital * 100.0
            / NULLIF(mp.yes_capital + mp.no_capital, 0),
            2
        )                                   AS legendary_yes_pct,
        -- divergence_pp placeholder: requires market_price_yes from API
        -- signal-agent populates this after Gamma API fetch
        NULL                                AS market_price_yes,
        NULL                                AS divergence_pp
    FROM market_positions mp
    INNER JOIN markets m ON mp.market_id = m.id
    WHERE
        mp.total_legendary_capital >= 10000  -- $10K minimum aggregate stake
        AND mp.legendary_trader_count >= 3   -- minimum 3 legendary traders
        -- Both sides must have some capital to compute a meaningful ratio
        AND mp.yes_capital > 0
        AND mp.no_capital > 0
)

SELECT
    market_id,
    market_title,
    resolution_date,
    yes_capital,
    no_capital,
    legendary_trader_count,
    total_legendary_capital,
    legendary_yes_pct,
    -- After signal-agent fetches market_price_yes from Gamma API,
    -- the effective WHERE condition for signal firing is:
    --   ABS(legendary_yes_pct - (market_price_yes * 100)) >= 20
    market_price_yes,   -- NULL until Gamma API fetch at scan time
    divergence_pp       -- NULL until computed post-fetch
FROM filtered_markets
ORDER BY total_legendary_capital DESC;

-- ---------------------------------------------------------------------------
-- TRADER DETAIL SUB-QUERY (for signal payload construction)
-- Run this for each market_id that passes the divergence threshold
-- to enumerate individual legendary trader positions.
-- ---------------------------------------------------------------------------

-- SELECT
--     p.trader_address,
--     lt.elo_score,
--     p.outcome,
--     p.amount                             AS position_size,
--     ROUND(p.amount * 100.0
--           / NULLIF(mp_total.total_cap, 0), 2)  AS pct_of_market_legendary_capital
-- FROM positions p
-- INNER JOIN legendary_traders lt ON p.trader_address = lt.trader_address
-- INNER JOIN markets m ON p.market_id = m.id
-- JOIN (
--     SELECT market_id, SUM(amount) AS total_cap
--     FROM positions p2
--     INNER JOIN legendary_traders lt2 ON p2.trader_address = lt2.trader_address
--     WHERE p2.market_id = '<TARGET_MARKET_ID>'
--     GROUP BY p2.market_id
-- ) mp_total ON p.market_id = mp_total.market_id
-- WHERE
--     p.market_id = '<TARGET_MARKET_ID>'
--     AND m.resolved = 0
-- ORDER BY p.amount DESC;
