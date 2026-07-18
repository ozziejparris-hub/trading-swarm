# MASTER HANDOVER — 2026-07-18

**Read this first.** This document supersedes scattered session summaries and prior
MASTER_HANDOVER snapshots as the single entry point for a new Claude chat instance
picking up this project. It is a snapshot, not a living doc — if it's more than a
couple weeks old when you're reading it, cross-check `brain/decisions/` for anything
newer before trusting it blindly.

**Read order for a new instance:**
1. This document, in full.
2. `brain/decisions/2026-07-17-edge-proof-experiment-design-FABLE.md` (the experiment spec).
3. Whatever recent session summaries Oscar points you to (`brain/decisions/2026-07-*-session-summary.md`).

---

## 1. SYSTEM ARCHITECTURE

### Two repos, one server

- **`~/projects/first-repo`** — the data/execution layer. Monitoring services, the
  Polymarket trade/trader database, the ELO scoring system. This is where the raw
  data lives and where daily-maintenance/monitoring code runs.
- **`~/trading-swarm`** — the multi-agent orchestration layer. `brain/` (this repo's
  knowledge base — findings, signals, decisions, strategy registry), the orchestrator,
  agent templates, worktree-based agent spawning.
- **Server:** Minisforum UM890 Pro, Ubuntu 24.04. SSH alias `trading-swarm`
  (`ssh trading-swarm` — resolves to `192.168.1.54`, user `parison`, key
  `~/.ssh/id_ed25519`). Both repos live on this one box, under the same user.
- **Live services:** `polymarket-monitoring` and `polymarket-observer` (systemd, running
  continuously, collecting trades/market data). The `trading-swarm` orchestrator service
  is **NOT started** — still gated on a 48h parallel observation run per CLAUDE.md; don't
  start it without Oscar's explicit instruction.
- **DB scale (approx., first-repo `data/polymarket_tracker.db`):** ~14.5GB, ~157K traders,
  9.87M trades, 6.3M positions, ~223K resolved markets, 10,091 resolved geo/elections markets
  specifically (the pool relevant to the current experiment).

### Workflow

- **Chat-Claude** (you, in a normal conversation) — plans, architects, reviews. Does not
  usually touch the server directly.
- **CC (Claude Code)** — implements, over SSH, on the actual server. Does the file edits,
  runs the scripts, commits.
- **Fable** — a more capable model, brought in for big design/audit tasks: the edge-proof
  experiment design, the ELO arc design, the deep swarm audit. Look for `-FABLE.md` suffix
  on decision docs — those are Fable's work product, treated as higher-trust design authority
  for the topics they cover.

### Environment quirks — know these before touching anything

- **`run_tests.py` is the canonical test runner** (first-repo root). Bare `pytest` wrongly
  collects legacy test files that don't belong in the active suite — don't use it directly.
- **Swarm tests need `PYTHONPATH` set** — trading-swarm's test suite won't resolve imports
  without it.
- **Detach long jobs**: `nohup ... & disown`. Both power and internet on this box are flaky
  independently — either one dropping mid-job kills an attached process. This bit the B2
  probe on 2026-07-17 (had to be re-launched detached). Always detach anything that runs
  more than a couple minutes.
- **Commit as soon as tests pass.** Don't let verified work sit uncommitted.
- **WAL-safe backup discipline before bulk writes** — the production DB is in WAL mode;
  back it up properly (not a naive file copy that can miss the WAL) before any bulk write
  operation, especially ELO writer changes.

---

## 2. THE STRATEGIC REFRAME — read this before anything else

**The project has pivoted from "build the system" to "prove the edge."**

After roughly two months of hardening (data integrity fixes, ELO system consolidation,
swarm infrastructure), the foundation is nearly solid. The near-term purpose of all current
work is running the **edge-proof experiment** against real data — not adding more
infrastructure.

**The thesis being tested:** does following the *aggregate* behavior of proven high-ELO
traders produce tradeable edge in geopolitics prediction markets?

Oscar's framing: the edge is not in mirroring any individual trader. It's in (a) having many
skillful traders on the radar simultaneously, plus (b) an ELO system accurate enough to
correctly identify who is genuinely elite. The signal is a **cohort aggregate**, not
individual-trader mimicry.

**Disproof is a valid, valuable outcome.** If the experiment shows no edge, that's grounds
for redirecting the whole project — not a failure to route around. Design every test for
truth, not for confirming the thesis. This shapes everything downstream: pre-registration,
placebo tests, holdout discipline (see §4) all exist because confirmation bias is the
specific failure mode being defended against here.

**The swarm (autonomous multi-agent automation) is deliberately deferred behind the proof.**
Sequencing principle, stated explicitly by Oscar on 2026-07-15: *make it work and prove it
works before automating it.* This is why Tier-3 agents got paused (§5) and why swarm
consolidation work (respawn logic, agent verification) is sitting behind the experiment in
priority, not because it's unimportant.

---

## 3. THE ELO ARC — essentially complete

This has been the spine of the last month of work.

**Root problem:** `comprehensive_elo` (the canonical trader-skill score) was being written
by multiple divergent writer code paths that had drifted apart over time. One consequence
discovered mid-arc: the "behavioral" component of the score had been a silent no-op for
**7 months** — code that looked like it was contributing to the score but structurally
wasn't.

**Solution:** collapse to one canonical pure formula plus an atomic write helper, making
multi-writer divergence structurally impossible going forward (not just fixed today, but
unable to recur).

**Stages, status:**

- **Stage 0 — DONE.** Gate redefined (was measuring the wrong population — see O-20 in
  lessons, §6). Behavioral validation study run: **W_beh = 0** — P&L is the dominant
  predictor (β=0.447, t=72.6), behavioral signal is statistically negligible. Writer C
  (a dead/divergent writer path) deleted.
- **Stage 1 — DONE.** Canonical formula extracted as a pure function. Zero-diff equivalence
  proven against the old scattered logic before cutover.
- **Stage 2 — DONE.** Writer B moved onto the canonical formula. Verified output-neutral on
  live data (no score changes from the migration itself).
- **Stage 3 — DONE (verified), first live run pending.** Writer A moved onto canonical
  formula, bounds turned ON. Dry-run proven safe. **Writer A's first REAL canonical run is
  scheduled Sunday 2026-07-19 03:00.** This is the next thing to check when you pick this up
  (see §7).
- **Stage 4 — no-op.** Since W_beh=0, there's nothing for this stage to do; it's closed by
  the Stage 0 finding.
- **Stage 5 — PENDING.** Cleanup: backfill remaining T-separated `elo_last_updated` values
  (closes ledger item O-3), retire Writer D remnants, unfreeze whatever was frozen during the
  arc. Not urgent, not blocking the experiment, but don't forget it.

---

## 4. THE EDGE EXPERIMENT — where it stands NOW (this is the live work)

**Design doc:** `brain/decisions/2026-07-17-edge-proof-experiment-design-FABLE.md` — read
this in full before doing anything on the experiment. Summary below is not a substitute.

**Shape:** two phases.
- **Phase 1 — backtest.** Pre-registered hypothesis, diagnostic ladder (steps A through D,
  increasing rigor), placebo tests (to catch spurious "edge" from lookahead or noise), strict
  train / validate / frozen-holdout split discipline.
- **Phase 2 — forward paper-trade.** Only reached if Phase 1 clears the pre-registered bar.

### Recent probes/findings feeding into the build

- **B2 (price-history probe) — result: GO.** CLOB `prices-history` is viable as the primary
  entry-price source: 98% token resolution, 100% retention on resolved geo/elec markets in
  the sample, ~30-min granularity matching target, no degradation across the old-vs-recent
  age split tested. Full result: `brain/decisions/2026-07-17-b2-price-history-probe-result.md`.
  Trade-tape stays as designed fallback for the ~2% CLOB can't resolve.
- **O-36 (resolution_date unreliable)** — up to ~29% of markets have `resolution_date` off by
  >14 days from the true resolution event (root cause: `fast_resolution_check.py` stamps
  `datetime.now()` at check-time rather than the true resolution timestamp — a write-time vs
  event-time bug, see recurring pattern #1 in §6). **Workaround validated:** anchor PIT
  (point-in-time) splits on trade-tape-end (MAX trade timestamp for the market) instead of
  `resolution_date`, and drop the ~16% of markets with zero trades (can't anchor those).
  This does **not** block B1. The real fix (correct timestamps captured at write-time, plus a
  backfill of historical rows) is deferred — tracked, not urgent, doesn't gate the experiment.
  Note the asymmetry: `resolution_date` itself is still safe to use for the *knowledge-lag
  margin* (the bug is one-directional / conservative there) — it's specifically PIT
  train/test splits and decay features that need the trade-tape-end anchor instead.
- **O-37 (synthetic/duplicated trades)** — 2,858 rows DB-wide with implausible stats (one
  example: 619K trades at a 222K-share average; distinct `market_id`s sharing identical trade
  counts). Scope, root cause, and ELO impact are **still unscoped** — this is open, not
  resolved. Doesn't block current build sequence but could matter for P&L-based ELO
  inputs if it turns out to be structural rather than a handful of bad rows.

### Build sequence (Fable's order — follow this, don't reorder without reason)

1. **B4 — order-book capture ON.** Start now, regardless of anything else. This is pure data
   collection running forward from today; every day it's delayed is unrecoverable data loss
   for that day.
2. **B1 — PIT replay engine.** Validate by reproducing the 30 existing `elo_snapshots`
   exactly — if the replay engine can regenerate known-good historical snapshots, it's
   trustworthy for generating new ones.
3. **B5 — event clustering.**
4. **B3 — backtest harness.**
5. Train → validate → freeze the spec → run the frozen holdout → GO/NO-GO decision.
6. If GO: Phase 2 (forward paper-trade).

---

## 5. THE OPEN BOARD — ledger items and pending decisions

**Data-integrity, open:**
- O-36 real fix (real timestamps + historical backfill) — deferred, workaround in place (§4).
- O-37 (synthetic/duplicated trades, 2,858 rows DB-wide) — unscoped. Needs a session to
  determine cause and whether it touches ELO/P&L.

**Decisions waiting on Oscar:**
- **`is_taker` / `transaction_hash`** — there's maintenance code (~3h of build time) building
  a filter that nothing currently reads. Fable's experiment design confirms the experiment
  does **not** rescue this — it doesn't end up needing the filter either. Decision needed:
  wire it into something that uses it, or retire it outright. Currently a dangling cost.
- **Tier-3 governance** — the standing, biggest swarm risk: Tier-3 agents run as
  full-shell agents (real filesystem/shell access, not sandboxed to a narrow task
  interface). No governance decision has been made about what constraints should exist
  before this is scaled back up. This is separate from the token-cost pause below — even at
  zero cost, the access-scope question is unresolved.

**Deferred consolidation work (paused behind the experiment, not abandoned):**
- Swarm respawn/verification build — "make the swarm real" (the orchestrator's respawn logic
  is currently more aspirational than functional; flagged in the 2026-07-10 deep audit).
- Paused Tier-3 agents: **research-scout** and **integration-test-agent**, both cron-paused
  2026-07-15 after a token audit rated them not-useful / redundant respectively (full
  rationale: `brain/decisions/2026-07-15-tier3-pause-token-bleed.md`). Plan is to reactivate
  **one at a time**, fixing the underlying issue for each before flipping it back on — not a
  blanket re-enable. Estimated ~15 agent-sessions/week saved by the pause.
- O-29 — shared write/co-write keystone (infrastructure work enabling safe concurrent writes
  across agents; not yet built).
- O-28 — harness invariants (structural checks on the agent harness itself).
- Two small swarm bugfixes from 2026-07-15: `spawn_agent.sh` exit-code handling, and a stale
  entry in the agent registry. Minor, not urgent, still open.

---

## 6. OPERATING DISCIPLINE — how this project works

Adopt these defaults; they were earned the hard way over the past two months.

- **Investigate and prove before acting.** Don't fix what you haven't confirmed is actually
  broken, and don't call something fixed until you've verified it, not just implemented it.
- **Non-tautological tests.** When writing a test for a bug fix, run the test against the
  *pre-fix* code first and confirm it fails. A test that would pass either way isn't testing
  anything.
- **"Show me, don't assert."** CC's and Fable's own claims of task completeness get verified,
  not taken at face value — re-run the check yourself, look at the actual output.
- **Zero-tolerance assertions catch what epsilon tolerances miss.** Where a check can be
  exact (counts, exact-match invariants), make it exact — don't round off the kind of error
  that a fuzzy threshold would quietly absorb.
- **Commit when tests pass. Detach long jobs.** (Repeated from §1 because it keeps mattering.)

### Recurring lesson patterns — these have each bitten more than once

1. **Event-time vs write-time trap.** Hit at least three times: O-21, the O-20 gate
   redefinition, O-33. The bug shape is always the same — code stamps "now" at the moment it
   runs, but the field is supposed to represent when something actually happened. Gate and
   validate on **write-time**, not assumed event-time, whenever a timestamp's provenance is
   unclear. (This is the same root shape as O-36 in §4.)
2. **A metric can look like it measures your concern and actually not.** Examples: a
   maintenance-status banner that showed "OK" without the underlying check actually running;
   a backup process that logged `[OK]` without verifying the backup was restorable; an
   inverted audit check (O-35) that passed exactly when it should have failed; the O-20 gate
   that was silently scoring the wrong population. The lesson: a green check is a claim, not
   proof — read what the check actually does, not just its output.
3. **When you change a system, grep for everything that *measures* it.** O-34/O-35 were both
   cases where a system changed but a monitoring/audit check elsewhere kept assuming the old
   shape, going stale silently. A code change isn't done until every consumer/observer of
   that code has been checked, not just the code's direct callers.
4. **Test the failure mode that actually happens, not the convenient one.** O-14: a clean
   reboot was tested and passed; the real production failure was an *unclean* reboot (a race
   between fsck and something else), which was never tested because it's more annoying to
   simulate. Match your test scenario to the failure that will actually occur, not the one
   that's easiest to write.

---

## 7. IMMEDIATE NEXT STEPS (for whoever picks this up)

1. **Confirm Writer A's Sunday 2026-07-19 03:00 canonical run went clean.** Compare output
   against the pre-run backup; expect scores to be forecast-matched (i.e., match what the
   dry-run predicted). If it diverges, stop and investigate before anything else touches ELO.
2. **Proceed with the edge-experiment build**, per the sequence in §4:
   **B4 (order-book capture ON) → B1 (PIT replay engine, validated against the 30 existing
   `elo_snapshots`)** → onward per Fable's order. The O-36 workaround (trade-tape-end
   anchoring, dropping zero-trade markets) is settled — build on it, don't re-litigate it
   unless new evidence surfaces.
3. Everything in §5 ("open board") is real but secondary — don't let it derail the build
   sequence above unless something there turns out to actively block B1/B4.

---

*This document was generated by Claude (chat instance) on 2026-07-18 at Oscar's request, to
replace ad hoc context-gathering across scattered session summaries for new-chat handoff. It
draws on `brain/decisions/2026-07-17-session-summary.md`,
`2026-07-17-edge-proof-experiment-design-FABLE.md`,
`2026-07-17-b2-price-history-probe-result.md`, `2026-07-15-tier3-pause-token-bleed.md`, and
direct verification of repo state (file listings, git log, SSH config) at time of writing.
Treat it as a snapshot — verify anything load-bearing against current repo state before
relying on it if significant time has passed.*
