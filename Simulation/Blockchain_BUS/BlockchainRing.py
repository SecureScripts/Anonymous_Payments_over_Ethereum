from User import User


class BlockchainRing:
    """
    Simulates a blockchain-based payment ring.

    Each ring contains a set of users that:
    - periodically receive a circulating "bus" where they may inject payment requests,
    - pay a confirmation cost when they collaborate,
    - are rewarded or penalized via a refundable deposit mechanism at epoch boundaries.

    This class coordinates:
    - bus rotations,
    - payment execution at the exit node,
    - confirmation rounds,
    - epoch transitions and deposit redistribution.
    """

    def __init__(
        self,
        users,
        confirm_cost_dollars,
        gas_in_dollars,
        result_end_epoch,
        result_no_end_epoch,
        bus_hop_time,
        first_ts_global,
        epoch_num,
        delta_D,
        total_wallet,
        initial_deposit,
    ):
        """
        Initialize the ring simulation.

        Parameters
        ----------
        users : list[User]
            Fully initialized list of User objects participating in the ring.
        confirm_cost_dollars : float
            Cost (in USD) of a single confirm() call for each user.
        gas_in_dollars : float
            Cost (in USD) of one gas unit (used to convert gas to USD).
        result_end_epoch : dict[int, dict]
            Gas cost profile for pay() and startConfirm() at the end of an epoch.
            Indexed by the number of payments in the round.
        result_no_end_epoch : dict[int, dict]
            Gas cost profile for pay() and startConfirm() in non-final rounds.
            Indexed by the number of payments in the round.
        bus_hop_time : float
            Time needed for the bus to move from one user to the next.
        first_ts_global : float
            Initial global timestamp for the simulation.
        epoch_num : int
            Total number of epochs in the ring lifetime.
        delta_D : float
            Amount of deposit that should be redistributed at the end of each epoch.
        total_wallet : float
            Total initial wallet value of all users in the ring.
        initial_deposit : float
            Initial deposit (in USD) associated with the ring.
        """
        self.users = users
        self.bus = []  # list of user IDs indicating which users have pending payments in the current round
        self.current_time = first_ts_global
        self.initial_time = first_ts_global

        self.exit_node_index = 0  # index of the current exit node in self.users

        self.confirm_cost_dollars = confirm_cost_dollars
        self.gas_in_dollars = gas_in_dollars
        self.result_end_epoch = result_end_epoch
        self.result_no_end_epoch = result_no_end_epoch
        self.bus_hop_time = bus_hop_time

        self.delta_D = delta_D
        self.total_wallet = total_wallet
        self.epoch_num = epoch_num
        self.current_epoch_num = 1
        self.deposit = initial_deposit
        self.end_epoch = False

    def set_user_payments(self, user_id, payments):
        """
        Set the payment schedule for a specific user.

        Parameters
        ----------
        user_id : int
            Index of the user in the ring.
        payments : list[tuple]
            List of (time, amount, remainder) for the user's payments.
        """
        self.users[user_id].payments = payments

    def simulate_round(self):
        """
        Simulate one or more full rotations of the bus until at least one payment is executed.

        The method:
        - starts at the current exit node,
        - iterates over users in ring order,
        - moves the bus hop by hop,
        - handles non-collaborating users (which delay the bus),
        - when the bus returns to the exit node with at least one payment,
          it triggers payment handling and moves the exit node to the next user.
        """
        self.bus = []

        current_user_index = self.exit_node_index
        current_user = self.users[current_user_index]

        while True:
            # If the bus returns to the exit node and contains at least one payment,
            # handle the payments and move the exit node.
            if current_user_index == self.exit_node_index and len(self.bus) > 0:
                self.handle_payments()
                # Shift the exit node for the next invocation
                self.exit_node_index = (self.exit_node_index + 1) % len(self.users)
                break

            # User does not collaborate
            if not current_user.will_collaborate(self.current_time):
                # A non-collaborating user effectively delays the bus.
                self.current_time += self.bus_hop_time * 2

                # If the exit node itself does not collaborate when the bus is empty,
                # shift the exit node.
                if current_user_index == self.exit_node_index and len(self.bus) == 0:
                    self.exit_node_index = (self.exit_node_index + 1) % len(self.users)
            else:
                # User collaborates and may inject a payment into the bus
                current_user.will_pay(self.current_time, self.bus)
                self.current_time += self.bus_hop_time

            # Move to the next user in the ring
            current_user_index = (current_user_index + 1) % len(self.users)
            current_user = self.users[current_user_index]

    def handle_payments(self):
        """
        Handle all payment requests currently stored in the bus when it reaches the exit node.

        This includes:
        - charging the exit node for startConfirm() and pay() costs (in USD),
        - executing all payments for the users whose IDs are in the bus,
        - clearing the bus,
        - running a confirmation round where each collaborating user pays the confirm() cost.
        """
        current_exit = self.users[self.exit_node_index]

        # Compute gas-based costs for startConfirm() and pay() depending on whether
        # this round ends an epoch or not.
        num_payments = len(self.bus)
        if self.end_epoch:
            start_confirm_gas = self.result_end_epoch[num_payments]["StartConfirmGas"]
            pay_gas = self.result_end_epoch[num_payments]["PayGas"]
        else:
            start_confirm_gas = self.result_no_end_epoch[num_payments]["StartConfirmGas"]
            pay_gas = self.result_no_end_epoch[num_payments]["PayGas"]

        start_confirm_cost = start_confirm_gas * self.gas_in_dollars
        pay_cost = pay_gas * self.gas_in_dollars

        # Exit node pays these two costs
        current_exit.expenses += start_confirm_cost + pay_cost

        # Execute all payments for users whose IDs are present in the bus
        for user_id in self.bus:
            self.users[user_id].pay(self.current_time)

        # Clear the bus after handling payments
        self.bus = []

        # Perform the confirmation round
        self.handle_confirmation_round()

    def handle_confirmation_round(self):
        """
        Handle the confirmation round.

        Each user that decides to collaborate at the current time pays
        the confirmation cost (e.g., cost of a confirm() transaction).
        """
        for user in self.users:
            if user.will_collaborate(self.current_time):
                user.expenses += self.confirm_cost_dollars

    def handle_epoch_end(self):
        """
        Handle the end of an epoch.

        This includes:
        - computing the total "collaboration weight" from user scores,
        - redistributing the per-epoch refundable deposit portion (delta_D)
          proportionally to collaboration,
        - resetting user scores,
        - updating the remaining ring deposit.
        """
        refund = max(0, self.delta_D)

        # Collaboration weight: users with a less negative score (closer to -1)
        # are considered more collaborative, so -1/score is larger.
        total_collaboration = sum((-1 / user.score) for user in self.users)

        if total_collaboration > 0:
            for user in self.users:
                weight = (-1 / user.score) / total_collaboration
                user.refunded_deposit += refund * weight
                # Reset score at the end of each epoch
                user.score = -1

        # Update remaining deposit after distributing refund for this epoch
        self.deposit = self.deposit - self.delta_D

    def run_simulation(self):
        """
        Run the ring simulation until all users have exhausted their payment schedules.

        The loop continues as long as at least one user still has scheduled payments.
        In each iteration:

        - The global wallet level is checked against the epoch progression:
            if total_current_wallet < total_wallet * (1 - current_epoch_num / epoch_num),
            then the next round is considered an end-of-epoch round.
        - One simulation round is executed.
        - If an epoch ends, deposits are redistributed and the epoch counter is incremented.

        At the very end, a final epoch end is handled and the remaining deposit
        is asserted to be (almost) zero.
        """
        while any(len(user.payments) > 0 for user in self.users):
            total_current_wallet = sum(user.wallet for user in self.users)

            # Epoch ends when the total remaining wallet is below a threshold
            if total_current_wallet < self.total_wallet * (1 - (self.current_epoch_num / self.epoch_num)):
                self.end_epoch = True

            # Simulate one round (or multiple rotations until a payment occurs)
            self.simulate_round()

            # If an epoch ended, redistribute deposit and move to the next epoch
            if self.end_epoch:
                self.handle_epoch_end()
                self.current_epoch_num += 1
                self.end_epoch = False

        # After all payments are completed, perform a final epoch-end redistribution
        self.end_epoch = True
        self.handle_epoch_end()
        self.current_epoch_num += 1
        self.end_epoch = False

        # At the end of the ring lifetime, the remaining deposit should be negligible
        assert self.deposit < 0.001
