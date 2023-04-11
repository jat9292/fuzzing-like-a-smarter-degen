pragma solidity 0.8.19;

contract InvariantBreaker {
    bool public flag0 = true;
    uint counter;

    function fuzzing(uint8 val) public returns (bool) {
        if (val > 40 && val < 60 && counter == 0) ++counter;
        else if (val > 40 && val < 60 && counter == 1) ++counter;
        else if (val > 210 && val < 230 && counter == 2) flag0 = false;
        else counter = 0;
        return flag0;
    }
}

contract InvariantTest {
    InvariantBreaker public inv;

    function setUp() public {
        inv = new InvariantBreaker();
    }

    function invariant_neverFalse() public returns (bool) {
        return inv.flag0();
    }
}
