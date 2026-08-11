"""
Benchmark extraction accuracy: regex-only vs regex+LLM on real filings.

Usage:
    python -m eval.benchmark
"""
from eval import run_benchmark

if __name__ == "__main__":
    run_benchmark()
