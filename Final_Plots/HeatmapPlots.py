#!/usr/bin/env python3
"""
HeatmapPlots.py

This script generates the final figures used in the paper
"Network-Layer Anonymous Payments over Ethereum via Cover Transactions".

Given the CSV output produced by SuperMain.py, it creates, for each
collaboration level:

1) A heatmap showing the difference in expenses between non-cooperative
   and cooperative users:
       delta = mean_expense_non_coll - mean_expense_coll

2) A line plot showing the average waiting time as a function of the bus
   hop time (T_hop), with standard deviation error bars.

Figures are saved both as PNG and PDF files.
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# Global plotting configuration
# =============================================================================

# Base font size suitable for a two-column LaTeX paper
BASE_FONT_SIZE = 12

plt.rcParams.update({
    "font.size": BASE_FONT_SIZE,
    "axes.titlesize": BASE_FONT_SIZE,
    "axes.labelsize": BASE_FONT_SIZE,
    "xtick.labelsize": BASE_FONT_SIZE - 1,
    "ytick.labelsize": BASE_FONT_SIZE - 1,
    "legend.fontsize": BASE_FONT_SIZE - 1,
})

# Collaboration levels for which plots are generated
COLLAB_LEVELS_TO_PLOT = [0.0, 0.3, 0.6, 0.9, 1.0]


# =============================================================================
# Helper functions
# =============================================================================

def compute_bin_edges(sorted_values: np.ndarray) -> np.ndarray:
    """
    Compute bin edges for pcolormesh given a sorted array of bin centers.

    Parameters
    ----------
    sorted_values : np.ndarray
        Sorted array of unique bin centers.

    Returns
    -------
    np.ndarray
        Array of bin edges with length len(sorted_values) + 1.
    """
    if len(sorted_values) == 1:
        delta = 0.5
        return np.array([sorted_values[0] - delta, sorted_values[0] + delta])

    diffs = np.diff(sorted_values)
    internal_edges = sorted_values[:-1] + diffs / 2.0

    left_edge = sorted_values[0] - diffs[0] / 2.0
    right_edge = sorted_values[-1] + diffs[-1] / 2.0

    return np.concatenate([[left_edge], internal_edges, [right_edge]])


def plot_for_collaboration_level(
    df: pd.DataFrame,
    coll_level: float,
    output_prefix: str = "heatmap_delta"
):
    """
    Generate the heatmap and waiting-time plot for a given collaboration level.

    Parameters
    ----------
    df : pandas.DataFrame
        Simulation results dataframe.
    coll_level : float
        Collaboration level of non-cooperative users.
    output_prefix : str
        Prefix used for output file names.
    """
    # Filter dataset for the selected collaboration level
    sub = df[df["collaboration_level"] == coll_level].copy()

    if sub.empty:
        print(f"[WARNING] No data for collaboration_level = {coll_level}. Skipping.")
        return

    # Compute expense difference
    sub["delta_expense"] = (
        sub["mean_expense_non_coll"] - sub["mean_expense_coll"]
    )

    # Pivot table for heatmap
    pivot_delta = sub.pivot_table(
        index="deposit",
        columns="T_hop",
        values="delta_expense",
        aggfunc="mean"
    ).sort_index(axis=0).sort_index(axis=1)

    deposits = pivot_delta.index.values
    t_hops = pivot_delta.columns.values
    Z = pivot_delta.values

    # Compute bin edges
    x_edges = compute_bin_edges(t_hops)
    y_edges = compute_bin_edges(deposits)

    # Meshgrid for contour line
    Xc, Yc = np.meshgrid(t_hops, deposits)

    # Aggregate waiting time statistics
    grouped_wait = sub.groupby("T_hop")
    t_hop_wait = grouped_wait["mean_waiting_time"].mean().index.values
    mean_wait = grouped_wait["mean_waiting_time"].mean().values
    sd_wait = grouped_wait["sd_waiting_time"].mean().values

    # Extract theoretical deposit curve if available
    has_theoretical = (
        "theoretical_deposit_percentage" in sub.columns
        and not sub["theoretical_deposit_percentage"].isna().all()
    )

    theoretical_deposit_vals = None
    if has_theoretical:
        theo_series = (
            sub.dropna(subset=["theoretical_deposit_percentage"])
               .groupby("T_hop")["theoretical_deposit_percentage"]
               .first()
        )
        theoretical_deposit_vals = theo_series.reindex(t_hops).values

    # =========================================================================
    # Create figure
    # =========================================================================

    fig, (ax_heat, ax_wait) = plt.subplots(
        2,
        1,
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05},
        dpi=300
    )
    fig.set_size_inches(7.0, 4.0)

    # -------------------------------------------------------------------------
    # Heatmap (top)
    # -------------------------------------------------------------------------

    cmap = plt.get_cmap("seismic")
    vmax = np.nanmax(np.abs(Z))
    if vmax == 0:
        vmax = 1.0

    mesh = ax_heat.pcolormesh(
        x_edges,
        y_edges,
        Z,
        cmap=cmap,
        vmin=-vmax,
        vmax=vmax,
        shading="auto"
    )

    cbar = fig.colorbar(
        mesh,
        ax=[ax_heat, ax_wait],
        fraction=0.046,
        pad=0.02
    )
    cbar.set_label("Δ expense = non-cooperative − cooperative")

    ax_heat.set_ylabel("Deposit (% of wallet)")

    # Zero-delta contour
    if np.any(Z > 0) and np.any(Z < 0):
        ax_heat.contour(
            Xc,
            Yc,
            Z,
            levels=[0.0],
            colors="black",
            linewidths=1.0
        )
        ax_heat.plot([], [], color="black", linewidth=1.0, label="Δ = 0")

    # Theoretical deposit curve
    if has_theoretical and theoretical_deposit_vals is not None:
        ax_heat.plot(
            t_hops,
            theoretical_deposit_vals,
            color="yellow",
            linestyle="--",
            linewidth=1.2,
            label="Theoretical deposit"
        )

    ax_heat.legend(loc="upper right", frameon=True)

    # -------------------------------------------------------------------------
    # Waiting time plot (bottom)
    # -------------------------------------------------------------------------

    ax_wait.errorbar(
        t_hop_wait,
        mean_wait / 3600000.0,
        yerr=sd_wait / 3600000.0,
        fmt="o-",
        linewidth=0.8,
        markersize=3,
        capsize=2
    )

    ax_wait.set_xlabel(r"$T_{\mathrm{hop}}$ (s)")
    ax_wait.set_ylabel("Waiting time (h)")
    ax_wait.grid(True, linestyle=":", linewidth=0.5, alpha=0.7)

    fig.tight_layout()

    # Save figures
    png_name = f"{output_prefix}_coll_{coll_level:.1f}.png"
    pdf_name = f"{output_prefix}_coll_{coll_level:.1f}.pdf"
    fig.savefig(png_name, bbox_inches="tight")
    fig.savefig(pdf_name, bbox_inches="tight")

    print(f"[INFO] Saved {png_name} and {pdf_name}")
    plt.close(fig)


# =============================================================================
# Main
# =============================================================================

def main(csv_path: str):
    """
    Load simulation results and generate plots for all collaboration levels.
    """
    df = pd.read_csv(csv_path, sep=";")

    # Convert time from ms to seconds
    df["T_hop"] = pd.to_numeric(df["T_hop"], errors="coerce") / 1000.0

    numeric_columns = [
        "deposit",
        "collaboration_level",
        "mean_waiting_time",
        "sd_waiting_time",
        "mean_expense_coll",
        "sd_expense_coll",
        "mean_expense_non_coll",
        "sd_expense_non_coll",
        "theoretical_deposit",
        "theoretical_deposit_percentage",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for coll in COLLAB_LEVELS_TO_PLOT:
        plot_for_collaboration_level(df, coll)

    print("[DONE] All plots generated successfully.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = "../../Simulation/Blockchain_BUS/simulation_results.csv"

    main(csv_file)
