#!/usr/bin/env python3
"""
generateCDF.py

This script generates CDF plots from precomputed CSV files.

It assumes that a previous preprocessing step has already produced the following CSVs
inside an output directory (default: "output_selection_2020"):

- cdf_amounts_new.csv
- cdf_amounts_original2020.csv
- cdf_mean_interpayment_hours_new.csv
- cdf_mean_interpayment_hours_original2020.csv

Each CSV is expected to contain:
- a value column ("value" for amounts, "value_hours" for times)
- a "cdf" column with cumulative probability values in [0, 1]

The script produces two PDF plots in the same output directory:
- cdf_payment_amounts.pdf
- cdf_mean_interpayment_time_hours.pdf

All comments, labels, and console messages are in English.
"""

from __future__ import annotations

import os
import argparse
from typing import Tuple

import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# Configuration
# =============================================================================

# Directory containing the precomputed CDF CSV files
DEFAULT_OUTPUT_DIR = "output_selection_2020"

# Filenames produced by the preprocessing step
CDF_AMOUNTS_CSV_NEW = "cdf_amounts_new.csv"
CDF_AMOUNTS_CSV_ORIG2020 = "cdf_amounts_original2020.csv"
CDF_MEAN_HOURS_CSV_NEW = "cdf_mean_interpayment_hours_new.csv"
CDF_MEAN_HOURS_CSV_ORIG2020 = "cdf_mean_interpayment_hours_original2020.csv"

# Output plot filenames
PDF_CDF_AMOUNTS = "cdf_payment_amounts.pdf"
PDF_CDF_MEAN_HOURS = "cdf_mean_interpayment_time_hours.pdf"

# Plot styling (centralized here to match paper formatting)
PLOT_SETTINGS = {
    "figsize": (8, 5),
    "font_family": "DejaVu Sans",   # You can change this to "Times New Roman", etc.
    "font_size": 16,
    "axis_label_size": 16,
    "tick_label_size": 14,
    "legend_fontsize": 14,
    "line_width": 1.5,
    "grid_alpha": 0.3,
}


# =============================================================================
# Helper functions
# =============================================================================

def apply_plot_settings() -> None:
    """
    Apply global matplotlib settings from PLOT_SETTINGS.
    """
    plt.rcParams["font.family"] = PLOT_SETTINGS["font_family"]
    plt.rcParams["font.size"] = PLOT_SETTINGS["font_size"]
    plt.rcParams["xtick.labelsize"] = PLOT_SETTINGS["tick_label_size"]
    plt.rcParams["ytick.labelsize"] = PLOT_SETTINGS["tick_label_size"]


def load_cdf_csv(path: str, value_column: str, cdf_column: str = "cdf") -> Tuple[pd.Series, pd.Series]:
    """
    Load a CSV representing a CDF curve.

    Parameters
    ----------
    path : str
        Path to the CSV file.
    value_column : str
        Name of the column containing x-values (e.g., "value" or "value_hours").
    cdf_column : str
        Name of the column containing CDF values (default: "cdf").

    Returns
    -------
    (x, y) : tuple[pandas.Series, pandas.Series]
        x-values and CDF values.
    """
    df = pd.read_csv(path)

    if value_column not in df.columns:
        raise ValueError(f"Column '{value_column}' not found in: {path}")
    if cdf_column not in df.columns:
        raise ValueError(f"Column '{cdf_column}' not found in: {path}")

    x = df[value_column]
    y = df[cdf_column]
    return x, y


def plot_cdf_amounts(output_dir: str) -> None:
    """
    Plot the CDF of payment amounts from precomputed CSVs.

    Required files in output_dir:
    - cdf_amounts_new.csv
    - cdf_amounts_original2020.csv
    """
    new_path = os.path.join(output_dir, CDF_AMOUNTS_CSV_NEW)
    orig_path = os.path.join(output_dir, CDF_AMOUNTS_CSV_ORIG2020)

    if not os.path.isfile(new_path):
        raise FileNotFoundError(f"Missing file: {new_path}")
    if not os.path.isfile(orig_path):
        raise FileNotFoundError(f"Missing file: {orig_path}")

    new_x, new_y = load_cdf_csv(new_path, value_column="value", cdf_column="cdf")
    orig_x, orig_y = load_cdf_csv(orig_path, value_column="value", cdf_column="cdf")

    plt.figure(figsize=PLOT_SETTINGS["figsize"])

    if len(new_x) > 0:
        plt.step(
            new_x,
            new_y,
            where="post",
            label="New dataset (wallet-capped)",
            linewidth=PLOT_SETTINGS["line_width"],
        )

    if len(orig_x) > 0:
        plt.step(
            orig_x,
            orig_y,
            where="post",
            label="Original 2020 dataset (pre-selection)",
            linewidth=PLOT_SETTINGS["line_width"],
        )

    plt.xlabel("Payment amount", fontsize=PLOT_SETTINGS["axis_label_size"])
    plt.ylabel("CDF", fontsize=PLOT_SETTINGS["axis_label_size"])
    plt.grid(True, alpha=PLOT_SETTINGS["grid_alpha"])
    plt.legend(fontsize=PLOT_SETTINGS["legend_fontsize"])
    plt.tight_layout()

    output_pdf = os.path.join(output_dir, PDF_CDF_AMOUNTS)
    plt.savefig(output_pdf, bbox_inches="tight")
    plt.close()
    print(f"[INFO] Saved: {output_pdf}")


def plot_cdf_mean_interpayment_hours(output_dir: str) -> None:
    """
    Plot the CDF of mean interpayment time per user (in hours) from precomputed CSVs.

    Required files in output_dir:
    - cdf_mean_interpayment_hours_new.csv
    - cdf_mean_interpayment_hours_original2020.csv
    """
    new_path = os.path.join(output_dir, CDF_MEAN_HOURS_CSV_NEW)
    orig_path = os.path.join(output_dir, CDF_MEAN_HOURS_CSV_ORIG2020)

    if not os.path.isfile(new_path):
        raise FileNotFoundError(f"Missing file: {new_path}")
    if not os.path.isfile(orig_path):
        raise FileNotFoundError(f"Missing file: {orig_path}")

    new_x, new_y = load_cdf_csv(new_path, value_column="value_hours", cdf_column="cdf")
    orig_x, orig_y = load_cdf_csv(orig_path, value_column="value_hours", cdf_column="cdf")

    plt.figure(figsize=PLOT_SETTINGS["figsize"])

    if len(new_x) > 0:
        plt.step(
            new_x,
            new_y,
            where="post",
            label="New dataset (wallet-capped)",
            linewidth=PLOT_SETTINGS["line_width"],
        )

    if len(orig_x) > 0:
        plt.step(
            orig_x,
            orig_y,
            where="post",
            label="Original 2020 dataset (pre-selection)",
            linewidth=PLOT_SETTINGS["line_width"],
        )

    plt.xlabel("Mean interpayment time per user (hours)", fontsize=PLOT_SETTINGS["axis_label_size"])
    plt.ylabel("CDF", fontsize=PLOT_SETTINGS["axis_label_size"])
    plt.grid(True, alpha=PLOT_SETTINGS["grid_alpha"])
    plt.legend(fontsize=PLOT_SETTINGS["legend_fontsize"])
    plt.tight_layout()

    output_pdf = os.path.join(output_dir, PDF_CDF_MEAN_HOURS)
    plt.savefig(output_pdf, bbox_inches="tight")
    plt.close()
    print(f"[INFO] Saved: {output_pdf}")


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Generate CDF plots from precomputed CSV files.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory containing the CDF CSV files (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    """
    Entry point: validate paths, apply plot settings, and generate both plots.
    """
    args = parse_args()
    output_dir = args.output_dir

    if not os.path.isdir(output_dir):
        raise NotADirectoryError(f"Output directory does not exist: {output_dir}")

    apply_plot_settings()

    plot_cdf_amounts(output_dir)
    plot_cdf_mean_interpayment_hours(output_dir)

    print("[DONE] All CDF plots generated successfully.")


if __name__ == "__main__":
    main()
