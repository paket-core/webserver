pragma solidity ^0.4.13;
// ---------------------------------------------------------------------
// Pass mappings to functions.
// ---------------------------------------------------------------------


contract Bul {
    struct MapWrap {
        mapping (string => uint256) stam;
    }
    
    MapWrap m1;
    MapWrap m2;

    function init() public {
        m1.stam["one"] = 2;
        m2.stam["one"] = 4;
    }
    
    function _t(mapping (string => uint256) _m) internal returns (uint256) {
        return _m.stam["one"];
    }
    
    function f1() public view returns (uint256) {
        return _t(m1);
    }

    function f2() public view returns (uint256) {
        return _t(m2);
    }
}
