"""Corpus analysis script - generates stats and keywords for documents"""
import sys
from pathlib import Path
import csv
import tiktoken
from collections import Counter
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.document_loader import MultiFormatDocumentLoader
from src.config import RAW_DATA_DIR, OUTPUTS_DIR
from src.utils import logger


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens using tiktoken"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except:
        return len(text.split()) * 1.3


def extract_keywords(text: str, n: int = 3) -> list:
    """Simple keyword extraction - most frequent meaningful words"""
    words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿœæç]+\b', text.lower())

    stop_words = {
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'mais',
        'dans', 'pour', 'par', 'sur', 'avec', 'sans', 'est', 'sont', 'à',
        'au', 'aux', 'ce', 'ces', 'cette', 'cet', 'son', 'sa', 'ses',
        'leur', 'leurs', 'qui', 'que', 'dont', 'où', 'si', 'plus', 'peut',
        'être', 'avoir', 'faire', 'tout', 'tous', 'toute', 'toutes'
    }

    meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
    word_counts = Counter(meaningful_words)
    return [word for word, _ in word_counts.most_common(n)]


def detect_language(text: str) -> str:
    """Simple language detection based on common words"""
    french_indicators = ['le', 'la', 'les', 'un', 'une', 'des', 'et', 'est', 'dans', 'pour']
    english_indicators = ['the', 'a', 'an', 'and', 'is', 'in', 'for', 'of', 'to']

    text_lower = text.lower()
    french_count = sum(1 for word in french_indicators if f' {word} ' in text_lower)
    english_count = sum(1 for word in english_indicators if f' {word} ' in text_lower)

    return "Français" if french_count > english_count else "English"


def analyze_corpus():
    """Main corpus analysis function"""
    logger.info("Starting corpus analysis...")

    loader = MultiFormatDocumentLoader()
    documents = loader.load_directory(RAW_DATA_DIR, recursive=False)
    logger.info(f"Loaded {len(documents)} documents")

    analysis_results = []
    total_tokens = 0

    for i, doc in enumerate(documents, 1):
        filename = doc.metadata.get('filename', f'doc_{i}')
        format_type = doc.metadata.get('format', 'unknown')
        num_pages = doc.metadata.get('num_pages', 1)
        content = doc.page_content

        char_count = len(content)
        token_count = count_tokens(content)
        language = detect_language(content)
        keywords = extract_keywords(content, n=3)

        total_tokens += token_count

        analysis_results.append({
            'document_num': i,
            'filename': filename,
            'format': format_type,
            'num_pages': num_pages,
            'char_count': char_count,
            'token_count': token_count,
            'language': language,
            'keyword_1': keywords[0] if len(keywords) > 0 else '',
            'keyword_2': keywords[1] if len(keywords) > 1 else '',
            'keyword_3': keywords[2] if len(keywords) > 2 else ''
        })

        logger.info(f"{i}. {filename}: {token_count} tokens")

    # Save CSV
    csv_path = OUTPUTS_DIR / "corpus_analysis.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=analysis_results[0].keys())
        writer.writeheader()
        writer.writerows(analysis_results)

    logger.info(f"Saved: {csv_path}")

    # Generate report
    report_path = OUTPUTS_DIR / "corpus_analysis_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("Corpus Analysis Report\n\n")
        f.write(f"Total documents: {len(documents)}\n")
        f.write(f"Total tokens: {total_tokens:,}\n")
        f.write(f"Average tokens per doc: {total_tokens // len(documents):,}\n\n")

        languages = [r['language'] for r in analysis_results]
        lang_counts = Counter(languages)
        f.write(f"Languages: {dict(lang_counts)}\n")

        formats = [r['format'] for r in analysis_results]
        format_counts = Counter(formats)
        f.write(f"Formats: {dict(format_counts)}\n\n")

        for result in analysis_results:
            f.write(f"{result['document_num']}. {result['filename']}\n")
            f.write(f"  {result['token_count']:,} tokens, {result['language']}\n")
            f.write(f"  Keywords: {result['keyword_1']}, {result['keyword_2']}, {result['keyword_3']}\n\n")

    logger.info(f"Saved: {report_path}")
    logger.info(f"Analysis complete: {len(documents)} docs, {total_tokens:,} tokens")


if __name__ == "__main__":
    analyze_corpus()
