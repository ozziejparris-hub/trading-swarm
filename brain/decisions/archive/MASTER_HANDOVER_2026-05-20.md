# Master Handover Document — 2026-05-20
*Compiled from all session history: Fresh Start Fixes 1-8, Server Setup 1-6, and current session*
*For use at the start of new chat sessions alongside brain/decisions/ entries*

---

## The North Star (read this first)

Oscar is building a system that tracks all profitable non-bot geopolitics traders on Polymarket, rates them via a custom ELO system, and surfaces actionable signals when elite traders express strong directional conviction. The edge hypothesis: a small minority of traders have genuine information advantages in geopolitics markets. The Columbia/Haifa paper confirmed this — 6 wallets made $1.2M on the Iran strike 71 minutes before news broke. The Van Dyke DOJ indictment (April 2026) confirmed it further — a US Army Special Forces soldier made $409,881 trading on classified Operation Absolute Resolve information.

**The goal is not a trading bot. The goal is an intelligence system that knows, before the market does, which direction geopolitics events will resolve — by tracking the traders who demonstrably know things first.**

Paper trading (Phase 5) requires validation gates. Live trading (Phase 6) requires proven edge. Both are downstream of data accumulation and signal validation that is currently in progress.

---

## Oscar — Personal Context

- Self-taught developer, non-technical background, learns quickly
- Works in national water permitting in the UK (entirely separate from this project)
- GitHub: ozziejparris-hub
- Server username: parison, SSH alias: trading-swarm
- Workflow: Claude (this chat) for architecture/diagnosis/prompts → Claude Code (CC) for implementation → Oscar pastes CC output back for review
- Preferences: production-grade fixes over quick wins, honest assessments, be told explicitly which terminal to use for each command

---

## Hardware & Infrastructure

**Server:** Minisforum UM890 Pro mini PC
- CPU: Ryzen 9 8945HS
- RAM: 96GB DDR5-5600
- Storage: 2TB Kingston NVMe
- OS: Ubuntu 24.04, headless
- GPU: AMD Radeon 780M iGPU (Vulkan backend, OLLAMA_VULKAN=1)
- VPN: Mullvad (Stockholm exit, always-on)
- Mesh: Tailscale
- SSH alias: trading-swarm

**Local machine:** Windows PC with WSL2 (parison@DESKTOP-JC6VGAE)
- Top terminal = WSL2 local
- Bottom terminal = SSH into server

---

## Two Repositories

### first-repo (ozziejparris-hub/first-repo)
**The Polymarket monitoring system.** Runs 24/7 on the server.
- Path: ~/projects/first-repo/
- Database: data/polymarket_tracker.db (SQLite, ~1.8GB, WAL mode)
- Three systemd services:
  - polymarket-monitoring.service — main monitor, active since May 11
  - polymarket-observer.service — health monitoring, active since May 7
  - (background P&L worker runs inside monitoring service)

**Key scripts:**
- monitoring/monitor.py — main monitoring loop, 15-minute cycles
- monitoring/background_pnl_worker.py — continuous P&L calculation
- monitoring/background_backfill_worker.py — NEW: historical trade backfill (added May 2026)
- analysis/unified_elo_system.py — ELO calculation with P&L modifiers
- scripts/daily_maintenance.py — 9-step daily pipeline at 06:00 UTC

**Daily maintenance steps (06:00 UTC):**
1. update_research_exclusions.py — syncs is_flagged, promotes leaderboard traders
2. promote_high_pnl_traders.py — NEW: auto-promotes >$50K P&L traders
3. verify_market_titles.py
4. fast_resolution_check.py — resolves ~14K markets per run (Gamma API)
5. evaluate_new_trader_results.py — scores won/lost trades for flagged traders
6. requeue_resolved_market_traders.py
7. apply_full_elo_modifiers.py
8. resync_position_counts.py
9. write_integration_health.py → brain/integration-health.json

**Sunday-only additions:**
- recalculate_comprehensive_elo.py
- discover_leaderboard_traders.py --limit 100 (NEW: weekly trader discovery)

### trading-swarm (ozziejparris-hub/trading-swarm)
**The multi-agent intelligence system.** Runs 24/7 on the server.
- Path: ~/trading-swarm/
- Service: trading-swarm.service — orchestrator loop, active since May 9

**Key directories:**
- brain/ — shared filesystem memory layer
- brain/signals.json — signal bus between agents
- brain/findings.json — accumulated research findings (31 entries)
- brain/feedback.json — feedback loop state
- brain/integration-health.json — daily health snapshot from first-repo
- brain/integration-contract.md — authoritative schema contract (v1.3)
- brain/model-routing.md — tier assignments and routing decisions
- brain/strategy-notes/ — research directions and pre-registrations
- brain/reference-library/ — book notes and research papers
- brain/agent-outputs/ — per-agent output directories
- brain/decisions/ — session summaries and handover docs (NEW pattern)
- brain/research-scout/pending-review/ — incoming research findings

---

## Database State (as of 2026-05-20)

- Total traders: ~97K
- Monitored (is_flagged=1, research_excluded=0): ~7,900
- Backfill: COMPLETE (0 remaining as of May 20 morning)
- Legendary (ELO > 2175): ~326
- High P&L (>$50K, no bots): ~254
- Clean markets (resolved): ~13,890
- Geopolitics trades: 1,011,882 (Aug 2025 to present)

**Critical data quality notes:**
- JOIN key: trades.market_id = markets.condition_id (NOT markets.market_id)
- Always filter: research_excluded=0, resolved=1, trade_gap_flag=0/NULL, timestamp <= now()
- 199K+ unresolved markets still in backlog — fast_resolution_check resolves ~14K/day
- first_seen is monitor capture date, NOT Polymarket account creation date

---

## ELO System

The ELO system (unified_elo_system.py) uses a multi-modifier architecture:
- base_category_elo: win/loss ELO from resolved trades
- behavioral_modifier: Kelly alignment, patience, timing
- advanced_modifier: contrarian performance, correlation
- pnl_modifier: P&L-weighted score

**Critical known issue:** As of May 2026, 324/333 legendary traders have <10 resolved trades — their ELO is primarily P&L-weighted, not accuracy-validated. This is a data maturity issue, not a bug. Will naturally correct as fast_resolution_check resolves historical markets over ~2-4 weeks.

**Unrealized drag fix (May 15):** The pnl_modifier unrealized_drag formula was catastrophically penalising backfilled traders with many open positions. Fixed: drag now scales by open/closed ratio (drag_weight = min(0.5, 1/open_to_closed_ratio)), capped at realized_pnl.

**Signal filter added (May 19):** STR-003 signal criteria now require resolved_trades_count >= 10 for legendary trader qualification. Prevents signals from traders with thin ELO data.

---

## Trader Discovery Pipeline

Traders enter the monitored pool via three channels:
1. **Live feed** — monitor captures trades in real time (255 traders, avg ELO 2,616)
2. **Leaderboard discovery** — weekly Sunday scan of top geopolitics markets (7,597 traders, avg ELO 1,496)
3. **Manual watchlist** — add_watched_trader.py (2 traders: Wickier + 1 other)

**Key trader:** Wickier (0x1cc16713196d456f86fa9c7387dd326a7f73b8df)
- $660K+ all-time volume on geopolitics markets
- 2,198 trades backfilled, $141K realized P&L, ELO ~1,663
- Used as the test case for backfill system validation

**is_flagged sync:** update_research_exclusions.py syncs is_flagged with research_excluded daily. Leaderboard and watched traders are exempt from the 20-trade minimum.

---

## Strategy Registry

| Strategy | Status | Notes |
|----------|--------|-------|
| STR-001 | SUSPENDED | LP contamination — liquidity providers inflate signal counts |
| STR-001b | SUSPENDED | 0 qualifying signals after STR-001 fix |
| STR-002 | EXPERIMENTAL | Pre-resolution intelligence, 4/10 resolved, 50% accuracy |
| STR-003 | PENDING_REVIEW | Primary strategy — single legendary trader ≥95% directional, ≥$2K, max 2 concurrent, no LP bidirectional holders, now requires resolved_trades_count >= 10 |
| STR-004 | HYPOTHESIS | Capital-weighted legendary aggregate, needs 9 more resolved signals |

**signals.json is currently EMPTY** — existing signals failed rescan due to resolved_trades_count < 10 filter and concurrent markets rule. This is correct behaviour, not a bug.

---

## Phase 5 Gate Status

| Gate | Requirement | Status |
|------|------------|--------|
| Feedback-loop runs | 4+ | 7 ✅ |
| HIGH confidence findings | 3+ (≥20 samples each) | 0 ❌ |
| Pre-resolution accuracy | ≥60% across 10+ markets | 50% across 4 ❌ |
| RQ1.1 + RQ3.2 | Both passed | Pending ❌ |

**Realistic paper trading start:** late July to September 2026, after RQ1.1 June 1 rerun and Putin invasion resolution (~June 2026).

---

## Agent Architecture

**Model tiers:**
- Tier 1: Gemma 4 E2B (Ollama, free, immune system/log watching)
- Tier 2: Gemma 4 E4B (Ollama, free, nothing currently assigned)
- Tier 2.5: Qwen3-Coder 30B-A3B (Ollama, free, research-scout-agent via agentic loop)
- Tier 3: Claude Sonnet 4.6 (Pro subscription via OAuth, all complex agents)
- Tier 4: Claude Opus 4.7 (escalation only, 3x Tier 3 failures)

**CRITICAL:** ANTHROPIC_API_KEY must be unset before claude CLI invocation (fixed May 19 in spawn_agent.sh). The API account has no credits — all Tier 3/4 runs use OAuth Pro subscription.

**Agent schedule:**
- Daily 08:00: research-scout (twice daily at 08:00 and 20:00 UTC, real web search via Claude CLI)
- Monday 07:00: feedback-loop-agent
- Monday 07:30: changelog-monitor
- Monday 08:00: signal-agent (Tier 3 Sonnet)
- Monday 08:00: performance-analyst-agent
- Friday 20:00: code-hygiene-agent
- Saturday 09:00: training-librarian-agent
- Sunday 23:00: integration-test-agent
- Sunday (maintenance): ELO recalculation + leaderboard discovery

---

## Research Scout — Major Fix (May 19)

The research scout was running on Qwen3-Coder locally with no web access and fabricating research from training memory. All 87 fabricated pending-review files were deleted. The scout was rebuilt as scripts/run_research_scout.py — uses claude CLI with web search via Pro subscription. First real run produced 4 verified findings:

1. **Polymarket CLOB V2** — V1 deprecated April 28. Checked: no impact on first-repo (read-only Gamma API only).
2. **arXiv 2605.02287** (Nechepurenko 2026) — Three-layer informed trading detection. CRITICAL reading.
3. **ForesightFlow ILS** (arXiv 2605.00493) — Per-market information leakage score framework.
4. **DeepSeek V4 Preview** — 1.6T params, Apache 2.0, benchmark against Qwen3-Coder when stable.

---

## Key Paper — Must Read for Strategy

**arXiv 2605.02287: Nechepurenko (2026) — Three-layer informed trading detection on Polymarket**

Three complementary detection layers:
1. **Sign-randomization skill classifier** (Gomez-Cram et al.) — 3.14% of accounts classified as "skilled winners", 44% out-of-sample persistence (4x better than equity mutual funds). Validates the ELO approach.
2. **Lifecycle-and-conviction heuristic** — accounts created within 7 days of event, trade exclusively in that event, ≥$1K volume, ≥$1K profit, go dormant after resolution. Flagged Van Dyke's account to the dollar ($409,882 vs $409,881 DOJ indictment).
3. **ILS framework** (ForesightFlow) — per-market information leakage score.

**Critical insight:** Category-conditioning is essential. Platform-wide ELO pools sports/crypto/geopolitics. This directly explains why LEGENDARY accuracy is 57% and QUALIFIED is 92% — geopolitics-specific ELO is needed.

**RQ-LH-001 pre-registered:** Lifecycle heuristic implementation for geopolitics insider detection. 174 candidate traders identified. Pipeline validated. Ready for quant-research-agent implementation.

---

## Quant-Research Pipeline

**Pipeline validated May 19** via quant-test-20260519-v2:
- spawn_agent.sh → CC reads brain → contract validation → DB query → file write → clean exit ✅
- Pre-registration at brain/strategy-notes/rq-lifecycle-heuristic-preregistration-2026-05-19.md

**To run LH-001:**
```bash
cd ~/trading-swarm && bash scripts/spawn_agent.sh \
    "lh001-$(date +%Y%m%d)" \
    "quant-research" \
    "3" \
    "Implement RQ-LH-001 as pre-registered in brain/strategy-notes/rq-lifecycle-heuristic-preregistration-2026-05-19.md. Run the three-phase methodology: Phase 1 identify candidates, Phase 2 compare against control group, Phase 3 cross-reference ELO pool. Write results to brain/agent-outputs/quant-research/LH-001/. Follow pre-registration exactly."
```

---

## Swarm Communication Fixes (May 19)

- **Signal routing fixed:** knowledge_gap_critical, revalidation_requested, hypothesis_ready now route to Telegram alerts instead of being silently dropped
- **Source attribution added:** findings.json entries now include "source" field (agent name) going forward
- **Librarian pipeline fixed:** template updated to actively consume and delete pending-review files, write digest to agent-outputs
- **pending_review_count added to integration-health.json**

---

## Session Summary Pattern (NEW)

At end of each session, Oscar says "done" and Claude writes brain/decisions/YYYY-MM-DD-session-summary.md via CC. This is the primary handover mechanism going forward. The decisions directory accumulates a permanent record of what was built and why.

Combined with this master handover document, a new chat should have full context.

---

## Immediate Next Actions

1. **Spawn quant-research-agent with LH-001** — pipeline validated, pre-registration done
2. **Monday 08:00 UTC** — signal-agent runs with resolved_trades_count >= 10 filter
3. **June 1** — RQ1.1 rerun (pre-registered, critical gate)
4. **~June 2026** — Putin invasion signal resolves (first STR-003 resolution, first real accuracy data point)

---

## Outstanding Items (not urgent)

- Schema compatibility check between first-repo and trading-swarm (flagged multiple times, never done)
- Geopolitics-specific ELO (category-conditioned, essential per Nechepurenko paper)
- ForesightFlow ILS implementation (arXiv 2605.00493) — market selector tool
- ELO-IMP-001: dollar-weighted ROI in pnl_modifier (documented in research-directions.md)
- Training librarian Saturday run missing (investigate next Saturday)

---

## Key Commands Reference

```bash
# SSH to server
ssh trading-swarm

# Service status
sudo systemctl status polymarket-monitoring polymarket-observer trading-swarm --no-pager | grep Active

# Maintenance log
tail -20 ~/projects/first-repo/logs/daily_maintenance.log

# Backfill progress
grep -a "backfill_worker" ~/projects/first-repo/logs/monitoring.log | grep "progress\|queue" | tail -5

# Pool state
sqlite3 ~/projects/first-repo/data/polymarket_tracker.db "SELECT SUM(CASE WHEN is_flagged=1 AND research_excluded=0 THEN 1 ELSE 0 END) as monitored, SUM(CASE WHEN comprehensive_elo > 2175 AND research_excluded=0 THEN 1 ELSE 0 END) as legendary FROM traders;"

# Spawn agent
cd ~/trading-swarm && bash scripts/spawn_agent.sh "<task-id>" "<agent-type>" "3" "<description>"

# CI check
cd ~/trading-swarm && bash ci/run_ci.sh 2>&1 | tail -5

# Push both repos
cd ~/trading-swarm && git push origin master
cd ~/projects/first-repo && git push origin main
```

---

## Opening Prompt for Next Chat

```
This is [Server Setup 7 / next session], continuing from Server Setup 6.

Read brain/decisions/2026-05-20-handover.md for technical state.
Read the attached MASTER_HANDOVER_2026-05-20.md for full context.

Two repos:
- ozziejparris-hub/first-repo — Polymarket monitoring system
- ozziejparris-hub/trading-swarm — Multi-agent trading swarm

Server: SSH as trading-swarm (parison@trading-swarm)
Workflow: Claude prompts CC, Oscar pastes output back.

[Paste recent Telegram hourly reports]
[Paste brain/integration-health.json]
[Paste brain/signals.json if any signals exist]
```

---
*Generated: 2026-05-20*
*Covers: Fresh Start Fixes 1-8 (Nov 2025 - Mar 2026), Server Setup 1-6 (Mar - May 2026)*
*Next session: Server Setup 7*
