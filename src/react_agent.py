"""ReAct Agent with Vector DB and Web Search tools"""
from typing import Dict, Any
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from pydantic import Field, ConfigDict
import asyncio
import time

from src.config import *
from src.weaviate_rag_pipeline import WeaviateRAGPipeline
from src.web_agent import WebSearchAgent
from src.semantic_cache import get_cache
from src.utils import logger


class VectorSearchTool(BaseTool):
    name: str = "search_vector_database"
    description: str = "Cherche dans la base Givaudan (parfums, arômes, laboratoires, etc.)"
    rag_pipeline: Any = Field(default=None, exclude=True)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, query: str) -> str:
        try:
            docs = self.rag_pipeline.retrieve_relevant_chunks(query, k=3)
            if not docs:
                return "Aucun document trouvé."

            results = []
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get('filename', 'unknown')
                content = doc.page_content[:300]
                results.append(f"[Doc {i} - {source}]\n{content}...")

            return "\n".join(results)
        except Exception as e:
            return f"Erreur: {e}"


class WebSearchTool(BaseTool):
    name: str = "search_web"
    description: str = "Cherche sur internet (pour info récentes uniquement)"
    web_agent: Any = Field(default=None, exclude=True)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, query: str) -> str:
        try:
            results = self.web_agent.search_web(query)
            return results[:500] if results else "Aucun résultat web."
        except Exception as e:
            return f"Erreur: {e}"


class ReActAgent:
    def __init__(self):
        validate_config()
        logger.info("Init Agent...")

        # LLM - single model (gpt-4o-mini)
        llm_config = {"temperature": 0, "api_key": OPENAI_API_KEY}
        self.llm = ChatOpenAI(model=LLM_MODEL, **llm_config)

        # Components
        self.rag_pipeline = None
        self.web_agent = WebSearchAgent()
        self.cache = get_cache()
        self.tools = []
        self.agent_executor = None

        logger.info("Agent ready")

    def setup_rag(self):
        if not self.rag_pipeline:
            self.rag_pipeline = WeaviateRAGPipeline(
                weaviate_url=WEAVIATE_URL,
                top_k_retrieve=WEAVIATE_TOP_K_RETRIEVE,
                top_k_final=WEAVIATE_TOP_K_FINAL,
                hybrid_alpha=WEAVIATE_HYBRID_ALPHA
            )

            stats = self.rag_pipeline.get_stats()
            if stats['total_chunks'] == 0:
                self.rag_pipeline.index_documents()

            # Create tools
            self.tools = [
                VectorSearchTool(rag_pipeline=self.rag_pipeline),
                WebSearchTool(web_agent=self.web_agent)
            ]

            # Create agent
            template = """Tu es un assistant Givaudan expert en parfumerie et arômes.

Outils: {tools}

Format:
Question: [question]
Thought: [réflexion]
Action: [{tool_names}]
Action Input: [input]
Observation: [résultat]
Thought: Je connais la réponse
Final Answer: [réponse]

RÈGLES:
1. Cherche dans search_vector_database en premier
2. Si documents trouvés → Final Answer
3. Si rien → search_web (seulement pour actualités)
4. MAX 2 actions

{chat_history}

Question: {input}
Thought: {agent_scratchpad}"""

            prompt = PromptTemplate.from_template(template)
            agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)

            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                max_iterations=AGENT_MAX_ITERATIONS,
                max_execution_time=AGENT_MAX_EXECUTION_TIME,
                early_stopping_method="force",
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )

            logger.info("RAG ready")

    def _is_conversational(self, question: str) -> bool:
        q = question.strip().lower()
        greetings = ['bonjour', 'salut', 'hello', 'hi', 'merci', 'thanks', 'ok', 'super', 'hey']

        # Exact match or with punctuation
        return q in greetings or any(q == g + p for g in greetings for p in ['!', '.', '?'])

    async def ask_async(self, question: str, chat_history: list = None) -> Dict:
        start_time = time.time()

        try:
            # Check conversational
            if self._is_conversational(question):
                answer = "Bonjour ! Je suis l'assistant Givaudan. Comment puis-je vous aider ?"
                return {
                    'question': question,
                    'answer': answer,
                    'cache_hit': False,
                    'processing_time': time.time() - start_time
                }

            # Check cache
            cached = await self.cache.get(question, system_type="react_agent")
            if cached:
                return {
                    'question': question,
                    'answer': cached['answer'],
                    'cache_hit': True,
                    'processing_time': time.time() - start_time
                }

            # Format chat history for context (simple & minimal)
            history_text = ""
            if chat_history and len(chat_history) > 0:
                # Only keep last 3 exchanges to avoid token bloat
                recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
                history_parts = []
                for msg in recent_history:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    history_parts.append(f"{role.capitalize()}: {content}")
                history_text = "Conversation précédente:\n" + "\n".join(history_parts) + "\n"

            # Run agent with history
            result = self.agent_executor.invoke({
                "input": question,
                "chat_history": history_text
            })

            answer = result.get('output', '')

            # Cache result
            asyncio.create_task(
                self.cache.set(query=question, answer=answer, system_type="react_agent")
            )

            return {
                'question': question,
                'answer': answer,
                'cache_hit': False,
                'processing_time': time.time() - start_time,
                'model_used': LLM_MODEL
            }

        except Exception as e:
            logger.error(f"Error: {e}")
            return {
                'question': question,
                'answer': f"Erreur: {e}",
                'cache_hit': False,
                'processing_time': time.time() - start_time
            }
