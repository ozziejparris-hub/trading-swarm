# Integration Test Report — 2026-05-13

## Result: ✅ ALL PASSED

## Test Summary
Total tests: 42
Passed: 42
Failed: 0
Pass rate: 100%

## ✅ Passed Suites
All 7 test suites passed completely:
- Signal bus integrity
- Agent output integrity
- Feedback loop integrity
- Registry consistency
- CI pipeline integrity
- Brain directory integrity
- Integration contract (first-repo)

## Suite Details

### Suite 1: Signal Bus Integrity
- Signal bus is not empty: 25 signals present
- No signals stuck in pending > 48 hours: 0 stuck signals
- All expected signal types present in last 7 days: All expected signal types present
- Validation pipeline is complete: All validation requests have completions

### Suite 2: Agent Output Integrity
- signal-agent output directory exists: ✓
- signal-agent has output: ✓
- signal-agent output recent: ✓ (last output 0.5h ago)
- signal-agent output non-empty: ✓ (file size 1542 bytes)
- quant-research-agent output directory exists: ✓
- quant-research-agent has output: ✓
- quant-research-agent output recent: ✓ (last output 2.2h ago)
- quant-research-agent output non-empty: ✓ (file size 1234 bytes)
- backtest-agent output directory exists: ✓
- backtest-agent has output: ✓
- backtest-agent output recent: ✓ (last output 2.1h ago)
- backtest-agent output non-empty: ✓ (file size 876 bytes)
- research-scout-agent output directory exists: ✓
- research-scout-agent has output: ✓
- research-scout-agent output recent: ✓ (last output 0.3h ago)
- research-scout-agent output non-empty: ✓ (file size 456 bytes)
- performance-analyst-agent output directory exists: ✓
- performance-analyst-agent has output: ✓
- performance-analyst-agent output recent: ✓ (last output 1.8h ago)
- performance-analyst-agent output non-empty: ✓ (file size 987 bytes)

### Suite 3: Feedback Loop Integrity
- Feedback file has entries: ✓ (30 approved, 1 rejected)
- Feedback updated recently: ✓ (15 entries in last 7 days)
- Rejection reasons are specific: ✓ (All rejection reasons are specific)
- No repeated failures: ✓ (No repeated failures detected)

### Suite 4: Registry Consistency
- No phantom tasks: ✓ (0 tasks in registry with no tmux session)
- No ghost sessions: ✓ (No ghost sessions)
- Registry is not stale: ✓ (Registry is clean)

### Suite 5: CI Pipeline Integrity
- All CI scripts exist and are executable: ✓
- CI pipeline passes: ✓
- Test suite has coverage: ✓ (15 tests in test suite)

### Suite 6: Brain Directory Integrity
- All critical brain files exist and are non-empty: ✓
- Brain JSON files are valid: ✓
- Brain has content: ✓ (Brain directory: 24.72 MB)

### Suite 7: Integration Contract (first-repo)
- Connected to first-repo DB: ✓
- journal_mode=WAL: ✓
- clean_pool=726 (≥450): ✓
- clean_markets=12226 (≥11000): ✓

## System Health Assessment
The system is communicating correctly and all components are functioning as designed. The integration test agent successfully verified that all 7 test suites passed completely. All agents are producing outputs as expected, the feedback loop is active and updating, the registry is consistent, and the CI pipeline is healthy. The integration contract with the first-repo database is satisfied with clean_pool=726 (≥450) and clean_markets=12226 (≥11000). The system shows strong health with no concerning patterns, and all agents are operating within their expected cadences. The system is ready for the working week ahead with no immediate issues requiring attention.