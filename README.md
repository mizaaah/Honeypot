# 🍯 Honeypot as a Service

<div align="center">

[![CI/CD](https://github.com/mizaaah/Honeypot/actions/workflows/ci.yml/badge.svg)](https://github.com/mizaaah/Honeypot/actions)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-k3s_v1.35-326CE5?logo=kubernetes&logoColor=white)](https://k3s.io)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Cowrie](https://img.shields.io/badge/Honeypot-Cowrie-FF6B35?logo=linux&logoColor=white)](https://github.com/cowrie/cowrie)
[![Grafana](https://img.shields.io/badge/Dashboard-Grafana-F46800?logo=grafana&logoColor=white)](https://grafana.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Déploiement de honeypots SSH/Telnet en haute disponibilité sur Kubernetes**  
Collecte de logs enrichis · Dashboard Grafana temps réel · API FastAPI · Hardening CIS/ANSSI

</div>

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        🌐 Internet — Attaquants                         │
│                                                                         │
│           SSH/Telnet brute-force, scans, malware downloads...           │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ☸️  Cluster k3s — namespace: honeypot                │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │               🪤  Layer Honeypot (HPA: 1 → 10 pods)             │   │
│  │                                                                  │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │   │
│  │   │  Cowrie Pod  │  │  Cowrie Pod  │  │  Cowrie Pod  │  · · ·  │   │
│  │   │   port 2222  │  │   port 2222  │  │   port 2222  │         │   │
│  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │   │
│  └──────────┼─────────────────┼─────────────────┼─────────────────┘   │
│             │  logs JSON       │                 │                      │
│             └──────────────────┼─────────────────┘                     │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    🔄  Backend / Collecteur                      │   │
│  │                                                                  │   │
│  │   Parse logs JSON Cowrie · Enrichissement GeoIP · Threading     │   │
│  └──────────────────┬────────────────────────────┬─────────────────┘   │
│                     │                            │                      │
│          ┌──────────▼──────────┐    ┌────────────▼──────────┐          │
│          │    📊  Loki         │    │   🗄️  PostgreSQL       │          │
│          │    logs structurés  │    │   données brutes       │          │
│          └──────────┬──────────┘    └────────────┬──────────┘          │
│                     │                            │                      │
│          ┌──────────▼────────────────────────────▼──────────┐          │
│          │                 🌐  FastAPI                        │          │
│          │      REST API · Webhooks · Alertes                │          │
│          └──────────────────────┬────────────────────────────┘          │
│                                 │                                       │
│          ┌──────────────────────▼────────────────────────────┐          │
│          │              📈  Grafana Dashboard                  │          │
│          │   Carte géo · Top commandes · Timeline · Alertes   │          │
│          └───────────────────────────────────────────────────┘          │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  🖥️  Infrastructure — ESXi + k3s                                 │  │
│  │                                                                   │  │
│  │   k3s-master (192.168.240.247)  ·  control-plane                 │  │
│  │   k3s-worker-1 (192.168.240.196)  ·  Cowrie pods + KubeVirt      │  │
│  │   k3s-worker-2 (192.168.240.253)  ·  Backend + Grafana           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack technique

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| 🪤 Honeypot SSH/Telnet | [Cowrie](https://github.com/cowrie/cowrie) | Simulation système vulnérable, capture des attaques |
| ☸️ Orchestration | k3s v1.35 + KubeVirt | Déploiement, scaling, isolation des pods |
| 📈 Auto-scaling | HPA (Horizontal Pod Autoscaler) | Scale 1→10 pods selon charge CPU/mémoire |
| 🔄 Collecteur | Python 3.12 | Parse logs JSON, enrichissement GeoIP |
| 🌐 API | FastAPI | REST API, webhooks, données Grafana |
| 📊 Dashboard | Grafana + Loki | Visualisation temps réel, alertes |
| 🔐 Sécurité infra | CIS Benchmark + ANSSI | Hardening des nodes Kubernetes |
| 🚀 CI/CD | GitHub Actions + Trivy | Build, scan vulnérabilités, push images |

---

## 📁 Structure du projet

```
Honeypot/
├── .github/
│   └── workflows/
│       └── ci.yml              # Pipeline CI/CD — Build, Trivy scan, Push GHCR
├── api/                        # FastAPI — REST API données + dashboards
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── backend/                    # Collecteur Python — parse logs JSON Cowrie
│   ├── collecteur.py           # Collecteur principal (GeoIP, enrichissement)
│   ├── requirements.txt
│   └── Dockerfile
├── cowrie/                     # Honeypot SSH/Telnet Cowrie
│   ├── Dockerfile              # Image Docker → ghcr.io/mizaaah/cowrie:latest
│   ├── cowrie.cfg              # Config Cowrie (ports, logs JSON, hostname)
│   └── docker-compose.yml      # Déploiement local pour tests
├── grafana/                    # Dashboards Grafana temps réel
│   ├── dashboards/             # JSON dashboards (carte géo, top cmds, timeline)
│   └── datasources/            # Connexions Loki / PostgreSQL
├── hardening/
│   └── hardening-nodes.sh      # Hardening Linux — CIS Benchmark + ANSSI
├── k8s/                        # Manifests Kubernetes
│   ├── namespace.yaml          # Namespace honeypot
│   ├── network-policies.yaml   # NetworkPolicy — isolation réseau
│   ├── cowrie/
│   │   ├── deployment.yaml     # Deployment Cowrie + SecurityContext
│   │   ├── configmap.yaml      # ConfigMap cowrie.cfg
│   │   ├── hpa.yaml            # HPA auto-scaling 1→10 pods
│   │   └── service.yaml        # NodePort SSH/Telnet
│   ├── api/
│   │   ├── deployment.yaml
│   │   ├── hpa.yaml
│   │   └── service.yaml
│   └── kubevirt/
│       └── cowrie-vm.yaml      # Deployment Cowrie (pod) via image GHCR
└── README.md
```

---

## 🚀 Déploiement

### Prérequis

- Cluster k3s opérationnel (3 nodes minimum)
- `kubectl` configuré (`KUBECONFIG=/etc/rancher/k3s/k3s.yaml`)
- Accès à `ghcr.io/mizaaah/cowrie:latest` (image CI/CD)

### Déploiement complet

```bash
# 1. Cloner le repo
git clone https://github.com/mizaaah/Honeypot.git
cd Honeypot

# 2. Créer le namespace
kubectl apply -f k8s/namespace.yaml

# 3. Déployer Cowrie
kubectl apply -f k8s/kubevirt/cowrie-vm.yaml

# 4. Vérifier tous les composants
kubectl get all -n honeypot

# 5. Récupérer le port exposé
kubectl get svc -n honeypot
```

### Vérification rapide

```bash
# Statut du cluster
kubectl get nodes

# Pods Cowrie
kubectl get pods -n honeypot

# Logs en temps réel
kubectl logs -n honeypot deployment/cowrie -f

# Test connexion honeypot (remplacer PORT par le NodePort)
ssh root@<WORKER_IP> -p <NODEPORT>
```

---

## 🔐 Hardening des nodes

Le script `hardening/hardening-nodes.sh` applique les recommandations **CIS Benchmark** et **ANSSI** sur chaque node Kubernetes.

### Ce qui est appliqué

| Catégorie | Mesure |
|-----------|--------|
| SSH | Désactivation root, auth par clé uniquement, MaxAuthTries=3, banner légal |
| Kernel | sysctl — protection SYN flood, ICMP, martians, ASLR, kptr_restrict |
| Audit | auditd — journalisation connexions, execve, sudo, modifications /etc |
| Brute-force | fail2ban — ban 24h après 3 échecs SSH (LAN ignoré) |
| Services | Désactivation bluetooth, avahi, cups, postfix, rpcbind... |
| Fichiers | chmod 000 /etc/shadow, chmod 600 /etc/ssh/sshd_config |
| Core dumps | Désactivés (limits.conf + sysctl) |

```bash
# Lancer sur chaque node (master + workers)
sudo bash hardening/hardening-nodes.sh

# Vérifier les règles auditd
auditctl -l

# Vérifier fail2ban
sudo fail2ban-client status sshd
```

> ⚠️ **Important** : Configurer les clés SSH avant de lancer le script (`PasswordAuthentication` sera désactivé).

---

## 🪤 Cowrie — Honeypot SSH

Cowrie simule un faux serveur Linux vulnérable. Tout attaquant qui se connecte croit interagir avec un vrai système.

### Ce que Cowrie capture

- Toutes les commandes tapées par l'attaquant
- Tentatives de téléchargement de malware (`wget`, `curl`)
- Credentials utilisés (login/password)
- Empreinte du client SSH
- Durée et timeline de la session

### Logs JSON

Les logs sont stockés dans `var/log/cowrie/cowrie.json` au format JSONLines :

```json
{
  "eventid": "cowrie.login.failed",
  "username": "root",
  "password": "123456",
  "src_ip": "185.x.x.x",
  "timestamp": "2026-06-17T10:00:00Z"
}
```

### Configuration

La config principale est dans `cowrie/cowrie.cfg` :

```ini
[honeypot]
hostname = server01
listen_endpoints = tcp:2222:interface=0.0.0.0

[output_jsonlog]
enabled = true
logfile = var/log/cowrie/cowrie.json
```

---

## 📊 Observabilité

### Grafana Dashboard

Dashboards temps réel disponibles :

- **Carte géographique** — localisation des attaquants (GeoIP)
- **Top 10 commandes** — commandes les plus utilisées
- **Timeline des attaques** — volume par heure/jour
- **Credentials** — top logins/passwords tentés
- **Alertes** — seuil > 100 tentatives/min

### Loki — Logs structurés

```bash
# Requête LogQL — toutes les connexions réussies
{app="cowrie"} |= "login.success"

# Requête LogQL — top IPs attaquantes
{app="cowrie"} | json | line_format "{{.src_ip}}"
```

---

## 🔄 CI/CD — GitHub Actions

Le pipeline `.github/workflows/ci.yml` se déclenche sur chaque push sur `main` et `dev` :

```
Push → Lint & Tests → Build Docker → Trivy Scan → Push GHCR
                                          ↓
                                   Upload SARIF (GitHub Security)
```

| Job | Description |
|-----|-------------|
| `lint-test` | Ruff linter + pytest avec coverage |
| `build-cowrie` | Build + Trivy scan + push `ghcr.io/mizaaah/cowrie:latest` |
| `build-collector` | Build + Trivy scan + push `ghcr.io/mizaaah/collector:latest` |
| `build-api` | Build + Trivy scan + push `ghcr.io/mizaaah/api:latest` |

---

## 🛡️ Sécurité Kubernetes

### SecurityContext — pods

Chaque pod Cowrie tourne avec les contraintes suivantes :

```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
  seccompProfile:
    type: RuntimeDefault
automountServiceAccountToken: false
```

### NetworkPolicy — isolation réseau

```
Cowrie pods  ──logs──►  Collecteur  ──►  Loki / PostgreSQL
                                    ──►  API
    ▲
    │ SSH/Telnet uniquement
    │
 Internet
```

Aucune communication inter-pods non autorisée. L'IP source des attaquants est préservée via `externalTrafficPolicy: Local`.

---

## 💻 Développement local

```bash
# Lancer Cowrie localement (Docker)
cd cowrie
docker-compose up -d

# Tester la connexion
ssh root@localhost -p 2222

# Voir les logs
docker logs cowrie -f
```

```bash
# Lancer le backend
cd backend
pip install -r requirements.txt
python collecteur.py

# Lancer l'API
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 👥 Équipe

| Membre | Rôle |
|--------|------|
| **Mizaah** | Lead Infrastructure — k3s, KubeVirt, Hardening, ESXi |
| **Enzo** | Infrastructure — Setup VMs, déploiement cluster |
| **joris-landaret** | Backend — Collecteur Python, Loki, API |
| **takseyes** | Backend — Dockerfiles, CI/CD, Grafana |

---

## 📄 License

MIT — voir [`LICENSE`](LICENSE)

---

<div align="center">

*"Security is not a product, but a process."* — Bruce Schneier

</div>
