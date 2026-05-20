import json

file_json = "teste-log-co-ssh.json"

def parser_log_cowrie(log_cowrie):
    try:
        # On lit le fichier log de cowrie qui est en format json
        with open(log_cowrie, "r") as f:
            # On parcourt le fichier ligne par ligne (Format JSON Lines)
            for ligne in f:
                # On nettoie les espaces ou retours à la ligne vides
                ligne = ligne.strip()
                if not ligne:
                    continue

                try:
                    # On charge le JSON de LA ligne actuelle dans un dictionnaire
                    data = json.loads(ligne)
                    print("\n--- Nouveau log détecté ---")
                    print(data)

                    # On extrait les informations dont on a besoin
                    id_evenement = data.get("eventid")
                    ip_attaquant = data.get("src_ip")
                    print(f"[+] Événement détecté : {id_evenement}")
                    print(f"    IP Attaquant : {ip_attaquant}")

                    if id_evenement == "cowrie.login.failed":
                        user = data.get("username")
                        pwd = data.get("password")
                        print(f"    Tentative de connexion avec l'utilisateur '{user}' et le mot de passe '{pwd}'")

                    # C'est ici que tu ajouteras plus tard la fonction GeoIP !
                    # et l'envoi vers Loki/Elasticsearch

                except json.JSONDecodeError:
                    print("[-] Erreur : Une ligne du fichier n'est pas un JSON valide. On passe à la suivante.")
                    continue

        return data

    except json.JSONDecodeError:
        print("[-] Erreur : La ligne n'est pas un JSON valide.")
        return None

parser_log_cowrie(file_json)