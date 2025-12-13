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

## Overview

The protocol ensures that a payer remains indistinguishable among at least **k** honest users, even against an adversary capable of monitoring all on-chain and off-chain traffic. Users are grouped into cyclic structures called **rings**, within which they exchange **zero-fee cover transactions** carrying a layered-encrypted bus.

### Core Concepts

- **Ring overlay:** Users are partitioned into groups of size *(k + α)*, forming anonymity sets.
- **Cover transactions:** Zero-fee Ethereum transactions carrying an encrypted bus; indistinguishable from one another.
- **Layered encryption:** Each hop adds an encryption layer, making all bus seats indistinguishable.
- **Surrogate keys:** Pseudonymous public keys used to sign anonymous payment requests.
- **Exit user:** Decrypts the bus and submits collected payment requests to the smart contract.
- **t-confirmation mechanism:** Prevents unauthorized payments by requiring approval from multiple ring members.
- **Refundable deposit with trust-weighted rewards:** Encourages cooperation and discourages free-riding.

---

## Protocol Summary

### 1. Ring Formation
Users join the root contract. Once **N = β · (k + α)** users have joined, they are shuffled into β rings using a future block hash, ensuring unpredictability and resistance to manipulation.

### 2. Surrogate Key Exchange
Each participant submits a surrogate public key through an encrypted bus. The exit user eventually broadcasts the full list of surrogate keys, without revealing the mapping to Ethereum addresses.

### 3. Bus Circulation and Cover Traffic
A bus with *(k + α)* seats circulates through ring members. Each hop:
- decrypts one layer  
- optionally inserts a new encrypted payment tuple into its seat  
- re-encrypts the entire bus  

Continuous cover traffic makes all users indistinguishable.

### 4. Anonymous Payment Submission
To issue a payment, a user inserts into their seat:

```
⟨ServiceProvider, Amount, Signature_with_surrogate_key⟩
```

This tuple is encrypted in multiple layers and cannot be linked to the user's position.

### 5. Payment Execution
The exit user:
1. Decrypts all seats  
2. Calls `startConfirm()` with the collected payment requests  
3. Users call `confirm()`  
4. Exit user calls `pay()`, executing payments that reached **t** confirmations  
5. At epoch boundaries, `depositBack()` distributes trust-weighted refunds  

---

## Features

- k-anonymity against global network observers  
- No direct communication among users  
- Ethereum-compatible implementation  
- Incentive-compatible through refundable deposits  
- Extensive simulation engine  
- Realistic execution-based gas-cost profiling  
- Reproduction of all experimental results from the paper  

---

## Repository Structure

(To be completed once code structure is provided.)

```
/src/                     # Simulator implementation
/contracts/               # Solidity smart contracts
/experiments/             # Experiment scripts
/notebooks/               # Analysis and plotting
/data/                    # Preprocessed datasets or download utilities
README.md
```

---

## Installation

(To be updated once dependencies are provided.)

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

(To be completed when script names are provided.)

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
