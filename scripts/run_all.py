"""Run all output generation scripts in sequence"""
import sys
from pathlib import Path
import subprocess
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import logger


def run_script(script_path: Path, description: str):
    """Run a Python script and handle errors"""
    logger.info(f"\nRunning: {description}")
    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        elapsed = time.time() - start_time
        logger.info(f"Completed in {elapsed:.2f}s")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed: {description}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    """Run all generation scripts"""
    logger.info("Running all scripts...")

    scripts_dir = Path(__file__).parent
    scripts = [
        (scripts_dir / "01_analyze_corpus.py", "Corpus Analysis"),
        (scripts_dir / "02_generate_rag_answers.py", "RAG Answers"),
        (scripts_dir / "03_compare_baseline_vs_rag.py", "Comparison Report"),
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
        time.sleep(1)

    total_elapsed = time.time() - total_start

    logger.info("\nExecution Summary:")
    for description, success in results:
        status = "OK" if success else "FAILED"
        logger.info(f"  [{status}] {description}")

    successful = sum(1 for _, success in results if success)
    logger.info(f"\nCompleted {successful}/{len(results)} scripts in {total_elapsed:.2f}s")

    if successful == len(results):
        logger.info("Check outputs/ directory for results")


if __name__ == "__main__":
    main()
