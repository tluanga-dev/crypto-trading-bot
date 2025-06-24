from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime
from loguru import logger
from config import Config

class Position:
    """Represents a trading position."""
    
    def __init__(self, symbol: str, side: str, quantity: float, entry_price: float, 
                 stop_loss: Optional[float] = None, take_profit: Optional[float] = None):
        self.symbol = symbol
        self.side = side  # 'buy' or 'sell'
        self.quantity = quantity
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_time = datetime.now()
        self.exit_time = None
        self.exit_price = None
        self.pnl = 0.0
        self.status = 'open'  # 'open', 'closed'
        
    def update_pnl(self, current_price: float):
        """Update unrealized PnL based on current price."""
        if self.side == 'buy':
            self.pnl = (current_price - self.entry_price) * self.quantity
        else:  # sell position
            self.pnl = (self.entry_price - current_price) * self.quantity
    
    def close_position(self, exit_price: float):
        """Close the position."""
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.status = 'closed'
        self.update_pnl(exit_price)
        
    def to_dict(self) -> Dict:
        """Convert position to dictionary."""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl': self.pnl,
            'status': self.status
        }


class RiskManager:
    """Risk management system for trading operations."""
    
    def __init__(self, initial_balance: float):
        self.initial_balance = initial_balance
        self.max_position_size = Config.MAX_POSITION_SIZE / 100  # Convert to decimal
        self.max_daily_loss = 0.05  # 5% max daily loss
        self.max_drawdown = 0.15  # 15% max drawdown
        self.daily_loss = 0.0
        self.max_open_positions = 3
        
    def calculate_position_size(self, balance: float, signal_confidence: float) -> float:
        """Calculate appropriate position size based on risk parameters."""
        # Base position size
        base_size = balance * self.max_position_size
        
        # Adjust based on signal confidence
        confidence_multiplier = min(signal_confidence, 1.0)
        
        # Reduce size if daily loss is significant
        loss_reduction = max(0.3, 1.0 - (self.daily_loss / self.max_daily_loss))
        
        position_size = base_size * confidence_multiplier * loss_reduction
        
        logger.debug(f"Calculated position size: {position_size} (confidence: {signal_confidence}, loss reduction: {loss_reduction})")
        return position_size
    
    def should_allow_trade(self, balance: float, open_positions: int, proposed_size: float) -> Tuple[bool, str]:
        """Check if trade should be allowed based on risk parameters."""
        # Check maximum open positions
        if open_positions >= self.max_open_positions:
            return False, f"Maximum open positions ({self.max_open_positions}) reached"
        
        # Check daily loss limit
        if self.daily_loss >= self.max_daily_loss:
            return False, f"Daily loss limit ({self.max_daily_loss*100}%) exceeded"
        
        # Check maximum drawdown
        drawdown = (self.initial_balance - balance) / self.initial_balance
        if drawdown >= self.max_drawdown:
            return False, f"Maximum drawdown ({self.max_drawdown*100}%) exceeded"
        
        # Check if position size is reasonable
        if proposed_size > balance * self.max_position_size:
            return False, f"Position size too large (max: {self.max_position_size*100}% of balance)"
        
        return True, "Trade allowed"
    
    def update_daily_loss(self, loss: float):
        """Update daily loss tracking."""
        if loss > 0:  # Only track losses
            self.daily_loss += loss / self.initial_balance


class Portfolio:
    """Portfolio management system."""
    
    def __init__(self, initial_balance: float):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions: List[Position] = []
        self.trade_history: List[Dict] = []
        self.risk_manager = RiskManager(initial_balance)
        
    def add_position(self, position: Position):
        """Add a new position to the portfolio."""
        self.positions.append(position)
        logger.info(f"Added position: {position.symbol} {position.side} {position.quantity} @ {position.entry_price}")
    
    def close_position(self, symbol: str, exit_price: float) -> Optional[Position]:
        """Close a position by symbol."""
        for position in self.positions:
            if position.symbol == symbol and position.status == 'open':
                position.close_position(exit_price)
                
                # Update balance
                self.current_balance += position.pnl
                
                # Add to trade history
                self.trade_history.append(position.to_dict())
                
                # Update risk manager
                if position.pnl < 0:
                    self.risk_manager.update_daily_loss(abs(position.pnl))
                
                logger.info(f"Closed position: {position.symbol} PnL: {position.pnl:.4f}")
                return position
        
        logger.warning(f"No open position found for {symbol}")
        return None
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return [pos for pos in self.positions if pos.status == 'open']
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """Get open position by symbol."""
        for position in self.positions:
            if position.symbol == symbol and position.status == 'open':
                return position
        return None
    
    def update_positions_pnl(self, prices: Dict[str, float]):
        """Update PnL for all open positions."""
        for position in self.get_open_positions():
            if position.symbol in prices:
                position.update_pnl(prices[position.symbol])
    
    def get_total_pnl(self) -> float:
        """Get total unrealized PnL."""
        return sum(pos.pnl for pos in self.get_open_positions())
    
    def get_portfolio_value(self) -> float:
        """Get current portfolio value including unrealized PnL."""
        return self.current_balance + self.get_total_pnl()
    
    def calculate_position_size(self, signal_confidence: float) -> float:
        """Calculate position size for new trade."""
        return self.risk_manager.calculate_position_size(
            self.get_portfolio_value(), signal_confidence
        )
    
    def can_open_position(self, proposed_size: float) -> Tuple[bool, str]:
        """Check if new position can be opened."""
        return self.risk_manager.should_allow_trade(
            self.get_portfolio_value(),
            len(self.get_open_positions()),
            proposed_size
        )
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate portfolio performance metrics."""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'total_return': 0.0
            }
        
        trades = [trade for trade in self.trade_history if trade['status'] == 'closed']
        pnls = [trade['pnl'] for trade in trades]
        
        winning_trades = [pnl for pnl in pnls if pnl > 0]
        losing_trades = [pnl for pnl in pnls if pnl < 0]
        
        total_pnl = sum(pnls)
        total_wins = sum(winning_trades) if winning_trades else 0
        total_losses = abs(sum(losing_trades)) if losing_trades else 0
        
        # Calculate drawdown
        running_pnl = 0
        peak = self.initial_balance
        max_drawdown = 0
        
        for pnl in pnls:
            running_pnl += pnl
            current_value = self.initial_balance + running_pnl
            
            if current_value > peak:
                peak = current_value
            
            drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades) if trades else 0,
            'total_pnl': total_pnl,
            'avg_win': sum(winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_loss': sum(losing_trades) / len(losing_trades) if losing_trades else 0,
            'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': self._calculate_sharpe_ratio(pnls),
            'total_return': (self.get_portfolio_value() - self.initial_balance) / self.initial_balance
        }
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if not returns or len(returns) < 2:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        return_std = pd.Series(returns).std()
        
        if return_std == 0:
            return 0.0
        
        # Annualized Sharpe ratio (assuming daily returns)
        sharpe = (avg_return * 365 - risk_free_rate) / (return_std * (365 ** 0.5))
        return sharpe
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary."""
        open_positions = self.get_open_positions()
        performance = self.get_performance_metrics()
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'unrealized_pnl': self.get_total_pnl(),
            'portfolio_value': self.get_portfolio_value(),
            'open_positions': len(open_positions),
            'open_positions_details': [pos.to_dict() for pos in open_positions],
            'performance_metrics': performance,
            'risk_metrics': {
                'daily_loss': self.risk_manager.daily_loss,
                'max_daily_loss': self.risk_manager.max_daily_loss,
                'max_position_size': self.risk_manager.max_position_size,
                'max_drawdown_limit': self.risk_manager.max_drawdown
            }
        }
    
    def export_trade_history(self, filename: str = None) -> str:
        """Export trade history to CSV."""
        if not filename:
            filename = f"trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if not self.trade_history:
            logger.warning("No trade history to export")
            return filename
        
        df = pd.DataFrame(self.trade_history)
        df.to_csv(filename, index=False)
        logger.info(f"Trade history exported to {filename}")
        return filename