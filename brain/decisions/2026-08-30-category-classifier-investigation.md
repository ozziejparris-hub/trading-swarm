# Category Classifier: What Constrains Throughput, and Is There Another Route?

**Date:** 2026-08-31 (filename carries the 08-30 investigation-series date, matching
the predecessor `2026-08-30-geo-backlog-and-category-reach.md`).
**Scope:** read-only. Nothing fixed, nothing resumed. Establishes why
`backfill_market_categories.py` runs at ~60 attempted / ~19 classified per day,
whether that is config or capability, how large the geo/elec job actually is, and
whether the sweep's resolved-market output can reach the thesis population by any
route other than that classifier.

**Tagging:** `[V]` = verified this session by reading the code / querying the DB /
reading the log directly. `[I]` = inferred. Per the standing instruction every
claim in the task prompt was treated as a hypothesis and checked against the
component it names.

---

## VERDICT

**It is a capability problem wearing a config problem's clothes, plus a genuine
iteration bug. Raising `--limit` does not route the sweep's output into the thesis
population.**

1. **The 60/day figure is 100% a config throttle** — `daily_maintenance.py` invokes
   the script with `["--limit", "50"]`; batch size 20 makes it overshoot to 60. The
   run takes **~85 seconds**. There is no API quota, no cost, no timeout, and no
   candidate-set exhaustion involved. Runtime headroom in the 3-4h maintenance
   window is effectively unlimited for this step. `[V]`

2. **But ~68% of what it attempts is correctly rejected as genuinely non-geo/elec.**
   Every SKIP in the log is `category=Unknown confidence=HIGH` — the LLM is
   *confidently* saying "not political," not declining uncertain cases and not
   failing. The skipped titles are keyword false positives: `war`→"Warsaw",
   "Warriors", "Warhawks"; `president`→"Presidents Cup" (golf); plus weather,
   crypto, esports. Raising the limit processes the backlog faster but most of the
   additional throughput is spent confirming non-political markets are
   non-political. `[V]`

3. **The classifier also has a `hydrate_stub_markets`-class no-progress pathology —
   a different variant.** It *does* have `ORDER BY market_id` and a monotonic
   `last_processed_offset`, so it does not retry the same rows forever the way
   `hydrate_stub_markets` does. Instead: its candidate set (`WHERE
   category='Unknown'`) is mutated *by the job itself* (every classification removes
   a row) while pagination is purely positional (`LIMIT 20 OFFSET n`). The
   OFFSET↔row mapping drifts every run. Observed consequence: consecutive daily runs
   re-SKIP identical `market_id`s despite non-overlapping offset windows, **and**
   ~19,000 keyword-matching Unknown markets have been stepped over entirely and will
   never be examined. `[V]`

4. **The keyword pre-filter structurally caps the sweep contribution at ~2.5% of the
   sweep population regardless of `--limit`.** Of 214,516 CLOB-resolved (`sweep`)
   Unknown markets, only **5,412** match the 37-term keyword filter at all. The
   other 209,104 are invisible to this mechanism forever. `[V]`

5. **The genuine geo/elec subset of the sweep backlog is small — ~1,000-3,000
   markets (0.5-1.4%)**, by two independent estimates that agree on order of
   magnitude. The practical job is that subset, not 214,000. At the confirmed real
   rate the classifier contributes sweep-resolved geo/elec markets to the population
   at **~0.4/day** (259 in ~640 days of running). `[V]/[I]`

6. **`trades.market_category` is not another route.** It agrees with
   `markets.category` on 672,845 / 672,845 rows (zero disagreements, whole DB) — it
   is a write-time mirror of the same column, staler, and 'Unknown' for 214,092 /
   214,516 sweep-Unknown markets. It carries no independent signal and cannot seed
   anything. `[V]`

7. **A real alternative route exists but is a one-off detached job, not a config
   change:** point an LLM pass at `resolution_evidence_source='clob' AND
   category='Unknown'` directly, with no keyword pre-filter and a stable cursor
   (not `OFFSET` over a mutating set). ~214k markets / batch-20 / ~85s-per-3-batches
   ≈ **~84 hours of Ollama compute**, runnable over a few days outside the daily
   window. The Gamma API's own event tags are a second, cleaner route. Both are
   described in Part 4; neither is built or planned here.

---

## PART 1 — Why 60 attempted?

### 1.1 What sets the number `[V]`

`scripts/daily_maintenance.py`, in `STEPS`:

```python
("Backfill market categories", SCRIPTS_DIR / "backfill_market_categories.py",
 ["--limit", "50"], True),
```

- The `50` is an explicit `--limit` argument. The 4th tuple field `True` marks the
  step **non-blocking** (a failure does not abort the maintenance run). No timeout
  override is passed (several neighbouring steps pass one — e.g. `backfill_transaction_hashes`
  gets `28800` (8h), `polygon_maker_taker` gets `1800` — this step gets none).
- `backfill_market_categories.py` defaults: `DEFAULT_BATCH_SIZE = 20`,
  `SLEEP_BETWEEN_BATCHES = 0.5`. `--limit` is checked at the **top of the batch
  loop** against `run_classified + run_skipped`, so with batch 20 the loop completes
  its third batch (60 processed) before `60 >= 50` stops it. **Every run lands on
  exactly 60, never 50.** This is the script's own arithmetic, confirmed by the log:
  one `"Reached --limit 50 for this run, stopping."` line per day, `processed`
  advancing by exactly 60 each run.
- Not an API rate limit: the only external call is to local Ollama
  (`http://localhost:11434`), no quota. Not a cost constraint: local inference. Not
  a timeout: none set. Not candidate-set size: the set is still ~27k rows (Part 3).
  **It is the `--limit 50` and nothing else.**

### 1.2 The actual ceiling `[V]/[I]`

Measured run duration from `logs/category_backfill.log`, most recent run:

```
2026-08-31 08:28:43  === category_backfill starting ===
2026-08-31 08:30:05  === category_backfill finished ===   (82 seconds, 3 batches)
```

- ~27s per 20-title Ollama batch on `qwen3-coder:30b-a3b-q4_K_M`. `[V]` (three
  batch-boundary timestamps 21s apart in the log, plus setup).
- The daily maintenance window is 3-4h on weekdays, dominated by
  `backfill_transaction_hashes` (~2-3h) and `update_geo_elo`. This step's 85s is
  noise. `[V]` (comments in `daily_maintenance.py` STEPS give the timing budgets).
- Raising `--limit` to e.g. 2000 would take ~2000/20 × 27s ≈ **45 minutes** of
  added Ollama wall-time. That is affordable in the window but it would contend with
  `update_geo_elo` for CPU/GPU and I/O against the same DB under WAL. `[I]` — the
  contention cost is not quantified here.
- Constraint if pushed hard: not runtime per se but **Ollama saturating local
  compute** while the geo-ELO recalculation runs, and **the DB-write contention**
  (`UPDATE markets` + `UPDATE trades` per classification, `trades` being the 1M+
  row table). `[I]`

### 1.3 No-progress pathology — present, different from `hydrate_stub_markets` `[V]`

`hydrate_stub_markets.py`'s candidate query (line 128):

```sql
SELECT DISTINCT m.market_id, m.title, m.api_id, m.category
FROM markets m
WHERE m.resolution_date IS NULL
  AND m.market_id NOT IN (SELECT ... discovery_source='external_seed' ...)
LIMIT ?
```

— no `ORDER BY`, no offset, no state file. Failed rows stay `resolution_date IS
NULL` and are re-returned first every run; rows past the `LIMIT` are never reached.

`backfill_market_categories.py`'s candidate query (`fetch_batch`, line 102):

```sql
SELECT market_id, title
FROM markets
WHERE category = 'Unknown' AND title IS NOT NULL AND (<37-keyword OR-list>)
ORDER BY market_id
LIMIT ? OFFSET ?
```

with `OFFSET = state["last_processed_offset"]`, persisted in
`data/category_backfill_state.json`, **monotonically increasing** (+60/run,
confirmed across every run 2026-08-12 → 2026-08-31: offset 18,664 → 19,844).

So it does **not** re-attempt the same offset forever. Its defect is subtler:

- **The candidate set shrinks under the cursor.** Each successful classification
  does `UPDATE markets SET category = 'Geopolitics'|'Elections'`, removing that row
  from the `WHERE category='Unknown'` result set. Rows after it shift to lower
  positions. Next run's `OFFSET n` (n larger by 60) now lands on a *different* row
  than positional arithmetic would suggest.
- **The candidate set also grows under the cursor** — the sweep (segments 3, 4 ran
  2026-08-24 / 2026-08-30) resolves markets that land in `category='Unknown'` and
  match keywords; those insert at their `market_id` sort position, some *below* the
  cursor, pushing the mapping the other way.

**Observed drift — re-skip:** the 2026-08-30 run processed offset window
[19,724, 19,784); the 2026-08-31 run processed [19,784, 19,844) — non-overlapping.
Yet both runs' SKIP lists **begin with the identical market_ids**:
`0xb3ce61d40761...` ("Luke Altmyer Davey O'Brien Award"),
`0xb3de3c8e...` (Valorant), `0xb3e62d22...` (Mönchengladbach),
`0xb3e76f1f...` (Warsaw temp May 12), … The set shifted enough between runs that a
later `OFFSET` re-landed on rows the previous run already examined. `[V]`

**Observed drift — step-over:** `market_id` is `TEXT`; 39,282 of the 39,307
keyword-matching markets have `0x…` hex ids, so `ORDER BY market_id` is
lexicographic over the hex range. The **maximum `market_id` that has been
classified** sits at position **~39,283 of 39,307** in that ordering — i.e. the
cursor's write-frontier has reached the *end* of the keyword set. Yet **26,967
keyword-matching Unknown markets remain**, almost all with `market_id` *below* that
frontier. `total_skipped` (rows actually examined by the LLM and declined) is only
**7,944**. So **~19,000 keyword-matching Unknown markets between the start and the
frontier were never sent to the LLM at all** — stepped over as the set collapsed
under the advancing offset. `[V]`

**Effective fresh-examination rate is below 60/day** because of the re-skip
overlap. From the 08-30/08-31 comparison the overlap is roughly the first 15-20
SKIP lines of a 60-row run, so effective new markets examined ≈ **30-45/day**, not
60. `[V] that overlap exists; [I] the precise fraction.`

**End state:** live keyword-Unknown count is 26,992 and falling ~19/day; offset is
19,844 and rising ~60/day; the gap (7,148) closes at ~72/day. In **~100 days**
`fetch_batch` returns empty, the script logs `"No more Unknown markets matching
keyword filter. Done."` every run thereafter, and **~19,000 stepped-over
keyword-Unknown markets (plus all ~209,000 non-keyword sweep-Unknown markets)
remain unclassified permanently** — unless new keyword-matching Unknown rows keep
entering fast enough to hold the count above the offset. `[V]/[I]`

---

## PART 2 — Why do 41 of 60 fail?

### 2.1 The classification mechanism `[V]`

Local LLM. `backfill_market_categories.py`:

- Endpoint `http://localhost:11434/api/generate`, model
  `qwen3-coder:30b-a3b-q4_K_M`, `temperature 0.1`, 120s timeout, `stream=false`.
- 20 titles per call, numbered, one prompt. The prompt defines Geopolitics /
  Elections / Unknown, and instructs: *"IMPORTANT: Be conservative. If unsure,
  classify as Unknown."* Response is a JSON array of
  `{id, category, confidence: HIGH|LOW}`.
- **Write rule (`apply_classifications`, line 184):** a row is written **only if
  `confidence == "HIGH"` AND `category in ("Geopolitics", "Elections")`.** Anything
  else — `Unknown`, or `LOW` confidence, or a malformed/parse-failed batch — is a
  SKIP, and the row stays `category='Unknown'`.
- On write: `UPDATE markets SET category = ?` **and** `UPDATE trades SET
  market_category = ?` for that `market_id`, in one transaction.

There is a keyword pre-filter *before* the LLM ever sees a title (the 37-term
`build_keyword_where()` OR-list: election, president, … war, russia, china, iran,
… trump, biden, … mayor, governor, … tariff, coup, protest, revolution).

### 2.2 Why the ~41/60 skips happen — sampled `[V]`

Every SKIP line in `logs/category_backfill.log` (checked the last ~600) is:

```
DEBUG SKIP market_id=… title='…' category=Unknown confidence=HIGH
```

**`category=Unknown confidence=HIGH` for 100% of them.** Not `LOW` confidence, not
API failures (`errors=1` lifetime, one bad batch in ~640 runs), not a conservative
threshold turning away borderline-political titles. The LLM is *confidently and
correctly* classifying them as non-political. Sampled skipped titles:

| title (skipped) | why the keyword filter caught it |
|---|---|
| `Niagara Purple Eagles vs. Howard Bison: O/U 145.5` | — (college basketball; likely `war`… no; caught by ?) |
| `Will the highest temperature in Warsaw be 23°C on May 26?` | `war` ⊂ "Warsaw" |
| `Spread: Warriors (-3.5)` | `war` ⊂ "Warriors" |
| `Counter-Strike: Lynn Vision vs Chinggis Warriors (BO3)` | `war` ⊂ "Warriors" |
| `Hawaii Rainbow Warriors vs. UC Irvine Anteaters` | `war` ⊂ "Warriors" |
| `Will Sam Burns score the most points at the Presidents Cup?` | `president` ⊂ "Presidents Cup" |
| `Will Timothée Chalamet be nominated for Best Actor at the 98…` | ? (entertainment; `nato`? no — likely another term) |
| `Will Liam Lawson win the 2025 China Grand Prix?` | `china` |

The dominant skip driver visible in the sample is **`war` matching
"Warsaw"/"Warriors"/"Warhawks"** (weather markets for Warsaw, and NBA/college teams
named "Warriors"), then `president`→"Presidents Cup", `china`→Grand Prix. These are
true negatives the LLM is right to reject.

### 2.3 THE PIVOTAL DISTINCTION — config or capability? `[V]`

**Most failures are genuine unclassifiability (correct rejection of keyword false
positives), not throughput limiting and not a conservative threshold.**

Therefore:

- Raising `--limit` **makes the backlog finish sooner** but a large fraction of the
  extra throughput is the LLM confirming that "Warriors vs. Pelicans O/U 225.5" is
  not geopolitics. It is not wasted in the sense of being wrong, but it does not
  advance the goal proportionally.
- Raising `--limit` **does not reach** the ~19,000 markets the offset drift has
  stepped over (Part 1.3) — those need a cursor that is stable under a mutating set,
  or a one-time state reset.
- Raising `--limit` **cannot touch** the 209,104 sweep-Unknown markets the keyword
  filter excludes (Part 3.1).

**The sweep's output needs a different route.** Config alone (a bigger `--limit`)
gets the current keyword-scoped, drift-limited mechanism to its natural ceiling
faster — and that ceiling is ~2,700 sweep markets, not 214,000 (Part 3).

---

## PART 3 — Is the job 214,000 markets, or much smaller?

### 3.1 The sweep-relevant candidate pool `[V]`

| population | count |
|---|---|
| `markets` total | 792,792 (CLAUDE.md's "220K+" is badly stale) |
| `category = 'Unknown'` | 778,986 (98.3%) |
| CLOB-resolved (`resolution_evidence_source='clob'` = the sweep) | 214,775 |
| …of which `category='Unknown'` | **214,516** |
| …of which classified `Geopolitics` / `Elections` | 122 / 137 = **259** |
| …of those 259, entering the canonical population today | **226** (predecessor doc said 225; +1 is one market gaining a `tape_end`, benign) |
| sweep-Unknown markets matching the 37-term keyword filter | **5,412 (2.5%)** |
| current keyword-Unknown candidate set (all resolution sources) | 26,992 |
| …of those, CLOB-resolved | 5,412 |
| …of those, not resolved at all (live/open markets) | 10,526 |

The classifier's keyword pre-filter can only ever *see* **5,412** of the 214,516
sweep-Unknown markets. The remaining **209,104** are permanently out of its reach
no matter the `--limit`.

### 3.2 What fraction of the sweep backlog is genuinely geo/elec? `[V]/[I]`

**Method A — random title sample.** 400 CLOB-resolved Unknown titles, pseudo-random
by `substr(market_id,-6)`, hand-classified:

| bucket | count | share |
|---|---|---|
| crypto "X Up or Down - HH:MM" / "above $N" | 178 | 44.5% |
| weather ("highest/lowest temperature in CITY") | 52 | 13.0% |
| sports / esports (O/U, spread, "A vs. B", "Set N winner", LoL/Dota/CS) | 110 | 27.5% |
| **plausibly Geopolitics/Elections** | **6** | **1.5%** |
| other (stocks, entertainment, Eurovision, RT scores) | 54 | 13.5% |

Of the 6 "plausible": 1 substantive (`US x Iran ceasefire by March 2?`), the rest
are low-signal prop markets the classifier tends to call Elections
(`Will Trump say "Sick person" this week?`, `Will NYC Mayor post 60-79 posts …`).

**Method B — tight SQL keyword counts over all 214,516 sweep-Unknown:**

| pattern | markets |
|---|---|
| broad political terms (`election`, `president`, `senate`, `parliament`, `ceasefire`, `sanction`, `putin`, `netanyahu`, `nato`, `tariff`, `impeach`, `prime minister`, `ballot`, `primary`, `caucus`, `coup`, `govern%`, ` war `) | 1,158 |
| `Will Trump say "…"` prop markets | 966 |
| `post N posts from …` / `post N times on Truth` prop markets | 845 |
| substantive election phrases (`election`, `win the most seats`, `next president of`, `mayoral`, `presidential`, `parliamentary`) | 484 |

Union of these (with overlap) ≈ **2,500-3,000** if the "say"/"post" prop markets
count as Elections (the classifier treats them so); **~600-1,200** if only
substantive geo/elec counts.

**Estimate:** the genuine Geopolitics/Elections subset of the 214,516 sweep-Unknown
markets is **~1,000-3,000 markets (0.5-1.4%)**. Confidence: **medium** — a single
400-title sample (binomial 95% CI on 1.5% ≈ ±1.2pp → roughly 600-5,800 markets),
cross-checked against full-population keyword counts that land in the same
range and order of magnitude. Both methods say **low thousands, not tens of
thousands, and not 214,000.**

### 3.3 Time-to-clear for the geo/elec subset alone `[V]/[I]`

- **Historical actual:** the classifier has moved **259** sweep-resolved markets
  into geo/elec over its entire operating life (~640 daily runs since the state
  file's earliest committed value). That is **~0.4 sweep-geo/elec markets per
  day.** At that rate, ~2,500 more ≈ **~17 years.** `[V] for the 259 and the run
  count; [I] for the projection.`
- **Why so slow despite ~19 classified/day:** ~98% of what the classifier
  classifies is *not* sweep-resolved — it is older `live_monitoring` /
  `background_backfill` "Will Trump say X" prop markets that also match keywords and
  also sit in the same `market_id` range. Of 11,967 geo/elec markets DB-wide, only
  259 are `resolution_evidence_source='clob'`; 11,706 have it `NULL`. `[V]`
- **If the mechanism were pointed only at the 5,412 keyword-matching sweep-Unknown
  markets, with drift fixed:** at 60/day that set clears in **~90 days**, yielding
  ~40-60% true geo/elec ≈ **~2,700 markets** into the population. That is the
  mechanism's realistic ceiling. `[I]`

---

## PART 4 — Is there another route?

### 4.1 `trades.market_category` — NOT a route `[V]`

- **Provenance:** written by `backfill_market_categories.py` (`UPDATE trades SET
  market_category = ?` in the same transaction as the `markets` update) and by the
  live monitor at trade-insert time, copying the then-current `markets.category`.
  It is a write-time denormalization of `markets.category`. No independent
  classifier, no independent source.
- **Populated for sweep markets?** For the 214,516 CLOB-resolved Unknown markets:
  `trades.market_category = 'Unknown'` for 214,092, `<no trades>` for 424. Zero are
  something else. It is 'Unknown' exactly where `markets.category` is 'Unknown'.
- **Agreement where both exist:** **672,845 markets, 672,845 agree, 0 disagree**
  (whole DB, grouping `trades` by `market_id`). It never diverges today.
- **Verdict:** it cannot seed `markets.category` — it *is* `markets.category`, one
  step staler, and blank for markets with no trades. Feasibility: none.

### 4.2 Cheaper / more reliable signals — described, not built `[I]`

1. **Polymarket Gamma API event tags.** Gamma returns per-event tags (`Politics`,
   `Geopolitics`, `Elections`, `Sports`, `Crypto`, …) authored by Polymarket. This
   is the authoritative upstream category. One call per event (events group many
   markets), batchable. This is the fix-shaped route: it replaces an LLM guess with
   the source of truth. Cost: API calls (rate-limited, but a one-off backfill of
   ~214k markets grouped into far fewer events is days, not years). **Not built,
   not planned here.**

2. **Deterministic title-template pre-classifier for the dominant non-geo classes.**
   ~85% of sweep-Unknown markets are four rigid templates:
   `"<ASSET> Up or Down - "`, `"Will the highest/lowest temperature in "`,
   `" vs. "` + (`O/U`|`Spread:`|`Moneyline`|`Both Teams to Score`|`end in a draw`),
   `"Set N Winner:"` / esports `"(BO3)"`/`"(BO5)"`. A ~20-line regex pass tags those
   as definitively non-geo/elec. It does not classify anything *into* the
   population, but it shrinks any subsequent LLM pass to the residual ~15% —
   ~6× cheaper. **Describe only.**

3. **`condition_id` / event-sibling propagation — mostly unavailable for this
   population.** In principle, markets sharing a `condition_id` (neg-risk event
   group) share a category, so one classified sibling could seed the rest. But
   `markets` has **no `neg_risk` / event / series column**, and `condition_id` is
   populated for only **1,019 of the 214,516** sweep-Unknown markets — the sweep
   resolved via CLOB token id without backfilling `condition_id`. This route is a
   dead end for the sweep population specifically until `condition_id` is
   backfilled. `[V]`

4. **Point the existing LLM at the right set.** Change the candidate query from
   `category='Unknown' AND <keyword filter> ORDER BY market_id LIMIT ? OFFSET ?`
   to `resolution_evidence_source='clob' AND category='Unknown'`, iterated by a
   **stable keyset cursor** (`WHERE market_id > :last ORDER BY market_id LIMIT N`),
   dropping the keyword pre-filter entirely. The LLM is the only tool that reliably
   separates `"US x Iran ceasefire by March 2?"` from
   `"Curaçao vs. Côte d'Ivoire: O/U 7.5"`, and it does that well (Part 2.2). Cost:
   214,516 / 20 per batch × ~27s ≈ **~80-85 hours of Ollama wall-time**, runnable
   as a detached one-off over several days, outside the daily maintenance window.
   Combined with (2) as a pre-filter it drops to ~12-15 hours. **Describe only —
   not built, not planned.**

### 4.3 Would changing the metric's predicate to accept `trades.market_category` be
sound? `[V]`

`monitoring/column_definitions.py` Section 6, `BACKTEST_WINDOW_BASE_WHERE` (line
469):

```python
BACKTEST_WINDOW_BASE_WHERE = (
    "m.resolved = 1"
    "\n  AND m.category IN ('Geopolitics', 'Elections')"
    "\n  AND (m.trade_gap_flag = 0 OR m.trade_gap_flag IS NULL)"
)
```

with an explicit comment (line 456): *"category IN (...) reads markets.category —
never trades.market_category (O-2/O-30: the trades-table column is a write-time
denormalization that can lag or diverge …)"* and a **structural self-test** (line
659-662) that asserts the generated SQL contains `m.category IN ('Geopolitics',
'Elections')` and does **not** contain `trades.market_category` or
`tr.market_category`. `BACKTEST_WINDOW_SQL_VERSION` must be bumped on any change.

**The argument for accepting `trades.market_category`:** none of substance. Since
the two columns agree on 100% of rows (§4.1), adding it as an alternative would be a
no-op for correctness — it would classify exactly zero additional markets, because
`trades.market_category` is 'Unknown' wherever `markets.category` is.

**The argument against:**
- It breaks the single-canonical-source invariant the file is built around, and
  trips a self-test that is deliberately there to stop exactly this edit.
- O-2/O-30 established `markets.category` as canonical *because* the `trades` column
  is a denormalization not enforced by any constraint — it agrees today only
  because the backfill writes both; a future writer that updates `markets` and not
  `trades` (or vice versa) would silently split the population definition.
- `trades.market_category` cannot represent a market with zero trades (424
  sweep-Unknown markets already have none).
- It would change `BACKTEST_WINDOW_SQL_VERSION` semantics and invalidate the
  comparability of every existing `backtest_population_snapshots` row.

**Net:** unsound *and* pointless. The blocker is not the predicate — it is that
`markets.category = 'Unknown'` for 214,516 sweep markets and nothing classifies
them at a useful rate. Changing the predicate classifies nothing. The canonical
population definition should not be touched for this.

---

## WHAT REMAINS UNCHECKED (named, not chased)

- The precise fraction of each 60-row daily run that is re-skip overlap vs. fresh
  examination (Part 1.3) — established that overlap exists from the 08-30/08-31 log
  comparison, not quantified across many run pairs.
- The exact size of the offset-drift step-over set — estimated ~19,000 from
  (26,967 remaining keyword-Unknown − 7,944 lifetime `total_skipped`); not
  reconciled row-by-row against the classified set's `market_id` distribution.
- Whether new keyword-matching Unknown markets enter fast enough (via ongoing live
  monitoring) to keep the live candidate count above `last_processed_offset` and
  postpone the permanent-"Done" end state past the ~100-day estimate.
- CPU/GPU and DB-write contention cost of a large `--limit` running concurrently
  with `update_geo_elo` in the maintenance window (Part 1.2) — flagged as the real
  constraint if the limit were raised, not measured.
- Gamma API tag coverage and rate limits for a ~214k-market (far fewer events)
  one-off backfill (Part 4.2 route 1) — not probed.

No fixes, no plan. This is the read.
