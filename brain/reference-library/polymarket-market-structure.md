# Polymarket Market Structure — LP Mechanics and Signal Design Constraints

**Audience:** quant-research-agent, signal-agent. Read before designing any new strategy.

---

## LP Mechanics

Liquidity providers (LPs) on Polymarket hold **both YES and NO positions simultaneously**. They do not express a directional view — they profit by capturing the bid-ask spread. A typical LP wallet shows $50K YES and $48K NO on the same market: net exposure is ~$2K, not $98K directional.

This means: **a large wallet size is not a signal**. LPs are the largest capital holders in most markets and are systematically uninformative about outcome direction.

---

## The 95% Directional Threshold — LP Filter

STR-003 requires 95%+ of a trader's capital on a single side. LPs structurally never reach this. A wallet with $50K YES / $48K NO is 51% directional — excluded. Only genuine conviction positions clear the filter.

Why 95% and not 80% or 70%: our DB contains legendary traders (ELO > 2175) who hold mixed positions for hedging or partial conviction. At 80%, some LP-adjacent wallets slip through. At 95%, the only positions that pass are ones where the trader has committed almost no capital to the opposing side — operationally impossible for a spread-capturing LP.

**Implication:** when a legendary trader (ELO > 2175) clears the 95% filter, the position is genuinely informational. The threshold is not arbitrary — it is a mechanical consequence of how LP economics work.

---

## ⚠ CRITICAL: Authoritative Research Pool Filter

**Do not rely on any embedded trader count in this file — run the explicit filter to get the current authoritative pool size.** Pool counts change as new traders are added and as script regressions occur (see warning below).

Always use the full explicit filter:

```sql
-- AUTHORITATIVE CLEAN POOL FILTER — always use this:
WHERE research_excluded = 0
  AND resolved_trades >= 20
  AND bot_suspect = 0
  AND wash_trade_suspect = 0
-- Do NOT use research_excluded=0 alone — it massively overstates the pool.
```

Root cause: update_research_exclusions.py's set-eligible logic is inconsistent with its reverse-exclusion logic. Until code-hygiene fixes this, the explicit filter is the authoritative query.

**History of pool count instability:**
- 2026-05-13: `research_excluded=0` returned 604; explicit filter returned 493 (111-trader gap)
- 2026-05-18: `research_excluded=0` returned 7,852; explicit filter returned **104** (7,748-trader regression)

The script set research_excluded=0 for thousands of traders lacking ≥20 resolved trades in a single run on or before May 18. The explicit filter is the ONLY reliable method. Any count embedded in this file or any other file is a historical snapshot only — do not act on it without re-running the query.

---

## ARB_BOT Pattern

Distinct from LPs, ARB_BOTs are coordinated wallet clusters that exploit price inefficiencies across markets or platforms. They are characterised by: rapid entry/exit within seconds, near-simultaneous trades across related markets, and wallet clustering (same controller, multiple addresses).

ARB_BOTs are not expressing views either — they are extracting mechanical inefficiencies. Including them contaminates ELO scores and inflates apparent "legendary" counts.

**Our DB exclusions (493-trader clean pool as of 2026-05-13):**
- 257 wallets flagged as `LP_ARTIFACT` — excluded
- 111 wallets flagged as `ARB_BOT` — excluded
- Clean pool: 493 traders with `research_excluded=0, bot_type=NULL` (as of May 13)

**WARNING 2026-05-18:** 39 new traders have appeared above ELO 3,500 (max ELO now 4,305 vs 3,471 May 13). Same structural signature as the ARB_BOT cluster excluded May 6. Run RQ0.2 bot detection before trusting any signals from traders above ELO 3,500 — the cluster may be coordinated arbitrage wallets not yet flagged. Bring RQ0 gate forward from June 13 if these traders appear in signal generation paths.

---

## Implications for Signal Design

**Why STR-001 failed:** counted the number of legendary traders on each side, not capital. LPs hold large balanced positions — they triggered both YES and NO legs simultaneously on 78% of markets. The signal fired in both directions and added no edge over market price.

**Why STR-003 works:** 95% directional threshold mechanically filters all LP activity. Only conviction holders remain. Result: YES 61.1% (n=18), NO 77.8% (n=9) at eventual resolution on the clean pool.

**Why STR-004 uses capital weighting:** some legendary traders hold mixed positions (e.g., 60/40 YES/NO) that are still informative in aggregate. Capital-weighted consensus neutralises the balanced LP positions (which contribute equal weight to both sides and cancel out) while preserving the net directional signal from traders with genuine skew.

---

## Design Rules Derived from This Structure

1. Always filter on `research_excluded=0, bot_type=NULL` before any analysis.
2. Any directional filter below 95% requires explicit justification — LP contamination risk is real below that threshold.
3. Capital-weighted aggregates (STR-004) are more robust than trader-count aggregates (STR-001) because LP positions self-cancel.
4. When in doubt: check whether the top capital holders on a market are LP-structured before interpreting position data.

---

## Gamma API Known Limitations (as of 2026-05-11)

### Search and filter endpoints broken
The following Gamma API patterns do NOT work and should not be used:

  GET /markets?conditionId={cid}    — filter silently ignored
  GET /markets?condition_id={cid}   — filter silently ignored
  GET /markets?search={query}       — returns default popular markets
  GET /events?search={query}        — returns default popular markets
  GET /public-search?query={query}  — returns 422 error

All of the above return the same 20 default high-volume markets
regardless of parameters.

### What DOES work
  GET /markets/{api_id}    — direct lookup by numeric api_id ✅
  GET /markets/{api_id}    — used by verify_market_titles.py ✅

### Implication for manual investigation
When investigating a specific market by condition_id or title,
the Gamma API cannot be used for search. Alternatives:
  1. Query the local DB by condition_id directly
  2. Use the Polymarket website URL pattern:
     https://polymarket.com/event/{event-slug}
  3. Use the Data API for on-chain resolution data

### Implication for production scripts
No production scripts are affected — all scripts use
/markets/{api_id} direct lookup which continues to work.
