# Session Summary — 2026-07-12

**A major session: a 12-hour power outage survived with uncommitted work intact, the signals.json locking bug fixed and proven, O-14 properly re-resolved on its real failure mode, and the ELO arc finally started — with the long-blocking gate turning out to measure the wrong population entirely.**

---

## 1. Power outage #4 (06:23–19:00 UTC, 12h37m)

Both trees had **uncommitted work** sitting through the outage. Survived intact; committed immediately on recovery (first-repo `8b9a903`, trading-swarm `d7129be`).

**LESSON (recorded):** commit as soon as tests pass — don't let work sit uncommitted overnight in this house.

---

## 2. The signals.json safe-write fix (session's big engineering win, pre-outage)

An exhaustive writer census found **8 writers of `signals.json`** across both repos.

**Critical finding:** the locks were fake. Writers locked the target file itself while the orchestrator locked a `.lock` sidecar — different inodes, so nothing actually serialized.

**Fix:** shared `json_safety` modules in both repos — locking + atomic write (temp → fsync → `os.replace`) + never-reinitialize-on-corrupt-read (backs up and raises instead of silently wiping). All 8 writers routed through it.

**Proven** with a cross-repo concurrency test using real OS processes from both repos — fails against the old code, passes now.

This closed a live data-loss risk: the old code would silently destroy `str003_signals` (months of validation history) on a single corrupt read.

Commits: `8b9a903` (first-repo), `d7129be` (trading-swarm).

---

## 3. O-14 reopened and properly re-resolved

`/mnt/backup` failed to mount after the outage — a **second, different root cause** from July's label-length bug.

**Mechanism:** on an unclean shutdown the drive's ext4 journal is dirty → `systemd-fsck` starts recovering → `nofail` lets `local-fs.target` proceed without waiting → ~2s later the boot transaction prunes the fsck job → `mnt-backup.mount` (which `Requires=` it) never starts. Both prior "reboot tests" were **clean** reboots — never the failure mode that actually happens here.

**Fix:** `x-systemd.automount` (defers mount+fsck outside the boot transaction; verified working) **plus** absence detection (`health_checker.check_offsite_backup` alerts within 60s if unmounted or last backup >26h — it fired a real Telegram alert against the genuinely-broken state).

Commits: first-repo `28b507c`, ledger `f074357`.

**LESSON (generalizable, recorded):** "it survived a reboot" ≠ "it survives the reboot that matters." Test the failure mode that will actually occur, not the convenient one.

---

## 4. The ELO arc finally started — and the gate was measuring the wrong thing

### O-20 gate redefined
The "BUY trades with no position" metric we'd been waiting weeks to see go flat is **99.97% non-flagged discovery-pool traders** (`background_backfill_worker` bulk-loads new traders before promotion) — **not** the ELO baseline population. The ELO population's actual orphan count is **6 trades / 5 traders**. The metric also structurally cannot go flat — every backfill batch spikes it by design. We were blocking the biggest item on the board on a metric that measures a population the arc doesn't touch.

**New gate:** `stale_elo_orphans` (BUY, no position, flagged, non-excluded, >24h) ≤ 20. Current: **4 — passing.**

Also resolved: the backfill "throughput slowdown" was ran-out-of-candidates, not degradation — worker cleared 3,568 in 1.5 days at ~170/hr then idled. Healthy.

### Stage 0c done
Dead Writer C (`integrate_behavioral_elo.py`, 447 lines) deleted after independent dormancy proof. Commit: first-repo `61adaf5`.

### Stage 0b done — the behavioral validation study
`2026-07-12-behavioral-validation-study-STAGE-0B.md`, commit `37d2171`.

**Result: W_beh = 0.** Behavioral's incremental R² over ELO+P&L is 0.00018 (at the detection floor with n=21,218 — a well-powered null, not underpowered). The one p<.05 coefficient has the **wrong sign** and doesn't replicate in the high-reliability subsample. P&L dominates (β=0.447, t=72.6 — a 30x gap). Decomposition: kelly/patience correlate **negatively** with the composite (r≈−0.59) — behavioral isn't internally coherent in the current data.

**Key method note:** using win-rate as the outcome would have shown a large spurious behavioral effect (β=0.52) via the favorite-buying confound (entry_price↔win_rate r=0.98). Market-relative edge was the correct outcome, and choosing it was the study's most consequential decision.

**Oscar's thesis vindicated:** P&L is the best predictor; behavioral must earn its place and hasn't.

**Consequence (big):** with W_beh=0, Stage 2's canonical formula IS today's Writer B, byte-identical. The migration collapses from "change everyone's ELO" to a **pure plumbing unification with zero value changes.** Risk drops enormously.

### Stage 0 status: 3/4 done
0a (redefined + passing), 0b (done), 0c (done). **0d** (harness invariants in OBSERVE mode) not done — rides with Stage 1.

Commit: `7020002` (Stage 0 complete — ledger + ELO design doc updated, W_beh=0).

---

## Next session

- **Stage 1 (+ 0d folded in):** build `comprehensive_elo_formula.py` as a pure function + golden tests (§2.4 worked examples) + property tests + the zero-diff exact-equivalence test proving `compute(w_beh=0, apply_soft_cap=False, apply_floor=False) == WriterB_formula()` across the input grid — this is the test that would have caught the original bonus-leak bug, must assert **zero** diffs, not near-zero. Plus the shadow side-table (`elo_shadow`) + delta report. Zero production writes in Stage 1.
- Confirmatory O-20 sample after a clean 24h cycle (today's was disturbed by the outage).
- Also open: swarm consolidation (fictional respawn / unimplemented `verify_output`), **Oscar's Tier-3 governance decision** (biggest standing swarm risk — full-shell agents undercut every code guard we build), the `is_taker`/`transaction_hash` decision (2–3h/day of maintenance building a filter nothing reads — wire it in or retire it), O-28/O-29 (harness invariants; the shared write/co-write keystone), and the research-scout dedup (prerequisite to Oscar's eventual research-content review).

---

*Session closed 2026-07-12. Both repos committed and pushed.*
