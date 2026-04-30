# ADEMA: Knowledge-State Orchestration for Long-Horizon Agent Tasks

**Source:** arXiv:2604.25849
**Added:** 2026-04-30 (approved from research-scout cycle 4)
**Relevant phases:** Phase 3+ (self-improvement loop design, orchestrator timeout handling)

---

## The Problem ADEMA Solves

Long-running LLM agents accumulate "knowledge state drift": accumulated evidence degrades
across reasoning rounds, intermediate commitments stay implicit, and interruptions fracture
the evolving evidence chain. The result is invalid or incoherent final outputs despite
correct initial setup.

This is the exact failure mode hitting quant-research-agent multi-step tasks. The immune
system currently checks whether output files exist — it does not verify whether the agent
maintained coherent epistemic state across hours of work.

---

## Eight Mechanisms (Ablation-Tested, 60 Runs)

| Mechanism | What it does | Priority |
|---|---|---|
| **Checkpoint-resumable persistence** | Save + restore mid-task state | **CRITICAL** — removing this was the only config producing invalid runs |
| Heterogeneous dual-evaluator governance | Two independent evaluators check reasoning validity | High |
| Adaptive task-mode switching | Switch between exploration/exploitation based on evidence state | Medium |
| Reputation-shaped resource allocation | Allocate compute to highest-confidence paths | Medium |
| Segment-level memory condensation | Condense evidence segments; track pointers not full text | Medium |
| Artifact-first assembly | Build outputs incrementally with verifiable intermediate artifacts | Medium |
| Explicit epistemic bookkeeping | Track which hypotheses have been tested and what they mean | Medium |
| Final-validity checking with safe fallback | Check output validity before committing; fall back on failure | Lower |

---

## Immediately Transferable to This System

### 1. Checkpoint-resumable persistence (most critical)

Quant-research-agent tasks exceeding 4 hours currently hit the orchestrator timeout
and are killed. Restart is from scratch — all intermediate results are lost.

ADEMA pattern: agent writes `checkpoint.json` at each major step containing current
hypothesis state, intermediate results, and next step. Orchestrator reads checkpoint on
restart and passes it as context rather than restarting cold.

Implementation path: Add checkpoint write to quant-research-agent template as a
mandatory step between each research phase. Add checkpoint read to spawn_agent.sh for
Tier 3/4 agents. The orchestrator can then resume rather than respawn.

### 2. Segment-level memory condensation

Relevant for training-librarian-agent which re-reads entire reference library files
each cycle. ADEMA principle: condense reviewed segments into evidence pointers, store
summaries not full text.

Implementation path: Add condensation step to training-librarian template — produce a
`library-index.md` with segment summaries and relevance pointers after each audit.

### 3. Artifact-first assembly

Rather than producing a final report at the end, build outputs incrementally with
verifiable intermediate files. Analogous to writing intermediate JSON results at each
research step rather than just a final summary.

Already partially implemented: quant-research-agent writes phase-by-phase files.
Can be strengthened by requiring each intermediate file to be self-contained and
independently parseable by the orchestrator's immune system.

---

## Relation to Existing System Components

| ADEMA concept | Current system equivalent | Gap |
|---|---|---|
| Checkpoint-resumable persistence | None — restart from scratch | **Major gap** |
| Dual-evaluator governance | Immune system (file existence only) | Immune system checks existence, not epistemic validity |
| Artifact-first assembly | Phase-by-phase output files | Partially done |
| Epistemic bookkeeping | failed-experiments/ directory | No within-session tracking |

**Complements OMC (already in reference library):** OMC addresses multi-agent
coordination (who does what); ADEMA addresses within-task knowledge management (how
a single agent maintains coherent state over time). Different problems, both needed.

---

## When to Apply

- Phase 3: Before designing the self-improvement loop — checkpoint/resume should be
  built into the feedback-loop-agent architecture from the start.
- When addressing the >4h orchestrator timeout — the fix is checkpointing, not
  raising the timeout.
- When quant-research-agent runs fail silently with incomplete outputs — the dual
  evaluator pattern is the diagnostic upgrade.
