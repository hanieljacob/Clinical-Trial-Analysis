"""
load_data.py - Initialize SQLite database and load cell-count.csv

Schema design rationale:
- projects: normalized project metadata (scales to hundreds of projects)
- subjects: one row per subject with demographic + treatment info
- samples: one row per biological sample (a subject can have multiple)
- cell_counts: cell population counts per sample (wide format for fast aggregation)

Run: python load_data.py
"""

import sqlite3
import csv
import os

DB_PATH = "clinical_trial.db"
CSV_PATH = "cell-count.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS subjects (
    subject     TEXT PRIMARY KEY,
    project     TEXT NOT NULL REFERENCES projects(project),
    condition   TEXT NOT NULL,
    age         INTEGER,
    sex         TEXT,
    treatment   TEXT,
    response    TEXT
);

CREATE TABLE IF NOT EXISTS samples (
    sample_id                   TEXT PRIMARY KEY,
    subject                     TEXT NOT NULL REFERENCES subjects(subject),
    sample_type                 TEXT NOT NULL,
    time_from_treatment_start   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cell_counts (
    sample_id   TEXT PRIMARY KEY REFERENCES samples(sample_id),
    b_cell      INTEGER NOT NULL,
    cd8_t_cell  INTEGER NOT NULL,
    cd4_t_cell  INTEGER NOT NULL,
    nk_cell     INTEGER NOT NULL,
    monocyte    INTEGER NOT NULL
);

-- Indexes for common analytical filters
CREATE INDEX IF NOT EXISTS idx_subjects_project   ON subjects(project);
CREATE INDEX IF NOT EXISTS idx_subjects_condition ON subjects(condition);
CREATE INDEX IF NOT EXISTS idx_subjects_treatment ON subjects(treatment);
CREATE INDEX IF NOT EXISTS idx_subjects_response  ON subjects(response);
CREATE INDEX IF NOT EXISTS idx_subjects_sex       ON subjects(sex);
CREATE INDEX IF NOT EXISTS idx_samples_subject    ON samples(subject);
CREATE INDEX IF NOT EXISTS idx_samples_type       ON samples(sample_type);
CREATE INDEX IF NOT EXISTS idx_samples_time       ON samples(time_from_treatment_start);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def load_csv(conn: sqlite3.Connection, csv_path: str) -> None:
    projects_seen: set = set()
    subjects_seen: set = set()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    project_rows = []
    subject_rows = []
    sample_rows = []
    cell_rows = []

    for row in rows:
        project = row["project"]
        subject = row["subject"]
        sample_id = row["sample"]

        if project not in projects_seen:
            projects_seen.add(project)
            project_rows.append((project,))

        if subject not in subjects_seen:
            subjects_seen.add(subject)
            age = int(row["age"]) if row["age"] else None
            response = row["response"] if row["response"] else None
            subject_rows.append((
                subject, project, row["condition"],
                age, row["sex"], row["treatment"], response,
            ))

        sample_rows.append((
            sample_id, subject,
            row["sample_type"],
            int(row["time_from_treatment_start"]),
        ))

        cell_rows.append((
            sample_id,
            int(row["b_cell"]),
            int(row["cd8_t_cell"]),
            int(row["cd4_t_cell"]),
            int(row["nk_cell"]),
            int(row["monocyte"]),
        ))

    conn.executemany("INSERT OR IGNORE INTO projects VALUES (?)", project_rows)
    conn.executemany(
        "INSERT OR IGNORE INTO subjects VALUES (?,?,?,?,?,?,?)", subject_rows
    )
    conn.executemany(
        "INSERT OR IGNORE INTO samples VALUES (?,?,?,?)", sample_rows
    )
    conn.executemany(
        "INSERT OR IGNORE INTO cell_counts VALUES (?,?,?,?,?,?)", cell_rows
    )
    conn.commit()

    print(f"Loaded {len(project_rows)} projects, {len(subject_rows)} subjects, "
          f"{len(sample_rows)} samples.")


def main() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        load_csv(conn, CSV_PATH)
        print(f"Database ready: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
