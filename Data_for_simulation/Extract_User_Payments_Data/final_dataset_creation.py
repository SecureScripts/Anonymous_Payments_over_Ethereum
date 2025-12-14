#!/usr/bin/env python3
"""
final_dataset_creation.py

This script creates the final "wallet-capped" dataset used by the simulator.

Input
-----
It expects a CSV file produced by the initial preprocessing step
(e.g., `first_dataset_preprocess.py`):

    user_transaction_pairs.csv

with columns:
- User
- pairs_json  (JSON-encoded list of [timestamp_ms, amount])

What this script does
---------------------
1) Builds *reference CDFs* from the original 2020 transactions:
   - CDF of payment amounts (all 2020 payments)
   - CDF of per-user mean interpayment time (hours)

2) Selects users who have payments in 2020 and keeps the top 1000 users
   by total amount spent in 2020.

3) Defines a "wallet" value equal to the minimum 2020 total among the selected users.
   This wallet is used to cap each user's payment sequence so that all selected users
   have the same total spending amount.

4) For each selected user:
   - Starting from the first transaction in 2020, collects transactions until the
     cumulative sum reaches the wallet.
   - The last payment is truncated if necessary to match the wallet exactly.

5) Saves the final filtered dataset to:
    output_selection_2020/filtered_dataset.csv

6) Saves CSV files containing the CDF curves (new vs original 2020):
   - cdf_amounts_new.csv
   - cdf_amounts_original2020.csv
   - cdf_mean_interpayment_hours_new.csv
   - cdf_mean_interpayment_hours_original2020.csv

7) Optionally generates PDF plots for the two CDF comparisons.

Notes
-----
- All timestamps are treated as UNIX timestamps in milliseconds.
- The year filtering is performed using UTC boundaries for 2020.
"""

from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# Configuration
# =============================================================================

INPUT_CSV = "user_transaction_pairs.csv"      # CSV produced by the initial preprocessing step
OUTPUT_DIR = "output_selection_2020"          # Output folder
NEW_DATASET_CSV = "filtered_dataset.csv"      # Final dataset (used by the simulator)

# Output CSV files for the empirical CDF curves
CDF_AMOUNTS_CSV_NEW = "cdf_amounts_new.csv"
CDF_AMOUNTS_CSV_ORIG2020 = "cdf_amounts_original2020.csv"
CDF_MEAN_HOURS_CSV_NEW = "cdf_mean_interpayment_hours_new.csv"
CDF_MEAN_HOURS_CSV_ORIG2020 = "cdf_mean_interpayment_hours_original2020.csv"

# If True, generate PDF plots comparing original vs new CDFs
MAKE_PLOTS = True

# Number of users to keep (top spenders in 2020)
TOP_USERS = 1000


# =============================================================================
# 2020 time boundaries (UTC) in milliseconds
# =============================================================================

TS_2020_START_MS = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
TS_2021_START_MS = int(datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def in_2020(ts_ms: int) -> bool:
    """
    Return True if a timestamp (ms) falls within year 2020 (UTC boundaries).
    """
    return TS_2020_START_MS <= ts_ms < TS_2021_START_MS


# =============================================================================
# Data loading and helper computations
# =============================================================================

def load_dataset(csv_path: str) -> pd.DataFrame:
    """
    Load the dataset and parse pairs_json into a Python list.

    Parameters
    ----------
    csv_path : str
        Input CSV path.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns: ["User", "pairs"] where pairs is a list.
    """
    df = pd.read_csv(csv_path)
    df["pairs"] = df["pairs_json"].apply(lambda s: json.loads(s) if isinstance(s, str) else [])
    return df[["User", "pairs"]]


def total_spent_in_2020(pairs: list) -> float:
    """
    Compute total amount spent in 2020 for a given list of (timestamp, amount) pairs.
    """
    return float(sum(amount for ts, amount in pairs if in_2020(int(ts))))


def first_ts_in_2020(pairs: list) -> Optional[int]:
    """
    Return the earliest timestamp (ms) in 2020, or None if the user has no 2020 payments.
    """
    ts_2020 = [int(ts) for ts, _ in pairs if in_2020(int(ts))]
    return min(ts_2020) if ts_2020 else None


def build_capped_sequence_from_first_2020(pairs: list, wallet: float) -> list:
    """
    Starting from the first transaction in 2020, accumulate payments until the
    total reaches the wallet amount. The last payment is truncated (if needed)
    to match the wallet exactly.

    Parameters
    ----------
    pairs : list
        List of (timestamp_ms, amount).
    wallet : float
        Wallet cap to enforce.

    Returns
    -------
    list
        List of [timestamp_ms, amount] capped to 'wallet'.
    """
    if wallet <= 0:
        return []

    # Sort transactions by timestamp
    pairs_sorted = sorted(((int(ts), float(a)) for ts, a in pairs), key=lambda x: x[0])

    # Find the first transaction timestamp in 2020
    start_ts = first_ts_in_2020(pairs_sorted)
    if start_ts is None:
        return []

    # Keep transactions from start_ts onward
    tail = [(ts, amt) for ts, amt in pairs_sorted if ts >= start_ts]

    result = []
    acc = 0.0

    for ts, amt in tail:
        remaining = wallet - acc
        if remaining <= 0:
            break

        if amt <= remaining + 1e-12:
            result.append([ts, float(amt)])
            acc += amt
        else:
            # Truncate last payment to fit wallet exactly
            result.append([ts, float(remaining)])
            acc += remaining
            break

    # Edge case: if nothing was added, but there is at least one transaction
    if not result and tail:
        ts0, amt0 = tail[0]
        result.append([ts0, float(min(wallet, amt0))])

    # Safety adjustment in case of floating-point overshoot
    total = sum(a for _, a in result)
    if total > wallet:
        diff = total - wallet
        ts_last, amt_last = result[-1]
        result[-1] = [ts_last, float(max(0.0, amt_last - diff))]

    return result


def empirical_cdf(values: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute an empirical CDF for the given array.

    Parameters
    ----------
    values : np.ndarray
        Input values.

    Returns
    -------
    (x_sorted, y) : tuple[np.ndarray, np.ndarray]
        Sorted values and corresponding cumulative probabilities.
    """
    if values.size == 0:
        return np.array([]), np.array([])

    x = np.sort(values)
    n = x.size
    y = np.arange(1, n + 1) / n
    return x, y


def per_user_mean_interpayment_hours(pairs_list: list) -> np.ndarray:
    """
    For each user, compute the mean time between consecutive payments (in hours).

    Parameters
    ----------
    pairs_list : list
        List of per-user lists of [timestamp_ms, amount].

    Returns
    -------
    np.ndarray
        Array of mean interpayment times in hours (one per eligible user).
    """
    means = []
    for pairs in pairs_list:
        if len(pairs) < 2:
            continue

        seq = sorted(((int(ts), float(a)) for ts, a in pairs), key=lambda x: x[0])
        ts_arr = np.array([ts for ts, _ in seq], dtype=np.int64)

        diffs_ms = np.diff(ts_arr)
        diffs_ms = diffs_ms[diffs_ms > 0]

        if diffs_ms.size > 0:
            mean_hours = float(np.mean(diffs_ms) / (1000.0 * 60.0 * 60.0))
            means.append(mean_hours)

    return np.array(means, dtype=float)


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1) Load dataset
    # -------------------------------------------------------------------------
    df = load_dataset(INPUT_CSV)
    print(f"[INFO] Loaded input dataset: {INPUT_CSV} (users: {len(df)})")

    # -------------------------------------------------------------------------
    # 2) Build reference CDFs from original 2020 transactions
    # -------------------------------------------------------------------------
    original2020_amounts: List[float] = []
    original2020_pairs_per_user: List[list] = []

    for _, row in df.iterrows():
        pairs_2020 = [[int(ts), float(a)] for ts, a in row["pairs"] if in_2020(int(ts))]
        if pairs_2020:
            original2020_pairs_per_user.append(pairs_2020)
            original2020_amounts.extend(float(amt) for _, amt in pairs_2020)

    original2020_amounts_arr = np.array(original2020_amounts, dtype=float)
    orig_x_amt, orig_y_amt = empirical_cdf(original2020_amounts_arr)

    orig_mean_hours = per_user_mean_interpayment_hours(original2020_pairs_per_user)
    orig_x_hours, orig_y_hours = empirical_cdf(orig_mean_hours)

    print(f"[INFO] Original 2020 reference: {len(original2020_amounts)} payments total.")

    # -------------------------------------------------------------------------
    # 3) Select users with 2020 activity and keep top N by 2020 spending
    # -------------------------------------------------------------------------
    df["total_2020"] = df["pairs"].apply(total_spent_in_2020)
    df_has2020 = df[df["total_2020"] > 0].copy()

    if df_has2020.empty:
        print("[ERROR] No users with payments in 2020. Exiting.")
        return

    df_top = df_has2020.sort_values("total_2020", ascending=False).head(TOP_USERS).copy()
    print(f"[INFO] Selected top users by 2020 spending: {len(df_top)}")

    # -------------------------------------------------------------------------
    # 4) Compute wallet cap
    # -------------------------------------------------------------------------
    wallet = float(df_top["total_2020"].min())
    print(f"[INFO] Wallet cap (minimum 2020 total among selected users): {wallet:.6f}")

    # -------------------------------------------------------------------------
    # 5) Create capped dataset
    # -------------------------------------------------------------------------
    new_rows = []
    capped_pairs_per_user = []

    for _, row in df_top.iterrows():
        user = row["User"]
        capped_pairs = build_capped_sequence_from_first_2020(row["pairs"], wallet)

        if capped_pairs:
            new_rows.append({
                "User": user,
                "pairs_json": json.dumps(capped_pairs, separators=(",", ":"))
            })
            capped_pairs_per_user.append(capped_pairs)

    new_df = pd.DataFrame(new_rows, columns=["User", "pairs_json"])

    new_dataset_path = os.path.join(OUTPUT_DIR, NEW_DATASET_CSV)
    new_df.to_csv(new_dataset_path, index=False)
    print(f"[INFO] New wallet-capped dataset saved to: {new_dataset_path} (users: {len(new_df)})")

    # -------------------------------------------------------------------------
    # 6) Compute CDFs for the new dataset (amounts)
    # -------------------------------------------------------------------------
    new_amounts = []
    for s in new_df["pairs_json"]:
        try:
            pairs = json.loads(s)
        except Exception:
            pairs = []
        for _, amt in pairs:
            new_amounts.append(float(amt))

    new_amounts_arr = np.array(new_amounts, dtype=float)
    new_x_amt, new_y_amt = empirical_cdf(new_amounts_arr)

    # Save amount CDF CSVs
    pd.DataFrame({"value": new_x_amt, "cdf": new_y_amt}).to_csv(
        os.path.join(OUTPUT_DIR, CDF_AMOUNTS_CSV_NEW), index=False
    )
    pd.DataFrame({"value": orig_x_amt, "cdf": orig_y_amt}).to_csv(
        os.path.join(OUTPUT_DIR, CDF_AMOUNTS_CSV_ORIG2020), index=False
    )
    print("[INFO] Amount CDF CSV files written.")

    # -------------------------------------------------------------------------
    # 7) Compute CDFs for the new dataset (mean interpayment time per user)
    # -------------------------------------------------------------------------
    new_mean_hours = per_user_mean_interpayment_hours(capped_pairs_per_user)
    new_x_hours, new_y_hours = empirical_cdf(new_mean_hours)

    # Save mean interpayment time CDF CSVs
    pd.DataFrame({"value_hours": new_x_hours, "cdf": new_y_hours}).to_csv(
        os.path.join(OUTPUT_DIR, CDF_MEAN_HOURS_CSV_NEW), index=False
    )
    pd.DataFrame({"value_hours": orig_x_hours, "cdf": orig_y_hours}).to_csv(
        os.path.join(OUTPUT_DIR, CDF_MEAN_HOURS_CSV_ORIG2020), index=False
    )
    print("[INFO] Mean interpayment time CDF CSV files written.")

    # -------------------------------------------------------------------------
    # 8) Optional: generate PDF plots comparing original vs new
    # -------------------------------------------------------------------------
    if MAKE_PLOTS:
        # CDF of payment amounts
        plt.figure(figsize=(8, 5))
        if new_x_amt.size > 0:
            plt.step(new_x_amt, new_y_amt, where="post", label="New dataset (wallet-capped)")
        if orig_x_amt.size > 0:
            plt.step(orig_x_amt, orig_y_amt, where="post", label="Original 2020 (pre-selection)")
        plt.xlabel("Payment amount")
        plt.ylabel("CDF")
        plt.title("CDF of payment amounts")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "cdf_payment_amounts.pdf"))
        plt.close()

        # CDF of mean interpayment time per user (hours)
        plt.figure(figsize=(8, 5))
        if new_x_hours.size > 0:
            plt.step(new_x_hours, new_y_hours, where="post", label="New dataset (wallet-capped)")
        if orig_x_hours.size > 0:
            plt.step(orig_x_hours, orig_y_hours, where="post", label="Original 2020 (pre-selection)")
        plt.xlabel("Mean interpayment time per user (hours)")
        plt.ylabel("CDF")
        plt.title("CDF of mean interpayment time per user")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "cdf_mean_interpayment_time_hours.pdf"))
        plt.close()

        print("[INFO] CDF comparison plots saved as PDF in the output directory.")

    print("[DONE] Final dataset creation completed successfully.")


if __name__ == "__main__":
    main()
