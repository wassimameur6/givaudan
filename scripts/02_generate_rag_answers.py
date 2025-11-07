"""
SCRIPT 2: RAG Answers Generation
=================================
Generates rag_answers.csv with:
- Baseline LLM answers (no document access)
- RAG answers (with document retrieval)
- Sources
- Performance metrics

Requirements from PDF:
- Answer 5-10 test questions
- Compare baseline vs RAG
- Save to rag_answers.csv with columns: question, rag_answer, sources
"""
import sys
from pathlib import Path
import csv
import asyncio
from typing import List, Dict
from langchain_openai import ChatOpenAI

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.react_agent import ReActAgent
from src.config import (
 OPENAI_API_KEY,
 LLM_MODEL,
 SYSTEM_PROMPT,
 TEST_QUESTIONS,
 OUTPUTS_DIR,
 WEAVIATE_URL,
 WEAVIATE_TOP_K_RETRIEVE,
 WEAVIATE_TOP_K_FINAL,
 WEAVIATE_HYBRID_ALPHA
)
from src.utils import logger


# Test questions (you can modify these)
QUESTIONS = [
 "Où sont les laboratoires Givaudan ?",
 "En quelle année Givaudan a été fondée ?",
 "Qu'est-ce que la pyramide olfactive ?",
 "Combien Givaudan investit-elle en recherche et développement ?",
 "Quelles sont les différences entre les ingrédients naturels et synthétiques ?",
 "Quels sont les principaux métiers chez Givaudan ?",
 "Comment Givaudan assure-t-elle la durabilité de ses ingrédients ?",
]


def test_baseline_llm(question: str) -> str:
 """
 Test baseline LLM (no RAG, no documents)
 Uses only system prompt
 """
 llm = ChatOpenAI(
 model=LLM_MODEL,
 temperature=0,
 api_key=OPENAI_API_KEY
 )

 messages = [
 {"role": "system", "content": SYSTEM_PROMPT},
 {"role": "user", "content": question}
 ]

 response = llm.invoke(messages)
 return response.content


async def test_rag_system(question: str, agent: ReActAgent) -> Dict:
 """Test RAG system with full pipeline"""
 result = await agent.ask_async(question=question, chat_history=[])
 return result


async def generate_answers():
 """Main function to generate all answers"""
 logger.info("\n" + "="*80)
 logger.info(" RAG ANSWERS GENERATION - Task 2")
 logger.info("="*80)

 # Initialize RAG system
 logger.info(" Initializing RAG system...")
 agent = ReActAgent()
 agent.setup_rag()
 logger.info(" RAG system ready!")

 # Results storage
 results = []

 logger.info(f"\n Testing {len(QUESTIONS)} questions...\n")

 for i, question in enumerate(QUESTIONS, 1):
 logger.info(f"\n{'='*80}")
 logger.info(f"Question {i}/{len(QUESTIONS)}: {question}")
 logger.info('='*80)

 # Test baseline LLM (no RAG)
 logger.info(" [1/2] Testing baseline LLM (no documents)...")
 baseline_answer = test_baseline_llm(question)
 logger.info(f" Baseline: {baseline_answer[:100]}...")

 # Test RAG system
 logger.info(" [2/2] Testing RAG system (with documents)...")
 rag_result = await test_rag_system(question, agent)
 rag_answer = rag_result['answer']
 cache_hit = rag_result.get('cache_hit', False)
 processing_time = rag_result.get('processing_time', 0)

 logger.info(f" RAG: {rag_answer[:100]}...")
 logger.info(f" Cache: {'HIT' if cache_hit else 'MISS'}, Time: {processing_time:.2f}s")

 # Store results
 results.append({
 'question': question,
 'llm_answer_baseline': baseline_answer,
 'rag_answer': rag_answer,
 'sources': 'Givaudan corpus (see data/raw/)',
 'cache_hit': cache_hit,
 'processing_time_seconds': round(processing_time, 2)
 })

 # Save to CSV
 csv_path = OUTPUTS_DIR / "rag_answers.csv"
 with open(csv_path, 'w', newline='', encoding='utf-8') as f:
 writer = csv.DictWriter(f, fieldnames=results[0].keys())
 writer.writeheader()
 writer.writerows(results)

 logger.info(f"\n Saved {len(results)} Q&A pairs to: {csv_path}")
 logger.info("\n" + "="*80)
 logger.info(" ANSWERS GENERATION COMPLETE")
 logger.info("="*80)


if __name__ == "__main__":
 asyncio.run(generate_answers())
