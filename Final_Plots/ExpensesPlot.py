#!/usr/bin/env python3
"""
ExpensesPlot.py

This script reads the simulation output CSV produced by SuperMain.py and generates
a plot for the fully cooperative scenario (collaboration_level = 1.0):

    y = mean_expense_coll / w * 100     (expenses as % of initial wallet)
    x = mean_waiting_time (hours)

Error bars represent:
    sd_expense_coll / w * 100

The figure is saved as both PDF and PNG in the current working directory.
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# Configuration
# =============================================================================

# Default input CSV (can be overridden via CLI argument)
DEFAULT_CSV_PATH = "../../Simulation/Blockchain_BUS/simulation_results.csv"

# Initial wallet amount used for normalization (same w used in the paper)
WALLET_INITIAL_AMOUNT = 6602.23

# Convert milliseconds to hours
MS_TO_HOURS = 3_600_000.0

# Output file names
OUTPUT_PDF_NAME = "expenses_percentage_vs_mean_waiting_time_collab1.pdf"
OUTPUT_PNG_NAME = "expenses_percentage_vs_mean_waiting_time_collab1.png"

# Matplotlib styling (edit here if you want a different look)
BASE_FONT_SIZE = 12
plt.rcParams.update({
    "font.size": BASE_FONT_SIZE,
    "axes.titlesize": BASE_FONT_SIZE,
    "axes.labelsize": BASE_FONT_SIZE,
    "xtick.labelsize": BASE_FONT_SIZE - 1,
    "ytick.labelsize": BASE_FONT_SIZE - 1,
    "legend.fontsize": BASE_FONT_SIZE - 1,
})


# =============================================================================
# Main
# =============================================================================

def main(csv_path: str) -> None:
    """
    Load the simulation CSV, filter for collaboration_level = 1.0,
    compute expenses as % of wallet, and generate the plot.

    Parameters
    ----------
    csv_path : str
        Path to the simulation results CSV file.
    """
    # Load CSV (the project uses ';' as separator)
    try:
        df = pd.read_csv(csv_path, sep=";", engine="python", on_bad_lines="skip")
    except FileNotFoundError:
        print(f"[ERROR] CSV file not found: {csv_path}")
        return

    # Ensure required columns exist
    required_cols = [
        "collaboration_level",
        "mean_waiting_time",
        "mean_expense_coll",
        "sd_expense_coll",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"[ERROR] Missing required columns in CSV: {missing}")
        return

    # Convert numeric columns
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Filter fully cooperative scenario
    df_collab = df[df["collaboration_level"] == 1.0].copy()
    if df_collab.empty:
        print("[WARNING] No rows found with collaboration_level = 1.0.")
        return

    # Group by mean_waiting_time to remove duplicates (if any)
    grouped = (
        df_collab
        .groupby("mean_waiting_time", as_index=False)
        .agg({
            "mean_expense_coll": "mean",
            "sd_expense_coll": "mean",
        })
        .sort_values("mean_waiting_time")
    )

    # Convert waiting time to hours
    grouped["mean_waiting_time_hours"] = grouped["mean_waiting_time"] / MS_TO_HOURS

    # Convert expenses to percentage of initial wallet
    grouped["mean_expense_percentage"] = (
        grouped["mean_expense_coll"] / WALLET_INITIAL_AMOUNT * 100.0
    )
    grouped["sd_expense_percentage"] = (
        grouped["sd_expense_coll"] / WALLET_INITIAL_AMOUNT * 100.0
    )

    # Extract arrays for plotting
    x = grouped["mean_waiting_time_hours"].values
    y = grouped["mean_expense_percentage"].values
    yerr = grouped["sd_expense_percentage"].values

    # Create plot
    fig, ax = plt.subplots(figsize=(6.0, 4.0), dpi=300)
    ax.errorbar(
        x,
        y,
        yerr=yerr,
        fmt="o-",
        capsize=3,
        linewidth=1.0,
        markersize=4,
    )

    ax.set_xlabel("Mean waiting time (hours)")
    ax.set_ylabel("Expenses (% of initial wallet)")
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.7)

    fig.tight_layout()

    # Save plot
    pdf_path = os.path.abspath(OUTPUT_PDF_NAME)
    png_path = os.path.abspath(OUTPUT_PNG_NAME)
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight")

    print(f"[INFO] Saved: {pdf_path}")
    print(f"[INFO] Saved: {png_path}")

    plt.close(fig)


if __name__ == "__main__":
    # Allow the user to pass a CSV path from the command line
    # Example:
    #   python ExpensesPlot.py ../../Simulation/Blockchain_BUS/simulation_results.csv
    csv_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV_PATH
    main(csv_file)
