import time
import docker
from docker.errors import NotFound
import requests
import json

LOKI_URL = "http://localhost:3100/loki/api/v1/push"

# --- Pour l'Alerting ---
COMPTEUR_ATTAQUES = 0
DERNIER_RESET_TEMPS = time.time()
SEUIL_ALERTE = 100  # 100 tentatives
INTERVALLE_TEMPS = 60

def verifier_alerte_seuil():
    """Vérifie si le seuil d'attaques par minute est dépassé """
    global COMPTEUR_ATTAQUES, DERNIER_RESET_TEMPS
    temps_actuel = time.time()

    # Si une minute s'est écoulée, on réinitialise le compteur
    if temps_actuel - DERNIER_RESET_TEMPS > INTERVALLE_TEMPS:
        COMPTEUR_ATTAQUES = 0
        DERNIER_RESET_TEMPS = temps_actuel

    COMPTEUR_ATTAQUES += 1

    # On retourne True si le seuil est dépassé, sinon False
    return COMPTEUR_ATTAQUES > SEUIL_ALERTE

def enrichir_geoip(ip_attaquant):
    """Interroge l'API ip-api pour géolocaliser l'IP"""
    # On évite de géolocaliser les IPs locales de test (localhost)
    if ip_attaquant in ["127.0.0.1", "localhost"] or ip_attaquant.startswith("192.168."):
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
        print(f"[-] Erreur lors de l'enrichissement GeoIP : {e}")

    return {"pays": "Inconnu", "latitude": 0.0, "longitude": 0.0}

def send_to_loki(log_dict):
    """Transforme le dictionnaire en JSON string et l'envoie à Loki """
    try:
        # On convertit le dictionnaire enrichi en chaîne de caractères JSON
        line_json_string = json.dumps(log_dict)

        payload = {
            "streams": [
                {
                    "stream": {"job": "cowrie", "container": "cowrie2"},
                    "values": [[str(int(time.time() * 1e9)), line_json_string]],
                }
            ]
        }
        reponse = requests.post(LOKI_URL, json=payload, timeout=5)
        if reponse.status_code != 204:
            print(f"[-] Erreur Loki (Code {reponse.status_code}): {reponse.text}")
    except requests.exceptions.RequestException as e:
        print(f"[-] Impossible de joindre Loki : {e}. Le log est mis de côté.")

def collect_logs():
    client = docker.from_env()
    try:
        container = client.containers.get("cowrie2")
    except NotFound:
        print("Le conteneur 'cowrie2' est introuvable. Vérifiez que P4 l'a démarré.")
        return

    print("Collecteur démarré, en attente de logs...")

    for log in container.logs(stream=True, follow=True, tail=10):
        line = log.decode("utf-8").strip()
        if line:
            try:
                # 1. Transformation en dictionnaire
                log_data = json.loads(line)

                # 2. Extraction de l'IP et enrichissement GeoIP
                ip_attaquant = log_data.get("src_ip")
                if ip_attaquant:
                    log_data["geoip"] = enrichir_geoip(ip_attaquant)

                # 3. Logique d'affichage et d'alerting
                id_evenement = log_data.get("eventid")

                # Par défaut, pas d'alerte sur le log
                log_data["alerte_seuil"] = False

                if id_evenement == "cowrie.login.failed":
                    user = log_data.get("username")
                    pwd = log_data.get("password")
                    print(f"Tentative de connexion avec l'utilisateur '{user}' et le mot de passe '{pwd}'")

                    # VÉRIFICATION DU SEUIL D'ALERTE
                    # Si la fonction renvoie True, on passe le champ à True dans le JSON
                    if verifier_alerte_seuil():
                        print(f"🚨 [ALERTE SÉCURITÉ] Seuil de {SEUIL_ALERTE} attaques dépassé !")
                        log_data["alerte_seuil"] = True

                elif id_evenement == "cowrie.command.input":
                    command = log_data.get("input")
                    print(f"Commande tapée par le hacker : {command}")

                # 4. Envoie du dictionnaire proprement enrichi à Loki
                send_to_loki(log_data)
                print(f"[+] Log enrichi et envoyé pour l'IP: {ip_attaquant}")

            except json.JSONDecodeError:
                # On ignore proprement les lignes qui ne sont pas du JSON
                continue


if __name__ == "__main__":
    collect_logs()
