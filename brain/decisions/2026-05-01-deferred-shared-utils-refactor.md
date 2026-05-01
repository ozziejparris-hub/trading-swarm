# Decision Record: Deferred shared_utils.py Refactor

Date: 2026-05-01
Decided by: Oscar
Status: Deferred
Review trigger: After 2026-06-01 RQ1.1 rerun, when Phase 5 gate risk is reduced

---

## Decision

Defer the creation of `orchestrator/shared_utils.py` and the associated
caller refactors. Revisit after RQ1.1 and RQ3.2 are validated.

---

## Context

The 2026-05-01 code-hygiene-agent run identified four duplicate code patterns:
- 3 divergent `send_telegram()` implementations
- 4 SQLite read-only connection patterns (one missing WAL pragma)
- 2 `load_json` implementations with inconsistent error handling
- 2 `load_env` implementations

Consolidating these into `orchestrator/shared_utils.py` would require
touching 6 files including `orchestrator/orchestrator.py` and the two
Phase 5 gate scripts (`rq1_1_elo_persistence.py`, `rq3_2_crowd_vs_elite.py`).

---

## Reason for Deferral

Blast radius is too wide during the Phase 5 gate validation window.
An import error in a worktree (e.g. shared_utils.py not on the Python path
during an RQ script run) would silently fail a gate-critical run.
The inconsistency is a latent risk but not an active bug.

---

## Action Required

After June 1 2026 RQ1.1 rerun (or whenever Phase 5 gate risk clears):
implement `orchestrator/shared_utils.py` consolidation as described in
the hygiene agent's Proposal B (see `brain/agent-outputs/code-hygiene/2026-05-01-weekly.md`).
Include the WAL pragma fix for `run_feedback_loop_agent.py` `get_db_conn()`.
