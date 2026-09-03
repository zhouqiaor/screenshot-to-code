#!/usr/bin/env python3
"""Resume kotlin_pipeline from stage 3 (skip stage 1-2, reuse existing outputs)."""
import json
import os
import sys
from pathlib import Path

# Reuse functions from kotlin_pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kotlin_pipeline import (
    ANALYSIS_JSON, HTML_PREVIEW, KOTLIN_FILE, REPORT_HTML, RUN_DIR,
    stage3_kotlin_generate, stage4_compile, stage5_report,
)

def main():
    print("=" * 60)
    print("Resume: Stage 3-5 (skip analysis + HTML preview)")
    print("=" * 60)

    # Load existing analysis
    analysis = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
    print(f"Loaded analysis: {ANALYSIS_JSON}")

    # Load existing HTML preview
    html_code = HTML_PREVIEW.read_text(encoding="utf-8")
    print(f"Loaded HTML preview: {HTML_PREVIEW} ({len(html_code)} chars)")

    # Stage 3: Kotlin generation
    kotlin_code = stage3_kotlin_generate(analysis)

    # Stage 4: Compile
    compile_result = stage4_compile(kotlin_code)

    # Stage 5: Report
    stage5_report(analysis, html_code, kotlin_code, compile_result)

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"Report: {REPORT_HTML}")
    print("=" * 60)

if __name__ == "__main__":
    main()
