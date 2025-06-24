"""
Professional Order Management System
Advanced order types, risk management, and position sizing for professional trading.
"""

import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
from loguru import logger

from events import get_event_publisher
from config import Config
from demo_client import BinanceClientFactory


class OrderType(Enum):
    """Order types supported by the system."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    OCO = "OCO"  # One-Cancels-Other


class OrderStatus(Enum):
    """Order status states."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderSide(Enum):
    """Order side."""
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(Enum):
    """Time in force options."""
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill


@dataclass
class RiskParameters:
    """Risk management parameters for orders."""
    max_position_size: float = 1000.0  # Maximum position size in quote currency
    max_position_percentage: float = 0.1  # Maximum % of portfolio per position
    stop_loss_percentage: float = 0.02  # Default stop loss %
    take_profit_percentage: float = 0.04  # Default take profit %
    max_daily_loss: float = 100.0  # Maximum daily loss limit
    max_orders_per_symbol: int = 5  # Maximum orders per symbol
    allow_margin: bool = False  # Allow margin trading
    require_confirmation: bool = True  # Require confirmation for large orders


@dataclass
class OrderRequest:
    """Represents an order request before execution."""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    
    # Advanced order parameters
    trailing_delta: Optional[float] = None  # For trailing stops
    parent_order_id: Optional[str] = None  # For OCO orders
    reduce_only: bool = False  # Only reduce position
    
    # Risk management
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    
    # Metadata
    strategy: Optional[str] = None
    notes: Optional[str] = None
    client_order_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class Order:
    """Represents an order in the system."""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    quantity: float
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    avg_fill_price: Optional[float] = None
    
    # Timestamps
    created_time: datetime = field(default_factory=datetime.now)
    submitted_time: Optional[datetime] = None
    filled_time: Optional[datetime] = None
    cancelled_time: Optional[datetime] = None
    
    # Advanced features
    trailing_delta: Optional[float] = None
    parent_order_id: Optional[str] = None
    child_orders: List[str] = field(default_factory=list)
    
    # Risk and metadata
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    strategy: Optional[str] = None
    notes: Optional[str] = None
    
    # Exchange data
    exchange_order_id: Optional[str] = None
    exchange_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.remaining_quantity = self.quantity - self.filled_quantity


class PositionSizer:
    """Calculates optimal position sizes based on risk parameters."""
    
    def __init__(self, risk_params: RiskParameters):
        self.risk_params = risk_params
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              stop_loss_price: Optional[float], 
                              account_balance: float,
                              risk_percentage: float = 0.02) -> Dict[str, float]:
        """
        Calculate optimal position size based on risk management.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price (optional)
            account_balance: Current account balance
            risk_percentage: Percentage of account to risk
        
        Returns:
            Dictionary with position sizing information
        """
        # Maximum risk amount
        max_risk_amount = account_balance * risk_percentage
        
        # Position size based on stop loss
        if stop_loss_price:
            price_diff = abs(entry_price - stop_loss_price)
            risk_per_unit = price_diff
            
            if risk_per_unit > 0:
                optimal_size = max_risk_amount / risk_per_unit
            else:
                optimal_size = 0
        else:
            # Default to 2% stop loss if not specified
            default_stop_pct = self.risk_params.stop_loss_percentage
            risk_per_unit = entry_price * default_stop_pct
            optimal_size = max_risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        
        # Apply maximum position size limits
        max_position_value = min(
            self.risk_params.max_position_size,
            account_balance * self.risk_params.max_position_percentage
        )
        
        max_size_by_value = max_position_value / entry_price
        final_size = min(optimal_size, max_size_by_value)
        
        return {
            'optimal_quantity': optimal_size,
            'max_quantity_by_risk': max_size_by_value,
            'recommended_quantity': final_size,
            'position_value': final_size * entry_price,
            'risk_amount': min(max_risk_amount, risk_per_unit * final_size),
            'risk_percentage': (risk_per_unit * final_size) / account_balance * 100
        }
    
    def calculate_stop_loss_price(self, entry_price: float, side: OrderSide,
                                 stop_loss_percentage: Optional[float] = None) -> float:
        """Calculate stop loss price based on entry price and percentage."""
        stop_pct = stop_loss_percentage or self.risk_params.stop_loss_percentage
        
        if side == OrderSide.BUY:
            return entry_price * (1 - stop_pct)
        else:  # SELL
            return entry_price * (1 + stop_pct)
    
    def calculate_take_profit_price(self, entry_price: float, side: OrderSide,
                                   take_profit_percentage: Optional[float] = None) -> float:
        """Calculate take profit price based on entry price and percentage."""
        tp_pct = take_profit_percentage or self.risk_params.take_profit_percentage
        
        if side == OrderSide.BUY:
            return entry_price * (1 + tp_pct)
        else:  # SELL
            return entry_price * (1 - tp_pct)


class OrderValidator:
    """Validates orders before execution."""
    
    def __init__(self, risk_params: RiskParameters):
        self.risk_params = risk_params
    
    def validate_order(self, order_request: OrderRequest, 
                      current_orders: List[Order],
                      account_balance: float,
                      current_price: float) -> Dict[str, Any]:
        """
        Validate an order request against risk parameters.
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'risk_metrics': {}
        }
        
        # Check maximum orders per symbol
        symbol_orders = [o for o in current_orders if o.symbol == order_request.symbol 
                        and o.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]]
        
        if len(symbol_orders) >= self.risk_params.max_orders_per_symbol:
            validation_result['errors'].append(
                f"Maximum orders per symbol exceeded ({self.risk_params.max_orders_per_symbol})"
            )
            validation_result['is_valid'] = False
        
        # Check position size
        position_value = order_request.quantity * (order_request.price or current_price)
        
        if position_value > self.risk_params.max_position_size:
            validation_result['errors'].append(
                f"Position size exceeds maximum (${position_value:.2f} > ${self.risk_params.max_position_size:.2f})"
            )
            validation_result['is_valid'] = False
        
        # Check percentage of portfolio
        position_percentage = position_value / account_balance
        if position_percentage > self.risk_params.max_position_percentage:
            validation_result['errors'].append(
                f"Position exceeds maximum portfolio percentage ({position_percentage*100:.1f}% > {self.risk_params.max_position_percentage*100:.1f}%)"
            )
            validation_result['is_valid'] = False
        
        # Price validation
        if order_request.price and current_price:
            price_diff_pct = abs(order_request.price - current_price) / current_price
            if price_diff_pct > 0.05:  # 5% difference warning
                validation_result['warnings'].append(
                    f"Order price differs significantly from market price ({price_diff_pct*100:.1f}%)"
                )
        
        # Stop loss validation
        if order_request.stop_loss_price and order_request.price:
            if order_request.side == OrderSide.BUY:
                if order_request.stop_loss_price >= order_request.price:
                    validation_result['errors'].append("Stop loss must be below entry price for BUY orders")
                    validation_result['is_valid'] = False
            else:  # SELL
                if order_request.stop_loss_price <= order_request.price:
                    validation_result['errors'].append("Stop loss must be above entry price for SELL orders")
                    validation_result['is_valid'] = False
        
        # Large order confirmation
        if position_value > account_balance * 0.05 and self.risk_params.require_confirmation:
            validation_result['warnings'].append(
                f"Large order requires confirmation (${position_value:.2f})"
            )
        
        # Calculate risk metrics
        validation_result['risk_metrics'] = {
            'position_value': position_value,
            'position_percentage': position_percentage * 100,
            'price_deviation': price_diff_pct * 100 if order_request.price and current_price else 0
        }
        
        return validation_result


class OrderManager:
    """
    Professional order management system with advanced order types and risk management.
    """
    
    def __init__(self, binance_client=None, initial_balance: float = 10000.0):
        self.binance_client = binance_client or BinanceClientFactory.create_client()
        self.event_publisher = get_event_publisher()
        
        # Order storage
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        
        # Risk management
        self.risk_params = RiskParameters()
        self.position_sizer = PositionSizer(self.risk_params)
        self.validator = OrderValidator(self.risk_params)
        
        # Account info
        self.account_balance = initial_balance
        self.daily_pnl = 0.0
        self.daily_loss_limit_reached = False
        
        # Order management
        self.order_callbacks: Dict[str, Callable] = {}
        self.is_monitoring = False
        
        logger.info("Order Management System initialized")
    
    def update_risk_parameters(self, **kwargs):
        """Update risk management parameters."""
        for key, value in kwargs.items():
            if hasattr(self.risk_params, key):
                setattr(self.risk_params, key, value)
                logger.info(f"Updated risk parameter {key} to {value}")
    
    async def submit_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """
        Submit an order to the exchange.
        
        Args:
            order_request: Order request object
            
        Returns:
            Dictionary with order submission result
        """
        try:
            # Get current market price for validation
            ticker = self.binance_client.get_symbol_ticker(order_request.symbol)
            current_price = float(ticker.get('price', 0))
            
            # Validate order
            validation = self.validator.validate_order(
                order_request,
                list(self.orders.values()),
                self.account_balance,
                current_price
            )
            
            if not validation['is_valid']:
                return {
                    'success': False,
                    'message': f"Order validation failed: {'; '.join(validation['errors'])}",
                    'validation': validation
                }
            
            # Check daily loss limit
            if self.daily_loss_limit_reached:
                return {
                    'success': False,
                    'message': "Daily loss limit reached. Trading suspended.",
                    'validation': validation
                }
            
            # Create order object
            order = Order(
                order_id=order_request.client_order_id,
                client_order_id=order_request.client_order_id,
                symbol=order_request.symbol,
                side=order_request.side,
                order_type=order_request.order_type,
                status=OrderStatus.PENDING,
                quantity=order_request.quantity,
                price=order_request.price,
                stop_price=order_request.stop_price,
                trailing_delta=order_request.trailing_delta,
                parent_order_id=order_request.parent_order_id,
                strategy=order_request.strategy,
                notes=order_request.notes
            )
            
            # Add to orders
            self.orders[order.order_id] = order
            
            # Submit to exchange (in testnet mode, simulate)
            if Config.TRADING_MODE == "testnet":
                result = await self._simulate_order_submission(order)
            else:
                result = await self._submit_to_exchange(order)
            
            if result['success']:
                order.status = OrderStatus.SUBMITTED
                order.submitted_time = datetime.now()
                order.exchange_order_id = result.get('exchange_order_id')
                order.exchange_data = result.get('exchange_data', {})
                
                # Submit stop loss and take profit orders if specified
                if order_request.stop_loss_price:
                    await self._submit_stop_loss_order(order, order_request.stop_loss_price)
                
                if order_request.take_profit_price:
                    await self._submit_take_profit_order(order, order_request.take_profit_price)
                
                # Publish event
                self.event_publisher.publish_system_event(
                    "order_submitted",
                    f"Order submitted: {order.symbol} {order.side.value} {order.quantity} @ {order.price or 'MARKET'}"
                )
                
                logger.info(f"Order submitted successfully: {order.order_id}")
            else:
                order.status = OrderStatus.REJECTED
                logger.error(f"Order submission failed: {result['message']}")
            
            return {
                'success': result['success'],
                'message': result['message'],
                'order_id': order.order_id,
                'validation': validation,
                'order': order
            }
            
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            return {
                'success': False,
                'message': f"Order submission error: {str(e)}",
                'validation': {}
            }
    
    async def _simulate_order_submission(self, order: Order) -> Dict[str, Any]:
        """Simulate order submission for testnet mode."""
        # Simulate exchange response
        await asyncio.sleep(0.1)  # Simulate network delay
        
        return {
            'success': True,
            'message': 'Order submitted (simulated)',
            'exchange_order_id': f"SIM_{order.order_id[:8]}",
            'exchange_data': {
                'status': 'NEW',
                'timeInForce': 'GTC',
                'transactTime': int(datetime.now().timestamp() * 1000)
            }
        }
    
    async def _submit_to_exchange(self, order: Order) -> Dict[str, Any]:
        """Submit order to actual exchange."""
        try:
            # Convert internal order to Binance format
            binance_order = {
                'symbol': order.symbol,
                'side': order.side.value,
                'type': order.order_type.value,
                'quantity': order.quantity,
                'newClientOrderId': order.client_order_id
            }
            
            # Add price for limit orders
            if order.price and order.order_type in [OrderType.LIMIT, OrderType.STOP_LOSS_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
                binance_order['price'] = order.price
            
            # Add stop price for stop orders
            if order.stop_price and order.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LOSS_LIMIT]:
                binance_order['stopPrice'] = order.stop_price
            
            # Submit to Binance
            response = self.binance_client.create_order(**binance_order)
            
            return {
                'success': True,
                'message': 'Order submitted successfully',
                'exchange_order_id': response.get('orderId'),
                'exchange_data': response
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Exchange submission failed: {str(e)}"
            }
    
    async def _submit_stop_loss_order(self, parent_order: Order, stop_loss_price: float):
        """Submit stop loss order for a parent order."""
        try:
            opposite_side = OrderSide.SELL if parent_order.side == OrderSide.BUY else OrderSide.BUY
            
            stop_order_request = OrderRequest(
                symbol=parent_order.symbol,
                side=opposite_side,
                order_type=OrderType.STOP_LOSS,
                quantity=parent_order.quantity,
                stop_price=stop_loss_price,
                parent_order_id=parent_order.order_id,
                strategy=parent_order.strategy,
                notes=f"Stop loss for {parent_order.order_id}"
            )
            
            result = await self.submit_order(stop_order_request)
            if result['success']:
                parent_order.stop_loss_order_id = result['order_id']
                parent_order.child_orders.append(result['order_id'])
                logger.info(f"Stop loss order submitted for {parent_order.order_id}")
            
        except Exception as e:
            logger.error(f"Failed to submit stop loss order: {e}")
    
    async def _submit_take_profit_order(self, parent_order: Order, take_profit_price: float):
        """Submit take profit order for a parent order."""
        try:
            opposite_side = OrderSide.SELL if parent_order.side == OrderSide.BUY else OrderSide.BUY
            
            tp_order_request = OrderRequest(
                symbol=parent_order.symbol,
                side=opposite_side,
                order_type=OrderType.TAKE_PROFIT,
                quantity=parent_order.quantity,
                price=take_profit_price,
                parent_order_id=parent_order.order_id,
                strategy=parent_order.strategy,
                notes=f"Take profit for {parent_order.order_id}"
            )
            
            result = await self.submit_order(tp_order_request)
            if result['success']:
                parent_order.take_profit_order_id = result['order_id']
                parent_order.child_orders.append(result['order_id'])
                logger.info(f"Take profit order submitted for {parent_order.order_id}")
            
        except Exception as e:
            logger.error(f"Failed to submit take profit order: {e}")
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        try:
            order = self.orders.get(order_id)
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]:
                return {'success': False, 'message': 'Order cannot be cancelled'}
            
            # Cancel on exchange
            if Config.TRADING_MODE == "testnet":
                # Simulate cancellation
                await asyncio.sleep(0.1)
                success = True
            else:
                try:
                    self.binance_client.cancel_order(
                        symbol=order.symbol,
                        orderId=order.exchange_order_id
                    )
                    success = True
                except Exception as e:
                    logger.error(f"Failed to cancel order on exchange: {e}")
                    success = False
            
            if success:
                order.status = OrderStatus.CANCELLED
                order.cancelled_time = datetime.now()
                
                # Cancel child orders (stop loss, take profit)
                for child_order_id in order.child_orders:
                    await self.cancel_order(child_order_id)
                
                self.event_publisher.publish_system_event(
                    "order_cancelled",
                    f"Order cancelled: {order.symbol} {order.side.value} {order.quantity}"
                )
                
                logger.info(f"Order cancelled: {order_id}")
                return {'success': True, 'message': 'Order cancelled successfully'}
            else:
                return {'success': False, 'message': 'Failed to cancel order on exchange'}
                
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {'success': False, 'message': f"Cancellation error: {str(e)}"}
    
    def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get active orders, optionally filtered by symbol."""
        active_statuses = [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
        active_orders = [order for order in self.orders.values() if order.status in active_statuses]
        
        if symbol:
            active_orders = [order for order in active_orders if order.symbol == symbol]
        
        return active_orders
    
    def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Order]:
        """Get order history."""
        history = self.order_history[-limit:] if not symbol else [
            order for order in self.order_history[-limit:] if order.symbol == symbol
        ]
        return history
    
    def calculate_optimal_position(self, symbol: str, entry_price: float,
                                 stop_loss_percentage: Optional[float] = None,
                                 risk_percentage: float = 0.02) -> Dict[str, float]:
        """Calculate optimal position size for a trade."""
        stop_loss_price = None
        if stop_loss_percentage:
            stop_loss_price = entry_price * (1 - stop_loss_percentage)
        
        return self.position_sizer.calculate_position_size(
            symbol, entry_price, stop_loss_price, self.account_balance, risk_percentage
        )
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        active_orders = self.get_active_orders()
        total_exposure = sum(
            order.quantity * (order.price or 0) for order in active_orders
        )
        
        return {
            'account_balance': self.account_balance,
            'active_orders_count': len(active_orders),
            'total_exposure': total_exposure,
            'exposure_percentage': (total_exposure / self.account_balance * 100) if self.account_balance > 0 else 0,
            'daily_pnl': self.daily_pnl,
            'daily_loss_limit': self.risk_params.max_daily_loss,
            'daily_loss_limit_reached': self.daily_loss_limit_reached,
            'risk_parameters': self.risk_params
        }


# Singleton instance
_order_manager: Optional[OrderManager] = None

def get_order_manager() -> OrderManager:
    """Get the singleton order manager."""
    global _order_manager
    if _order_manager is None:
        _order_manager = OrderManager()
    return _order_manager