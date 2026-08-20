# 2026-08-20 — sizing the Gamma resolution-discovery blind spot: pre-registration

**Committed before any CLOB sampling call is made.** Per the standing
instruction on reproducible decision numbers: none of what follows may be
adjusted after seeing sampling output. Source: `2026-08-20-open-smells-register.md`
(`f4418cb`) item 1, classified REAL-UNBOUNDED. This document fixes the
method; the result (with the committed script and figures) is a separate
document, `2026-08-20-discovery-gap-sizing-result.md`, filed after this one.

Every population figure below is **[V]**, queried live against
`data/polymarket_tracker.db` today (2026-08-20), not carried over from the
register without re-checking.

---

## 0. The two questions, kept separate

- **Q1 (RAW):** what fraction of the 511,829-figure population (re-verified
  below as 510,378 — see §1 note) of dateless unresolved markets are
  already resolved according to CLOB?
- **Q2 (RELEVANT):** what fraction of the subset this project actually
  depends on — Geopolitics/Elections category, with trades, within the
  canonical backtest population's own filter shape — is already resolved
  and undiscovered?

These are reported separately throughout. Q2 is the number that carries
the decision; Q1 characterizes how the world looks, per the register's own
boundary-check obligation.

---

## 1. Populations — re-verified today, not assumed

The register's headline figure was "510,380 unresolved markets with both
`resolution_date` and `end_date` NULL." Re-querying today with the exact
same predicate returns **510,378** — a drift of 2 (population churn since
the register was written a few hours ago; not a discrepancy in method).
**This document uses 510,378 as the base population, re-verified live.**

```sql
-- base population (dateless unresolved)
SELECT COUNT(*) FROM markets
WHERE (resolved = 0 OR resolved IS NULL)
  AND resolution_date IS NULL AND end_date IS NULL;
-- 510,378
```

**New facts established during this pre-registration's scoping work, not
in the register, and load-bearing for the stratification below:**

- **509,902 of 510,378 (99.9%) have at least one trade.** Only 476 have
  zero trades. This corrects an implicit assumption in the register's own
  boundary-check framing (that this population might be dominated by
  "stub markets that were never real") — it is not; it is overwhelmingly a
  population of markets with real trading activity that simply never got a
  resolution/end date recorded.
- **Only 1,273 of 510,378 (0.25%) have a non-null `condition_id`.** But
  **495,008 (97.0%) have a `market_id` that is itself condition_id-shaped**
  (66-char, `0x`-prefixed hex — confirmed by direct sampling: for every
  row checked, `market_id` and `condition_id` were byte-identical when
  both were present). A further 15,369 (3.0%) have a 64-char `market_id`
  (the same hex string missing its `0x` prefix). One row has an empty
  `market_id`. This is the **query identifier**, resolved in §2.
- **Category breakdown:** 509,911 "Unknown", 248 Elections, 135
  Geopolitics, and small remainders (Crypto 23, Sports 22, Economics 21,
  etc.).
- **30 rows carry `trade_gap_flag=1`, `flag_reason='synthetic_quarantine_2026-07-19'`**
  (the O-37 synthetic-market quarantine, already known and excluded from
  the canonical backtest population by design — `monitoring/column_definitions.py`'s
  `BACKTEST_WINDOW_BASE_WHERE`).

---

## 2. Definitions, fixed before sampling

### 2.1 Query identifier

```
clob_id = condition_id if condition_id else (
    '0x' + market_id if len(market_id) == 64 and not market_id.startswith('0x')
    else market_id
)
```
A market with `market_id == ''` (the one zero-length row) or `clob_id`
otherwise unusable is recorded as **INDETERMINATE — no queryable
identifier**, not attempted against CLOB.

### 2.2 CLOB endpoint

`GET https://clob.polymarket.com/markets/{clob_id}` — the same endpoint
and identifier-fallback convention (`condition_id or market_id`) already
live in `scripts/fast_resolution_check.py::run_stale_clob_pass`, and the
design's own A1 Rank-1 evidence source (`token.winner`).

### 2.3 Response classification — three categories, fixed

- **RESOLVED:** HTTP 200, response JSON has `closed == true`, AND at least
  one entry in the `tokens` list has `winner == true`.
- **OPEN:** HTTP 200, response JSON has `closed == false` — matches the
  live codebase's own definition of "not yet resolved"
  (`run_stale_clob_pass`: `if not data.get('closed'): continue`).
  Token `winner` values are not consulted for this category.
- **INDETERMINATE (third category — never folded into RESOLVED or OPEN):**
  - No queryable identifier (§2.1), OR
  - HTTP status != 200 after retry policy (§2.4) — includes 404 (not
    found on CLOB), 422, 5xx, OR
  - HTTP 200 but the `closed` field is missing/null, OR
  - HTTP 200, `closed == true`, but **no** token shows `winner == true`
    (an ambiguous "closed with no declared winner" state — real per the
    canonical design's A3 no-winner case, but not treated as evidence of
    resolution *discovery* for this sizing task, since no winning_outcome
    could be extracted from it the way a genuine discovery would need).

### 2.4 Retry policy

One retry after a 2-second pause, **only** for a connection error or
timeout. HTTP 404/422/5xx are **not** retried — they are recorded as
INDETERMINATE on the first response.

### 2.5 Rate limiting

0.25s sleep between calls (matching the existing codebase's CLOB-pass
convention of 0.2s, rounded up for headroom).

---

## 3. Populations subject to Q2 (canonical-relevance filter)

Grounded in the project's own canonical backtest population definition
(`monitoring/column_definitions.py::BACKTEST_WINDOW_BASE_WHERE`:
`category IN ('Geopolitics','Elections') AND (trade_gap_flag=0 OR NULL)`),
adapted to the *unresolved* side (the backtest filter requires
`resolved=1`; Q2 asks about markets that would enter that population if
resolution were properly recorded):

```sql
SELECT COUNT(*) FROM markets m
JOIN (SELECT DISTINCT market_id FROM trades) t ON t.market_id = m.market_id
WHERE (m.resolved = 0 OR m.resolved IS NULL)
  AND m.resolution_date IS NULL AND m.end_date IS NULL
  AND m.category IN ('Elections','Geopolitics')
  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL);
-- 317  (Elections 202, Geopolitics 115)
```

**This is small enough to census in full — 317 CLOB calls.** Q2 is
therefore not a sampling exercise; every market in this population is
queried. There is no sampling error in the Q2 figure — the only
uncertainty is the INDETERMINATE rate, reported separately (§6), not
folded into a confidence interval.

---

## 4. Stratification for Q1

Three disjoint strata, partitioning the full 510,378-row base population:

| Stratum | Definition | N | Sampling |
|---|---|---|---|
| **G** (= the Q2 population) | Geo/Elections, has trades, gap-flag clean | 317 | **Full census** (n=317) |
| **Z** | Zero trades, any category | 476 | Random sample, n=60 |
| **O** | Everything else (has trades, not in G) | 509,585 | Stratified random sample by age tercile, n=150 (50/tercile) |

`G ∩ Z = ∅` by construction (G requires trades, Z requires none). `O = 510,378 − G − Z`,
confirmed by direct query to equal exactly 509,585 (materialized as a temp
table, `JOIN trades` restricted to the same base-population predicate,
excluding G's own filter).

**Stratum O's age sub-strata**, using `tape_start = MIN(trades.timestamp)`
per market as the age proxy (the same convention `tape_end` already uses
in this codebase, mirrored for the start of a market's trading window),
computed once, live, over the full O population (no CLOB calls):

- O-terciles computed by literal thirds of O's `tape_start`-sorted list.
- **Tercile boundaries [V]:** `tape_start < 2026-04-14`
  (oldest third) | `2026-04-14 ≤ tape_start < 2026-06-13` (middle third) |
  `tape_start ≥ 2026-06-13` (newest third).
- **This is itself informative and reported regardless of the CLOB
  result:** O's `tape_start` range spans 2023-02-16 to 2026-08-20 (today),
  but two-thirds of the population's first trade falls within the last
  ~4.5 months (since 2026-04-14). The dateless population is heavily
  concentrated in recent ingestion, not evenly spread across the
  project's full history.
- 50 markets sampled per tercile, `random.sample` without replacement.

---

## 5. Random selection — reproducible, seeded

- **RNG:** Python's `random` module, `random.seed(20260820)` — today's
  date as an integer, fixed before any sampling call in the committed
  script.
- **Enumeration order before sampling:** each stratum/sub-stratum's
  market_id list is materialized via `ORDER BY market_id ASC` (a stable,
  content-derived order, not insertion order) before `random.sample` is
  applied — so the selection is reproducible from the DB snapshot alone,
  independent of any incidental table-scan order.
- **Sample sizes, fixed:** G = 317 (full census), Z = 60, O = 150 (50 ×
  3 terciles). **Total CLOB calls: 527.** At 0.25s/call plus network
  latency, expected wall time ≈ 4–8 minutes — considerate of CLOB rate
  limits, consistent with the existing codebase's own per-call pacing.

---

## 6. Estimation method, fixed

**Per-stratum proportion:** `p_hat = resolved / determinate`, where
`determinate = n − indeterminate` for that stratum (INDETERMINATE
excluded from the denominator, its rate reported as its own statistic:
`indeterminate / n`).

**Per-stratum 95% CI:** Wilson score interval (chosen over the normal/Wald
approximation for better small-`n`/extreme-`p` behavior):
```
z = 1.96
center = (p_hat + z²/(2n)) / (1 + z²/n)
halfwidth = z·√(p_hat(1−p_hat)/n + z²/(4n²)) / (1 + z²/n)
```
using `n = determinate` for that stratum.

**Overall Q1 estimate** (stratified combination across G, Z, O):
```
p_hat_overall = Σ_h (N_h · p_hat_h) / Σ_h N_h
Var(p_hat_overall) = Σ_h [ (N_h/N_total)² · (1 − n_h/N_h) · p_hat_h(1−p_hat_h) / (n_h − 1) ]
95% CI = p_hat_overall ± 1.96·√Var
```
using `N_h` = full stratum population, `n_h` = determinate sample size in
that stratum. For G (full census), the finite-population-correction term
`(1 − n_G/N_G) = 0`, so G contributes zero sampling variance to the
overall estimate — correct, since a census has no sampling error.

**Q2 (census) reporting:** point estimate = `resolved_G / determinate_G`
as an exact fraction of the census, with **no statistical CI** (there is
no sampling error in a full census) — instead, a best-case/worst-case
bound is reported: best case treats every INDETERMINATE result as
"presumed open" (lower bound on the resolved count), worst case treats
every INDETERMINATE result as "presumed resolved" (upper bound). Both
bounds are reported alongside the determinate-only point estimate, not in
place of it.

---

## 7. Boundary check — applied to this method itself, before results exist

Pre-registering what would make a striking result a property of *where we
looked* rather than *the world*:

- If stratum O's result is dominated by one age tercile or one
  `data_source` value, the Q1 headline number characterizes that
  ingestion era specifically, not "dateless markets" as a timeless
  category — this will be reported per-tercile, not just pooled, for
  exactly this reason.
- If Q2's 317-market census turns up markets concentrated in one
  `data_source` (e.g., all from `historical_backfill` rather than
  `live_monitoring`), that would suggest the gap is an artifact of one
  ingestion batch rather than an ongoing structural leak — checked and
  reported in the result document, not assumed either way here.
- The register's own framing ("dateless" = "off the Gamma/CLOB safety-net
  radar") is itself downstream of §1's finding that 97%+ of this
  population *is* CLOB-queryable via `market_id`-as-`condition_id` — the
  actual barrier these markets face is not "no identifier exists" but "no
  script currently uses this identifier this way." That distinction is
  material to interpreting the result and is stated here before the
  result is known, not fitted to it afterward.

---

## 8. Cross-check method, fixed

For every market classified RESOLVED in the Q2 census (bounded — if this
exceeds 15, the first 15 by `market_id` order are cross-checked, and the
total count needing cross-check is reported): query
`SELECT MAX(timestamp) FROM trades WHERE market_id = ?` (the project's own
`tape_end` definition) and compare against today. **Threshold, fixed:**
`tape_end` more than 30 days before 2026-08-20 counts as corroborating
evidence of genuine resolution (trading stopped well before the query, as
expected for a resolved market). `tape_end` within 30 days is reported as
a **discrepancy**, not silently resolved either way — CLOB says resolved,
our own tape shows recent activity, and both facts are reported together.

---

## 9. Materiality — fixed before results exist

This is what determines whether the classification changes, decided now:

- If the **Q2 census** finds the resolved-and-undiscovered count to be
  **small enough to enumerate and act on directly (interpreted as: the
  determinate-based point estimate implies fewer than ~15 markets, i.e.
  a resolved fraction under ~5% of the 317-market census)**, the
  classification moves to **REAL-BOUNDED**, with the bound being the
  exact census count (not an estimate — a full enumeration).
- If the Q2 census finds a **larger** resolved-and-undiscovered count
  (≥~5% of 317, i.e. ≥16 markets), the classification remains
  **REAL-BOUNDED** but with a materially larger, still-exact bound
  (a census, not a projection) — the distinction from REAL-UNBOUNDED is
  that the number is now *known*, regardless of its size.
- The classification **stays REAL-UNBOUNDED only if the census itself
  cannot produce a usable determinate rate** — fixed threshold: if
  INDETERMINATE exceeds 30% of the 317-market Q2 census, the result is
  reported as inconclusive for Q2 and the classification is not changed
  by this sizing exercise; a different method (not sampling-based) would
  be needed.
- **Q1's result does not by itself change the classification** — it
  characterizes the raw world, which the register already used to
  motivate this sizing task; it is reported for completeness and for the
  boundary check, per §7.

---

*Pre-registered 2026-08-20, before any CLOB sampling call. Committed to
`trading-swarm` prior to running `scripts/discovery_gap_sizing.py` (to be
committed alongside the result document). Source:
`2026-08-20-open-smells-register.md` (`f4418cb`).*
