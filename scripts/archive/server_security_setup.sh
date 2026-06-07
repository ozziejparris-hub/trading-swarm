#!/bin/bash
# ─────────────────────────────────────────────
# server_security_setup.sh
# Day-one security hardening for the trading swarm server.
# Run this ONCE immediately after the server arrives and
# before starting any agents.
#
# What this script does:
#   1. Creates a dedicated swarm user with restricted permissions
#   2. Configures UFW firewall with agent-specific outbound rules
#   3. Hardens SSH configuration
#   4. Sets correct file permissions on sensitive files
#   5. Configures automatic security updates
#   6. Sets up basic audit logging
#
# Usage:
#   sudo bash scripts/server_security_setup.sh
#
# Run as root or with sudo. One-time setup only.
# ─────────────────────────────────────────────

set -e

echo "══════════════════════════════════════════"
echo "  Trading Swarm — Server Security Setup"
echo "  $(date)"
echo "══════════════════════════════════════════"
echo ""

# ── Verify running as root ──────────────────
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Run this script with sudo"
    echo "  sudo bash scripts/server_security_setup.sh"
    exit 1
fi

MAIN_USER=${SUDO_USER:-parison}
PROJECT_DIR="/home/$MAIN_USER/trading-swarm"
DATA_DIR="/data"

echo "Main user:    $MAIN_USER"
echo "Project dir:  $PROJECT_DIR"
echo "Data dir:     $DATA_DIR"
echo ""

# ─────────────────────────────────────────────
# STEP 1 — Dedicated swarm agent user
# ─────────────────────────────────────────────
echo "── Step 1: Creating dedicated swarm user ──"

# Create swarm user with no login shell and no home directory
# Agents run as this user — no sudo, no root access, no lateral movement
if id "swarm" &>/dev/null; then
    echo "  User 'swarm' already exists, skipping creation"
else
    useradd \
        --system \
        --no-create-home \
        --shell /sbin/nologin \
        --comment "Trading swarm agent user" \
        swarm

    echo "  ✓ Created system user: swarm"
fi

# Give swarm user read access to project and data
# but NOT write access except to specific agent output dirs
chown -R $MAIN_USER:swarm "$PROJECT_DIR" 2>/dev/null || true
chmod -R g+rX "$PROJECT_DIR" 2>/dev/null || true

# Agent output dirs: swarm user can write here
WRITABLE_DIRS=(
    "$PROJECT_DIR/brain/agent-outputs"
    "$PROJECT_DIR/brain/signals.json"
    "$PROJECT_DIR/brain/feedback.json"
    "$PROJECT_DIR/logs"
    "$PROJECT_DIR/worktrees"
)

for dir in "${WRITABLE_DIRS[@]}"; do
    if [ -e "$dir" ]; then
        chown -R $MAIN_USER:swarm "$dir" 2>/dev/null || true
        chmod -R g+w "$dir" 2>/dev/null || true
        echo "  ✓ Swarm write access: $dir"
    fi
done

echo "  ✓ Swarm user configured"
echo ""

# ─────────────────────────────────────────────
# STEP 2 — Database file permissions
# ─────────────────────────────────────────────
echo "── Step 2: Hardening database permissions ──"

# polymarket_tracker.db — read-only for everyone except the
# Polymarket monitoring process that writes to it.
# Agents are supposed to be read-only by convention.
# File permissions make this a hard guarantee.

if [ -f "$DATA_DIR/polymarket_tracker.db" ]; then
    # Owner: main user (Polymarket monitor runs as this user)
    # Group: swarm (agents can read)
    # Permissions: owner rw, group r, others none
    chown $MAIN_USER:swarm "$DATA_DIR/polymarket_tracker.db"
    chmod 640 "$DATA_DIR/polymarket_tracker.db"
    echo "  ✓ polymarket_tracker.db: 640 ($MAIN_USER:swarm)"
else
    echo "  ⚠ polymarket_tracker.db not found at $DATA_DIR"
    echo "    Apply manually after database transfer:"
    echo "    sudo chown $MAIN_USER:swarm /data/polymarket_tracker.db"
    echo "    sudo chmod 640 /data/polymarket_tracker.db"
fi

# Protect the env file with credentials
ENV_FILE="/home/$MAIN_USER/.env_trading"
if [ -f "$ENV_FILE" ]; then
    chmod 600 "$ENV_FILE"
    chown $MAIN_USER:$MAIN_USER "$ENV_FILE"
    echo "  ✓ .env_trading: 600 (owner read/write only)"
else
    echo "  ⚠ .env_trading not found — remember to chmod 600 after creating it"
fi

# Brain files — most should not be world-writable
chmod 750 "$PROJECT_DIR/brain" 2>/dev/null || true
chmod 640 "$PROJECT_DIR/brain/signals.json" 2>/dev/null || true
chmod 640 "$PROJECT_DIR/brain/feedback.json" 2>/dev/null || true

echo ""

# ─────────────────────────────────────────────
# STEP 3 — UFW Firewall
# ─────────────────────────────────────────────
echo "── Step 3: Configuring UFW firewall ──"

apt-get install -y ufw > /dev/null 2>&1

# Reset to clean state
ufw --force reset > /dev/null 2>&1

# Default policies — deny everything in/out, then allow specific
ufw default deny incoming
ufw default deny outgoing

# ── Inbound rules ──
# SSH only — no web server, no open ports
ufw allow in 22/tcp comment "SSH access"

# ── Outbound rules ──
# DNS — needed for all hostname resolution
ufw allow out 53/udp comment "DNS"
ufw allow out 53/tcp comment "DNS TCP"

# HTTPS — all API calls use 443
ufw allow out 443/tcp comment "HTTPS - API calls"

# HTTP — package updates and some API endpoints
ufw allow out 80/tcp comment "HTTP - package updates"

# Ollama local — agents talk to local Ollama on 11434
# This is loopback only, no external exposure needed
# (loopback is always allowed, this is documentation)

# NTP — keep server time accurate (important for timestamps)
ufw allow out 123/udp comment "NTP time sync"

# Enable
ufw --force enable

echo "  ✓ UFW enabled with restrictive outbound rules"
echo ""
echo "  Inbound:  SSH (22) only"
echo "  Outbound: DNS, HTTPS (443), HTTP (80), NTP"
echo "  All other traffic: DENIED"
echo ""
ufw status numbered
echo ""

# ─────────────────────────────────────────────
# STEP 4 — SSH Hardening
# ─────────────────────────────────────────────
echo "── Step 4: Hardening SSH ──"

SSH_CONFIG="/etc/ssh/sshd_config"
SSH_BACKUP="/etc/ssh/sshd_config.backup.$(date +%Y%m%d)"

# Backup original
cp "$SSH_CONFIG" "$SSH_BACKUP"
echo "  Backed up original: $SSH_BACKUP"

# Apply hardening settings
# These are conservative — they disable password auth and root login
# but don't break existing key-based access

cat > /etc/ssh/sshd_config.d/99-trading-swarm-hardening.conf << 'EOF'
# Trading Swarm SSH Hardening
# Applied by server_security_setup.sh

# Disable root login entirely
PermitRootLogin no

# Disable password authentication — key-based only
PasswordAuthentication no
ChallengeResponseAuthentication no

# Disable empty passwords
PermitEmptyPasswords no

# Limit auth attempts
MaxAuthTries 3

# Disconnect idle sessions after 30 minutes
ClientAliveInterval 300
ClientAliveCountMax 6

# Disable X11 forwarding (not needed)
X11Forwarding no

# Only allow specific users to SSH in
# Add your username here
AllowUsers parison

# Log level — captures auth events
LogLevel VERBOSE
EOF

echo "  ✓ SSH hardening config written"
echo ""
echo "  ⚠  IMPORTANT: Before restarting SSH, verify you have"
echo "     SSH key authentication working."
echo "     If you only use passwords, you will lock yourself out."
echo ""
echo "  To restart SSH after verifying key access works:"
echo "    sudo systemctl restart ssh"
echo ""

# ─────────────────────────────────────────────
# STEP 5 — Automatic security updates
# ─────────────────────────────────────────────
echo "── Step 5: Automatic security updates ──"

apt-get install -y unattended-upgrades > /dev/null 2>&1

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};

// Automatically reboot if required, at 3am
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "03:00";

// Remove unused dependencies
Unattended-Upgrade::Remove-Unused-Dependencies "true";

// Email on failure (optional — requires mail setup)
// Unattended-Upgrade::Mail "your@email.com";
// Unattended-Upgrade::MailOnlyOnError "true";
EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

echo "  ✓ Automatic security updates enabled"
echo "  ✓ Auto-reboot at 3am if kernel updates require it"
echo ""

# ─────────────────────────────────────────────
# STEP 6 — Basic audit logging
# ─────────────────────────────────────────────
echo "── Step 6: Basic audit logging ──"

apt-get install -y auditd > /dev/null 2>&1

# Log writes to the database file
if [ -f "$DATA_DIR/polymarket_tracker.db" ]; then
    auditctl -w "$DATA_DIR/polymarket_tracker.db" \
        -p w \
        -k polymarket_db_write 2>/dev/null || true
    echo "  ✓ Audit rule: alert on writes to polymarket_tracker.db"
fi

# Log writes to env files (credential access)
auditctl -w "/home/$MAIN_USER/.env_trading" \
    -p rwa \
    -k credentials_access 2>/dev/null || true
echo "  ✓ Audit rule: alert on credential file access"

# Log execution of spawn_agent.sh (every agent spawn)
if [ -f "$PROJECT_DIR/scripts/spawn_agent.sh" ]; then
    auditctl -w "$PROJECT_DIR/scripts/spawn_agent.sh" \
        -p x \
        -k agent_spawn 2>/dev/null || true
    echo "  ✓ Audit rule: log all agent spawns"
fi

systemctl enable auditd > /dev/null 2>&1
systemctl start auditd > /dev/null 2>&1
echo "  ✓ auditd running"
echo ""

# ─────────────────────────────────────────────
# STEP 7 — Fail2ban for SSH
# ─────────────────────────────────────────────
echo "── Step 7: Fail2ban (SSH brute force protection) ──"

apt-get install -y fail2ban > /dev/null 2>&1

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
EOF

systemctl enable fail2ban > /dev/null 2>&1
systemctl start fail2ban > /dev/null 2>&1
echo "  ✓ Fail2ban running — SSH brute force protection active"
echo "  ✓ 3 failed attempts = 1 hour ban"
echo ""

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
echo "══════════════════════════════════════════"
echo "  Security Setup Complete"
echo "══════════════════════════════════════════"
echo ""
echo "✓ Swarm agent user created (restricted permissions)"
echo "✓ Database file permissions hardened"
echo "✓ UFW firewall: deny-by-default with agent allowlist"
echo "✓ SSH hardened (key-only, no root, no passwords)"
echo "✓ Automatic security updates enabled"
echo "✓ Audit logging active on sensitive files"
echo "✓ Fail2ban protecting SSH"
echo ""
echo "⚠  Manual steps still required:"
echo ""
echo "  1. Set up SSH key authentication BEFORE restarting sshd"
echo "     From your Windows machine:"
echo "     ssh-keygen -t ed25519 -C 'trading-swarm'"
echo "     ssh-copy-id $MAIN_USER@<server-ip>"
echo ""
echo "  2. Restart SSH after verifying key access works:"
echo "     sudo systemctl restart ssh"
echo ""
echo "  3. After transferring polymarket_tracker.db, run:"
echo "     sudo chown $MAIN_USER:swarm /data/polymarket_tracker.db"
echo "     sudo chmod 640 /data/polymarket_tracker.db"
echo ""
echo "  4. Verify firewall allows your API calls:"
echo "     curl -I https://api.anthropic.com"
echo "     curl -I https://api.telegram.org"
echo "     (Both should succeed)"
echo ""
echo "  5. Install and start orchestrator service:
     sudo cp scripts/trading-swarm.service /etc/systemd/system/
     sudo systemctl daemon-reload
     sudo systemctl enable trading-swarm

  6. Set up daily database backup:
     crontab -e
     Add: 0 3 * * * /home/parison/trading-swarm/scripts/backup_database.sh

  7. Check audit logs anytime with:"
echo "     sudo ausearch -k polymarket_db_write"
echo "     sudo ausearch -k credentials_access"
echo "     sudo ausearch -k agent_spawn"
echo ""
