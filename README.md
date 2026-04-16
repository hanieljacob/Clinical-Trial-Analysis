# Clinical Trial Analysis – Loblaw Bio

Interactive analysis of immune cell population data from a clinical trial evaluating the drug candidate **miraclib**.

---

## Quick Start (GitHub Codespaces / Local)

```bash
make setup     # Install dependencies
make pipeline  # Run full analysis pipeline
make dashboard # Launch interactive dashboard
```

The dashboard will be available at `http://localhost:8501`.

> **Dashboard link (deployed):** *(see submission form)*

---

## Project Structure

```
.
├── cell-count.csv              # Raw input data
├── load_data.py                # Part 1: DB schema + data loading
├── pipeline.py                 # Orchestrates all analysis steps
├── analysis/
│   ├── part2_frequency.py      # Part 2: Cell frequency table
│   ├── part3_statistics.py     # Part 3: Statistical analysis + boxplot
│   └── part4_subset.py         # Part 4: Subset analysis
├── dashboard/
│   └── app.py                  # Streamlit interactive dashboard
├── outputs/                    # Generated tables and plots (created by pipeline)
├── requirements.txt
├── Makefile
└── README.md
```

---

## Database Schema

### Tables

```
projects  ─┐
           │ (1:N)
subjects  ─┤─┐
             │ (1:N)
samples   ───┤
             │ (1:1)
cell_counts ─┘
```

| Table | Primary Key | Description |
|---|---|---|
| `projects` | `project` | One row per research project |
| `subjects` | `subject` | One row per patient: demographics, condition, treatment, response |
| `samples` | `sample_id` | One row per biological sample (a subject can have multiple) |
| `cell_counts` | `sample_id` | Five cell-population counts per sample (wide format) |

### Design Rationale

**Normalized subject/project split:** `subjects` references `projects` so project-level metadata (or additional columns like site, PI, protocol) can be added without touching sample or count tables. At hundreds of projects, this also makes project-level rollups efficient.

**Samples separate from subjects:** A patient has multiple samples collected at different time points (`time_from_treatment_start`). Keeping samples in their own table avoids repeating demographic data and lets you add new sample types (e.g., tissue biopsies) without schema changes.

**Wide `cell_counts` table:** Five population columns per row (instead of one row per population per sample) enables fast `SUM(b_cell + cd8_t_cell + ...)` aggregations — the most common analytical pattern — without costly pivots. If new populations are added, an `ALTER TABLE ADD COLUMN` is the only change needed.

**Indexes:** Composite analytical filters (condition + treatment + sample_type + time) are supported by individual indexes on each column; SQLite's query planner combines them. At millions of rows, these would be upgraded to composite indexes aligned with the most common query patterns.

**Scaling considerations:**
- *Hundreds of projects / thousands of samples:* The schema handles this well as-is. The `projects` table can hold project-level attributes (start date, PI, indication group) without affecting sample throughput.
- *New analytic types (longitudinal, multi-omics):* Additional `assay_results` tables can join to `samples` on `sample_id`, preserving the shared subject/sample spine.
- *Production workloads:* Migrate from SQLite to PostgreSQL; replace wide `cell_counts` with a normalized `population_counts(sample_id, population, count)` table plus materialized views for the common percentage aggregation, enabling columnar storage and parallelism.

---

## Code Design

Each analysis part lives in its own module (`analysis/part*.py`) so it can be run standalone or imported by the dashboard without side effects. `pipeline.py` imports and calls each module in sequence — no shell subprocesses — so failures surface with full Python tracebacks.

The Streamlit dashboard (`dashboard/app.py`) uses `@st.cache_data` on all DB queries so repeated navigation between pages does not re-run SQL. All plots are Plotly (interactive) rather than static images to give Bob and his colleagues hover tooltips and zoom.

---

## Results Summary

### Part 4 Answer

**Average B cells for melanoma male responders at baseline (time=0):** `10401.28`

(n = 184 samples across prj1 and prj3)

### Part 3 Findings

Using a Mann-Whitney U test (two-sided, α = 0.05) on melanoma/miraclib/PBMC samples:

| Population | Responder Median % | Non-Responder Median % | p-value | Significant |
|---|---|---|---|---|
| B Cell | 9.43 | 9.79 | 0.0557 | No |
| CD8 T Cell | 24.73 | 24.60 | 0.6391 | No |
| **CD4 T Cell** | **30.22** | **29.66** | **0.0133** | **Yes** |
| NK Cell | 14.51 | 14.80 | 0.1211 | No |
| Monocyte | 19.61 | 19.94 | 0.1632 | No |

**Conclusion:** CD4 T cell relative frequency is the only population with a statistically significant difference between responders and non-responders (p = 0.013). Responders have a modestly higher CD4 T cell frequency, suggesting this population may contribute to treatment response.
