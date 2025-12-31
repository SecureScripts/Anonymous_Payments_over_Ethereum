// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract RingSmartContract {
    address public owner;
    uint256 public t; // Threshold for tuples
    uint256 public totalAmount; // Total amount for payments
    uint256 public totalDeposit; // Total deposit for score-based distribution
    address[] public ringUsers; // Users in the ring
  
    // Struct to store tuple data
    struct Tuple {
        address[] SP; // Service Provider addresses
        uint256[] A;  // Amounts to transfer
        bool F;     // Flag for end of epoch
        uint256[] deposits; // Deposits
    }
    Tuple public currentTuple; // Tuple for the current confirmation phase
    uint256 public confirmations; // Number of confirmations received in the current phase


    // Modifier to restrict function access
    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

     mapping(address => bool) public isRingUser; // Mapping to check if an address is a ring user
     mapping(address => bool) public hasConfirmed; // Tracks if a user has confirmed in the current phase


    // Modifier to check if the contract has enough funds
    modifier hasEnoughFunds(uint256 amount, uint256 deposit) {
        require(totalAmount >= amount, "Insufficient total amount");
        require(totalDeposit >= deposit, "Insufficient total deposit");
        _;
    }


constructor(
    uint256 _t,
    uint256 _totalAmount,
    uint256 _totalDeposit,
    address[] memory _ringUsers
) payable {
    require(msg.value == (_totalAmount + _totalDeposit), "Mismatch between sent funds and initial setup");
    require(_totalAmount > 0 && _totalDeposit > 0, "Initial funds must be positive");
    require(_ringUsers.length > 0, "At least one user required in the ring");

    owner = msg.sender;
    t = _t;
    totalAmount = _totalAmount;
    totalDeposit = _totalDeposit;

    //Inizialization of users in the ring
    for (uint256 i = 0; i < _ringUsers.length; i++) {
        address user = _ringUsers[i];
        require(user != address(0), "Invalid user address");
        isRingUser[user] = true;
        ringUsers.push(user);
    }
}

// Modifier to check that a function is called by ring users
modifier onlyRingUser() {
    require(isRingUser[msg.sender], "Caller is not an authorized ring user");
    _;
}


function startConfirm(
        address[] memory SP,
        uint256[] memory A,
        bool F,
        uint256[] memory D
    ) public onlyRingUser {
        currentTuple = Tuple(SP, A, F, D);
        confirmations = 0;
    }


    function confirm() public onlyRingUser {
        require(!hasConfirmed[msg.sender], "User has already confirmed");
        hasConfirmed[msg.sender] = true;
        confirmations++;
    }
    function pay() public onlyRingUser {
        require(confirmations >= t, "Not enough confirmations");

        // Execute payments
        for (uint256 i = 0; i < currentTuple.SP.length; i++) {
            uint256 amount = currentTuple.A[i];
            address serviceProvider = currentTuple.SP[i];
            totalAmount -= amount;
            payable(serviceProvider).transfer(amount);
        }

        // If F is true, call depositBack
        if (currentTuple.F) {
            depositBack(currentTuple.deposits);
        }
        // Reset confirmation phase for the next epoch
        delete currentTuple;
        confirmations = 0;

        // Reset confirmations for all users
        for (uint256 i = 0; i < ringUsers.length; i++) {
            hasConfirmed[ringUsers[i]] = false;
        }
     
    }

    
      function depositBack(uint256[] memory D) internal {
        for (uint256 i = 0; i < D.length; i++) {
            uint256 depositAmount = D[i];
            address user = ringUsers[i];
            totalDeposit -= depositAmount;
            payable(user).transfer(depositAmount);
        }
    }

    // Function to check balances
    function checkBalances() public view returns (uint256, uint256) {
        return (totalAmount, totalDeposit);
    }


    function setConfirm() public onlyOwner {
        for (uint256 i = 0; i < ringUsers.length; i++) {
            hasConfirmed[ringUsers[i]] = true;
        }
        confirmations=ringUsers.length;
    }

}
