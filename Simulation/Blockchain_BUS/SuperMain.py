"""
SuperMain.py

This script runs the full simulation campaign for the paper
"Network-Layer Anonymous Payments over Ethereum via Cover Transactions".

It:
- Loads the preprocessed user payment dataset (wallet-capped 2020 data).
- Estimates the average payment generation rate and the average number of payments per user.
- Loads execution-based gas costs (from Ganache) for startConfirm() and pay().
- Explores different configurations of:
    * bus hop time,
    * deposit size (as a percentage of wallet),
    * collaboration level for non-cooperative users.
- For each configuration, runs multiple simulations of a single ring using BlockchainRing.
- Collects statistics on:
    * mean waiting time,
    * expenses of cooperative users,
    * expenses of non-cooperative users.
- Saves the results to simulation_results.csv.
"""

import csv
from math import inf
import random
from typing import List, Dict, Tuple
import math
import pandas as pd
import json
import statistics as stats

from User import User
from BlockchainRing import BlockchainRing


# --------------------------------------------------------------------------------------
# Utility functions for dataset statistics
# --------------------------------------------------------------------------------------


def average_payment_generation_rate(pairs_by_source: Dict[int, list]) -> float:
    """
    Compute the global average payment generation rate (payments per second).

    For each user in pairs_by_source, this function:
    - sorts that user's payments by timestamp,
    - computes the average inter-payment time,
    - averages these per-user inter-payment times across all users.

    The final rate is:
        rate = 1 / (global_mean_inter_payment_time)

    Parameters
    ----------
    pairs_by_source : dict
        Mapping: source_user_id -> list of [timestamp_ms, amount].

    Returns
    -------
    float
        Global average payment generation rate (payments per second).
    """
    mean_intervals = []

    for _, pairs in pairs_by_source.items():
        if len(pairs) < 2:
            continue

        # Sort by timestamp (in ms)
        sorted_pairs = sorted((int(ts), float(val)) for ts, val in pairs)
        timestamps = [ts for ts, _ in sorted_pairs]

        # Compute successive differences in seconds
        diffs_sec = [
            (timestamps[i + 1] - timestamps[i]) / 1000.0
            for i in range(len(timestamps) - 1)
            if timestamps[i + 1] > timestamps[i]
        ]

        if not diffs_sec:
            continue

        mean_interval = sum(diffs_sec) / len(diffs_sec)
        mean_intervals.append(mean_interval)

    if not mean_intervals:
        return 0.0

    global_mean_interval = sum(mean_intervals) / len(mean_intervals)
    return 1.0 / global_mean_interval


def average_number_of_payments(pairs_by_source: Dict[int, list]) -> float:
    """
    Compute the average number of payments per user.

    Parameters
    ----------
    pairs_by_source : dict
        Mapping: source_user_id -> list of [timestamp_ms, amount].

    Returns
    -------
    float
        Average number of payments per user.
    """
    if not pairs_by_source:
        return 0.0
    counts = [len(p) for p in pairs_by_source.values()]
    return float(sum(counts) / len(counts))


def pick_users_indices(available_indices: List[int], k: int, seed: int) -> List[int]:
    """
    Draw k user indices from the available indices.

    If k <= len(available_indices), a sample WITHOUT replacement is used.
    If k  > len(available_indices), sampling is WITH replacement.

    The random seed is given by `seed` for reproducibility.

    Parameters
    ----------
    available_indices : list[int]
        List of indices that can be chosen.
    k : int
        Number of indices to draw.
    seed : int
        Random seed.

    Returns
    -------
    list[int]
        Selected indices.
    """
    rng = random.Random(seed)
    if k <= len(available_indices):
        return rng.sample(available_indices, k)
    # With replacement
    return [rng.choice(available_indices) for _ in range(k)]


def build_dict_from_csv(path_csv: str, target_k: int, target_alpha: int):
    """
    Build two dictionaries from the Ganache result CSV:

    - result_end:     gas costs for rounds that END an epoch
    - result_no_end:  gas costs for rounds that DO NOT end an epoch

    Each dictionary is indexed by the number of payments in the round.

    Parameters
    ----------
    path_csv : str
        Path to the CSV file containing Ganache gas measurements.
    target_k : int
        Number of cooperative users in the ring.
    target_alpha : int
        Number of additional (possibly non-cooperative) users.

    Returns
    -------
    (dict, dict)
        result_end, result_no_end
    """
    result_end = {}
    result_no_end = {}

    with open(path_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            try:
                k_val = int(row["k"].strip())
                alpha_val = int(row["alpha"].strip())

                if not (k_val == target_k and alpha_val == target_alpha):
                    continue

                n_pay = int(row["nPayments"])
                end_epoch = str(row["End Epoch"])
                start_confirm = int(row["StartConfirmGas"])
                pay_gas = int(row["PayGas"])

                if end_epoch == "Yes":
                    result_end[n_pay] = {
                        "StartConfirmGas": start_confirm,
                        "PayGas": pay_gas,
                    }
                else:
                    result_no_end[n_pay] = {
                        "StartConfirmGas": start_confirm,
                        "PayGas": pay_gas,
                    }

            except Exception:
                # Invalid or incomplete row, skip it
                continue

    return result_end, result_no_end


def ceil_to_multiple(x: float, step: float) -> float:
    """
    Round x up to the nearest multiple of step.

    Parameters
    ----------
    x : float
        Value to be rounded.
    step : float
        Step size.

    Returns
    -------
    float
        Rounded value.
    """
    if step <= 0:
        return x
    return math.ceil(x / step) * step


def load_filtered_dataset(path: str) -> pd.DataFrame:
    """
    Load the preprocessed "wallet-capped" dataset for the year 2020.

    The input CSV is expected to contain:
    - a "User" column,
    - a "pairs_json" column with a JSON list of [timestamp_ms, amount].

    This function converts "pairs_json" to a Python list and returns a
    DataFrame with columns: "User", "pairs".

    Parameters
    ----------
    path : str
        Path to the filtered dataset CSV.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns "User" and "pairs".
    """
    df = pd.read_csv(path)
    df["pairs"] = df["pairs_json"].apply(
        lambda s: json.loads(s) if isinstance(s, str) else []
    )
    return df[["User", "pairs"]]


def mean_sd(values):
    """
    Compute mean and standard deviation of a list of values.

    Parameters
    ----------
    values : list[float]

    Returns
    -------
    (float, float)
        (mean, standard deviation). If there is a single value, std = 0.0.
        If the list is empty, both mean and std are 0.0.
    """
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0
    mn = stats.mean(values)
    sd = stats.stdev(values)
    return float(mn), float(sd)


# --------------------------------------------------------------------------------------
# Global configuration constants
# --------------------------------------------------------------------------------------

# Path to Ganache gas measurement results (FINAL_RES.csv)
FINAL_RES_CSV = "../../Data_for_simulation/Extract_Blockchain_Operation_Cost/FINAL_RES.csv"

# Cost in USD of one gas unit (from Price_Estimate results for 2024)
GAS_IN_DOLLARS = 0.0000598392

# Confirmation transaction gas (from GanacheSimulationCosts.py)
CONFIRMATION_COST_GAS = 50056
CONFIRMATION_COST_DOLLARS = CONFIRMATION_COST_GAS * GAS_IN_DOLLARS

# Initial wallet balance per user (in USD)
WALLET_START_PER_USER = 6602.23

# Number of epochs in the ring lifetime
E = 20

# Path to the filtered 2020 dataset ("wallet-capped" users)
FILTERED_DATASET_CSV = (
    "../../Data_for_simulation/UserPayments/output_selection_2020/filtered_dataset.csv"
)

# Output file for all simulation results
OUTPUT_CSV = "simulation_results.csv"


# --------------------------------------------------------------------------------------
# Main simulation procedure
# --------------------------------------------------------------------------------------


def main():
    # Load filtered dataset for 2020 (top 1000 wallet-capped users)
    df_filtered = load_filtered_dataset(FILTERED_DATASET_CSV)

    # Available source user indices (pointing to rows in df_filtered)
    source_user_ids = df_filtered.index.to_list()
    pairs_by_source = df_filtered["pairs"].to_dict()

    # Compute average payment generation rate and average number of payments
    lambda_ = average_payment_generation_rate(pairs_by_source)
    m = average_number_of_payments(pairs_by_source)

    # Prepare CSV output file
    with open(OUTPUT_CSV, mode="w", newline="") as f:
        writer = csv.writer(f, delimiter=';')

        # CSV header
        writer.writerow([
            "T_hop",
            "deposit_percentage",
            "collaboration_level",
            "mean_waiting_time",
            "sd_waiting_time",
            "mean_expense_coll",
            "sd_expense_coll",
            "mean_expense_non_coll",
            "sd_expense_non_coll",
            "theoretical_deposit",
            "theoretical_deposit_percentage",
        ])

        # In the current setup, we consider exactly 100 cooperative users
        for num_cooperative_users in [100]:
            # and 30% additional non-cooperative users
            for level in [30]:
                alpha = (level * num_cooperative_users) // 100
                total_users = num_cooperative_users + alpha

                # Load gas results for this (k, alpha) pair
                result_end_epoch, result_no_end_epoch = build_dict_from_csv(
                    FINAL_RES_CSV,
                    num_cooperative_users,
                    alpha,
                )

                total_wallet = WALLET_START_PER_USER * total_users

                # Collaboration level among the alpha "non-cooperative" users
                # 1.0 means always cooperative; 0.0 means never cooperative
                for collaboration_level_alpha in [0, 0.3, 0.6, 0.9, 1]:
                    # Build a list of collaboration levels for all users:
                    # first 'num_cooperative_users' are fully cooperative,
                    # the remaining 'alpha' have collaboration_level_alpha.
                    collaboration_level = [
                        1.0 if i < num_cooperative_users else collaboration_level_alpha
                        for i in range(total_users)
                    ]
                    random.shuffle(collaboration_level)

                    # Bus hop time in milliseconds
                    for bus_hop_time in range(10000, 210001, 10000):
                        # Round time in seconds
                        T_round = total_users * bus_hop_time / 1000.0

                        # Expected number of rounds per epoch
                        n_round = m / (E * lambda_ * T_round)

                        # Maximum number of payments per round (upper bound)
                        M_round = min(
                            math.ceil(total_users * lambda_ * T_round),
                            total_users - 1,
                        )

                        # Gas-based costs for a "no end epoch" round
                        pay_cost_dollars = (
                            result_no_end_epoch[M_round]["PayGas"] * GAS_IN_DOLLARS
                        )
                        start_confirm_cost_dollars = (
                            result_no_end_epoch[M_round]["StartConfirmGas"]
                            * GAS_IN_DOLLARS
                        )

                        # Extra cost at epoch end (difference between end_epoch and no_end_epoch)
                        deposit_back_cost_dollars = (
                            (
                                result_end_epoch[M_round]["PayGas"]
                                + result_end_epoch[M_round]["StartConfirmGas"]
                            ) - (
                                result_no_end_epoch[M_round]["PayGas"]
                                + result_no_end_epoch[M_round]["StartConfirmGas"]
                            )
                        ) * GAS_IN_DOLLARS

                        # Theoretical delta_D for this configuration
                        delta_D = (
                            CONFIRMATION_COST_DOLLARS * (total_users - 1) * n_round
                            + (pay_cost_dollars + start_confirm_cost_dollars) * n_round
                            + deposit_back_cost_dollars
                        )

                        # Theoretical deposit per user
                        theoretical_deposit = (delta_D * E) / total_users
                        theoretical_deposit_percentage = (
                            theoretical_deposit / WALLET_START_PER_USER
                        ) * 100.0

                        # Explore initial deposit as a percentage of total wallet
                        for initial_deposit_percentage in range(1, 201, 5):
                            total_deposit = (total_wallet * initial_deposit_percentage) / 100.0
                            current_delta_D = total_deposit / E
                            deposit_per_user = total_deposit / total_users

                            waiting_times_all_runs = []
                            expenses_coll_all_runs = []
                            expenses_non_coll_all_runs = []

                            # Repeat simulation for multiple runs to capture variability
                            for run in range(0, 30):
                                print(
                                    f"run: {run} | "
                                    f"collaboration_level_alpha: {collaboration_level_alpha} | "
                                    f"bus_hop_time: {bus_hop_time} ms | "
                                    f"initial_deposit_percentage: {initial_deposit_percentage}%"
                                )

                                # Select source users in a reproducible way
                                chosen = pick_users_indices(
                                    source_user_ids,
                                    total_users,
                                    seed=run,
                                )

                                # Instantiate local User objects with assigned collaboration levels
                                users = [
                                    User(i, WALLET_START_PER_USER, [], collaboration_level[i])
                                    for i in range(total_users)
                                ]

                                first_ts_global = inf

                                # Assign payments from the chosen source users
                                for new_uid, src_idx in enumerate(chosen):
                                    payments = pairs_by_source[src_idx]  # [[ts_ms, amount], ...]
                                    users[new_uid].payments = payments

                                    if payments:
                                        # Each payment is [timestamp_ms, amount, remainder]
                                        ts_first = payments[0][0]
                                        if ts_first < first_ts_global:
                                            first_ts_global = ts_first

                                # If no payments exist at all (unlikely in this dataset),
                                # we abort the simulation to avoid invalid timestamps.
                                if first_ts_global is inf:
                                    raise RuntimeError(
                                        "No valid payments found in the dataset for this configuration."
                                    )

                                # Create and run the ring simulation
                                ring = BlockchainRing(
                                    users=users,
                                    confirm_cost_dollars=CONFIRMATION_COST_DOLLARS,
                                    gas_in_dollars=GAS_IN_DOLLARS,
                                    result_end_epoch=result_end_epoch,
                                    result_no_end_epoch=result_no_end_epoch,
                                    bus_hop_time=bus_hop_time,
                                    first_ts_global=first_ts_global,
                                    epoch_num=E,
                                    delta_D=current_delta_D,
                                    total_wallet=total_wallet,
                                    initial_deposit=total_deposit,
                                )

                                print("Starting simulation...")
                                ring.run_simulation()
                                print("Simulation finished.")

                                # Collect statistics from this run
                                for u in ring.users:
                                    # Waiting time
                                    waiting_times_all_runs.append(
                                        u.compute_mean_waiting_time()
                                    )

                                    # Expenses: separate cooperative vs non-cooperative users
                                    effective_expense = (
                                        u.expenses - u.refunded_deposit + deposit_per_user
                                    )
                                    if u.collaboration_level == 1.0:
                                        expenses_coll_all_runs.append(effective_expense)
                                    else:
                                        expenses_non_coll_all_runs.append(effective_expense)

                            # Compute statistics across all runs for this configuration
                            (
                                mean_waiting_time,
                                sd_waiting_time,
                            ) = mean_sd(waiting_times_all_runs)
                            (
                                mean_expense_coll,
                                sd_expense_coll,
                            ) = mean_sd(expenses_coll_all_runs)
                            (
                                mean_expense_non_coll,
                                sd_expense_non_coll,
                            ) = mean_sd(expenses_non_coll_all_runs)

                            # Write one CSV row for this configuration
                            writer.writerow([
                                bus_hop_time,                    # T_hop (ms)
                                initial_deposit_percentage,      # deposit as percentage of total wallet
                                collaboration_level_alpha,       # collaboration level of non-cooperative users
                                mean_waiting_time,
                                sd_waiting_time,
                                mean_expense_coll,
                                sd_expense_coll,
                                mean_expense_non_coll,
                                sd_expense_non_coll,
                                theoretical_deposit,
                                theoretical_deposit_percentage,
                            ])
                            f.flush()

    print(f"Final CSV written to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
