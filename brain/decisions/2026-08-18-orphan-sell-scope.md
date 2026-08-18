# 2026-08-18: scoping the orphan-SELL drop against the actual result-of-record populations

Read-only. No repair to `position_tracker.py`, no re-ingestion, no FIFO
re-run against production, no recomputation of the thesis result. Every
claim tagged **[V]** (verified — command/query/file:line given) or **[I]**
(inferred/plausible, explicitly marked). Unverifiable points are stated in
place with what would settle them, per the standing instruction (memory:
`feedback_verify_dont_propagate.md`).

Committed script: `scripts/characterize_orphan_sell_scope.py` (first-repo).
Re-run: `python3 scripts/characterize_orphan_sell_scope.py`. Writes a
timestamped JSON artifact to `data/characterizations/`, generating params
recorded inside. Today's run: `data/characterizations/orphan_sell_scope_20260818T190319Z.json`.

**Explicit non-goal, honored throughout:** this doc does not estimate the
direction or magnitude of bias on the +0.0316 edge figure. No entry price
exists anywhere for an orphan SELL (established in the prior doc), so any
such estimate would be fabrication. Where a finding below tempts an
estimate, the temptation is named and declined rather than silently
avoided — see Q3 and Q4.

## Background claims, checked before use

- "The reported overlap (7 traders / 26 trade rows / 21 markets) was
  measured against the 295-trader superset, a proxy" — **[V]** confirmed;
  that number is `metric_v2f_intersection_cohort`, the Objective-1
  full-population cohort, not the pre-split-restricted Objective-2 cohort.
  Re-derived against the TRUE populations below, the real numbers are
  smaller and different in shape (Q1).
- "148 traders qualifying at T_split" / "120 surviving into the OOS window"
  / "placebo cohort" — **[V]** all three now have real, reproduced
  membership (not prose figures) via `build_presplit_cohort` and
  `match_control`, v2f's own existing functions
  (`scripts/trader_skill_metric_v2f.py:236,279`), called read-only, capturing
  ID sets only — no new edge/CI value was computed or is reported anywhere
  in this doc. Reproduction: **presplit cohort = 148** (exact match to the
  `2026-08-16-result-of-record-reproducibility-audit.md` figure and to the
  persisted `metric_v2f_oos_result` row), **OOS survivors = 120** (exact
  match to `metric_v2f_oos_result`'s persisted `n_traders=120`), **placebo
  pool = 148** (matches the audit's "148/148 cohort traders matched to
  controls"), **placebo survivors = 108** (persisted value is **110** — a
  2-trader drift, see "Reproduction drift" below).
- "M>=10 distinct markets plus significance-95" qualification criterion —
  **[V]** confirmed directly in code: `M_CHOSEN = 10`
  (`trader_skill_metric_v2f.py:133`), `elig = t_ci[t_ci.n_pairs >= M_CHOSEN]`,
  `sig95 = elig[elig.ci_lo_t > 0]` (`build_presplit_cohort`,
  same file:262-263), plus `EFFECT_BAR = 0.02` on `shrunk_mean` as the
  required secondary filter (line 134, applied at line 266).
- "+0.0316 vs +0.0127" — **[V]** these exist as real, persisted, committed
  production values: `metric_v2f_oos_result` (`kind='cohort'`,
  `point_gap=0.031598...`) and (`kind='placebo'`, `point_gap=0.012707...`),
  spec `SKILLV2F-2026-08-15-v1`, generator commit `eaeabbc`. **[V]** Also
  newly noted, not previously flagged anywhere in this arc's docs: both
  persisted CIs actually *include* zero (`cohort` CI = [-0.0088, 0.0710];
  `placebo` CI = [-0.0210, 0.0461]) — under v2f's own stated verdict logic
  (`thesis_verdict` branches, `trader_skill_metric_v2f.py:429-444`), this
  would print as **NULL, not SUPPORTED**. This doc does not re-litigate that
  verdict (out of scope — the task here is orphan-SELL scoping, not the
  thesis verdict), but it is recorded since it bears directly on how much
  weight "touching the result of record" should carry, and no prior doc in
  this session's chain surfaced it.
- "2026-07-25 to 2026-08-07 outage window" (task prompt's phrasing) —
  **[V]** corrected: the actual box-down window per
  `2026-08-07-session-summary.md:5` is **2026-07-24 21:46 → 2026-08-07
  09:37**, and the zero-trade data gap is **2026-07-25 → 2026-08-06** (13
  full days). The task prompt's dates were close but not exact; both the
  precise box-down window and the tighter zero-trade window are checked
  below (Q6), not the prompt's rounded version.
- "O-37 synthetic-trade quarantine" — **[V]** real, confirmed in
  `2026-07-19-o37-synthetic-market-quarantine.md`: 84 markets, mechanism is
  `markets.flag_reason='synthetic_quarantine_2026-07-19'` layered on the
  existing `trade_gap_flag` exclusion. Checked directly against `flag_reason`
  (not inferred from timestamps) in Q6.

## Reproduction drift (both repos' standing reproducibility rule applied)

| quantity | persisted 2026-08-15 (`eaeabbc`) | reproduced today | drift |
|---|---|---|---|
| presplit cohort n | 148 | **148** | 0 |
| OOS cohort survivors n | 120 | **120** | 0 |
| placebo pool n | 148 | **148** | 0 |
| placebo survivors n | 110 | **108** | **-2** |

**[V]** Three of four counts reproduce exactly. **[I]** The 2-trader drift
on placebo survivors is plausibly explained by `match_control`'s greedy
nearest-neighbour matching drawing on a `elig_pool` (M>=10-eligible, all
traders) whose composition shifts slightly as new trades accrue daily —
the same mechanism the 08-16 reproducibility audit already documented
("explains why the placebo moved more than the cohort" for an analogous
drift). **[U]** Not settled here: which 2 specific traders differ between
the 08-15 run and today's, since the 08-15 run's placebo membership was
never persisted (same standing gap this task partially closes going
forward — today's run *is* persisted, at the JSON path above, so a future
diff is now possible).

## Q1: exact population intersection

Persisted this run (JSON artifact, `q1_intersection` key — full trader-ID
lists there, not reproduced in full here for length):

| population | true n | affected (orphan-SELL) | 
|---|---|---|
| (a) presplit-qualifying cohort (148) | 148 | **4** |
| (b) OOS survivors (120) | 120 | **3** |
| (c) placebo pool (148, matched) | 148 | **6** |
| placebo survivors (108/110) | 108 (today) | **5** |

**[V]** (b) is non-zero: **3 real cohort members who survive into the OOS
window carry orphan-SELL drops in their pre-split trading history.** This
is smaller than the previously-reported proxy figure (7 traders against the
295-superset) and specifically identifies which of those 7 are real vs.
proxy-only: `0x0cb10c40...`, `0xbc54e696...`, `0xe0f1e775...` are the 3 real
OOS-survivor overlaps (all three also appear in the proxy's 7); the proxy's
other 4 (`0x50396e4d...`, `0x635d4ea1...`, `0x8a4ec9c5...`, `0x8f6287a0...`)
are NOT part of the true 120-survivor set — `0x8f6287a0...` is in the true
148 presplit cohort but did not survive to place a post-split position;
the other 3 are not in the true cohort or placebo at all (295-superset
false positives relative to the true Objective-2 population).

## Q2: per-trader materiality

Full table persisted in the JSON artifact (`q2_per_trader_materiality`, 10
rows — the union of all affected traders across a/b/c). Summary:

| trader | populations | presplit markets total / dropped | postsplit positions / dropped |
|---|---|---|---|
| `0x0cb10c40...` | cohort, OOS survivor | 105 / **10** (9.5%) | 82 / **0** |
| `0x8f6287a0...` | cohort only | 143 / **1** (0.7%) | 0 / 0 |
| `0xbc54e696...` | cohort, OOS survivor | 121 / **2** (1.7%) | 1 / **0** |
| `0xe0f1e775...` | cohort, OOS survivor | 228 / **3** (1.3%) | 33 / **0** |
| `0x260d13a4...` | placebo pool+survivor | 82 / **1** (1.2%) | 11 / 0 |
| `0x50396e4d...` | placebo pool+survivor | 33 / **1** (3.0%) | 47 / 0 |
| `0x5c7482fa...` | placebo pool only | 12 / **1** (8.3%) | 0 / 0 |
| `0xb6d39751...` | placebo pool+survivor | 225 / **2** (0.9%) | 31 / 0 |
| `0xcc80d2fe...` | placebo pool+survivor | 38 / **2** (5.3%) | 5 / 0 |
| `0xce5bec63...` | placebo pool+survivor | 21 / **3** (14.3%) | 2 / 0 |

**[V]** Every relevant trader's `postsplit_dropped_markets = 0` — this is
not a coincidence, it is a direct consequence of Q5 below (the entire
161-market population is pre-split by construction). The heaviest
materiality is `0x0cb10c40...` at 9.5% of their pre-split market count
(a true cohort+OOS-survivor member), and `0xce5bec63...` at 14.3% (a
placebo-pool+survivor member) — no trader loses more than ~1 in 7 of their
pre-split markets to this mechanism.

## Q3: qualification-boundary effect

**[V]** 3a (currently-qualifying, near the M>=10 boundary, with drops that
could have changed their qualification or CI): **zero found.** Query:
`t_ci_full` filtered to `n_pairs >= 10 AND ci_lo_t > 0 AND (n_pairs -
dropped_markets) < 10` — empty result.

**[V]** 3b (did NOT qualify, but `n_pairs + dropped_markets >= M_CHOSEN`,
i.e. the raw market-count boundary alone would have been crossed): **2
candidates found**, both from the M>=10-eligible presplit pool:

| trader | current n_pairs | dropped markets | current ci_lo_t | current shrunk_mean |
|---|---|---|---|---|
| `0x0a7aaf83...` | 6 | 13 | -0.234 | -0.0070 |
| `0x2c719eda...` | 9 | 1 | -0.191 | -0.0080 |

**[U] — this is the one genuinely unresolved question in this doc, named
explicitly rather than rounded either way.** Both candidates' CURRENT
significance and effect-size (computed on their existing, non-dropped
markets only) are negative — on the data we can see, neither looks like
they'd have cleared `ci_lo_t > 0` and `shrunk_mean >= 0.02` even with
`n_pairs >= 10`. **The temptation here is to read that negative existing
edge as evidence they wouldn't have qualified even with the missing
markets — that inference is explicitly declined.** It would require
knowing what edge those dropped markets themselves would have contributed,
and that is exactly the quantity established as undeterminable: an orphan
SELL has no entry price anywhere in the DB, so there is no way to compute
what `won - entry_price` would have been for these specific dropped
positions. A trader could in principle have 13 badly-losing visible
markets and 13 well-winning invisible ones — nothing in the data rules
that out. **What would settle it:** re-ingesting the missing BUY trades
from Polymarket's API for these 2 traders' 14 combined dropped markets
(same recoverability path named in the sibling doc's Q6 — in principle
possible, not attempted here per the read-only/no-re-ingestion
constraint) would supply the missing entry prices and let `n_pairs`,
`ci_lo_t`, and `shrunk_mean` be recomputed for real, rather than inferred.

## Q4: placebo exposure differential

**[V]** Real cohort: 4/148 affected = **2.70%**. Placebo: 6/148 affected =
**4.05%**. The placebo is affected at a *higher* rate than the real
cohort, not lower — the reverse of what would indicate the cohort is
being selectively harmed.

**Temptation named and declined:** it would be easy to read "placebo more
affected than cohort" as reassuring evidence that the mechanism is
structural/random rather than cohort-specific, strengthening confidence in
the +0.0316-vs-+0.0127 comparison's validity. That reading is not
supported at this sample size. With counts this small (4 vs. 6 out of 148
each), a two-proportion comparison has essentially no power to distinguish
"truly higher for placebo," "truly equal," or "truly higher for cohort" —
the observed gap is well within noise for n=148 groups at these
prevalences. **The correct statement is: no differential is detected, and
none could be detected reliably at this sample size in either direction.**
This is reported as a genuine null, not upgraded to "confirms no
differential" — see the standing instruction's `feedback_reproducibility_decision_numbers`
note on not treating underpowered ad-hoc comparisons as settled.

## Q5: temporal distribution

**[V]** 205/205 orphan-SELL trades (100%) fall pre-split; 0 post-split.
**This is not an independent empirical finding — it is true by
construction.** `canonical_market_ids`/`v2f_market_ids`
(`scripts/characterize_no_fifo_close_markets.py:45,56`, reused unmodified
here) both filter on `tape_end < window_end` / `tape_end <= window_end`
with `window_end = T_SPLIT`, so the entire 161-market no-FIFO-close
population is pre-split-scoped by definition — asking "pre vs. post split"
of this specific population cannot return anything but 100%/0%. The
genuinely informative temporal question — whether affected markets cluster
recently or represent broad historical residue *within* the pre-split
window — was already answered in the sibling doc's `tape_end_month_buckets`
(spanning mid-2024 through March 2026: broad residue, not recent-onset);
not re-derived here since nothing about that distribution bears on
cohort/placebo scope specifically.

**This result does materially simplify the harm classification**, though:
since zero orphan-SELL drops fall in the post-split measurement window,
this mechanism can **only ever contaminate cohort/placebo *qualification*
(who is counted as being in the 148/120/placebo)**, never the *measured
post-split edge itself* for any trader who does qualify. Every affected
trader's `postsplit_dropped_markets = 0` (Q2) is the direct, verified
consequence of this.

## Q6: interaction with known gaps

**[V]** Zero overlap on every channel checked:
- Box-down window (2026-07-24 21:46 – 2026-08-07 09:37): **0** trade rows.
- Zero-trade data gap (2026-07-25 – 2026-08-06): **0** trade rows.
- Today's 93-minute outage (2026-08-18 14:45:50–16:19:04): **0** trade rows
  (expected — all 205 affected trades are historical/pre-split, none from
  today).
- `data_source = 'gap_recovery_20260811'`: **0** rows.
- `markets.flag_reason` (O-37 or any other quarantine reason) on any of the
  161 markets: **0** rows.

**[V]** None of the 161 markets' orphan-SELL trades were ingested via the
08-11 gap-recovery backfill, none are flagged synthetic/quarantined, and
none fall inside either known outage window. **This means the orphan-BUY
was never ingested for a reason unrelated to any of the infrastructure
gaps this project has already characterized** — consistent with the
sibling doc's Q6 finding that the loss is a genuine "BUY never existed in
the feed" case rather than an infrastructure-outage side-effect, now
confirmed against every specific known-gap channel rather than inferred
generally.

## Verdict

Applying the criteria fixed in advance:

- Intersection with the real result-of-record populations exists and is
  non-zero (Q1: 3 true OOS survivors, 4 true presplit-cohort members).
- 3a (currently-qualifying near-boundary case): **not found** — does not
  trigger MATERIAL-OPEN on its own.
- Q4 (placebo differential): **not found**, and the observed direction (if
  anything) runs opposite to a cohort-specific-harm story, at a sample size
  with no power to distinguish it from noise either way — does not trigger
  MATERIAL-OPEN.
- 3b (invisible would-have-qualified trader): **2 named candidates whose
  status cannot be ruled in or out** — not because the investigation
  stopped short, but because the deciding quantity (their edge on the
  dropped markets) is fundamentally unrecoverable from this DB without
  re-ingesting the missing trades. This is a genuine open case, not a
  resolved negative.

**VERDICT: MATERIAL-OPEN**, triggered specifically and solely by the 3b
residual (`0x0a7aaf83...`, `0x2c719eda...`). Everything else checked —
3a, Q4, and the magnitude of Q1/Q2 exposure among traders who ARE
resolved — points toward small, bounded impact: max per-trader exposure
~14% of pre-split markets, zero post-split contamination anywhere (Q5,
structural), zero overlap with any known infrastructure gap (Q6), and a
placebo that is if anything more exposed than the real cohort (Q4). The
file is not closed only because of the two named 3b traders, and it closes
the moment their missing BUY trades are re-ingested and their qualification
status can be computed for real rather than left as an open question.

## What would close this

1. Re-ingest the missing BUY trades (from Polymarket's API, where
   reachable) for the 14 combined dropped markets belonging to
   `0x0a7aaf83...` and `0x2c719eda...`, recompute their `n_pairs`,
   `ci_lo_t`, and `shrunk_mean` for real, and settle 3b definitively.
2. Persist today's true 148/120/148/108 membership lists (done, this run —
   `data/characterizations/orphan_sell_scope_20260818T190319Z.json`) so a
   future session can diff instead of re-deriving from scratch, closing the
   same kind of gap that made the 08-15 run's placebo membership
   unrecoverable for the drift check above.
3. If the CI-includes-zero observation on both persisted `cohort` and
   `placebo` results (noted under "Background claims") is followed up, that
   is a separate, larger question about the thesis verdict itself — out of
   scope here, flagged for whoever owns that next.
