pragma solidity ^0.4.13;
// ---------------------------------------------------------------------
// PaKeT experiment
// ---------------------------------------------------------------------

//import 'https://github.com/OpenZeppelin/zeppelin-solidity/contracts/token/MintableToken.sol';
import '../node_modules/zeppelin-solidity/contracts/token/ERC20/MintableToken.sol';

contract Paket is MintableToken {
    string public name = "PaKeT Bul";
    string public symbol = "BUL";
    uint256 public decimals = 18;
    address public owner = msg.sender;

    function Paket() public {
        totalSupply_ = 10 ** 6 * 10 ** decimals;
        balances[msg.sender] = totalSupply_;
    }

    struct PaketStruct {
        address recipient;
        uint256 deadline;
        // Balances in case of success and failure, indexed by payment and collateral.
        mapping (address => uint256) successBalances;
        address[] paymentBenificieries;
        address[] collateralRefundees;
        mapping (address => uint256) failBalances;
        address[] collateralBenificieries;
        address[] paymentRefundees;
    }

    mapping (uint256 => PaketStruct) private pakets;

    // Create a new "empty" paket if _deadline is in the future and_paketId is unique.
    function create(uint256 _paketId, address _recipient, uint256 _deadline) public {
        require(_deadline > now);
        require(pakets[_paketId].deadline == 0);
        pakets[_paketId] = PaketStruct(
            _recipient, _deadline, new address[](0), new address[](0), new address[](0), new address[](0)
        );
    }

    // Modifier to functions that commit BULs.
    // FIXME Perhaps we better use zeppelin's transfre method.
    // Which probably means we will be sending BULs to the contract itself.
    modifier commitBuls(uint256 _amount) {
        require(balanceOf(msg.sender) >= _amount);
        balances[msg.sender] -= _amount;
        _;
    }

    // Modifier to functions that need to add balances from outside.
    modifier managePaketBalances(uint256 _paketId, address _successAddress, address _failAddress, uint256 _amount) {
        pakets[_paketId].successBalances[_successAddress] += _amount;
        pakets[_paketId].failBalances[_failAddress] += _amount;
        _;
    }

    // Add payment to a paket.
    function commitPayment (uint256 _paketId, address _payee, uint256 _amount) public
        commitBuls(_amount) managePaketBalances(_paketId, _payee, msg.sender, _amount)
    {
        pakets[_paketId].paymentBenificieries.push(_payee);
        pakets[_paketId].paymentRefundees.push(msg.sender);
    }

    // Add collateral to a paket.
    function commitCollateral(uint256 _paketId, address _payee, uint256 _amount) public
        commitBuls(_amount) managePaketBalances(_paketId, msg.sender, _payee, _amount)
    {
        pakets[_paketId].collateralBenificieries.push(_payee);
        pakets[_paketId].collateralRefundees.push(msg.sender);
    }

    // Promise some of the payment previously promised to you to another.
    function relayPayment(uint256 _paketId, address _payee, uint256 _amount) public {
        require(pakets[_paketId].successBalances[msg.sender] >= _amount);
        pakets[_paketId].successBalances[msg.sender] -= _amount;
        pakets[_paketId].successBalances[_payee] += _amount;
        pakets[_paketId].paymentBenificieries.push(msg.sender);
    }

    // Cover someone else's collateral (so he gets his BULs back).
    // _amount must be equal or less than what he committed.
    // For increasing collateral use commitCollateral.
    function coverCollateral(uint256 _paketId, address _payee, uint256 _amount) public commitBuls(_amount) {
        require(pakets[_paketId].successBalances[_payee] >= _amount);
        pakets[_paketId].successBalances[_payee] -= _amount;
        pakets[_paketId].successBalances[msg.sender] += _amount;
        pakets[_paketId].collateralRefundees.push(msg.sender);
        balances[_payee] += _amount;
    }

    // Check my balance in case of success and failure;
    function paketSelfInterest(uint256 _paketId) public view returns (uint256, uint256) {
        return (pakets[_paketId].successBalances[msg.sender], pakets[_paketId].failBalances[msg.sender]);
    }

// Why can't we use this helper function?
//    function _settle(address[] _benificiaries, mapping (address => uint256) _payments) private {
//        for (uint256 idx = 0; idx < _benificiaries.length; idx++) {
//            balances[_benificiaries[idx]] += _payments[_benificiaries[idx]];
//            _payments[_benificiaries[idx]] = 0;
//        }
//    }
//
// Or even someting like this:
//
//    // This is a helper struct so we can bypass Solidity's limitation of not passing mappings as function arguments.
//    struct IndexedBalances {
//        mapping (address => uint256) balances;
//        address[] benificieries;
//    }
//
//    // Helper function that settles a bunch of balances.
//    function _settle(IndexedBalances storage _ibs) private {
//        for (uint256 idx = 0; idx < _ibs.benificiaries.length; idx++) {
//            balances[_ibs.benificiaries[idx]] += _ibs.payments[_ibs.benificiaries[idx]];
//            _ibs.payments[_ibs.benificiaries[idx]] = 0;
//        }
//    }
//
//    // Refund all payments and forward all collaterals if the deadline has passed.
//    function refund(uint256 _paketId) public {
//        require(pakets[_paketId].deadline < now);
//        _settle(IndexedBalances(pakets[_paketId].failBalances, pakets[_paketId].paymentRefundees));
//        _settle(IndexedBalances(pakets[_paketId].failBalances, pakets[_paketId].collateralBenificieries));

    // Refund all payments and forward all collaterals if the deadline has passed.
    function refund(uint256 _paketId) public {
        require(pakets[_paketId].deadline < now);
        uint256 idx;
        address payee;
        for (idx = 0; idx < pakets[_paketId].paymentRefundees.length; idx++) {
            payee = pakets[_paketId].paymentRefundees[idx];
            balances[payee] += pakets[_paketId].failBalances[payee];
            pakets[_paketId].failBalances[payee] = 0;
        }
        for (idx = 0; idx < pakets[_paketId].collateralBenificieries.length; idx++) {
            payee = pakets[_paketId].collateralBenificieries[idx];
            balances[payee] += pakets[_paketId].failBalances[payee];
            pakets[_paketId].failBalances[payee] = 0;
        }
        delete pakets[_paketId];
    }

    // Forward all payments and refund all collaterals if recipient agrees.
    function payout(uint256 _paketId) public {
        require(pakets[_paketId].recipient == msg.sender);
        uint256 idx;
        address payee;
        for (idx = 0; idx < pakets[_paketId].collateralRefundees.length; idx++) {
            payee = pakets[_paketId].collateralRefundees[idx];
            balances[payee] += pakets[_paketId].successBalances[payee];
            pakets[_paketId].successBalances[payee] = 0;
        }
        for (idx = 0; idx < pakets[_paketId].paymentBenificieries.length; idx++) {
            payee = pakets[_paketId].paymentBenificieries[idx];
            balances[payee] += pakets[_paketId].successBalances[payee];
            pakets[_paketId].successBalances[payee] = 0;
        }
        delete pakets[_paketId];
    }
}
