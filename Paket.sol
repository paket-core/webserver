pragma solidity ^0.4.13;
// ---------------------------------------------------------------------
// PaKeT experiment
// ---------------------------------------------------------------------

import 'https://github.com/OpenZeppelin/zeppelin-solidity/contracts/token/MintableToken.sol';

contract Bul is MintableToken {
    string public name = "Bul";
    string public symbol = "BUL";
    uint256 public decimals = 18;
    address public owner = msg.sender;

    function Bul() public {
        totalSupply = 10 ** 6 * 10 ** decimals;
        balances[msg.sender] = totalSupply;
    }

    struct Paket {
        address recipient;
        uint256 deadline;
        uint256 offeredPayment;
        uint256 requiredCollateral;

        // Balances in case of success and failure, indexed by payment and collateral.
        mapping (address => uint256) successBalances;
        address[] paymentBenificieries;
        address[] collateralRefundees;
        mapping (address => uint256) failBalances;
        address[] collateralBenificieries;
        address[] paymentRefundees;
    }

    Paket[] private pakets;

    // Create a new "empty" paket.
    function create(
        address _recipient, uint256 _deadline, uint256 _offeredPayment, uint256 _requiredCollateral
    ) public returns (uint256) {
        require(_deadline > now);
        // push returns the new length of the array, so we subtract 1 to get the new index.
        // Also note the new emptyt arrays created for the new paket struct.
        return pakets.push(Paket(
            _recipient, _deadline, _offeredPayment, _requiredCollateral,
            new address[](0), new address[](0), new address[](0), new address[](0)
        )) - 1;
    }

    // Modifier to functions that commit BULs.
    modifier commitBuls(uint256 _amount) {
        require(balanceOf(msg.sender) >= _amount);
        balances[msg.sender] -= _amount;
        _;
    }

    // Modifier to functions that need to add balances from outside.
    modifier managePaketBalances(uint256 _paketIdx, address _successAddress, address _failAddress, uint256 _amount) {
        pakets[_paketIdx].successBalances[_successAddress] += _amount;
        pakets[_paketIdx].failBalances[_failAddress] += _amount;
        _;
    }

    // Add payment to a paket.
    function commitPayment (uint256 _paketIdx, address _payee, uint256 _amount) public
        commitBuls(_amount) managePaketBalances(_paketIdx, _payee, msg.sender, _amount)
    {
        pakets[_paketIdx].paymentBenificieries.push(_payee);
        pakets[_paketIdx].paymentRefundees.push(msg.sender);
    }

    // Add collateral to a paket.
    function commitCollateral(uint256 _paketIdx, address _payee, uint256 _amount) public
        commitBuls(_amount) managePaketBalances(_paketIdx, msg.sender, _payee, _amount)
    {
        pakets[_paketIdx].collateralBenificieries.push(_payee);
        pakets[_paketIdx].collateralRefundees.push(msg.sender);
    }

    // Promise some of the payment previously promised to you to another.
    function relayPayment(uint256 _paketIdx, address _payee, uint256 _amount) public {
        require(pakets[_paketIdx].successBalances[msg.sender] >= _amount);
        pakets[_paketIdx].successBalances[msg.sender] -= _amount;
        pakets[_paketIdx].successBalances[_payee] += _amount;
        pakets[_paketIdx].paymentBenificieries.push(msg.sender);
    }

    // Cover someone else's collateral (so he gets his BULs back).
    // _amount must be equal or less than what he committed.
    // For increasing collateral use commitCollateral.
    function coverCollateral(uint256 _paketIdx, address _payee, uint256 _amount) public commitBuls(_amount) {
        require(pakets[_paketIdx].successBalances[_payee] >= _amount);
        pakets[_paketIdx].successBalances[_payee] -= _amount;
        pakets[_paketIdx].successBalances[msg.sender] += _amount;
        pakets[_paketIdx].collateralRefundees.push(msg.sender);
        balances[_payee] += _amount;
    }

    // Check my balance in case of success and failure;
    function paketSelfInterest(uint256 _paketIdx) public view returns (uint256, uint256) {
        return (pakets[_paketIdx].successBalances[msg.sender], pakets[_paketIdx].failBalances[msg.sender]);
    }

// Why can't we use this helper function?
//    function _settle(address[] _benificiaries, mapping (address => uint256) _payments) private {
//        for (uint256 idx = 0; idx < _benificiaries.length; idx++) {
//            balances[_benificiaries[idx]] += _payments[_benificiaries[idx]];
//            _payments[_benificiaries[idx]] = 0;
//        }
//    }

    // Refund all payments and forward all collaterals if the deadline has passed.
    function refund(uint256 _paketIdx) public {
        require(pakets[_paketIdx].deadline < now);
        uint256 idx;
        address payee;
        for (idx = 0; idx < pakets[_paketIdx].paymentRefundees.length; idx++) {
            payee = pakets[_paketIdx].paymentRefundees[idx];
            balances[payee] += pakets[_paketIdx].failBalances[payee];
            pakets[_paketIdx].failBalances[payee] = 0;
        }
        for (idx = 0; idx < pakets[_paketIdx].collateralBenificieries.length; idx++) {
            payee = pakets[_paketIdx].collateralBenificieries[idx];
            balances[payee] += pakets[_paketIdx].failBalances[payee];
            pakets[_paketIdx].failBalances[payee] = 0;
        }
        delete pakets[_paketIdx];
    }

    // Forward all payments and refund all collaterals if recipient agrees.
    function pay(uint256 _paketIdx) public {
        require(pakets[_paketIdx].recipient == msg.sender);
        uint256 idx;
        address payee;
        for (idx = 0; idx < pakets[_paketIdx].collateralRefundees.length; idx++) {
            payee = pakets[_paketIdx].collateralRefundees[idx];
            balances[payee] += pakets[_paketIdx].successBalances[payee];
            pakets[_paketIdx].successBalances[payee] = 0;
        }
        for (idx = 0; idx < pakets[_paketIdx].paymentBenificieries.length; idx++) {
            payee = pakets[_paketIdx].paymentBenificieries[idx];
            balances[payee] += pakets[_paketIdx].successBalances[payee];
            pakets[_paketIdx].successBalances[payee] = 0;
        }
        delete pakets[_paketIdx];
    }
}
