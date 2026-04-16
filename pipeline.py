"""
pipeline.py - Run the complete analysis pipeline end-to-end.

Steps:
  1. Initialize database and load data (load_data.py)
  2. Part 2: Compute cell frequency table
  3. Part 3: Statistical analysis + boxplot
  4. Part 4: Data subset analysis
"""

import subprocess
import sys
import os


def run_step(description: str, func) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print("=" * 60)
    func()


def main() -> None:
    os.makedirs("outputs", exist_ok=True)

    # Step 1: load data
    run_step("Step 1: Initialize database and load data", lambda: __import__("load_data").main())

    # Step 2: frequency table
    run_step("Step 2: Cell population frequency table", lambda: __import__("analysis.part2_frequency", fromlist=["main"]).main())

    # Step 3: statistical analysis
    run_step("Step 3: Statistical analysis (responders vs non-responders)", lambda: __import__("analysis.part3_statistics", fromlist=["main"]).main())

    # Step 4: subset analysis
    run_step("Step 4: Data subset analysis (melanoma PBMC baseline)", lambda: __import__("analysis.part4_subset", fromlist=["main"]).main())

    print("\n" + "=" * 60)
    print("  Pipeline complete. Outputs in ./outputs/")
    print("=" * 60)


if __name__ == "__main__":
    main()
