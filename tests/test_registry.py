"""
test_registry.py
Basic tests for the agent registry system.
These run on every CI check to confirm core
orchestrator functions work correctly.
"""

import json
import pytest
import tempfile
import os
from pathlib import Path


def create_temp_registry():
    """Create a temporary registry file for testing."""
    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    )
    json.dump({"active_tasks": []}, tmp)
    tmp.close()
    return tmp.name


def test_registry_loads_correctly():
    """Registry file loads as valid JSON."""
    path = create_temp_registry()
    with open(path) as f:
        data = json.load(f)
    assert "active_tasks" in data
    assert isinstance(data["active_tasks"], list)
    os.unlink(path)


def test_registry_add_task():
    """Tasks can be added to registry."""
    path = create_temp_registry()
    with open(path) as f:
        registry = json.load(f)

    registry["active_tasks"].append({
        "id": "test-001",
        "agent": "signal-agent",
        "status": "running"
    })

    with open(path, 'w') as f:
        json.dump(registry, f)

    with open(path) as f:
        loaded = json.load(f)

    assert len(loaded["active_tasks"]) == 1
    assert loaded["active_tasks"][0]["id"] == "test-001"
    os.unlink(path)


def test_signals_file_structure():
    """Signals file has correct structure."""
    signals_path = Path("/home/parison/trading-swarm/brain/signals.json")
    if signals_path.exists():
        with open(signals_path) as f:
            data = json.load(f)
        assert "signals" in data
        assert isinstance(data["signals"], list)


def test_feedback_file_structure():
    """Feedback file has correct structure."""
    feedback_path = Path("/home/parison/trading-swarm/brain/feedback.json")
    if feedback_path.exists():
        with open(feedback_path) as f:
            data = json.load(f)
        assert "approved" in data
        assert "rejected" in data


def test_backtest_validator_pass():
    """Backtest validator correctly passes good results."""
    good_result = {
        "strategy": "test-strategy",
        "sharpe_ratio": 1.5,
        "brier_score": 0.15,
        "total_trades": 50,
        "win_rate": 0.55,
        "max_drawdown": -0.15,
        "verdict": "pass",
        "reason": "all thresholds met"
    }
    path = tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    )
    json.dump(good_result, path)
    path.close()

    import subprocess
    result = subprocess.run(
        ["python3", "ci/validate_backtest.py", path.name],
        capture_output=True,
        cwd="/home/parison/trading-swarm"
    )
    assert result.returncode == 0
    os.unlink(path.name)


def test_backtest_validator_fail():
    """Backtest validator correctly fails bad results."""
    bad_result = {
        "strategy": "bad-strategy",
        "sharpe_ratio": 0.3,
        "total_trades": 10,
        "win_rate": 0.35,
        "max_drawdown": -0.60,
        "verdict": "pass",
        "reason": "agent incorrectly passed this"
    }
    path = tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    )
    json.dump(bad_result, path)
    path.close()

    import subprocess
    result = subprocess.run(
        ["python3", "ci/validate_backtest.py", path.name],
        capture_output=True,
        cwd="/home/parison/trading-swarm"
    )
    assert result.returncode != 0
    os.unlink(path.name)
