# Session Summary — 2026-09-12 (Server Setup 17)

Documentation only. Every commit hash and figure below was checked against
its source this session. first-repo `main`, trading-swarm `master`.

---

## HEADLINE — a hardware outage cut daily maintenance short, and a five-pass research review closed more doors than it opened

**The morning progression check found the server had suffered a full,
unplanned power loss overnight** — not a service hang, the whole machine —
which killed `daily_maintenance.py` mid-run and left the observer's
Telegram-token-leak fix (committed yesterday, `dd0fb5e`) still uninstalled
in the running process until the crash forced a restart. **The token is
still live and unrotated.** The rest of the day ran a five-pass "heatmap"
review of the project's entire research history — asset inventory, a
graded ruled-out register, external literature research, candidate
generation, and a scored shortlist — five commits, all read-only, no
project data touched. **The shortlist is five candidates; the more
consequential finding may be the administrative one underneath it: 25 of
35 named research questions were simply never run, and a project
document has been silently stale for three months without anyone
deciding to stop maintaining it.**

---

## INFRASTRUCTURE EVENTS — a hardware fact first

### The outage: 07:58:21 → 13:07:20 UTC, ~5h9m, hard power loss

`journalctl --list-boots` recorded the previous boot ending at
**2026-09-12 07:58:21 UTC** and the next boot starting at **13:07:20
UTC** — a full machine-down interval of roughly 5 hours 9 minutes, not a
service restart. No systemd shutdown sequence for that boot was found in
the journal (no "Stopping"/"Reached target Shutdown" trail before the
gap), consistent with a hard power loss rather than a clean shutdown.

`daily_maintenance.py` had started on schedule at 06:00:01 UTC and was
mid-run — inside a Pool C backfill loop, on trader `[3527/4482]` — when
the log's last write landed at **07:56**, seconds before the boot ended.
**It did not auto-resume after the reboot**: no new `Starting
daily-maintenance` line appears in the log after 13:07:20. Step 8
(canonical drift) had already run and completed correctly before the
crash (1 violation, register-suppressed, no alert — expected behaviour).
**Step 22, the geo/elec pending backlog evaluator, never ran at all.**
Consequently, that day's pending-geo reading of **122** (79
`background_backfill`, 43 `polymarket_api`) is **yesterday's number
carried forward, not a second data point** — confirmed by a direct query
against the live database later in the day returning the identical
122/79/43 split, unchanged from the prior reading.

**Oscar's working theory is extension-cord contention** — reported here
as stated, not independently verifiable from the box itself. **The
machine has been moved to a wall socket.**

### A possible precursor, recorded not diagnosed

Shortly before the crash, `polymarket-observer` hung on SIGTERM twice —
**06:45:21** and **06:45:57** UTC — each timing out on `stop-sigterm`
and requiring a SIGKILL, matching the service's prior documented pattern
of hanging on shutdown. Separately, the observer's own health-check
counters show an anomaly in the hours before that: sequential numbering
jumps from **#2233** (2026-09-11, 10:13:17) to **#3160** (2026-09-12,
01:49:36), then **#3161 through #3314+** are all stamped the **identical
second**, 03:05:19 — a burst of what should be roughly per-minute log
lines all landing in one instant, consistent with a buffered-output
flush or a runaway loop rather than real-time logging. **Recorded as a
possible precursor to the crash; not diagnosed, and no causal link to
the power loss is established.**

### The Telegram token leak — still live, still unrotated

**Root cause** (unchanged from yesterday's fix, `dd0fb5e`, first-repo
only — this commit does not exist in trading-swarm): `httpx`
(python-telegram-bot's HTTP backend) logs every request's full URL at
INFO, and Telegram's Bot API embeds the token in that URL's path.
Invisible until something calls `logging.basicConfig(level=INFO)`, which
three analysis modules do unconditionally at import
(`calibration_analysis.py`, `risk_adjusted_returns.py`,
`regret_analysis.py`) and `monitoring/main.py` does at its own top
level.

**Fixed at four senders**, each by capping `logging.getLogger("httpx")`
to `WARNING` at the point the sender constructs its `Bot`:
`monitoring/telegram_health_bot.py` (the observer's sender, confirmed
leaking), `monitoring/telegram_bot.py` (currently dead code, fixed
defensively), and the deferred-import senders in
`scripts/audit_invariants.py` and `scripts/check_canonical_definitions.py`.
**Verified two ways**: a real send through the fixed sender under the
exact leak-triggering condition (root logger forced to INFO first),
confirming zero token/URL bytes in the captured log; and a deliberate
send with an invalid token, confirming genuine errors (`Unauthorized`)
still log normally — the fix suppresses only the request-line noise, not
real failures. A tenth-check regression test,
`tests/test_telegram_httpx_log_redaction.py`, is committed.

**Because the fix was committed at 19:35 UTC yesterday but the observer
process was not restarted, the fix sat inert until today's crash-forced
reboot restarted every service at 13:07:25 UTC** — this morning's
progression check confirmed the leak pattern was present as recently as
01:49:36 UTC today (before the reboot) and absent from all journal
output since the restart, though no Telegram send has yet occurred
post-restart to positively re-confirm the fix is live in practice, only
that the code path is now the fixed one.

**The token is the live one and rotation is not done.** If rotated, the
recorded sequence is:
1. Update `/home/parison/.env_trading` — the same token value is carried
   under three separate variable names: `telegram_alerts_token`,
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_AGENTS_TOKEN`
   (`TELEGRAM_ORCHESTRATOR_TOKEN`/`TELEGRAM_METRICS_TOKEN` are different
   bots, unaffected).
2. Restart every long-running consumer that reads one of those three
   vars: `polymarket-observer.service`, `polymarket-monitoring.service`,
   `trading-swarm.service` (`audit_invariants.py`/
   `check_canonical_definitions.py` self-load credentials fresh each
   cron invocation and need no restart).
3. Confirm all consumers are on the new value.
4. **Only then** revoke the old token at BotFather — revoking first
   would break every still-running consumer immediately, since the old
   token stays valid in memory until each process actually restarts.

Full detail: trading-swarm `2026-09-11-telegram-token-log-leak.md`.

---

## THE HEATMAP — five passes, one day, five commits

A five-pass research review of the entire project, run back-to-back
today, each pass reading the prior ones and cross-referencing by asset/
register/finding ID:

| Pass | Subject | Commit |
|---|---|---|
| 1 | Asset inventory — what exists, what it's proven to do | `1bb36e1` |
| 2 | Ruled-out register — what's been closed, and how strongly | `5e94eef` |
| 3 | External research — what the outside literature already knows | `9efc118` |
| 4 | Combinations — candidate questions generated from passes 1-3 | `8a6c4ea` |
| 5 | Scoring and shortlist — the final, ordered shortlist | `e796357` |

Each pass has a committed `.md` and `.json`. `metric_v2f_oos_result`'s
sha256 (`021be40a...074cd4e`) was checked and confirmed unchanged before
and after every pass.

### The shortlist, in order, with its one-line rationale

1. **Execution timing within the directional-skill harness's validated
   cohort** (re-running RQ-EXEC-001 properly) — the last open
   execution-adjacent door still standing after copy-trade capture and
   presence-based mispricing both closed; the original n=4 result
   predates the now-validated cohort.
2. **Calibration re-weighting test** — resolves pass 5's own headline
   external conflict (see below) at near-zero cost using an
   already-validated instrument.
3. **CLOB v2 maker-rebate before/after split on `is_taker`** — the
   cheapest test in the whole exercise (hours), informative regardless
   of outcome.
4. **Result-of-record recompute** on current data with the
   now-deterministic `match_control()` — the only candidate in the
   entire register with an effect size already known to clear the cost
   floor if it resolves.
5. **Wash-trading network-detection cross-check** — highest stakes by
   blast radius (bears on confidence in every downstream result if the
   canonical population is contaminated undetected), but the most
   expensive item on the list.

### Headline exclusions

**`S3-6`** (rerunning ELO persistence) — cheap and clean but **low
consequence**: it would only re-validate a condemned, already-superseded
instrument (`geo_elo`/`comprehensive_elo`), and the directional-skill
harness already answered the analogous question soundly. **`S4-10`**
(tracing `comprehensive_elo`'s exact defect) matches pass 5's own stated
example almost exactly: knowing the defect changes nothing about
direction, since the project has already moved past that instrument.
**`S3-2`** (reopening the Gómez-Cram 44% comparison) is not reachable at
all — its cohort is capped by a fixed split date, not a data-volume
problem, so waiting cannot fix it. 14 candidates total did not make the
shortlist, each with a stated reason.

---

## THE FINDINGS THAT MATTER MOST

- **25 of 35 named research questions were never run.** Dropped for cost
  or attention shift as the project's center of gravity moved to the
  ELO-arc migration and then the `geo_elo` condemnation — not because
  anything returned negative.
- **`brain/strategy-registry.md` has been silently stale since
  2026-06-12** — three months. It still lists STR-002's revalidation as
  a *future* date while a direct query today shows real accumulated
  signal data — **flagging a discrepancy here rather than reconciling
  it silently**: pass 2's own meta-finding narrative and its JSON both
  state this as **n=221 signals at 34% correct**, but pass 2's own
  register entry `C5` and a fresh query against `str002_signals` run
  today both return **n=227**, matching pass 1's original count. The
  227 figure is the one that reproduces against the live database; the
  221 figure appears only in pass 2's narrative prose and has not been
  traced to its source. Either way, the substantive finding stands:
  the agent responsible for catching this kind of drift
  (`feedback-loop-agent`) was disabled 2026-08-31, but **the registry
  was already 2.5 months stale before that pause began** — the pause is
  not the explanation.
- **The literature has already answered questions the project shelved.**
  `RQ-ILS-001` and `RQ-SCI-001` both have published frameworks under the
  same name and concept (a Nechepurenko research program on Polymarket
  informed-trading detection), one with public code. `RQ3.2` is directly
  answered by Gómez-Cram, Guo, Jensen & Kung (SSRN 6617059) — a paper
  the project was already citing elsewhere, for a different purpose,
  without ever closing the loop back to its own abandoned RQ3.2.
- **A mid-project structural change the corpus never mentions**:
  Polymarket's CLOB v2 upgrade and a $1M maker-rebate program,
  2026-04-28, sits directly against the project's own finding of zero
  maker-side rows in 621,350 labelled trades (`built_b7`'s cited figure
  — the live count has since grown to roughly 664,000 as trading has
  continued, but the specific rebate-program question is a before/after
  split on the 2026-04-28 date, unaffected by total volume growth).
- **The calibration shape conflict, unresolved.** The project's own
  measurement finds the recalibration slope *falling* with horizon;
  arXiv:2602.19520 finds it *rising*. Both agree on direction
  (underconfidence). Weighting scheme (price-weighted vs.
  position-size-weighted) is the leading candidate explanation and is
  **untested** — it's the #2 shortlist item precisely because it's the
  cheapest way to settle this.
- **The one candidate with an effect size already known to clear the
  cost floor is the result of record, recomputed.** Everything else on
  the shortlist and in the wider candidate set is diagnostic or
  characterisation work — informative, but not itself a claim of
  tradeable edge.

---

## THE OPEN DISAGREEMENT — recorded unresolved, for Oscar

Pass 5 excluded the composite informed-trading screen (`S5-1`, the
Mitts & Ofir-style bet-size/timing/profitability/concentration composite)
from the shortlist on the activity-matched-placebo objection — the same
objection that killed four prior single-dimension selectors. But pass
5's own structural-observation section argues the objection may not
straightforwardly bind here: the five failed selectors all tested
whether a trader's mere *presence* marks a market as mispriced *for
others* to exploit, while the composite methods in the literature
predict a trader's *own* outcome from their own behavioral profile —
different questions, with plausibly different failure modes, not the
same test with more features bolted on. Pass 5 then states plainly that
no shortlisted candidate tests this structural hypothesis at all, and
that answering it properly would require the matched-placebo comparison
built into the design from the first run, not appended after a positive
result invites one.

**Chat-Claude's position, recorded as a disagreement with the pass, not
a correction of it:** the exclusion is probably wrong as a final
verdict, and the right fix is to design `S5-1` with the matched-placebo
comparison built in from the start — not to promote it to the shortlist
as currently specified, and not to leave it fully off the table either.
As pass 5 left it, this is genuinely unresolved. It is Oscar's call
which reading governs.

---

## WHAT TOMORROW ADDRESSES

**Per Oscar: a methodology-extraction pass, before touching the
shortlist.** Pass 3 gathered *findings* — effect sizes and verdicts —
not *methodology*. Two of the three foundational external papers (Della
Vedova, SSRN 6191618; Gómez-Cram et al., SSRN 6617059) returned HTTP 403
on their own abstract pages this session, so **every figure attributed
to either paper anywhere in the heatmap is secondhand**, sourced from
search-result excerpts and secondary summaries, not the primary text.

The specific questions for tomorrow's pass: how does **Mitts & Ofir's
permutation test** construct its null, and does that construction do the
work an activity-matched placebo does here, or something different; how
does **Gómez-Cram's split-half** method handle low-event traders, and
how it avoids (or doesn't) the p-value-pinning problem this project hit
at 1,500 permutations in its own REPS work. **This reads a few papers
deeply rather than many shallowly, and is scoped to produce
implementation requirements, not new findings.**

---

## OPEN THREADS CARRIED FORWARD

- **~190 of 244 decision documents remain unread by any pass**,
  including the 1,883-line discovery-gap-closure pre-registration. Pass
  5 states plainly that the shortlist rests on an incomplete base and
  should be read as the strongest set of candidates given what five
  passes actually found — not proof nothing better exists in the unread
  remainder.
- **The result of record's founding pre-registration was never
  conclusively identified** by any pass, across two separate attempts
  (pass 2, then pass 4 building on pass 2). `2026-08-21-discovery-gap-closure-prereg.md`
  is confirmed to be a *later* document governing the result's
  protection, not its origin.
- **Token rotation — undecided**, sequence recorded above, not executed.
- **The observer's memory/SIGTERM behaviour — undiagnosed.** Today's
  burst-flush anomaly and the recurring SIGTERM hangs are recorded as
  a possible precursor to the crash; no root cause established for
  either.
- **The relevance-classifier gate adjudication — still outstanding.**
  Pass 2 confirmed the gate was run (2026-09-03, resolving a prior
  "unclear if ever run" flag) and found recall clearly failed (90.35%
  vs. ≥95%), but the design's own §3.10/§3.11 abandon-vs-retry call
  remains Oscar's, not yet made.
- **Deletion of dead code deferred until a path forward is chosen.**
  Pass 2's register distinguishes code killed by evidence (one clear
  case: `calculate_geo_elo.py`, removed after being found to have no
  `WHERE` clause) from code killed by neglect (nearly everything else
  marked dormant or abandoned) — that distinction is the input to a
  future deletion decision, not a decision itself.

---

## What this document does NOT do

No verdict on what to do next — the shortlist is a shortlist, not a
decision. The administrative-drift findings and the token section above
are stated as found, not softened.
