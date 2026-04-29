# Efficient Multivariate Kelly Optimization Reveals Sigmoidal Scaling Laws

## Source
https://arxiv.org/abs/2604.24723
arXiv:2604.24723 — "Efficient Multivariate Kelly Optimization Reveals Sigmoidal Scaling Laws"

## Domain
Quantitative Methods

## What It Is
Solves simultaneous multi-bet Kelly optimization — the problem of sizing multiple correlated positions at once — reducing complexity from O(2^N) to O(N) via an integral transform. A second decomposition approach provides solution quality bounds described by a sigmoidal function of subproblem size, enabling accurate Kelly sizing across "hundreds of bets" with quantifiable worst-case error.

## Why It Matters to This System
**Directly upgrades RQ4 series.** The current system design assumes standard single-asset Kelly criterion (brain/strategy-notes/research-directions.md RQ4.1-4.3). But in Phase 4-6 the system will hold multiple simultaneous Polymarket positions, many of which are correlated (the 933 high-correlation pairs in correlation_cache.json). Single-asset Kelly applied independently to each position systematically overfits and risks ruin when correlated events co-resolve — precisely the blow-up scenario RQ5.1 tests for.

This paper provides a tractable O(N) algorithm specifically built for this problem. The sigmoidal scaling law is a practical tool: given a computational budget, you can compute the exact worst-case suboptimality of your Kelly allocation — which is exactly what quant-research-agent needs when presenting sizing recommendations to Oscar.

**Bridges RQ4 and RQ5:** Kelly sizing with explicit correlation handling directly addresses both the single-position sizing questions (RQ4.1-4.3) and the correlated-market blow-up risk (RQ5.1).

## What to Do With It
"New research direction: add RQ4-MULTI to research-directions.md — when quant-research-agent begins Phase 4 position sizing work, implement multivariate Kelly using the O(N) integral transform from this paper instead of independent single-asset Kelly. Note the 933 high-correlation pairs in correlation_cache.json as input to the multivariate optimisation."

## Effort to Implement
Medium (1 day to add to research-directions.md and note implementation approach; High to actually implement in Phase 4)

## Urgency
This month

## Raw Notes
- Standard Kelly for N simultaneous bets requires O(2^N) time and memory — intractable for N > ~20
- Integral transform approach: O(N) for independent bets; decomposition approach gives solution bounds
- Sigmoidal bound: solution accuracy as function of subproblem size follows sigmoidal curve — parameters derivable from low-dimensional problem statistics
- Authors report method handles "hundreds of bets" with quantifiable suboptimality bounds
- No code repo mentioned in abstract — check PDF for supplementary materials when implementing
- Connection to Polymarket: the 933 high-correlation pairs in correlation_cache.json are exactly the N inputs to the multivariate optimisation — the data structure already exists
- Phase 4-6 priority: do not block Phase 2-3 work on this, but note for implementation before live trading
