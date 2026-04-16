"""
Part 2: Data Overview - relative frequency of each cell population per sample.

Outputs:
  outputs/part2_frequency_table.csv
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "clinical_trial.db"
OUTPUT_DIR = "outputs"
POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def compute_frequency_table(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT
            s.sample_id AS sample,
            cc.b_cell,
            cc.cd8_t_cell,
            cc.cd4_t_cell,
            cc.nk_cell,
            cc.monocyte
        FROM samples s
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
    """
    df = pd.read_sql_query(query, conn)

    df["total_count"] = df[POPULATIONS].sum(axis=1)

    records = []
    for pop in POPULATIONS:
        pop_df = df[["sample", "total_count", pop]].copy()
        pop_df = pop_df.rename(columns={pop: "count"})
        pop_df["population"] = pop
        pop_df["percentage"] = (pop_df["count"] / pop_df["total_count"] * 100).round(4)
        records.append(pop_df)

    result = pd.concat(records, ignore_index=True)
    result = result[["sample", "total_count", "population", "count", "percentage"]]
    result = result.sort_values(["sample", "population"]).reset_index(drop=True)
    return result


def main() -> pd.DataFrame:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        df = compute_frequency_table(conn)
    finally:
        conn.close()

    out_path = os.path.join(OUTPUT_DIR, "part2_frequency_table.csv")
    df.to_csv(out_path, index=False)
    print(f"Part 2: frequency table saved to {out_path} ({len(df)} rows)")
    return df


if __name__ == "__main__":
    main()
