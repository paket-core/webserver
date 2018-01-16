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
        mapping (address => uint256) successBalances;
        address[] paymentBenificieries;
        address[] collateralRefundees;
        mapping (address => uint256) failBalances;
        address[] collateralBenificieries;
        address[] paymentRefundees;
    }

    Paket[] private pakets;

    function create(
        address _recipient, uint256 _deadline, uint256 _offeredPayment, uint256 _requiredCollateral
    ) public returns (uint256) {
        require(_deadline > now);
        return pakets.push(Paket(
            _recipient, _deadline, _offeredPayment, _requiredCollateral,
            new address[](0), new address[](0), new address[](0), new address[](0)
        )) - 1;
    }

    modifier commitBuls(uint256 _amount) {
        require(balanceOf(msg.sender) >= _amount);
        balances[msg.sender] -= _amount;
        _;
    }

    modifier managePaketBalances(uint256 _paketIdx, address _successAddress, address _failAddress, uint256 _amount) {
        pakets[_paketIdx].successBalances[_successAddress] += _amount;
        pakets[_paketIdx].failBalances[_failAddress] += _amount;
        _;
    }

    function commitPayment (uint256 _paketIdx, address _payee, uint256 _amount) public
        commitBuls(_amount) managePaketBalances(_paketIdx, _payee, msg.sender, _amount)
    {
        pakets[_paketIdx].paymentBenificieries.push(_payee);
        pakets[_paketIdx].paymentRefundees.push(msg.sender);
    }

    function commitCollateral(uint256 _paketIdx, address _payee, uint256 _amount) public
        commitBuls(_amount) managePaketBalances(_paketIdx, msg.sender, _payee, _amount)
    {
        pakets[_paketIdx].collateralBenificieries.push(_payee);
        pakets[_paketIdx].collateralRefundees.push(msg.sender);
    }

    function relayPayment(uint256 _paketIdx, address _payee, uint256 _amount) public {
        require(pakets[_paketIdx].successBalances[msg.sender] >= _amount);
        pakets[_paketIdx].successBalances[msg.sender] -= _amount;
        pakets[_paketIdx].successBalances[_payee] += _amount;
        pakets[_paketIdx].paymentBenificieries.push(msg.sender);
    }

    function coverCollateral(uint256 _paketIdx, address _payee, uint256 _amount) public commitBuls(_amount) {
        require(pakets[_paketIdx].successBalances[_payee] >= _amount);
        pakets[_paketIdx].successBalances[_payee] -= _amount;
        pakets[_paketIdx].successBalances[msg.sender] += _amount;
        pakets[_paketIdx].collateralRefundees.push(msg.sender);
        balances[_payee] += _amount;
    }

    function paketSelfInterest(uint256 _paketIdx) public view returns (uint256, uint256) {
        return (pakets[_paketIdx].successBalances[msg.sender], pakets[_paketIdx].failBalances[msg.sender]);
    }

//    function _settle(address[] _benificiaries, mapping (address => uint256) _payments) private {
//        for (uint256 idx = 0; idx < _benificiaries.length; idx++) {
//            balances[_benificiaries[idx]] += _payments[_benificiaries[idx]];
//            _payments[_benificiaries[idx]] = 0;
//        }
//    }

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
