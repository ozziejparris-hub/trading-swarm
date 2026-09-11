# ELO-Tier-Conditioned Calibration + elo_snapshots Inventory

**Two parts, independent. Part 1 is a test, Part 2 is an inventory.
Read-only throughout. No selector, no strategy, no signal, no rating
built.** Nothing persisted; no write to any production table; `--persist`
not implemented; no canonical definition, harness, threshold, or ELO
script modified; the copy-trade decay ladder was not re-run; no service
restarted.

Script `scripts/elo_tier_causal_test.py` (first-repo, committed `22f435b`,
script_commit-at-run-time `e3ac29e`). Artifact
`data/characterizations/elo_tier_causal_test_20260911T202445Z.json`.
`seed=42`, `reps=1500`. `--selfcheck` passed. `run_tests.py`: 26 files, 26
passed (no new test file — same convention as
[[2026-09-11-skilled-presence-causal-vs-compositional]]: an analysis
script reusing already-tested harness functions, not a module change).

Tags: **[V]** verified this session, **[I]** reasoned judgment.

**No verdict on what to do next — that is Oscar's.**

---

## FRAMING — stated up front, as required

**`geo_elo` is condemned for SKILL-RANKING**
(`MASTER_HANDOVER_2026-08-15` Section 1: sign error, improper scoring
rule, 35.7% sell contamination, 52.3% double-counting, uncalibrated
parameters). **Nothing in this document reopens that.** Every use of
`geo_elo_active` / `geo_accuracy_pool` / `tier` below is strictly as a
**CONDITIONING VARIABLE on market mispricing** — the identical use as
skilled-trader presence in
[[2026-09-11-skilled-presence-causal-vs-compositional]] — **never as a
skill measure, never as a selector, never as a claim that any trader is
good.** "LEGENDARY-present" below means only "a trader currently carrying
that tier label holds a position in this market"; it says nothing about
whether that label means anything as a competence measure. A future
reader should not mistake this for a revival of ELO-as-skill.

---

## Headline

**All three ELO-tier conditioning variables produce a complete, negative
finding — and each one fails at an EARLIER stage than the five prior
conditioning variables the placebo has already killed.** None reached
the placebo test at all:

- **LEGENDARY** (n=9 traders): the matched-comparison direction
  *reverses* at 5 of 6 horizons — stopped at Part 2.
- **NEAR_LEGENDARY** (n=26): direction preserved at only 3 of 6 — not a
  majority — stopped at Part 2.
- **Pool C** (n=4,483): a +16.62pp base-rate gap between present and
  absent markets — far past the pre-registered 10pp confound threshold
  — stopped at **Part 1**, before matching was even attempted.

Per the SURPRISE-framing instruction: this is the *expected* direction
of outcome (the placebo has been killing conditioning variables, and
these results are even more decisively negative than that pattern would
predict), so it is reported plainly as a negative result, not treated as
a discovery requiring an alternative explanation.

Part 2 (elo_snapshots inventory): the table exists, is written daily,
covers 232,536 rows / 70 distinct dates / 6,149 traders, has real gaps
(the largest is 15 days, encompassing both outage dates named in the
task), and **is read by exactly two non-live, non-scheduled research
scripts** — not literally "nothing," but nothing in the automated
pipeline.

---

## Part 1 — ELO-tier-conditioned calibration

### Tiers that exist in `column_definitions.py` (`derive_tier()`), current counts [V]

| tier | definition | current n |
|---|---|---|
| **LEGENDARY** | `geo_elo_active >= 2175`, clean pool member (`LEGENDARY_GATE_WHERE`) | **9** |
| **NEAR_LEGENDARY** | `1800 <= geo_elo_active < 2175`, clean pool member | **26** |
| ELITE | `geo_elo_active >= 1400` (no pool-cleanliness requirement — `derive_tier`'s own design note) | 304 |
| QUALIFIED | `geo_elo_active >= 1000` (no pool-cleanliness requirement) | 6,066 |
| DEVELOPING | has a value, below QUALIFIED | not separately queried |
| UNRANKED | `geo_elo_active IS NULL` | not separately queried |
| **Pool C** (`geo_accuracy_pool=1`) | the broad tier, not itself a `derive_tier()` rung | **4,483** |

LEGENDARY was "9–10 traders as of 2026-09-10" per the task's own framing;
**today it is 9** — consistent, no material change. Pool C was ~4,469 on
09-10; today **4,483** — small, ordinary drift. Three conditioning
variables run: (a) LEGENDARY, (b) Pool C, (c) NEAR_LEGENDARY as the one
other clean, well-defined tier boundary — chosen because it is an actual
rung in the canonical tier ladder, not an invented threshold. ELITE and
QUALIFIED were *not* run as separate conditioning variables: per
`derive_tier`'s own design note they carry no pool-cleanliness
requirement, making them a different, noisier kind of variable than the
clean top two + the broad Pool C already tested — reported here as
existing, not run, rather than silently run past.

### (a) LEGENDARY — n=9 traders, 697 markets present [V]

**Part 1 — characterisation.** Base rate: present 33.0%, absent 28.8%,
gap **+4.15pp [+0.54, +7.77]** — real but well under the 10pp stop
threshold; proceeded to Part 2.

| observable | present (n=697) | absent (n=9,066) |
|---|---|---|
| n_trades (median/mean) | 89 / 544 | 7 / 40 |
| n_distinct_traders (median/mean) | 36 / 144 | 4 / 17 |
| volume $ (median/mean) | 17,377 / 262,324 | 324 / 13,873 |
| lifetime hours (median/mean) | 660 / 1,267 | 120 / 636 |
| category (Geo% / Elec%) | 58% / 42% | 35% / 65% |
| cluster solo% | 35% | 53% |

Same pattern of gross size/activity/category difference as the original
skilled-presence test — present markets are bigger, more active,
longer-lived, and skew Geopolitics.

**Part 1 → per-horizon raw presence (before matching), n:**

| horizon | n present | n absent |
|---|---|---|
| ~0.5h | 695 | 7,675 |
| ~3h | 692 | 7,416 |
| ~12h | 683 | 6,836 |
| ~3d | 632 | 5,145 |
| ~14d | 469 | 3,281 |
| ~45d | 245 | 1,592 |

**None of the six horizons is market-count-UNCOMPUTABLE** by the
`MIN_N_FOR_FIT=30` threshold — even the thinnest (45d, n=245 present) is
well above it. The power warning about n=9 traders does not translate
into thin market counts here; 9 traders can touch hundreds of markets.

**Part 2 — matched comparison** (`match_markets()`, within category,
caliper 1.0; 290/291 Elections matched, 360/406 Geopolitics matched, 650
matched pairs total):

| horizon | matched-present slope [CI] (n) | matched-absent slope [CI] (n) | direction preserved? |
|---|---|---|---|
| ~0.5h | 1.350 [1.064, 2.652] (648) | 1.387 [1.052, 3.466] (646) | **no** |
| ~3h | 1.147 [0.891, 1.697] (645) | **1.398** [1.094, 2.116] (643) | **no** |
| ~12h | 1.173 [0.930, 1.656] (636) | **1.308** [1.017, 1.983] (632) | **no** |
| ~3d | **1.216** [0.949, 1.650] (585) | 1.151 [0.907, 1.621] (575) | yes |
| ~14d | 1.068 [0.792, 1.504] (428) | **1.211** [0.866, 1.868] (423) | **no** |
| ~45d | 0.829 [0.474, 1.449] (223) | **1.121** [0.770, 2.126] (237) | **no** |

**Direction reverses at 5 of 6 horizons** — matched-absent slope exceeds
matched-present at every horizon except ~3d. **Part 2's stop condition
trips: the effect disappears/reverses under matching.** This is a
complete, negative finding for LEGENDARY — the raw (unmatched) base-rate
gap and any raw slope elevation the un-matched comparison might have
shown is a composition artifact of LEGENDARY-present markets being
bigger/more active/more Geopolitics-heavy, not a marker LEGENDARY
presence adds once that's controlled for. **Halted before Part 3 — the
placebo was never run for this arm.**

### (b) NEAR_LEGENDARY — n=26 traders, 921 markets present [V]

**Part 1.** Base rate: present 29.3%, absent 29.1%, gap **+0.19pp
[−2.90, +3.28]** — essentially zero, nowhere near the stop threshold.

| observable | present (n=921) | absent (n=8,842) |
|---|---|---|
| n_trades (median/mean) | 104 / 475 | 7 / 34 |
| n_distinct_traders (median/mean) | 43 / 134 | 4 / 15 |
| volume $ (median/mean) | 16,506 / 236,302 | 304 / 10,289 |
| lifetime hours (median/mean) | 750 / 1,437 | 113 / 602 |
| category (Geo% / Elec%) | **74%** / 26% | 33% / 67% |
| cluster solo% | 34% | 54% |

Even more Geopolitics-skewed than LEGENDARY (74% vs. 26%, against a
population that's ~34% Geopolitics overall).

**Part 2** (239/240 Elections matched, 545/681 Geopolitics matched, 784
matched pairs total):

| horizon | matched-present slope [CI] (n) | matched-absent slope [CI] (n) | direction preserved? |
|---|---|---|---|
| ~0.5h | 1.581 [1.322, 5.607] (779) | 1.520 [1.159, 3.783] (779) | yes |
| ~3h | 1.361 [1.084, 2.028] (779) | **1.425** [1.135, 2.080] (778) | **no** |
| ~12h | 1.237 [0.987, 1.711] (775) | **1.277** [1.040, 1.784] (772) | **no** |
| ~3d | 1.156 [0.912, 1.565] (718) | 1.156 [0.937, 1.577] (703) | no (tie to 3 d.p.) |
| ~14d | 1.237 [0.974, 1.696] (537) | 1.155 [0.856, 1.682] (500) | yes |
| ~45d | 1.194 [0.815, 2.033] (294) | 0.941 [0.654, 1.574] (265) | yes |

**Direction preserved at only 3 of 6 horizons (h0.5h, h14d, h45d) — not
a majority; h3d is an exact tie, counted as not-preserved.** **Part 2's
stop condition trips.** No fits are market-count-UNCOMPUTABLE (all n ≥
265). Complete, negative finding. **Halted before Part 3.**

### (c) Pool C — n=4,483 traders, 8,777 markets present [V]

| observable | present (n=8,777) | absent (n=986) |
|---|---|---|
| n_trades (median/mean) | 10 / 84 | 2 / 4.2 |
| n_distinct_traders (median/mean) | 6 / 29 | 1 / 2.3 |
| volume $ (median/mean) | 539 / 33,857 | 15 / 11,614 |
| lifetime hours (median/mean) | 174 / 734 | **0.054 / 206** |
| category (Geo% / Elec%) | 39% / 61% | 21% / 79% |

**Base rate: present 30.8%, absent 14.2%, gap +16.62pp [+14.24,
+19.00].** This clears the 10-pp stop threshold with a wide margin — a
CI-solid, unambiguous confound at the root. **Part 1's stop condition
trips before Part 2 is attempted.**

The absent-of-Pool-C median lifetime is **~3.25 minutes** (0.054 hours)
— these are not "smaller but comparable" markets, they are markets that
essentially never traded at all beyond their opening print. Pool C's
gate requires ≥10 resolved geo trades and a non-NULL directionality
score — by construction, "no Pool C member ever traded here" selects
almost entirely for markets nobody minimally-qualified ever engaged
with. A calibration-slope comparison between "traded by someone
qualified" and "essentially untraded" is not interpretable as a
mispricing-marker question at all; it is closer to "does a market having
had any real trading activity correlate with its resolution rate,"
which is a different, uninteresting question. **Reported and halted per
the stop condition — no matched comparison, no placebo, attempted for
Pool C.**

### Summary across all three arms

| conditioning variable | Part 1 stop? | Part 2 stop (direction)? | reached Part 3 (placebo)? |
|---|---|---|---|
| LEGENDARY (n=9) | no | **yes — reverses 5/6** | **no** |
| NEAR_LEGENDARY (n=26) | no | **yes — 3/6, not majority** | **no** |
| Pool C (n=4,483) | **yes — +16.62pp base-rate gap** | n/a | **no** |

**None of the three ELO-tier conditioning variables reached the placebo
stage.** This is a stronger negative result than the skilled-presence
test, which survived Part 1 and Part 2 before the placebo killed it at
Part 3. Per the task's pre-stated expectation ("the placebo has killed
five conditioning variables in a row... if it kills these too, that is
the result"): these three didn't even make it that far — the calibration
slope elevation associated with tier presence does not survive
controlling for the same size/activity/category confounds that killed
skilled-presence, for any of the three tiers tested. No Part 4
(edge-units-vs-cost-floor) table was produced for any arm — none
qualified.

---

## Part 2 — `elo_snapshots` inventory

### Schema, size, and date coverage [V]

Columns: `snapshot_date, address, geo_elo, geo_elo_active,
comprehensive_elo, geo_accuracy_pool, research_excluded, bot_type,
geo_resolved_trades_count, geo_directionality_score, tier, archetype`
(PK: `snapshot_date, address`).

| | value |
|---|---|
| row count | **232,536** |
| distinct dates | **70** |
| date range | **2026-06-11 → 2026-09-11** (93 calendar days) |
| coverage continuous? | **NO — 7 gaps** |

Gaps found (calendar-day jumps > 1):

| after | before | gap (days) |
|---|---|---|
| 2026-06-18 | 2026-06-23 | 5 |
| 2026-06-27 | 2026-06-29 | 2 |
| 2026-06-30 | 2026-07-02 | 2 |
| 2026-07-11 | 2026-07-13 | 2 |
| **2026-07-24** | **2026-08-08** | **15** |
| 2026-08-10 | 2026-08-12 | 2 |
| 2026-08-21 | 2026-08-23 | 2 |

**The 15-day gap (2026-07-24 → 2026-08-08) encompasses both outage dates
named in the task (07-26, 08-02) and considerably more** — this is not
two isolated missed days, it is a three-week stretch with only the
endpoints recorded. 93 calendar days minus 70 recorded dates = 23
missing days total, of which 15 fall in this one gap.

### Traders and series length [V]

| | value |
|---|---|
| distinct traders ever snapshotted | **6,149** |
| snapshot-count per trader: median / mean | 46 / 37.8 |
| p25 / p75 | 8 / 63 |
| max possible | 70 |

| usability threshold | n traders meeting it |
|---|---|
| ≥ 7 snapshots | 5,380 |
| ≥ 14 snapshots | 4,006 |
| ≥ 30 snapshots | **3,547** |
| ≥ 60 snapshots | 2,370 |

A little over half (3,547/6,149, 58%) have at least 30 recorded points —
a reasonable bar for "long enough to be usable" for any future
longitudinal work, though what "usable" means depends on that work's own
question and was not assessed further here (task scope: inventory, not
analysis).

### Column population — NULL vs. default vs. computed [V]

| column | % NULL | note |
|---|---|---|
| geo_elo, geo_elo_active, geo_accuracy_pool, research_excluded, geo_resolved_trades_count, geo_directionality_score, tier | **0.0%** | always populated |
| **comprehensive_elo** | 0.0% | **0.32% (747/232,536) sit at exactly the schema default 1500.0** — the rest (99.68%) are not at the bare default, i.e. not obviously uncomputed by this test; "has a value" ≠ "was computed" only distinguishes ~747 rows here, not the bulk of the table |
| **bot_type** | **100.0%** | **every row NULL — explained, not a gap**: `snapshot_elo_scores.py` only snapshots Pool C traders (`WHERE geo_accuracy_pool = 1`), and `POOL_C_GATE_WHERE` itself requires `bot_type IS NULL` for pool membership — a bot-flagged trader can never be in Pool C, so can never appear in `elo_snapshots`, so the column is NULL by construction, not by writer omission. Live `traders` table does have non-NULL `bot_type` values (409 ARB_BOT, 259 LP_ARTIFACT, 17 THIN_SAMPLE_ARTIFACT) — confirming the column itself works, it's just never reached for this table's population. |
| archetype | **98.9%** | sparse, optional (2,563/232,536 populated) |

**The table's entire population is, by construction, the historical
record of Pool C membership over time** — every row is a Pool C trader
on that date (confirmed via `snapshot_elo_scores.py:100-101`:
`SELECT ... FROM traders WHERE geo_accuracy_pool = 1`).

### Who reads this table [V]

Searched both repos (all `.py` files, excluding this script itself) for
`elo_snapshots`. **Not literally nothing, but nothing in the live
pipeline:**

| file | genuinely reads it? |
|---|---|
| `scripts/verify_dilution_guard.py` | **yes** — real `SELECT address FROM elo_snapshots WHERE geo_elo >= {tier_threshold}`, and validates a position/tier reconstruction function against "the 30 recorded elo_snapshots dates" |
| `scripts/validate_pit_geo_elo.py` | **yes** — multiple real `SELECT ... FROM elo_snapshots` queries (dated `2026-07-21`, references "07-20/07-21 elo_snapshots") |
| `scripts/snapshot_backtest_population.py` | no — comment only, cites it as a design-pattern analogy ("mirrors elo_snapshots / order_book_snapshots") |
| `scripts/migrate_add_category_source.py` | no — comment listing table names |
| `scripts/build_event_cluster_labels.py` | no — comment only, same design-pattern citation |
| `scripts/snapshot_elo_scores.py` | writer, not reader (the daily-maintenance step that populates the table) |
| trading-swarm repo | **zero references found** |

Both genuine readers (`verify_dilution_guard.py`, dated Aug 14;
`validate_pit_geo_elo.py`, dated Jul 21) are **not** referenced in
`daily_maintenance.py` and were not found in crontab — they are one-off
research/validation scripts from prior sessions, not part of any
scheduled or live pipeline. So: the task's framing ("nothing in either
repo appears to read it") is correct in spirit — nothing *live* reads
it — but not literally true; two dormant investigative scripts do,
genuinely, via real queries. Reported as found, not rounded down to
zero.

### Tier column values vs. current `derive_tier()` [V]

| tier value in table | row count |
|---|---|
| QUALIFIED | 152,215 |
| DEVELOPING | 44,316 |
| ELITE | 33,064 |
| NEAR_LEGENDARY | 2,070 |
| LEGENDARY | 871 |

**Every observed tier value matches the current `derive_tier()` scheme
exactly** (`{LEGENDARY, NEAR_LEGENDARY, ELITE, QUALIFIED, DEVELOPING,
UNRANKED}` — five of six appear; UNRANKED never appears, consistent with
the table only ever containing Pool C members, who by definition have a
non-NULL `geo_elo_active`). **No retired or orphaned tier strings
found** — the column has not drifted from the live definition it's
computed with (`snapshot_elo_scores.py` calls `cd.derive_tier(...)`
directly at write time, so this is close to guaranteed by construction,
but confirmed empirically rather than assumed).

---

## What was NOT determined

- **Whether ELITE or QUALIFIED, as separate conditioning variables,
  would behave differently from the three tested.** Explicitly not run
  — `derive_tier`'s own design note says these two do not require
  pool-cleanliness, making them a different kind of variable; running
  them was judged out of the task's stated scope ("a mid tier if one is
  defined... report what tiers exist rather than inventing boundaries"
  was read as calling for one additional rung, not an exhaustive sweep
  of all six).
- **Whether a market-matching caliper looser or tighter than 1.0 would
  change LEGENDARY's or NEAR_LEGENDARY's Part 2 direction.** Not swept —
  the caliper is inherited unchanged from `skilled_presence_causal_test.py`
  per instructions not to rebuild `match_markets()`.
- **Why LEGENDARY's matched comparison specifically reverses (rather
  than just going to zero) at 5/6 horizons.** Not chased — the finding
  is reported as "direction does not survive matching," not interpreted
  further; a reversal and a null are both consistent with "no
  skill-specific marker survives," and distinguishing them was not asked
  for.
- **`elo_snapshots`' usefulness for any specific future longitudinal
  question.** Explicitly out of scope — Part 2 is an inventory of what
  exists, not an analysis of rating dynamics, trend, or stability.
- **Whether the 23 missing calendar days (7 gaps) correlate with
  anything beyond the two named outage dates.** Not investigated beyond
  listing the gaps themselves.
- **Whether the 747 `comprehensive_elo` rows sitting at exactly 1500.0
  are genuinely uncomputed defaults or a coincidental true value.**
  Reported as the plausible-default count, not confirmed against the
  writer's own logic for when it would leave the default un-overwritten.

---

## Reproducibility

- **Script:** `scripts/elo_tier_causal_test.py` (first-repo, committed
  `22f435b`; `script_commit` recorded in the artifact is `e3ac29e`, HEAD
  at run time — same convention as the two prior decision docs). Read-only;
  `--persist` not implemented. Imports and reuses, unchanged:
  `own_market_calibration.py`'s population/tape/snapshot machinery, and
  `skilled_presence_causal_test.py`'s `base_market_features`,
  `part1_characterise`, `match_markets`, `part2_matched`,
  `part2_survives`, `part3_placebo`, `part3_survives`, `CALIPER`,
  `BASE_RATE_STOP_PP` — none re-derived. New code: the three tier-trader-
  set queries (current `traders` table state, via
  `cd.LEGENDARY_GATE_WHERE` / `geo_accuracy_pool=1` / the
  NEAR_LEGENDARY band), the market-presence join, the UNCOMPUTABLE
  annotation pass, and the `elo_snapshots` inventory (Part 2, fully
  independent of Part 1). `--selfcheck`: `describe()` on a known series;
  the UNCOMPUTABLE-flagging logic on synthetic thin/thick arms; tier
  threshold ordering (`GEO_ELO_NEAR_LEGENDARY < GEO_ELO_LEGENDARY`).
- **Artifact:**
  `data/characterizations/elo_tier_causal_test_20260911T202445Z.json` —
  full Part 1 characterisation, per-horizon raw presence with
  UNCOMPUTABLE flags, match results and balance, all matched-arm curves
  and slopes with CIs, Part 2/3 gate detail (where reached), for all
  three tiers; the full `elo_snapshots` inventory (schema, dates, gaps,
  per-trader series-length distribution, column NULL/default stats,
  tier-value counts, the reader search results for both repos).
- **Detached run:** launched via `setsid ... nohup ... < /dev/null &` +
  `disown`, watched via a bounded `Monitor` on the log for
  `[done]`/`Traceback`/`STOP]`, confirmed complete by reading the
  resulting JSON artifact directly (matches stdout, `oos_result_unchanged:
  true`). A quick low-`reps` smoke test was run first and its point
  estimates (not CI-dependent) matched the final `reps=1500` run exactly
  — the stop-condition outcomes for all three arms were established
  before the full bootstrap run even started, and confirmed unchanged by
  it. Runtime: ~1 minute (Part 2 inventory) + ~1 minute (LEGENDARY +
  NEAR_LEGENDARY Part 2 bootstraps; Pool C stopped at Part 1 with no
  bootstrap needed) — much faster than the skilled-presence run, since
  none of the three arms reached the expensive Part 3 placebo
  construction.
- **Stop conditions — three tripped, as designed:** LEGENDARY and
  NEAR_LEGENDARY both tripped Part 2's direction-collapse condition;
  Pool C tripped Part 1's base-rate condition. `metric_v2f_oos_result`
  sha256 `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e`
  unchanged before and after (verified in both the run log and the
  artifact).
- **Tests:** `run_tests.py` (not bare pytest) — **26 files, 26 passed, 0
  failed** (339,919 assertions). No new test file — same convention as
  the prior two decision docs.
- **Copy-trade decay ladder:** not touched, not re-run, per scope.
