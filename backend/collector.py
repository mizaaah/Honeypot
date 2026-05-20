import time
import docker
import requests

LOKI_URL = "http://localhost:3100/loki/api/v1/push"


def send_to_loki(line):
    payload = {
        "streams": [
            {
                "stream": {"job": "cowrie", "container": "cowrie2"},
                "values": [[str(int(time.time() * 1e9)), line]],
            }
        ]
    }
    requests.post(LOKI_URL, json=payload)


def collect_logs():
    client = docker.from_env()
    container = client.containers.get("cowrie2")
    print("Collecteur démarré, en attente de logs...")
    for log in container.logs(stream=True, follow=True, tail=10):
        line = log.decode("utf-8").strip()
        if line:
            send_to_loki(line)
            print(f"Log envoyé: {line[:80]}")


if __name__ == "__main__":
    collect_logs()
