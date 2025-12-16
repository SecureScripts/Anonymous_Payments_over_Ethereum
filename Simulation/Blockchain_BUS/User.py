import random


class User:
    """
    Represents a single user in the simulation.

    Attributes
    ----------
    user_id : int or str
        Unique identifier of the user.
    wallet : float
        Initial wallet balance of the user.
    payments : list[tuple]
        List of future payment requests in the form:
        (scheduled_time, payment_amount, remainder).
    collaboration_level : float
        Probability in [0.0, 1.0] that the user will collaborate
        (i.e., correctly forward the bus / perform required actions)
        when they do NOT currently have a payment scheduled at this time.
    expenses : float
        Total amount spent by the user (e.g., fees, payments).
    refunded_deposit : float
        Total amount of deposit refunded to this user.
    current_pending_payment : tuple or None
        Payment tuple currently waiting to be executed, if any.
    score : int
        Trust score used by the incentive mechanism. Starts at -1
        and is decreased when the user does not collaborate.
    all_waiting_time : list[float]
        List of waiting times for each executed payment
        (execution_time - scheduled_time).
    final_mean_waiting_time : float
        Average waiting time computed at the end of the simulation.
    """

    def __init__(self, user_id, wallet, payments, collaboration_level=1.0):
        self.user_id = user_id
        self.wallet = wallet
        self.payments = payments
        self.expenses = 0.0
        self.all_waiting_time = []
        self.final_mean_waiting_time = 0.0
        self.collaboration_level = collaboration_level
        self.refunded_deposit = 0.0
        self.current_pending_payment = None
        self.score = -1

    def will_collaborate(self, current_time):
        """
        Decide whether the user collaborates at the current time step.

        If the user has at least one payment whose scheduled time
        is <= current_time, they are forced to collaborate (return True),
        since they need the protocol to progress for their own payment.

        Otherwise, they collaborate with probability equal to
        self.collaboration_level. If they do not collaborate,
        their score is decreased by 1.

        Parameters
        ----------
        current_time : float
            Current simulation time.

        Returns
        -------
        bool
            True if the user collaborates at this time step, False otherwise.
        """
        # If the next payment is due, the user collaborates for sure
        if len(self.payments) > 0 and self.payments[0][0] <= current_time:
            return True

        # Otherwise, collaboration is probabilistic
        will_collaborate = random.random() < self.collaboration_level
        if not will_collaborate:
            self.score -= 1
        return will_collaborate

    def will_pay(self, current_time, bus):
        """
        If the next scheduled payment time has been reached, insert the
        user's identifier into the bus and mark the payment as pending.

        Parameters
        ----------
        current_time : float
            Current simulation time.
        bus : list
            Data structure representing the bus; here we only append the
            user_id to indicate that this user has a payment to inject.

        Notes
        -----
        - If there are no remaining payments, nothing happens.
        - The method assumes that at most one payment can be pending
          at a time for this user (enforced via an assertion).
        """
        if len(self.payments) == 0:
            return

        # There must be no currently pending payment
        assert self.current_pending_payment is None

        time, payment = self.payments[0]
        if time <= current_time:
            # Mark payment as pending and signal on the bus
            self.current_pending_payment = (time, payment)
            bus.append(self.user_id)
        return

    def pay(self, current_time):
        """
        Finalize the current pending payment.

        This method:
        - Removes the first scheduled payment from the queue.
        - Computes and stores the waiting time
          (current_time - scheduled_time).
        - Deducts the payment amount from the user's wallet.
        - Clears the current_pending_payment attribute.

        Parameters
        ----------
        current_time : float
            Current simulation time (time of payment execution).
        """
        assert len(self.payments) > 0
        assert self.current_pending_payment is not None

        # Remove the executed payment from the queue
        self.payments.pop(0)

        scheduled_time, amount = self.current_pending_payment

        # Store waiting time for this payment
        self.all_waiting_time.append(current_time - scheduled_time)

        # Update wallet after payment
        self.wallet -= amount
        # Optionally enforce non-negative wallet if required by the model:
        # assert self.wallet >= 0

        # Clear pending payment
        self.current_pending_payment = None

    def compute_mean_waiting_time(self):
        """
        Compute the mean waiting time over all executed payments.

        Returns
        -------
        float
            The average waiting time. Returns 0.0 if the user has no
            recorded payments.
        """
        if not self.all_waiting_time:
            self.final_mean_waiting_time = 0.0
        else:
            self.final_mean_waiting_time = (
                sum(self.all_waiting_time) / len(self.all_waiting_time)
            )
        return self.final_mean_waiting_time
