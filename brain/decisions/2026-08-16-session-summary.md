# Session Summary — 2026-08-16

## THEME

Reconciliation day, not build day. The planned work was a CI power diagnostic — decompose
the 08-15 out-of-sample result's CI to determine whether a frozen-cohort Phase 2 can
resolve the underpowered thesis result in finite time. That work was deliberately
deferred. Judgement call: decomposing the confidence interval of a number whose
underlying population had not itself been characterised — never traced against the
comprehensive_elo sign-error finding, never checked against the canonical population
definition it should have used, never checked for whether it reproduces at all — would
have been building analysis on top of an unverified foundation, the exact failure shape
08-15 spent a month correcting for once already. Three characterisation passes ran
instead: a dependency trace, a canonical-infrastructure recon, and a reproducibility
audit. Nothing was fixed. Three things were characterised, precisely, and the master
handover was amended to carry the corrections forward.

## THE RECURRING SHAPE (record it — this is the reusable lesson)

The same failure shape surfaced three times independently in one session, in three
different reports, about three different pieces of infrastructure:

1. `backtest_window_sql()` exists, is validated, is documented as canonical — and the
   v2f pipeline that produced the headline result does not call it. It computes
   `tape_end` independently instead.
2. `check_canonical_definitions.py` — the drift guard wired into daily maintenance —
   exists specifically to catch this class of bypass, and does not cover the module
   section (`backtest_window_sql`, Section 6) where the bypass actually occurred. It
   covers geo_elo thresholds and Pool-C SQL shapes only.
3. The snapshot-persistence pattern needed to make Objective 2's cohort reproducible
   already exists in the same script family — Objective 1 uses it
   (`metric_v2f_intersection_cohort`) — and Objective 2 simply didn't use it, so its
   148/120/148 cohort has no persisted membership to diff against.

In every case the correct infrastructure was already built, already in reach, and
already validated for a neighbouring use. Nobody chose not to use it — it just wasn't
reached for, and nothing was watching for that. **Convention-only enforcement does not
fail loudly. It accumulates quiet exceptions until a number cannot be regenerated.**
That is exactly what happened here: the exceptions were silent for weeks, and the first
signal that anything was wrong was a reproducibility audit turning up UNREPRODUCIBLE on
the project's own headline result. The operating rule this earns: whenever an instance
of this shape is found, the question is never just "fix this one" — it is "what else was
in reach and unused, and would anything have told us." All three instances above were
found by asking that second question, not the first.

**A second, quieter lesson, about the audit that found this:** the UNREPRODUCIBLE
verdict was returned under real pressure to round it to something friendlier. The
finding hadn't changed character — still null, still directionally positive, still
~2.3x the placebo's point estimate — and the drift causing the miss was tiny: one
additional position, a point-estimate shift of 0.0002. It would have been easy, and not
obviously wrong, to call that "close enough" and report EXACT or DRIFTED. It wasn't
rounded, because the verdict criteria (EXACT / DRIFTED / UNREPRODUCIBLE, with DRIFTED
requiring row-level attribution for every discrepancy) were fixed *before* the audit
ran, not adjusted afterward to fit what came back. This is the pre-registration
discipline working exactly as designed, on itself, under the one condition that
actually tests it — a small, sympathetic, easy-to-wave-through gap. Record this as
positive evidence the discipline holds, not just as a rule stated in §7 of the
handover.

## WHAT WAS ACHIEVED

1. **comprehensive_elo dependency trace: NO CONTACT.** The 08-15 thesis result's
   inputs — the positions FIFO aggregation, the T_split cohort query, the placebo
   matching, the whole `trader_skill_metric_v2*.py` chain — are clean of both
   `comprehensive_elo` and `calibration_analysis.py`. One real causal path was found
   and traced to where it stops: `comprehensive_elo` feeds `update_research_exclusions.
   py`'s bot-tagging (`comprehensive_elo < 700` → `LP_ARTIFACT`;
   `comprehensive_elo BETWEEN 1500 AND 3500` → `ARB_BOT`), which sets `traders.bot_type`,
   which sets `traders.research_excluded`. But `research_excluded` is never read
   anywhere in the v2 pipeline — confirmed by direct grep across every
   `trader_skill_metric_v2*.py` file, `layer0c_corrected_metric.py`, and
   `position_tracker.py`: zero hits. The path is real; it terminates one hop short of
   the result. Incidental finding recorded alongside the verdict: the v2 pipeline
   applies **no `research_excluded` filter at all**, unlike most other research
   queries in this codebase — not investigated further (out of the trace's scope), but
   flagged for whoever next touches cohort eligibility.
   (`2026-08-16-comprehensive-elo-dependency-trace.md`)

2. **Canonical infrastructure recon: the v2f population bypass, confirmed on live
   data.** Canonical population at the T_split boundary (via `backtest_window_sql`'s
   actual definition) = 6,842 markets. v2f's implicit population (positions-anchored,
   via its own `build_tape_end_map`) = 6,588 markets. Symmetric difference: 254
   markets, entirely one-directional — v2f's population is a strict subset of
   canonical, nothing appears in v2f's set that canonical excludes. Root cause,
   verified row-level, not inferred: 166 of the 254 have trades but no FIFO-closed
   position; 88 have positions but the entry trade's `trade_result = 'pending'` on a
   market flagged `resolved = 1`. The recon's second finding: adherence to canonical
   definitions across this project is convention-only. `check_canonical_definitions.py`
   would not have caught this bypass — its coverage stops at geo_elo thresholds and
   Pool-C SQL shapes. Nothing in the codebase would have detected it.
   (`2026-08-16-canonical-infrastructure-recon.md`, commit `f6cbbf0`)

3. **Reproducibility audit: UNREPRODUCIBLE.** The reasoning is procedural, not
   substantive — the finding itself did not change character, but the fixed criteria
   (row-level attribution required for every discrepancy, or the verdict is
   UNREPRODUCIBLE by default) were not met. Code drift was ruled out entirely: current
   HEAD *is* `eaeabbc`, the `generator_commit` persisted on every result-of-record row
   — zero commits since. The persisted tables (`metric_v2f_oos_result`,
   `metric_v2f_findings`, `generated_at = 2026-08-15T19:36:56.85Z`) reconcile exactly
   to the handover's stated figures — the number of record genuinely is the number
   persisted. A prior, wrong belief was corrected in the process: O-49's "0 → 4,979 →
   20,211" trajectory was never a `trade_gap_flag` measurement — it was an ad-hoc
   readiness count, never applied as a write. Today's actual `trade_gap_flag = 1`
   count is 250, the same April-gap (166) + O-37-quarantine (84) components that
   predate 08-15, untouched by O-49. What the audit could NOT do is trace the small
   re-run deltas (cohort 3,032 → 3,033 positions; placebo 2,569/110 → 2,518/106;
   Objective-1 intersection 295 → 298) to specific rows, because Objective 2's cohort
   membership was never persisted in the first place — there is nothing to diff
   against. This is the Objective 2 persistence gap named in item 3 of the recurring
   shape above.
   (`2026-08-16-result-of-record-reproducibility-audit.md`, commit `5195b01`)

All three findings, plus the master handover amendment that carries them forward, are
committed and pushed as of this session
(`f6cbbf0`, `5195b01`, `9941d50`).

## STATE FOR NEXT SESSION

The order below is **proposed, not decided** — Oscar has not signed off on sequencing.

1. **The 88 `resolved=1`/`trade_result='pending'` markets** — a real, standalone
   data-consistency gap (`markets.resolved` and the entry trade's `trade_result` can
   disagree), and part of what makes v2f's population a conditioned subset: because
   `edge = won − entry_price` requires a closed position, the metric is structurally
   restricted to markets where a position closed cleanly, and the cohort's edge is
   measured on a non-random slice of the population of unknown direction and
   magnitude.
2. **Pin-mechanism design.** Pre-register cohort persistence for Objective 2 — the
   schema pattern already exists (`metric_v2f_intersection_cohort`'s shape) and was
   simply never applied to the 148/120/148 cohort that actually produces the headline
   result. Any future decomposition of this result should run against a pinned
   population, not a live one.
3. **The deferred CI power diagnostic (Track 2).** Its pre-registration must be
   amended before it is committed: its A3 stop condition, as currently drafted, reads
   a reproduction miss as evidence of a broken harness. Today's audit shows that
   diagnosis would have been wrong — substrate drift (ongoing background backfill
   inserting pre-T_split-timestamped trades, confirmed active: 162,648 such rows among
   the most recent 553,800 inserted) is the live, demonstrated cause, not a harness
   defect. Fix the stop condition before this diagnostic runs, not after it produces a
   confusing result.
4. **Reconciliation surface still unexamined** — this session characterised three
   things; it did not attempt a full sweep. Open, unchecked: whether the frozen
   `bt_pop_2025-11-01_v1` snapshot is still regenerable post-quarantine (O-37); whether
   `event_cluster_labels` (4,712/4,712 at labelling time) still covers the current
   population given the population has moved since; whether the PIT validations
   (3,229 traders, 1.2M items) predate Writer A's 2026-07-19 canonical run and the
   08-11 gap recovery, and if so whether they need re-running; and ELO arc Stage 5,
   never closed, including whether the frozen/paused state of the ELO recalculation
   arc was ever formally unfrozen.
5. **Carried from 08-15, unchanged:** the cutover decision (does the new metric
   replace `geo_elo` in production — not made); the category-split cost floor
   (elections sits at the top of its own cost range); ingestion detection (still no
   alert for missing trades); the consensus question (still untested, still gated on
   Objective 2 having more out-of-sample power); the `comprehensive_elo` sign error
   (now known, via this session's dependency trace, NOT to touch the thesis result —
   but still open and live-affecting elsewhere in the system, e.g. bot-tagging, ELO
   modifier scores, live monitoring/alerting surfaces); elections calibration re-run
   (O-40); O-38; O-18.
