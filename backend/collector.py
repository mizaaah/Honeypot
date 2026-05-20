import time
import docker
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")


def create_index():
    if not es.indices.exists(index="cowrie-logs"):
        es.indices.create(
            index="cowrie-logs",
            body={
                "mappings": {
                    "properties": {
                        "message": {"type": "text"},
                        "timestamp": {"type": "float"},
                    }
                }
            },
        )
        print("Index cowrie-logs créé")


def collect_logs():
    client = docker.from_env()
    container = client.containers.get("cowrie2")
    print("Collecteur démarré, en attente de logs...")
    for log in container.logs(stream=True, follow=True, tail=10):
        line = log.decode("utf-8").strip()
        if line:
            doc = {"message": line, "timestamp": time.time()}
            es.index(index="cowrie-logs", document=doc)
            print(f"Log envoyé: {line[:80]}")


if __name__ == "__main__":
    create_index()
    collect_logs()
