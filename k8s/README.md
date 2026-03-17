# 🍯 Projet : Honeypot SSH Sécurisé (Kubernetes & KubeVirt)

Ce projet consiste à déployer un honeypot (Cowrie) au sein d'une infrastructure Kubernetes (K3s). Pour garantir une sécurité maximale et éviter les évasions de conteneurs, le honeypot ne tourne pas dans un simple pod, mais à l'intérieur d'une véritable **Machine Virtuelle isolée** gérée par KubeVirt.

## 🏗️ Architecture Technique

| Composant | Technologie |
|---|---|
| Orchestrateur | K3s (Kubernetes allégé) |
| Hyperviseur / VM Layer | KubeVirt (Opérateur + Custom Resources) |
| Provisioning Automatisé | `cloud-init` |
| Honeypot | Image Docker `cowrie/cowrie` |

## ✨ Fonctionnalités Actuelles

- [x] Déploiement d'un cluster K3s fonctionnel
- [x] Installation de KubeVirt et validation de la compatibilité matérielle KVM
- [x] Déploiement "Infrastructure as Code" (IaC) d'une VM Ubuntu 22.04
- [x] Automatisation `cloud-init` :
  - Formatage et montage dynamique d'un disque de données supplémentaire (5 Go)
  - Installation automatisée de Docker
  - Lancement automatique du honeypot Cowrie sur le port `2222` à l'intérieur de la VM

## 🚀 Déploiement de l'infrastructure

### 1. Prérequis

Le nœud Kubernetes doit supporter la virtualisation matérielle (KVM). Pour vérifier :

\`\`\`bash
egrep -c '(vmx|svm)' /proc/cpuinfo
# Doit renvoyer un chiffre supérieur à 0
\`\`\`

### 2. Installation de KubeVirt

\`\`\`bash
export VERSION=v1.2.0
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/$\{VERSION\}/kubevirt-operator.yaml
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/$\{VERSION\}/kubevirt-cr.yaml
\`\`\`

### 3. Lancement de la VM Honeypot

Depuis la racine du projet, appliquez le manifeste :

\`\`\`bash
kubectl apply -f k8s/cowrie-vm.yaml
\`\`\`

Vérifiez que la VM est en statut `Running` :

\`\`\`bash
kubectl get vmi
\`\`\`

## 🚧 Roadmap

| Statut | Tâche |
|---|---|
| ⏳ | **CI/CD & Image Custom** — Pipeline GitHub Actions pour construire notre propre image Cowrie |
| ⏳ | **Réseau** — Service K8s `LoadBalancer` pour exposer la VM à l'extérieur |
| ⏳ | **Hardening** — Sécurisation du nœud principal (CIS/ANSSI, fail2ban) |
