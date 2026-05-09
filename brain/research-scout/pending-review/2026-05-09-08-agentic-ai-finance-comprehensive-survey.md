# Agentic AI in Finance: Comprehensive Survey — Reference Library Addition

## Source
https://arxiv.org/abs/2604.21672 — "Agentic Artificial Intelligence in Finance: A Comprehensive
Survey" (April 2026). Companion reference: arxiv.org/abs/2603.13942 — "AI Agents in Financial
Markets: Architecture, Applications, and Systemic Implications" (March 2026).

## Domain
Domain 2 — Quantitative Methods
Domain 1 — Agent Orchestration

## What It Is
Two complementary surveys released in Q1-Q2 2026 synthesising the agentic AI finance research
landscape. The April 2026 survey (2604.21672) covers system architecture, market applications,
regulatory frameworks, and systemic implications across recent agentic AI deployments in finance.
The March 2026 paper (2603.13942) proposes a four-layer architecture: data perception → reasoning
engine → strategy generation → execution with control. Key argument in the March paper: systemic
implications of AI in finance depend less on model intelligence than on how agent architectures
are distributed, coupled, and governed across institutions.

## Why It Matters to This System
These surveys serve as an authoritative checkpoint against our current design:
1. **Four-layer architecture validation**: Our system (polymarket_tracker.db → signal-agent →
   quant-research-agent → live trading) maps roughly to their data perception → reasoning →
   strategy → execution layers. The survey surfaces what is typically missing or weak at each
   layer in production deployments.
2. **Regulatory framework section**: As Phase 6 approaches, the regulatory landscape for agentic
   AI trading is actively evolving. The survey's regulatory chapter covers emerging frameworks
   relevant to autonomous prediction market agents — a pre-read before Phase 5 integration gate.
3. **Taxonomy of agent failures**: The comprehensive survey catalogs failure modes across market
   applications — useful context for hardening our immune system before Phase 3.

## What to Do With It
Add to reference library: brain/reference-library/agentic-ai-finance-survey.md
Specifically: extract the four-layer architecture taxonomy, the failure mode catalogue, and
the regulatory section into a single reference file. Quant-research-agent should read this
before starting Phase 3 strategy generation tasks.

## Effort to Implement
Low (< 1 hour) to skim and extract the key taxonomy and failure modes.

## Urgency
Backlog — useful reference before Phase 3, not urgent today.

## Raw Notes
- Four-layer architecture (March 2026 paper): data perception, reasoning engine, strategy
  generation, execution with control. Our layers map cleanly to this.
- Key argument: governance and coupling matter more than model capability for systemic outcomes
  — consistent with our own design philosophy (immune system, pre-registration, stopped by
  capability gate criteria not calendar)
- April 2026 survey is comprehensive (multi-author, likely 50+ pages) — worth adding to
  reference library alongside Lopez de Prado, Dixon et al.
- Companion paper on representation homogeneity (2604.22818) is filed separately today —
  that paper is the more immediately actionable one; this survey is longer-term reference
- Neither paper has been in previous scout cycles — both are pre-May but missed in April
  when we had fewer cycles running
- The March paper's four-layer architecture diagram would be useful to document in
  brain/reference-library/ as a cross-check against our own agent design taxonomy
