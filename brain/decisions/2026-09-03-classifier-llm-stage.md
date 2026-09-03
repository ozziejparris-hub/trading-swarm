# Classifier LLM Stage — Prompt + Wrapper Built, NOT Run Against the Gate

**Date:** 2026-09-03. **Scope:** BUILD ONLY. `classify_batch()` was exercised
against six hand-constructed examples (informal smoke test, §4) to confirm
the wrapper works end to end. It has **not** been run against
`brain/decisions/gate-sets-2026-09-01/` (`set_a.csv`, `set_b.csv`, `set_c.csv`,
`labels.csv`) or the 11,967-row pre-classified corpus. No write path exists
yet — `markets`, `category_source`, and `category_classification_log` are
untouched by this task, verified below (§5).
**Design:** `2026-08-31-relevance-classifier-design.md` (e601648) §1.3, §2.4,
§2.6, §2.8, §2.9. **Predecessors:** `2026-08-31-classifier-schema-migration.md`
(c1037e3), `2026-08-31-prefilter-implementation.md` (3fb24af),
`2026-08-31-slug-fetch.md` (291aeb1), `2026-09-01-slug-fetch-unswept.md`
(c544e9f), `2026-09-01-gate-sets.md` (f75e1ea). **Code:** first-repo, on top
of `05873c4`.
**Tagging:** `[V]` verified this session; `[I]` inferred/judgment call, not
run/measured. Every claim in the task prompt treated as a hypothesis.

---

## 1. FILES SHIPPED

| File | Role |
|---|---|
| `monitoring/relevance_classifier_prompt.py` | The prompt (`PROMPT_TEMPLATE`, `MARKET_ENTRY_TEMPLATE`), with the two required departures from M9 argued in its own module docstring. No imports, no logic, not executable. |
| `monitoring/relevance_classifier.py` | The wrapper: `classify_batch(markets) -> list[ClassificationResult]`. Imports the prompt module; does everything else (batching, the Ollama call, parsing, error classification). |

Both are new files; nothing existing was edited. `scripts/backfill_market_categories.py` (M9) is untouched and still the live nightly step, per design §2.8 ("the repoint to `daily_maintenance.py` happens ONLY AFTER the gate passes").

---

## 2. THE PROMPT — design and its two required departures from M9

Adapted, not rewritten from scratch: same model, same "numbered list in →
JSON array out" contract, same `{i+1: dict}` batch convention M9 uses in
`apply_classifications`.

**Departure 1 — dropped "be conservative, if unsure classify as Unknown."**
M9's instruction suits M9's candidate set: a 37-keyword `LIKE`-filtered
subset where almost everything already carries a geo/elec-suggestive token,
so conservatism there mostly just catches the keyword filter's own false
positives (cheap precision, since the filter already discarded almost
everything). This classifier's residual has already passed
`relevance_prefilter.py`'s deterministic exclusion — no keyword filter
upstream (design §1.3 is explicit that the 37-keyword filter is "the wrong
gate" for this stage). A "default to NotRelevant when unsure" instruction on
an already-narrowed, already-ambiguous residual just re-inflates the
false-negative rate the whole cascade exists to avoid (design §2.4: "the
residual is exactly the zone where LLM judgment is needed"). The reasoning
is written into the prompt file's own module docstring, not just here, per
the task's instruction, so a future reader touching the prompt sees it
in place.

**Departure 2 — slug inputs, not title alone.** The prompt shows four
fields per market — `title`, `market_slug`, `event_slug`, `event_title` —
matching design §1.3 exactly ("title + market.slug + event.slug +
event.title, concatenated, one market per line"). These are the same four
fields staged in `relevance_slug_staging` by the two Gamma slug-fetch runs.

**Category definitions — same rubric the gate was labelled against.** The
prompt's Elections/Geopolitics/NotRelevant definitions are the design §2.9 /
§3.10 rubric in substance (vote/candidate/seat/primary/nomination/
coalition/party-leadership, or a declared political figure's conduct in
political capacity; state action/armed conflict/diplomacy/sanctions/
treaties/territorial control/international relations), including the
explicit carve-in for "will X say/announce" appearance-prop markets scoped
to a politician's political role (§3.10's parenthetical: "this matches M9's
existing convention, so it does not artificially inflate disagreement") and
the explicit boundary-case instruction (pick the closer fit on
geo-vs-elections ambiguity, matching §3.10: "any relevant call counts as a
directional match"). This was a deliberate choice, stated in the prompt
file's docstring as a warning against future drift: **the classifier and
the gate must share one standard**, or a measured disagreement conflates
"the classifier is wrong" with "the classifier used a different rubric than
the labeller."

**Output vocabulary:** `{Geopolitics, Elections, NotRelevant}`, not M9's
`{Geopolitics, Elections, Unknown}` — `'Unknown'` already means "never
classified" for `markets.category` (design §2.6); reusing it as an LLM
output would collide with that meaning. `NotRelevant` is recorded in
`category_classification_log` (when a write path exists) but never written
to `markets.category` (§2.6: "it writes nothing when the decision is 'not
relevant'").

---

## 3. BATCH-SIZE DECISION

The task asked me to confirm M9's `batch_size=20` still holds given the
added slug text, and adjust if the context budget is tighter.

**Real field-length averages, queried against the live DB `[V]`:**

| Field | Avg length (chars) | Source |
|---|---|---|
| `title` | 54.1 | `markets` (Unknown population, 818,865 rows) |
| `market_slug` | 49.2 | `relevance_slug_staging` (found rows, 66,748) |
| `event_slug` | 37.1 | same |
| `event_title` | 43.8 | same |

Per-market entry in the new prompt (title + all three slug fields, with the
`MARKET_ENTRY_TEMPLATE` labels/newlines): **244 chars/market**, vs. M9's
title-only line (~60 chars/market, `"{i+1}. {title}"`) — **a ~4x increase**,
slightly more than the task's "roughly triples" hypothesis, verified rather
than assumed.

**Prompt fixed overhead** (category definitions + instructions +
reply-format, measured by rendering `PROMPT_TEMPLATE` with an empty
candidate list) **`[V]`: 2,102 chars.**

**Total prompt size by batch size** (chars/3.7 as a chars-per-token
estimate `[I]` — not measured against the model's actual tokenizer):

| Batch size | Prompt chars | Prompt tokens (~) | + completion tokens (~) | Total tokens (~) |
|---|---|---|---|---|
| 12 | 5,042 | 1,363 | 178 | 1,541 |
| 15 | 5,777 | 1,561 | 223 | 1,784 |
| **20 (M9's)** | **7,002** | **1,892** | **297** | **~2,190** |
| 25 | 8,227 | 2,224 | 372 | 2,596 |

**Decision: keep `DEFAULT_BATCH_SIZE = 20`, unchanged.** The arithmetic says
20 is not actually tight — ~2,190 tokens total is comfortable margin under
any context window this model would plausibly run at.

**But the real risk this task's question was pointing at was not the
model's native context — it was `num_ctx`.** `ollama show
qwen3-coder:30b-a3b-q4_K_M` reports the model's native context length as
**262,144** `[V]`, far larger than anything relevant here. What matters is
Ollama's *per-request* `num_ctx`, which the `/api/generate` endpoint applies
when the caller doesn't specify one — and **M9 never sets it** (`call_ollama`
only sets `temperature`). I did not find a server-level override either:
`systemctl show ollama --property=Environment` has no `OLLAMA_CONTEXT_LENGTH`
`[V]`, and `ollama -v` reports **0.22.1** `[V]` — I did not track down that
exact version's undocumented default rather than guess at it, because it
doesn't matter: **this module does not rely on it.**
`monitoring/relevance_classifier.py` sets `"num_ctx": 8192` explicitly in
every Ollama call's `options` — a fixed, generous, known budget, roughly 4x
the ~2,190-token estimate for a 20-market batch. **The adjustment this task
asked for was made to `num_ctx`, not to batch size** — batch size didn't
need to shrink once the actual binding unknown (an unset runtime default)
was fixed directly. This is a latent gap in M9 itself (it has been running
for some unknown, unverified `num_ctx` this whole time) — noted here, not
fixed there; M9 is out of scope for this task.

---

## 4. THE WRAPPER — interface and error handling

```python
def classify_batch(markets: list[dict], *, batch_size: int = 20, model: str = OLLAMA_MODEL) -> list[ClassificationResult]
```

- Input dict: `{market_id, title, market_slug, event_slug, event_title}`.
  Slug fields may be `None`/`""` (e.g. a market the slug fetch marked
  `not_found`); rendered as empty in the prompt, title-only classification
  still proceeds.
- `ClassificationResult`: frozen dataclass, `{market_id, category,
  confidence, raw_response}`. **`category=None` is a distinct outcome from
  `category="NotRelevant"`** — `None` means the classification *failed*
  (network error, unparseable JSON, an id the response omitted, or a
  category/confidence value outside the fixed vocabulary); `"NotRelevant"`
  means the model made an actual negative call. Conflating these would let
  a silent failure masquerade as a real decision — stated explicitly in the
  dataclass's own docstring so a caller can't miss it.
- **Writes nothing.** No `sqlite3` import, no DB connection, no
  `UPDATE`/`INSERT`/`DELETE` anywhere in the module — confirmed by grep
  (§5) rather than asserted from having written it carefully.
- Batches internally at `batch_size` (default 20, §3); one `_call_ollama`
  per batch. A whole-batch failure (network/parse) marks every market in
  that batch as `category=None` with a distinguishing `raw_response` — it
  does not raise, and does not silently drop markets (verified in §4.1
  below, chunking a 45-market list into 20/20/5 still returns 45 results).

### 4.1 Non-network correctness checks (mocked Ollama, no LLM calls)

Ran against a fake `_call_ollama` to isolate the wrapper's own logic from
model behavior:

- **Chunking:** 45 synthetic markets, `batch_size=20` → 3 Ollama calls
  (batch sizes 20/20/5 confirmed by inspecting the mocked call arguments),
  **45 results returned** — no market dropped across a batch boundary.
- **Network/call failure** (`_call_ollama` returns `None`): every market in
  the batch gets `category=None`, `raw_response="ERROR: Ollama request
  failed (see log)"`.
- **Malformed JSON** (`"not json at all"`): `category=None`,
  `raw_response` contains `"unparseable response: ..."`.
- **Out-of-vocabulary category** (model returns `"category": "Unknown"`,
  outside `{Geopolitics, Elections, NotRelevant}`): `category=None`,
  `raw_response` contains `"out-of-vocabulary response: ..."` — the wrapper
  does **not** silently coerce an unexpected value into a valid one.
- **Missing id** (model's array omits an entry for a market it was shown):
  `category=None`, `raw_response` contains `"missing from Ollama response
  array"`.

All four error paths return a `ClassificationResult` (never raise, never
drop the market silently) and are distinguishable from each other and from
a genuine `NotRelevant` by `raw_response` text.

---

## 5. WRITE-PATH VERIFICATION (nothing touched)

```
$ grep -inE "sqlite3|UPDATE |INSERT |DELETE |conn\.|cursor\(" monitoring/relevance_classifier.py monitoring/relevance_classifier_prompt.py
monitoring/relevance_classifier.py:31: (docstring text only, no code matches)
monitoring/relevance_classifier.py:32: (docstring text only, no code matches)
monitoring/relevance_classifier.py:37: (docstring text only, no code matches)
```
All three matches are inside the module's own docstring explaining that it
has no DB code — no actual `sqlite3`/`UPDATE`/`INSERT`/`DELETE`/`conn.`/
`cursor(` token exists outside prose. `[V]`

Before and after building/running the smoke test, confirmed unchanged:
`markets.category` distribution, `category_source` counts (`legacy` still
exactly 11,967, no new value), and `category_classification_log` row count
(**0**, unchanged) `[V]`.

---

## 6. INFORMAL SMOKE TEST — NOT THE GATE

**This is not gate data and not a substitute for the formal §3.8-3.11 run.**
Six markets, hand-constructed independently of
`brain/decisions/gate-sets-2026-09-01/` (none of these `market_id`s or
titles appear in `set_a.csv`/`set_b.csv`/`set_c.csv`/`labels.csv`), run
through the real `classify_batch()` against the live Ollama endpoint —
purpose was to confirm the wrapper parses a real response correctly and the
prompt produces sane output at all, not to measure accuracy:

| market_id | constructed as | classifier said | confidence |
|---|---|---|---|
| `smoke-crypto-1` | obvious NotRelevant (crypto up/down template) | NotRelevant | HIGH |
| `smoke-sports-1` | obvious NotRelevant (sports O/U line) | NotRelevant | HIGH |
| `smoke-election-1` | obvious Elections (governor race) | Elections | HIGH |
| `smoke-geo-1` | obvious Geopolitics (ceasefire) | Geopolitics | HIGH |
| `smoke-boundary-1` | Geo/Elec boundary (tariff policy) | Elections | HIGH |
| `smoke-missing-slugs-1` | title-only, all slug fields `None` (UN sanctions) | Geopolitics | HIGH |

All six calls returned well-formed JSON on the first attempt, all six
`market_id`s round-tripped correctly, no parse failures, no out-of-vocabulary
values, and the four "obvious" cases matched their intended category. The
boundary case and the missing-slug-fields case both produced sane
in-vocabulary answers without erroring, which is what this smoke test was
checking for — it says nothing about whether "Elections" was the *correct*
side of the tariff boundary call, that judgment is the gate's job (§3.10),
not this task's.

**Smoke-test script location:** scratchpad only
(`smoke_test_relevance_classifier.py`), not committed — it is a throwaway
harness, not a project test. Re-running it is one `python3` invocation
importing `monitoring.relevance_classifier.classify_batch` with a
hand-written market list; nothing about it depends on gate data.

---

## 7. STATE FOR NEXT SESSION

The classifier's four pieces are now: schema migration, deterministic
pre-filter, both slug fetches (all four shipped prior to this task), and
now the LLM stage (prompt + wrapper, this task). **Not built yet, and not
part of this task:**

a. **The write path** — the guarded `UPDATE markets SET category=...,
   category_source=..., last_checked=... WHERE category='Unknown'` +
   mirrored `trades.market_category` write, per design §2.6. This module
   returns `ClassificationResult`s; nothing calls a write with them yet.
b. **The keyset-cursor batch driver** — a script that pages `Unknown`
   markets by `market_id > :last_market_id` (design §2.5), joins to
   `relevance_slug_staging` for the four input fields, calls
   `classify_batch()`, and (once (a) exists) writes results plus a
   `category_classification_log` row per decision, including
   `NotRelevant` ones.
c. **The formal gate run (§3.8-3.11 of the design)** — recall against the
   11,967 pre-classified, precision against `set_a`/`set_c`, disagreement
   adjudication against a random 50, run **once**, thresholds fixed
   already. This task deliberately did not touch it. `spotcheck_blind.csv`
   is Oscar's separate blind check, also still untouched (confirmed at
   session-start, 2026-09-03-status-check equivalent — see prior status
   check).
d. Only after (c) passes: repoint `daily_maintenance.py`'s category step
   from M9 to this module (design §2.8), retire M9.

**Be accurate about what exists:** two new files, zero classifications
recorded, zero gate evidence generated. The prompt and wrapper are built
and smoke-tested on invented examples; whether they clear the pre-registered
thresholds is completely unknown and is exactly what the next task
(the formal gate run, b+c above) is for.
