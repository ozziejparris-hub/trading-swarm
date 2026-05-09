# Coordination as an Architectural Layer: 41-87% Production Failure Rate in LLM Multi-Agent Systems

## Source
https://arxiv.org/abs/2605.03310 — "Coordination as an Architectural Layer for LLM-Based
Multi-Agent Systems" (May 6, 2026). Code, traces, and production agents publicly released.

## Domain
Domain 1 — Agent Orchestration

## What It Is
The paper argues that coordination in multi-agent LLM systems should be a configurable
architectural layer, separable from agent logic and from information access — not an
engineering afterthought. Their key empirical finding: LLM multi-agent systems fail in
production at rates of 41-87%, primarily due to coordination defects rather than model
capability limits. They instantiate the framework using five reference coordination
configurations tested on 100 Polymarket binary markets, deployed as live agents on
Foresight Arena. Using the Murphy decomposition of the Brier score to separate calibration
from discriminative power, three of five predicted outcomes were confirmed; two configurations
dominated the cost-quality efficiency frontier.

## Why It Matters to This System
The 41-87% production failure rate statistic is the key data point: this is not a theoretical
concern but an empirically measured failure mode. Our current orchestrator.py immune system
treats coordination as a side effect of the tmux/registry design — not as a first-class
architectural concern. The paper's separation of coordination from agent logic maps directly
to a potential structural improvement:
- Our current architecture: coordination lives inside orchestrator.py (tightly coupled)
- Their architecture: coordination is a configurable layer the orchestrator can swap
The Polymarket + Foresight Arena test bed means their configurations are directly comparable
to our prediction market use case. The five reference configurations and their cost-quality
tradeoffs are immediately applicable to deciding how our agents coordinate signal handoffs.

## What to Do With It
Add to reference library: create brain/reference-library/coordination-architectural-layer.md
summarising the five coordination configurations and their Polymarket benchmark results.
Longer term: when orchestrator.py reaches Phase 3 refactor point, use their framework to
audit whether our coordination design is a configurable layer or remains tightly coupled
to our agent type definitions.

## Effort to Implement
Low (< 1 hour) to read the code and summarise the five configurations.
Medium (1 day) to apply the Murphy Brier decomposition to our own signal-agent output as a
calibration vs. discrimination diagnostic.

## Urgency
This month — read the paper and reference library entry before Phase 3 orchestrator work.

## Raw Notes
- Five reference coordination configurations — paper doesn't name them in abstract but
  code is publicly released; need to read Appendix B for repository URL
- Murphy decomposition of Brier score: calibration component + resolution component
  — useful to add to backtest-agent evaluation suite
- Three of five predicted outcomes confirmed; two configurations dominated cost-quality frontier
- "Not a general cross-model claim" — results specific to their instantiation, but methodology
  is transferable
- The 41-87% production failure rate source: appears to be cited across several multi-agent
  failure mode papers — worth tracking down the primary citation
- Deployed on Foresight Arena (the on-chain benchmark paper from arxiv 2605.00420) —
  these two papers are companion work, both from May 2026
- Direct relevance to Phase 3: before scaling to multiple simultaneous agents, we should
  audit orchestrator.py's coordination design against this framework
