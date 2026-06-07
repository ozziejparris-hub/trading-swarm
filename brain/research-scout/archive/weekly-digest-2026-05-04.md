# Research Scout Weekly Digest — 2026-05-04

## This Week's Findings: 14 items total
## Pending Your Review: 7 items (3 carried from yesterday, 4 new today)

---

### IMMEDIATE ESCALATION — Action Required Now

**DeepSeek V4 Released (April 24 — 10 days ago)**
The single highest-priority watchlist item from model-routing.md has dropped.
V4-Flash (284B/13B active MoE, $0.14/$0.28 per MTok) and V4-Pro (1.6T/49B active, $1.74/$3.48)
are both open-weight (MIT), Ollama-compatible, GGUF available, Anthropic API drop-in.
V4-Pro at $1.74/$3.48 output vs Sonnet at $3/$15 = 4-5x cheaper output tokens.
V4-Flash MoE at Q2 ≈ 71GB — may fit in 96GB DDR5 for local inference.
DeepClaude repo (408 HN points) validates agent loop integration works.
model-routing.md explicitly said: "Halt all Tier 3 cost decisions until V4 drops."
→ **Finding:** pending-review/2026-05-04-08-deepseek-v4-released-open-weights.md
→ **Action:** evaluate V4-Flash local inference on UM890 Pro; benchmark V4-Pro API vs Sonnet on 3 Tier 3 tasks

---

### High Priority (action this week)

- **MiniMax M2.7 open weights** (approved 2026-05-01): Action items already in priorities.md.
  RAM headroom check → GGUF pull → 3-task benchmark → routing decision still outstanding.
  → Pending your action from last Monday's escalation.

- **Prediction Arena: AI agents trading on Polymarket and Kalshi** (arXiv:2604.07355, pending-review):
  Academic benchmark running AI forecasting models live on Polymarket. Competitive landscape context.
  If AI agent accuracy in this benchmark exceeds 60%, raises bar for our Phase 5 accuracy gate.
  → **Action:** read paper to understand baseline AI accuracy on live markets; relevant to Phase 5 gate design.

---

### Medium Priority (action this month)

- **Polymarket Info Leakage 2020-2026** (arXiv:2605.00459, new today):
  6-year study of 12,708 markets. Post-2024 regulatory_formal markets = near-zero leakage.
  Regulatory_announcement markets retain significant leakage.
  → Relevant to RQ3.2 design: pre-stratify by market category before running elite vs market analysis.
  → Finding: pending-review/2026-05-04-08-polymarket-info-leakage-population-scale.md

- **Signal Credibility Index** (arXiv:2604.27041, new today):
  Real-time diagnostic that filters genuine information moves from noise using flow concentration metrics.
  Post-RQ3.2 enhancement for signal-agent — adds credibility gating before forwarding price signals.
  → Finding: pending-review/2026-05-04-08-signal-credibility-index-prediction-markets.md

- **Grok 4.3 — Tier 3 cost reduction candidate** (pending-review, yesterday):
  Improved agentic performance at lower pricing than previous Grok versions.
  → Defer evaluation until DeepSeek V4 benchmark completes — avoid routing churn with multiple candidates active simultaneously.

- **Kimi K2.6 — leading open-weight model** (pending-review, yesterday):
  New Moonshot AI open-weight model, competitive with Sonnet on several benchmarks.
  → Same deferral logic as Grok 4.3. Prioritise V4 evaluation first.

---

### For Reference (no immediate action)

- **FutureWorld: Live RL prediction agents** (arXiv, approved Apr 30):
  Reinforcement learning approach to prediction market agents using live resolution feedback.
  Relevant context for Phase 3+ signal-agent improvement.

- **BTF2 Forecasting Agents Benchmark** (approved Apr 30):
  Standardised benchmark for comparing AI forecasting agent performance. Useful baseline reference.

- **Architectural Heterogeneity in Multi-Agent Forecasting** (approved Apr 30):
  Heterogeneous agent ensembles outperform homogeneous ones on forecasting benchmarks.
  Reinforces swarm design philosophy — agents at different model tiers provide diversity.

- **ADEMA Knowledge State Orchestration** (approved Apr 29):
  Knowledge state tracking for orchestration systems. Relevant to Phase 3 orchestrator improvement.

- **Multivariate Kelly Optimization** (approved Apr 29):
  Sigmoidal scaling laws for multi-asset Kelly bet sizing. Relevant to Phase 4 portfolio construction.

- **Polymarket CFTC US Launch** (approved May 1):
  US markets live under CFTC regulation April 28. Sharp US institutional money entering.
  → US market signal quality watch already in strategy-notes — monitor through mid-June.

- **One Man Company: Heterogeneous Orchestration** (approved Apr 28):
  Production agent orchestration patterns for lean teams.

- **Polymarket Orderbook Microstructure** (approved Apr 28):
  Empirical order flow study — now in reference library.

- **Bayes-Consistent Agentic Orchestration ICML 2026** (new today):
  Position paper arguing orchestration layers should maintain calibrated beliefs and update dynamically.
  Backlog item — relevant for Phase 3 orchestrator redesign.

---

### Discarded This Week: ~40 items

Primary filters applied:
- HuggingFace papers on computer vision, video generation, robotics, audio — not applicable
- Hacker News stories on mesh networking, CAD generation, medical LLM diagnosis — no domain connection
- arXiv cs.AI papers on trip planning, gaming, speech systems — below relevance threshold
- Model releases without agentic coding or cost benchmarks relevant to current tier structure
- Cryptocurrency speculation content (multiple items from Decrypt)
- General "AI industry expansion" announcements (Anthropic ANZ office, AWS compute expansion)

---

### Self-Assessment Note (for weekly record)

DeepSeek V4 was released April 24 — the scout missed it for 10 days. It appeared in HN search (2090 points) and the HuggingFace model tree. The HN monitoring should catch a 2000+ point story. Likely cause: HN daily scan was not reaching the item because it was 3-7 days old by the time each cycle ran. 

Recommended filter adjustment: add a secondary check — after daily HN scan, run a targeted search for any top-priority watchlist items (DeepSeek V4, MiniMax M2.7, Qwen3-Coder) regardless of post date. A 2000-point story about a top watchlist item should never be missed.
