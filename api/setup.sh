#!/bin/bash

echo "🔧 Création du venv..."
python3 -m venv .venv

echo "📦 Installation des dépendances..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "✅ Done ! Lance l'API avec :"
echo "   source .venv/bin/activate"
echo "   uvicorn main:app --reload"
