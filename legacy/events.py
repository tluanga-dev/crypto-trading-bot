"""
Event-driven system for the cryptocurrency trading application.
Enables loose coupling between core trading service and UI interfaces.
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
from loguru import logger
from collections import defaultdict
import weakref
import threading

from models import (
    TradingEvent, MarketDataEvent, SignalGeneratedEvent, 
    PositionOpenedEvent, PositionClosedEvent, RiskEvent, SystemEvent
)

class EventBus:
    """
    Thread-safe event bus for publishing and subscribing to trading events.
    Supports both synchronous and asynchronous event handlers.
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._async_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self._event_history: List[TradingEvent] = []
        self._max_history = 1000
        
    def subscribe(self, event_type: str, handler: Callable[[TradingEvent], None]):
        """Subscribe to events of a specific type with a synchronous handler."""
        with self._lock:
            # Use weak reference to prevent memory leaks
            if hasattr(handler, '__self__'):
                # Method - use weak reference
                weak_handler = weakref.WeakMethod(handler)
                self._subscribers[event_type].append(weak_handler)
            else:
                # Function - use weak reference
                weak_handler = weakref.ref(handler)
                self._subscribers[event_type].append(weak_handler)
        
        logger.debug(f"Subscribed to event type: {event_type}")
    
    def subscribe_async(self, event_type: str, handler: Callable[[TradingEvent], None]):
        """Subscribe to events of a specific type with an asynchronous handler."""
        with self._lock:
            if hasattr(handler, '__self__'):
                weak_handler = weakref.WeakMethod(handler)
                self._async_subscribers[event_type].append(weak_handler)
            else:
                weak_handler = weakref.ref(handler)
                self._async_subscribers[event_type].append(weak_handler)
        
        logger.debug(f"Subscribed to async event type: {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from events of a specific type."""
        with self._lock:
            # Remove from sync subscribers
            self._subscribers[event_type] = [
                ref for ref in self._subscribers[event_type]
                if ref() is not handler
            ]
            
            # Remove from async subscribers
            self._async_subscribers[event_type] = [
                ref for ref in self._async_subscribers[event_type]
                if ref() is not handler
            ]
        
        logger.debug(f"Unsubscribed from event type: {event_type}")
    
    def publish(self, event: TradingEvent):
        """Publish an event to all subscribers."""
        try:
            # Add to history
            with self._lock:
                self._event_history.append(event)
                if len(self._event_history) > self._max_history:
                    self._event_history.pop(0)
            
            # Notify synchronous subscribers
            self._notify_sync_subscribers(event)
            
            # Notify asynchronous subscribers
            asyncio.create_task(self._notify_async_subscribers(event))
            
        except Exception as e:
            logger.error(f"Error publishing event {event.event_type}: {e}")
    
    def _notify_sync_subscribers(self, event: TradingEvent):
        """Notify synchronous subscribers."""
        dead_refs = []
        
        with self._lock:
            subscribers = self._subscribers.get(event.event_type, []).copy()
        
        for weak_ref in subscribers:
            handler = weak_ref()
            if handler is None:
                dead_refs.append(weak_ref)
                continue
            
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in sync event handler for {event.event_type}: {e}")
        
        # Clean up dead references
        if dead_refs:
            with self._lock:
                for dead_ref in dead_refs:
                    if dead_ref in self._subscribers[event.event_type]:
                        self._subscribers[event.event_type].remove(dead_ref)
    
    async def _notify_async_subscribers(self, event: TradingEvent):
        """Notify asynchronous subscribers."""
        dead_refs = []
        
        with self._lock:
            subscribers = self._async_subscribers.get(event.event_type, []).copy()
        
        for weak_ref in subscribers:
            handler = weak_ref()
            if handler is None:
                dead_refs.append(weak_ref)
                continue
            
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in async event handler for {event.event_type}: {e}")
        
        # Clean up dead references
        if dead_refs:
            with self._lock:
                for dead_ref in dead_refs:
                    if dead_ref in self._async_subscribers[event.event_type]:
                        self._async_subscribers[event.event_type].remove(dead_ref)
    
    def get_event_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[TradingEvent]:
        """Get recent event history, optionally filtered by event type."""
        with self._lock:
            events = self._event_history[-limit:] if not event_type else [
                event for event in self._event_history[-limit:]
                if event.event_type == event_type
            ]
        return events
    
    def clear_history(self):
        """Clear event history."""
        with self._lock:
            self._event_history.clear()
        logger.info("Event history cleared")

class EventPublisher:
    """
    Helper class for publishing specific types of trading events.
    Used by the core trading service to emit events.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    def publish_market_data(self, symbol: str, price: float, volume: Optional[float] = None, timestamp: Optional[datetime] = None):
        """Publish market data update event."""
        event = MarketDataEvent(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=timestamp or datetime.now(),
            data={"symbol": symbol, "price": price, "volume": volume}
        )
        self.event_bus.publish(event)
    
    def publish_kline_data(self, symbol: str, interval: str, open_price: float, high_price: float, 
                          low_price: float, close_price: float, volume: float, timestamp: datetime):
        """Publish kline/candlestick data event."""
        event = TradingEvent(
            event_type="kline_data",
            timestamp=timestamp,
            data={
                "symbol": symbol,
                "interval": interval,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "timestamp": timestamp
            }
        )
        self.event_bus.publish(event)
    
    def publish_order_book_update(self, symbol: str, bids: List[tuple], asks: List[tuple], timestamp: datetime):
        """Publish order book update event."""
        event = TradingEvent(
            event_type="order_book_update",
            timestamp=timestamp,
            data={
                "symbol": symbol,
                "bids": bids,
                "asks": asks,
                "timestamp": timestamp
            }
        )
        self.event_bus.publish(event)
    
    def publish_trade_data(self, symbol: str, price: float, quantity: float, is_buyer_maker: bool, timestamp: datetime):
        """Publish individual trade data event."""
        event = TradingEvent(
            event_type="trade_data",
            timestamp=timestamp,
            data={
                "symbol": symbol,
                "price": price,
                "quantity": quantity,
                "is_buyer_maker": is_buyer_maker,
                "timestamp": timestamp
            }
        )
        self.event_bus.publish(event)
    
    def publish_signal_generated(self, symbol: str, signal: Any):
        """Publish trading signal generated event."""
        event = SignalGeneratedEvent(
            symbol=symbol,
            signal=signal,
            timestamp=datetime.now(),
            data={"symbol": symbol, "signal": signal.dict() if hasattr(signal, 'dict') else signal}
        )
        self.event_bus.publish(event)
    
    def publish_position_opened(self, position: Any):
        """Publish position opened event."""
        event = PositionOpenedEvent(
            position=position,
            timestamp=datetime.now(),
            data={"position": position.dict() if hasattr(position, 'dict') else position}
        )
        self.event_bus.publish(event)
    
    def publish_position_closed(self, position: Any):
        """Publish position closed event."""
        event = PositionClosedEvent(
            position=position,
            timestamp=datetime.now(),
            data={"position": position.dict() if hasattr(position, 'dict') else position}
        )
        self.event_bus.publish(event)
    
    def publish_risk_event(self, risk_type: str, message: str, severity: str = "warning"):
        """Publish risk management event."""
        event = RiskEvent(
            risk_type=risk_type,
            message=message,
            severity=severity,
            timestamp=datetime.now(),
            data={"risk_type": risk_type, "message": message, "severity": severity}
        )
        self.event_bus.publish(event)
    
    def publish_system_event(self, system_action: str, message: str):
        """Publish system event."""
        event = SystemEvent(
            system_action=system_action,
            message=message,
            timestamp=datetime.now(),
            data={"system_action": system_action, "message": message}
        )
        self.event_bus.publish(event)

class EventSubscriber:
    """
    Helper class for subscribing to trading events.
    Used by UI interfaces to receive updates from the core trading service.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._handlers = []  # Keep references to prevent garbage collection
    
    def on_market_data(self, handler: Callable[[MarketDataEvent], None], async_handler: bool = False):
        """Subscribe to market data events."""
        self._handlers.append(handler)
        if async_handler:
            self.event_bus.subscribe_async("market_data", handler)
        else:
            self.event_bus.subscribe("market_data", handler)
    
    def on_signal_generated(self, handler: Callable[[SignalGeneratedEvent], None], async_handler: bool = False):
        """Subscribe to signal generated events."""
        self._handlers.append(handler)
        if async_handler:
            self.event_bus.subscribe_async("signal_generated", handler)
        else:
            self.event_bus.subscribe("signal_generated", handler)
    
    def on_position_opened(self, handler: Callable[[PositionOpenedEvent], None], async_handler: bool = False):
        """Subscribe to position opened events."""
        self._handlers.append(handler)
        if async_handler:
            self.event_bus.subscribe_async("position_opened", handler)
        else:
            self.event_bus.subscribe("position_opened", handler)
    
    def on_position_closed(self, handler: Callable[[PositionClosedEvent], None], async_handler: bool = False):
        """Subscribe to position closed events."""
        self._handlers.append(handler)
        if async_handler:
            self.event_bus.subscribe_async("position_closed", handler)
        else:
            self.event_bus.subscribe("position_closed", handler)
    
    def on_risk_event(self, handler: Callable[[RiskEvent], None], async_handler: bool = False):
        """Subscribe to risk events."""
        self._handlers.append(handler)
        if async_handler:
            self.event_bus.subscribe_async("risk_event", handler)
        else:
            self.event_bus.subscribe("risk_event", handler)
    
    def on_system_event(self, handler: Callable[[SystemEvent], None], async_handler: bool = False):
        """Subscribe to system events."""
        self._handlers.append(handler)
        if async_handler:
            self.event_bus.subscribe_async("system_event", handler)
        else:
            self.event_bus.subscribe("system_event", handler)
    
    def on_kline_data(self, handler: Callable[[TradingEvent], None], async_handler: bool = False):
        """Subscribe to kline/candlestick data events."""
        self._handlers.append(handler)
        if async_handler:
            self.event_bus.subscribe_async("kline_data", handler)
        else:
            self.event_bus.subscribe("kline_data", handler)
    
    def on_order_book_update(self, handler: Callable[[TradingEvent], None], async_handler: bool = False):
        """Subscribe to order book update events."""
        self._handlers.append(handler)
        if async_handler:
            self.event_bus.subscribe_async("order_book_update", handler)
        else:
            self.event_bus.subscribe("order_book_update", handler)
    
    def on_trade_data(self, handler: Callable[[TradingEvent], None], async_handler: bool = False):
        """Subscribe to individual trade data events."""
        self._handlers.append(handler)
        if async_handler:
            self.event_bus.subscribe_async("trade_data", handler)
        else:
            self.event_bus.subscribe("trade_data", handler)
    
    def unsubscribe_all(self):
        """Unsubscribe from all events."""
        for handler in self._handlers:
            for event_type in ["market_data", "signal_generated", "position_opened", 
                             "position_closed", "risk_event", "system_event",
                             "kline_data", "order_book_update", "trade_data"]:
                self.event_bus.unsubscribe(event_type, handler)
        self._handlers.clear()

# Global event bus instance
_global_event_bus = None

def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus

def get_event_publisher() -> EventPublisher:
    """Get an event publisher instance."""
    return EventPublisher(get_event_bus())

def get_event_subscriber() -> EventSubscriber:
    """Get an event subscriber instance."""
    return EventSubscriber(get_event_bus())

# Event type constants for easy reference
class EventTypes:
    """Event type constants."""
    MARKET_DATA = "market_data"
    SIGNAL_GENERATED = "signal_generated"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    RISK_EVENT = "risk_event"
    SYSTEM_EVENT = "system_event"
    KLINE_DATA = "kline_data"
    ORDER_BOOK_UPDATE = "order_book_update"
    TRADE_DATA = "trade_data"