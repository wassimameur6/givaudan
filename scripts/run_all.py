"""
MASTER SCRIPT: Run All Output Generation Scripts
=================================================
Executes all scripts in sequence to generate all required outputs:
1. Corpus analysis (corpus_analysis.csv + report)
2. RAG answers (rag_answers.csv)
3. Baseline vs RAG comparison (baseline_vs_rag_comparison.txt)

Usage:
    poetry run python scripts/run_all.py
    # or
    python scripts/run_all.py
"""
import sys
from pathlib import Path
import subprocess
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import logger


def run_script(script_path: Path, description: str):
    """Run a Python script and handle errors"""
    logger.info("\n" + "="*80)
    logger.info(f" RUNNING: {description}")
    logger.info("="*80)

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=True
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        elapsed = time.time() - start_time
        logger.info(f"{description} completed in {elapsed:.2f}s")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"{description} failed!")
        logger.error(f"Error: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    """Run all generation scripts"""
    logger.info("\n" + "="*80)
    logger.info(" RUNNING ALL OUTPUT GENERATION SCRIPTS")
    logger.info("="*80)

    scripts_dir = Path(__file__).parent
    scripts = [
        (scripts_dir / "01_analyze_corpus.py", "Corpus Analysis"),
        (scripts_dir / "02_generate_rag_answers.py", "RAG Answers Generation"),
        (scripts_dir / "03_compare_baseline_vs_rag.py", "Baseline vs RAG Comparison"),
    ]

    results = []
    total_start = time.time()

    for script_path, description in scripts:
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            results.append((description, False))
            continue

        success = run_script(script_path, description)
        results.append((description, success))

        # Small delay between scripts
        time.sleep(1)

    total_elapsed = time.time() - total_start

    # Summary
    logger.info("\n" + "="*80)
    logger.info(" EXECUTION SUMMARY")
    logger.info("="*80)

    for description, success in results:
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"   {status}: {description}")

    logger.info(f"\nTotal execution time: {total_elapsed:.2f}s")

    successful = sum(1 for _, success in results if success)
    logger.info(f"\n{successful}/{len(results)} scripts completed successfully")

    if successful == len(results):
        logger.info("\nALL OUTPUTS GENERATED SUCCESSFULLY!")
        logger.info(f"   Check outputs/ directory for results")
    else:
        logger.warning("\nSome scripts failed - check errors above")

    logger.info("="*80)


if __name__ == "__main__":
    main()
