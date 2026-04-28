# RQ3.2 Theoretical Grounding

## Supporting Literature

### Information Aggregation with AI Agents (Galanis, 2026)
arXiv:2604.20050

Key findings relevant to our system:
- Smarter agents outperform at information aggregation and 
  generate higher profits — directly validates ELO premise
- Performance feedback paradoxically WORSENS aggregation 
  quality — feedback-loop-agent should inject historical 
  accuracy as soft Bayesian prior, NOT hard weight
- Information complexity degrades aggregate accuracy — 
  complex geopolitical markets may have larger exploitable 
  gap for elite forecasters

Implication for feedback-loop-agent:
Do not use raw accuracy metrics as hard weights in 
signal confidence scoring. Use as soft prior only.
