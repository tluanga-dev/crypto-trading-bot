# 🚀 Cryptocurrency Algorithmic Trading Bot

A professional-grade cryptocurrency trading bot with dual interfaces: a beautiful Rich terminal UI for local development and a REST API server for production deployment on Railway.com.

## ✨ Features

- **Dual Interface**: Rich terminal dashboard + REST API server
- **Real-time Updates**: Live market data and portfolio tracking
- **Advanced Analytics**: RSI, MACD, Bollinger Bands, and more technical indicators
- **Risk Management**: Built-in position sizing, stop-loss, and daily loss limits
- **Multiple Strategies**: RSI+MACD combination and Bollinger Bands mean reversion
- **Event-Driven Architecture**: Real-time notifications across all interfaces
- **Railway.com Ready**: Deploy as API server with static IP for Binance
- **Paper Trading**: Testnet mode by default for safe development

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                         │
├─────────────────────┬───────────────────────────────────────┤
│   Rich Terminal UI  │        FastAPI Server               │
│   (Local Dev)       │        (Production)                  │
└─────────────────────┼───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                 Core Trading Service                        │
│  ┌─────────────────┬─────────────────┬─────────────────┐   │
│  │  Market Analysis│  Risk Management│  Portfolio Mgmt │   │
│  │     Engine      │     System      │     System      │   │
│  └─────────────────┴─────────────────┴─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                Event System & Models                        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/tluanga-dev/crypto-trading-bot.git
cd crypto-trading-bot

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Binance API credentials
# Get API keys from: https://www.binance.com/en/my/settings/api-management
```

**Required Configuration:**
```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
TRADING_MODE=testnet  # Use 'testnet' for development, 'live' for production
```

### 3. Run the Trading Bot

#### 🎨 Rich Terminal Interface (Recommended for Local Development)

**Live Dashboard with Real-time Updates:**
```bash
python main.py dashboard --symbol BTCUSDT --balance 10000
```

**Interactive Command-line Interface:**
```bash
python main.py interactive --symbol BTCUSDT --balance 10000
```

**Quick Market Analysis:**
```bash
python main.py analyze --symbol BTCUSDT --strategy rsi_macd
```

#### 🌐 API Server (Production/Web Access)

**Start API Server Locally:**
```bash
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

**Access API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📋 Command Reference

### Rich Terminal Interface Commands

| Command | Description | Example |
|---------|-------------|---------|
| `dashboard` | Live trading dashboard with real-time updates | `python main.py dashboard --symbol BTCUSDT` |
| `interactive` | Interactive command-line interface | `python main.py interactive --symbol ETHUSDT` |
| `analyze` | Quick market analysis for a symbol | `python main.py analyze --symbol ADAUSDT --strategy bollinger` |

**Available Options:**
- `--symbol`: Trading pair symbol (default: BTCUSDT)
- `--balance`: Initial portfolio balance (default: 10000.0)
- `--strategy`: Trading strategy (rsi_macd, bollinger)

### Interactive Mode Commands

Once in interactive mode, use these commands:

| Command | Shortcut | Description |
|---------|----------|-------------|
| `analyze` | `a` | Analyze current market conditions |
| `position` | `p` | Open new trading position |
| `close` | `c` | Close existing position |
| `portfolio` | `pf` | Show portfolio summary |
| `strategies` | `s` | List available strategies |
| `help` | | Show command help |
| `quit` | `q` | Exit the program |

## 🌐 REST API Endpoints

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

### Real-time Updates
- `WS /ws/live-data` - WebSocket for real-time market data and portfolio updates

### API Usage Examples

**Analyze Market:**
```bash
curl -X GET "http://localhost:8000/api/analyze/BTCUSDT"
```

**Get Portfolio:**
```bash
curl -X GET "http://localhost:8000/api/portfolio"
```

**Open Position:**
```bash
curl -X POST "http://localhost:8000/api/positions" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT", "strategy": "rsi_macd"}'
```

**WebSocket Connection (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live-data');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## 🚀 Railway.com Deployment

### 1. Deploy to Railway

```bash
# Connect your GitHub repository to Railway
# Railway will automatically detect and deploy using:
# - Procfile
# - railway.json
# - requirements.txt
```

### 2. Set Environment Variables

In Railway dashboard, configure:
```env
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
TRADING_MODE=testnet
DEFAULT_SYMBOL=BTCUSDT
# ... other variables from .env.example
```

### 3. Configure Binance API

1. Get your Railway app's static IP address
2. Add it to your Binance API whitelist:
   - Go to Binance API Management
   - Edit your API key
   - Add Railway's IP to "Restrict access to trusted IPs only"

### 4. Access Your Deployed API

Your API will be available at: `https://your-app-name.railway.app`

## 📊 Trading Strategies

### RSI + MACD Strategy (Default)
- **Entry Signals**: RSI oversold + MACD bullish crossover
- **Exit Signals**: RSI overbought + MACD bearish crossover
- **Best For**: Trending markets with momentum

### Bollinger Bands Strategy
- **Entry Signals**: Price touches lower band (oversold)
- **Exit Signals**: Price returns to middle band
- **Best For**: Range-bound markets with mean reversion

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BINANCE_API_KEY` | Your Binance API key | Required |
| `BINANCE_SECRET_KEY` | Your Binance secret key | Required |
| `TRADING_MODE` | Trading mode (testnet/live) | testnet |
| `DEFAULT_SYMBOL` | Default trading pair | BTCUSDT |
| `MAX_POSITION_SIZE` | Max position size (% of portfolio) | 0.1 |
| `STOP_LOSS_PERCENTAGE` | Stop loss percentage | 2.0 |
| `TAKE_PROFIT_PERCENTAGE` | Take profit percentage | 5.0 |
| `ANALYSIS_TIMEFRAME` | Analysis timeframe | 1h |

### Risk Management Settings

- **Position Sizing**: Automatic based on portfolio size and signal confidence
- **Stop Loss**: Configurable percentage-based stop losses
- **Daily Loss Limit**: Maximum daily loss protection (5% default)
- **Maximum Drawdown**: Portfolio protection (15% default)
- **Position Limits**: Maximum number of concurrent positions (3 default)

## 🧪 Development & Testing

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .

# Run tests (when available)
python -m pytest
python -m pytest -v  # verbose output
```

### Debug Mode
```bash
# Set log level to DEBUG in .env
LOG_LEVEL=DEBUG

# View logs
tail -f logs/trading.log
```

## 🔒 Security Best Practices

### API Key Security
- ✅ Never commit API keys to repository
- ✅ Use environment variables for all secrets
- ✅ Enable IP restrictions on Binance API keys
- ✅ Use testnet for development
- ✅ Regular API key rotation

### Trading Safety
- ✅ Always start with testnet mode
- ✅ Use small position sizes initially
- ✅ Set appropriate stop losses
- ✅ Monitor positions regularly
- ✅ Implement proper risk management

## 📁 Project Structure

```
crypto_trade/
├── trading_service.py   # Core trading service (business logic)
├── models.py            # Shared Pydantic models for data validation
├── events.py            # Event-driven system for loose coupling
├── main.py              # Rich terminal interface (CLI)
├── api_server.py        # FastAPI REST API server
├── config.py            # Centralized configuration management
├── binance_client.py    # Binance API wrapper with error handling
├── data_analyzer.py     # Technical analysis and market data processing
├── strategy.py          # Trading strategy implementations
├── portfolio.py         # Portfolio management and risk management
├── logger.py            # Centralized logging configuration
├── requirements.txt     # Python dependencies
├── Procfile             # Railway deployment configuration
├── railway.json         # Railway deployment settings
├── .env.example         # Environment variables template
├── .gitignore          # Git ignore rules
└── logs/               # Application logs (auto-created)
```

## 🐛 Troubleshooting

### Common Issues

**1. API Connection Errors**
```bash
# Check API credentials
python -c "from binance_client import BinanceClient; client = BinanceClient(); print('Connected!')"
```

**2. Module Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**3. Binance IP Restrictions**
- Ensure your IP is whitelisted in Binance API settings
- For Railway deployment, add Railway's static IP

**4. Permission Errors (Railway)**
- Check that all environment variables are set
- Verify API keys have correct permissions

### Getting Help

1. Check the logs: `logs/trading.log` and `logs/trading_errors.log`
2. Enable DEBUG logging: Set `LOG_LEVEL=DEBUG` in `.env`
3. Test with testnet mode first: `TRADING_MODE=testnet`

## 📈 Performance Monitoring

### Built-in Metrics
- Portfolio value and PnL tracking
- Win rate and trade statistics
- Sharpe ratio and maximum drawdown
- Real-time position monitoring

### Logging
- **General logs**: `logs/trading.log`
- **Trading activity**: `logs/trading_trading.log`
- **Errors**: `logs/trading_errors.log`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is for educational purposes. Use at your own risk when trading with real funds.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Never invest more than you can afford to lose.

---

## 🎯 Quick Command Cheatsheet

```bash
# Local Development (Terminal UI)
python main.py dashboard --symbol BTCUSDT          # Live dashboard
python main.py interactive --symbol BTCUSDT        # Interactive mode
python main.py analyze --symbol BTCUSDT            # Quick analysis

# API Server
uvicorn api_server:app --reload --port 8000        # Start API server
curl http://localhost:8000/health                  # Health check
curl http://localhost:8000/api/portfolio           # Get portfolio

# Setup
cp .env.example .env                               # Copy config
pip install -r requirements.txt                   # Install deps
source venv/bin/activate                          # Activate env
```

Happy Trading! 🚀📈