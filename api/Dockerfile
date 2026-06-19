FROM python:3.12-slim-bookworm

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY main.py .

# Utilisateur non-root (hardening)
RUN useradd -m -u 1001 appuser
USER appuser

EXPOSE 8000

# Liveness probe friendly : uvicorn avec reload désactivé en prod
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
