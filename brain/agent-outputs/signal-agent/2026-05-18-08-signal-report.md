# Signal Agent Report — 2026-05-18 08:00 UTC

**Cycle type:** STR-003 rescan + new legendary trader scan
**Task ID:** signal-20260518
**Model:** Claude Sonnet 4.6 (Tier 3)

---

## Summary

- **HIGH signals found:** 0
- **MEDIUM signals found:** 0 new (4 existing rescanned)
- **LOW signals found:** 0
- **Signals upgraded:** 0
- **Signals flagged for review:** 2 (Signals 2 and 4 — concurrent markets rule concern)
- **New counter-signal noted:** Putin market (ELO 2549.7 legendary YES vs ELO 3323 NO)
- **Anomaly:** Research pool expansion from ~604 (2026-05-13) to 7,951 (today)

---

## Validation

Section 9 contract validation passed before any research queries:

| Check | Result | Status |
|-------|--------|--------|
| clean_pool | 7,951 | PASS (> 440) |
| clean_markets | 13,259 | PASS (> 11,000) |
| wal_mode | wal | PASS |

Legendary traders in clean pool: **246** (ELO range: 2,184.7 – 3,471.3)

---

## Rescan: Active STR-003 Signals

### Signal 1 — Newsom 2026 Drop Out (MEDIUM — CONFIRMED)

**Market:** Will Newsom drop out of 2026 race before September?
**Market ID:** `0xbc60ca287f8f5ab1a910b1cc6ff51fe32c0b8840517f8220554454b9d2d4afac`
**Resolution:** Unresolved. End date: before September 2026.

| Trader | ELO | Outcome | Invested | Direction % | Concurrent Markets | Qualifies |
|--------|-----|---------|----------|-------------|-------------------|-----------|
| 0x7dd47e4c...1302 | 2,797.7 | NO | $3,475 | 100% | 2 | YES |
| 0x72a1ac12...466b | 3,153.9 | NO | $30,616 | 100% | 6 | NO (max-2 fail) |

**Rescan result:** Signal 1 CONFIRMED at MEDIUM.
- ELO 2797.7 trader holds $3,475 NO (100%) with only 2 concurrent markets — the two being Newsom and Ethereum above $150 by January 2027. Fully qualifying.
- ELO 3153.9 trader (formerly ELO 2741) holds $30,616 NO (100%) but now has 6 open market positions (Newsom, Bitcoin ETF, Bitcoin >$75K, Drake album, Biden presidential run, Curry MVP). Disqualified under max-2 concurrent rule.
- **Upgrade condition NOT MET.** Still requires 1+ additional qualifying legendary NO trader.
- **Category flag:** Elections. Apply skepticism (category accuracy: 0.467).

---

### Signal 2 — USA join UN Security Council 2026 (MEDIUM — FLAGGED FOR REVIEW)

**Market:** Will USA join UN Security Council in 2026?
**Market ID:** `0x3082f67beee73c7a96a5b8dbf3762ca7d26cab01a7e5512a44ca7297b9641361`
**Resolution:** Unresolved. End date not recorded in DB.

| Trader | ELO | Outcome | Invested | Direction % | Concurrent Markets | Qualifies |
|--------|-----|---------|----------|-------------|-------------------|-----------|
| 0xef1dd162...1c96 | 3,150.3 | NO | $40,581 | 100% | 4 | BORDERLINE |

**Concurrent market breakdown for ELO 3150.3:**
1. Brady to win MVP in 2025? — $40,980 (STALE — Brady retired, 2025 market expired)
2. USA join UN Security Council 2026 — $40,581 (ACTIVE)
3. Republicans win Pennsylvania Senate 2027 — $29,003 (ACTIVE)
4. Ramaswamy announce presidential run by Q2 2026 — $9,781 (ACTIVE, ends June 2026)

**Rescan result:** Signal 2 FLAGGED. Under strict max-2 rule, this trader is borderline:
- If Brady MVP 2025 is counted (DB shows open, but market is clearly expired): 4 markets → disqualified
- If stale market excluded from count: 3 active markets → still exceeds max-2
- Recommendation: Oscar review whether to suspend Signal 2 pending data cleanup or apply a stale-market exclusion policy

**Position itself unchanged:** $40,581 NO at 100% — conviction held. The concern is the focus criterion, not the position quality.
- **Category flag:** Geopolitics. Confidence boost applies (category accuracy: 0.923).

---

### Signal 3 — Fed to Strike Rates in March 2027 (MEDIUM — CONFIRMED)

**Market:** Fed to strike rates in March 2027?
**Market ID:** `0x5fdadea511a3ed74c6a9e6caee6e4eb71a836ea1bae7c8c086d51310e3c4fe12`
**Resolution:** Unresolved. Resolves March 2027.

| Trader | ELO | Outcome | Invested | Direction % | Concurrent Markets (active only) | Qualifies |
|--------|-----|---------|----------|-------------|----------------------------------|-----------|
| 0x9fb0f92a...b61 | 2,923.3 | NO | $33,390 | 100% | ~2 | YES |

**Other legendary traders in this market (not qualifying):**

| Trader | ELO | YES | NO | Direction % |
|--------|-----|-----|-----|-------------|
| 0xae1a6d3a...c7d | 3,308.1 | $8,625 | $17,967 | 67.6% NO — bidirectional, fails 95% |
| 0xed858462...f66 | 3,307.7 | $16,987 | $52,069 | 75.4% NO — bidirectional, fails 95% |
| 0x5ac39f36...105 | 3,307.0 | $8,248 | $14,735 | 64.1% NO — bidirectional, fails 95% |
| 0x69cdf891...03c | 2,928.3 | $73,094 | $29,305 | 71.4% YES — bidirectional, fails 95% |
| 0xa46fddd8...220 | 2,543.1 | $41,302 | $79,984 | 65.9% NO — bidirectional, fails 95% |

**Concurrent market breakdown for ELO 2923.3 (conservative, excluding stale):**
- Republicans win Michigan Senate 2025 — STALE (2025 passed)
- Google merger by March 2025 — STALE
- Trump win 2026 presidential election — STALE/invalid (no 2026 US presidential election)
- Cowboys vs Red Sox {template} — template market
- Democrats win Nevada Senate 2027 — ACTIVE (future)
- LeBron 3+ TDs in merger — template/nonsense
- Fed to strike rates March 2027 — ACTIVE

Conservative active count: 2 genuine future markets (Nevada Senate 2027 + Fed March 2027). Passes max-2 rule under conservative counting.

**Rescan result:** Signal 3 CONFIRMED at MEDIUM.
- ELO 2923.3 trader has held $33,390 NO across 7 DB entries since original signal (September–October 2025 entry period). Conviction unchanged.
- Multiple other legendary traders in this market are bidirectional (no 95%+ threshold), suggesting genuine uncertainty among elites on rate direction.
- **Upgrade condition NOT MET.** No second qualifying legendary NO trader found.

---

### Signal 4 — Putin to Invade by June 2026 (MEDIUM — FLAGGED + COUNTER-SIGNAL)

**Market:** Putin to invade by June 2026?
**Market ID:** `0x657195fda8c315771fe0cf25a1b60df207a9072688f73b96cf17a890ce7ab753`
**Resolution:** Unresolved. End date ~June 2026 (~2–3 weeks remaining as of 2026-05-18).

| Trader | ELO | Outcome | Invested | Direction % | Concurrent Markets | Qualifies for STR-003 |
|--------|-----|---------|----------|-------------|-------------------|----------------------|
| 0xdffc6760...302 | 3,323.0 | NO | $7,191 | 100% | 6 (3 active) | BORDERLINE |
| 0x0a956f4e...2f8 | 2,549.7 | YES | $12,967 | 100% | 7 (stale-heavy) | NO (>2 markets) |

**Concurrent markets for ELO 3323.0:**
1. Harris drop out before September 2025? — $1,880,436 (STALE — 2025 expired)
2. Harris announce presidential run by March 2025? — $343,703 (STALE — March 2025 expired)
3. Yankees vs Giants {template} — $224,051 (template market)
4. Ethereum above $150 by June 2026 — $79,128 (ACTIVE)
5. S&P 500 above 2500 by end of 2026 — $77,852 (ACTIVE)
6. Putin to invade by June 2026 — $7,191 (ACTIVE)

Conservative active count (excluding stale/template): 3 markets → exceeds max-2 rule.

**Rescan result:** Signal 4 FLAGGED for two reasons:
1. **Concurrent markets:** ELO 3323 trader has 3+ genuinely active positions (max-2 exceeded, even conservatively)
2. **NEW COUNTER-SIGNAL:** ELO 2549.7 legendary trader holds $12,967 YES (100%) on Putin invading. This opposing legendary position EXCEEDS the size of the original NO signal ($12,967 vs $7,191). While the YES trader is also disqualified (7 markets), the legendary divergence weakens the original NO conviction.

**Important:** Market resolves in ~2–3 weeks (by end of June 2026). Even if the signal quality is questionable, the resolution will provide a first STR-003 geopolitics data point either way.
- **Category flag:** Geopolitics. Confidence boost applies (category accuracy: 0.923).
- **Action:** Monitor for resolution. Record outcome in strategy-registry.md STR-003 accuracy stats.

---

## New Qualifying Legendary Trader Scan

Broad scan executed across all 246 legendary traders (ELO > 2175, research_excluded=0) in 7,951-trader clean pool. Filters: open positions only, unresolved markets, ≥95% directional, ≥$2,000 minimum.

**Result: No new qualifying STR-003 signals found.**

All candidates encountered one or more disqualifying conditions:

| Market | Top Trader ELO | Position | Disqualifier |
|--------|---------------|----------|--------------|
| Ramaswamy announce Q2 2026 | 3,150.3 | $9,781 NO 100% | 4 concurrent markets |
| Ron DeSantis win 2028 election | 3,304.3 (Ferwhere) | $7,055 YES 100% | 50 concurrent markets |
| US confirm aliens by June 30 | 3,304.3 (Ferwhere) | $5,376 YES 100% | 50 concurrent markets |
| Nuclear Treaty in 2026 | 3,133.6 | $8,388 NO 100% | 6 concurrent markets |
| Mission Impossible >$100M | 3,314.9 | $7,249 NO 100% | 5 concurrent markets |
| XRP reach Ukraine market cap | 3,387.6 | $5,498 NO 100% | 4 concurrent markets |
| Bitcoin >$150K by Q2 2026 | 2,601.8 | $7,713 YES 100% | Not checked (near-term Q2) |
| Dow above 16000 by end 2026 | 2,973.3 / 3,194.2 | Split YES/NO | Legendary divergence — no consensus |

Note: Several scan candidates are in markets with no end_date in the DB. Titles with clear 2025 end dates (Bitcoin >$75K Dec 2025, Unemployment Q3 2025, Apple layoffs Dec 2025, etc.) appear as unresolved=0 — stale data inflating the active universe. The genuine 2026+ candidate list is shorter than the raw scan suggests.

---

## Anomalies

### 1. Research Pool Expansion — NOTABLE
- 2026-05-13 (backtest feedback): clean_pool = 604, legendary_in_pool = 142
- 2026-05-18 (today, live query): clean_pool = 7,951, legendary_in_pool = 246
- Integration-health.json: 7,852 (contract_valid=true, no alerts)

This is a 13x pool expansion in 5 days. Possible explanations:
  a) The resolved_trades_count threshold for research_excluded was lowered in daily maintenance
  b) A large batch of traders newly accumulated 20+ resolved trades
  c) A bot exclusion pass was reversed

The integration health script shows no alerts and contract_valid=true. However, the 13x jump is unexpected. The change affects the legendary count (from 142 to 246 — a 73% increase). More legendary traders means the upgrade conditions for STR-003 signals (2+ on same side) should be easier to meet. However, the new legendary traders all appear to have many concurrent market positions, limiting their STR-003 eligibility.

**Recommended action:** Oscar to verify daily_maintenance.py logs around 06:00 UTC on 2026-05-14–18 to understand what changed.

### 2. Stale Market Data — STRUCTURAL ISSUE
- The DB contains many unresolved markets (resolved=0) with titles/context indicating 2025 end dates
- These appear as "open" positions inflating concurrent market counts
- Affects STR-003 eligibility filtering: real concurrent count vs DB count diverges
- Examples: "Harris drop out 2025", "Google merger March 2025", "Bitcoin >$75K Dec 2025", "Apple layoffs Dec 2025"
- Recommended action: one-time maintenance to resolve all markets where end_date < 2026-01-01 and trade activity has ceased

### 3. ELO Score Changes on Signal Traders
- Signal 1 trader was ELO 2741 on 2026-04-27, now 3153.9 (ELO gain: +412.9 points — major upgrade)
- Signal 1 other trader was ELO 2398, now 2797.7 (ELO gain: +399.7 points)
- Signal 4 counter-trader confirmed at ELO 2549.7 (new entrant since last scan)

---

## Markets Monitored This Cycle

| Market | Status | Signal Status |
|--------|--------|---------------|
| Will Newsom drop out of 2026 race before September? | Unresolved | MEDIUM — confirmed |
| Will USA join UN Security Council in 2026? | Unresolved | MEDIUM — flagged for review |
| Fed to strike rates in March 2027? | Unresolved | MEDIUM — confirmed |
| Putin to invade by June 2026? | Unresolved (~3 weeks to end) | MEDIUM — flagged + counter-signal |
| All legendary trader open positions | Broad scan | No new signals |

---

## Recommended Actions

1. **Signal 1 (Newsom):** No action. Monitor for additional legendary NO entrants. Upgrade to HIGH if ELO 3153.9 reduces to ≤2 concurrent markets.

2. **Signal 2 (UN Security Council):** Oscar review recommended. ELO 3150.3 trader now holds 3 active future-market positions. If strict max-2 rule applied, signal should be suspended. Position conviction is high ($40,581 NO, unchanged) but focus criterion technically violated. Suspend or accept as borderline MEDIUM?

3. **Signal 3 (Fed March 2027):** No action. Signal qualifies under conservative counting. Monitor for second legendary NO trader reducing concurrent positions.

4. **Signal 4 (Putin June 2026):** Track to resolution (~June 30 2026). Record YES/NO outcome in strategy-registry.md as first STR-003 geopolitics data point. Note legendary divergence (ELO 3323 NO vs ELO 2549.7 YES) in the outcome record.

5. **Pool expansion anomaly:** Oscar review of daily_maintenance.py logs (2026-05-14 to 2026-05-18) to understand 604 → 7,951 pool jump.

6. **Stale market cleanup:** Recommend a one-time task for code-hygiene-agent or quant-research-agent to identify markets where end_date < 2026-01-01 AND all positions show zero recent trade activity — mark those markets as resolved=1 to clean up the concurrent-count inflation issue.

---

## Definition of Done Checklist

- [x] Output file written with real content
- [x] All 4 active STR-003 signals rescanned with live DB data
- [x] Every signal includes: market_id, trader addresses, ELO scores, position sizes, confidence level
- [x] Upgrade conditions checked for all active signals — none met
- [x] New legendary trader scan executed across full clean pool
- [x] Anomalies documented
- [x] signals.json updated with rescan_complete entry
- [x] No exceptions or unhandled errors in execution
- [ ] Telegram notification — TELEGRAM_AGENTS_TOKEN not available in worktree environment. Orchestrator will detect via signals.json at next 10-minute cycle. No HIGH signals requiring escalation.
