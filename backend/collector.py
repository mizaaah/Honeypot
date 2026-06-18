import time
import json
import requests
import threading
from kubernetes import client, config
from kubernetes.client.rest import ApiException

LOKI_URL = "http://loki:3100/loki/api/v1/push"

# --- Pour l'Alerting ---
COMPTEUR_ATTAQUES = 0
DERNIER_RESET_TEMPS = time.time()
SEUIL_ALERTE = 100
INTERVALLE_TEMPS = 60
lock = threading.Lock()


def verifier_alerte_seuil():
    """Vérifie si le seuil d'attaques par minute est dépassé"""
    global COMPTEUR_ATTAQUES, DERNIER_RESET_TEMPS
    temps_actuel = time.time()

    with lock:
        if temps_actuel - DERNIER_RESET_TEMPS > INTERVALLE_TEMPS:
            COMPTEUR_ATTAQUES = 0
            DERNIER_RESET_TEMPS = temps_actuel

        COMPTEUR_ATTAQUES += 1
        return COMPTEUR_ATTAQUES > SEUIL_ALERTE


def enrichir_geoip(ip_attaquant):
    """Interroge l'API ip-api pour géolocaliser l'IP"""
    if ip_attaquant in ["127.0.0.1", "localhost"] or ip_attaquant.startswith("192.168.") or ip_attaquant.startswith("10."):
        return {"pays": "Local network", "latitude": 0.0, "longitude": 0.0}

    try:
        url = f"http://ip-api.com/json/{ip_attaquant}"
        reponse = requests.get(url, timeout=5)
        donnees_geo = reponse.json()

        if donnees_geo.get("status") == "success":
            return {
                "pays": donnees_geo.get("country"),
                "ville": donnees_geo.get("city"),
                "latitude": donnees_geo.get("lat"),
                "longitude": donnees_geo.get("lon")
            }
    except Exception as e:
        print(f"[-] Erreur GeoIP : {e}")

    return {"pays": "Inconnu", "latitude": 0.0, "longitude": 0.0}


def send_to_loki(log_dict):
    """Envoie le log enrichi à Loki"""
    try:
        line_json_string = json.dumps(log_dict)

        payload = {
            "streams": [
                {
                    "stream": {"job": "cowrie", "app": "cowrie"},
                    "values": [[str(int(time.time() * 1e9)), line_json_string]],
                }
            ]
        }
        reponse = requests.post(LOKI_URL, json=payload, timeout=5)
        if reponse.status_code != 204:
            print(f"[-] Erreur Loki (Code {reponse.status_code}): {reponse.text}")
    except requests.exceptions.RequestException as e:
        print(f"[-] Impossible de joindre Loki : {e}")


def traiter_ligne(line, pod_name):
    """Traite une ligne de log JSON de Cowrie"""
    line = line.strip()
    if not line:
        return

    try:
        log_data = json.loads(line)

        # Ajout du nom du pod source
        log_data["pod"] = pod_name

        # Enrichissement GeoIP
        ip_attaquant = log_data.get("src_ip")
        if ip_attaquant:
            log_data["geoip"] = enrichir_geoip(ip_attaquant)

        id_evenement = log_data.get("eventid")
        log_data["alerte_seuil"] = False

        if id_evenement == "cowrie.login.failed":
            user = log_data.get("username")
            pwd = log_data.get("password")
            print(f"[{pod_name}] Tentative connexion : '{user}' / '{pwd}'")

            if verifier_alerte_seuil():
                print(f"🚨 [ALERTE] Seuil de {SEUIL_ALERTE} attaques/min dépassé !")
                log_data["alerte_seuil"] = True

        elif id_evenement == "cowrie.command.input":
            command = log_data.get("input")
            print(f"[{pod_name}] Commande : {command}")

        elif id_evenement == "cowrie.session.connect":
            ip = log_data.get("src_ip")
            print(f"[{pod_name}] Nouvelle connexion depuis : {ip}")

        # Envoi à Loki
        send_to_loki(log_data)
        print(f"[+] Log envoyé pour IP: {ip_attaquant} depuis {pod_name}")

    except json.JSONDecodeError:
        pass  # Ignorer les lignes non-JSON (démarrage Cowrie, etc.)


def stream_pod_logs(pod_name, namespace="honeypot"):
    """Stream les logs d'un pod Cowrie"""
    v1 = client.CoreV1Api()
    print(f"[*] Démarrage stream logs pour {pod_name}")

    while True:
        try:
            logs = v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                follow=True,
                _preload_content=False,
                tail_lines=0  # Ne lire que les nouveaux logs
            )

            for chunk in logs:
                for line in chunk.decode("utf-8").splitlines():
                    traiter_ligne(line, pod_name)

        except ApiException as e:
            print(f"[-] Erreur API K8s pour {pod_name}: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"[-] Erreur inattendue pour {pod_name}: {e}")
            time.sleep(5)


def collect_logs():
    """Point d'entrée principal — collecte les logs de tous les pods Cowrie"""

    # Charger la config Kubernetes
    try:
        config.load_incluster_config()  # Dans un pod Kubernetes (production)
        print("[*] Config Kubernetes chargée (in-cluster)")
    except Exception:
        config.load_kube_config()       # En local avec kubeconfig
        print("[*] Config Kubernetes chargée (kubeconfig local)")

    v1 = client.CoreV1Api()

    print("[*] Collecteur Honeypot démarré — namespace: honeypot")
    print(f"[*] Seuil d'alerte : {SEUIL_ALERTE} attaques/{INTERVALLE_TEMPS}s")
    print(f"[*] Loki URL : {LOKI_URL}")

    threads = []

    while True:
        try:
            # Récupérer tous les pods Cowrie en Running
            pods = v1.list_namespaced_pod(
                namespace="honeypot",
                label_selector="app=cowrie"
            )

            pods_actifs = [
                pod.metadata.name
                for pod in pods.items
                if pod.status.phase == "Running"
            ]

            # Lancer un thread par pod non encore streamé
            pods_en_cours = [t.name for t in threads if t.is_alive()]

            for pod_name in pods_actifs:
                if pod_name not in pods_en_cours:
                    print(f"[+] Nouveau pod détecté : {pod_name}")
                    t = threading.Thread(
                        target=stream_pod_logs,
                        args=(pod_name,),
                        name=pod_name,
                        daemon=True
                    )
                    t.start()
                    threads.append(t)

            # Nettoyer les threads morts
            threads = [t for t in threads if t.is_alive()]

        except ApiException as e:
            print(f"[-] Erreur liste pods : {e}")

        # Vérifier les nouveaux pods toutes les 30 secondes
        time.sleep(30)


if __name__ == "__main__":
    collect_logs()
