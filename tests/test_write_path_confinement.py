"""
test_write_path_confinement.py
Tests for orchestrator/ollama_agent_loop.py's _confined_write_path() — the
boundary check used by tool_write_file / tool_append_to_json_array /
tool_write_handoff.

Fable finding 2d/4 (O-24-class): the old guard `path.startswith(WRITE_PREFIX)`
did NO path resolution, so "/home/parison/trading-swarm/../projects/first-repo/..."
passed while resolving OUTSIDE the repo — a Tier-2/2.5 agent could overwrite
first-repo code (incl. the enforcement layer ollama_agent_loop.py and the frozen
ELO writer update_geo_elo.py), ~/.env_trading, ~/.bashrc, and cron wrappers.
The fix resolves symlinks + ".." to a real absolute path and confirms the target
is strictly inside brain/ before writing.

These tests never write to disk except the hermetic symlink case (tmp_path only) —
_confined_write_path() only resolves and checks; it does not itself write.

Run: python3 -m pytest tests/test_write_path_confinement.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import orchestrator.ollama_agent_loop as loop
from orchestrator.ollama_agent_loop import _confined_write_path, WRITE_ROOT


# The EXACT pre-fix guard, replicated verbatim so we can prove the hole was real
# and that the new check catches precisely what the old one missed. This is the
# non-tautological anchor: for every traversal/in-repo escape below we assert the
# OLD guard PASSED it, then that the NEW check REJECTS it.
_OLD_WRITE_PREFIX = "/home/parison/trading-swarm/"


def _old_guard_passed(path: str) -> bool:
    return path.startswith(_OLD_WRITE_PREFIX)


def _rejected(result) -> bool:
    return isinstance(result, dict) and "error" in result


def _accepted(result) -> bool:
    return isinstance(result, Path)


# ── (b) legitimate agent-output writes still PASS ────────────────
LEGIT = [
    "/home/parison/trading-swarm/brain/agent-outputs/signal-agent/2026-07-10-report.md",
    "/home/parison/trading-swarm/brain/agent-outputs/handoffs/task-123.json",
    "/home/parison/trading-swarm/brain/agent-outputs/quant-research/RQ1.1/out.md",
    "/home/parison/trading-swarm/brain/signals.json",
    "/home/parison/trading-swarm/brain/findings.json",
]


@pytest.mark.parametrize("path", LEGIT)
def test_legit_writes_pass(path):
    result = _confined_write_path(path)
    assert _accepted(result), f"legit path wrongly rejected: {result}"
    assert WRITE_ROOT in result.parents


# ── (a) traversal into first-repo now REJECTED (proven live pre-fix) ──
TRAVERSAL_INTO_FIRST_REPO = [
    "/home/parison/trading-swarm/../projects/first-repo/orchestrator/ollama_agent_loop.py",
    "/home/parison/trading-swarm/../projects/first-repo/scripts/update_geo_elo.py",
    "/home/parison/trading-swarm/brain/../../projects/first-repo/data/x",
]


@pytest.mark.parametrize("path", TRAVERSAL_INTO_FIRST_REPO)
def test_traversal_into_first_repo_rejected(path):
    assert _old_guard_passed(path) is True, "pre-fix guard should have passed this"
    assert _rejected(_confined_write_path(path))


# ── (c) traversal into credentials / system files REJECTED ───────
TRAVERSAL_INTO_SYSTEM = [
    "/home/parison/trading-swarm/../.env_trading",
    "/home/parison/trading-swarm/scripts/cron_wrappers/../../../.bashrc",
    "/home/parison/trading-swarm/brain/../../.ssh/authorized_keys",
]


@pytest.mark.parametrize("path", TRAVERSAL_INTO_SYSTEM)
def test_traversal_into_system_rejected(path):
    assert _old_guard_passed(path) is True, "pre-fix guard should have passed this"
    assert _rejected(_confined_write_path(path))


# ── (d) in-repo-but-outside-brain REJECTED (closes 2d's enforcement-layer hole) ──
IN_REPO_OUTSIDE_BRAIN = [
    "/home/parison/trading-swarm/orchestrator/ollama_agent_loop.py",  # enforcement layer
    "/home/parison/trading-swarm/scripts/cron_wrappers/run_signal_agent.sh",
    "/home/parison/trading-swarm/.gitignore",
]


@pytest.mark.parametrize("path", IN_REPO_OUTSIDE_BRAIN)
def test_in_repo_outside_brain_rejected(path):
    # These PASSED the old guard (they start with the repo prefix) — the in-repo
    # half of finding 2d, now also closed by confining to brain/.
    assert _old_guard_passed(path) is True
    assert _rejected(_confined_write_path(path))


# ── (c) plain absolute paths outside the repo REJECTED ───────────
@pytest.mark.parametrize("path", [
    "/etc/passwd",
    "/home/parison/projects/first-repo/scripts/update_geo_elo.py",
    "/home/parison/.env_trading",
    "/home/parison/trading-swarm-evil/brain/x",   # sibling-prefix trap
    "/home/parison/trading-swarm/brain-evil/x",   # sibling-of-brain prefix trap
])
def test_absolute_outside_rejected(path):
    assert _rejected(_confined_write_path(path))


# ── writing over WRITE_ROOT itself is rejected (can't write a file over the dir) ──
def test_write_root_itself_rejected():
    assert _rejected(_confined_write_path(str(WRITE_ROOT)))


# ── (c) symlink escape REJECTED (hermetic — tmp only) ────────────
def test_symlink_escape_rejected(tmp_path, monkeypatch):
    root = tmp_path / "brain"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    # A symlink placed inside the write root that points outside it.
    (root / "escape").symlink_to(outside)
    monkeypatch.setattr(loop, "WRITE_ROOT", root.resolve())
    result = loop._confined_write_path(str(root / "escape" / "pwned.py"))
    assert _rejected(result), "symlink escape should be rejected"
    # A genuine path inside the root still passes under the same patched root.
    ok = loop._confined_write_path(str(root / "agent-outputs" / "x.md"))
    assert _accepted(ok)
