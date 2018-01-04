pragma solidity ^0.4.13;
// ---------------------------------------------------------------------
// Paket experiment
// ---------------------------------------------------------------------

import 'zeppelin-solidity/contracts/token/MintableToken.sol';

contract Paket is MintableToken {
    string public name = "BUL";
    string public symbol = "BUL";
    uint8 public decimals = 18;
    uint256 _totalSupply = 1000000;
    address public owner = msg.sender;

    function Paket(){
        totalSupply = _totalSupply;
        balances[msg.sender] = totalSupply;
    }
}
