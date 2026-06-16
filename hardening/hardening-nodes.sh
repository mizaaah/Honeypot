#!/usr/bin/env bash
# =============================================================================
# Hardening Linux — Nodes Kubernetes Honeypot
# Référentiel : CIS Benchmark Linux + Guide ANSSI
# Usage : sudo bash hardening-nodes.sh
# =============================================================================

set -euo pipefail
LOG="/var/log/hardening-honeypot.log"
exec > >(tee -a "$LOG") 2>&1

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
info() { echo -e "        $*"; }

echo "============================================================"
echo " Hardening Linux — $(hostname) — $(date)"
echo "============================================================"

# --------------------------------------------------------------------------
# 1. SSH — Désactivation root + durcissement (ANSSI R67, CIS 5.2)
# --------------------------------------------------------------------------
echo ""
echo ">> 1. Hardening SSH"

SSH_CFG="/etc/ssh/sshd_config"
cp "$SSH_CFG" "${SSH_CFG}.bak.$(date +%s)"

declare -A SSH_PARAMS=(
  ["PermitRootLogin"]="no"
  ["PasswordAuthentication"]="no"
  ["PermitEmptyPasswords"]="no"
  ["X11Forwarding"]="no"
  ["MaxAuthTries"]="3"
  ["LoginGraceTime"]="30"
  ["AllowTcpForwarding"]="no"
  ["ClientAliveInterval"]="300"
  ["ClientAliveCountMax"]="2"
  ["Protocol"]="2"
  ["IgnoreRhosts"]="yes"
  ["HostbasedAuthentication"]="no"
  ["UsePAM"]="yes"
  ["LogLevel"]="VERBOSE"
  ["Banner"]="/etc/ssh/banner"
)

for key in "${!SSH_PARAMS[@]}"; do
  val="${SSH_PARAMS[$key]}"
  if grep -qE "^#?${key}" "$SSH_CFG"; then
    sed -i "s|^#\?${key}.*|${key} ${val}|" "$SSH_CFG"
  else
    echo "${key} ${val}" >> "$SSH_CFG"
  fi
  info "${key} = ${val}"
done

# Banner légal
cat > /etc/ssh/banner << 'EOF'
##############################################################
# Systeme de securite — Acces non autorise interdit
# Toute connexion est enregistree et analysee
##############################################################
EOF

systemctl restart ssh && ok "SSH durci et redemarré"

# --------------------------------------------------------------------------
# 2. Paramètres kernel sysctl (CIS 3.x, ANSSI R9, R10)
# --------------------------------------------------------------------------
echo ""
echo ">> 2. Paramètres sysctl"

SYSCTL_CFG="/etc/sysctl.d/99-honeypot-hardening.conf"
cat > "$SYSCTL_CFG" << 'EOF'
# Réseau — protection contre les attaques courantes
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.ip_forward = 1          # Nécessaire pour Kubernetes
net.ipv6.conf.all.disable_ipv6 = 0  # IPv6 requis pour K8s

# Kernel — durcissement mémoire et accès
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.sysrq = 0
fs.suid_dumpable = 0
kernel.randomize_va_space = 2
kernel.perf_event_paranoid = 3

# Filesystem
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
EOF

sysctl --system > /dev/null && ok "Paramètres sysctl appliqués"

# --------------------------------------------------------------------------
# 3. Installation et configuration de auditd (CIS 4.x)
# --------------------------------------------------------------------------
echo ""
echo ">> 3. auditd — journalisation des appels système"

apt-get install -y auditd audispd-plugins > /dev/null 2>&1

cat > /etc/audit/rules.d/honeypot.rules << 'EOF'
# Supprimer les règles existantes
-D
# Buffer
-b 8192
# Echecs critiques
-f 2

# Surveillance des connexions réseau
-a always,exit -F arch=b64 -S connect -k network_connect
-a always,exit -F arch=b64 -S accept -k network_accept

# Surveillance des exécutions de commandes
-a always,exit -F arch=b64 -S execve -k exec_commands

# Surveillance des modifications de fichiers critiques
-w /etc/passwd -p wa -k passwd_changes
-w /etc/shadow -p wa -k shadow_changes
-w /etc/ssh/sshd_config -p wa -k sshd_config
-w /etc/sudoers -p wa -k sudoers_changes

# Surveillance des montages
-a always,exit -F arch=b64 -S mount -k mounts

# Accès aux fichiers de log Cowrie
-w /cowrie/var/log/ -p rwa -k cowrie_logs

# Tentatives d'élévation de privilèges
-a always,exit -F arch=b64 -S ptrace -k ptrace
-w /usr/bin/sudo -p x -k sudo_exec
EOF

systemctl enable --now auditd && ok "auditd installé et configuré"

# --------------------------------------------------------------------------
# 4. fail2ban — protection contre le brute-force sur le node lui-même
# --------------------------------------------------------------------------
echo ""
echo ">> 4. fail2ban"

apt-get install -y fail2ban > /dev/null 2>&1

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
backend  = systemd

[sshd]
enabled  = true
port     = ssh
logpath  = %(sshd_log)s
maxretry = 3
bantime  = 86400
EOF

systemctl enable --now fail2ban && ok "fail2ban configuré"

# --------------------------------------------------------------------------
# 5. Désactivation des services inutiles
# --------------------------------------------------------------------------
echo ""
echo ">> 5. Services inutiles"

SERVICES_TO_DISABLE=(
  bluetooth avahi-daemon cups postfix rpcbind nfs-server
  nis telnet xinetd rsh-server talk
)

for svc in "${SERVICES_TO_DISABLE[@]}"; do
  if systemctl is-enabled "$svc" 2>/dev/null | grep -q enabled; then
    systemctl disable --now "$svc" 2>/dev/null
    info "Désactivé : $svc"
  fi
done
ok "Services inutiles désactivés"

# --------------------------------------------------------------------------
# 6. Permissions fichiers critiques (CIS 6.x)
# --------------------------------------------------------------------------
echo ""
echo ">> 6. Permissions fichiers"

chmod 644 /etc/passwd
chmod 000 /etc/shadow
chmod 644 /etc/group
chmod 600 /etc/ssh/sshd_config
chmod 700 /root

ok "Permissions appliquées"

# --------------------------------------------------------------------------
# 7. Désactivation du core dump
# --------------------------------------------------------------------------
echo ""
echo ">> 7. Core dumps"

echo "* hard core 0" >> /etc/security/limits.conf
echo "* soft core 0" >> /etc/security/limits.conf
echo "ulimit -S -c 0 > /dev/null 2>&1" >> /etc/profile
ok "Core dumps désactivés"

# --------------------------------------------------------------------------
# 8. Résumé
# --------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Hardening terminé — $(date)"
echo " Log complet : $LOG"
echo "============================================================"
echo ""
warn "ACTIONS MANUELLES RESTANTES :"
echo "  1. Configurer les clés SSH uniquement (PasswordAuthentication=no)"
echo "  2. Vérifier que K8s peut toujours communiquer après les NetworkPolicy"
echo "  3. Tester fail2ban : ssh -o NumberOfPasswordPrompts=4 root@localhost"
echo "  4. Lancer 'auditctl -l' pour vérifier les règles audit"
echo "  5. Reboot recommandé pour activer tous les paramètres kernel"
