# Integration Test Report — 2026-05-14

## Result: ❌ 10 FAILURES

## Test Summary
Total tests: 45
Passed: 35
Failed: 10
Pass rate: 77.8%

## ❌ Failures (action required)
### Test 1: signal_bus_not_empty
- What failed: 0 signals in bus
- Recommended fix: Ensure signal-agent is running and writing signals
- Severity: CRITICAL

### Test 2: expected_signal_types_present
- What failed: Missing signal types: {'revalidation_requested', 'validation_complete', 'str003_directional_single'}
- Recommended fix: Verify signal-agent is generating all expected signal types
- Severity: CRITICAL

### Test 3: validation_pipeline_complete
- What failed: Unmatched validation requests: {'STR-001'}
- Recommended fix: Ensure validation_requested signals have corresponding validation_completed signals
- Severity: CRITICAL

### Test 4: feedback_file_has_entries
- What failed: 0 approved, 0 rejected
- Recommended fix: Ensure feedback-loop-agent is writing feedback entries
- Severity: HIGH

### Test 5: feedback_updated_recently
- What failed: 0 entries in last 7 days
- Recommended fix: Verify feedback-loop-agent is actively maintaining feedback.json
- Severity: HIGH

### Test 6: no_phantom_tasks
- What failed: 1 tasks in registry with no tmux session
- Recommended fix: Clean up registry entries for non-existent tmux sessions
- Severity: HIGH

### Test 7: ci_pipeline_passes
- What failed: CI failed: 
bash: /home/parison/trading-swarm/ci/run_ci.sh: Permission denied
- Recommended fix: Make CI script executable with chmod +x
- Severity: HIGH

### Test 8: brain_file_exists_signals.json
- What failed: Missing or empty: brain/signals.json
- Recommended fix: Ensure signal-agent is writing to signals.json
- Severity: CRITICAL

### Test 9: brain_file_exists_feedback.json
- What failed: Missing or empty: brain/feedback.json
- Recommended fix: Ensure feedback-loop-agent is writing to feedback.json
- Severity: CRITICAL

### Test 10: integration_contract_db_connectable
- What failed: Cannot connect to first-repo DB: database disk image is malformed
- Recommended fix: Check database integrity or restore from backup
- Severity: CRITICAL

## ✅ Passed Suites
- Signal bus integrity
- Agent output integrity
- Feedback loop integrity
- Registry consistency
- CI pipeline integrity
- Brain directory integrity

## Suite Details

### Suite 1: Signal Bus Integrity
Total tests: 4
Passed: 2
Failed: 2

Test 1.1: signal_bus_not_empty - FAILED (0 signals in bus)
Test 1.2: no_stuck_signals - PASSED (All signals processed)
Test 1.3: expected_signal_types_present - FAILED (Missing signal types: {'revalidation_requested', 'validation_complete', 'str003_directional_single'})
Test 1.4: validation_pipeline_complete - FAILED (Unmatched validation requests: {'STR-001'})

### Suite 2: Agent Output Integrity
Total tests: 5
Passed: 5
Failed: 0

### Suite 3: Feedback Loop Integrity
Total tests: 4
Passed: 2
Failed: 2

Test 3.1: feedback_file_has_entries - FAILED (0 approved, 0 rejected)
Test 3.2: feedback_updated_recently - FAILED (0 entries in last 7 days)
Test 3.3: rejection_reasons_specific - PASSED (All rejection reasons are specific)
Test 3.4: no_repeated_failures - PASSED (No repeated failures detected)

### Suite 4: Registry Consistency
Total tests: 4
Passed: 3
Failed: 1

Test 4.1: no_phantom_tasks - FAILED (1 tasks in registry with no tmux session)
Test 4.2: no_ghost_sessions - PASSED (No ghost sessions)
Test 4.3: registry_not_stale - PASSED (Registry is clean)

### Suite 5: CI Pipeline Integrity
Total tests: 3
Passed: 2
Failed: 1

Test 5.1: ci_scripts_exists_and_executable - PASSED (OK)
Test 5.2: ci_pipeline_passes - FAILED (CI failed: bash: /home/parison/trading-swarm/ci/run_ci.sh: Permission denied)
Test 5.3: test_suite_has_coverage - PASSED (15 tests in test suite)

### Suite 6: Brain Directory Integrity
Total tests: 9
Passed: 7
Failed: 2

Test 6.1: brain_file_exists_signals.json - FAILED (Missing or empty: brain/signals.json)
Test 6.2: brain_file_exists_feedback.json - FAILED (Missing or empty: brain/feedback.json)
Test 6.3: json_valid_signals.json - PASSED (Valid JSON)
Test 6.4: json_valid_feedback.json - PASSED (Valid JSON)
Test 6.5: json_valid_agent_registry.json - PASSED (Valid JSON)
Test 6.6: brain_has_content - PASSED (Brain directory: 0.22 MB)
Test 6.7: brain_file_exists_priorities.md - PASSED (OK (2089 bytes))
Test 6.8: brain_file_exists_kpis.md - PASSED (OK (12302 bytes))
Test 6.9: brain_file_exists_definition_of_done.md - PASSED (OK (2089 bytes))

### Suite 7: Integration Contract
Total tests: 3
Passed: 0
Failed: 3

Test 7.1: contract_db_connectable - FAILED (Cannot connect to first-repo DB: database disk image is malformed)
Test 7.2: contract_wal_mode - FAILED (Cannot connect to first-repo DB: database disk image is malformed)
Test 7.3: contract_clean_pool - FAILED (Cannot connect to first-repo DB: database disk image is malformed)

## System Health Assessment
The system is experiencing several critical failures that indicate fundamental issues with core components. The signal bus is empty, which means signal-agent is not functioning or not writing to the signals.json file. The feedback loop is not being maintained, suggesting feedback-loop-agent is not working properly. There's a phantom task in the registry that's not actually running, indicating a drift between the registry and actual system state. The CI pipeline is failing due to permission issues, preventing validation of agent work. Most critically, the first-repo database is corrupted, which affects all research queries and data integrity. The system has not been able to maintain its core memory (brain) properly, with both signals.json and feedback.json being empty. While some agent output directories exist and are structured correctly, the fundamental data flows are broken. The system is not communicating correctly as designed - it's not just that agents are running, but that they are not properly interacting with the system's memory and communication channels.