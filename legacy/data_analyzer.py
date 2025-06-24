import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import ta
from loguru import logger

class DataAnalyzer:
    """Technical analysis and data processing for cryptocurrency market data."""
    
    def __init__(self):
        """Initialize the data analyzer."""
        self.data = None
        
    def klines_to_dataframe(self, klines: List[List]) -> pd.DataFrame:
        """Convert Binance klines data to pandas DataFrame."""
        try:
            columns = [
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ]
            
            df = pd.DataFrame(klines, columns=columns)
            
            # Convert to appropriate data types
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                             'quote_asset_volume', 'taker_buy_base_asset_volume', 
                             'taker_buy_quote_asset_volume']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            
            logger.debug(f"Converted {len(df)} klines to DataFrame")
            return df
            
        except Exception as e:
            logger.error(f"Failed to convert klines to DataFrame: {e}")
            raise
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the DataFrame."""
        try:
            # Moving Averages
            df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
            df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
            df['ema_12'] = ta.trend.ema_indicator(df['close'], window=12)
            df['ema_26'] = ta.trend.ema_indicator(df['close'], window=26)
            
            # MACD
            df['macd'] = ta.trend.macd_diff(df['close'])
            df['macd_signal'] = ta.trend.macd_signal(df['close'])
            df['macd_histogram'] = ta.trend.macd(df['close'])
            
            # RSI
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            
            # Bollinger Bands
            df['bb_upper'] = ta.volatility.bollinger_hband(df['close'])
            df['bb_middle'] = ta.volatility.bollinger_mavg(df['close'])
            df['bb_lower'] = ta.volatility.bollinger_lband(df['close'])
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            
            # Stochastic Oscillator
            df['stoch_k'] = ta.momentum.stoch(df['high'], df['low'], df['close'])
            df['stoch_d'] = ta.momentum.stoch_signal(df['high'], df['low'], df['close'])
            
            # Average True Range (ATR)
            df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'])
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_weighted_average_price'] = ta.volume.volume_weighted_average_price(
                df['high'], df['low'], df['close'], df['volume']
            )
            
            # Support and Resistance levels
            df['support'] = df['low'].rolling(window=20).min()
            df['resistance'] = df['high'].rolling(window=20).max()
            
            logger.debug("Added technical indicators to DataFrame")
            return df
            
        except Exception as e:
            logger.error(f"Failed to add technical indicators: {e}")
            raise
    
    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate buy/sell signals based on technical indicators."""
        try:
            # Initialize signal columns
            df['signal'] = 0  # 0: hold, 1: buy, -1: sell
            df['signal_strength'] = 0.0  # Signal strength from 0 to 1
            
            # RSI signals
            rsi_oversold = df['rsi'] < 30
            rsi_overbought = df['rsi'] > 70
            
            # MACD signals
            macd_bullish = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
            macd_bearish = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
            
            # Moving Average signals
            ma_bullish = df['close'] > df['sma_20']
            ma_bearish = df['close'] < df['sma_20']
            
            # Bollinger Bands signals
            bb_oversold = df['close'] < df['bb_lower']
            bb_overbought = df['close'] > df['bb_upper']
            
            # Combine signals
            buy_signals = (
                (rsi_oversold & macd_bullish) |
                (bb_oversold & ma_bullish) |
                (macd_bullish & ma_bullish)
            )
            
            sell_signals = (
                (rsi_overbought & macd_bearish) |
                (bb_overbought & ma_bearish) |
                (macd_bearish & ma_bearish)
            )
            
            df.loc[buy_signals, 'signal'] = 1
            df.loc[sell_signals, 'signal'] = -1
            
            # Calculate signal strength
            df['signal_strength'] = np.abs(
                (df['rsi'] / 100) * 0.3 +
                (np.abs(df['macd']) / df['close']) * 0.4 +
                (df['bb_width']) * 0.3
            )
            
            logger.debug("Calculated trading signals")
            return df
            
        except Exception as e:
            logger.error(f"Failed to calculate signals: {e}")
            raise
    
    def get_market_summary(self, df: pd.DataFrame) -> Dict[str, float]:
        """Get a summary of current market conditions."""
        try:
            latest = df.iloc[-1]
            
            summary = {
                'current_price': float(latest['close']),
                'price_change_24h': float((latest['close'] - df.iloc[-24]['close']) / df.iloc[-24]['close'] * 100) if len(df) >= 24 else 0,
                'volume_24h': float(df['volume'].tail(24).sum()) if len(df) >= 24 else float(latest['volume']),
                'rsi': float(latest['rsi']) if not pd.isna(latest['rsi']) else 50,
                'macd': float(latest['macd']) if not pd.isna(latest['macd']) else 0,
                'bb_position': float((latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower'])) if not pd.isna(latest['bb_lower']) else 0.5,
                'signal': int(latest['signal']),
                'signal_strength': float(latest['signal_strength']) if not pd.isna(latest['signal_strength']) else 0,
                'support_level': float(latest['support']) if not pd.isna(latest['support']) else float(latest['close']) * 0.95,
                'resistance_level': float(latest['resistance']) if not pd.isna(latest['resistance']) else float(latest['close']) * 1.05,
            }
            
            logger.debug("Generated market summary")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate market summary: {e}")
            raise
    
    def analyze_trend(self, df: pd.DataFrame, periods: int = 20) -> Dict[str, str]:
        """Analyze market trend over specified periods."""
        try:
            if len(df) < periods:
                return {'trend': 'insufficient_data', 'strength': 'unknown'}
            
            recent_data = df.tail(periods)
            
            # Price trend
            price_slope = np.polyfit(range(len(recent_data)), recent_data['close'], 1)[0]
            
            # Moving average trend
            sma_slope = np.polyfit(range(len(recent_data)), recent_data['sma_20'], 1)[0] if 'sma_20' in recent_data.columns else 0
            
            # Determine trend
            if price_slope > 0 and sma_slope > 0:
                trend = 'bullish'
            elif price_slope < 0 and sma_slope < 0:
                trend = 'bearish'
            else:
                trend = 'sideways'
            
            # Determine strength
            price_volatility = recent_data['close'].std() / recent_data['close'].mean()
            if price_volatility < 0.02:
                strength = 'weak'
            elif price_volatility < 0.05:
                strength = 'moderate'
            else:
                strength = 'strong'
            
            result = {
                'trend': trend,
                'strength': strength,
                'price_slope': float(price_slope),
                'volatility': float(price_volatility)
            }
            
            logger.debug(f"Trend analysis: {trend} ({strength})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze trend: {e}")
            raise
    
    def find_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Tuple[List[float], List[float]]:
        """Find support and resistance levels."""
        try:
            highs = df['high'].rolling(window=window).max()
            lows = df['low'].rolling(window=window).min()
            
            # Find local maxima and minima
            resistance_levels = []
            support_levels = []
            
            for i in range(window, len(df) - window):
                if df['high'].iloc[i] == highs.iloc[i]:
                    resistance_levels.append(float(df['high'].iloc[i]))
                
                if df['low'].iloc[i] == lows.iloc[i]:
                    support_levels.append(float(df['low'].iloc[i]))
            
            # Remove duplicates and sort
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)[:5]
            support_levels = sorted(list(set(support_levels)))[:5]
            
            logger.debug(f"Found {len(support_levels)} support and {len(resistance_levels)} resistance levels")
            return support_levels, resistance_levels
            
        except Exception as e:
            logger.error(f"Failed to find support/resistance levels: {e}")
            raise