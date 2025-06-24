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

### FastAPI Server Usage
```bash
# Start the API server locally
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000

# Start with production settings
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Railway deployment (automatic)
# Railway will use: uvicorn api_server:app --host 0.0.0.0 --port $PORT
```

### CLI Usage (Legacy)
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
├── api_server.py        # FastAPI REST API server with WebSocket support
├── main.py              # CLI application (legacy)
├── config.py            # Centralized configuration management
├── binance_client.py    # Binance API wrapper with error handling
├── data_analyzer.py     # Technical analysis and market data processing
├── strategy.py          # Trading strategy implementations and framework
├── portfolio.py         # Portfolio management and risk management
├── logger.py            # Centralized logging configuration
├── requirements.txt     # Python dependencies with FastAPI
├── Procfile             # Railway deployment configuration
├── railway.json         # Railway deployment settings
├── runtime.txt          # Python version specification
├── .env.example         # Environment variables template
├── .gitignore          # Git ignore rules
├── venv/               # Python virtual environment (excluded from version control)
└── logs/               # Application logs (created automatically)
```

## Core Components

- **TradingBotAPI**: FastAPI server class that orchestrates all components
- **WebSocketManager**: Manages real-time WebSocket connections for live updates
- **BinanceClient**: Handles all Binance API interactions with error handling
- **DataAnalyzer**: Processes market data and calculates technical indicators
- **StrategyManager**: Manages multiple trading strategies (RSI+MACD, Bollinger Bands)
- **Portfolio**: Tracks positions, calculates PnL, and manages risk
- **Config**: Centralized configuration using environment variables

## REST API Endpoints

### Market Analysis
- `GET /api/analyze/{symbol}` - Analyze market data for a symbol
- `GET /health` - Health check endpoint

### Portfolio Management
- `GET /api/portfolio` - Get portfolio status and metrics
- `GET /api/positions` - Get all open positions

### Trading Operations
- `POST /api/positions` - Open new position
- `DELETE /api/positions/{symbol}` - Close position

### Strategy Management
- `GET /api/strategies` - List available strategies
- `POST /api/strategies/{strategy_name}` - Set active strategy

### Real-time WebSocket
- `WS /ws/live-data` - Real-time market data and portfolio updates

## API Usage Examples

### Analyze Market
```bash
curl -X GET "https://your-railway-app.railway.app/api/analyze/BTCUSDT"
```

### Get Portfolio
```bash
curl -X GET "https://your-railway-app.railway.app/api/portfolio"
```

### Open Position
```bash
curl -X POST "https://your-railway-app.railway.app/api/positions" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT", "strategy": "rsi_macd"}'
```

### WebSocket Connection (JavaScript)
```javascript
const ws = new WebSocket('wss://your-railway-app.railway.app/ws/live-data');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

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

### Local Development
1. Copy `.env.example` to `.env` and configure with your Binance API credentials
2. Ensure TRADING_MODE is set to "testnet" for development
3. Install dependencies: `pip install -r requirements.txt`
4. Start API server: `uvicorn api_server:app --reload --host 0.0.0.0 --port 8000`
5. Access API documentation: `http://localhost:8000/docs`

### Railway.com Deployment
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard:
   - `BINANCE_API_KEY`
   - `BINANCE_SECRET_KEY`
   - `TRADING_MODE=testnet`
   - Other variables from `.env.example`
3. Railway will automatically deploy using `Procfile` and `railway.json`
4. Your API will be available at: `https://your-app-name.railway.app`

### Static IP for Binance
- Railway provides static IP addresses automatically
- Add Railway's IP to your Binance API whitelist
- Configure API restrictions in Binance for security

## Technical Indicators Used

- **RSI**: Relative Strength Index for momentum
- **MACD**: Moving Average Convergence Divergence for trend
- **Bollinger Bands**: Price volatility and mean reversion
- **Moving Averages**: SMA and EMA for trend confirmation
- **Volume Analysis**: Volume-weighted average price
- **Support/Resistance**: Dynamic levels based on price history