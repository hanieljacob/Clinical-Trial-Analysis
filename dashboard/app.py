"""
Streamlit dashboard for the Clinical Trial Analysis.

Run from repo root:  streamlit run dashboard/app.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import streamlit as st

# ── Paths / constants ─────────────────────────────────────────────────────────
ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "clinical_trial.db")

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
POP_LABELS  = {
    "b_cell":     "B Cell",
    "cd8_t_cell": "CD8 T Cell",
    "cd4_t_cell": "CD4 T Cell",
    "nk_cell":    "NK Cell",
    "monocyte":   "Monocyte",
}
ALPHA = 0.05

# chart colours — warm, not the generic teal/blue starter pack
AMBER   = "#C8965A"
SAGE    = "#6FA688"
TERRA   = "#B55C44"
SAND    = "#C4A96A"
SLATE   = "#7A8FA6"
PALETTE = [AMBER, SAGE, TERRA, SAND, SLATE]

RESP_COLOR = {"yes": SAGE, "no": TERRA}
RESP_LABEL = {"yes": "Responder", "no": "Non-Responder"}

# base plotly layout — warm dark background, serif titles
_CHART = dict(
    paper_bgcolor="#1C1A17",
    plot_bgcolor="#121110",
    font=dict(family="JetBrains Mono, monospace", color="#8C8270", size=11),
    title_font=dict(family="'Crimson Pro', Georgia, serif", color="#E8DFC8", size=14),
    xaxis=dict(gridcolor="#2C2A25", linecolor="#3A3830",
               tickfont=dict(color="#8C8270", family="JetBrains Mono, monospace")),
    yaxis=dict(gridcolor="#2C2A25", linecolor="#3A3830",
               tickfont=dict(color="#8C8270", family="JetBrains Mono, monospace")),
    legend=dict(bgcolor="#1C1A17", bordercolor="#2C2A25", borderwidth=1,
                font=dict(color="#8C8270", size=11, family="JetBrains Mono, monospace")),
    margin=dict(t=50, b=40, l=50, r=20),
)

def theme(fig, **kw):
    fig.update_layout(**{**_CHART, **kw})
    return fig


# ── Styling ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Loblaw Bio – Miraclib Trial",
    page_icon="⬡",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300;1,400&family=JetBrains+Mono:wght@300;400;500&display=swap');

.stApp { background: #121110 !important; }
.main .block-container { padding-top: 1.25rem; max-width: 1420px; }

/* sidebar */
[data-testid="stSidebar"] {
    background: #1A1815 !important;
    border-right: 1px solid #2A2824 !important;
}
[data-testid="stSidebar"] h1 {
    font-family: 'Crimson Pro', Georgia, serif !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    color: #C8965A !important;
    letter-spacing: 0.01em !important;
    border-bottom: none !important;
    padding-bottom: 0 !important;
    margin-bottom: 0.1rem !important;
    font-style: italic !important;
}
[data-testid="stSidebar"] p {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.68rem !important;
    color: #5C5448 !important;
    letter-spacing: 0.04em !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] > label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.74rem !important;
    color: #8C8270 !important;
}
[data-testid="stSidebar"] hr   { border-color: #2A2824 !important; margin: 1.2rem 0 !important; }
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    font-size: 0.62rem !important;
    color: #4C4840 !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* headings */
h1 {
    font-family: 'Crimson Pro', Georgia, serif !important;
    color: #E8DFC8 !important;
    font-size: 1.85rem !important;
    font-weight: 400 !important;
    font-style: italic !important;
    letter-spacing: -0.01em !important;
    border-bottom: 1px solid #2C2A25 !important;
    padding-bottom: 0.6rem !important;
    margin-bottom: 1.2rem !important;
}
h2, h3 {
    font-family: 'Crimson Pro', Georgia, serif !important;
    color: #D4C9B0 !important;
    font-weight: 400 !important;
    font-style: italic !important;
}

/* body text */
p, .stMarkdown p {
    color: #8C8270 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
    line-height: 1.8 !important;
}
strong { color: #C8B898 !important; }

/* dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid #2C2A25 !important;
    border-radius: 4px !important;
    background: #1A1815 !important;
}

/* inputs */
[data-testid="stTextInput"] input {
    background: #1C1A17 !important;
    border: 1px solid #3A3830 !important;
    color: #E8DFC8 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
    border-radius: 3px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #C8965A !important;
    outline: none !important;
    box-shadow: none !important;
}

/* alerts */
[data-testid="stAlert"] {
    background: rgba(200,150,90,0.07) !important;
    border: 1px solid rgba(200,150,90,0.18) !important;
    border-radius: 4px !important;
}

/* caption */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #4C4840 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.04em !important;
}

/* divider */
hr { border-color: #2C2A25 !important; margin: 1.5rem 0 !important; }

/* scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #1A1815; }
::-webkit-scrollbar-thumb { background: #3A3830; border-radius: 2px; }

/* stat cards (just big numbers, no box) */
.stat-block { padding: 0.5rem 0 0.25rem; }
.stat-num {
    font-family: 'Crimson Pro', Georgia, serif;
    font-size: 2.4rem;
    font-weight: 300;
    color: #C8965A;
    line-height: 1;
    letter-spacing: -0.02em;
}
.stat-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #5C5448;
    margin-top: 0.3rem;
}

/* section label */
.sec {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #C8965A;
    border-bottom: 1px solid #2C2A25;
    padding-bottom: 0.45rem;
    margin: 1.75rem 0 0.9rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def stat(num, label):
    return f'<div class="stat-block"><div class="stat-num">{num}</div><div class="stat-label">{label}</div></div>'

def sec(title):
    return f'<div class="sec">{title}</div>'


# ── DB helpers ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    if not os.path.exists(DB_PATH):
        import subprocess
        subprocess.run(
            [sys.executable, os.path.join(ROOT, "load_data.py")],
            check=True,
        )
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data
def load_frequency_table() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT s.sample_id AS sample, cc.b_cell, cc.cd8_t_cell, cc.cd4_t_cell, cc.nk_cell, cc.monocyte "
        "FROM samples s JOIN cell_counts cc ON cc.sample_id = s.sample_id",
        conn,
    )
    df["total_count"] = df[POPULATIONS].sum(axis=1)
    parts = []
    for pop in POPULATIONS:
        t = df[["sample", "total_count", pop]].copy().rename(columns={pop: "count"})
        t["population"] = pop
        t["percentage"] = (t["count"] / t["total_count"] * 100).round(4)
        parts.append(t)
    return pd.concat(parts, ignore_index=True)[["sample", "total_count", "population", "count", "percentage"]]


@st.cache_data
def load_melanoma_miraclib_pbmc() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT s.sample_id, subj.response,
               cc.b_cell, cc.cd8_t_cell, cc.cd4_t_cell, cc.nk_cell, cc.monocyte
        FROM samples s
        JOIN subjects subj ON subj.subject = s.subject
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
        WHERE subj.condition = 'melanoma'
          AND subj.treatment = 'miraclib'
          AND s.sample_type  = 'PBMC'
          AND subj.response  IN ('yes','no')
    """, conn)
    df["total_count"] = df[POPULATIONS].sum(axis=1)
    for pop in POPULATIONS:
        df[f"{pop}_pct"] = (df[pop] / df["total_count"] * 100).round(4)
    return df


@st.cache_data
def load_subset_data() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query("""
        SELECT s.sample_id, subj.subject, subj.project,
               subj.sex, subj.response, cc.b_cell
        FROM samples s
        JOIN subjects subj ON subj.subject = s.subject
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
        WHERE subj.condition              = 'melanoma'
          AND s.sample_type               = 'PBMC'
          AND s.time_from_treatment_start = 0
          AND subj.treatment              = 'miraclib'
    """, conn)


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("Loblaw Bio")
st.sidebar.markdown("Miraclib clinical trial")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Part 2: Cell Frequencies", "Part 3: Statistical Analysis", "Part 4: Subset Analysis"],
)
st.sidebar.markdown("---")
st.sidebar.caption("clinical_trial.db")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ══════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("Clinical Trial Analysis")
    st.markdown("Immune cell population analysis for the Loblaw Bio miraclib trial.")

    conn = get_connection()
    n_proj = pd.read_sql_query("SELECT COUNT(*) as n FROM projects", conn).iloc[0, 0]
    n_subj = pd.read_sql_query("SELECT COUNT(*) as n FROM subjects", conn).iloc[0, 0]
    n_samp = pd.read_sql_query("SELECT COUNT(*) as n FROM samples",  conn).iloc[0, 0]
    n_cell = pd.read_sql_query(
        "SELECT SUM(b_cell+cd8_t_cell+cd4_t_cell+nk_cell+monocyte) as n FROM cell_counts", conn
    ).iloc[0, 0]

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(stat(n_proj, "Projects"),          unsafe_allow_html=True)
    with c2: st.markdown(stat(n_subj, "Subjects"),          unsafe_allow_html=True)
    with c3: st.markdown(stat(n_samp, "Samples"),           unsafe_allow_html=True)
    with c4: st.markdown(stat(f"{n_cell:,.0f}", "Cells counted"), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(sec("Dataset overview"), unsafe_allow_html=True)
    ca, cb = st.columns(2)

    with ca:
        cond_df = pd.read_sql_query(
            "SELECT condition, COUNT(*) as count FROM subjects GROUP BY condition", conn
        )
        fig = px.pie(cond_df, names="condition", values="count",
                     title="Subjects by condition", color_discrete_sequence=PALETTE)
        fig.update_traces(textfont=dict(family="JetBrains Mono, monospace", color="#E8DFC8", size=10))
        theme(fig)
        st.plotly_chart(fig, width="stretch")

    with cb:
        trt_df = pd.read_sql_query(
            "SELECT treatment, COUNT(*) as count FROM subjects GROUP BY treatment", conn
        )
        fig = px.pie(trt_df, names="treatment", values="count",
                     title="Subjects by treatment", color_discrete_sequence=PALETTE)
        fig.update_traces(textfont=dict(family="JetBrains Mono, monospace", color="#E8DFC8", size=10))
        theme(fig)
        st.plotly_chart(fig, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Part 2
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Part 2: Cell Frequencies":
    st.title("Cell Population Frequencies")
    st.markdown(
        "Relative frequency of each immune population per sample, "
        "expressed as a percentage of the total cell count."
    )

    with st.spinner("Loading…"):
        freq_df = load_frequency_table()

    c1, c2 = st.columns(2)
    with c1:
        selected = st.multiselect("Population", POPULATIONS, default=POPULATIONS,
                                  format_func=lambda x: POP_LABELS[x])
    with c2:
        search = st.text_input("Search sample ID", "")

    filtered = freq_df[freq_df["population"].isin(selected)]
    if search:
        filtered = filtered[filtered["sample"].str.contains(search, case=False)]

    st.dataframe(
        filtered,
        width="stretch",
        height=400,
        column_config={
            "percentage":  st.column_config.NumberColumn("percentage",  format="%.2f%%"),
            "total_count": st.column_config.NumberColumn("total_count", format="%d"),
            "count":       st.column_config.NumberColumn("count",       format="%d"),
        },
    )
    st.caption(f"{len(filtered):,} rows shown · {len(freq_df):,} total")

    st.markdown("---")
    st.markdown(sec("Mean frequency by population"), unsafe_allow_html=True)

    avg_df = (
        freq_df.groupby("population")["percentage"]
        .agg(["mean", "std"])
        .reset_index()
        .rename(columns={"mean": "Mean %", "std": "Std Dev"})
    )
    avg_df["population"] = avg_df["population"].map(POP_LABELS)

    fig = px.bar(
        avg_df, x="population", y="Mean %", error_y="Std Dev",
        color="population",
        title="Mean relative frequency — all samples",
        labels={"population": "", "Mean %": "Mean frequency (%)"},
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(showlegend=False)
    theme(fig)
    st.plotly_chart(fig, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Part 3
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Part 3: Statistical Analysis":
    st.title("Responders vs Non-Responders")
    st.markdown(
        "Melanoma patients treated with miraclib, PBMC samples only. "
        "Mann-Whitney U test (two-sided, α = 0.05)."
    )

    with st.spinner("Loading…"):
        df = load_melanoma_miraclib_pbmc()

    n_r = (df["response"] == "yes").sum()
    n_n = (df["response"] == "no").sum()
    c1, c2 = st.columns(2)
    with c1: st.markdown(stat(n_r, "Responder samples"),     unsafe_allow_html=True)
    with c2: st.markdown(stat(n_n, "Non-responder samples"), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(sec("Relative frequency distributions"), unsafe_allow_html=True)

    fig = make_subplots(
        rows=1, cols=len(POPULATIONS),
        subplot_titles=[POP_LABELS[p] for p in POPULATIONS],
        shared_yaxes=False,
    )
    for i, pop in enumerate(POPULATIONS, 1):
        col = f"{pop}_pct"
        for rv in ["yes", "no"]:
            subset = df[df["response"] == rv][col]
            fig.add_trace(
                go.Box(
                    y=subset,
                    name=RESP_LABEL[rv],
                    marker_color=RESP_COLOR[rv],
                    showlegend=(i == 1),
                    legendgroup=rv,
                    boxmean=True,
                    line=dict(width=1.5),
                    marker=dict(size=3, opacity=0.55),
                ),
                row=1, col=i,
            )

    theme(fig, height=480,
          title_text="Cell population frequencies — responders vs non-responders",
          boxmode="group")
    for i in range(1, len(POPULATIONS) + 1):
        fig.update_xaxes(gridcolor="#2C2A25", linecolor="#3A3830",
                         tickfont=dict(color="#8C8270", family="JetBrains Mono, monospace"),
                         row=1, col=i)
        fig.update_yaxes(title_text="Frequency (%)" if i == 1 else "",
                         gridcolor="#2C2A25", linecolor="#3A3830",
                         tickfont=dict(color="#8C8270", family="JetBrains Mono, monospace"),
                         row=1, col=i)
    for ann in fig.layout.annotations:
        ann.font.color  = "#8C8270"
        ann.font.family = "JetBrains Mono, monospace"
        ann.font.size   = 10

    st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown(sec("Mann-Whitney U results"), unsafe_allow_html=True)

    rows = []
    for pop in POPULATIONS:
        col  = f"{pop}_pct"
        resp = df.loc[df["response"] == "yes", col]
        nonr = df.loc[df["response"] == "no",  col]
        u, p = stats.mannwhitneyu(resp, nonr, alternative="two-sided")

        if   p < 0.001: stars = "***"
        elif p < 0.01:  stars = "**"
        elif p < 0.05:  stars = "*"
        else:           stars = "ns"

        rows.append({
            "Population":               POP_LABELS[pop],
            "Responder median (%)":     round(resp.median(), 2),
            "Non-responder median (%)": round(nonr.median(), 2),
            "Mann-Whitney U":           round(u, 1),
            "p-value":                  round(p, 6),
            "Sig.":                     stars,
            "Significant (α=0.05)":     "yes" if p < ALPHA else "no",
        })

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    sig = [r["Population"] for r in rows if r["Significant (α=0.05)"] == "yes"]
    if sig:
        st.success(f"Statistically significant difference found in: **{', '.join(sig)}**")
    else:
        st.info("No significant differences at α = 0.05.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Part 4
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Part 4: Subset Analysis":
    st.title("Melanoma PBMC Baseline")
    st.markdown(
        "Melanoma patients · miraclib treatment · PBMC samples · time from treatment start = 0"
    )

    with st.spinner("Loading…"):
        df = load_subset_data()

    c1, c2 = st.columns(2)
    with c1: st.markdown(stat(len(df),                    "Baseline samples"),  unsafe_allow_html=True)
    with c2: st.markdown(stat(df["subject"].nunique(),    "Unique subjects"),   unsafe_allow_html=True)

    st.markdown("---")
    ca, cb, cc = st.columns(3)

    with ca:
        st.markdown(sec("Samples per project"), unsafe_allow_html=True)
        by_proj = df.groupby("project")["sample_id"].count().reset_index()
        by_proj.columns = ["Project", "Sample Count"]
        st.dataframe(by_proj, hide_index=True, width="stretch")
        fig = px.bar(by_proj, x="Project", y="Sample Count", color="Project",
                     title="Samples per project",
                     color_discrete_sequence=PALETTE)
        fig.update_layout(showlegend=False)
        theme(fig)
        st.plotly_chart(fig, width="stretch")

    with cb:
        st.markdown(sec("Response"), unsafe_allow_html=True)
        subj_resp = df.drop_duplicates("subject")["response"].value_counts().reset_index()
        subj_resp.columns = ["Response", "Subject Count"]
        subj_resp["Response"] = subj_resp["Response"].map(
            {"yes": "Responder", "no": "Non-Responder"}
        ).fillna(subj_resp["Response"])
        st.dataframe(subj_resp, hide_index=True, width="stretch")
        fig = px.pie(subj_resp, names="Response", values="Subject Count",
                     title="Responders / non-responders",
                     color_discrete_sequence=[SAGE, TERRA])
        fig.update_traces(textfont=dict(family="JetBrains Mono, monospace", color="#E8DFC8", size=10))
        theme(fig)
        st.plotly_chart(fig, width="stretch")

    with cc:
        st.markdown(sec("Sex"), unsafe_allow_html=True)
        subj_sex = df.drop_duplicates("subject")["sex"].value_counts().reset_index()
        subj_sex.columns = ["Sex", "Subject Count"]
        subj_sex["Sex"] = subj_sex["Sex"].map({"M": "Male", "F": "Female"}).fillna(subj_sex["Sex"])
        st.dataframe(subj_sex, hide_index=True, width="stretch")
        fig = px.pie(subj_sex, names="Sex", values="Subject Count",
                     title="Males / females",
                     color_discrete_sequence=[AMBER, SLATE])
        fig.update_traces(textfont=dict(family="JetBrains Mono, monospace", color="#E8DFC8", size=10))
        theme(fig)
        st.plotly_chart(fig, width="stretch")
