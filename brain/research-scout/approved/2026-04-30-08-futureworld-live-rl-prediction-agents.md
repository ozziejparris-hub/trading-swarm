# FutureWorld: Live RL Environment That Closes the Prediction-to-Outcome Training Loop

## Source
arXiv:2604.26733 — "FutureWorld: A Live Environment for Training Predictive Agents with Real-World Outcome Rewards"
Authors: Zhixin Han et al. (14 authors, Microsoft Research affiliation implied by author names)
Dataset: PredictingFuture/FutureWorld on Hugging Face
Submitted: April 30, 2026

## Domain
Domain 4 — Prediction Market Intelligence
(Secondary: Domain 1 — Agent Orchestration)

## What It Is
FutureWorld is a reinforcement learning environment designed specifically for training agents to predict real-world future events. The training loop works as follows: agent makes predictions on upcoming questions → outcomes materialize in the real world → agent parameters update based on accuracy. The system trains on a continuous stream of prediction questions across diverse real-world event categories, with anti-leakage measures to prevent answer contamination. Three open-source base models were trained "for consecutive days" showing measurable improvement. A historical dataset subset is publicly available on Hugging Face.

## Why It Matters to This System
This is the closest published implementation of what Phase 3+ of this swarm is heading toward: a feedback loop where prediction accuracy on resolved markets drives agent improvement. FutureWorld's architecture — prediction questions → outcome rewards → parameter updates — is analogous to this system's planned feedback-loop-agent cycle, but FutureWorld closes the loop through actual RL fine-tuning rather than strategic rule updates. Two implications: (1) the published historical dataset could provide additional training examples for calibrating Brier score thresholds, supplementing the polymarket_tracker.db data; (2) the RL loop architecture is a more advanced version of what this swarm's Phase 3+ self-improvement layer should aspire to, once sufficient historical accuracy data exists.

## What to Do With It
Monitor for 30 days before acting. Fetch the Hugging Face dataset to assess alignment with Polymarket question types and Brier score ranges. If dataset is high-quality and compatible, flag for quant-research-agent as a supplemental calibration benchmark beyond polymarket_tracker.db. Do not attempt RL fine-tuning of production agents — that's Phase 6+ territory.

## Effort to Implement
Low to assess (< 1 hour to download dataset and check compatibility). High to fully implement (fine-tuning infrastructure is Phase 6+, out of scope now).

## Urgency
This month — download and assess dataset quality; no action required beyond that for current phase.

## Raw Notes
The "anti-leakage" mechanism is the critical detail — FutureWorld explicitly prevents trained models from memorising answers by controlling the training corpus. This is equivalent to the pre-registration requirement in this system's backtest protocol. Good alignment philosophically.

The open-source base models trained in the paper are not named in the abstract. Important to check whether they're locally runnable — if any match the Tier 2 local profile, this becomes a direct model routing candidate for signal-agent.

Check: PredictingFuture/FutureWorld dataset on Hugging Face. Assess: question format, event categories, resolution criteria, date range, volume.
