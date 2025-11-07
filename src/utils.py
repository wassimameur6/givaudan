"""Logging and utility functions"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from src.config import LOG_FILE, LOG_LEVEL

class RAGLogger:

    def __init__(self, log_file: Path = LOG_FILE):
        self.log_file = log_file
        self._setup_logger()

    def _setup_logger(self):
        # Créer le logger
        self.logger = logging.getLogger("RAG_Givaudan")
        self.logger.setLevel(getattr(logging, LOG_LEVEL))

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Create log directory if it doesn't exist
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # File handler
        file_handler = logging.FileHandler(self.log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def section(self, title: str):
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f" {title}")
        self.logger.info(f"{separator}\n")

    def write_header(self):
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f"MINI-RAG GIVAUDAN - Exécution du {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{separator}\n")


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        # Fallback: approximation basique (1 token ≈ 4 caractères)
        return len(text) // 4


def format_sources(sources: list) -> str:
    if not sources:
        return "Aucune source"

    formatted = []
    for i, source in enumerate(sources, 1):
        metadata = source.metadata if hasattr(source, 'metadata') else {}
        source_name = metadata.get('source', 'Document inconnu')
        formatted.append(f"[{i}] {Path(source_name).name}")

    return " | ".join(formatted)


def clean_text(text: str) -> str:
    # Supprimer les espaces multiples
    text = " ".join(text.split())

    # Supprimer les retours à la ligne multiples
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text.strip()


# Créer une instance globale du logger
logger = RAGLogger()
