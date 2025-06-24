# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cryptocurrency trading application built with Python. The project is in early development stage.

## Development Environment

- Python virtual environment is located in `venv/`
- Activate virtual environment: `source venv/bin/activate`
- Deactivate virtual environment: `deactivate`

## Common Commands

### Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Application Usage
```bash
# Analyze market for a specific symbol
python main.py analyze --symbol BTCUSDT --strategy rsi_macd

# Run the trading bot continuously
python main.py run --symbol BTCUSDT --strategy rsi_macd --interval 60

# Run backtest on historical data
python main.py backtest --symbol BTCUSDT --strategy rsi_macd

# List available strategies
python main.py strategies
```

### Development Workflow
```bash
# Code formatting and linting
black .
flake8 .

# Run tests (when test files exist)
python -m pytest
python -m pytest -v  # verbose output
```

## Project Structure

```
crypto_trade/
├── main.py              # Main application entry point with CLI commands
├── config.py            # Centralized configuration management
├── binance_client.py    # Binance API wrapper with error handling
├── data_analyzer.py     # Technical analysis and market data processing
├── strategy.py          # Trading strategy implementations and framework
├── portfolio.py         # Portfolio management and risk management
├── logger.py            # Centralized logging configuration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .gitignore          # Git ignore rules
├── venv/               # Python virtual environment (excluded from version control)
└── logs/               # Application logs (created automatically)
```

## Core Components

- **TradingBot**: Main bot class that orchestrates all components
- **BinanceClient**: Handles all Binance API interactions with error handling
- **DataAnalyzer**: Processes market data and calculates technical indicators
- **StrategyManager**: Manages multiple trading strategies (RSI+MACD, Bollinger Bands)
- **Portfolio**: Tracks positions, calculates PnL, and manages risk
- **Config**: Centralized configuration using environment variables

## Security Considerations

- Never commit API keys, private keys, or sensitive trading credentials
- Use environment variables for configuration
- Implement proper error handling for API calls
- Consider rate limiting for exchange APIs
- Validate all user inputs and API responses

## Trading Application Specifics

- **Default Mode**: Application runs in testnet mode by default for safety
- **Risk Management**: Built-in position sizing, stop losses, and daily loss limits
- **Strategies Available**: RSI+MACD combination and Bollinger Bands mean reversion
- **Logging**: Comprehensive logging with separate files for trading, errors, and general logs
- **Real Trading**: Requires explicit confirmation and environment variable changes

## Setup Instructions

1. Copy `.env.example` to `.env` and configure with your Binance API credentials
2. Ensure TRADING_MODE is set to "testnet" for development
3. Install dependencies: `pip install -r requirements.txt`
4. Run analysis: `python main.py analyze --symbol BTCUSDT`

## Technical Indicators Used

- **RSI**: Relative Strength Index for momentum
- **MACD**: Moving Average Convergence Divergence for trend
- **Bollinger Bands**: Price volatility and mean reversion
- **Moving Averages**: SMA and EMA for trend confirmation
- **Volume Analysis**: Volume-weighted average price
- **Support/Resistance**: Dynamic levels based on price history