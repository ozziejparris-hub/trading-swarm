# Geo/Elections Relevance Classifier — Design

**Date:** 2026-08-31. **Scope:** DESIGN ONLY. Nothing built, nothing run, nothing
classified. ~19 live Gamma calls were made to characterise the slug input (Part 1.2);
counts stated inline.
**Predecessors:** `2026-08-31-geo-scoping-inventory.md` (3b367dd),
`2026-08-31-why-unknown-investigation.md` (ce35996),
`2026-08-31-ingest-category-defect.md` (6df24e6).
**Tagging:** `[V]` verified this session; `[I]` inferred. Every claim in the prompt
treated as a hypothesis.

---

## SUMMARY

- **Inputs:** `title` is the only rich signal already in the DB (100 % coverage).
  `market.slug`, `event.slug`, `event.title` require a Gamma call
  (`/markets?condition_ids=<id>&closed=true`); `market_id` **is** the conditionId for
  100 % of swept and 92.7 % of unswept markets, so the call is available. `tags` and
  `event.category` come back but are empty for this population (established).
- **Slug finding:** `event.slug` is a strongly structured **negative** discriminator
  (rigid template prefixes for crypto / weather / sports / esports cover ~83 % of the
  population, recognisable from `title` alone) and a **moderate positive** one
  (`…-election-…`, `…-primary-…`, `nominee-for-…`, `governor` are decisive; the
  geopolitics prop tail and the Geo/Elec boundary are not). **Slug alone is not
  trustworthy as the sole classifier; it is an excellent cheap pre-filter.**
- **Recommended shape:** a **cascade** — deterministic `title`/`slug` exclusion of the
  template ~83 %, then the existing local LLM (Qwen3-Coder) on the ~17 % residual with
  `[title, market.slug, event.slug, event.title]` as inputs and **no keyword
  pre-filter**. ~15 h of local compute vs ~80 h for LLM-on-everything.
- **Iteration:** stable **keyset cursor** on `market_id` (immutable unique PK) — never
  `LIMIT/OFFSET` over the mutating `category='Unknown'` set (that is the confirmed
  step-over pathology that has permanently skipped ~19,000 rows in the current M9).
- **Writes:** `markets.category` **only**, guarded `WHERE category='Unknown'`; mirrors
  to `trades.market_category`; adds a `category_source` provenance column + a sidecar
  log. Touches no resolution/provenance column — enforced structurally.
- **Validation gate, thresholds fixed below before any result exists:** relevance
  recall **≥ 95 %** against the 11,967 pre-classified (and ≥ 95 % in every
  origin-mechanism and Geo/Elec stratum); directional agreement **≥ 90 %**;
  hand-adjudicated genuine-error rate on a 50-disagreement sample **≤ 20 %**;
  false-positive rate on hand-labelled negatives **≤ 2 %** (template bucket) / **≤ 10 %**
  (residual); pre-filter false-exclusion **≤ 0.5 %**. **On failure: STOP** — the
  corpus is spent; at most one retry against a *fresh independently-drawn* corpus with
  the fix specified in advance; a second failure means abandon.

---

## PART 1 — THE INPUTS

### 1.1 Signal inventory & coverage `[V]`

`markets` has **no** slug, event, or tags column (`PRAGMA table_info` →
`market_id, title, category, end_date, resolved, winning_outcome, last_checked,
resolution_date, condition_id, api_id, difficulty_score, trade_gap_flag,
clob_token_id_*, data_source, flag_reason, resolution_recorded_at,
resolution_evidence_source, resolution_evidence_detail`).

| Signal | In DB? | Coverage — swept `Unknown` (214,516) | Coverage — unswept `Unknown` (353,047) | Notes |
|---|---|---|---|---|
| `markets.title` | **yes** | 214,516 / 214,516 = **100 %** | 353,047 / 353,047 = **100 %** | the only rich signal already local |
| `trades.market_title` | yes (denormalised) | ~100 % (markets with ≥1 trade) | lower (unresolved/thin markets may have 0 trades) | redundant with `markets.title` |
| `market_id` usable as conditionId for a Gamma call | yes | **214,516 / 214,516 = 100 %** (all 66-char `0x…`) | **327,379 / 353,047 = 92.7 %** (25,668 are zero-padded synthetic ids, mostly the ~30k " AND "-parlay markets — not real conditionIds, not in Gamma) | `condition_id` *column* is only populated for 1,019 swept, but is not needed — `market_id` is the hash |
| `market.slug` | **no — Gamma call** | ~100 % of queryable (30/30 + 14/15 in this session's samples; the 1 miss was a still-open market excluded by `closed=true`) | ~100 % of the 92.7 % queryable | kebab-case slugified question |
| `event.slug` | **no — Gamma call** | ~100 % of queryable (every sampled market had ≥1 event) | ~100 % of queryable | **the new candidate — see 1.2** |
| `event.title` | **no — Gamma call** | ~100 % of queryable | ~100 % of queryable | e.g. "Sachsen-Anhalt Parliamentary Election" |
| `event.tags` | Gamma call | present but **`[]`** for this population `[V]` (this session + ce35996) | same | dead input |
| `event.category` / `market.category` | Gamma call | present but **`null`** for 0/131 sampled `[V]` (ce35996 + this session) | same | dead input — this is the whole reason the classifier is needed |
| `end_date`, `data_source` | yes | 100 % | 100 % | weak priors only (e.g. 5-minute `end_date` gap ⇒ crypto template) |

**One Gamma fetch per market** yields `market.slug + event.slug + event.title` in a
single response; batchable ~12 conditionIds/request. For 214,516 swept: ≈ **17,900
requests ≈ 6.5 h** at the ~1.3 s/request pacing observed this session (no `429`s seen
across ~19 calls). Fetch once, stage to a table, then classify offline.

### 1.2 Characterising the slug `[V]`

**Samples this session** (Gamma `/markets?condition_ids=…&closed=true`, batched):
30 swept-`Unknown` backlog markets (30/30 returned), 14 known geo/elec positives
(14/15 returned), plus the 16 slugs already on record from ce35996 / the ingest-defect
doc.

**How structured is it?** Both `market.slug` and `event.slug` are kebab-case. For a
large majority of the population the `event.slug` is a **machine-generated template
descriptor with a rigid family prefix**, not free text:

| Family | `event.slug` shape (observed) | Relevance |
|---|---|---|
| Crypto up/down | `btc-updown-5m-1785326700`, `eth-updown-15m-1786086000`, `sol-updown-5m-…` | non-geo |
| Crypto price level | `solana-above-on-may-11`, `ethereum-above-on-june-8-2026-7pm-et` | non-geo |
| Weather | `highest-temperature-in-helsinki-on-may-7-2026`, `highest-temperature-in-ankara-on-june-6-2026` | non-geo |
| Sports (league code) | `nba-was-mem-2025-12-20`, `epl-bre-wol-2026-03-16-more-markets`, `mlb-bal-laa-2026-06-22`, `fifwc-fra-mar-2026-07-09-total-corners`, `wta-svitoli-kalinsk-2026-06-15`, `cwbb-day-david-2026-02-21` | non-geo |
| Esports (game code) | `dota2-aur1-ts8-2026-05-14`, `cs2-nrg-iowast-2026-07-28`, `lol-g2-ly-2026-07-10`, `mlbb-omnix-aterio-2026-05-29` | non-geo |
| Commodities / misc | `what-will-crude-oil-cl-settle-at-on-april-8`, `the-american-rodeo-championship-bareback-winner` | non-geo |
| **Elections** | `romania-presidential-election-winner`, `democratic-nominee-for-florida-governor`, `chile-presidential-election-1st-round-3rd-place`, `sachsen-anhalt-parliamentary-election-winner`, `bulgaria-presidential-election`, `ny-10-house-margin-of-victory-2026`, `brampton-mayoral-election-winner`, `paris-mayoral-election-runoff-…` | **Elections** |
| **Geopolitics** | `usisrael-strikes-iran-by`, `will-russia-abandon-syrian-naval-base-before-april`, `odds-of-russia-x-ukraine-ceasefire-in-2025-on-friday`, `israel-withdraws-from-lebanon-by`, `strait-of-hormuz-traffic-returns-to-normal-by-…` | **Geopolitics** |
| **Politician-conduct props** | `what-will-trump-say-during-australia-pm-events-on-…`, `who-will-trump-talk-to-in-september`, `trump-vp-announcement-when`, `will-trump-release-more-epstein-files-in-2025` | Elections per M9's convention; borderline |

**How consistently does it encode category?**

- **As a NEGATIVE filter: very consistent.** Every crypto / weather / sports / esports
  market carries an unambiguous family token in `title` **and** `event.slug`
  (`up or down`/`updown`, `temperature`, the league/game code, `: O/U `, `Spread:`,
  ` vs. `). Crude title-only bucketing already tags **177,978 / 214,516 = 83.0 %** of
  the swept backlog as template families `[V]`. A weather/crypto/sports market is
  effectively never Geopolitics or Elections — a deterministic exclusion on these
  patterns has near-zero false-negative risk (to be gate-measured, Part 3.9).
- **As a POSITIVE filter: moderate.** `-election-`, `-primary-`, `-parliamentary-`,
  `nominee-for-`, `-governor`, `-senate`, `-referendum`, `mayoral-election` in
  `event.slug` are near-decisive for Elections. Geopolitics tokens (`russia`,
  `ukraine`, `israel`, `iran`, `ceasefire`, `sanctions`, `tariff`, `strikes`,
  `nato`, `hormuz`) are indicative but noisier — `iran`/`israel` also occur as
  athlete/team names, `strike` is a sports term. The **politician-conduct prop tail**
  (`what-will-trump-say-…`) has no election token at all and needs judgment. The
  Geo↔Elec boundary itself is genuinely fuzzy (`will-trump-remove-10-blanket-tariff`
  — Geo or Elec?).

**What a slug rule would look like:** a two-list keyword match on
`concat(title, ' ', market_slug, ' ', event_slug, ' ', event_title)`:
`EXCLUDE_PREFIXES/TOKENS` (the template families above) → not-relevant;
`ELECTION_TOKENS` / `GEOPOLITICS_TOKENS` → tentative Elections / Geopolitics;
everything matching neither → residual. It resolves the ~83 % cleanly on the exclude
side and a further slice on the election side, but leaves the geopolitics tail and
the boundary cases unresolved.

### 1.3 Which inputs the classifier should use

- **Deterministic pre-filter:** `title` (DB) + `event.slug`/`event.title` (Gamma).
  Its job is exclusion of the template families — where it is strong.
- **LLM stage:** `title` + `market.slug` + `event.slug` + `event.title`, concatenated,
  one market per line, **no 37-keyword pre-filter** (that filter reaches only 2.5 % of
  the population and over-selects 2–3×; it is the wrong gate). `tags` and
  `event.category` are omitted — they are empty.
- **Slug alone is not sufficient** as the whole classifier: its positive recall on
  geopolitics props and its handling of the Geo/Elec boundary are too weak to pass a
  precision gate unaided. It **is** sufficient — and cheaper than the LLM — for the
  exclusion half, which is why the recommended shape is a cascade, not a pure rule
  and not a pure LLM.

---

## PART 2 — THE DESIGN

### 2.4 Classifier shape — options and recommendation

| Option | Accuracy expectation | Cost | Verdict |
|---|---|---|---|
| **A. Deterministic slug/title rule only** | High precision on template exclusion and on clean `-election-` slugs; **weak recall** on geopolitics props and ambiguous cases; brittle to new template families | seconds, no API beyond the one-time slug fetch | **Not as sole classifier.** Fails a positive-recall gate. Keep as the pre-filter. |
| **B. LLM (Qwen3-Coder) on the whole population, better inputs, no keyword filter** | Highest — the LLM already decides well when it sees the right candidates (established: every logged skip is a confident correct rejection) | 214,516 / 20 per batch × ~27 s ≈ **~80 h** local compute + ~6.5 h slug fetch | Works, but 5× the compute for marginal accuracy gain over C — most of that 80 h is the LLM re-confirming that "btc-updown-5m" is not geopolitics |
| **C. Cascade: deterministic exclusion → LLM on the residual** *(recommended)* | Same as B on the part that matters (the ambiguous ~17 %); the excluded 83 % are template families the LLM would also reject with confidence | pre-filter ~0; slug fetch for residual ~1 h; LLM on ~36 k residual / 20 × 27 s ≈ **~13–15 h** | **Recommended** |

**Recommendation: C, the cascade.** Reasoning:
1. **5× cheaper** (~15 h vs ~80 h) with no accuracy cost on the decision that matters —
   the residual is exactly the zone where LLM judgment is needed.
2. **The pre-filter is independently validatable** (Part 3.9 false-exclusion gate), so
   its aggressiveness is bounded by evidence, not assumed.
3. It concentrates the scarce resource (LLM judgment) on the ambiguous tail rather
   than on 178 k confident rejections.
4. It degrades gracefully: if the pre-filter proves less safe than expected
   (false-exclusion > 0.5 %), narrow it and the residual grows toward option B's
   cost — a known, measured trade, not a surprise.

**Cost caveat `[I]`:** the ~15 h figure assumes the deterministic pass safely removes
~80 %. If it only safely removes ~60 %, the residual is ~86 k → ~32 h. **The
pre-filter's safe coverage must be measured (Part 3.9) before the run is scheduled**,
not assumed from the 83 % title-bucket figure.

### 2.5 Candidate query & iteration — stable keyset cursor

**Do NOT** use `LIMIT ? OFFSET ?` over `WHERE category='Unknown' …`. The current M9
does exactly this and its offset advances monotonically while classifications remove
rows from the predicate, so the window slides past unexamined rows —
`2026-08-30-category-classifier-investigation.md` established ~19,000 rows permanently
skipped this way. `[V]`

**Cursor state:** a single value `last_market_id` (persisted in a small state file or
a one-row control table), initialised to `''`.

**Per batch:**
```sql
SELECT market_id, title            -- + staged market_slug, event_slug, event_title
FROM markets
WHERE category = 'Unknown'
  AND title IS NOT NULL
  AND market_id > :last_market_id
ORDER BY market_id
LIMIT :batch_size;                 -- e.g. 200 for the pre-filter, 20 for the LLM stage
```
After processing the batch, set `:last_market_id` to the **largest `market_id` seen in
the batch** (not "+ batch_size" — the actual last row).

**Why this has no step-over:**
- `market_id` is the immutable, unique PRIMARY KEY. The only mutation the job makes is
  `category` `'Unknown' → 'Geopolitics'/'Elections'`, which **removes** a row from the
  predicate without changing any row's `market_id` or its order relative to the
  cursor. A classified row simply is not returned next time; nothing shifts under the
  cursor.
- Rows inserted later with `market_id > last_market_id` are still picked up.
- Rows inserted with `market_id < last_market_id` (rare — new markets get fresh
  hashes, and the ingest path writes `'Unknown'` anyway) would be missed in the
  current pass. **Reconciliation:** when the query returns 0 rows, reset
  `last_market_id = ''` and sweep again. Rows already classified are filtered by
  `category='Unknown'`; only genuinely-still-`Unknown` rows are revisited. Each full
  sweep is idempotent and cheap once the backlog is drained.
- **Concurrency with M9:** if M9 keeps running, both target `category='Unknown'`.
  SQLite serialises writes (WAL + `busy_timeout`). Because both sides only ever move a
  row *out* of `Unknown`, last-writer-wins is harmless (same terminal state family).
  Recommend M9 be paused for the one-off backlog run to avoid the two cursors
  interfering, but it is not required for correctness. (Decision on pausing M9 is out
  of scope here.)

**Sweep-scoping use (prompt goal (a)):** the same deterministic pre-filter, run over
the *unswept* candidate set, produces the "sweep only what is plausibly relevant"
list — it is the pre-filter output, not a separate mechanism.

### 2.6 What it writes — and what it must not

**Writes, and only these:**
```sql
UPDATE markets
SET category = :decided_category,          -- 'Geopolitics' or 'Elections' ONLY
    category_source = :method_tag,         -- new column, Part 2.7
    last_checked = :now
WHERE market_id = :market_id
  AND category = 'Unknown';                -- guard: never overwrite a non-Unknown category
```
```sql
UPDATE trades
SET market_category = :decided_category
WHERE market_id = :market_id
  AND market_category = 'Unknown';         -- mirror, same guard (matches M9's behaviour)
```
- It writes **nothing** when the decision is "not relevant" — the market stays
  `category='Unknown'`; the outcome is recorded in the sidecar log (Part 2.7), not in
  `markets`. (Rationale: `'Unknown'` already means "not classified as ours"; inventing
  a `'NotRelevant'` value would break every existing `category IN
  ('Geopolitics','Elections')` / `category='Unknown'` consumer catalogued in the
  geo-scoping inventory.)
- The `AND category = 'Unknown'` guard makes the write **idempotent and
  race-safe** and structurally incapable of touching a market another mechanism has
  already classified.

**Must NOT touch:** `resolved`, `winning_outcome`, `resolution_date`,
`resolution_recorded_at`, `resolution_evidence_source`, `resolution_evidence_detail`,
`trade_gap_flag`, `end_date`, `title`, `condition_id`, `api_id`. Those six resolution
columns have a single canonical writer, `monitoring/resolution_writer.py::
mark_market_resolved()`, backed by the `trg_resolved_no_unresolve` trigger.

**How that is enforced (not merely intended):**
1. The classifier issues the two `UPDATE … SET category`/`market_category` statements
   above **as literal SQL** — it does **not** call `db.update_market()` (which fans
   out to 8 columns including `resolved`/`winning_outcome` via `ON CONFLICT` — see
   `2026-08-31-ingest-category-defect.md` §2.5). Using `update_market()` here is the
   specific anti-pattern.
2. A unit test asserts the classifier module's SQL contains no token from
   {`resolved`, `winning_outcome`, `resolution_date`, `resolution_recorded_at`,
   `resolution_evidence`}, mirroring the structural self-test that
   `column_definitions.py` already uses for `BACKTEST_WINDOW_BASE_WHERE`.
3. `audit_invariants.py` gains a check: no row where `category_source` is a classifier
   tag has a `resolution_*` value that changed in the same run window (belt-and-braces;
   the trigger already blocks `1→0` and the classifier never sets `resolved` at all).

### 2.7 Provenance

**Yes — it must record provenance.** `markets.category` today carries no record of
which of the ~10 mechanisms (geo-scoping inventory M1–M14) set it, and the project has
been bitten repeatedly by untagged writes — O-2/O-30 (`trades.market_category`
divergence), and the entire `resolution_evidence_source` retrofit, whose central
problem was "resolved=1 rows with no record of who resolved them, un-adjudicable after
the fact." Adding a classifier that writes tens of thousands of category values
**without** provenance would recreate exactly that.

**Proposed (design only):**
- **New column `markets.category_source TEXT`** (nullable). Values:
  `'llm_relevance_v1'`, `'deterministic_slug_v1'`, `'gamma_event'` (for future M3
  writes), `'legacy'` (backfilled for existing non-`Unknown` rows so audits can tell
  "pre-classifier" from "classifier"), `NULL` (never classified). One value per row,
  set atomically with `category`.
- **Sidecar table `category_classification_log`**
  `(market_id, decided_category, method, model_version, confidence, inputs_hash,
  run_id, classified_at)` — append-only, composite PK `(market_id, run_id)`. Records
  every decision **including "not relevant"** (which writes nothing to `markets`), so
  a disagreement (Part 3.10) can be reconstructed: what the classifier saw, what it
  said, which run. `inputs_hash` = hash of the exact `title|market_slug|event_slug|
  event_title` string fed in.
- This lets `audit_invariants.py` assert "every `category IN
  ('Geopolitics','Elections')` row has a non-NULL `category_source`" once the
  `'legacy'` backfill is done, and makes the validation gate's disagreement analysis a
  table join rather than an archaeology exercise.
- Adding a column and a table is a schema migration — **specified here, not
  performed.**

---

## PART 3 — THE VALIDATION GATE (thresholds fixed now, before any result exists)

The corpus and the hand-labelled sets defined below are the **held-out gate**. They
are used **once**. Tuning the classifier against them and re-measuring is the
garden-of-forking-paths this project has repeatedly guarded against — see Part 3.11
for the stop.

### 3.8 Recall — against the 11,967 already-classified

**Corpus:** all rows with `category IN ('Geopolitics','Elections')` — **11,967**
(7,937 Elections, 4,030 Geopolitics) `[V]`. Origin mix `[V]`: `live_monitoring` 7,566,
`historical_backfill` 1,797, `gamma_backfill_*` 2,459, `background_backfill` 144,
`gap_recovery` 1.

**Procedure:** run the full cascade over all 11,967 (temporarily treating them as
input; the classifier does not see the stored label). For each, record the
classifier's output ∈ {Geopolitics, Elections, NotRelevant}.

**Metrics & thresholds (fixed):**
| Metric | Definition | Threshold to pass |
|---|---|---|
| **Relevance recall (overall)** | fraction classified Geopolitics **or** Elections | **≥ 95 %** |
| **Relevance recall (per stratum)** | same, computed separately for {Geopolitics vs Elections} × {live_monitoring, historical_backfill, gamma_backfill} — 6 cells (background_backfill/gap_recovery too small, folded into nearest) | **≥ 95 % in every cell** — a systematic blind spot cannot be averaged away |
| **Directional agreement** | of the rows called relevant, fraction whose Geo/Elec label matches the stored label | **≥ 90 %** (lower band: the Geo↔Elec boundary is genuinely fuzzy — a tariff/shutdown market is defensibly either) |

Rows the classifier calls `NotRelevant` (expected ≤ 5 %) and directional mismatches
(expected ≤ 10 %) are **disagreements** → adjudicated per 3.10.

### 3.9 Precision — false positives on known-negatives

**Negative corpus (hand-labelled, drawn now, before results):**
- **150 from the deterministic-template bucket** — random `Unknown` markets whose
  `title` matches a template family (crypto up/down, weather, sports O/U, esports).
  Near-certain true negatives.
- **150 from the residual** — random `Unknown` markets whose `title` matches **no**
  template pattern and **no** election/geopolitics token (the genuinely ambiguous
  zone).
- Total **300**, hand-labelled Relevant / NotRelevant by the adjudicator against the
  3.10 rubric **before** the classifier is run over them.

**Thresholds (fixed):**
| Metric | Threshold to pass |
|---|---|
| Classifier false-positive rate on the **template bucket** (calls a weather/crypto/sports market Geo or Elec) | **≤ 2 %** (≤ 3 of 150) — a hard-error class |
| Classifier false-positive rate on the **residual** | **≤ 10 %** (≤ 15 of 150) — this is the number that governs "does it pollute the population" |
| **Pre-filter false-exclusion:** of a **random 200 markets the deterministic pass EXCLUDES**, fraction that are actually Geo/Elec on hand-inspection | **≤ 0.5 %** (≤ 1 of 200) — the pre-filter must not discard relevant markets before the LLM sees them |

### 3.10 Adjudicating a disagreement

A disagreement is **classifier output ≠ stored label** (3.8) or **classifier output ≠
hand-label** (3.9).

- **Who decides:** the human operator running the gate (per this project's
  decision-record convention, Oscar).
- **On what basis — rubric, fixed now:**
  - **Elections** — resolution turns on a vote / candidate / seat / primary /
    nomination / coalition / party-leadership outcome, *or* on the official conduct of
    a declared political figure in political capacity (this includes the
    "will X say/post …" appearance-prop markets — they are scoped to a politician's
    political event; this matches M9's existing convention, so it does not
    artificially inflate disagreement).
  - **Geopolitics** — resolution turns on state action, armed conflict, diplomacy,
    sanctions, treaties, territorial control, or an international-relations event.
  - **Relevant** = Elections ∨ Geopolitics. **NotRelevant** = everything else
    (markets, sports, weather, entertainment, crypto, science, personal/celebrity).
  - **Geo-vs-Elec ambiguity** (tariffs, shutdowns, a leader's foreign-policy speech):
    the gate scores **relevance**, so any relevant call counts as a directional match;
    the adjudicator notes it as "boundary" and moves on.
  - **Evidence the adjudicator may use:** the market `title`, the Gamma
    `market.slug` / `event.slug` / `event.title`. Not the stored label (that is what
    is being adjudicated).
- **Output:** for each of a **random 50 disagreements** (stratified: ~25 from 3.8's
  mismatch set, ~25 from 3.9's), the adjudicator records
  `{market_id, stored/hand label, classifier output, adjudicated truth, one-line
  reason}` in the gate result doc.
- **Adjudication metric (fixed):** **genuine classifier-error rate ≤ 20 %** of the 50
  — i.e. ≤ 10 cases where the adjudicated truth matches the stored/hand label and the
  classifier was wrong. Above 20 % ⇒ the disagreements are not "the old mechanisms
  were sloppy," they are the classifier failing ⇒ gate FAILS.
- **Single-adjudicator safeguard:** there is effectively one reviewer. Borderline
  calls (adjudicator genuinely unsure after reading title + slugs) are recorded as
  **"classifier error"** — i.e. ties break *against* the classifier, conservatively.

### 3.11 What happens if it FAILS the gate

Fixed now. **Not "iterate until it passes."**

1. **Any** threshold in 3.8 or 3.9 missed, **or** adjudicated genuine-error rate
   > 20 % (3.10) ⇒ **STOP.** Write a gate-result decision doc stating exactly which
   threshold failed, by how much, and the adjudication notes.
2. The 11,967-corpus, the 300 hand-labelled negatives, and the 200 pre-filter
   exclusions are now **spent**. They must not be re-measured against a revised
   classifier — that is the forking-paths failure.
3. **Permitted next move — exactly one of:**
   - **(a) Abandon** the classifier for this population. Concretely: the swept backlog
     stays `Unknown`; sweep-scoping stays on whatever pre-filter exists today; the
     question returns to design with the gate-result doc as input. This is a valid,
     expected outcome — not a defeat to be engineered around.
   - **(b) One fresh-corpus retry**, and only if the failure is a **narrowly
     diagnosed, mechanical** bug (e.g. a prompt-formatting error, a cascade token list
     that is demonstrably too aggressive) whose fix is **written down before any new
     result is seen**. The retry runs against a **freshly drawn, independent**
     validation set: a new stratified random 11,967-equivalent sample of pre-classified
     markets + a new random 300 negatives + a new 200 pre-filter exclusions, all
     re-hand-labelled. Same thresholds. **One retry maximum.** A second failure ⇒
     abandon (a).
4. **Partial pass is a FAIL.** "Recall passes but precision fails" (or vice versa)
   does not license shipping the classifier for sweep-scoping but not for backfill,
   *unless* those two uses are pre-registered as two separate gates with their own
   thresholds **before** any result exists. Absent that pre-registration, one gate,
   pass-or-abandon.

---

## WHAT REMAINS UNSPECIFIED (deliberately — needs its own step)

- The exact `EXCLUDE` / `ELECTION` / `GEOPOLITICS` token lists for the deterministic
  pass — they must be drafted, then their coverage and false-exclusion measured
  (3.9) before the run is scheduled. Draft ≠ design.
- The LLM prompt text (the current M9 prompt is a starting point; it must be adapted
  to take slug inputs and drop the "be conservative, default Unknown" instruction that
  suits M9's keyword-pre-filtered candidates but would hurt recall here).
- Schema migration mechanics for `category_source` + `category_classification_log`
  (backup, `ALTER`, `'legacy'` backfill of ~11,967 rows).
- Whether M9 is paused for the one-off run (recommended, not required — noted in 2.5).
- Staging-table design for the one-time Gamma slug fetch.

No implementation. This is the design and the pre-registered gate.
