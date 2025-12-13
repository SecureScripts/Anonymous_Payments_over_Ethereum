"""
Average_wei_dollars_estimation.py

This script computes:
1. The average gas price in wei per gas unit in a given year, from export-AvgGasPrice.csv.
2. The average Ether price in USD in the same year, from export-EtherPrice.csv.
3. The corresponding average gas cost in USD per gas unit.
4. (Optional) The estimated USD cost of a transaction that consumes a given amount of gas
   (e.g., a confirm() transaction).

Both CSV files are expected to have the following structure:
- Column 0: date in the format MM/DD/YYYY
- Column 2: numerical value (wei per gas unit OR USD per ETH, depending on the file)
"""

import csv
from datetime import datetime

# Configuration
YEAR = 2024
AVG_GAS_FILE = "export-AvgGasPrice.csv"     # Contains average gas price in wei per gas unit
ETHER_PRICE_FILE = "export-EtherPrice.csv"  # Contains Ether price in USD
DATE_COLUMN_INDEX = 0
VALUE_COLUMN_INDEX = 2

# Optional: estimated gas used by a typical transaction, e.g., confirm()
GAS_PER_CONFIRM_TRANSACTION = 50056


def read_yearly_average_from_csv(filename, year, date_col=0, value_col=2):
    """
    Read a CSV file and compute the average of the values in 'value_col'
    for all rows whose date (in 'date_col') falls within the specified year.

    Parameters
    ----------
    filename : str
        Path to the input CSV file.
    year : int
        Target year (e.g., 2024).
    date_col : int
        Index of the date column (default: 0).
    value_col : int
        Index of the numeric value column (default: 2).

    Returns
    -------
    float or None
        The average of the selected values for the target year,
        or None if no valid data is found.
    """
    values = []

    with open(filename, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for row in reader:
            # Skip empty or too-short rows
            if not row or len(row) <= max(date_col, value_col):
                continue

            date_str = row[date_col].strip()
            value_str = row[value_col].strip()

            try:
                # Parse date in MM/DD/YYYY format
                date = datetime.strptime(date_str, "%m/%d/%Y")
            except ValueError:
                # Skip header rows or invalid date formats
                continue

            # Use only values from the target year
            if date.year == year:
                try:
                    value = float(value_str)
                    values.append(value)
                except ValueError:
                    # Skip rows with non-numeric values
                    continue

    if not values:
        return None

    return sum(values) / len(values)


def main():
    # 1. Average gas price in wei per gas unit (from export-AvgGasPrice.csv)
    avg_wei_per_gas = read_yearly_average_from_csv(
        AVG_GAS_FILE,
        YEAR,
        date_col=DATE_COLUMN_INDEX,
        value_col=VALUE_COLUMN_INDEX,
    )

    if avg_wei_per_gas is None:
        print(f"No valid gas price data found for year {YEAR} in '{AVG_GAS_FILE}'.")
        return

    print(f"Average gas price in {YEAR} (wei per gas unit): {avg_wei_per_gas:.2f}")

    # Convert from wei to Ether
    avg_ether_per_gas = avg_wei_per_gas / 10**18
    print(f"Average gas price in {YEAR} (ETH per gas unit): {avg_ether_per_gas:.10f}")

    # 2. Average Ether price in USD (from export-EtherPrice.csv)
    avg_ether_price_usd = read_yearly_average_from_csv(
        ETHER_PRICE_FILE,
        YEAR,
        date_col=DATE_COLUMN_INDEX,
        value_col=VALUE_COLUMN_INDEX,
    )

    if avg_ether_price_usd is None:
        print(f"No valid Ether price data found for year {YEAR} in '{ETHER_PRICE_FILE}'.")
        return

    print(f"Average Ether price in {YEAR} (USD per ETH): {avg_ether_price_usd:.2f}")

    # 3. Average gas cost in USD per gas unit
    avg_gas_cost_usd = avg_ether_per_gas * avg_ether_price_usd
    print(f"Average gas cost in {YEAR} (USD per gas unit): {avg_gas_cost_usd:.10f}")

    # 4. Optional: estimated cost of a confirm() transaction
    confirm_tx_cost_usd = GAS_PER_CONFIRM_TRANSACTION * avg_gas_cost_usd
    print(
        f"Estimated cost of a confirm() transaction "
        f"(~{GAS_PER_CONFIRM_TRANSACTION} gas): {confirm_tx_cost_usd:.2f} USD"
    )


if __name__ == "__main__":
    main()
