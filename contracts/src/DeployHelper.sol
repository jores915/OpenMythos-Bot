// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./OpenMythosMicroArb.sol";

contract DeployHelper {
    address constant UNISWAP_ROUTER = 0x2626664c2603336E57B271c5C0b26F421741e481;
    
    function deploy() external returns (OpenMythosMicroArb) {
        return new OpenMythosMicroArb(UNISWAP_ROUTER);
    }
}
