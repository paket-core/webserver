pragma solidity ^0.4.8;

// ----------------------------------------------------------------------------------------------
// Botavili experiment
// ----------------------------------------------------------------------------------------------

// ERC Token Standard #20 Interface
// https://github.com/ethereum/EIPs/issues/20
contract ERC20Interface{
    // Get the total token supply
    function totalSupply() public constant returns (uint256 supply);

    // Get the account balance of another account with address _owner
    function balanceOf(address _owner) public constant returns (uint256 balance);

    // Send _value amount of tokens to address _to
    function transfer(address _to, uint256 _value) public returns (bool success);

    // Send _value amount of tokens from address _from to address _to
    function transferFrom(address _from, address _to, uint256 _value) public returns (bool success);

    // Allow _spender to withdraw from your account, multiple times, up to the _value amount.
    // If this function is called again it overwrites the current allowance with _value.
    // this function is required for some DEX functionality
    function approve(address _spender, uint256 _value) public returns (bool success);

    // Returns the amount which _spender is still allowed to withdraw from _owner
    function allowance(address _owner, address _spender) public constant returns (uint256 remaining);

    // Triggered when tokens are transferred.
    event Transfer(address indexed _from, address indexed _to, uint256 _value);

    // Triggered whenever approve(address _spender, uint256 _value) is called.
    event Approval(address indexed _owner, address indexed _spender, uint256 _value);
}

contract FixedSupplyToken is ERC20Interface{
    uint256 _totalSupply;

    // Balances for each account
    mapping(address => uint256) balances;

    // Owner of account approves the transfer of an amount to another account
    mapping(address => mapping (address => uint256)) allowed;

    // Constructor
    function FixedSupplyToken(uint256 _supply) public{
        _totalSupply = _supply;
        balances[msg.sender] = _totalSupply;
    }

    function totalSupply() public constant returns (uint256 supply){
        supply = _totalSupply;
    }

    // What is the balance of a particular account?
    function balanceOf(address _owner) public constant returns (uint256 balance){
        return balances[_owner];
    }

    // Transfer the balance from owner's account to another account
    function transfer(address _to, uint256 _amount) public returns (bool success){
        if (balances[msg.sender] >= _amount
            && _amount > 0
            && balances[_to] + _amount > balances[_to]){
            balances[msg.sender] -= _amount;
            balances[_to] += _amount;
            Transfer(msg.sender, _to, _amount);
            return true;
        } else{
            return false;
        }
    }

    // Send _value amount of tokens from address _from to address _to
    // The transferFrom method is used for a withdraw workflow, allowing contracts to send
    // tokens on your behalf, for example to "deposit" to a contract address and/or to charge
    // fees in sub-currencies; the command should fail unless the _from account has
    // deliberately authorized the sender of the message via some mechanism; we propose
    // these standardized APIs for approval:
    function transferFrom(
        address _from,
        address _to,
        uint256 _amount
    ) public returns (bool success){
        if (balances[_from] >= _amount
            && allowed[_from][msg.sender] >= _amount
            && _amount > 0
            && balances[_to] + _amount > balances[_to]){
            balances[_from] -= _amount;
            allowed[_from][msg.sender] -= _amount;
            balances[_to] += _amount;
            Transfer(_from, _to, _amount);
            return true;
        } else{
            return false;
        }
    }

    // Allow _spender to withdraw from your account, multiple times, up to the _value amount.
    // If this function is called again it overwrites the current allowance with _value.
    function approve(address _spender, uint256 _amount) public returns (bool success){
        allowed[msg.sender][_spender] = _amount;
        Approval(msg.sender, _spender, _amount);
        return true;
    }

    function allowance(address _owner, address _spender) public constant returns (uint256 remaining){
        return allowed[_owner][_spender];
    }
}

contract Paket{
    struct Escrow{
        address custodian;
        address courier;
        uint256 payment;
        uint256 collateral;
    }
    Escrow[] public escrows;
    uint256 deadline;
    address custodian;

    function Paket(uint256 _payment, uint256 _collateral, uint256 _deadline) public{
        escrows.push(Escrow(msg.sender, 0x0, _payment, _collateral));
        custodian = msg.sender;
        deadline = _deadline;
    }

    function commit(address courier_) public{
        escrows[escrows.length - 1].courier = courier_;
    }

    function getLauncher() public constant returns (address _launcher){
        _launcher = escrows[0].custodian;
    }

    function isRefundable() public constant returns (bool _refundable){
        _refundable = block.timestamp >= deadline;
    }

    function processFunds(function(address, uint256) external callback, bool refund) public{
        for(uint i = 0; i < escrows.length - 1; i++){
            address benificiary = refund ? escrows[i].courier : escrows[i].custodian;
            callback(benificiary, escrows[i].payment + escrows[i].collateral);
        }
    }
}

contract Bul is FixedSupplyToken{
    string public constant symbol = "BUL";
    string public constant name = "BUL";
    uint256 _totalSupply = 1000000;

    Paket[] pakets;

    function Bul() public FixedSupplyToken(_totalSupply){}

    function launch(uint256 _payment, uint256 _collateral, uint256 _deadline) public returns (uint256 id){
        assert(balanceOf(msg.sender) >= _payment);
        balances[msg.sender] -= _payment;
        pakets.push(new Paket(_payment, _collateral, _deadline));
        return pakets.length - 1;
    }

    function commit(uint256 id_){
        //Paket p = pakets[id_].commit();
        //assert(balanceOf(msg.sender) >= payment_);
        //balances[msg.sender] -= _payment;
        //pakets.push(new Paket(_payment, _collateral, _deadline));
        //return pakets.length - 1;
    }

    function settle_(address benificiary_, uint256 amount_) external{
        balances[benificiary_] += amount_;
    }

    function settle(uint256 id_, bool refund) public{
        pakets[id_].processFunds(this.settle_, refund);
    }
}
