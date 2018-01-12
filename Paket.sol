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

    struct Commitment {
        uint256 amount;
        address payer;
        address payee;
    }

    struct Paket {
        address recipient;
        address custodian;
        uint256 deadline;
        uint256 offeredPayment;
        uint256 requiredCollateral;
        Commitment[] payments;
        mapping (address => uint256[]) payerToPayments;
        mapping (address => uint256[]) payeeToPayments;
        Commitment[] collaterals;
        mapping (address => uint256[]) payerToCollaterals;
        mapping (address => uint256[]) payeeToCollaterals;
    }

    Paket[] private pakets;

    function create(
        address _recipient,
        uint256 _deadline,
        uint256 _offeredPayment,
        uint256 _requiredCollateral
    ) public returns (uint256) {
        require(_deadline > now);
        uint256 paketIdx = pakets.length;
        pakets.length++;
        pakets[paketIdx].custodian = msg.sender;
        pakets[paketIdx].recipient = _recipient;
        pakets[paketIdx].deadline = _deadline;
        pakets[paketIdx].offeredPayment = _offeredPayment;
        pakets[paketIdx].requiredCollateral = _requiredCollateral;
        return paketIdx;
    }

    function transferCustodianship(uint256 _paketIdx, address _newCustodian) public {
        require (pakets[_paketIdx].custodian == msg.sender);
        pakets[_paketIdx].custodian = _newCustodian;
    }

    modifier commitBuls(uint256 _amount) {
        require(balanceOf(msg.sender) >= _amount);
        balances[msg.sender] -= _amount;
        _;
    }

    function _commitPayment(uint256 _paketIdx, address _payee, uint256 _amount) private {
            uint256 idx = pakets[_paketIdx].payments.push(Commitment(_amount, msg.sender, _payee)) - 1;
            pakets[_paketIdx].payerToPayments[msg.sender].push(idx);
            pakets[_paketIdx].payeeToPayments[_payee].push(idx);
    }

    function _commitCollateral(uint256 _paketIdx, address _payee, uint256 _amount) private {
            uint256 idx = pakets[_paketIdx].collaterals.push(Commitment(_amount, msg.sender, _payee)) - 1;
            pakets[_paketIdx].payerToCollaterals[msg.sender].push(idx);
            pakets[_paketIdx].payeeToCollaterals[_payee].push(idx);
    }

    function commitPayment(uint256 _paketIdx, address _payee, uint256 _amount) public commitBuls(_amount) {
        _commitPayment(_paketIdx, _payee, _amount);
    }

    function commitCollateral(uint256 _paketIdx, address _payee, uint256 _amount) public commitBuls(_amount) {
        _commitCollateral(_paketIdx, _payee, _amount);
    }

    function _countCommitments(Commitment[] _commintments, uint256[] _creditIndexes, uint256[] _debitIndexes) private pure returns (uint256) {
        uint256 sum = 0;
        uint256 idx;
        for (idx = 0; idx < _creditIndexes.length; idx++) {
            sum += _commintments[idx].amount;
        }
        for (idx = 0; idx < _debitIndexes.length; idx++) {
            sum -= _commintments[idx].amount;
        }
        return sum;
    }

    function paketPaymentsToMe(uint256 _paketIdx) public view returns (uint256) {
        return _countCommitments(pakets[_paketIdx].payments, pakets[_paketIdx].payeeToPayments[msg.sender], pakets[_paketIdx].payerToPayments[msg.sender]);
    }

    function paketCollateralsToMe(uint256 _paketIdx) public view returns (uint256) {
        return _countCommitments(pakets[_paketIdx].collaterals, pakets[_paketIdx].payeeToCollaterals[msg.sender], pakets[_paketIdx].payerToCollaterals[msg.sender]);
    }

    function relayPayment(uint256 _paketIdx, address _payee, uint256 _amount) public {
        require(paketPaymentsToMe(_paketIdx) >= _amount);
        _commitPayment(_paketIdx, _payee, _amount);
    }

    function coverCollateral(uint256 _paketIdx, address _payee, uint256 _amount) public commitBuls(_amount) {
        uint256 amountLeft = _amount;
        uint256 idx;
        for (uint256 idxOfIdx = 0; idxOfIdx <= pakets[_paketIdx].payerToCollaterals[_payee].length && amountLeft > 0; idxOfIdx++) {
            idx = pakets[_paketIdx].payerToCollaterals[_payee][idxOfIdx];
            if (pakets[_paketIdx].collaterals[idx].amount <= amountLeft) {
                pakets[_paketIdx].collaterals[idx].payer = msg.sender;
                amountLeft -= pakets[_paketIdx].collaterals[idx].amount;
            } else {
                pakets[_paketIdx].collaterals[idx].amount -= amountLeft;
                _commitCollateral(_paketIdx, pakets[_paketIdx].collaterals[idx].payee, amountLeft);
                amountLeft = 0;
            }
        }
        require(amountLeft == 0);
        balances[_payee] += _amount;
    }
}
