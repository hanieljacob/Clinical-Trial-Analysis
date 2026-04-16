"""
Part 3: Statistical Analysis

Compares cell population relative frequencies between responders and non-responders
for melanoma patients treated with miraclib (PBMC samples only).

Uses Mann-Whitney U test (non-parametric, no normality assumption).

Outputs:
  outputs/part3_boxplot.png
  outputs/part3_stats_results.csv
"""

import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
import os

DB_PATH = "clinical_trial.db"
OUTPUT_DIR = "outputs"
POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
ALPHA = 0.05

POP_LABELS = {
    "b_cell": "B Cell",
    "cd8_t_cell": "CD8 T Cell",
    "cd4_t_cell": "CD4 T Cell",
    "nk_cell": "NK Cell",
    "monocyte": "Monocyte",
}


def load_melanoma_miraclib_pbmc(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT
            s.sample_id,
            subj.response,
            cc.b_cell,
            cc.cd8_t_cell,
            cc.cd4_t_cell,
            cc.nk_cell,
            cc.monocyte
        FROM samples s
        JOIN subjects subj ON subj.subject = s.subject
        JOIN cell_counts cc ON cc.sample_id = s.sample_id
        WHERE subj.condition   = 'melanoma'
          AND subj.treatment   = 'miraclib'
          AND s.sample_type    = 'PBMC'
          AND subj.response    IN ('yes', 'no')
    """
    df = pd.read_sql_query(query, conn)
    df["total_count"] = df[POPULATIONS].sum(axis=1)
    for pop in POPULATIONS:
        df[f"{pop}_pct"] = df[pop] / df["total_count"] * 100
    return df


def run_statistics(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for pop in POPULATIONS:
        col = f"{pop}_pct"
        responders = df.loc[df["response"] == "yes", col]
        non_responders = df.loc[df["response"] == "no", col]

        stat, p_value = stats.mannwhitneyu(
            responders, non_responders, alternative="two-sided"
        )

        results.append({
            "population": pop,
            "responders_median_pct": round(responders.median(), 4),
            "non_responders_median_pct": round(non_responders.median(), 4),
            "n_responders": len(responders),
            "n_non_responders": len(non_responders),
            "mannwhitney_u": round(stat, 2),
            "p_value": round(p_value, 6),
            "significant": p_value < ALPHA,
        })

    return pd.DataFrame(results)


def make_boxplot(df: pd.DataFrame, stats_df: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, len(POPULATIONS), figsize=(18, 6), sharey=False)
    fig.suptitle(
        "Cell Population Frequencies: Responders vs Non-Responders\n"
        "(Melanoma patients, miraclib treatment, PBMC samples)",
        fontsize=13, fontweight="bold", y=1.02,
    )

    colors = {"yes": "#4C9BE8", "no": "#E8734C"}
    labels = {"yes": "Responder", "no": "Non-Responder"}

    for ax, pop in zip(axes, POPULATIONS):
        col = f"{pop}_pct"
        data_resp = df.loc[df["response"] == "yes", col].values
        data_nonr = df.loc[df["response"] == "no", col].values

        bp = ax.boxplot(
            [data_resp, data_nonr],
            patch_artist=True,
            medianprops=dict(color="black", linewidth=2),
            whiskerprops=dict(linewidth=1.2),
            capprops=dict(linewidth=1.2),
            flierprops=dict(marker="o", markersize=2, alpha=0.4),
        )
        for patch, key in zip(bp["boxes"], ["yes", "no"]):
            patch.set_facecolor(colors[key])
            patch.set_alpha(0.8)

        # Annotate significance
        stat_row = stats_df.loc[stats_df["population"] == pop].iloc[0]
        p = stat_row["p_value"]
        sig_text = f"p = {p:.4f}"
        if p < 0.001:
            sig_text += " ***"
        elif p < 0.01:
            sig_text += " **"
        elif p < 0.05:
            sig_text += " *"
        else:
            sig_text += " ns"

        ax.set_title(POP_LABELS[pop], fontsize=11, fontweight="bold")
        ax.set_ylabel("Relative Frequency (%)")
        ax.set_xticks([1, 2])
        ax.set_xticklabels(["Resp.", "Non-Resp."], fontsize=9)
        ax.annotate(sig_text, xy=(0.5, 0.97), xycoords="axes fraction",
                    ha="center", va="top", fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.2", fc="lightyellow", ec="gray", alpha=0.8))

    legend_patches = [
        mpatches.Patch(color=colors["yes"], alpha=0.8, label="Responder"),
        mpatches.Patch(color=colors["no"], alpha=0.8, label="Non-Responder"),
    ]
    fig.legend(handles=legend_patches, loc="upper right", bbox_to_anchor=(1.0, 1.0), fontsize=10)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "part3_boxplot.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return out_path


def main() -> tuple[pd.DataFrame, pd.DataFrame]:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        df = load_melanoma_miraclib_pbmc(conn)
    finally:
        conn.close()

    stats_df = run_statistics(df)

    # Save stats
    stats_path = os.path.join(OUTPUT_DIR, "part3_stats_results.csv")
    stats_df.to_csv(stats_path, index=False)

    # Print summary
    print("\nPart 3: Statistical Results (Mann-Whitney U, two-sided, α=0.05)")
    print("-" * 70)
    for _, row in stats_df.iterrows():
        sig = "SIGNIFICANT" if row["significant"] else "not significant"
        print(f"  {row['population']:<15} p={row['p_value']:.6f}  [{sig}]  "
              f"Resp. median={row['responders_median_pct']:.2f}%  "
              f"Non-resp. median={row['non_responders_median_pct']:.2f}%")
    print(f"\nStats saved to {stats_path}")

    # Make boxplot
    plot_path = make_boxplot(df, stats_df)
    print(f"Boxplot saved to {plot_path}")

    return df, stats_df


if __name__ == "__main__":
    main()
