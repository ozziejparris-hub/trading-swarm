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

## ARB_BOT Pattern

Distinct from LPs, ARB_BOTs are coordinated wallet clusters that exploit price inefficiencies across markets or platforms. They are characterised by: rapid entry/exit within seconds, near-simultaneous trades across related markets, and wallet clustering (same controller, multiple addresses).

ARB_BOTs are not expressing views either — they are extracting mechanical inefficiencies. Including them contaminates ELO scores and inflates apparent "legendary" counts.

**Our DB exclusions (493-trader clean pool):**
- 257 wallets flagged as `LP_ARTIFACT` — excluded
- 111 wallets flagged as `ARB_BOT` — excluded
- Clean pool: 493 traders with `research_excluded=0, bot_type=NULL`

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
