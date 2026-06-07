#!/bin/bash
# ─────────────────────────────────────────────
# pre_server_security_check.sh
# Run this from WSL2 BEFORE the server arrives.
# Checks and prepares security prerequisites on
# your Windows machine side.
#
# Usage:
#   bash scripts/pre_server_security_check.sh
#
# Does NOT require sudo. Safe to run anytime.
# ─────────────────────────────────────────────

echo "══════════════════════════════════════════"
echo "  Pre-Server Security Check"
echo "  Run from WSL2 before server arrives"
echo "  $(date)"
echo "══════════════════════════════════════════"
echo ""

PASS=0
WARN=0
FAIL=0

check_pass() { echo "  ✓ $1"; ((PASS++)); }
check_warn() { echo "  ⚠ $1"; ((WARN++)); }
check_fail() { echo "  ✗ $1"; ((FAIL++)); }

# ─────────────────────────────────────────────
# CHECK 1 — SSH key exists
# ─────────────────────────────────────────────
echo "── SSH Key ──"

if [ -f "$HOME/.ssh/id_ed25519" ]; then
    check_pass "SSH ed25519 key exists at ~/.ssh/id_ed25519"
elif [ -f "$HOME/.ssh/id_rsa" ]; then
    check_warn "SSH RSA key found — ed25519 is preferred but RSA works"
    echo "         To generate ed25519: ssh-keygen -t ed25519 -C 'trading-swarm'"
else
    check_fail "No SSH key found"
    echo ""
    echo "  Generate one now:"
    echo "    ssh-keygen -t ed25519 -C 'trading-swarm'"
    echo "  Accept the default location (~/.ssh/id_ed25519)"
    echo "  Set a passphrase (recommended)"
    echo ""
fi

# Check SSH config exists
if [ -f "$HOME/.ssh/config" ]; then
    check_pass "SSH config file exists"
else
    check_warn "No SSH config file — consider creating one for convenience"
    echo ""
    echo "  Suggested ~/.ssh/config entry (fill in server IP when known):"
    echo "    Host trading-swarm"
    echo "      HostName <server-ip>"
    echo "      User parison"
    echo "      IdentityFile ~/.ssh/id_ed25519"
    echo "      ServerAliveInterval 60"
    echo ""
fi

echo ""

# ─────────────────────────────────────────────
# CHECK 2 — .gitignore protects credentials
# ─────────────────────────────────────────────
echo "── .gitignore Credential Protection ──"

GITIGNORE="$HOME/trading-swarm/.gitignore"

if [ ! -f "$GITIGNORE" ]; then
    check_fail ".gitignore not found at ~/trading-swarm/.gitignore"
else
    # Check for .env patterns
    if grep -q "\.env" "$GITIGNORE"; then
        check_pass ".env files are gitignored"
    else
        check_fail ".env files are NOT in .gitignore — credentials could be committed"
        echo "  Add to .gitignore: .env*"
    fi

    # Check for specific credential files
    if grep -q "\.env_trading" "$GITIGNORE"; then
        check_pass ".env_trading specifically gitignored"
    else
        check_warn ".env_trading not explicitly in .gitignore"
        echo "  Add: .env_trading"
    fi

    # Check no actual env files are tracked
    if git -C "$HOME/trading-swarm" ls-files | grep -q "\.env"; then
        check_fail "WARNING: .env file is tracked by git — remove immediately"
        echo "  Run: git rm --cached .env_trading"
    else
        check_pass "No .env files tracked in git"
    fi
fi

echo ""

# ─────────────────────────────────────────────
# CHECK 3 — No credentials in git history
# ─────────────────────────────────────────────
echo "── Credential Scan in Git History ──"

if [ -d "$HOME/trading-swarm/.git" ]; then
    # Quick scan for common credential patterns in recent commits
    SUSPICIOUS=$(git -C "$HOME/trading-swarm" log \
        --all \
        --full-history \
        --oneline \
        -50 \
        -S "TELEGRAM_\|ANTHROPIC_API\|sk-ant\|bot[0-9]" \
        2>/dev/null | wc -l)

    if [ "$SUSPICIOUS" -gt 0 ]; then
        check_fail "Possible credentials found in git history ($SUSPICIOUS commits)"
        echo "  Review with: git log -S 'TELEGRAM_' --all"
        echo "  If found, use git-filter-repo to scrub history"
    else
        check_pass "No obvious credentials found in recent git history"
    fi
else
    check_warn "Not inside a git repo — skipping history scan"
fi

echo ""

# ─────────────────────────────────────────────
# CHECK 4 — Current .env file permissions
# ─────────────────────────────────────────────
echo "── Env File Permissions (WSL2) ──"

ENV_FILE="$HOME/.env_trading"

if [ -f "$ENV_FILE" ]; then
    PERMS=$(stat -c "%a" "$ENV_FILE")
    if [ "$PERMS" = "600" ]; then
        check_pass ".env_trading permissions: 600 (owner only)"
    else
        check_warn ".env_trading permissions: $PERMS (should be 600)"
        echo "  Fix with: chmod 600 ~/.env_trading"
    fi

    # Check it's not world-readable
    if [ "$PERMS" = "644" ] || [ "$PERMS" = "664" ] || [ "$PERMS" = "666" ]; then
        check_fail "CRITICAL: .env_trading is world-readable"
        echo "  Run immediately: chmod 600 ~/.env_trading"
    fi
else
    check_warn ".env_trading not found on WSL2"
    echo "  Expected at: ~/.env_trading"
    echo "  Will need to recreate on the server"
fi

echo ""

# ─────────────────────────────────────────────
# CHECK 5 — Verify .gitignore has all sensitive patterns
# ─────────────────────────────────────────────
echo "── Sensitive File Patterns in .gitignore ──"

REQUIRED_PATTERNS=(
    "*.db"
    ".env"
    "*.log"
    "__pycache__"
)

if [ -f "$GITIGNORE" ]; then
    for pattern in "${REQUIRED_PATTERNS[@]}"; do
        if grep -q "$pattern" "$GITIGNORE"; then
            check_pass ".gitignore covers: $pattern"
        else
            check_warn ".gitignore missing pattern: $pattern"
        fi
    done
else
    check_fail ".gitignore not found"
fi

echo ""

# ─────────────────────────────────────────────
# CHECK 6 — server_security_setup.sh is committed
# ─────────────────────────────────────────────
echo "── Security Script in Repo ──"

if [ -f "$HOME/trading-swarm/scripts/server_security_setup.sh" ]; then
    check_pass "server_security_setup.sh is in the repo"

    if git -C "$HOME/trading-swarm" ls-files \
        "scripts/server_security_setup.sh" | grep -q .; then
        check_pass "server_security_setup.sh is committed to git"
    else
        check_warn "server_security_setup.sh exists but is not committed"
        echo "  Run: git add scripts/server_security_setup.sh && git commit"
    fi
else
    check_fail "server_security_setup.sh not found"
    echo "  Download and place at: ~/trading-swarm/scripts/server_security_setup.sh"
fi

echo ""

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
echo "══════════════════════════════════════════"
echo "  Pre-Server Check Complete"
echo "══════════════════════════════════════════"
echo ""
echo "  ✓ Passed:   $PASS"
echo "  ⚠ Warnings: $WARN"
echo "  ✗ Failed:   $FAIL"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "  Address all FAILED checks before server arrives."
    echo ""
elif [ "$WARN" -gt 0 ]; then
    echo "  No critical issues. Address warnings when convenient."
    echo ""
else
    echo "  All checks passed. Ready for server setup."
    echo ""
fi

echo "  When server arrives, run on the server:"
echo "    sudo bash scripts/server_security_setup.sh"
echo ""
echo "  Day-one SSH setup sequence:"
echo "    1. Get server IP from supplier"
echo "    2. SSH in with password (first time only):"
echo "       ssh parison@<server-ip>"
echo "    3. Copy your SSH key:"
echo "       ssh-copy-id -i ~/.ssh/id_ed25519 parison@<server-ip>"
echo "    4. Test key login works (open new terminal):"
echo "       ssh parison@<server-ip>"
echo "    5. Once key login works, run security setup:"
echo "       sudo bash ~/trading-swarm/scripts/server_security_setup.sh"
echo "    6. Restart SSH to apply hardening:"
echo "       sudo systemctl restart ssh"
echo "    7. Test you can still SSH in (new terminal before closing old one)"
echo ""
