"""Baseline vs RAG comparison report generator"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import OUTPUTS_DIR
from src.utils import logger


def generate_comparison():
    """Generate baseline vs RAG comparison report"""
    logger.info("Generating comparison report...")

    comparison_text = """Baseline LLM vs RAG System Comparison

Methodology:
- Baseline: GPT-4o-mini with system prompt only
- RAG: Hybrid search (Weaviate) + ReAct Agent

Key Differences:

1. Accuracy
   Baseline: Generic answers based on training data
   RAG: Specific answers from Givaudan documents

2. Sources
   Baseline: No source attribution
   RAG: Cites specific documents (PDF, TXT, MD)

3. Hallucinations
   Baseline: Can invent facts not in training data
   RAG: Grounded in actual documents from corpus
"""

    report_path = OUTPUTS_DIR / "baseline_vs_rag_comparison.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(comparison_text)

    logger.info(f"Saved: {report_path}")
    print(comparison_text)


if __name__ == "__main__":
    generate_comparison()
