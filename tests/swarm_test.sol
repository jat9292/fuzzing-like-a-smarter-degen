pragma solidity 0.8.19;

contract InvariantBreaker {
    uint counter = 0;
    bool public flag1 = true;

    function reset(int256 val) public {
        counter = 0;
    }

    function set(int256 val) public returns (bool) {
        counter = counter + 1;
        if (counter == 50) {
            flag1 = false;
        }
        return flag1;
    }
}

contract InvariantTest {
    InvariantBreaker public inv;

    function setUp() public {
        inv = new InvariantBreaker();
    }

    function invariant_neverFalse() public returns (bool) {
        return inv.flag1();
    }
}
