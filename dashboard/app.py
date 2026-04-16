"""
Streamlit dashboard for the Clinical Trial Analysis.

Run from repo root:  streamlit run dashboard/app.py
"""

import sys
import os

# Allow imports from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import streamlit as st

# ── Config ──────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clinical_trial.db")
POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
POP_LABELS = {
    "b_cell": "B Cell",
    "cd8_t_cell": "CD8 T Cell",
    "cd4_t_cell": "CD4 T Cell",
    "nk_cell": "NK Cell",
    "monocyte": "Monocyte",
}
ALPHA = 0.05

st.set_page_config(
    page_title="Clinical Trial Analysis – Loblaw Bio",
    page_icon="🔬",
    layout="wide",
)


# ── DB helpers ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}. Run `python load_data.py` first.")
        st.stop()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


@st.cache_data
def load_frequency_table() -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT s.sample_id AS sample,
               cc.b_cell, cc.cd8_t_cell, cc.cd4_t_cell, cc.nk_cell, cc.monocyte
        FROM samples s
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
    """
    df = pd.read_sql_query(query, conn)
    df["total_count"] = df[POPULATIONS].sum(axis=1)
    records = []
    for pop in POPULATIONS:
        tmp = df[["sample", "total_count", pop]].copy()
        tmp = tmp.rename(columns={pop: "count"})
        tmp["population"] = pop
        tmp["percentage"] = (tmp["count"] / tmp["total_count"] * 100).round(4)
        records.append(tmp)
    result = pd.concat(records, ignore_index=True)
    return result[["sample", "total_count", "population", "count", "percentage"]]


@st.cache_data
def load_melanoma_miraclib_pbmc() -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT s.sample_id, subj.response,
               cc.b_cell, cc.cd8_t_cell, cc.cd4_t_cell, cc.nk_cell, cc.monocyte
        FROM samples s
        JOIN subjects subj ON subj.subject = s.subject
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
        WHERE subj.condition = 'melanoma'
          AND subj.treatment = 'miraclib'
          AND s.sample_type  = 'PBMC'
          AND subj.response  IN ('yes', 'no')
    """
    df = pd.read_sql_query(query, conn)
    df["total_count"] = df[POPULATIONS].sum(axis=1)
    for pop in POPULATIONS:
        df[f"{pop}_pct"] = (df[pop] / df["total_count"] * 100).round(4)
    return df


@st.cache_data
def load_subset_data() -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT s.sample_id, subj.subject, subj.project,
               subj.sex, subj.response, cc.b_cell
        FROM samples s
        JOIN subjects subj ON subj.subject = s.subject
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
        WHERE subj.condition              = 'melanoma'
          AND s.sample_type               = 'PBMC'
          AND s.time_from_treatment_start = 0
          AND subj.treatment              = 'miraclib'
    """
    return pd.read_sql_query(query, conn)


# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("🔬 Clinical Trial Analysis")
st.sidebar.markdown("**Loblaw Bio – Miraclib Study**")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Part 2: Cell Frequencies", "Part 3: Statistical Analysis", "Part 4: Subset Analysis"],
)
st.sidebar.markdown("---")
st.sidebar.caption("Database: clinical_trial.db")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ══════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("Clinical Trial Analysis Dashboard")
    st.markdown(
        """
        This dashboard presents the results of the Loblaw Bio miraclib clinical trial analysis.
        Use the sidebar to navigate between analysis parts.

        | Part | Description |
        |------|-------------|
        | **Part 2** | Cell population relative frequencies per sample |
        | **Part 3** | Statistical comparison: responders vs non-responders (melanoma, miraclib, PBMC) |
        | **Part 4** | Subset analysis: melanoma PBMC baseline samples |
        """
    )

    conn = get_connection()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_projects = pd.read_sql_query("SELECT COUNT(*) as n FROM projects", conn).iloc[0, 0]
        st.metric("Projects", n_projects)
    with col2:
        n_subjects = pd.read_sql_query("SELECT COUNT(*) as n FROM subjects", conn).iloc[0, 0]
        st.metric("Subjects", n_subjects)
    with col3:
        n_samples = pd.read_sql_query("SELECT COUNT(*) as n FROM samples", conn).iloc[0, 0]
        st.metric("Samples", n_samples)
    with col4:
        n_cells = pd.read_sql_query(
            "SELECT SUM(b_cell+cd8_t_cell+cd4_t_cell+nk_cell+monocyte) as n FROM cell_counts", conn
        ).iloc[0, 0]
        st.metric("Total Cells Counted", f"{n_cells:,.0f}")

    st.markdown("---")
    st.subheader("Dataset Distribution")
    col_a, col_b = st.columns(2)

    with col_a:
        cond_df = pd.read_sql_query(
            "SELECT condition, COUNT(*) as count FROM subjects GROUP BY condition", conn
        )
        fig = px.pie(cond_df, names="condition", values="count", title="Subjects by Condition")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        trt_df = pd.read_sql_query(
            "SELECT treatment, COUNT(*) as count FROM subjects GROUP BY treatment", conn
        )
        fig = px.pie(trt_df, names="treatment", values="count", title="Subjects by Treatment")
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Part 2
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Part 2: Cell Frequencies":
    st.title("Part 2: Cell Population Relative Frequencies")
    st.markdown(
        "For each sample, the relative frequency of each immune cell population "
        "is expressed as a percentage of the total cell count."
    )

    with st.spinner("Loading frequency table…"):
        freq_df = load_frequency_table()

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        selected_pops = st.multiselect(
            "Filter by population",
            options=POPULATIONS,
            default=POPULATIONS,
            format_func=lambda x: POP_LABELS[x],
        )
    with col2:
        sample_search = st.text_input("Search sample ID (optional)", "")

    filtered = freq_df[freq_df["population"].isin(selected_pops)]
    if sample_search:
        filtered = filtered[filtered["sample"].str.contains(sample_search, case=False)]

    st.dataframe(
        filtered.style.format({"percentage": "{:.2f}%", "total_count": "{:,.0f}", "count": "{:,.0f}"}),
        use_container_width=True,
        height=400,
    )
    st.caption(f"Showing {len(filtered):,} rows (of {len(freq_df):,} total)")

    st.markdown("---")
    st.subheader("Average Relative Frequency by Population")
    avg_df = (
        freq_df.groupby("population")["percentage"]
        .agg(["mean", "std", "median"])
        .reset_index()
        .rename(columns={"mean": "Mean %", "std": "Std Dev", "median": "Median %"})
    )
    avg_df["population"] = avg_df["population"].map(POP_LABELS)

    fig = px.bar(
        avg_df, x="population", y="Mean %",
        error_y="Std Dev",
        color="population",
        title="Mean Relative Frequency per Cell Population (all samples)",
        labels={"population": "Population", "Mean %": "Mean Frequency (%)"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Part 3
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Part 3: Statistical Analysis":
    st.title("Part 3: Responders vs Non-Responders")
    st.markdown(
        """
        **Cohort:** Melanoma patients treated with **miraclib**, PBMC samples only.

        **Method:** Mann-Whitney U test (two-sided, non-parametric — no normality assumption required).
        Significance threshold: α = 0.05.
        """
    )

    with st.spinner("Loading data…"):
        df = load_melanoma_miraclib_pbmc()

    n_resp = (df["response"] == "yes").sum()
    n_nonr = (df["response"] == "no").sum()
    col1, col2 = st.columns(2)
    col1.metric("Responder samples", n_resp)
    col2.metric("Non-Responder samples", n_nonr)

    st.markdown("---")
    st.subheader("Boxplots: Relative Frequency by Response")

    # Build interactive plotly boxplot
    fig = make_subplots(
        rows=1, cols=len(POPULATIONS),
        subplot_titles=[POP_LABELS[p] for p in POPULATIONS],
        shared_yaxes=False,
    )
    colors_map = {"yes": "#4C9BE8", "no": "#E8734C"}
    resp_labels = {"yes": "Responder", "no": "Non-Responder"}

    for i, pop in enumerate(POPULATIONS, start=1):
        col = f"{pop}_pct"
        for resp_val in ["yes", "no"]:
            subset = df[df["response"] == resp_val][col]
            fig.add_trace(
                go.Box(
                    y=subset,
                    name=resp_labels[resp_val],
                    marker_color=colors_map[resp_val],
                    showlegend=(i == 1),
                    legendgroup=resp_val,
                    boxmean=True,
                ),
                row=1, col=i,
            )

    fig.update_layout(
        height=500,
        title_text="Cell Population Frequencies – Responders vs Non-Responders",
        boxmode="group",
    )
    for i in range(1, len(POPULATIONS) + 1):
        fig.update_yaxes(title_text="Frequency (%)", row=1, col=i)

    st.plotly_chart(fig, use_container_width=True)

    # Statistics table
    st.markdown("---")
    st.subheader("Statistical Test Results")

    stat_rows = []
    for pop in POPULATIONS:
        col = f"{pop}_pct"
        resp = df.loc[df["response"] == "yes", col]
        nonr = df.loc[df["response"] == "no", col]
        u_stat, p_val = stats.mannwhitneyu(resp, nonr, alternative="two-sided")

        sig = "✅ Yes" if p_val < ALPHA else "❌ No"
        if p_val < 0.001:
            stars = "***"
        elif p_val < 0.01:
            stars = "**"
        elif p_val < 0.05:
            stars = "*"
        else:
            stars = "ns"

        stat_rows.append({
            "Population": POP_LABELS[pop],
            "Responder Median (%)": round(resp.median(), 2),
            "Non-Responder Median (%)": round(nonr.median(), 2),
            "Mann-Whitney U": round(u_stat, 1),
            "p-value": round(p_val, 6),
            "Significance": stars,
            "Significant (α=0.05)": sig,
        })

    stat_df = pd.DataFrame(stat_rows)
    st.dataframe(stat_df, use_container_width=True, hide_index=True)

    sig_pops = [r["Population"] for r in stat_rows if "✅" in r["Significant (α=0.05)"]]
    if sig_pops:
        st.success(
            f"**Conclusion:** The following populations show a statistically significant difference "
            f"in relative frequency between responders and non-responders: **{', '.join(sig_pops)}**."
        )
    else:
        st.info("No cell populations showed a statistically significant difference at α=0.05.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Part 4
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Part 4: Subset Analysis":
    st.title("Part 4: Melanoma PBMC Baseline Subset")
    st.markdown(
        """
        **Filter:** Melanoma patients | Miraclib treatment | PBMC samples | **Baseline (time = 0)**
        """
    )

    with st.spinner("Loading subset…"):
        df = load_subset_data()

    total_samples = len(df)
    total_subjects = df["subject"].nunique()
    col1, col2 = st.columns(2)
    col1.metric("Total Samples (baseline)", total_samples)
    col2.metric("Unique Subjects", total_subjects)

    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.subheader("Samples per Project")
        by_proj = df.groupby("project")["sample_id"].count().reset_index()
        by_proj.columns = ["Project", "Sample Count"]
        st.dataframe(by_proj, hide_index=True, use_container_width=True)
        fig = px.bar(by_proj, x="Project", y="Sample Count", color="Project",
                     title="Samples per Project",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Subjects: Responders / Non-Responders")
        subj_resp = df.drop_duplicates("subject")["response"].value_counts().reset_index()
        subj_resp.columns = ["Response", "Subject Count"]
        subj_resp["Response"] = subj_resp["Response"].map(
            {"yes": "Responder", "no": "Non-Responder"}
        ).fillna(subj_resp["Response"])
        st.dataframe(subj_resp, hide_index=True, use_container_width=True)
        fig = px.pie(subj_resp, names="Response", values="Subject Count",
                     title="Response Distribution",
                     color_discrete_sequence=["#4C9BE8", "#E8734C"])
        st.plotly_chart(fig, use_container_width=True)

    with col_c:
        st.subheader("Subjects: Males / Females")
        subj_sex = df.drop_duplicates("subject")["sex"].value_counts().reset_index()
        subj_sex.columns = ["Sex", "Subject Count"]
        subj_sex["Sex"] = subj_sex["Sex"].map({"M": "Male", "F": "Female"}).fillna(subj_sex["Sex"])
        st.dataframe(subj_sex, hide_index=True, use_container_width=True)
        fig = px.pie(subj_sex, names="Sex", values="Subject Count",
                     title="Sex Distribution",
                     color_discrete_sequence=["#6BAED6", "#FD8D3C"])
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Average B Cells – Melanoma Males, Responders, Baseline")

    male_resp = df[(df["sex"] == "M") & (df["response"] == "yes")]
    avg_b = male_resp["b_cell"].mean()

    st.metric(
        label="Average B Cell Count",
        value=f"{avg_b:.2f}",
        help=f"Based on {len(male_resp)} samples from melanoma male responders at time=0",
    )
    st.caption(f"n = {len(male_resp)} samples")
