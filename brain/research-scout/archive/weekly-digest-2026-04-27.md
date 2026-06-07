# Research Scout Weekly Digest — 2026-04-27 (Monday)

## This Week's Findings: 4 items
## Pending Your Review: 4 items

---

### High Priority (action this week)

- **Polymarket CTF Exchange V2 API breaking changes** → `pending-review/2026-04-27-13-polymarket-v2-api-breaking-changes.md`
  EIP-712 domain version bump + new pagination + submit response change. Cutover is April 28 ~11:00 UTC. Audit `orchestrator/task_templates/` for market-builder-agent API patterns before this agent is ever spawned. System is not yet live — no production incident, but the clock is running.

- **DeepSeek V4 open weights released** → `pending-review/2026-04-27-13-deepseek-v4-open-weights-released.md`
  V4-Flash at $0.14/$0.28 per MTok vs Sonnet at $3.00/$15.00 — 53x cheaper output, within 1 percentage point on SWE-bench Verified. This fires the explicit Tier 3 freeze trigger in `brain/model-routing.md`. Schedule a 3-task benchmark comparison before committing to a routing change. Sovereignty question (Chinese-hosted API) is the blocker — Oscar decides the line.

### Medium Priority (action this month)

- **Claude Opus 4.7 released — Tier 4 model string stale** → `pending-review/2026-04-27-13-claude-opus-4-7-model-routing-update.md`
  Model ID should be `claude-opus-4-7` in `brain/model-routing.md` and `orchestrator/orchestrator.py`. Note: 35% tokenizer overhead means effective per-task cost increases despite flat per-token pricing. Low effort (<1 hour) — two string replacements.

### For Reference (no action needed)

- **Machine Spirits: LLM agents in heterogeneous asset markets** → `pending-review/2026-04-27-13-machine-spirits-llm-agents-in-markets.md`
  Peer-reviewed empirical validation that sophisticated LLMs exploit unsophisticated agents in mixed markets. Confirms RQ0.2's bot exclusion premise and provides supporting literature for RQ7.1 signal crowding risk. Add as citation before quant-research-agent begins RQ0.2.

---

### Discarded This Week: 3 items

- **"Dissecting AI Trading: Behavioral Finance and Market Bubbles"** (arXiv:2604.18373) — Covers LLM behavioral biases (disposition effect, recency weighting) in trading agents. Interesting but low applicability: this system tracks human forecaster ELO, not LLM trading decisions. Overlaps with Machine Spirits thematically. Discarded.
- **HuggingFace daily papers below top result** — Video analysis, 3D reconstruction, LLM safety detection, state space attention. Zero intersection with 6 relevance domains.
- **arXiv cs.MA agent orchestration survey papers** — Several 2026 surveys on multi-agent coordination topologies (chain, star, mesh). No new technical substance beyond what is already implemented in orchestrator.py. Discarded as general knowledge, not actionable.

---

### Sources Checked This Cycle
- ✅ HuggingFace Daily Papers (April 27)
- ✅ arXiv q-fin recent (April 21-27)
- ✅ arXiv cs.AI/cs.MA recent
- ✅ Karpathy autoresearch repo (no new commits)
- ✅ DeepSeek/HuggingFace model releases
- ✅ Polymarket API changelog
- ✅ Anthropic news (Opus 4.7)
- ⚠️ Twitter/X accounts — not accessible via web fetch; flagged for Phase 2 autonomous source intelligence

---

### Signal to Watch This Week
The Polymarket V2 cutover on April 28 is the highest-urgency item. If the system goes live before market-builder-agent templates are audited for v2 API patterns, the first spawned market-builder will fail silently on order submission. This needs a 30-minute audit before the trading-swarm service is ever started.
