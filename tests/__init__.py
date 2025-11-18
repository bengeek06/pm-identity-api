"""
tests/__init__.py
-----------------
Charge les variables d'environnement de test AVANT tout import.
Ce fichier est exécuté en premier par pytest.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Définir FLASK_ENV avant de charger le .env
os.environ["FLASK_ENV"] = "testing"

# Charger le fichier .env.test depuis la racine du projet
project_root = Path(__file__).parent.parent
env_file = project_root / ".env.test"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
