"""Configuration for Givaudan RAG System"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Chemins de base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = BASE_DIR / "outputs"
LOG_FILE = OUTPUTS_DIR / "log.txt"
CSV_FILE = OUTPUTS_DIR / "rag_answers.csv"

# Configuration OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Configuration RAG
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "3"))

# Configuration Web Search
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

# Configuration Weaviate (Vector Database)
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8090")
WEAVIATE_TOP_K_RETRIEVE = int(os.getenv("WEAVIATE_TOP_K_RETRIEVE", "10"))
WEAVIATE_TOP_K_FINAL = int(os.getenv("WEAVIATE_TOP_K_FINAL", "3"))
WEAVIATE_HYBRID_ALPHA = float(os.getenv("WEAVIATE_HYBRID_ALPHA", "0.7"))

# Configuration Agent Performance
AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "5"))
AGENT_MAX_EXECUTION_TIME = int(os.getenv("AGENT_MAX_EXECUTION_TIME", "30"))

# Configuration Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# System Prompt pour le chatbot
SYSTEM_PROMPT = """Tu es un assistant spécialisé en parfumerie et aromatique, expert de l'entreprise Givaudan.

RÈGLES STRICTES :
1. Tu ne dois répondre qu'aux questions concernant les parfums, arômes, ingrédients et l'entreprise Givaudan
2. Si l'information demandée N'EST PAS dans le contexte fourni, tu dois dire clairement : "Je ne dispose pas de cette information dans ma base de connaissances."
3. Ne jamais inventer ou halluciner des informations
4. Toujours citer les sources quand tu utilises le contexte fourni
5. Être précis, concis et professionnel

PÉRIMÈTRE :
- Histoire et activités de Givaudan
- Composition des parfums et arômes
- Ingrédients naturels et synthétiques
- Processus de création et fabrication
- Tendances et innovations dans le secteur

Si une question sort de ce périmètre, réponds poliment que tu es spécialisé uniquement dans les parfums et arômes Givaudan."""

# Questions de test (utilisées pour baseline et RAG)
TEST_QUESTIONS = [
    "Quelle est l'histoire de l'entreprise Givaudan ?",
    "Quels sont les principaux types d'ingrédients utilisés dans les parfums ?",
    "Quelle est la différence entre les ingrédients naturels et synthétiques ?",
    "Comment se déroule le processus de création d'un parfum ?",
    "Quels sont les métiers clés chez Givaudan ?",
    "Quelles sont les tendances actuelles dans l'industrie des arômes ?",
    "Comment Givaudan assure-t-elle la durabilité de ses ingrédients ?",
    "Qu'est-ce qu'une note de tête, de cœur et de fond dans un parfum ?",
    "Quels sont les principaux marchés de Givaudan ?",
    "Comment fonctionne la pyramide olfactive ?"
]

def validate_config():
    """Valide que la configuration est correcte"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY n'est pas définie. Veuillez créer un fichier .env avec votre clé API.")

    # Créer les dossiers s'ils n'existent pas
    for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUTS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    return True
