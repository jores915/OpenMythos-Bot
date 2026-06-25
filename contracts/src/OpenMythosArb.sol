// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IUniswapV3Pool {
    function flash(address recipient, uint256 amount0, uint256 amount1, bytes calldata data) external;
    function token0() external view returns (address);
    function token1() external view returns (address);
}

interface ISwapRouter {
    struct ExactInputParams {
        bytes   path;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }
    function exactInput(ExactInputParams calldata params) external payable returns (uint256 amountOut);
}

contract OpenMythosArb {
    address public owner;
    ISwapRouter public constant ROUTER =
        ISwapRouter(0x2626664c2603336E57B271c5C0b26F421741e481);
    address public constant FLASH_POOL =
        0xd0b53D9277642d899DF5C87A3966A349A798F224;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function startArbitrage(
        address tokenIn,
        uint256 amountIn,
        bytes calldata path1,
        bytes calldata path2,
        uint256 minProfit,
        uint24  flashFee
    ) external onlyOwner {
        IUniswapV3Pool pool = IUniswapV3Pool(FLASH_POOL);
        bool isToken0 = pool.token0() == tokenIn;
        bytes memory data = abi.encode(tokenIn, amountIn, path1, path2, minProfit, flashFee);
        pool.flash(address(this), isToken0 ? amountIn : 0, isToken0 ? 0 : amountIn, data);
    }

    function uniswapV3FlashCallback(
        uint256 fee0,
        uint256 fee1,
        bytes calldata data
    ) external {
        require(msg.sender == FLASH_POOL, "Unauthorized callback");

        (
            address tokenIn,
            uint256 amountIn,
            bytes memory path1,
            bytes memory path2,
            uint256 minProfit,
        ) = abi.decode(data, (address, uint256, bytes, bytes, uint256, uint24));

        uint256 fee = fee0 > 0 ? fee0 : fee1;

        IERC20(tokenIn).approve(address(ROUTER), amountIn);
        uint256 amountMid = ROUTER.exactInput(
            ISwapRouter.ExactInputParams({
                path: path1, recipient: address(this),
                deadline: block.timestamp + 60,
                amountIn: amountIn, amountOutMinimum: 1
            })
        );

        address tokenMid = _extractLastToken(path1);
        IERC20(tokenMid).approve(address(ROUTER), amountMid);
        uint256 amountOut = ROUTER.exactInput(
            ISwapRouter.ExactInputParams({
                path: path2, recipient: address(this),
                deadline: block.timestamp + 60,
                amountIn: amountMid, amountOutMinimum: 1
            })
        );

        uint256 owed = amountIn + fee;
        require(amountOut > owed + minProfit, "Not profitable");

        bool ok1 = IERC20(tokenIn).transfer(FLASH_POOL, owed);
        require(ok1, "Repay failed");
    }

    function _extractLastToken(bytes memory path) internal pure returns (address token) {
        require(path.length >= 20, "Path too short");
        assembly {
            token := shr(96, mload(add(add(path, 0x20), sub(mload(path), 20))))
        }
    }

    function withdraw(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        require(bal > 0, "Nothing to withdraw");
        bool ok = IERC20(token).transfer(owner, bal);
        require(ok, "Withdraw failed");
    }

    function withdrawETH() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }

    receive() external payable {}
}
