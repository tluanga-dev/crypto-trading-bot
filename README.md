# Crypto Trading Platform - Real-time Market Data

A modern cryptocurrency trading platform with real-time market data visualization, built with FastAPI backend and Next.js frontend.

## Features

- 🔄 Real-time price updates via WebSocket
- 📊 Interactive candlestick charts with multiple timeframes (1m, 5m, 15m, 30m, 1h, 4h, 1d)
- 🎯 Multi-tab support for monitoring multiple cryptocurrencies
- ⭐ Favorite symbols for quick access
- 🔍 Symbol search functionality
- 📱 Responsive design for desktop and mobile
- 🌐 Powered by Binance API

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **WebSockets** - Real-time data streaming
- **python-binance** - Binance API integration
- **Pydantic** - Data validation
- **httpx** - Async HTTP client

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type safety
- **Context API** - State management
- **TailwindCSS** - Styling
- **Lightweight Charts** - TradingView charting library
- **Radix UI** - Headless UI components

## Project Structure

```
crypto_trade/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Core functionality
│   │   ├── models/       # Data models
│   │   ├── services/     # Business logic
│   │   └── main.py       # FastAPI app
│   └── requirements.txt
│
└── frontend/
    ├── app/              # Next.js app directory
    ├── components/       # React components
    ├── contexts/         # Context providers
    ├── types/           # TypeScript types
    └── package.json
```

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

5. Run the backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000
API documentation: http://localhost:8000/docs

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## API Endpoints

### REST Endpoints

- `GET /api/v1/symbols` - Get all trading symbols
- `GET /api/v1/symbols/search?q={query}` - Search symbols
- `GET /api/v1/symbols/popular` - Get popular symbols
- `GET /api/v1/market/{symbol}` - Get market data for a symbol
- `GET /api/v1/market/{symbol}/klines` - Get candlestick data
- `GET /api/v1/market/{symbol}/orderbook` - Get order book

### WebSocket Endpoint

- `WS /ws/{client_id}` - Real-time market data stream

## WebSocket Messages

### Client to Server

```json
{
  "type": "subscribe",
  "symbol": "BTCUSDT",
  "timeframes": ["1m", "5m"]
}
```

### Server to Client

```json
{
  "type": "price_update",
  "symbol": "BTCUSDT",
  "price": 45123.45,
  "volume": 1234567.89,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Environment Variables

### Backend (.env)
```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
BINANCE_TESTNET=true
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Development

### Running Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Linting
```bash
# Backend
cd backend
flake8 .
black .

# Frontend
cd frontend
npm run lint
```

## Production Deployment

### Backend
1. Use a production ASGI server like Gunicorn with Uvicorn workers
2. Set up proper environment variables
3. Configure CORS for your production domain
4. Use Redis for caching (optional)

### Frontend
1. Build the production bundle:
```bash
npm run build
```

2. Deploy to Vercel, Netlify, or any static hosting service

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.