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

    function launch(
        address _recipient,
        uint256 _deadline,
        uint256 _offeredPayment,
        uint256 _requiredCollateral
    ) public returns (uint256) {
        require(_deadline > now);
        uint256 paketIdx = pakets.length++;
        pakets[paketIdx].custodian = msg.sender;
        pakets[paketIdx].recipient = _recipient;
        pakets[paketIdx].deadline = _deadline;
        pakets[paketIdx].offeredPayment = _offeredPayment;
        pakets[paketIdx].requiredCollateral = _requiredCollateral;
        return paketIdx;
    }

    function _commitBuls(uint256 _paketIdx, uint256 _amount, address _payee, bool _isCollateral) private {
        require(balanceOf(msg.sender) >= _amount);
        balances[msg.sender] -= _amount;
        uint256 idx;
        if (_isCollateral) {
            idx = pakets[_paketIdx].collaterals.push(Commitment(_amount, msg.sender, _payee)) - 1;
            pakets[_paketIdx].payerToCollaterals[msg.sender].push(idx);
            pakets[_paketIdx].payeeToCollaterals[_payee].push(idx);
        } else {
            idx = pakets[_paketIdx].payments.push(Commitment(_amount, msg.sender, _payee)) - 1;
            pakets[_paketIdx].payerToPayments[msg.sender].push(idx);
            pakets[_paketIdx].payeeToPayments[_payee].push(idx);
        }
    }

    function commitPayment(uint256 _paketIdx, uint256 _amount, address _payee) public {
        _commitBuls(_paketIdx, _amount, _payee, false);
    }

    function commitCollateral(uint256 _paketIdx, uint256 _amount, address _payee) public {
        _commitBuls(_paketIdx, _amount, _payee, true);
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

    function paketSelfInterest(uint256 _paketIdx) public view returns (uint256, uint256) {
        uint256 payment = 0;
        uint256 collateral = 0;
        uint256 idx;
        for (idx = 0; idx < pakets[_paketIdx].payments.length; idx++) {
            if (pakets[_paketIdx].payments[idx].payee == msg.sender) {
                payment += pakets[_paketIdx].payments[idx].amount;
            } else if (pakets[_paketIdx].payments[idx].payer == msg.sender) {
                payment -= pakets[_paketIdx].payments[idx].amount;
            }
        }
        for (idx = 0; idx < pakets[_paketIdx].collaterals.length; idx++) {
            if (pakets[_paketIdx].collaterals[idx].payee == msg.sender) {
                collateral += pakets[_paketIdx].collaterals[idx].amount;
            } else if (pakets[_paketIdx].collaterals[idx].payer == msg.sender) {
                collateral -= pakets[_paketIdx].collaterals[idx].amount;
            }
        }
        return (payment, collateral);
    }

    function setCustodian(uint256 _paketIdx, address _newCustodian) public {
        require (pakets[_paketIdx].custodian == msg.sender);
        pakets[_paketIdx].custodian = _newCustodian;
    }

    function forwardPayment(uint256 _paketIdx, address _payee, uint256 _amount) public {
    }
}
