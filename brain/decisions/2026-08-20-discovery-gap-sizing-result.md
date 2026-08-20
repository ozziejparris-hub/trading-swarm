# 2026-08-20 — sizing the Gamma resolution-discovery blind spot: result

**Method locked in `2026-08-20-discovery-gap-sizing-prereg.md` (`a9a0cf9`),
committed before any CLOB call. Nothing in that method was adjusted after
seeing this output — every threshold, stratum boundary, sample size, and
materiality rule below was fixed before this document existed.** Script:
`scripts/discovery_gap_sizing.py` (first-repo, committed alongside this
document). Raw output: `data/characterizations/discovery_gap_sizing_20260820T211955Z.json`.
Every figure is **[V]**, produced by the committed script's single run
against the live DB and the live CLOB API, this session.

**Headline: this is not a rare edge case. Roughly two-thirds of the
markets this project's canonical backtest population actually depends on
(Geopolitics/Elections, with trades) are already resolved and completely
undiscovered.**

---

## Q2 — the relevant question — RESOLVED (full census, not a sample)

**Population:** all 317 markets matching the canonical-relevance filter
(§3 of the pre-registration: Geo/Elections, has trades, `trade_gap_flag`
clean) — **every one queried**, not sampled.

| | Count |
|---|---|
| N (census) | 317 |
| RESOLVED | **203** |
| OPEN | 98 |
| INDETERMINATE | 16 (all `http_404` — market not found on CLOB) |
| Determinate (resolved + open) | 301 |

**Point estimate: 203/301 = 67.4% of determinate Q2 markets are already
resolved.** Wilson 95% CI: **[62.0%, 72.5%]**. This is a census, not a
sample — there is no sampling error in the 203 count itself; the interval
here reflects only the standard uncertainty framing applied uniformly
across the document, not a projection from a subsample.

**Bounds accounting for the 16 indeterminate cases** (pre-registered, not
chosen after the fact): best case (indeterminate presumed open) = 203
resolved; worst case (indeterminate presumed resolved) = 219 resolved.
**The number that matters — 203 confirmed, exact, out of 317 — does not
depend on how the indeterminate cases resolve.**

**Boundary check — not concentrated in one ingestion era:** resolved
markets split `historical_backfill` 114/193 (59.1%) and `live_monitoring`
87/122 (71.3%), with 2/2 `background_backfill`. **This is not an artifact
of one old backfill batch — it affects markets from the live, ongoing
monitoring ingestion path at a higher rate than the historical backfill
batch.** This means the gap is not a fixed historical residue that will
stop growing on its own; markets are entering this undiscovered-resolved
state on an ongoing basis.

---

## Q1 — the raw question — sampled, stratified

| Stratum | N (population) | n (sample) | Resolved fraction (determinate) | Wilson 95% CI |
|---|---|---|---|---|
| G (= Q2 population) | 317 | 317 (census) | 67.4% | [62.0%, 72.5%] |
| Z (zero trades) | 476 | 60 | 91.2% | [81.1%, 96.2%] |
| O-oldest tercile | 169,861 | 50 | 100% | [92.9%, 100%] |
| O-middle tercile | 169,862 | 50 | 100% | [92.9%, 100%] |
| O-newest tercile | 169,862 | 50 | 97.7% | [88.2%, 99.6%] |
| **O pooled** | 509,585 | 150 | 99.3% | [96.2%, 99.9%] |

**Q1 overall (stratified combination across G, Z, O, per the pre-registered
formula):** **p̂ = 99.28%**, 95% CI **[97.9%, 100%]**, N = 510,378.

**In absolute terms: the point estimate implies roughly 506,700 of the
510,378 dateless unresolved markets are already resolved on CLOB and
undiscovered** — this follows directly from the point estimate and is
reported for scale, not as a separately-estimated figure with its own
error bars (it inherits Q1's CI).

**Total CLOB calls made: 527** (317 + 60 + 150), exactly as pre-registered.
At 0.25s/call plus latency, the full run completed in a few minutes.

---

## Boundary check (§7 of the pre-registration, applied here)

- **Age concentration in O, reported as pre-committed:** two of three
  age terciles (`O-oldest`, `O-middle` — everything with a first trade
  before 2026-06-13) returned **100% resolved, zero exceptions, in 50/50
  samples each.** `O-newest` (first trade since 2026-06-13, i.e. within
  the last ~2 months) is lower but still overwhelming at 97.7%
  determinate (43/44), with a slightly elevated indeterminate rate (12%
  vs 0% in the older two terciles) — consistent with very recently-traded
  markets being more likely to still be genuinely open or not yet
  CLOB-indexed, not evidence against the overall finding.
- **This is not "old markets we can safely ignore."** The oldest tercile
  spans first-trades back to 2023-02-16; the newest starts 2026-06-13 —
  both ends of a 3.5-year range show the same pattern. Age does not
  explain the gap away.
- **Not dominated by never-real stub markets** — pre-registration §1
  already established 99.9% of the base population has real trades; this
  result confirms those traded markets are, overwhelmingly, real resolved
  markets sitting undiscovered, not synthetic or malformed rows.
- **The barrier is not "no identifier exists."** As pre-registered, 97%
  of `market_id` values are themselves condition_id-shaped and were used
  directly as the CLOB query identifier with a 5% (G), 5% (Z), and 0-12%
  (O terciles) indeterminate rate — CLOB happily answered the overwhelming
  majority of queries. **The barrier is that no script in the resolution
  cluster ever queries these markets this way** — not a data-availability
  problem, a coverage-of-code problem.

**Conclusion of the boundary check: the striking number is a property of
the world (a real, large population of resolved-but-unrecorded markets),
not an artifact of where or how this method looked.**

---

## Cross-check (§8 of the pre-registration)

First 15 of the 203 Q2-resolved markets (by `market_id` order), each
checked against our own `tape_end` (`MAX(trades.timestamp)`):

**15 of 15 corroborate.** Every sampled market's `tape_end` falls well
outside the pre-registered 30-day threshold — ranging from 85 to 555 days
before today (2026-08-20). **Zero discrepancies** — no case where CLOB
says resolved but our own trade tape shows recent activity that would
contradict it. This is strong, independent corroboration that CLOB's
signal is genuine: these markets stopped trading a long time ago,
consistent with having actually resolved, not a false-positive CLOB read.

---

## Materiality determination (§9 of the pre-registration, applied mechanically)

The pre-registered rule: Q2 census resolved count ≥16 (≥~5% of 317) →
**REAL-BOUNDED**, with the bound being the exact census count, not a
projection. **203 ≥ 16.** Indeterminate rate for the Q2 census is 16/317 =
5.05%, well under the pre-registered 30% inconclusive threshold, so the
census is usable and this rule applies cleanly, with no ambiguity in which
branch of the pre-registered rule fires.

---

## Does this change the classification? — Yes: REAL-UNBOUNDED → REAL-BOUNDED

**The Gamma resolution-discovery blind spot (item 1,
`2026-08-20-open-smells-register.md`) is reclassified from REAL-UNBOUNDED
to REAL-BOUNDED.**

**The bound, stated exactly, per the pre-registered materiality rule:**
Within the project's own canonical-relevance population (Geopolitics/
Elections, with trades — 317 markets, fully censused, not estimated),
**203 markets (64.0% of the full 317-market population, 67.4% of the 301
determinate) are confirmed already resolved on CLOB and completely
undiscovered by any of the four passes in `fast_resolution_check.py` or
`hydrate_stub_markets.py`.** This is an exact count from a full census,
not a projection — the bound is not "unknown," it is 203, with a
16-market residual (the indeterminate `http_404` cases) whose true status
is unresolved by this method but does not change the headline number
either direction beyond [203, 219].

**What "bounded" does not mean here: small.** REAL-BOUNDED describes
*known extent*, not *low severity*. This is a large, known, exactly-counted
gap — 203 out of 317 markets this project's own canonical backtest
population is defined against are sitting in this state. The
classification change reflects that the number is now known and
actionable (a specific list of 203 market_ids, sitting in the raw JSON
output), not that the problem is small.

**Q1's number is reported for context and the boundary check, per the
pre-registration's own rule that Q1 does not by itself change the
classification** — but it corroborates the same conclusion at the full
population scale: this is not a phenomenon isolated to the categories this
project prioritizes, it is close to universal across the entire
510,378-market dateless-unresolved population (p̂=99.3%).

---

## What this does not do

No fix implemented. No writer migrated. No repair to any of the 203 (or
506,700-projected) markets. No keyset pagination built. Stage 3 untouched.
This document produces a number with an interval, a full census list (in
the committed JSON), and the context to decide how urgently to act — the
decision and any implementation are separate, future work.

---

## Reproducibility

```
python3 scripts/discovery_gap_sizing.py
```
Deterministic given the DB snapshot and `random.seed(20260820)` (fixed in
the script, per the pre-registration) — population membership and
stratum/tercile boundaries are derived live from the DB at run time, so a
re-run against a materially different DB snapshot will select a different
sample from O and Z (not G, which is a full census and therefore stable
modulo population churn). The Q2 census (G) is the load-bearing number and
is exact, not sample-dependent, for whatever the population is at run
time.

---

*Generated 2026-08-20. Method: `2026-08-20-discovery-gap-sizing-prereg.md`
(`a9a0cf9`), committed and fixed before this run. Script:
`scripts/discovery_gap_sizing.py` (first-repo). Raw data:
`data/characterizations/discovery_gap_sizing_20260820T211955Z.json`
(first-repo, 317+60+150=527 CLOB query results, full detail per market).
Read-only: no writer modified, no schema touched, no data repaired.*
