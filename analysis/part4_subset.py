"""
Part 4: Data Subset Analysis

Filters to melanoma PBMC baseline (time=0) samples from miraclib-treated patients.
Reports:
  - Samples per project
  - Responder/non-responder subject counts
  - Male/female subject counts
  - Average B cells for melanoma male responders at time=0

Outputs:
  outputs/part4_samples_per_project.csv
  outputs/part4_response_counts.csv
  outputs/part4_sex_counts.csv
  outputs/part4_summary.txt
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "clinical_trial.db"
OUTPUT_DIR = "outputs"


def run_subset_analysis(conn: sqlite3.Connection) -> dict:
    # Base query: melanoma, PBMC, time=0, miraclib
    base_query = """
        SELECT
            s.sample_id,
            subj.subject,
            subj.project,
            subj.condition,
            subj.sex,
            subj.response,
            s.sample_type,
            s.time_from_treatment_start,
            cc.b_cell
        FROM samples s
        JOIN subjects subj ON subj.subject = s.subject
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
        WHERE subj.condition              = 'melanoma'
          AND s.sample_type               = 'PBMC'
          AND s.time_from_treatment_start = 0
          AND subj.treatment              = 'miraclib'
    """
    df = pd.read_sql_query(base_query, conn)

    # --- Samples per project ---
    samples_per_project = (
        df.groupby("project")["sample_id"]
        .count()
        .reset_index()
        .rename(columns={"sample_id": "sample_count"})
        .sort_values("project")
    )

    # For subject-level counts, deduplicate on subject
    subjects_df = df.drop_duplicates(subset="subject")

    # --- Responders / non-responders ---
    response_counts = (
        subjects_df["response"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "response", "count": "subject_count"})
    )

    # --- Males / females ---
    sex_counts = (
        subjects_df["sex"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "sex", "count": "subject_count"})
    )

    # --- Average B cells: melanoma males, responders, time=0 ---
    male_resp = df[(df["sex"] == "M") & (df["response"] == "yes")]
    avg_b_cell = male_resp["b_cell"].mean()

    return {
        "df": df,
        "samples_per_project": samples_per_project,
        "response_counts": response_counts,
        "sex_counts": sex_counts,
        "avg_b_cell_male_responders": avg_b_cell,
        "n_male_responders": len(male_resp),
    }


def main() -> dict:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        results = run_subset_analysis(conn)
    finally:
        conn.close()

    # Save tables
    results["samples_per_project"].to_csv(
        os.path.join(OUTPUT_DIR, "part4_samples_per_project.csv"), index=False
    )
    results["response_counts"].to_csv(
        os.path.join(OUTPUT_DIR, "part4_response_counts.csv"), index=False
    )
    results["sex_counts"].to_csv(
        os.path.join(OUTPUT_DIR, "part4_sex_counts.csv"), index=False
    )

    avg = results["avg_b_cell_male_responders"]
    summary_lines = [
        "Part 4: Data Subset Analysis",
        "=" * 50,
        "Filter: Melanoma | PBMC | time_from_treatment_start=0 | Treatment=miraclib",
        "",
        "Samples per project:",
        results["samples_per_project"].to_string(index=False),
        "",
        "Subjects: Responders vs Non-Responders:",
        results["response_counts"].to_string(index=False),
        "",
        "Subjects: Males vs Females:",
        results["sex_counts"].to_string(index=False),
        "",
        f"Average B cells (melanoma males, responders, time=0): {avg:.2f}",
        f"  (n={results['n_male_responders']} samples)",
    ]
    summary_text = "\n".join(summary_lines)
    print("\n" + summary_text)

    summary_path = os.path.join(OUTPUT_DIR, "part4_summary.txt")
    with open(summary_path, "w") as f:
        f.write(summary_text + "\n")
    print(f"\nPart 4 summary saved to {summary_path}")

    return results


if __name__ == "__main__":
    main()
