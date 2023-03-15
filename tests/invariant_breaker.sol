contract InvariantBreaker {
    bool public flag0 = true;
    bool public flag1 = true;

    function set0(int256 val) public returns (bool) {
        if (val % 100 == 0) flag0 = false;
        return flag0;
    }

    function set1(int256 val) public returns (bool) {
        if (val % 10 == 0 && !flag0) flag1 = false;
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
