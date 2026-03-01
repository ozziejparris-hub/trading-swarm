
#!/bin/bash
# ─────────────────────────────────────────────
# verify_output.sh
# Verifies an agent actually produced real output.
# Called by orchestrator after every task completion.
# Never trust agent self-reports — verify independently.
#
# Usage:
#   ./scripts/verify_output.sh <task_id> <expected_output_path>
#
# Returns:
#   0 = verified (success)
#   1 = failed verification
# ─────────────────────────────────────────────

TASK_ID=$1
OUTPUT_PATH=$2
MIN_SIZE=${3:-10}  # Minimum file size in bytes

echo "Verifying output for task: $TASK_ID"
echo "Expected file: $OUTPUT_PATH"

# Check file exists
if [ ! -f "$OUTPUT_PATH" ]; then
    echo "FAIL: Output file does not exist"
    echo "  Expected: $OUTPUT_PATH"
    exit 1
fi

# Check file has real content
FILE_SIZE=$(stat -c%s "$OUTPUT_PATH" 2>/dev/null || stat -f%z "$OUTPUT_PATH")
if [ "$FILE_SIZE" -lt "$MIN_SIZE" ]; then
    echo "FAIL: Output file is empty or too small ($FILE_SIZE bytes)"
    exit 1
fi

echo "PASS: Output verified ($FILE_SIZE bytes)"
echo "  File: $OUTPUT_PATH"
exit 0
