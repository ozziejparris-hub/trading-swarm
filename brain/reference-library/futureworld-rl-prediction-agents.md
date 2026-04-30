# FutureWorld: Live RL Environment for Prediction Agent Training

**Source:** arXiv:2604.26733 — "FutureWorld: A Live Environment for Training Predictive Agents with Real-World Outcome Rewards"
**Authors:** Zhixin Han et al. (Microsoft Research affiliation)
**Dataset:** PredictingFuture/FutureWorld on Hugging Face
**Added:** 2026-04-30 (approved from research-scout cycle 4, monitor-only action)
**Relevant phases:** Phase 3 calibration (dataset assessment); Phase 6+ (RL fine-tuning)

---

## What FutureWorld Is

A reinforcement learning environment for training agents to predict real-world future
events. The loop: agent predicts → outcome materialises → parameters update based on
accuracy. Three open-source base models were trained "for consecutive days" showing
measurable improvement.

Key design decision: **anti-leakage measures** prevent answer contamination by controlling
the training corpus. This is philosophically equivalent to this system's pre-registration
requirement — both enforce a separation between the signal and the validation.

Historical dataset subset is publicly available on Hugging Face.

---

## Relevance to This System

### Phase 3 — Dataset Assessment (Low Effort, Immediate)

The publicly available historical dataset could supplement polymarket_tracker.db as a
calibration benchmark. If question formats and Brier score ranges align with Polymarket,
quant-research-agent can validate its calibration models against an independent dataset.

**Action checklist (do this within 30 days):**
- [ ] Fetch PredictingFuture/FutureWorld from Hugging Face
- [ ] Check: question format (binary? probability? multi-class?)
- [ ] Check: event categories — do they overlap with Polymarket market types?
- [ ] Check: resolution criteria — are they deterministic and clearly defined?
- [ ] Check: date range — is there sufficient historical depth (2+ years)?
- [ ] Check: volume — how many resolved questions?
- [ ] If compatible: flag for quant-research-agent as supplemental benchmark for RQ1.1 and RQ3.2

### Phase 3+ — Architecture Reference

FutureWorld's architecture (predict → reward → update) is the most concrete published
implementation of what this swarm's Phase 3+ self-improvement layer is heading toward.
The current feedback-loop-agent updates strategic rules, not model parameters. FutureWorld
is the next step beyond that — closing the loop through actual parameter updates.

Do NOT attempt RL fine-tuning of production agents until Phase 6+. The infrastructure
(GPU for fine-tuning, evaluation harness, rollback mechanism) does not exist yet.

### Model Routing Opportunity (Conditional)

The base models fine-tuned in the paper are not named in the abstract. If any are:
- Open-weight ✓
- Runnable on 96GB RAM (UM890 Pro) ✓
- Text-only or text-primary ✓

...they become a potential Tier 2 candidate for signal-agent (replacing or supplementing
Gemma 4 E4B). Check once paper full-text is available.

---

## Status

- Dataset: NOT YET ASSESSED — fetch and evaluate within 30 days of 2026-04-30
- Model: NOT EVALUATED — check paper full-text for model names and sizes
- RL fine-tuning: OUT OF SCOPE until Phase 6+
