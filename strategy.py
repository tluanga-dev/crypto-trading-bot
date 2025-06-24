from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
from loguru import logger
from data_analyzer import DataAnalyzer
from config import Config

class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, name: str):
        self.name = name
        self.analyzer = DataAnalyzer()
        self.active_positions = []
        
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Dict[str, any]:
        """Generate trading signal based on market data."""
        pass
    
    @abstractmethod
    def should_enter_position(self, df: pd.DataFrame) -> bool:
        """Determine if strategy should enter a new position."""
        pass
    
    @abstractmethod
    def should_exit_position(self, df: pd.DataFrame, position: Dict) -> bool:
        """Determine if strategy should exit an existing position."""
        pass
    
    def calculate_position_size(self, balance: float, risk_percentage: float = None) -> float:
        """Calculate position size based on risk management rules."""
        if risk_percentage is None:
            risk_percentage = Config.MAX_POSITION_SIZE
        
        return balance * (risk_percentage / 100)


class RSIMACDStrategy(BaseStrategy):
    """Strategy based on RSI and MACD indicators."""
    
    def __init__(self):
        super().__init__("RSI_MACD_Strategy")
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        
    def generate_signal(self, df: pd.DataFrame) -> Dict[str, any]:
        """Generate signal based on RSI and MACD."""
        try:
            if len(df) < 50:  # Need enough data for indicators
                return {'action': 'hold', 'confidence': 0, 'reason': 'insufficient_data'}
            
            latest = df.iloc[-1]
            previous = df.iloc[-2]
            
            # RSI conditions
            rsi_oversold = latest['rsi'] < self.rsi_oversold
            rsi_overbought = latest['rsi'] > self.rsi_overbought
            rsi_recovering = previous['rsi'] < self.rsi_oversold and latest['rsi'] > self.rsi_oversold
            rsi_declining = previous['rsi'] > self.rsi_overbought and latest['rsi'] < self.rsi_overbought
            
            # MACD conditions
            macd_bullish_cross = (latest['macd'] > latest['macd_signal'] and 
                                previous['macd'] <= previous['macd_signal'])
            macd_bearish_cross = (latest['macd'] < latest['macd_signal'] and 
                                previous['macd'] >= previous['macd_signal'])
            
            # Price above/below moving averages
            price_above_sma20 = latest['close'] > latest['sma_20']
            price_below_sma20 = latest['close'] < latest['sma_20']
            
            # Generate signals
            buy_conditions = [
                rsi_recovering and macd_bullish_cross,
                rsi_oversold and price_above_sma20 and latest['macd'] > latest['macd_signal'],
                macd_bullish_cross and price_above_sma20 and latest['rsi'] < 50
            ]
            
            sell_conditions = [
                rsi_declining and macd_bearish_cross,
                rsi_overbought and price_below_sma20 and latest['macd'] < latest['macd_signal'],
                macd_bearish_cross and price_below_sma20 and latest['rsi'] > 50
            ]
            
            if any(buy_conditions):
                confidence = self._calculate_confidence(df, 'buy')
                return {
                    'action': 'buy',
                    'confidence': confidence,
                    'reason': 'RSI_MACD_bullish_signal',
                    'entry_price': latest['close'],
                    'stop_loss': latest['close'] * (1 - Config.STOP_LOSS_PERCENTAGE / 100),
                    'take_profit': latest['close'] * (1 + Config.TAKE_PROFIT_PERCENTAGE / 100)
                }
            
            elif any(sell_conditions):
                confidence = self._calculate_confidence(df, 'sell')
                return {
                    'action': 'sell',
                    'confidence': confidence,
                    'reason': 'RSI_MACD_bearish_signal',
                    'entry_price': latest['close'],
                    'stop_loss': latest['close'] * (1 + Config.STOP_LOSS_PERCENTAGE / 100),
                    'take_profit': latest['close'] * (1 - Config.TAKE_PROFIT_PERCENTAGE / 100)
                }
            
            else:
                return {
                    'action': 'hold',
                    'confidence': 0,
                    'reason': 'no_clear_signal'
                }
                
        except Exception as e:
            logger.error(f"Error generating RSI MACD signal: {e}")
            return {'action': 'hold', 'confidence': 0, 'reason': 'error'}
    
    def should_enter_position(self, df: pd.DataFrame) -> bool:
        """Check if should enter new position."""
        signal = self.generate_signal(df)
        return signal['action'] in ['buy', 'sell'] and signal['confidence'] > 0.6
    
    def should_exit_position(self, df: pd.DataFrame, position: Dict) -> bool:
        """Check if should exit existing position."""
        latest_price = df.iloc[-1]['close']
        entry_price = position['entry_price']
        position_type = position['side']
        
        # Stop loss check
        if position_type == 'buy':
            stop_loss_triggered = latest_price <= position.get('stop_loss', entry_price * 0.95)
            take_profit_triggered = latest_price >= position.get('take_profit', entry_price * 1.05)
        else:  # sell position
            stop_loss_triggered = latest_price >= position.get('stop_loss', entry_price * 1.05)
            take_profit_triggered = latest_price <= position.get('take_profit', entry_price * 0.95)
        
        # Signal reversal check
        current_signal = self.generate_signal(df)
        signal_reversal = (
            (position_type == 'buy' and current_signal['action'] == 'sell') or
            (position_type == 'sell' and current_signal['action'] == 'buy')
        ) and current_signal['confidence'] > 0.7
        
        return stop_loss_triggered or take_profit_triggered or signal_reversal
    
    def _calculate_confidence(self, df: pd.DataFrame, action: str) -> float:
        """Calculate confidence score for the signal."""
        try:
            latest = df.iloc[-1]
            
            # Base confidence factors
            rsi_factor = 0.3
            macd_factor = 0.4
            trend_factor = 0.3
            
            confidence = 0.0
            
            if action == 'buy':
                # RSI confidence (higher when oversold and recovering)
                if latest['rsi'] < 40:
                    confidence += rsi_factor * (40 - latest['rsi']) / 40
                
                # MACD confidence (higher when MACD > signal and growing)
                if latest['macd'] > latest['macd_signal']:
                    confidence += macd_factor
                
                # Trend confidence (higher when price above moving averages)
                if latest['close'] > latest['sma_20']:
                    confidence += trend_factor
            
            elif action == 'sell':
                # RSI confidence (higher when overbought and declining)
                if latest['rsi'] > 60:
                    confidence += rsi_factor * (latest['rsi'] - 60) / 40
                
                # MACD confidence (higher when MACD < signal and declining)
                if latest['macd'] < latest['macd_signal']:
                    confidence += macd_factor
                
                # Trend confidence (higher when price below moving averages)
                if latest['close'] < latest['sma_20']:
                    confidence += trend_factor
            
            return min(confidence, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.0


class BollingerBandStrategy(BaseStrategy):
    """Strategy based on Bollinger Bands mean reversion."""
    
    def __init__(self):
        super().__init__("Bollinger_Band_Strategy")
        
    def generate_signal(self, df: pd.DataFrame) -> Dict[str, any]:
        """Generate signal based on Bollinger Bands."""
        try:
            if len(df) < 20:
                return {'action': 'hold', 'confidence': 0, 'reason': 'insufficient_data'}
            
            latest = df.iloc[-1]
            
            # Calculate position within Bollinger Bands
            bb_position = ((latest['close'] - latest['bb_lower']) / 
                          (latest['bb_upper'] - latest['bb_lower']))
            
            # Band width for volatility assessment
            bb_width = latest['bb_width']
            
            # Generate signals based on position and volatility
            if bb_position < 0.2 and bb_width > 0.02:  # Near lower band with good volatility
                return {
                    'action': 'buy',
                    'confidence': min(0.8, (0.2 - bb_position) * 4 + bb_width * 10),
                    'reason': 'bollinger_oversold',
                    'entry_price': latest['close'],
                    'stop_loss': latest['bb_lower'] * 0.99,
                    'take_profit': latest['bb_middle']
                }
            
            elif bb_position > 0.8 and bb_width > 0.02:  # Near upper band with good volatility
                return {
                    'action': 'sell',
                    'confidence': min(0.8, (bb_position - 0.8) * 4 + bb_width * 10),
                    'reason': 'bollinger_overbought',
                    'entry_price': latest['close'],
                    'stop_loss': latest['bb_upper'] * 1.01,
                    'take_profit': latest['bb_middle']
                }
            
            else:
                return {'action': 'hold', 'confidence': 0, 'reason': 'within_normal_range'}
                
        except Exception as e:
            logger.error(f"Error generating Bollinger Band signal: {e}")
            return {'action': 'hold', 'confidence': 0, 'reason': 'error'}
    
    def should_enter_position(self, df: pd.DataFrame) -> bool:
        """Check if should enter new position."""
        signal = self.generate_signal(df)
        return signal['action'] in ['buy', 'sell'] and signal['confidence'] > 0.5
    
    def should_exit_position(self, df: pd.DataFrame, position: Dict) -> bool:
        """Check if should exit existing position."""
        latest = df.iloc[-1]
        
        # Exit when price returns to middle band (take profit)
        if position['side'] == 'buy':
            return latest['close'] >= latest['bb_middle']
        else:
            return latest['close'] <= latest['bb_middle']


class StrategyManager:
    """Manager for handling multiple trading strategies."""
    
    def __init__(self):
        self.strategies = {
            'rsi_macd': RSIMACDStrategy(),
            'bollinger': BollingerBandStrategy()
        }
        self.active_strategy = 'rsi_macd'
        
    def set_active_strategy(self, strategy_name: str):
        """Set the active trading strategy."""
        if strategy_name in self.strategies:
            self.active_strategy = strategy_name
            logger.info(f"Active strategy set to: {strategy_name}")
        else:
            logger.error(f"Strategy '{strategy_name}' not found")
            raise ValueError(f"Strategy '{strategy_name}' not available")
    
    def get_signal(self, df: pd.DataFrame) -> Dict[str, any]:
        """Get signal from active strategy."""
        return self.strategies[self.active_strategy].generate_signal(df)
    
    def should_enter_position(self, df: pd.DataFrame) -> bool:
        """Check if active strategy suggests entering position."""
        return self.strategies[self.active_strategy].should_enter_position(df)
    
    def should_exit_position(self, df: pd.DataFrame, position: Dict) -> bool:
        """Check if active strategy suggests exiting position."""
        return self.strategies[self.active_strategy].should_exit_position(df, position)
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategies."""
        return list(self.strategies.keys())
    
    def add_custom_strategy(self, name: str, strategy: BaseStrategy):
        """Add a custom strategy to the manager."""
        self.strategies[name] = strategy
        logger.info(f"Added custom strategy: {name}")
    
    def backtest_strategy(self, df: pd.DataFrame, strategy_name: str = None) -> Dict[str, any]:
        """Simple backtest of strategy performance."""
        try:
            if strategy_name:
                strategy = self.strategies.get(strategy_name)
            else:
                strategy = self.strategies[self.active_strategy]
            
            if not strategy:
                raise ValueError(f"Strategy not found: {strategy_name}")
            
            # Simple backtest logic
            signals = []
            for i in range(50, len(df)):  # Start after enough data for indicators
                window_df = df.iloc[:i+1]
                signal = strategy.generate_signal(window_df)
                signals.append({
                    'timestamp': df.index[i],
                    'price': df.iloc[i]['close'],
                    'signal': signal
                })
            
            # Calculate performance metrics
            total_signals = len([s for s in signals if s['signal']['action'] != 'hold'])
            buy_signals = len([s for s in signals if s['signal']['action'] == 'buy'])
            sell_signals = len([s for s in signals if s['signal']['action'] == 'sell'])
            
            return {
                'strategy': strategy.name,
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'signal_frequency': total_signals / len(signals) if signals else 0,
                'avg_confidence': sum([s['signal']['confidence'] for s in signals]) / len(signals) if signals else 0
            }
            
        except Exception as e:
            logger.error(f"Error in backtest: {e}")
            return {'error': str(e)}