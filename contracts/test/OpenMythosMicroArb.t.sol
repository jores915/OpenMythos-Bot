// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../src/OpenMythosMicroArb.sol";

contract OpenMythosMicroArbTest {
    OpenMythosMicroArb public arb;
    
    function setUp() public {
        arb = new OpenMythosMicroArb(0x2626664c2603336E57B271c5C0b26F421741e481);
    }
    
    function testOwner() public view {
        require(arb.owner() == address(this), "owner mismatch");
    }
    
    function testRouter() public view {
        require(address(arb.router()) == 0x2626664c2603336E57B271c5C0b26F421741e481, "router mismatch");
    }
}
