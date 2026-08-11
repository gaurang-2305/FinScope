"""
Benchmark extraction accuracy: regex-only vs regex+LLM on real filings.

Usage:
    python -m eval.benchmark
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import run_full_pipeline
from models import FinancialStatement

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finscope.benchmark")

RESULTS_FILE = Path(__file__).parent / "results.md"


def run_benchmark():
    """Run benchmark on all PDFs in test_data/."""
    test_dir = Path(__file__).parent.parent / "test_data"
    
    if not test_dir.exists():
        logger.error("No test_data directory found")
        return
    
    pdfs = list(test_dir.glob("*.pdf"))
    if not pdfs:
        logger.error("No PDFs found in test_data/")
        return
    
    logger.info("Running benchmark on %d PDFs", len(pdfs))
    
    results = []
    for pdf_path in pdfs:
        logger.info("Processing: %s", pdf_path.name)
        
        try:
            extraction = run_full_pipeline(str(pdf_path))
            stmt = extraction.statement.model_dump()
            
            populated = {k: v for k, v in stmt.items() if v is not None}
            total = len(stmt)
            
            # Track extraction methods
            methods = {}
            for field_name, prov in extraction.provenance.items():
                methods[field_name] = prov.extraction_method
            
            results.append({
                "file": pdf_path.name,
                "populated": len(populated),
                "total": total,
                "coverage": len(populated) / total,
                "fields": populated,
                "methods": methods,
                "warnings": extraction.warnings,
            })
            
            logger.info(
                "  %d/%d fields populated (%.0f%% coverage)",
                len(populated), total, len(populated) / total * 100,
            )
            
        except Exception as e:
            logger.error("  Failed: %s", e)
            results.append({
                "file": pdf_path.name,
                "error": str(e),
            })
    
    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    
    for r in results:
        if "error" in r:
            print(f"\n{r['file']}: ERROR - {r['error']}")
        else:
            print(f"\n{r['file']}:")
            print(f"  Coverage: {r['populated']}/{r['total']} ({r['coverage']:.0%})")
            print(f"  Methods: {r['methods']}")
            if r['warnings']:
                print(f"  Warnings: {r['warnings']}")
    
    return results


if __name__ == "__main__":
    run_benchmark()
