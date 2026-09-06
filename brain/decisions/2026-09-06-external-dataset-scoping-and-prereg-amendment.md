# External Dataset Scoping + Persistence Pre-Registration Amendment

Two parts. Part 1 answers whether `vgregoire/polymarket-users` can
contribute to the directional-skill persistence test (N=146, first-repo
`1d34ced`). Part 2 amends
[2026-09-06-directional-skill-persistence-prereg.md](2026-09-06-directional-skill-persistence-prereg.md)
(trading-swarm `7743740`) on two points, both blind — no post-split
figure was computed or referenced anywhere in this task. **No verdict on
approving the persistence test is stated here — that remains Oscar's.**

---

## Part 1 — external dataset scoping: verdict is NO

Inspected directly from the parquet files (`pyarrow.parquet`, schema and
column-level stats only — no full-table load, no join against production
tables beyond address-set membership).

**1. Schema — per-TRADER aggregate, not per-position or per-trade.**
Both files: 2,480,104 rows, one row per `user_address`, in both files
(`user_pnl_summary.parquet` and `user_features.parquet` share an
identical address set, confirmed by direct set comparison).
`user_pnl_summary.parquet` holds only summed PnL fields (`pnl_total`,
`pnl_politics`, `pnl_maker_politics`, etc., 56 `double` columns, all
whole-history sums). `user_features.parquet` holds 91 aggregate feature
columns (`n_trades`, `avg_price_traded`, `frac_both_sides`,
`first_trade`/`last_trade` timestamps, etc.) — every column is a
per-trader summary statistic. **There is no market identifier, no
per-event row, no per-position row, anywhere in either file.**

**2. No per-position/per-trade records exist at all**, so the follow-up
question (do they carry market ID, side, entry price, outcome) does not
arise — there is nothing at that granularity to check. **Aggregates
cannot substitute, exactly as the task states, and this dataset offers
nothing else.**

**3. Actual coverage, verified from the files**:
`min(first_trade) = 2022-11-21 19:50:09 UTC`,
**`max(last_trade) = 2026-03-29 23:59:58 UTC`**. `T_split =
2026-04-01 00:00:00`. **Coverage ends 2 days, 15 minutes before
`T_split` — entirely pre-split, verified, not assumed.** The dataset
cannot supply a single post-split observation, independent of the
granularity problem in items 1–2.

**4. Address overlap with our `traders` table**: our table holds 194,211
distinct addresses. External dataset: 2,480,104 distinct addresses.
**2,348,455 external addresses (94.7%) do not appear in our `traders`
table at all.** 131,649 do.

**5. Overlap with the two study populations**: of the 753
twice-classifiable traders, **753/753 (100%)** appear in the external
dataset by address. Of the 5,732 PIT-legal classifiable traders,
**5,704/5,732 (99.5%)** appear. High overlap on both counts — but
irrelevant given items 1–3.

### Verdict

**No. This dataset cannot increase the persistence test's N, for two
independent reasons, either one sufficient on its own:**
1. It contains no per-position or per-trade records — only whole-history
   aggregates per trader. The sign-flip test needs market ID, side,
   entry price, and outcome per position; none of that exists in this
   dataset at any granularity.
2. Even disregarding (1), its coverage ends 2026-03-29 — before
   `T_split` — so it cannot supply a single post-split observation, which
   is specifically what N (the persistence re-classification) requires.

No workaround is proposed, per the task's instruction. This is a
complete, negative answer.

### Separate observation for Oscar (not acted on)

Item 4's 94.7% non-overlap is a large number, but **caution is warranted
before reading it as an ingestion-loss signal**: the external dataset
spans Polymarket's *entire* market taxonomy (sports, crypto, finance,
politics, tech, culture, weather — the V1 exchange as a whole), while our
`traders` table is populated by monitoring specifically scoped toward
Geopolitics/Elections activity. A large fraction of the 2.35M non-overlap
addresses plausibly trade sports/crypto/other categories our system was
never built to track, which would produce a large gap unrelated to the
known ~300-markets/day ingest-drop defect (`MASTER_HANDOVER_2026-09-05.md`
§6). **Distinguishing "never in scope" from "should have been ingested
but was dropped" would require restricting the comparison to
politics-active external addresses first** (e.g. `traded_politics=1` /
`frac_politics` thresholds, the same fields `MASTER_HANDOVER_2026-06-10.md`
already used for its own external-seed criteria) — not attempted here, is
new computation outside this task's scope, and is reported only as a
raw observation for Oscar to route as he judges, not a finding about the
ingest-drop defect.

### Cross-check against `MASTER_HANDOVER_2026-06-10.md`'s description

No discrepancy found. Documented coverage ("Nov 2022 – Mar 2026") matches
the verified range exactly. Documented sizes (495MB / 768MB) match the
actual file sizes (519,102,712 bytes ≈ 495.1MB;
804,956,644 bytes ≈ 767.7MB) to the MB. The handover's own "Key fields
used" list (`pnl_taker_politics`, `frac_both_sides`, `frac_maker`,
`frac_held_to_resolution`, `avg_market_age_at_trade`, `frac_early_trader`,
`frac_late_trader`) are all aggregate columns, consistent with the
schema found here — that document was always using this dataset as
whole-history aggregate features (its own June 2026 cross-reference
against Pool C / `geo_directionality_score` used exactly this kind of
column), never as position-level data. **No STOP condition triggered.**

---

## Part 2 — persistence pre-registration amendments

Both amendments are appended as a **dated amendment section at the end
of the document**, per its own established convention (matching
`MASTER_HANDOVER_2026-08-15.md`'s `*Amended...*` postscripts). §3 and §6
are marked with a pointer at their original location and left otherwise
intact — **nothing in the original text was deleted or silently
rewritten.** Neither amendment references, depends on, or was informed by
any post-split figure — both are justified entirely from the N=146 count
(first-repo `1d34ced`, itself a pre-split-classification-derived count,
already committed) and the already-committed post-split position-count
*distribution* (also a structural count, no direction/outcome
information).

**Amendment 1 (§6)** splits the combined success criterion into two
independently-reported comparisons: (A) persistence-rate CI vs. the
in-house synthetic-null CI (§8) — now the **primary** criterion, with
three mutually exclusive, exhaustive states (established-above /
no-persistence-overlap / reversal-below, a CI-vs-CI relationship has no
fourth state); and (B) the same CI vs. Gómez-Cram's 44% external
reference — now an explicitly **secondary** comparison with its own
three states, one of which is **UNRESOLVED** (CI straddles 44%) rather
than "inconclusive" for the whole test. Six named combinations replace
the original four outcomes. Reasoning for making this change now, on the
record before any result exists: N=146 was `unknown` in the original
document (its own Open Question 1); a rough binomial approximation at
N=146 for a rate near 40% (`SE ≈ √(0.4·0.6/146) ≈ 0.0405`, 95% half-width
`≈ 1.96·0.0405 ≈ 0.079`, i.e. **≈8 percentage points**, matching the
task's own stated estimate) shows the original combined AND-criterion
would route a substantively-informative in-house-established result to
"inconclusive" whenever its CI merely straddles 44% — a real, foreseeable
failure mode of the original design at this specific, now-known N.

**Amendment 2 (§3)** fixes, before any computation, that the persistence
rate will be reported **stratified by post-split position count**, using
five pre-specified bins drawn directly from the already-committed
pooled twice-classifiable distribution (first-repo
`directional_skill_twice_classifiable_population_20260906T170928Z.json`:
median 23, p25 14, p75 46, p90 82.8, max 359, floor 10 by construction):
`[10,14)`, `[14,23)`, `[23,46)`, `[46,83)`, `[83,∞)` — quartile-spaced
through p75, finer through p90 to isolate the long right tail (max=359)
where the activity-power effect (more positions ⇒ more power to clear
the per-trader significance bar for the same underlying tendency,
regardless of whether real skill differs) would show up most sharply.
The headline (pooled) persistence rate is reported alongside the
stratified breakdown, never instead of it, and if the cohort/comparison
difference turns out to be confined to the high-activity strata, that is
reported as such and not resolved by picking the pooled figure — no
weighting or correction is added, per the task's explicit instruction.

Full amendment text: see the pre-registration document itself
(`2026-09-06-directional-skill-persistence-prereg.md`, dated amendment
section at the end). Committed separately, with no results in the tree.

---

## What was not determined

- **Part 1**: whether restricting the external dataset to
  politics-active addresses (`traded_politics=1` etc.) would meaningfully
  narrow the 94.7% non-overlap gap, or whether that gap is genuinely
  informative about the ingest-drop defect — flagged as a separate
  question for Oscar, not investigated.
- **Part 1**: whether `user_pnl_summary.parquet`'s and
  `user_features.parquet`'s underlying trade-level source (if HuggingFace
  hosts one, e.g. a raw trades table this aggregate was built from) might
  exist elsewhere and offer position-level granularity — not searched;
  only the two files actually present in
  `data/external/` were inspected, per the task's scope.
- **Part 2**: whether N=146 and the 607-trader comparison group are
  large enough for either the primary or secondary criterion to resolve
  cleanly even with these amendments — a power question the amendments
  do not and cannot answer without computing an actual result, which this
  task does not do.
- **Part 2**: the outstanding §8 prerequisite (establishing the in-house
  synthetic-null persistence rate on the actual twice-classifiable
  population) remains unattempted and unchanged by this task — both
  amendments are structural/reporting fixes, neither substitutes for that
  prerequisite.
- **No post-split classification, sign-flip null, p-value, persistence
  rate, or outcome-dependent quantity was computed anywhere in this
  task** — Part 1 was schema/coverage inspection and address-set
  intersection only; Part 2's CI-width justification used only the
  already-known N=146 count via a standard closed-form approximation, no
  simulated or real outcome data.
