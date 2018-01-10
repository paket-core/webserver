pragma solidity ^0.4.13;
// ---------------------------------------------------------------------
// PaKeT experiment
// ---------------------------------------------------------------------

import 'https://github.com/OpenZeppelin/zeppelin-solidity/contracts/token/MintableToken.sol';

contract Bul is MintableToken {
    string public name = "Bul";
    string public symbol = "BUL";
    uint256 public decimals = 18;
    uint256 _totalSupply = 10 ** 6 * 10 ** decimals;
    address public owner = msg.sender;

    function Bul() public {
        totalSupply = _totalSupply;
        balances[msg.sender] = totalSupply;
    }


    struct Commitment {
        uint256 amount;
        address payer;
        address payee;
    }

    struct Paket {
        address recipient;
        uint256 deadline;
        uint256 offeredPayment;
        uint256 requiredCollateral;
        mapping(address => mapping(address => uint256)) payments;
        mapping(address => mapping(address => uint256)) collaterals;
    }

    Paket[] pakets;

    function launch(
        address _recipient,
        uint256 _deadline,
        uint256 _offeredPayment,
        uint256 _requiredCollateral
    ) public returns (uint256) {
        require(_deadline > now);
        Paket memory paket = Paket(_recipient, _deadline, _offeredPayment, _requiredCollateral);
        return pakets.push(paket) - 1;
    }

    function _commitBuls(uint256 _paketIdx, uint256 _amount, address _payee, bool _isCollateral) private {
        require(balanceOf(msg.sender) >= _amount);
        balances[msg.sender] -= _amount;
        if(_isCollateral) {
            pakets[_paketIdx].payments[msg.sender][_payee] += _amount;
        } else {
            pakets[_paketIdx].collaterals[msg.sender][_payee] += _amount;
        }
    }

    function commitPayment(uint256 _paketIdx, uint256 _amount, address _payee) public {
        _commitBuls(_paketIdx, _amount, _payee, false);
    }

    function commitCollateral(uint256 _paketIdx, uint256 _amount, address _payee) public {
        _commitBuls(_paketIdx, _amount, _payee, true);
    }
}
