# TradingAgents — Multi-Agent LLM Financial Trading Framework (54k Stars)

## Source
https://github.com/TauricResearch/TradingAgents
Apache-2.0. 54,518 stars, +932 stars today (trending #1 Python on GitHub 2026-04-29).

## Domain
Agent Orchestration + Equities and Futures Intelligence

## What It Is
Open-source multi-agent trading framework that mirrors real-world trading firm structure: four specialist analyst agents (fundamentals, sentiment, news, technical) feed into a researcher team (bullish/bearish perspectives), a trader decision agent, and a risk management / portfolio manager layer. Built on LangGraph, supports OpenAI, Anthropic, DeepSeek, Qwen, and local Ollama. Targets equities (stocks) only. Research-grade; not production-ready.

## Why It Matters to This System
**Domain 5 architecture reference:** When this system expands to equities (Phase 6+), TradingAgents is the most-starred concrete implementation of multi-agent LLM trading. Rather than designing the equities agent architecture from scratch, the analyst-specialist → debate → portfolio-manager pipeline is a proven pattern to evaluate and adapt.

**Three specific transferable patterns:**

1. **Multi-agent debate (bullish/bearish researcher team):** The structured debate before a trading decision is a more principled version of our current immune system veto pattern. The "two-sided argument before commit" design reduces the risk of single-agent overconfidence — applicable to our pre-resolution intelligence layer when signal quality is uncertain.

2. **Role specialisation that mirrors trading firm structure:** The fundamentals / sentiment / news / technical split maps cleanly to what we need for equities expansion. The existing signal-agent architecture could be extended with specialist sub-agents using this division.

3. **Ollama support with Anthropic fallback:** TradingAgents already solved the hybrid routing problem (local Ollama models for cheap tasks, API models for complex ones), which is the same architecture we use. Studying their implementation may surface optimisations for our spawn_agent.sh tier routing.

**Competitive intelligence:** 54k stars with +932 today means this is the current reference implementation for anyone building multi-agent trading. If this system's approach is compared to TradingAgents, the key differentiator is: prediction markets (not equities) + ELO-based skill filtering (not raw LLM analyst opinions) + Kelly position sizing. Worth knowing the competitive landscape.

## What to Do With It
"Add to reference library: create brain/reference-library/tradingagents-equity-framework.md summarising the analyst-specialist architecture and multi-agent debate pattern. Review when designing equities expansion in Phase 6+. Note the bullish/bearish debate mechanism as a pattern to evaluate for pre-resolution intelligence signal validation."

## Effort to Implement
High (1 week+ for equities expansion; Low for reference library entry)

## Urgency
Backlog

## Raw Notes
- Language: Python. License: Apache-2.0. Docker support, CLI and programmatic API
- Agent roles: Fundamentals Analyst, Sentiment Analyst, News Analyst, Technical Analyst → Researcher (bull/bear) → Trader → Risk Management / Portfolio Manager
- LLM support: OpenAI, Google, Anthropic, xAI, DeepSeek, Qwen, GLM, OpenRouter, local Ollama
- Explicitly research-grade — no performance benchmarks reported, no production disclaimer
- Equities-only — no prediction market, crypto, or futures support in current form
- LangGraph dependency: adds a framework dependency not in our current stack; evaluate trade-offs before adopting in this codebase
- 54k stars makes this the most adopted multi-agent trading framework on GitHub by a wide margin
- Chinese-enhanced fork (TradingAgents-CN) at 25k stars — indicates strong adoption in China, which correlates with DeepSeek/Qwen model integration patterns
