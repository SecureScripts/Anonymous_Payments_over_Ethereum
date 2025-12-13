# Anonymous_Payments_over_Ethereum

This repository contains the full implementation and experimental framework used in the paper:

**F. Buccafurri, V. De Angelis, S. Lazzaro**  
*Network-Layer Anonymous Payments over Ethereum via Cover Transactions*, TO APPEAR, 2025.

The repository provides:
- A simulator implementing the anonymous payment protocol described in the paper  
- Execution-based smart contract gas-cost profiling using Ganache  
- Preprocessing tools for user payment datasets  
- Automated simulation campaigns  
- Plot generation scripts that reproduce all figures in the publication  

---

## Repository Structure

```
Simulation/
└── Blockchain_BUS/
    ├── User.py                          # User model used in the simulator
    ├── BlockchainRing.py                # Full simulation of a ring lifecycle
    ├── SuperMain.py                     # Main simulation campaign (run this to reproduce experiments)
    └── simulation_results.csv           # Output generated after simulations (auto-created)

Price_Estimate/
├── Average_wei_dollars_estimation.py    # Computes 2024 average gas and Ether price → USD/gas conversion
├── export-AvgGasPrice.csv               # Avg gas price (wei per gas unit)
└── export-EtherPrice.csv                # Avg Ether price (USD per ETH)

Data_for_simulation/
└── Data_for_simulation/
    ├── Extract_Blockchain_Operation_Cost/
    │   ├── GanacheSimulationCosts.py    # Measures gas costs of startConfirm(), confirm(), pay(), setConfirm()
    │   └── FINAL_RES.csv                # Output of measured gas costs (used by the simulator)
    │
    └── Extract_User_Payments_Data/
        └── TODO: Add dataset-processing script name here

Final_Plots/
├── Extract_Plots.py                     # Generates the plots presented in the paper
└── (plots saved here)                   # Output directory for figures
```

---

## Requirements

- Python **3.10+**
- Ganache (CLI or GUI)
- Node.js (optional, only if installing Ganache CLI)
- Python packages (installed via `requirements.txt`):
  - `web3`
  - `pandas`
  - `matplotlib`
  - `numpy`

---

## Installation

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate.bat     # Windows

pip install -r requirements.txt  # Install dependencies
```

Ensure Ganache is running and its RPC URL matches the one defined in `Parameters.py`.

---

## Usage

The complete workflow consists of three stages:

1. Pre-compute required CSV input files  
2. Run the main simulation  
3. Generate the plots used in the paper  

### 1. Pre-compute Input Data

#### 1.1 Average gas & Ether prices (Price_Estimate)

```bash
cd Price_Estimate
python Average_wei_dollars_estimation.py
```

This script reads:
- `export-AvgGasPrice.csv`
- `export-EtherPrice.csv`

and computes the average USD cost per gas unit.

#### 1.2 Smart contract gas-cost profiling (Ganache)

```bash
cd Data_for_simulation/Extract_Blockchain_Operation_Cost
python GanacheSimulationCosts.py
```

Output:
```
FINAL_RES.csv
```

This file is used by the simulator to model realistic blockchain execution costs.

#### 1.3 Payment dataset preprocessing

```bash
cd Data_for_simulation/Extract_User_Payments_Data
python <TODO: dataset_processing_script>.py
```

This step must generate a file similar to:

```
Data_for_simulation/UserPayments/output_selection_2020/filtered_dataset.csv
```

which is consumed by `SuperMain.py`.

---

### 2. Run the Main Simulation

This is the core experiment campaign.

```bash
cd Simulation/Blockchain_BUS
python SuperMain.py
```

Output:
```
simulation_results.csv
```

This file contains:
- Mean waiting times
- Expenses of cooperative users
- Expenses of non-cooperative users
- Theoretical deposit values
- All aggregated statistics for plotting

---

### 3. Generate Final Plots

```bash
cd Final_Plots
python Extract_Plots.py
```

This script reads `simulation_results.csv` and produces all figures in the paper.

Plots are saved in:

```
Final_Plots/
```

---

## Quick Start

```bash
# 1) Compute USD/gas conversion
cd Price_Estimate
python Average_wei_dollars_estimation.py

# 2) Compute smart contract gas costs (requires Ganache)
cd ../Data_for_simulation/Extract_Blockchain_Operation_Cost
python GanacheSimulationCosts.py

# 3) Prepare payment dataset
cd ../Extract_User_Payments_Data
python <TODO: dataset_processing_script>.py

# 4) Run full simulation
cd ../../Simulation/Blockchain_BUS
python SuperMain.py

# 5) Generate final plots
cd ../../Final_Plots
python Extract_Plots.py
```

---

## Citation

```
@article{anonymous_payments_bus_2025,
  title={Network-Layer Anonymous Payments over Ethereum via Cover Transactions},
  author={Buccafurri, Francesco and De Angelis, Vincenzo and Lazzaro, Sara},
  journal={TO APPEAR},
  year={2025}
}
```

---

## Contributing

Pull requests, suggestions, and bug reports are welcome.

---

## Contact

For questions regarding the paper or implementation, please contact the authors.
