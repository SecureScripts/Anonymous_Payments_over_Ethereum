"""
GanacheSimulationCosts.py

This script performs an execution-based gas-cost profiling of the ring smart contract
used in the paper "Network-Layer Anonymous Payments over Ethereum via Cover Transactions".

It deploys the contract (and an auxiliary version), then repeatedly executes:
 - startConfirm()
 - confirm()
 - setConfirm()
 - pay()

across multiple scenarios, varying:
 - k (number of cooperative users)
 - alpha (number of additional users)
 - Npayment (number of payments inside a simulated bus round)

For each operation, the script extracts the gas consumption measured on a local Ganache
instance and saves the results in a CSV file named 'res'.

The resulting CSV is later used in the simulation engine to approximate realistic on-chain
execution costs.
"""

import csv
import sys
import statistics
from web3 import Web3
import Parameters


# -------------------------------------------------------------------------------------
#  Basic Web3 setup
# -------------------------------------------------------------------------------------

ganache_url = Parameters.ganache_url
web3 = Web3(Web3.HTTPProvider(ganache_url, {"timeout": 600}))

accounts = web3.eth.accounts
contract_abi = Parameters.contract_abi
contract_bytecode = Parameters.contract_bytecode

# Output CSV file
csvfile = open('res', 'w+', newline='')
writer = csv.writer(csvfile, delimiter=';')
writer.writerow([
    "k", "alpha", "nPayments", "EndEpoch", "DeployGas",
    "StartConfirmGas", "MaxConfirmGas", "MinConfirmGas", "PayGas"
])
csvfile.flush()


# -------------------------------------------------------------------------------------
#  Smart Contract Interaction Helpers
# -------------------------------------------------------------------------------------

def deploySC(Contract, t, ring_users, owner, total_amount, total_deposit):
    """
    Deploys a contract and returns:
      - the gas used for deployment
      - the deployed contract address
    """
    tx = {
        'from': owner,
        'value': web3.to_wei(total_amount + total_deposit, 'wei'),
        'gas': 10_000_000,
        'gasPrice': web3.to_wei('20', 'gwei'),
    }

    tx_hash = Contract.constructor(
        _t=t,
        _totalAmount=total_amount,
        _totalDeposit=total_deposit,
        _ringUsers=ring_users
    ).transact(tx)

    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.gasUsed, receipt.contractAddress


def startConfirm(deployed_contract, exit_user, SP, A, F, D):
    """
    Calls the startConfirm() function of the contract.
    """
    tx = {
        'from': exit_user,
        'gas': 10_000_000,
        'gasPrice': web3.to_wei('20', 'gwei'),
    }

    tx_hash = deployed_contract.functions.startConfirm(SP, A, F, D).transact(tx)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.gasUsed


def confirm(deployed_contract, address):
    """
    Calls confirm() on behalf of a ring user.
    """
    tx = {
        'from': address,
        'gas': 10_000_000,
        'gasPrice': web3.to_wei('20', 'gwei'),
    }

    tx_hash = deployed_contract.functions.confirm().transact(tx)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.gasUsed


def pay(deployed_contract, exit_user):
    """
    Calls pay() from the exit user.
    """
    tx = {
        'from': exit_user,
        'gas': 10_000_000,
        'gasPrice': web3.to_wei('20', 'gwei'),
    }

    tx_hash = deployed_contract.functions.pay().transact(tx)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.gasUsed


def setConfirm(deployed_contract, owner):
    """
    Calls the auxiliary function setConfirm() (used only in the simulation environment).
    """
    tx = {
        'from': owner,
        'gas': 10_000_000,
        'gasPrice': web3.to_wei('20', 'gwei'),
    }

    tx_hash = deployed_contract.functions.setConfirm().transact(tx)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.gasUsed


# -------------------------------------------------------------------------------------
#  Main Experiment Loop
# -------------------------------------------------------------------------------------

for k in range(100, 101, 10):  # Here only k=100 is executed
    if k == 100:
        alpha_values = [int(0.3 * k)]
    else:
        alpha_values = [int(0.1 * k), int(0.2 * k), int(0.3 * k)]

    for alpha in alpha_values:

        # -------------------------------------------------------------------------
        # Contract deployment
        # -------------------------------------------------------------------------
        Contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
        t = 2  # threshold for confirm()

        ring_users = [web3.to_checksum_address(addr) for addr in accounts[: (k + alpha)]]

        total_amount = int(Parameters.total_amount_per_user * (k + alpha))
        total_deposit = int(Parameters.total_deposit_per_user * (k + alpha))

        deployGas, contract_address = deploySC(
            Contract=Contract,
            t=t,
            ring_users=ring_users,
            owner=accounts[-1],
            total_amount=total_amount,
            total_deposit=total_deposit
        )

        # Deploy auxiliary version
        ContractAux = web3.eth.contract(abi=Parameters.abi_aux, bytecode=Parameters.bytecode_aux)
        deployGasAux, contract_addressAux = deploySC(
            Contract=ContractAux,
            t=t,
            ring_users=ring_users,
            owner=accounts[-1],
            total_amount=total_amount,
            total_deposit=total_deposit
        )

        print("Contract deployed. Gas used:", deployGas)
        print("------------------------------------------------------------")

        # -------------------------------------------------------------------------
        # Gas-cost evaluation for increasing number of payments
        # -------------------------------------------------------------------------
        for Npayment in range(1, k + alpha + 1):

            while True:
                try:
                    print(f"Simulation: k={k}, alpha={alpha}, Npayment={Npayment}")

                    contract = web3.eth.contract(address=contract_addressAux, abi=Parameters.abi_aux)

                    # -----------------------------------------------------------------
                    # Initialization round (no end epoch)
                    # -----------------------------------------------------------------
                    F = False
                    SP = [web3.to_checksum_address(addr)
                          for addr in accounts[(k + alpha):(k + alpha + Npayment)]]
                    A = [Parameters.payment_per_user for _ in range(Npayment)]
                    D = []

                    # Run the round
                    startConfirm(contract, accounts[0], SP, A, F, D)
                    for user in range(t):
                        confirm(contract, accounts[user])
                    setConfirm(contract, owner=accounts[-1])
                    pay(contract, exit_user=accounts[0])

                    # -----------------------------------------------------------------
                    # Initialization round (end of epoch)
                    # -----------------------------------------------------------------
                    F = True
                    D = [Parameters.deposit_back_per_user for _ in range(k + alpha)]

                    startConfirm(contract, accounts[0], SP, A, F, D)
                    for user in range(t):
                        confirm(contract, accounts[user])
                    setConfirm(contract, owner=accounts[-1])
                    pay(contract, exit_user=accounts[0])

                    # -----------------------------------------------------------------
                    # Actual round (no end epoch)
                    # -----------------------------------------------------------------
                    F = False
                    D = []

                    gasStartConfirm = startConfirm(contract, accounts[0], SP, A, F, D)

                    confirmGas = []
                    for user in range(t):
                        confirmGas.append(confirm(contract, accounts[user]))

                    setConfirm(contract, owner=accounts[-1])
                    payGas = pay(contract, exit_user=accounts[0])

                    print("=== No End Epoch ===")
                    print("StartConfirm gas:", gasStartConfirm)
                    print("Confirm gas (list):", confirmGas)
                    print("Confirm mean:", statistics.mean(confirmGas))
                    print("Confirm std:", statistics.stdev(confirmGas))
                    print("Pay gas:", payGas)

                    writer.writerow([
                        k, alpha, Npayment, "No", deployGas,
                        gasStartConfirm, max(confirmGas), min(confirmGas), payGas
                    ])

                    # -----------------------------------------------------------------
                    # Actual round (end epoch)
                    # -----------------------------------------------------------------
                    F = True
                    D = [Parameters.deposit_back_per_user for _ in range(k + alpha)]

                    gasStartConfirm = startConfirm(contract, accounts[0], SP, A, F, D)

                    confirmGas = []
                    for user in range(t):
                        confirmGas.append(confirm(contract, accounts[user]))

                    setConfirm(contract, owner=accounts[-1])
                    payGas = pay(contract, exit_user=accounts[0])

                    print("=== End Epoch ===")
                    print("StartConfirm gas:", gasStartConfirm)
                    print("Confirm gas (list):", confirmGas)
                    print("Confirm mean:", statistics.mean(confirmGas))
                    print("Confirm std:", statistics.stdev(confirmGas))
                    print("Pay gas:", payGas)

                    writer.writerow([
                        k, alpha, Npayment, "Yes", deployGas,
                        gasStartConfirm, max(confirmGas), min(confirmGas), payGas
                    ])

                    csvfile.flush()
                    print("============================================================")
                    break

                except Exception as e:
                    # Retry in case of temporary Ganache or RPC issues
                    print("Exception occurred:", e)
                    print("Retrying...")
