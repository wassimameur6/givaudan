"""RAG answers generation script"""
import sys
from pathlib import Path
import csv
import asyncio
from typing import Dict
from langchain_openai import ChatOpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.react_agent import ReActAgent
from src.config import (
    OPENAI_API_KEY,
    LLM_MODEL,
    SYSTEM_PROMPT,
    OUTPUTS_DIR
)
from src.utils import logger


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
    """Test baseline LLM without RAG"""
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
    logger.info("Starting RAG answers generation...")

    agent = ReActAgent()
    agent.setup_rag()

    results = []

    for i, question in enumerate(QUESTIONS, 1):
        logger.info(f"\nQuestion {i}/{len(QUESTIONS)}: {question}")

        baseline_answer = test_baseline_llm(question)
        rag_result = await test_rag_system(question, agent)
        rag_answer = rag_result['answer']
        cache_hit = rag_result.get('cache_hit', False)
        processing_time = rag_result.get('processing_time', 0)

        logger.info(f"Cache: {'HIT' if cache_hit else 'MISS'}, Time: {processing_time:.2f}s")

        results.append({
            'question': question,
            'llm_answer_baseline': baseline_answer,
            'rag_answer': rag_answer,
            'sources': 'Givaudan corpus (see data/raw/)',
            'cache_hit': cache_hit,
            'processing_time_seconds': round(processing_time, 2)
        })

    csv_path = OUTPUTS_DIR / "rag_answers.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"Saved {len(results)} Q&A pairs to: {csv_path}")


if __name__ == "__main__":
    asyncio.run(generate_answers())
