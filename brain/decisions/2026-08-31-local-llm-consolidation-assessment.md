# Local-LLM Classification Paths — Consolidation Assessment

**Date:** 2026-08-31. **Scope:** READ-ONLY. Nothing built, changed, or recommended for
implementation. A few bounded live checks (Ollama `/api/tags`, journald greps).
**Predecessors:** `2026-08-31-geo-scoping-inventory.md` (3b367dd),
`2026-08-31-why-unknown-investigation.md` (ce35996),
`2026-08-31-ingest-category-defect.md` (6df24e6),
`2026-08-31-relevance-classifier-design.md` (c918b2f).
**Tagging:** `[V]` verified this session; `[I]` inferred. Every claim in the prompt —
including "M6 is active in AI_FILTER_MODE='hybrid'" — treated as a hypothesis.

---

## HEADLINE FINDING

**M6 — monitor.py's Mistral KEEP/EXCLUDE gate — is not running in production.** The
inventory recorded it as "LIVE (hybrid mode)"; that was inferred from the
`AI_FILTER_MODE = "hybrid"` module constant, not verified against the entrypoint. The
production service runs `scripts/start_monitoring.py → monitoring.main_telegram_safe`,
which constructs the monitor with **`ai_agent=None`** (hardcoded). The Layer-2 guard
`if AI_FILTERING_ENABLED and AI_FILTER_MODE in ["hybrid","ai_only"] and self.ai_agent`
fails on `self.ai_agent` being `None`, so `_ai_categorization_check` is **never
called**. Journald confirms: last 2 h of the monitor loop = 25 `[KEYWORD FILTER]`, 5
`[DEFAULT]`, **0 `[AI PATH]`, 0 `[AI FILTER]`**; every restart banner since at least
2026-05-31 reads `TELEGRAM-SAFE POLYMARKET MONITORING`, never `AI Agent: Enabled`. `[V]`

Consequences that ripple through the rest of this assessment:
- **The `ai_cache` is always empty in production** (its only writer never runs). There
  is **no discarded intelligence to recover** — none was ever computed (Part 1.3).
- **M6 vs M9 agreement is unmeasurable** — one side has never executed a decision
  (Part 2.8).
- The proposed third classifier (c918b2f) is **not duplicating a working mechanism**.
  It duplicates M9 (which *does* run) and it *replaces* M6 (latent, never-run code).

---

## PART 1 — WHAT DOES M6 ACTUALLY DO?

### 1.1 `_ai_categorization_check` in full `[V]` (`monitor.py:290–363`)

- **Model:** `mistral:latest` via **Ollama**, wrapped by `pydantic_ai.Agent`
  (`Agent("openai:mistral:latest")` with `OPENAI_BASE_URL=http://localhost:11434/v1`),
  built by `initialize_pydantic_agent()` in **`monitoring/main.py`** — the entrypoint
  that is **not** used in production (Part 1.2). `mistral:latest` (4.4 GB) **is**
  pulled in Ollama, so the path would function if wired. `[V]`
- **Prompt:** market **title only**. Presents 7 categories (GEOPOLITICS, ECONOMICS,
  SPORTS, CRYPTO, STOCKS, ENTERTAINMENT, OTHER) as a reasoning scaffold, then:
  *"If it's clearly GEOPOLITICS or ECONOMICS, respond: KEEP. Otherwise, respond:
  EXCLUDE."*  Note: **GEOPOLITICS here bundles Elections + wars + IR + diplomacy +
  government policy**, and **ECONOMICS is KEEP too** — a wider net than the thesis's
  Geopolitics/Elections.
- **Output vocabulary:** effectively **binary** — the parser scans the response for
  `EXCLUDE` (→ exclude) then `KEEP` (→ keep); if neither, it checks for
  `SPORTS/CRYPTO/STOCKS/ENTERTAINMENT/OTHER/WEATHER` (→ exclude) else keep. Returns a
  `bool should_exclude`. **No category string is produced or stored.**
- **What happens to the answer:** returned up to `_should_exclude_market`, which
  returns it to `check_for_new_trades`. `True` → `continue` (market + trade **not
  stored**). `False` → market stored, but its `category` is taken from the Gamma
  event-cache (`internal_category`, ≈always `'Unknown'` — see ce35996), **not** from
  M6. So even a working M6 KEEP does **not** categorise; it only gates storage.
- **Failure mode:** any exception → logs a warning → returns `False` (INCLUDE).

### 1.2 `AI_FILTER_MODE` — the modes, and what "hybrid" means `[V]`

`_should_exclude_market` runs, in order:
1. **Gate 0** — if a Gamma `event_category` is present: `HARD_EXCLUDE_CATEGORIES` →
   exclude, `HARD_INCLUDE_CATEGORIES` → include. (`event_category` is ≈always `None`
   for this population, so Gate 0 ≈never fires.)
2. **Layer 1** — `_keyword_exclusion_check(title)` (~150 exclusion keywords + regex) →
   exclude.
3. **Fast path** — title contains any of 26 `geopolitics_signals` → **include, no AI**.
4. **Layer 2** — `if AI_FILTERING_ENABLED and AI_FILTER_MODE in ["hybrid","ai_only"]
   and self.ai_agent:` → `_ai_categorization_check`.
5. **Default** — include.

| Mode | Behaviour in this code |
|---|---|
| `keywords_only` | Layer 2 skipped; steps 1–3 then default-include |
| `hybrid` | Layer 2 runs **only** for titles that survived Layer 1 and matched no fast-path signal — i.e. the ambiguous residual |
| `ai_only` | **Identical to `hybrid`** in this code — the `in ["hybrid","ai_only"]` test treats them the same, and Layer 1's keyword exclusion still short-circuits first. The name is misleading; there is no "AI decides everything" mode. |

**Production is effectively `keywords_only` regardless of the constant**, because
`self.ai_agent is None` makes step 4's condition false. The constant says `"hybrid"`;
the wiring says otherwise.

### 1.3 THE CACHE `[V]`

- **What:** `self.ai_cache: OrderedDict`, keyed by **`market_title` string**, value =
  `should_exclude` **bool** (not a category).
- **Where it lives:** in-process memory only. **No file, no DB table, no serialisation.**
- **Persistence:** **none.** Recreated empty on every monitor start
  (`self.ai_cache = OrderedDict()` in `__init__`).
- **Size:** cap `_AI_CACHE_MAX = 10_000`; when full, evicts oldest 1,000 down to
  `_AI_CACHE_EVICT_TO = 9_000`. LRU via `move_to_end`.
- **Overlap with the backlog:** **zero, by construction.** The cache's only writer is
  `_ai_categorization_check`, which is never called in production (Part 1.2). Even in
  a hypothetical run where M6 were wired, the cache would hold at most 10,000 title→bool
  entries, non-persistent, and would contain **no category** — a KEEP entry does not
  say "Geopolitics" or "Elections", only "don't drop this." **There is no existing
  intelligence that was computed and discarded — it was never computed.**

### 1.4 EXCLUDE → the market is not stored at all `[V]`

`check_for_new_trades`: `if await self._should_exclude_market(...): excluded_count +=
1; continue`. The `continue` is **before** `store_market_from_trade` and `add_trade`.
So an excluded market gets **no `markets` row and no `trades` row**.

In production the only active exclusion is **Layer 1 keyword** (Gate 0 ≈never; Layer 2
off). Journald: ~25 `[KEYWORD FILTER] [EXCLUDED]` per 2 h ⇒ **~300 markets/day dropped
at ingest, never rowed** `[I]` (extrapolated from a 2 h window). **We are missing rows
entirely** for those — but from the deterministic keyword filter, not from any LLM.
Whether the keyword filter's exclusions are all correct is not audited (no
ground-truth pass exists); its false-exclusion risk is the same one the c918b2f
pre-filter gate is designed to measure.

### 1.5 Record of M6's decisions `[V]`

- **LLM decisions:** none exist, so no record.
- **Keyword/fast-path/default gate decisions:** `safe_print` → stdout → journald only.
  `[KEYWORD FILTER] [EXCLUDED] …`, `[FAST PATH] Strong geopolitics signal …`,
  `[DEFAULT] No match, including …`. Journald retains ~3 months (earliest entry
  2026-05-31; 3.2 GB archived+active). **Ephemeral, unindexed, not a table.** They
  record the *title* and the *gate that fired*, not a category, and only for markets
  that reached the ingest path (not `background_backfill`). Not a usable
  accuracy-measurement substrate without parsing months of journald.

---

## PART 2 — HOW M6 AND M9 DIFFER

### 2.6 Direct comparison `[V]`

| Axis | **M6** (`monitor.py._ai_categorization_check`) | **M9** (`backfill_market_categories.py`) |
|---|---|---|
| **Runs in production?** | **No** (`ai_agent=None`) | **Yes** — daily, `daily_maintenance.py` step, `--limit 50`; last run 2026-08-31 08:30, lifetime classified 11,880 |
| **Model** | `mistral:latest` (~7 B, 4.4 GB) via Ollama + pydantic-ai | `qwen3-coder:30b-a3b-q4_K_M` (~30 B MoE, 18.6 GB) via Ollama `/api/generate` |
| **Inputs** | market **title** only | market **title** only (batched 20/prompt) |
| **Prompt intent** | "is this GEOPOLITICS *or ECONOMICS*?" → KEEP/EXCLUDE (Elections folded into GEOPOLITICS; ECONOMICS also kept) | "classify each as **Geopolitics / Elections / Unknown**" + `confidence: HIGH/LOW`; *"be conservative, if unsure → Unknown"* |
| **Output vocabulary** | binary `KEEP`/`EXCLUDE` (bool) | `{Geopolitics, Elections, Unknown} × {HIGH, LOW}` |
| **Candidate scope** | every market on a flagged trader's incoming trade that survives Gate 0 + Layer-1 keyword + fast-path | `WHERE category='Unknown' AND title IS NOT NULL AND (37-keyword LIKE …)` — reaches only 2.5 % of the backlog (5,412 / 214,516), with `LIMIT/OFFSET` step-over (~19,000 rows skipped) |
| **What it writes** | **nothing to `category`** — only decides store vs drop; category still comes from Gamma (`'Unknown'`) | `UPDATE markets SET category=?` **and** `UPDATE trades SET market_category=?`, only when `confidence=HIGH AND category ∈ {Geopolitics,Elections}` |
| **Cost / decision** | n/a in prod. If wired: 1 Mistral call per uncached ambiguous title on the 15-min loop's critical path | ~27 s per 20-title batch ≈ **~1.35 s/title** of Qwen compute, off the critical path (nightly) |
| **Provenance recorded** | none | none |

### 2.7 Do they ever see the same market? `[V]/[I]`

- **M6-the-LLM:** sees **no** markets (never runs). So it never hands anything to M9.
- **The ingest keyword gates (which do run):** a market **kept** by the fast-path or
  by default, stored with `category='Unknown'`, reaches M9 **only if it also matches
  M9's 37-keyword filter**. The fast-path's 26 geo signals overlap M9's 37 keywords
  heavily (election, president, war, russia, ukraine, china, iran, nato, …), so a
  fast-path keep is *usually* in M9's candidate set. But a **default-keep** (title
  matched no keyword at all) is **not** in M9's 37-keyword set — M9 never sees it, and
  it sits `Unknown` permanently. This is the same 97.5 %-unreachable gap already
  quantified in `2026-08-30-category-classifier-investigation.md`; M6 does not change
  it.
- **Net:** even the parts of the ingest path that *are* live do not fully hand off to
  M9. There is no clean pipeline; there are two partially-overlapping keyword filters
  and one nightly LLM that between them leave most of the population untouched.

### 2.8 Do they agree? `[V]`

**Unanswerable — and that is the finding.** Agreement requires two mechanisms to have
each produced a decision on a shared set of markets. M6-the-LLM has produced **zero
decisions** in its production lifetime. There is no `ai_cache` on disk, no decision
log, no table. The only comparison available is *keyword-gate vs keyword-filter*,
which is mechanism-vs-mechanism keyword overlap already covered in the geo-scoping
inventory (§2b), not an LLM agreement study.

---

## PART 3 — THE CANONICAL QUESTION

### 3.9 Is the DECISION side canonical? `[V]`

**No. There is no canonical decision authority, and no module or doc claims one.**

- **Write side:** canonical — `markets.category`, with `column_definitions.py`'s
  structural self-test forbidding `trades.market_category` in population SQL.
- **Decision side:** `grep` for `def is_geo* / def classify_market* / def
  categorize_market* / def decide_category*` → **no single authority**; instead, at
  least these independent "is this market geo/political" code paths:
  1. `monitor.py._keyword_exclusion_check` + `geopolitics_signals` fast-path (live)
  2. `monitor.py._ai_categorization_check` — Mistral (latent, off)
  3. `backfill_market_categories.py` — Qwen (M9, live, nightly)
  4. `backfill_missing_markets.py.CATEGORY_TAG_MAP` — keyword→category (M10, live, ≈inert)
  5. `swarm/scripts/market_filter.py.should_include_market` — verbatim keyword fork, last synced 2026-05-02 (feedback-loop only)
  6. `scripts/detect_insider_activity.py._is_geopolitics` — older inline keyword fork
  7. `analysis/unified_elo_system.py.categorize_market` — DB-category-then-keyword, own 7-value vocabulary
  8. `analysis/trader_specialization_analysis.py.categorize_market` — keyword-score-max, own `CATEGORY_KEYWORDS`
  9. `analysis/consensus_divergence_detector.py.classify_market_by_disagreement` — (disagreement-based, tangential)

Nine code paths, five vocabularies, zero designated authority. The proposed third
classifier (c918b2f) would be the **first** built as a decision authority.

### 3.10 Should M6, M9, and the proposed third be ONE mechanism?

**Assessment: yes, they should be one decision module — and the c918b2f classifier is
the natural place for it, because M6-LLM is dead and M9 is a narrower version of what
c918b2f specifies.** What that would take, and what it would break:

**What "one mechanism" means concretely:**
- One module (e.g. `monitoring/relevance_classifier.py`) exposing one function —
  `classify(title, market_slug, event_slug, event_title) -> {Geopolitics, Elections,
  NotRelevant}` — one model (Qwen3-Coder; it already decides well and is the larger
  model), one prompt, one output vocabulary, one cascade (deterministic pre-filter →
  LLM residual).
- **Invoked from three sites**, not reimplemented in each:
  - *backlog / sweep-scoping* — the c918b2f one-off + keyset-cursor job.
  - *ingest* — a declared future caller (Part 3.11).
  - *M9's slot* — `backfill_market_categories.py` becomes a thin wrapper that calls
    the module, or is retired and its `daily_maintenance` step repointed.

**What it would take:**
- Build the c918b2f design as the module (not as a standalone script).
- Repoint `daily_maintenance.py`'s "Backfill market categories" step; retire M9's
  bespoke 37-keyword filter and `LIMIT/OFFSET` loop in favour of the module's
  keyset cursor. Preserve M9's write guard (`WHERE category='Unknown'`, dual
  `markets`+`trades` write).
- Leave M6's `_ai_categorization_check` in place but **de-scope it** — it is dead
  code; deleting it is a separate cleanup, not required for consolidation.

**What it would break / risk:**
- M9's daily cadence and its (buggy but bounded) behaviour is a known quantity;
  swapping it out is a change to a step in the 3–4 h maintenance window. The module's
  cascade must be validated (c918b2f gate) **before** it replaces M9, or a regression
  in the nightly step goes unnoticed.
- `market_filter.py` (swarm) and `detect_insider_activity._is_geopolitics` are
  *keyword* forks with their own callers (feedback-loop; insider scoring). Consolidation
  of those is a bigger blast radius (cross-repo, different runtime constraints — no
  Ollama in some contexts) and is **out of scope** for a geo-relevance decision
  module; they should be noted as "not yet converged," not force-fitted.
- The `analysis/*` `categorize_market` functions have their own vocabularies
  (Economics, Sports, …) serving ELO/specialisation logic, not thesis relevance —
  converging them is a different project.

### 3.11 The ingest opportunity `[V]/[I]`

M6's `_ai_categorization_check` **is** wired to the ingest hook
(`_should_exclude_market` at `monitor.py:883`), where a correct classification would
**prevent** an `Unknown` rather than requiring nightly repair. The
ingest-defect doc established ~13 new `Unknown`/day via `live_monitoring` and ~0 %
recoverable **from Gamma** — but a classifier is not Gamma.

**Could a consolidated classifier write `markets.category` at ingest? Feasibility:**
- **Hook exists** — `_should_exclude_market` already runs per new market and already
  has the title; adding a slug fetch is one Gamma call per genuinely-new market
  (~13/day + whatever the periodic re-scan surfaces) — cheap.
- **Model available** — Qwen3-Coder is pulled in the same Ollama the monitor host
  runs; Mistral too.
- **Write path** — would need `store_market_from_trade` / `store_market_dict` to accept
  and persist a classifier-supplied category instead of the Gamma-derived `'Unknown'`.

**What it would collide with:**
1. **The write-once early-return** (`2026-08-31-ingest-category-defect.md` §2.5). On
   *first* insert the classifier's category can be written cleanly (no conflict). The
   collision is only on *re-sightings* of existing markets — which the ingest-defect
   doc already says must be handled as a narrow guarded `UPDATE … WHERE
   category='Unknown'`, never via `update_market()`. So: first-sighting write is
   safe; re-sighting write must use the guarded form.
2. **Critical-path latency** — an LLM call inside the 15-minute monitor loop. Mitigated
   by: cascade (the deterministic pre-filter resolves ~83 % with no LLM call), a
   persistent decision cache (unlike M6's volatile one), or deferring the LLM leg to
   an async queue and writing `'Unknown'` provisionally.
3. **`ai_agent=None` wiring** — `main_telegram_safe.py` would need the classifier
   handle passed in (the one-line change M6 never got).
4. **Provenance** — an ingest-time write needs the same `category_source` tag c918b2f
   specifies, or it recreates the untagged-write problem at the ingest layer.
5. **Does NOT collide** with `mark_market_resolved()` / `trg_resolved_no_unresolve` —
   a category-only write touches none of the resolution columns.

**Net:** the ingest write is feasible and is the right long-term home, but it is
**strictly downstream of the classifier existing and passing its gate**. "Reactivate
M6" is not a shortcut — M6's prompt (binary, Elections-folded-into-Geopolitics,
Economics-kept), its title-only input, and its volatile cache would all have to be
replaced. What survives from M6 is the **hook location**, nothing else.

---

## PART 4 — DOES THIS CHANGE THE DESIGN?

**The c918b2f design should PROCEED, with three revisions — none of which are
"replace it with a consolidation," and none of which are "keep it as-is because it's
written."**

**Why proceed (not replace):**
- The pattern the prompt guards against — "capability existing, unexamined,
  duplicated" — **does not fully apply here.** M6-the-LLM has **never executed a single
  classification in production**. There is no working mechanism being needlessly
  re-implemented; there is dead code at a good hook location, and one narrow nightly
  LLM (M9).
- M9 *is* real, but the c918b2f cascade is **M9 done properly**: better inputs (slug),
  a fixed iteration cursor (vs M9's step-over), no lossy 37-keyword pre-filter (vs
  M9's 2.5 % reach), and — critically — a pre-registered validation gate M9 never had.
  Building c918b2f *is* the consolidation of M9, not a parallel third thing.

**The three revisions to c918b2f:**
1. **Frame it as a module, and subsume M9.** c918b2f currently says "M9 paused for the
   run, recommended not required." Stronger and correct: the classifier is built as
   `relevance_classifier.py`, and once it passes the gate, `daily_maintenance.py`'s
   category step is repointed to it and M9's bespoke script is retired. One model, one
   prompt, one vocabulary, one cursor.
2. **Name it the canonical decision authority.** Add to the design that this module is
   the single place "is this market Geopolitics/Elections" is decided, mirroring
   `column_definitions.py`'s role on the write side, with the ingest hook declared as
   a future caller. Record the nine scattered decision paths (Part 3.9) as
   known-not-yet-converged, with the `analysis/*` and cross-repo keyword forks
   explicitly out of scope.
3. **Add the M6 correction to the record.** The design and inventory both carry
   "M6 LIVE (hybrid)"; it is not. c918b2f's cost/consolidation section should note
   that M6-LLM is dead code, its `ai_cache` holds nothing, and its reactivation is a
   rewrite, not a reuse — so no one later proposes "just turn M6 back on" as a
   cheaper alternative.

**What does NOT change:** the cascade shape, the keyset cursor, the guarded
category-only write, the provenance column + sidecar log, and every threshold in the
validation gate (§3.8–3.11 of c918b2f) stand exactly as written.

---

## WHAT REMAINS UNCHECKED (named, not chased)

- The ~300/day keyword-filter ingest exclusions (§1.4) are extrapolated from one 2 h
  journald window; not measured over a longer span, and their correctness is unaudited.
- Whether `monitoring/main.py` (the M6-enabled entrypoint) is ever run manually for
  ad-hoc sessions — `restart_monitoring.py` only references it as a process pattern to
  *kill*; no launcher invokes it, but a human could.
- The `analysis/*` `categorize_market` functions were read for vocabulary, not traced
  to all their consumers.
- `AI_FILTER_MODE`/`AI_FILTERING_ENABLED` are module constants; not checked for a
  runtime override mechanism (there is no CLI flag for them in the entrypoints read).

No implementation. This is the assessment and the Part 4 call.
