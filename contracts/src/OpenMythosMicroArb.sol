// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
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

contract OpenMythosMicroArb {
    address public owner;
    ISwapRouter public immutable router;

    event TradeExecuted(
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        uint256 amountOut,
        uint256 profit,
        uint256 timestamp
    );

    event TradeFailed(
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        string reason,
        uint256 timestamp
    );

    constructor(address _router) {
        owner = msg.sender;
        router = ISwapRouter(_router);
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    /// @notice Execute a micro-arbitrage: swap tokenIn -> tokenMid -> tokenIn on same pool
    /// @param tokenIn The token to start with
    /// @param tokenMid The intermediate token to swap through
    /// @param amountIn The amount of tokenIn to trade
    /// @param path1 The swap path from tokenIn to tokenMid
    /// @param path2 The swap path from tokenMid back to tokenIn
    /// @param minProfit Minimum profit in tokenIn wei
    function executeTrade(
        address tokenIn,
        address tokenMid,
        uint256 amountIn,
        bytes calldata path1,
        bytes calldata path2,
        uint256 minProfit
    ) external onlyOwner returns (bool) {
        // Step 1: Pull tokens from owner
        require(IERC20(tokenIn).transferFrom(msg.sender, address(this), amountIn), "TransferFrom failed");

        // Step 2: Swap tokenIn -> tokenMid
        IERC20(tokenIn).approve(address(router), amountIn);
        uint256 amountMid;
        try router.exactInput(
            ISwapRouter.ExactInputParams({
                path: path1,
                recipient: address(this),
                deadline: block.timestamp + 120,
                amountIn: amountIn,
                amountOutMinimum: 0
            })
        ) returns (uint256 out) {
            amountMid = out;
        } catch Error(string memory reason) {
            emit TradeFailed(tokenIn, tokenMid, amountIn, reason, block.timestamp);
            // Refund
            require(IERC20(tokenIn).transfer(msg.sender, amountIn), "Refund failed");
            return false;
        }

        // Step 3: Swap tokenMid -> tokenIn
        IERC20(tokenMid).approve(address(router), amountMid);
        uint256 amountOut;
        try router.exactInput(
            ISwapRouter.ExactInputParams({
                path: path2,
                recipient: address(this),
                deadline: block.timestamp + 120,
                amountIn: amountMid,
                amountOutMinimum: 0
            })
        ) returns (uint256 out) {
            amountOut = out;
        } catch Error(string memory reason) {
            emit TradeFailed(tokenIn, tokenMid, amountIn, reason, block.timestamp);
            // Refund tokenMid
            require(IERC20(tokenMid).transfer(msg.sender, amountMid), "Refund mid failed");
            return false;
        }

        // Step 4: Check profit
        if (amountOut <= amountIn) {
            emit TradeFailed(tokenIn, tokenMid, amountIn, "Not profitable", block.timestamp);
            // Send back whatever we got
            require(IERC20(tokenIn).transfer(msg.sender, amountOut), "Return failed");
            return false;
        }

        uint256 profit = amountOut - amountIn;

        if (profit < minProfit) {
            emit TradeFailed(tokenIn, tokenMid, amountIn, "Profit below min", block.timestamp);
            require(IERC20(tokenIn).transfer(msg.sender, amountOut), "Return below min failed");
            return false;
        }

        // Step 5: Send profit + original to owner
        require(IERC20(tokenIn).transfer(msg.sender, amountOut), "Payout failed");

        emit TradeExecuted(tokenIn, tokenMid, amountIn, amountOut, profit, block.timestamp);
        return true;
    }

    /// @notice Withdraw any accumulated tokens
    function withdraw(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) require(IERC20(token).transfer(owner, bal), "Withdraw failed");
    }

    /// @notice Withdraw ETH
    function withdrawETH() external onlyOwner {
        (bool ok, ) = payable(owner).call{value: address(this).balance}("");
        require(ok, "ETH transfer failed");
    }

    receive() external payable {}
}
