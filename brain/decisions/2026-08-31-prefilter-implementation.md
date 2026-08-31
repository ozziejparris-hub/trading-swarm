# Relevance-Classifier Deterministic Pre-Filter — Implementation

**Date:** 2026-08-31. **Type:** code, read-only against production (no writes of any
kind).
**Design:** `2026-08-31-relevance-classifier-design.md` (e601648) §1.2, §1.3, §2.4, §2.5.
**Schema:** first-repo 26ba190.
**Code (first-repo):** `monitoring/relevance_prefilter.py`,
`tests/test_relevance_prefilter.py`, `scripts/measure_prefilter_coverage.py`.
**Tagging:** `[V]` verified this session.

---

## SUMMARY

- **`prefilter(title) -> "EXCLUDE" | "RESIDUAL"`** — a pure function, title-only, no
  DB / network / writes. `EXCLUDE` = matches a documented non-geo template family;
  `RESIDUAL` = goes to the LLM stage. RESIDUAL is the safe default.
- **No positive ELECTION_TOKENS / GEOPOLITICS_TOKENS list** — stated in the module.
  Positive classification is the LLM's job (a positive list is what M9 has and it
  over-selects 2–3×).
- **13 families, 55 patterns**, every one drafted from a committed decision doc or the
  implementation-task prompt. **Zero live population titles were inspected while
  drafting** (see §Provenance).
- **Coverage:** **EXCLUDE 87.6 %** on the 214,516 swept Unknown markets and **87.6 %**
  on the 353,048 unswept — **~4.6 pp above** the design's ~83 % prior. Reported as
  found; the lists were **not** adjusted toward the prior (§Coverage).
- **Residual:** swept **26,506** → **~9.9 h** Qwen (design assumed ~36 k → ~15 h);
  unswept **43,837** → ~16.4 h.
- **Tests: 63/63 pass**, including the required substring-trap EXCLUDEs, the four
  documented true-positive RESIDUALs, and a non-vacuity demonstration (T7: with the
  pattern list emptied, the trap cases come back RESIDUAL).

---

## THE TOKEN LISTS AND THEIR PROVENANCE

`EXCLUDE_PATTERNS` is a module-level list of `(family, compiled_regex)` tuples, each
commented with its family and a provenance code. Provenance codes:

| code | source (committed) |
|---|---|
| **[D1]** | `2026-08-31-relevance-classifier-design.md` §1.2 — family table + the explicit title-token list (`up or down`/`updown`, `temperature`, `: O/U `, `Spread:`, ` vs. `) |
| **[D2]** | `2026-08-30-category-classifier-investigation.md` — §Part-3 400-title sample composition (crypto 44.5 %, weather 13 %, sports/esports 27.5 %), §alt-route(2) "four rigid templates" (`<ASSET> Up or Down -`, `Will the highest/lowest temperature in`, ` vs. ` + O/U\|Spread:\|Moneyline\|Both Teams to Score\|end in a draw, `Set N Winner:` / `(BO3)`/`(BO5)`), and the skip-sample rows (`Spread: Warriors (-3.5)`, `Kel'el Ware: Rebounds O/U 6.5`, `Will CD Palestino win on 2026-05-26?`, `Will Micron … (MU) hit (LOW) $960`, …) |
| **[D3]** | `monitoring/market_filter.py` / `scripts/detect_insider_activity.py` `_EXCLUSION_KEYWORDS`, as enumerated in `2026-08-31-geo-scoping-inventory.md` (M8/M11) and `2026-08-31-local-llm-consolidation-assessment.md` §2.10 — sports leagues/tournaments, stock tickers/earnings/indices, gold/oil, `oscars`/`grammy`/`billboard`/`box office`, `jesus`/`rapture`/`antichrist`/`second coming` |
| **[P]** | the implementation-task prompt itself — the four required-EXCLUDE strings ("Presidents Cup", "China Grand Prix", Warsaw temperature, Warriors spread) |
| **[D4]** | `2026-08-30-geo-backlog-and-category-reach.md` — "Eurovision" as a documented non-thesis market |

### Families

| # | family | fires on | provenance |
|---|---|---|---|
| 1 | `crypto_updown` | `\bup or down\b` | [D1][D2] |
| 2 | `crypto_price_level` | coin name + comparison + number (`ethereum … above $2,500`) | [D1] |
| 3 | `weather` | `\b(highest\|lowest\|high\|low) temperature in\b`, `temperature in … be`, rain/snow totals | [D1][D2] |
| 4 | `sports_line` | `O/U \d`, `over/under`, `^Spread:`, `(-3.5)` / `(+1.5)` parenthetical, `moneyline`, `both teams to score`, `end in a draw`, `^Exact Score:`, `^Games Total: O/U`, quarter/half + line word, `corners` + line | [D1][D2] |
| 5 | `sports_prop` | `: rebounds\|points\|goals\|shots\|… (O/U)? \d`, `: 3+ goals` | [D2] |
| 6 | `sports_match_date` | `\bwin on \d{4}-\d{2}-\d{2}\b` | [D2] |
| 7 | `sports_set_map` | `\b(set\|map\|game\|frame\|leg\|end) \d+ winner\b`, `total sets O/U`, `set/map handicap` | [D1][D2] |
| 8 | `esports` | title starts with a game name (`LoL:`, `Counter-Strike:`, `Dota 2:`, `Valorant:`, `MLBB:`, …), `(BO3)`/`(BO5)`, `Map N Winner` | [D1][D2] |
| 9 | `sports_league` | `\b`-anchored league codes (`nba`, `nfl`, `epl`, `atp`, `wta`, `formula 1`, …) and multi-word tournament names (`super bowl`, `champions league`, **`grand prix`**, **`presidents cup`**, `wimbledon`, `olympics`, `eurovision`, `ballon d'or`, …) | [D1][D3][D4][P] |
| 10 | `stocks` | `(TSLA) hit\|finish\|close…`, `finish (the) week (of)`, `hit (LOW\|HIGH) $`, `close(s) at\|above\|below $`, earnings vocabulary, `S&P 500 / Nasdaq / QQQ / VIX … above\|below\|hit \d` | [D2][D3] |
| 11 | `commodities` | `(WTI\|Brent)? crude oil`, `price of gold\|oil\|silver…`, `gold … close\|price\|above\|below\|between $\d`, `natural gas … above\|below\|settle`, rodeo events | [D1][D3] |
| 12 | `entertainment` | `best actor\|picture\|director\|rock album\|game of the year\|…`, `academy awards?\|emmy\|grammy\|golden globe\|bafta\|billboard hot 100/200\|rotten tomatoes\|box office\|opening weekend\|spotify streams\|most-streamed` | [D2][D3] |
| 13 | `novelty_religion` | `the second coming`, `the rapture`, `antichrist`, `will jesus … return`, `will the world end`, `alien(s) … contact`, `bigfoot`, `loch ness monster` | [D3] |

### Exact list of market_ids inspected during drafting

**NONE.** Every pattern traces to a committed decision doc or the task prompt (table
above). No `SELECT title …` against the live DB, no sampling, no per-title inspection
was done to draft or refine the lists. The gate's 200-market sample of pre-filter
exclusions (design §3.9) is therefore uncontaminated by construction.

The coverage measurement (§Coverage) **does** run `prefilter` over every title in both
populations, but `scripts/measure_prefilter_coverage.py` prints **aggregate counts
only — never a title** — and the lists were drafted and frozen *before* it ran. It
was executed **once**; the lists were **not** iterated against its output.

---

## SUBSTRING-TRAP AVOIDANCE

The design (§1.2) and the task name three bare-substring failures of M9's positive
list: `war` ⊂ "Warsaw"/"Warriors"/"Warhawks", `president` ⊂ "Presidents Cup",
`china` ⊂ "China Grand Prix". This module avoids them:

1. **It carries no `war` / `president` / `china` token at all.** There is no positive
   list — the module only *excludes* template families. A test (`T5`) asserts the
   literals `war` / `president` / `china` do not appear as pattern strings in the
   source.
2. **Every pattern is `\b`-anchored or structural**, never a bare substring:
   `\b(highest|lowest) temperature in\b`, `\bo\s*/?\s*u\s*\d`, `\([+-]\d+(\.\d+)?\)`,
   `\bup\s*or\s*down\b`, `\(\s*bo\s*[1357]\s*\)`, `\bwin on \d{4}-\d{2}-\d{2}\b`.
   "Warsaw" matches the `weather` family via `temperature in`; "Warriors" matches
   `sports_line` via `^Spread:` / `(-3.5)` — neither via anything resembling `war`.
3. **"Presidents Cup" and "China Grand Prix" are caught by the two-word phrases**
   `\bpresidents cup\b` and `\bgrand prix\b` in `sports_league`, not by any
   single-word token. `T1` asserts both EXCLUDE; `T5` asserts the attributed family
   is `sports_league`.
4. **Tokens with a plausible geopolitics collision were deliberately omitted:** bare
   `\bf1\b` (≈ "F1 visa"), bare `us open` (≈ "US open its borders"), bare `strike`
   (labour / military strike). `formula 1` / `grand prix` / the golf majors cover the
   motorsport and golf cases without the collision.
5. **Bare "A vs. B" is RESIDUAL, not EXCLUDE.** ` vs. ` alone (no O/U / spread / score
   co-signal) would risk excluding "US vs. Iran". `sports_line` requires the
   co-signal; a bare head-to-head like "Seattle Mariners vs. Texas Rangers" goes to
   the LLM. This costs some coverage (below) and is the intended trade.

---

## COVERAGE (read-only, `scripts/measure_prefilter_coverage.py`) `[V]`

| population | total titles | EXCLUDE | RESIDUAL |
|---|---:|---:|---:|
| **swept Unknown** (`category='Unknown' AND resolution_evidence_source='clob'`) | 214,516 | **188,010 (87.6 %)** | **26,506 (12.4 %)** |
| **unswept Unknown** (`category='Unknown' AND (resolved=0 OR resolved IS NULL)`) | 353,048 | **309,211 (87.6 %)** | **43,837 (12.4 %)** |

### vs the design's ~83 % prior — reported, not adjusted

Coverage came out **87.6 %**, ~**4.6 pp above** the design's ~83 % (§1.2's "crude
title-only bucketing" figure of 177,978 / 214,516). Per the task instruction this is
**reported as found, not tuned toward the prior** — the lists were drafted once from
the documented families and measured once.

Likely reason for the gap: the §1.2 prior appears to have counted only the four
"rigid templates" (crypto up/down, temperature, ` vs. `+O/U, `Set N Winner`/`BO*`).
This module adds `sports_league` (leagues + tournaments), `stocks`,
`sports_match_date` (`win on YYYY-MM-DD`), `sports_set_map`, `entertainment`,
`commodities`, `novelty_religion` — all documented in [D2]/[D3]/[D4] — which together
account for ~14 % of exclusions (below). The direction (higher, not lower) means the
pre-filter is **not** discarding more than the prior expected on the template side;
it is recognising more documented template families. Whether any of the extra
exclusions are false (a real geo/elec market wrongly EXCLUDEd) is exactly what the
design's §3.9 pre-filter-false-exclusion gate (≤ 0.5 % of 200) measures — **not run
here.**

### Per-family EXCLUDE breakdown

| family | swept count | % of EXCLUDE | unswept count | % of EXCLUDE |
|---|---:|---:|---:|---:|
| `crypto_updown` | 86,538 | 46.0 % | 129,059 | 41.7 % |
| `sports_line` | 37,806 | 20.1 % | 74,433 | 24.1 % |
| `weather` | 25,380 | 13.5 % | 37,219 | 12.0 % |
| `crypto_price_level` | 8,424 | 4.5 % | 13,272 | 4.3 % |
| `sports_set_map` | 6,661 | 3.5 % | 10,883 | 3.5 % |
| `sports_match_date` | 6,316 | 3.4 % | 14,288 | 4.6 % |
| `sports_league` | 5,691 | 3.0 % | 10,235 | 3.3 % |
| `esports` | 5,126 | 2.7 % | 9,967 | 3.2 % |
| `stocks` | 4,364 | 2.3 % | 6,494 | 2.1 % |
| `sports_prop` | 1,036 | 0.6 % | 2,196 | 0.7 % |
| `entertainment` | 619 | 0.3 % | 1,115 | 0.4 % |
| `commodities` | 49 | 0.0 % | 47 | 0.0 % |
| `novelty_religion` | 0 | 0.0 % | 3 | 0.0 % |

**Nothing fires suspiciously.** `crypto_updown` at 46 % matches [D2]'s 44.5 % crypto
share; `weather` at 13.5 % matches [D2]'s 13 %; the sports families sum to ~35 % vs
[D2]'s 27.5 % sports/esports (the excess is `sports_league` + `sports_match_date` +
`stocks`, all documented). `commodities` (49) and `novelty_religion` (0) fire almost
never — expected; they are small documented families kept for completeness, not
coverage drivers. No family is a large silent contributor that would warrant a
second look.

### Residual size → LLM-stage cost

| population | residual | batches (÷20) | ~Qwen hours (×27 s) |
|---|---:|---:|---:|
| swept | **26,506** | 1,326 | **~9.9 h** |
| unswept | **43,837** | 2,192 | **~16.4 h** |

The design (§2.4) assumed ~36 k swept residual → ~15 h. Actual is **26.5 k → ~9.9 h**
— the cascade is **cheaper than designed** because coverage is higher than the ~83 %
prior. §2.4's caveat ("if the pre-filter only safely removes ~60 %, residual grows
toward ~32 h") is the opposite of what happened. The one-time Gamma slug fetch for
the residual (design §1.1: ~batched, ~1.3 s/req) is ~1,300–2,200 requests ≈ under an
hour, unchanged in shape.

---

## TESTS (`tests/test_relevance_prefilter.py`) `[V]`

**63 tests, 63 pass, 0 fail.**

| group | asserts |
|---|---|
| **T1** | the four documented substring-trap titles EXCLUDE (Warsaw temp, Warriors spread, Presidents Cup, China Grand Prix) |
| **T2** | the four documented true-positives are RESIDUAL (`paris-mayoral-election-runoff`, `sachsen-anhalt-parliamentary`, `usisrael-strikes-iran`, `ny-10-house`) |
| **T3** | one representative documented title per family EXCLUDEs (20 titles, all 13 families) |
| **T4** | 12 documented geo/elec titles (Romanian presidential, Florida Governor nominee, Russia–Syria base, US government shutdown, Russia×Ukraine ceasefire, Trump tariff, Vaughan mayoral, Haiti elections, Israel–Lebanon, "Trump say America First", US–Iran peace deal, Bulgarian presidential) all RESIDUAL |
| **T5** | trap EXCLUDEs attribute to the documented family (`weather` / `sports_line` / `sports_league`), and the source contains no `war` / `president` / `china` pattern literal |
| **T6** | `None` / `""` / whitespace / non-str → RESIDUAL |
| **T7** | **non-vacuity demonstration** — with `EXCLUDE_PATTERNS` monkey-patched to `[]`, all four T1 trap titles come back RESIDUAL (proving the filter, not the assertions, does the work), then the list is restored and Warsaw EXCLUDEs again |

`run_tests.py` full suite (`--skip=test_behavioral_integration.py`, the documented
auto-hang): **18 files run, 17 passed, 1 failed.** The new
`test_relevance_prefilter.py` → **PASS (63/63)**. The one failing file is
`test_backtest_window_population.py` (5 tests) — the **pre-existing** hardcoded-count
reconciliation drift, identical to the baseline established in
`2026-08-31-classifier-schema-migration.md` §f, unrelated to this change.
**No new failure.**

---

## KNOWN RESIDUAL RISKS (named, not chased — the §3.9 gate will measure them)

- **`\([+-]\d+(\.\d+)?\)`** (point-spread parenthetical) is broad. A geo/elec title
  with a parenthetical signed number (e.g. "… GDP (-2.5) …") would be wrongly
  EXCLUDEd. Judged rare; the §3.9 pre-filter-false-exclusion gate (≤ 0.5 % of 200)
  is the check.
- **`\bwin on \d{4}-\d{2}-\d{2}\b`** assumes ISO-date "win on" is always a single
  sports fixture. A hypothetical "Will Party X win on 2026-05-26?" election phrased
  that exact way would be EXCLUDEd. Not seen in any documented sample (elections read
  "win the 20xx … election"); flagged.
- **`sports_league` "eurovision" / "ballon d'or"** are competitive-event exclusions
  filed under a family named "sports_league" — the name is a slight misnomer; the
  EXCLUDE decision is correct.
- **Bare "A vs. B"** (no line co-signal) is RESIDUAL by design — a coverage loss, not
  a false-exclusion risk. It inflates the residual (and LLM cost) rather than risking
  a wrong EXCLUDE.
- Title-only: the design's `event.slug` / `event.title` inputs are not consulted here
  (they need a Gamma fetch). Adding them can only raise coverage, so 87.6 % is a
  lower bound for the full design pre-filter.

---

## WHAT WAS NOT DONE (scope)

- No positive `ELECTION_TOKENS` / `GEOPOLITICS_TOKENS` list — deliberate (module
  docstring).
- No LLM stage, no prompt.
- No validation gate run, no gate sample drawn.
- No writes: no `category`, no `category_source`, no `category_classification_log`
  rows. `monitoring/monitor.py`, `scripts/backfill_market_categories.py` (M9),
  `scripts/daily_maintenance.py` untouched.
- The lists were drafted once and measured once; not tuned to a coverage target.
