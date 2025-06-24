# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a modern cryptocurrency trading platform with real-time market data visualization. The project has been refactored into a FastAPI backend and Next.js frontend architecture.

## Development Environment

- Backend: Python 3.8+ with FastAPI
- Frontend: Node.js 18+ with Next.js 15
- Database: Binance API (no local database required)

## Project Structure

```
crypto_trade/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # REST API endpoints
│   │   ├── core/           # Core functionality (config, WebSocket)
│   │   ├── models/         # Pydantic data models
│   │   ├── services/       # Business logic services
│   │   └── main.py         # FastAPI application entry point
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # Next.js frontend
│   ├── app/               # Next.js App Router
│   ├── components/        # React components
│   ├── contexts/          # Context API providers
│   ├── types/            # TypeScript type definitions
│   └── package.json      # Node.js dependencies
│
└── legacy/               # Old trading bot files (archived)
```

## Common Commands

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
```

### Running the Application

#### Backend (API Server)
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API will be available at: http://localhost:8000
# API documentation: http://localhost:8000/docs
```

#### Frontend (Web Application)
```bash
cd frontend
npm run dev

# Web app will be available at: http://localhost:3000
```

#### Production Deployment
```bash
# Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run build
npm start
```

### Development Workflow

#### Backend
```bash
cd backend

# Code formatting and linting
black .
flake8 .

# Run tests (when test files exist)
python -m pytest
python -m pytest -v  # verbose output
```

#### Frontend
```bash
cd frontend

# Linting and formatting
npm run lint
npm run lint:fix

# Type checking
npx tsc --noEmit

# Build for production
npm run build
```

## Core Components

### Backend Components (FastAPI)
- **API Endpoints**: RESTful API for market data, symbols, and WebSocket management
- **WebSocket Manager**: Real-time Binance data streaming with auto-reconnection
- **Binance Service**: Async integration with Binance API
- **Data Models**: Pydantic models for type safety and validation
- **Configuration**: Environment-based settings management

### Frontend Components (Next.js)
- **Context Providers**:
  - **WebSocketContext**: Manages WebSocket connection and message handling
  - **MarketDataContext**: Stores and manages all market data
  - **TabsContext**: Handles multi-tab functionality with persistence
- **UI Components**:
  - **CryptoSelector**: Symbol selection with search and favorites
  - **CandlestickChart**: TradingView Lightweight Charts integration
  - **TimeframeSelector**: Multiple timeframe support (1m, 5m, 15m, 30m, 1h, 4h, 1d)
  - **TabManager**: Multi-tab interface for monitoring multiple symbols
  - **PriceDisplay**: Real-time price updates with animations

### Key Features
- **Real-time Updates**: WebSocket streaming for live price and chart data
- **Multi-symbol Support**: Monitor up to 10 symbols simultaneously in tabs
- **Professional Charts**: Candlestick charts with volume and technical indicators
- **Responsive Design**: Works on desktop and mobile devices
- **Favorites System**: Save frequently watched symbols
- **Symbol Search**: Quick symbol lookup with autocomplete

## REST API Endpoints

### Symbol Management
- `GET /api/v1/symbols` - Get all trading symbols with pagination
- `GET /api/v1/symbols/search?q={query}` - Search symbols by query
- `GET /api/v1/symbols/popular` - Get popular trading symbols
- `GET /api/v1/symbols/{symbol}` - Get detailed symbol information

### Market Data
- `GET /api/v1/market/{symbol}` - Get current market data for a symbol
- `GET /api/v1/market/{symbol}/klines` - Get candlestick data with timeframe
- `GET /api/v1/market/{symbol}/orderbook` - Get order book depth
- `GET /api/v1/market/{symbol}/trades` - Get recent trades
- `POST /api/v1/market/batch` - Get market data for multiple symbols

### System Endpoints
- `GET /health` - Health check endpoint
- `GET /` - API information

### Real-time WebSocket
- `WS /ws/{client_id}` - Real-time market data streaming

## API Usage Examples

### Get Market Data
```bash
curl -X GET "http://localhost:8000/api/v1/market/BTCUSDT"
```

### Search Symbols
```bash
curl -X GET "http://localhost:8000/api/v1/symbols/search?q=BTC"
```

### Get Candlestick Data
```bash
curl -X GET "http://localhost:8000/api/v1/market/BTCUSDT/klines?interval=5m&limit=100"
```

### WebSocket Connection (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/client_123');

ws.onopen = () => {
    // Subscribe to symbol updates
    ws.send(JSON.stringify({
        type: 'subscribe',
        symbol: 'BTCUSDT',
        timeframes: ['1m', '5m']
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## Security Considerations

- Never commit API keys or sensitive credentials
- Use environment variables for configuration
- Implement proper error handling for API calls
- Consider rate limiting for exchange APIs
- Validate all user inputs and API responses
- Use CORS properly for production deployments

## Application Architecture

- **Separation of Concerns**: Clean split between backend API and frontend UI
- **Real-time Communication**: WebSocket streaming for live data updates
- **Type Safety**: Full TypeScript support in frontend, Pydantic models in backend
- **State Management**: React Context API for predictable state updates
- **Responsive Design**: Mobile-first approach with desktop enhancements
- **Error Handling**: Comprehensive error boundaries and user feedback

## Architecture Benefits

- **Scalability**: Backend and frontend can be deployed independently
- **Maintainability**: Clear separation between data layer and presentation layer
- **Performance**: Efficient WebSocket streaming and optimized React rendering
- **Developer Experience**: Hot reloading, TypeScript, and modern tooling
- **User Experience**: Professional trading interface with real-time updates

## Setup Instructions

### Local Development

#### Backend Setup
1. Navigate to backend directory: `cd backend`
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment: `source venv/bin/activate` (Windows: `venv\Scripts\activate`)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure (optional for development)
6. Start server: `uvicorn app.main:app --reload`
7. Access API documentation: `http://localhost:8000/docs`

#### Frontend Setup
1. Navigate to frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Start development server: `npm run dev`
4. Access web application: `http://localhost:3000`

### Environment Variables

#### Backend (.env)
```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
BINANCE_TESTNET=true
CORS_ORIGINS=["http://localhost:3000"]
```

#### Frontend
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Production Deployment

The application can be deployed to any cloud platform that supports:
- Python/FastAPI applications (backend)
- Node.js/Next.js applications (frontend)

Popular options include Vercel, Netlify, Railway, Heroku, or AWS.

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **WebSockets**: Real-time bidirectional communication
- **Pydantic**: Data validation and settings management
- **httpx**: Async HTTP client for Binance API
- **python-binance**: Binance API wrapper

### Frontend
- **Next.js 15**: React framework with App Router
- **TypeScript**: Static type checking
- **TailwindCSS**: Utility-first CSS framework
- **Lightweight Charts**: TradingView charting library
- **Context API**: React state management
- **Radix UI**: Headless UI components