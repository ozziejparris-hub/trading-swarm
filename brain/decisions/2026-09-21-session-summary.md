# Session Summary — 2026-09-21 (Server Setup 23)

Documentation only. No computation, no new analysis — everything below draws on work
committed today. Every commit hash cited was checked against `git log --oneline -1 <hash>`
on the relevant repo/branch this session; every figure cited was checked against the
committed decision document it originates from, quoted or grepped directly, not recalled.

**Two discrepancies flagged up front, per instruction not to reconcile silently:**

1. The brief for Part B described the long-repeated figure as **"eight of nine wrappers
   unguarded."** The actual source (`MASTER_HANDOVER_2026-09-05.md:347`, quoted in
   `2026-09-21-daily-maintenance-flock-guard.md:14`) says **"the eight remaining unguarded
   cron wrappers"** — eight total, with no "of nine" anywhere in the source phrasing. The
   substance is the same either way (today's session found the figure doesn't reconcile
   against anything on disk, real count six), but the specific wording in this brief does
   not match the source it's citing.
2. The monitor RSS trend figures (417 MB at 16.5h, 1.16 GB at 46h, 1.34 GB at 71h) were
   reported conversationally during today's first task (the pilot-recovery health check) and
   are not committed to any decision document — no file exists to check them against. Carried
   forward here as given, not independently re-verified against a source this session, since
   none exists.

---

## HEADLINE — a schedule investigation meant to fix one projected collision found three that were already happening, and ended with a production job permanently disabled

---

## Part A — Corpus content extraction: from pilot to full run

Recovery first. Last night's session hit its usage limit mid-task. The fourth pilot's script
edits and its 8-document run were found on disk, complete and correct, but never reported —
verified from the existing artifacts this session rather than re-run.

The four-pilot arc, as a sequence of findings:

- **Pilot 1**: 6 of 12 documents returned every field as a flat list of bare strings instead
  of the required shape. Zero fabrications across 80 manually-traced "unverified" quotes
  (`2026-09-20-corpus-content-extraction-pilot.md:81`).
- **Re-pilot** (one worked example added to the prompt): schema pass rate 5/6, up from 0/6
  on the failing set. But the fix cost real things — projected full-corpus runtime roughly
  doubled (252.2s mean → the pilot's own 18.6h projection vs. the re-pilot's 34.4h), control
  breadth fell 36%/11% on the two control documents, a new timeout failure class appeared,
  and — the consequential finding — **two genuine fabrications**, both in `explicitly_open`
  on the corpus's largest document: the field was capped at 8, the model returned exactly 8,
  six real (`2026-09-20-corpus-content-extraction-repilot.md:135-136`, quoted: "8 items
  requested, 8 produced, 6 real").
- **Fourth pilot** (`258b860`, Ollama `format` constrained decoding replacing the worked
  example, caps rephrased as ceilings, no `minItems`): schema 8/8, both known fabrications
  confirmed absent on their own source document, breadth recovered on both controls (one
  exceeded the original pilot's figure), verification rate 88.8%.
- **Residual, found this session**: duplicate padding on long documents — real, verified
  quotes repeated to reach the cap rather than invented.

**The lesson about caps, recorded precisely as instructed**: a ceiling phrased as a bare
number reads as a quota. Blocked from inventing content once schema constraints made
fabrication harder, the model repeated real content instead — the same underlying pressure
(reach the stated maximum), a different symptom.

**A correction to this session's own earlier reasoning, also recorded as instructed**: in the
fourth-pilot report I attributed the duplicate padding to document length ("duplication
appears exactly on the two longest documents... and nowhere else"). This was wrong. The
dedup task's comparison against the re-pilot's artifacts found **zero duplicates across all
7 of its records, including the identical two long documents** — the re-pilot processed the
same long documents duplicate-free using the worked-example approach.
**Padding tracks the `maxItems`-constrained-decoding approach itself, not document length** —
document length was a confound in the one data point available at the time, not the actual
cause (`2026-09-21-dedup-and-length-scaled-timeout.md:145-150`).

**The design point that made constrained decoding safe to use at all**: no `minItems`
anywhere in the generation schema. Under a JSON-schema grammar, a minimum-length array makes
fabrication *structurally mandatory* once genuine content runs out, not merely likely — the
schema's own default `minItems: 0` permits an empty array, checked (not assumed) via a
runtime `assert` in the script itself.

Then `c7c94aa`: deterministic post-extraction dedup — two items in the same field are
duplicates if their quote is identical after `_normalize_ws()`, the same whitespace-collapse
already used for the verifier's "normalized" tier, reused rather than reinvented.
Conservative by construction: whitespace-collapsing cannot merge two genuinely distinct
passages into the same string, so a false-positive removal is structurally impossible.
Padding recorded as its own field per document per extraction field, not discarded. **24 real
duplicates found across all four artifact sets, every single one manually inspected and
confirmed byte-identical to its survivor's quote — zero false positives.** Length-scaled
timeout derived from a fit across all pilots' returned calls (`k=0.539 s/line`, `2.7×`
safety multiplier set from the worst observed actual-to-predicted ratio in that data, 300s
floor, 3600s hard ceiling).

**The full run is in progress**: PID 102652, started 2026-09-21T16:16:00 UTC, 276 documents
discovered and pending at launch (`logs/corpus_content_extractor_run.out:1-2`), projected
10.8–20.5h. Verification is tomorrow's task. Checked live at the end of this session: still
running, elapsed 4:50:57, 133 processed / 6 failed (isolated timeouts, not a stall — most
recent success postdates the most recent failure).

---

## Part B — The flock guard (`bfdf9d6`)

The 2026-09-05 proposal naming `run_daily_maintenance.sh` as the highest-priority unguarded
target is in **`MASTER_HANDOVER_2026-09-05.md` section 6** ("KNOWN DEFECTS, LIVE AND
UNFIXED") — **not section 5** as that day's task briefed it. A citation slip, confirmed by
directly reading the source rather than trusting the brief.

The repeated "eight remaining unguarded cron wrappers" figure (see discrepancy note above for
its exact source wording) does not reconcile against anything on disk today: counting wrapper
*files* gives 10, counting *currently active* crontab entries gives 3 wrapper-based jobs.
**The real count of currently-active, collision-relevant unguarded jobs, established this
session, is six** — another number that had drifted from whatever produced it, undiagnosed.

The guard itself: kernel advisory locking (`flock`), not a lockfile-existence check — a
SIGKILLed holder's lock releases automatically, the instant the process exits, for any
reason, with no cleanup code required. Exit **75** (`EX_TEMPFAIL`) on refusal, deliberately
not 0, so a refused run is distinguishable from a completed one by anything that checks the
wrapper's exit code, not just its log. Telegram on **every** refusal, deliberately not routed
through `failure_age.py`'s change-gating — gating would suppress the second and later
consecutive refusals, and each additional day maintenance is refused is independently bad,
not a repeat of the same news.

**The critical SIGKILL test passed. 33/33 assertions**, against an isolated stand-in, never
against production.

**Recorded honestly, as instructed: the guard is precautionary, not a fix for an observed
daily_maintenance problem.** The 2026-09-13 audit found 87 "Starting" and 87 "Finished"
markers perfectly paired across 106 days of log history — daily_maintenance has never
overlapped *itself*. What the guard actually closes are two separate, real risks surfaced
later the same day (Part C).

**Tomorrow's 06:00 run is the guard's first production exercise.** The real wrapper was
deliberately not run end-to-end this session, even with a stubbed payload, specifically to
avoid appending a spurious `Starting`/`Finished` pair to the live `logs/daily_maintenance.log`
that the corpus run's own log-tail maintenance detector (Part A) was actively watching at the
time.

---

## Part C — the Sunday schedule, and what it revealed

**The session's most consequential finding, recorded without softening, as instructed.**

The task that opened this thread asked about a single projected collision: the Sunday ELO
recalc overlapping `run_daily_maintenance.sh` from 2026-09-27. The reality found was worse,
and already happening, on the two most recent actual Sundays:

- `run_database_backup.sh` and `polymarket-sunday-elo.timer` both fire at exactly `03:00:00`
  every Sunday and ran concurrently for **~169 and ~174 minutes** on 2026-09-13 and
  2026-09-20 respectively.
- A backup that normally completes in 60–130 **seconds** ran **180.6–201.5 minutes** on those
  same two Sundays — roughly a hundredfold slowdown — because SQLite's Online Backup API
  restarts its copy whenever a page it has already copied is modified in the source, and the
  ELO recalc writes continuously for the whole 170-minute window.
- **This is the identical mechanism behind the backup-vs-sweep incident that motivated the
  2026-08-26 backup guard** in the first place — recurring every single week from the
  *ordinary* Sunday schedule itself, not from any special event, unnoticed until this
  session looked for it.
- It overran directly into `run_daily_maintenance.sh`'s 06:00 start by **5.6 minutes**
  (2026-09-13) and **21.5 minutes** (2026-09-20).

**A confirmed ordering dependency, not just a timing one**: the ELO recalc reads a snapshot
of market resolution status once, near the start of its run; `weekly_resolution_sweep.sh`
starts 30 minutes later and writes new resolutions for the remainder of the window. Any
market resolved by the sweep after ELO's snapshot but before ELO finishes was silently
treated as still-unresolved for that week's ELO computation — **deferred to the following
week, not corrupted**, but a real, previously undocumented gap between what the sweep
produces and what ELO actually saw.

The designed fix — a chain (sweep → ELO → backup) under a single wrapper, with Sunday's
`run_daily_maintenance.sh` blocking on a *second*, separate lock (waiting, not refusing)
before proceeding to its own self-overlap guard — was simulated clean across 13 weeks but was
**not built**, superseded by Part D's finding that the entire ELO recalc could be removed
instead.

**The reboot finding, recorded exactly as an open, unverified synthesis, not a confirmed
fact**: `Automatic-Reboot-Time=03:00`, conditional on a reboot-requiring update having landed
that morning — 8 of 9 scheduled reboots since May actually executed as boots. Separately,
`run_database_backup.sh` runs *daily* at 03:00, every day, not just Sundays. The inference
that the daily backup is therefore plausibly killed mid-copy on reboot days connects two
facts this session established independently; it was never itself stated or checked in any
committed document this session — genuinely unverified, not softened into a claim it doesn't
support.

---

## Part D — the ELO family, and the Sunday recalc disabled

`47704b0` established there are two, largely independent, ELO pipelines. Everything
operationally load-bearing today — `geo_elo`, `geo_elo_active`, tiers, Pool B/C, and the
LEGENDARY gate's five live daily/weekly consumers — runs on the **independent daily**
`update_geo_elo.py` path. The Sunday recalc's own, exclusive output was five behavioral
columns: `timing_score`, `patience_score`, `kelly_alignment_score`, `behavioral_modifier`,
`advanced_modifier`.

**The connected-element check that made removal defensible**: `timing_score` — Component 3
of the canonical skill metric design — is produced **only** by the Sunday job; the daily
`apply_full_elo_modifiers.py` step (Writer B) reads and re-writes the same value unchanged, a
carry-forward, not a recomputation. Disabling the Sunday job therefore freezes it, not merely
slows it. Judged acceptable specifically because `timing_score` is validated only on a
169-trader cohort, with 21.2% contamination found beyond it — and a frozen archive of its
current value preserves exactly the research value that validated cohort already has.

Then, in sequence: `41d68e5` (first-repo) — 203,677 rows archived, provenance embedded, hash
reproducing, 20/20 random spot-checks against the live table matching exactly; true
last-computed time independently verified from `logs/sunday_elo.log` as **2026-09-20
03:00:03–05:54:26 UTC**, not from the `elo_last_updated` column (see standing hazard below).
`95fd9ff` — the composite scoring consumer (`analysis_scheduler.py`'s daily 01:00 UTC step)
was traced to its actual destination and found to **reach nobody**: the CSV it writes isn't
among the three filename patterns `system_observer.py`'s report-discovery step globs for, and
the method that builds the Telegram message's text has zero references to composite scores
anywhere. **This corrects this same session's own `47704b0` finding**, which had
characterized the composite as "surfaced in the daily Telegram summary" — traced the exact
code path this time rather than re-stating the earlier read. `polymarket-sunday-elo.timer`
was then stopped and disabled by Oscar (this session could not supply the interactive sudo
password) — confirmed not masked, not deleted, dated re-enable procedure recorded. The
13-week simulation re-run with the job removed showed the Sunday DB-write cluster collapsing
to zero overlaps. The freeze was documented in `CLAUDE.md` (`fc83c71`), alongside a
correction to a line in the same file that this action had just made actively false.

**Recorded as a standing hazard, precisely as instructed**: `elo_last_updated` is **not** a
freshness marker for these five columns. Writer B bumps it daily even when it changes
nothing about them. Confirmed empirically, not just re-argued from reading the code: **0 of
46,423 rows with a real behavioral score differed in these five columns between a pre-Writer-B
offsite backup and the live table, while `elo_last_updated` itself differed for 43,879 of
those same 46,423 rows.** Found only by diffing against an independent backup — the column
itself would have misled a naive reader into believing the data was current.

**This is a production schedule change, not a documentation exercise.** The first Sunday
without the recalc is 2026-09-27.

---

## Open threads carried forward

- Verify the full corpus content run (PID 102652) once it completes.
- Tomorrow 06:00 UTC: the flock guard's first production exercise.
- Monday 2026-09-28: the first Sunday without the ELO recalc — the confirmation checklist is
  in `95fd9ff` (`brain/decisions/2026-09-21-disable-sunday-elo-recalc.md`, Part 6).
- `geo_elo` was condemned for skill-ranking on 2026-08-15 (`MASTER_HANDOVER_2026-08-15.md`),
  yet its daily output still drives trader promotion (`promote_high_pnl_traders.py`) and
  signal scoring (`score_str003_signals.py`, `register_str002_signals.py`) live, every day. A
  condemned metric still making skill-adjacent operational decisions — needs its own review,
  separate from today's Sunday-recalc question.
- The reboot-time decision (`Automatic-Reboot-Time=03:00`) is Oscar's call, not made today;
  and whether the daily backup is actually killed on reboot days remains unverified (Part C).
- Monitor RSS: 417 MB at 16.5h, 1.16 GB at 46h, 1.34 GB at 71h — growth appeared to be
  slowing; one more reading needed to know whether it's linear or leveling off (see
  discrepancy note above — not independently re-verified this session against a committed
  source).
- A correctly-built incremental rating is a legitimate future capability serving "rate
  traders continuously" — genuinely different from what a batch method like the v2 metric
  provides. The current `geo_elo` is explicitly not that capability, delivered correctly; its
  defects are in the formula and calibration, not in the incremental-update idea itself.
- Dropping `maxItems` from the extraction schema entirely would address the duplicate-padding
  finding at its source (nothing left to reach toward) rather than after the fact, the way
  this session's dedup pass does today.
- The post-commit hook pushes on every `brain/decisions/` commit regardless of task
  instructions — it is a git hook, not something session-level instructions can suppress, and
  fired as expected on every commit made today.
- The dormant-agents decision (Tier-3 pause, 2026-07-15/2026-08-31) — not touched or
  revisited this session, carried forward as still outstanding.
- The relevance-classifier §3.10 adjudication has been outstanding since 2026-09-03 — **18
  days**, as of today.

---

## Corpus run confirmation

PID 102652 confirmed running at the time this summary was written: elapsed 4:50:57,
`{"processed": 133, "failed": 6}` — running, healthy, not touched by this documentation-only
task.

No verdict on what to do next is offered here, per instruction.
