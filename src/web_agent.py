"""Web Search Agent using SerpAPI"""
from typing import Optional
from src.config import SERPAPI_API_KEY, validate_config
from src.utils import logger


class WebSearchAgent:

    def __init__(self):
        validate_config()
        self.serpapi_available = bool(SERPAPI_API_KEY)

        if self.serpapi_available:
            try:
                from langchain_community.utilities import SerpAPIWrapper
                self.search = SerpAPIWrapper(serpapi_api_key=SERPAPI_API_KEY)
                logger.info("Web Search Agent initialisé avec SerpAPI")
            except Exception as e:
                logger.warning(f"SerpAPI non disponible: {e}")
                self.serpapi_available = False
                self.search = None
        else:
            logger.warning("SERPAPI_API_KEY non configurée - recherche web désactivée")
            self.search = None

    def search_web(self, query: str) -> Optional[str]:
        if not self.serpapi_available or not self.search:
            return "Recherche web non disponible (SerpAPI non configurée)"

        try:
            # Add Givaudan context
            enriched_query = f"Givaudan parfums arômes {query}"
            results = self.search.run(enriched_query)
            logger.info(f" Web search results obtained for: {query}")
            return results
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return f"Erreur recherche web: {e}"
