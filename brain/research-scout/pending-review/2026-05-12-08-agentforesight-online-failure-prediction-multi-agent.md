# AgentForesight: Online Auditing for Early Failure Prediction in Multi-Agent Systems

## Source
https://arxiv.org/abs/2605.08715 — "AgentForesight: Online Auditing for Early Failure Prediction in Multi-Agent Systems" (May 2026). HuggingFace Daily Papers, 2 upvotes.

## Domain
Domain 1 — Agent Orchestration

## What It Is
AgentForesight reframes failure detection in multi-agent LLM systems as "online auditing": a dedicated auditor agent observes each step's trajectory prefix and decides whether to continue or alert at the earliest detectable error, before downstream agents accept and amplify the mistake. The authors trained AgentForesight-7B using RL on a curated 2K-trajectory dataset spanning coding, math, and agentic tasks, achieving +19.9% over GPT-4.1 and 3× lower step localization error.

## Why It Matters to This System
Our immune system currently checks only that tmux sessions exist and output files are non-empty — it detects failures only after they have fully occurred. AgentForesight's core insight maps directly: long-running swarm agents (quant-research-agent, backtest-agent) can produce subtly wrong outputs that pass the file-existence check but cascade silently into incorrect decisions. An online auditor that monitors output trajectory at intermediate steps — e.g., checking whether a quant-research-agent's intermediate statistical outputs are coherent before the final finding is written to brain/findings.json — would catch the class of failure our current immune system misses entirely.

## What to Do With It
Monitor for 30 days before acting — the 7B model would need to run locally on the UM890 Pro, and the technique requires training data specific to our agent types. File concept in reference library under agent orchestration. When the system has 4+ weeks of agent run history, revisit as a candidate for immune system upgrade.

## Effort to Implement
High (1 week+) — requires curating agent-specific trajectory data and fine-tuning a 7B auditor model.

## Urgency
Backlog

## Raw Notes
- Dataset: AFTraj-2K (coding, math, agentic tasks)
- Method: RL-trained auditor with "risk-anticipation" pre-training then step-level error localization refinement
- Outperforms GPT-4.1 and DeepSeek-V4-Pro on their benchmark
- Key architectural requirement: auditor observes trajectory prefix at each step, not just final output
- Application to trading swarm: auditor could flag if quant-research-agent is computing correlations on wrong data slice, before the finding gets filed
- Current immune system gap: we detect "file absent" and "session dead" — we do not detect "file present but contents are subtly wrong"
- Shepherd (arXiv:2605.10913, same day) is a complementary paper — formalized execution tracing infrastructure for meta-agents. Read alongside AgentForesight when implementing.
