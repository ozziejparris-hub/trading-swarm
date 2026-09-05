# Execution & Timing Signal Feasibility

**READ-ONLY.** Nothing built, nothing proposed. Builds on
`brain/decisions/2026-09-05-timing-execution-inventory.md` (first-repo
`c49648a` era) — its verified findings are taken as given, not re-derived.
Tags: **[V]** verified this session (query/code/doc cited), **[I]**
inferred or a judgment call. All queries run read-only against
`data/polymarket_tracker.db`; no writes anywhere in this session. Scratch
scripts used to produce these numbers live in this session's scratchpad,
not committed (not production code).

**Cohort throughout**: the Track 2 true cohort, 169 presplit-qualifying /
141 OOS-surviving traders, 3,795 OOS positions
(`data/characterizations/track2_ci_power_20260905T104945Z.json`).

---

## PART 1 — Can the trade tape supply a fair-price benchmark?

### 1a/1b. Trade density and coverage, by window

For each of the cohort's 3,795 positions, counted **other traders'**
trades (own-trader trades excluded) in the same market within ±1h/±6h/±24h
of entry [V, live computation, 231,440 trades loaded across the cohort's
564 distinct markets]:

| window | p10 | p25 | median | p75 | p90 | p99 | ≥1 | ≥3 | ≥5 | ≥10 | ==0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ±1h | 0 | 1 | 5 | 20 | 67.6 | 692.7 | 79.6% | 62.8% | 53.1% | 39.2% | **20.4%** |
| ±6h | 1 | 6 | 28 | 105 | 259 | 2,251 | 92.1% | 84.1% | 79.4% | 70.0% | 7.9% |
| ±24h | 4 | 24 | 101 | 305.5 | 750 | 3,075 | 97.1% | 91.8% | 88.9% | 83.5% | **2.9%** |

The tail matters exactly as flagged: even at ±24h, **2.9% of positions have
literally zero other-trader activity** in that market that day — no
benchmark is possible at any window width for those. At the tightest,
most microstructure-honest window (±1h), a full **fifth of positions
(20.4%) have zero comparison trades**, and the median position has only 5
— thin for a reliable price estimate even where nonzero.

### 1c. The trap — does benchmark availability degrade for high-volume traders?

Correlated each position's other-trader density against its own trader's
**total lifetime trade count** (whole-DB, not market-specific) [V]:

| window | corr(volume, density) | mean density: low-volume tercile | mid tercile | high tercile |
|---|---|---|---|---|
| ±1h | −0.023 | 38.4 | 44.0 | **34.2** |
| ±6h | −0.037 | 132.0 | 138.2 | **108.9** |
| ±24h | −0.039 | 286.3 | 322.2 | **249.6** |

The correlation coefficients are individually weak, but the pattern is
**consistent and real, not noise**: the high-volume tercile has the lowest
mean density of all three terciles, at every single window, not just a
monotonic decline. **Yes, it degrades for exactly the traders we care
about** — modestly, not dramatically, but the direction is unambiguous and
repeats across all three windows independently.

### 1d. What construction avoids VWAP's conflation, and its honest weakness

Della Vedova's objection to conventional VWAP is that a window spanning
across (or after) the position's entry lets the market's subsequent,
direction-relevant price convergence leak into what is supposed to be a
pure execution-quality benchmark — a good directional call starts to look
like good execution, because the "fair price" itself already reflects
information the position's own entry helped confirm.

**What the tape could support instead**: a trade-count-weighted mid-price
built **only from other traders' trades strictly before** the position's
entry timestamp, within a bounded pre-entry window. This avoids the
specific conflation Della Vedova names, since none of the comparison
trades postdate the position being benchmarked.

**Its honest weakness, stated plainly**: this is still an *endogenous*
benchmark — it reflects what *other participants in the same market*
already believed a few minutes or hours earlier, not an independent,
standing quoted price (an order-book mid/NBBO-equivalent). If those other
traders are themselves informed and moving on the same information the
target trader is acting on, the benchmark is already partly contaminated
by the same signal it's meant to net out, understating true execution
edge. It also inherits the density tail from §1a/1b: the ~3-20% of
positions with no nearby comparison trades get no benchmark at all under
any window choice. B4's order-book mid-price (§ inventory doc) would be
the cleaner, non-endogenous alternative in principle, but at 3.57%
coverage of Geo/Elec markets and zero overlap with this cohort, it is not
a usable substitute today.

---

## PART 2 — Can `timing_score` be rescued cheaply?

### 2a. The 0.5 fallback — trigger condition and ambiguity, verified directly

Confirmed in code (`analysis/trading_behavior_analysis.py:564-571`):
`optimal_timing_score = 0.5` is returned **only** when, after grouping a
trader's trades by market and requiring (i) ≥3 of the trader's own trades
in that market and (ii) ≥3 total distinct entrants ever in that market,
**zero markets survive both filters** — `entry_percentiles` ends up empty.

**Re-derived directly against the live code** (imported
`TradingBehaviorAnalyzer.calculate_timing_quality` unmodified, not
reimplemented) for a random sample of 300 of the 8,372 traders currently
stored at exactly `timing_score = 0.5` DB-wide:

- **297/300 (99.0%): confirmed FALLBACK** (`markets_analyzed == 0` on
  fresh recomputation) — 0.5 is overwhelmingly a genuine contamination
  marker.
- **1/300 (0.3%): GENUINE TIE** — one market qualified, and its
  `avg_entry_percentile` recomputed to exactly `50.0`. So 0.5 is not
  *uniquely* a contamination marker in the strict sense — a real tie can
  occur — but it is extremely rare.
- **2/300 (0.7%): an unanticipated third case — STALE/DRIFTED.** Fresh
  recomputation produced neither a fallback nor 0.5, but a *different*
  value entirely (0.256 and 0.462 in the two examples) — the stored value
  no longer matches what the same function would compute on the trader's
  current trade history at all. This is a separate data-staleness issue,
  not the fallback-ambiguity question the task posed, and it complicates
  any "just exclude the 0.5s" plan (§2c).

### 2b. Cohort contamination — smaller than the population-wide figure, and not where expected

Of the cohort's 169 traders [V, DB query]: **1** sits at exactly 0.5 (and
was independently confirmed FALLBACK by direct recomputation), **10** are
`NULL` (never computed/written at all), **158** carry a real computed
value. **The one fallback-contaminated trader has zero OOS positions** —
they are one of the 28 presplit-qualifying traders who don't survive the
OOS filter. **Zero of the cohort's 3,795 OOS positions belong to a
fallback-contaminated trader.** The only completeness gap touching actual
OOS positions is the 10 `NULL`-timing_score traders, whose positions total
**54/3,795 (1.4%)** — a data-completeness gap, not the 0.5-contamination
issue Stage 0b flagged.

**Contamination has grown substantially in the general population since
Stage 0b**, though: 8,372/39,465 (21.2%) of all traders with a non-null
`timing_score` now sit at exactly 0.5, up from Stage 0b's 1,541/21,249
(7.25%) on 2026-07-12 — nearly triple, consistent with the population
having grown substantially (more thin, single-event traders via
`resolution_sweep.py`) since then.

### 2c. Could Stage 0b's decomposition simply be re-run, excluding contaminated rows?

**What it would require**: (1) DB-wide fallback/genuine/stale
reclassification of all currently-0.5 traders — demonstrated tractable
above (~300 traders classified in this session via direct reuse of the
live function, no schema change, no `created_at`-equivalent needed); (2)
re-deriving `mean_edge` and the full regression population fresh against
today's data, using Stage 0b's own gate
(`is_flagged=1 AND research_excluded=0 AND resolved_trades_count>=10`).

**What blocks an exact "re-run"**: Stage 0b's own Appendix states its
"population and outcome extraction script + regression script +
intermediate CSV are in the session scratchpad, not committed." **The
original study's exact 21,218-trader population and per-trader `mean_edge`
values were never persisted anywhere.** Since the population gate is
dynamic (`research_excluded`/`is_flagged` sync daily, `resolved_trades_count`
grows), re-deriving it today would necessarily produce a *different*
(larger, drifted) population than the original 21,218 — this would be a
**new study using the same method**, not a resumption of the old one.
Nothing structurally blocks running such a new study — no missing column,
no missing script — but it is a fresh build-and-run task, out of scope for
this read-only assessment.

### 2d. Was exclusion ever considered in the Stage 0b doc?

**No.** [V, `grep -in "exclud"` against the full committed doc] The only
two uses of "exclud-" in the entire document are unrelated (the
`trade_gap_flag` market exclusion and the population gate's own wording).
The doc's §3.2 proposes exactly one remedy for the 7% neutral-default
contamination it found, quoted verbatim: **"re-deriving `timing_score`
from scratch on a repaired `created_at`-equivalent input."** Exclusion of
contaminated rows and re-running the same regression on the remainder was
never mentioned as an alternative.

---

## PART 3 — Entry-to-resolution lag

### 3a. Coverage

**100%** of the cohort's 3,795 positions have both `entry_timestamp` and a
non-null `resolution_date` [V] — no missing-data problem on its face. But
see §3d: **10.99% (417/3,795) have a *negative* lag** — `entry_timestamp`
falls *after* `resolution_date`, which is logically impossible for a
genuine pre-resolution entry and is a direct, position-level
manifestation of `resolution_date`'s known unreliability, not a rounding
artifact (tail out to −161 days).

### 3b. Distribution, resolution_date-anchored

| stat | value |
|---|---|
| p25 / median / p75 | 4.64 / 18.49 / 42.51 days |
| p90 / p99 | 60.0 / 138.5 days |
| mean | 26.0 days |
| fraction >8 days (Della Vedova "bot-like") | **67.9%** |
| fraction ≤3 days (Della Vedova "retail-like") | 21.3% |

### 3c. Polarity

The cohort's own distribution — under either anchor (§3d) — is **majority
long-lag**: 53.8–67.9% of positions enter more than 8 days before
resolution, only 21.3–25.2% enter within the retail-like ≤3-day window.
**This leans toward the Della Vedova "early entry = advantage" pattern,
not `detect_insider_activity.py`'s "late entry = suspicious" pattern.**
It is not clean, though — a real minority slice (11.6% under the sounder
tape-end anchor, §3d) sits at ≤1 day, exactly the bucket
`detect_insider_activity.py` scores as maximal insider suspicion. **The
cohort is not one polarity or the other — it is a mixture, tilted toward
early entry.**

### 3d. The resolution_date caveat — and whether tape_end is sounder

This project has **already investigated and answered** this exact
question, independently of this task: `brain/decisions/2026-07-18-MASTER-HANDOVER.md`
documents **O-36 (HIGH)**: up to ~29% of markets have `resolution_date` off
by >14 days from the true resolution event, root cause `fast_resolution_check.py`
stamping `datetime.now()` at check-time rather than the true event
timestamp. **"Workaround validated: anchor PIT splits on trade-tape-end...
instead of `resolution_date`."** The same doc notes an important asymmetry:
the bug is "one-directional / conservative" for `resolution_date` used as
a knowledge-lag margin — it is specifically PIT splits (this task's exact
use case) that need the tape-end anchor.

**Recomputing this cohort's lag with `tape_end` instead** [V]: 100%
coverage (0 missing, vs. resolution_date's logically-impossible 11%
negative-lag rate), **zero negative lags** (fully consistent — tape_end is
constructed from the same trade tape the entry itself belongs to). Median
lag drops to 8.92 days (vs. 18.49 under resolution_date); fraction >8 days
drops to 53.8% (vs. 67.9%); fraction ≤3 days rises to 25.2% (vs. 21.3%).
Median absolute difference between the two anchors across positions: 3.0
days; `resolution_date` reads later than `tape_end` in 53.0% of positions
— consistent with, though not overwhelming confirmation of, the documented
late-stamping direction.

**Yes, `resolution_date` compromises this measure as used naively, and
`tape_end` is the sounder anchor** — not a new finding, but a direct,
position-level confirmation of an already-validated project workaround,
applied here to this specific cohort and this specific question for the
first time.

---

## PART 4 — `is_taker` root cause (bounded)

### 4a. The stated hypothesis, tested directly against both writers' code

**Not confirmed in either script.** Both writers' branching logic
explicitly supports and would write `is_taker = 0` for a confirmed maker
match — this is not a NULL-vs-skip asymmetry as hypothesized:

`scripts/polygon_maker_taker.py:153-157` (`extract_maker_taker`):
```python
if is_taker_in_tx:
    return "taker"
if is_maker_in_tx:
    return "maker"
return None
```
and the write at lines 232-238: `"UPDATE trades SET is_taker = ? ..." , (1 if result == "taker" else 0, trade_id)` — a confirmed `"maker"` result writes `0` explicitly, not NULL. Only a genuine `None` (neither `taker_addr` nor `maker_addr` in any `OrderFilled` log topic matches the trader) is skipped, remaining NULL.

`scripts/polygon_event_scanner.py:381` (independent writer): `is_taker = 1 if role == "taker" else 0` — also an explicit binary write, no maker-side skip.

**The hypothesis as stated does not hold.** Both scripts are structurally
capable of writing 0, yet the database has never once recorded it.

### 4b. Is maker-side recoverable, or was it never captured?

**Could not be determined within the bounded scope of this task without
crossing into exactly the "deep Polygon RPC investigation" it warned
against** — stopping here, as instructed, and reporting where this got to:

- The code-level mechanism that would identify a maker (checking whether
  the trader's address appears as `topics[2]` in an `OrderFilled` log) is
  present and not obviously broken by inspection.
- One plausible, **unverified** [I] structural explanation: Polymarket's
  CLOB matches resting (maker) limit orders via *someone else's*
  transaction — the maker's own wallet may never itself send an on-chain
  transaction for a passive fill, only sign an off-chain order. Whether
  the `transaction_hash` this project stores per maker-side trade record
  (if one is even ingested at all) correctly points to the *shared*
  transaction that would let `extract_maker_taker` find them as
  `topics[2]` was not checked — doing so would mean inspecting real
  receipts and log topic values, out of scope here.
- A second, narrower observation: `polygon_event_scanner.py`'s own match
  logic (exact tx-hash or ±30s fuzzy timestamp against `trades` rows)
  determines whether it ever actually reaches its write statement at all;
  whether it contributes materially to the observed 621,350 labeled rows,
  or whether all of them in fact come from `polygon_maker_taker.py`, was
  not established — flagged as unresolved, not asserted either way.

**Bottom line: root cause not determined.** The specific hypothesis in the
task (NULL-vs-False code asymmetry) is ruled out by direct code reading.
Whether maker-side data was never captured upstream, or is captured but
mismatched at the join, remains open — it would require inspecting actual
transaction receipts, which this bounded diagnosis does not do.

---

## Plain summary — what's computable today, at what coverage

| signal | computable today? | coverage |
|---|---|---|
| Gómez-Cram randomized-direction (side/price/size/timestamp) | **Yes, fully** | ~100% of cohort trades |
| Entry-to-resolution lag (tape_end-anchored) | **Yes, fully** | 100% of cohort positions, 0 negative-lag artifacts |
| Entry-to-resolution lag (resolution_date-anchored) | Yes, but compromised | 100% nominal, 11.0% internally inconsistent |
| Trade-tape fair-price benchmark, ±24h window | Partial | 97.1% of positions have ≥1 comparison trade; 83.5% have ≥10 |
| Trade-tape fair-price benchmark, ±1h window | Partial, thin | 79.6% have ≥1; only 39.2% have ≥10; 20.4% have none |
| `timing_score` (cohort-specific) | Usably clean | 98.6% of cohort positions unaffected by fallback/NULL contamination |
| `timing_score` (general population) | Contaminated | 21.2% of all non-null values are the 0.5 fallback marker, growing |
| B4 order-book fair-price benchmark | No, at current coverage | 3.57% of Geo/Elec markets, disjoint from cohort |
| `is_taker` maker/liquidity-providing split | **No** | 0 maker-labeled rows exist anywhere in the database |

No design, no plan, no recommendation — per task scope.
