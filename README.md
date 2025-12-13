# Anonymous_Payments_over_Ethereum

This repository contains the full implementation and experimental framework used in the paper:

**F. Buccafurri, V. De Angelis, S. Lazzaro**  
*Network-Layer Anonymous Payments over Ethereum via Cover Transactions*, TO APPEAR, 2025.  
:contentReference[oaicite:0]{index=0}

The project introduces the first payment protocol that achieves network-layer payer anonymity against a global passive traffic observer, while remaining compatible with Ethereum and economically viable under realistic conditions.

This repository allows you to:
- Reproduce all experiments and figures from the paper  
- Deploy and test the smart contracts implementing ring-based anonymous payments  
- Explore the effect of cooperation levels, bus frequencies, gas costs, and deposit configurations  
- Study the incentive model and cost–latency trade-offs  

---

## Repository Structure

(To be completed)

## Repository Structure

```
Simulation/
└── Blockchain_BUS/
    ├── User.py                    # Simulation of a single user
    ├── BlockchainRing.py          # Simulation of the full lifecycle of a user ring
    ├── SuperMain.py               # Entry point to run the complete simulation campaign
    └── simulation_results.csv     # Output data produced by the simulator

Price_Estimate/
└── Average_wei_dollars_estimation.py   # Script to compute the 2024 average gas cost in wei and USD

Data_for_simulation/
└── Data_for_simulation/
    ├── Extract_Blockchain_Operation_Cost/
    │   ├── GanacheSimulationCosts.py   # Runs Ganache-based profiling of smart contract operations
    │   └── FINAL_RES.csv               # Extracted blockchain cost results
    │
    └── Extract_User_Payments_Data/     # (To be completed / adjusted)

Final_Plots/
├── Extract_Plots.py                    # Generates the figures used in the paper
└── (plots saved here)                  # All final plots produced from simulation_results.csv
```


---

## Installation

(To be updated)

```bash
git clone https://github.com/<username>/Anonymous_Payments_over_Ethereum.git
cd Anonymous_Payments_over_Ethereum
pip install -r requirements.txt
```

Smart-contract deployment requires:
- Node.js  
- Hardhat or Foundry  
- Ganache for local testing  
- Python ≥ 3.10  

---

## Usage

(To be completed)

Example:

```bash
python run_simulation.py --config configs/exp1.json
```

---

## Citation

If you use this repository in academic work, please cite:

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

Pull requests, suggestions, and reports are welcome.

## Contact

For inquiries related to the paper or the implementation, please contact the authors.
