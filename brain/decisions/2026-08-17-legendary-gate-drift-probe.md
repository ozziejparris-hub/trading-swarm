# The six canonical-definitions-drift violations: characterisation

**Date:** 2026-08-17
**Scope:** read-only on code and DB. No edits, no fixes, nothing repointed to `cd.LEGENDARY_GATE_WHERE`. Characterisation only — remediation is a separate decision.

**Trigger:** `daily_maintenance.py` step 8 (`check_canonical_definitions.py --alert`) has failed for several runs with 6 violations: a hardcoded `geo_elo >= 2175` in each of `trader_skill_metric_v2.py` / `v2b` / `v2c` / `v2d` / `v2e` / `v2f`, instead of `cd.LEGENDARY_GATE_WHERE`.

---

## Bottom line

**None of the six affects the result of record.** All six are the identical statement — `legendary = set(r[0] for r in conn.execute("SELECT address FROM traders WHERE geo_elo >= 2175"))` — and in every one of the six files, `legendary` is used **only** to compute an overlap-count comparison statistic against a population that is itself defined independently (by `shrunk_mean` percentile/significance/effect-size thresholds), never to select, exclude, or gate any trader/position/market that enters a cohort, a placebo match, an edge computation, or a CI. Verified individually per site below — not assumed from the general pattern yesterday's dependency trace observed. No FILTERING use was found, so the stop-and-report trigger in this task's instructions was never hit.

They are also **not** stylistic near-misses of the canonical gate: `cd.LEGENDARY_GATE_WHERE` uses a different column (`geo_elo_active`, time-decayed) and three additional required conditions the six sites omit entirely. And they were **not** carried in from before geo_elo was known broken — git blame puts all six at 2026-08-15, written in the same 3.5-hour session as the v2→v2f rebuild, *after* that same session's own audits (14:24–14:37 UTC) had already established geo_elo unfit for purpose (chain starts 16:02 UTC).

---

## Per-site table

| Site (file:line) | Statement | Classification | What it feeds |
|---|---|---|---|
| `trader_skill_metric_v2.py:390` | `legendary = set(r[0] for r in conn.execute("SELECT address FROM traders WHERE geo_elo >= 2175"))` | **REPORTING** | `legendary_overlap()` computes `{n_legendary, n_top_new, overlap, overlap_fraction}` — top-N-by-`shrunk_mean` vs. LEGENDARY, `len(legendary)`-sized. Stored in `findings['legendary_overlap']` (line 628), printed under `=== ITEM 9 ===`, written to `--json_out` if passed. Not persisted to any DB table in this script. |
| `trader_skill_metric_v2b.py:613` | same | **REPORTING** | `item9` dict (`n_legendary`, `overlap`, `overlap_fraction`), printed as `[item 9] LEGENDARY (n=...) overlap with top-...`, plus a `[cross-check:*]` print per alternate weighting. Persisted via `persist_findings()` → **`metric_v2b_findings`** table. |
| `trader_skill_metric_v2c.py:506` | same | **REPORTING** | `objective3['legendary_overlap']` / `n_legendary`, printed as `[item 9] LEGENDARY (n=...) overlap with top-... (v2b position-weighted got 7/81)`. Persisted to **`metric_v2c_findings`** (via the script's own `args.persist` block). |
| `trader_skill_metric_v2d.py:418` | same | **REPORTING** | `legendary_overlap` / `legendary_overlap_fraction` columns, computed *after* each `candidates[name]` cohort is already fixed by percentile/significance/effect-size thresholds on `shrunk_mean` — `legendary` only intersects a cohort that's already fully defined without it. Persisted to **`metric_v2d_threshold_candidates`**. |
| `trader_skill_metric_v2e.py:437` | same | **REPORTING** | Same pattern as v2d: `legendary_overlap` / `legendary_overlap_fraction` computed against already-fixed `candidates[name]` sets. Persisted to **`metric_v2e_threshold_candidates`**. |
| `trader_skill_metric_v2f.py:380` | same | **REPORTING** | Printed once: `overlap with LEGENDARY: {len(intersection_traders & legendary)}/{len(legendary)}` (line 385). `intersection_traders` — the actual Objective-1 cohort, and the population `build_presplit_cohort()` derives the OOS cohort from — is fully computed *before* this line from `sig95_full`/`shrunk_mean`/`EFFECT_BAR` alone. `legendary` is not referenced anywhere else in the file; not written to any `metric_v2f_*` table. |

**`metric_v2d_threshold_candidates` and `metric_v2e_threshold_candidates` have no downstream reader** — `grep -rn "metric_v2d_threshold_candidates\|metric_v2e_threshold_candidates" scripts/*.py` matches only each table's own `CREATE`/`INSERT` in its own file. Nothing queries them back, including `v2f.py`, which reproduces v2e's cohort by calling the *imported functions* directly (`per_trader_t_ci`, `compute_cap5_metric`, etc.), not by reading v2e's persisted table. `metric_v2b_findings` / `metric_v2c_findings` are likewise write-only diagnostic tables for their own iteration, not consumed by v2f.

**Does the statistic appear in the persisted `metric_v2f_*` tables or the 08-15 handover?** Not in `metric_v2f_*` (checked: `metric_v2f_cost_floor`, `metric_v2f_intersection_cohort`, `metric_v2f_oos_result` — none contain a `legendary`/`geo_elo`-derived column). It **does** appear in the handover narrative, as a critique of the old tier rather than an input: `brain/decisions/MASTER_HANDOVER_2026-08-15.md` line 118 — *"LEGENDARY overlap with the new metric's equivalent tier: 15/81 (18.5%). The current production tier has little in common with what a defensible metric calls the top tier."* This is exactly the kind of comparison-only role the code shows — used to argue the new metric's top tier and the old LEGENDARY tier disagree, not folded into any computed figure.

---

## (e) Does `cd.LEGENDARY_GATE_WHERE` match the hardcoded literal?

**No — different column, and three missing conditions. Not a stylistic violation.**

Canonical (`monitoring/column_definitions.py:123-128`):
```python
# LEGENDARY gate (WHERE fragment).
#
# CRITICAL: uses geo_elo_active, NOT geo_elo. Several legacy scripts use geo_elo
# for the LEGENDARY check; that is wrong because it ignores time-decay and
# overstates dormant traders' tier indefinitely. This is the canonical form.
LEGENDARY_GATE_WHERE = (
    f"geo_elo_active >= {GEO_ELO_LEGENDARY}"       # 2175.0
    f"\n  AND geo_accuracy_pool = 1"
    f"\n  AND research_excluded = 0"
    f"\n  AND bot_type IS NULL"
)
```
i.e. **`geo_elo_active >= 2175 AND geo_accuracy_pool = 1 AND research_excluded = 0 AND bot_type IS NULL`**.

The six sites: **`geo_elo >= 2175`** — bare, no other conditions, and using `geo_elo` (raw/undecayed) rather than `geo_elo_active` (time-decayed). The canonical module's own comment names this exact substitution — wrong column, ignoring time-decay, overstating dormant traders — as a known "legacy scripts" failure mode. The six sites' `legendary` set can include research-excluded traders, bot-suspects, traders outside `geo_accuracy_pool`, and dormant traders whose decayed `geo_elo_active` has since fallen below 2175 while their un-decayed `geo_elo` has not. Because all six uses are REPORTING-only (above), this doesn't touch the OOS population — but it does mean every "LEGENDARY overlap" percentage printed or persisted by these six sites, including the 15/81 figure quoted in the 08-15 handover, is measured against a *non-canonical, somewhat inflated* reference set, not the tier the rest of the codebase means by LEGENDARY.

---

## (f) Git blame — predate or postdate the 08-15 rebuild?

**All six were written the same day as, and after, the audits that established geo_elo unfit — not carried-in scaffolding.**

| Site | Commit | Timestamp (UTC) |
|---|---|---|
| v2.py:390 | `5e93131e` | 2026-08-15 16:02:07 |
| v2b.py:613 | `62603f94` | 2026-08-15 16:14:34 |
| v2c.py:506 | `ad6ed9ca` | 2026-08-15 16:43:43 |
| v2d.py:418 | `57d38bb7` | 2026-08-15 17:03:44 |
| v2e.py:437 | `511858cd` | 2026-08-15 19:16:10 |
| v2f.py:380 | `eaeabbc7` | 2026-08-15 19:35:22 |

Preceding that same day, the audits that established geo_elo unfit for purpose:
```
13:24  f1d2555  Layer 0 forward-accuracy test — does geo_elo predict individual trader skill?
14:02  77017a0  Layer 0b/0c — deconfound geo_elo forward-accuracy test
14:24  f7695c0  price-convention audit — test geo_elo formula for the Layer 0b sign error
14:37  57ed326  elo formula audit — quantify SELL contamination, double-counting, unweighted size
14:37  5170548  geo_elo derivation audit — quantify structural issues beyond the sign bug
16:02  5e93131  feat: trader skill metric v2 — entries/exits edge with EB shrinkage, alongside geo_elo   ← first of the six
```
The v2 chain begins over an hour after the audits finished. Each subsequent file (v2b→v2f) is an iteration on the previous one, and this one line was carried forward unchanged, copy-paste style, through all six — each new file's "LEGENDARY overlap" diagnostic reusing the same query rather than being re-derived. It reads as a deliberate (if imprecisely-coded) reporting comparison against the known-old tier system, written with full knowledge that `geo_elo` itself was already discredited — not an oversight inherited from before that was known.

---

## (g) What the drift check actually matches on

**AST-based, on the SQL string text — it has no way to tell FILTERING from REPORTING. Confirmed, not assumed.**

`scripts/check_canonical_definitions.py` runs two independent AST-driven gates:
1. `visit_Compare` — flags a **Python-level** comparison (`geo_elo >= 2175` as actual Python code, not SQL). Doesn't apply here — all six sites are SQL text inside a string, not a Python comparison.
2. `visit_Constant` — for every string constant not a docstring, regex-matches `RE_RAW_THRESHOLD` (`\bgeo_elo(?:_active)?\s*>=\s*(?:2175|1800|1400|1000|500)\b`) combined with `RE_SQL_CONTEXT` (must contain `SELECT|WHERE|UPDATE|INSERT|DELETE|FROM` to avoid matching English prose).

The only exemption from either gate is `_cosmetic()`: true when the string sits inside a call whose function name is in `_LOG_ATTRS = {print, info, debug, warning, warn, error, critical, exception}`. **`conn.execute(...)` is not in that set.** So a SQL string passed to `conn.execute()` is flagged identically whether its result later filters a cohort or only feeds a printed overlap count — the checker has no model of what happens to the query's *result*, only of which function call directly wraps the *string*. This is exactly why all six sites, despite being confirmed REPORTING-only, still fail the check: the check's pass/fail state is a property of the raw source text (is a canonical-shaped SQL threshold string present outside a print/log call), not of the query's role in the computation. **A failing drift-check run therefore does not, by itself, tell you whether a discredited threshold gates anything — that has to be established per-site, as done above.**

---

## Reproducibility

Per-site classification: read `git grep -n "geo_elo >= 2175"` for all six file:line locations, then read each site's full enclosing function plus every downstream use of the `legendary` variable (`grep -n "legendary"` per file) through to its terminal `print`/`findings[...]`/`persist_*` sink. Cross-checked table consumption with `grep -rn "metric_v2d_threshold_candidates\|metric_v2e_threshold_candidates" scripts/*.py`. Predicate comparison: read `monitoring/column_definitions.py` lines 60-135 in full. Git blame: `git blame -L <line>,<line>` per site, cross-referenced against `git log --format="%ai %s"` for the full 2026-08-15 commit sequence. Drift-check mechanism: read `scripts/check_canonical_definitions.py` in full (274 lines). Handover cross-check: `grep -n -i legendary brain/decisions/MASTER_HANDOVER_2026-08-15.md`. No files were modified; no query was run against the DB other than read-only lookups already covered by the git/grep evidence above (this task needed no new DB queries beyond what's already documented in the two prior investigations).
