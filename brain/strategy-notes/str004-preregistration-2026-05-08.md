# STR-004 Pre-Registration — Capital-Weighted Legendary Aggregate Signal

Pre-registration date: 2026-05-08
Filed by: Oscar (manual pre-registration before founding case resolves)
AsPredicted note: Not formally filed externally. Methodology documented
  here before the June 30 2026 resolution of the founding case is known.
  This document constitutes the system's internal pre-registration record.

---

## Hypothesis

Capital-weighted aggregate positions of legendary traders on a given
market, when diverging meaningfully from the crowd market price, predict
the eventual resolution outcome better than the market price alone.

Specifically: when the capital-weighted YES percentage across ALL legendary
traders (ELO > 2175, research_excluded=0, resolved_trades_count >= 20,
bot_type IS NULL) on an unresolved market diverges from the market's current
YES price by >= 20 percentage points, the legendary aggregate is a reliable
directional predictor.

This extends beyond STR-003 (which requires a single 95%+ directional
trader) by treating the *sum* of legendary capital allocation as a price
signal — including traders with mixed positions — since net imbalances
reveal aggregate directional conviction even when no single trader is
fully committed.

---

## Signal Definition

```
legendary_yes_pct  = yes_capital / (yes_capital + no_capital)
divergence         = legendary_yes_pct - market_price_yes

Signal fires when ALL of:
  1. abs(divergence) >= 0.20          (>= 20pp gap)
  2. total_legendary_capital >= 10000  ($10K minimum aggregate stake)
  3. legendary_trader_count >= 3       (at least 3 qualifying traders)

Direction:
  YES signal: legendary_yes_pct > market_price_yes (smart money bullish)
  NO signal:  legendary_yes_pct < market_price_yes (smart money bearish)

Qualifying traders (per integration-contract.md):
  ELO > 2175
  research_excluded = 0
  resolved_trades_count >= 20
  bot_type IS NULL
```

---

## Key Distinction from Prior Strategies

- **STR-001 (SUSPENDED)**: Counted traders — convergence of directional
  positions on same side. Structural flaw: 78% of markets saw legendary
  traders split across both sides, producing paired 50/50 signals.

- **STR-003 (EXPERIMENTAL)**: Requires 95%+ single-trader capital
  concentration. Misses traders with mixed positions and entire markets
  where no single trader has 95%+ conviction.

- **STR-004 (this strategy)**: Capital weighting across ALL legendary
  positions on a market. LPs holding both sides at equal weight contribute
  neutrally. Only net imbalances produce a signal. This directly addresses
  the STR-001 structural flaw by using capital weight, not trader count.

---

## Founding Validation Case

**Market**: Russia x Ukraine ceasefire by Q2 2026?
**Market ID**: 0x7b629fc0b14bece5d568e748f7a8c7c472f90833e9a00c3d4cc3c49e267f194c
**Note on DB title**: The DB may store this as "Will Russia invade Ukraine
  by Q2 2026?" — the actual Polymarket market is about ceasefire, confirmed
  via API. Direction=YES means ceasefire happens by June 30 2026.

**Signal metrics (as of 2026-05-08)**:
```
Legendary traders:        8
Total legendary capital:  $1,745,257.28
YES capital:              $972,565.59
NO capital:               $772,691.70
Legendary YES pct:        55.7%
Market price YES:         7%
Divergence:               +48.7pp  (far exceeds 20pp threshold)
Resolution date:          2026-06-30
Category:                 Geopolitics
Category accuracy:        92.3% (HIGH confidence, finding 2026-05-07-CATEGORY-GEOPOLITICS-001)
```

None of the 8 traders individually hold >= 95% directional concentration
(i.e. STR-003 would NOT fire on this market). STR-004 captures this
signal type that STR-003 misses entirely.

---

## Pass / Stop Criteria

### Pass Criterion (either satisfies)
- **Primary**: Founding case resolves YES (ceasefire happens by June 30 2026)
  AND accuracy >= 60% on the first 10 markets where STR-004 fires
- **Secondary**: Signal proves directionally correct in at least 6/10 of
  the first 10 markets where it fires (regardless of founding case outcome)

### Stop Criterion
- Accuracy < 50% on 10+ resolved markets → abandon STR-004
- Note: this is below the system 60% deployment threshold but above chance —
  sub-50% would indicate the aggregate signal is noise or anti-predictive

---

## Validation Plan

1. **Founding case resolution**: June 30 2026. This single case cannot
   validate the strategy but serves as the first data point and confirms
   the signal fires correctly.

2. **Accumulation phase**: Signal-agent runs STR-004 scan each cycle.
   Each new qualifying market is logged to signals.json. Each resolved
   market is scored by feedback-loop-agent.

3. **Formal backtest**: After n=10 resolved markets. Run by backtest-agent
   against CI thresholds. Category breakdown (Geopolitics vs Elections vs
   other) required given known category accuracy asymmetry.

4. **Separate YES/NO accuracy tracking**: Required. STR-003 showed NO
   signals more reliable (77.8% vs 61.1%). Track this split from the start.

5. **Next revalidation trigger**: After June 30 2026 founding case resolves,
   then continue accumulating. Formal backtest when n=10.

---

## Risks and Mitigations

1. **LP contamination** (the STR-001 killer): STR-004 is specifically
   designed to handle LPs. An LP holding $100K YES and $100K NO contributes
   neutrally to legendary_yes_pct — they push the ratio toward 50%, not
   toward either side. Only net imbalances matter. This is structurally
   different from STR-001's trader counting.

2. **Capital concentration in founding case**: The Russia/Ukraine market
   has $1.74M legendary capital — unusually large. Most markets will have
   less. The $10K minimum threshold may need tuning after n=5 signals.

3. **Market price staleness**: The DB does not store real-time market prices.
   The signal scan must fetch current prices from the Polymarket API at scan
   time. Using last-trade price as proxy introduces lag. Document in each
   signal what price source was used.

4. **Same-capital LP across many markets**: A single large LP holding
   balanced positions in 50 markets will appear in all 50 scans but
   contribute neutrally. This is correct behavior — they are not counted
   as a directional signal.

5. **Elections category**: Known 46.7% accuracy (below chance). If STR-004
   fires on an Elections market, apply Elections skepticism flag per
   finding 2026-05-07-CATEGORY-ELECTIONS-001. Geopolitics signals get
   confidence boost (92.3% accuracy).
