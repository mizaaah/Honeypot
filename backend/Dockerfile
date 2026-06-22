FROM python:3.12-slim-bookworm

WORKDIR /app

# Mise à jour système sans supprimer Perl (essentiel sur slim)
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY collector.py .

# Utilisateur non-root (hardening)
RUN useradd -m -u 1001 appuser
USER appuser

CMD ["python", "collector.py"]
