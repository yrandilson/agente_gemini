"""config.py — Configurações centrais"""

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
PORT           = int(os.getenv("PORT", 5000))
VERBOSE        = os.getenv("VERBOSE", "true").lower() == "true"
OUTPUT_DIR     = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY não encontrada!\n"
        "1. Acesse https://aistudio.google.com/apikey\n"
        "2. Crie uma chave gratuita\n"
        "3. Coloque no arquivo .env"
    )
