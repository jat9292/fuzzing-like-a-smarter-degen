pragma solidity 0.8.19;

contract InvariantBreaker {
    bool public flag0 = true;

    function set0(string memory val) public returns (bool) {
        if (keccak256(abi.encodePacked(val)) == keccak256("fuzzinglikeadegen"))
            flag0 = false;
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
