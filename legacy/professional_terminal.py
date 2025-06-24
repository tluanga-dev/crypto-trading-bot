"""
Professional Trading Terminal
Fox Pro-style trading terminal with real-time data, advanced charting, order management, and market scanning.
"""

import asyncio
import sys
import time
import select
import termios
import tty
from typing import Dict, Optional, List
from datetime import datetime
import json

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.prompt import Confirm, Prompt, FloatPrompt
from rich.columns import Columns

# Import all our professional modules
from websocket_manager import get_websocket_manager
from market_depth import get_market_depth_visualizer
from multi_symbol_monitor import get_multi_symbol_monitor, ScanCriteria, SymbolFilter
from watchlist_ui import get_watchlist_visualizer
from advanced_charting import get_advanced_chart_renderer, CandleData
from order_management import get_order_manager, OrderRequest, OrderType, OrderSide, TimeInForce

# Import existing modules
from trading_service import create_trading_service
from events import get_event_subscriber
from config import Config
from logger import get_logger

# Initialize
console = Console()
logger = get_logger("professional_terminal")


class ProfessionalTradingTerminal:
    """
    Professional trading terminal similar to Fox Pro.
    Features real-time data, advanced charting, order management, and market scanning.
    """
    
    def __init__(self, initial_balance: float = 10000.0):
        # Core services
        self.trading_service = create_trading_service(initial_balance)
        self.ws_manager = get_websocket_manager()
        self.multi_symbol_monitor = get_multi_symbol_monitor()
        self.order_manager = get_order_manager()
        
        # UI components
        self.market_depth_viz = get_market_depth_visualizer()
        self.watchlist_viz = get_watchlist_visualizer()
        self.chart_renderer = get_advanced_chart_renderer()
        
        # Event handling
        self.event_subscriber = get_event_subscriber()
        
        # UI state
        self.current_symbol = Config.DEFAULT_SYMBOL
        self.current_tab = 0  # 0: Trading, 1: Watchlist, 2: Charts, 3: Orders, 4: Scanner
        self.tab_names = ["Trading", "Watchlist", "Charts", "Orders", "Scanner"]
        self.current_timeframe = "1m"
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        self.chart_symbol = Config.DEFAULT_SYMBOL
        
        # Terminal state
        self.is_running = False
        self.last_update = datetime.now()
        self.update_interval = 2  # seconds
        
        # Data
        self.latest_order_book = None
        self.latest_trades = []
        self.scan_results = []
        
        # Setup
        self._setup_event_handlers()
        
        logger.info("Professional Trading Terminal initialized")
    
    def _setup_event_handlers(self):
        """Setup event handlers for real-time updates."""
        
        def on_market_data(event):
            self.last_update = datetime.now()
        
        def on_order_book_update(event):
            if event.data.get('symbol') == self.current_symbol:
                self.latest_order_book = {
                    'bids': event.data.get('bids', []),
                    'asks': event.data.get('asks', [])
                }
        
        def on_trade_data(event):
            if event.data.get('symbol') == self.current_symbol:
                self.latest_trades.append(event.data)
                if len(self.latest_trades) > 50:
                    self.latest_trades.pop(0)
        
        # Subscribe to events
        self.event_subscriber.on_market_data(on_market_data)
        self.event_subscriber.on_order_book_update(on_order_book_update)
        self.event_subscriber.on_trade_data(on_trade_data)
    
    async def initialize(self):
        """Initialize all services."""
        console.print("[cyan]🚀 Initializing Professional Trading Terminal...[/cyan]")
        
        # Initialize trading service
        if not await self.trading_service.initialize():
            console.print("[red]❌ Failed to initialize trading service[/red]")
            return False
        
        # Start WebSocket manager
        await self.ws_manager.start()
        
        # Subscribe to default symbol
        await self.ws_manager.subscribe_symbol(self.current_symbol)
        await self.multi_symbol_monitor.add_symbol(self.current_symbol)
        
        # Add to watchlist
        self.multi_symbol_monitor.add_to_watchlist(self.current_symbol)
        
        console.print("[green]✅ Professional Trading Terminal initialized[/green]")
        return True
    
    async def shutdown(self):
        """Shutdown all services."""
        self.is_running = False
        await self.ws_manager.stop()
        await self.trading_service.shutdown()
        console.print("[yellow]📊 Professional Trading Terminal stopped[/yellow]")
    
    def create_header_panel(self) -> Panel:
        """Create the header panel with system status."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get connection status
        ws_status = "🟢 LIVE" if self.ws_manager.get_connection_status() else "🔴 DISCONNECTED"
        
        # Get current price
        current_price = self.ws_manager.get_latest_price(self.current_symbol)
        price_text = f"${current_price:.4f}" if current_price else "Loading..."
        
        # Performance metrics
        perf_stats = self.multi_symbol_monitor.get_performance_stats()
        updates_per_sec = perf_stats.get('updates_per_second', 0)
        
        header_text = Text.assemble(
            ("🏛️ Professional Trading Terminal", "bold blue"),
            (" | ", "dim"),
            (f"{ws_status}", "bold"),
            (" | ", "dim"),
            (f"Symbol: {self.current_symbol}", "bold green"),
            (" | ", "dim"),
            (f"Price: {price_text}", "bold white"),
            (" | ", "dim"),
            (f"Updates: {updates_per_sec:.1f}/s", "dim"),
            (" | ", "dim"),
            (f"{current_time}", "dim")
        )
        
        return Panel(Align.center(header_text), border_style="blue", height=3)
    
    def create_tab_header(self) -> Panel:
        """Create tab navigation header."""
        tab_parts = []
        for i, tab_name in enumerate(self.tab_names):
            if i == self.current_tab:
                tab_parts.append(f"[bold white on blue] {i+1}:{tab_name} [/bold white on blue]")
            else:
                tab_parts.append(f"[dim] {i+1}:{tab_name} [/dim]")
        
        tab_text = "  ".join(tab_parts)
        
        # Add hotkeys
        hotkeys = "[dim]Hotkeys: [bold]1-5[/bold] tabs, [bold]S[/bold] change symbol, [bold]T[/bold] timeframe, [bold]O[/bold] order, [bold]Q[/bold] quit[/dim]"
        
        return Panel(
            f"{tab_text}\n{hotkeys}",
            title="Navigation",
            border_style="cyan",
            height=4
        )
    
    def create_trading_tab(self) -> Layout:
        """Create the main trading tab layout."""
        layout = Layout()
        
        layout.split_row(
            Layout(name="left", ratio=1),
            Layout(name="center", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        # Left panel: Market depth and recent trades
        layout["left"].split_column(
            Layout(self.create_order_book_panel(), name="order_book"),
            Layout(self.create_recent_trades_panel(), name="trades")
        )
        
        # Center panel: Price chart
        layout["center"].update(self.create_main_chart_panel())
        
        # Right panel: Position info and quick order
        layout["right"].split_column(
            Layout(self.create_position_panel(), name="positions"),
            Layout(self.create_quick_order_panel(), name="quick_order"),
            Layout(self.create_market_stats_panel(), name="stats")
        )
        
        return layout
    
    def create_order_book_panel(self) -> Panel:
        """Create order book panel."""
        if not self.latest_order_book:
            return Panel("Loading order book...", title="Order Book", border_style="yellow")
        
        return self.market_depth_viz.create_order_book_panel(
            self.current_symbol,
            self.latest_order_book['bids'],
            self.latest_order_book['asks']
        )
    
    def create_recent_trades_panel(self) -> Panel:
        """Create recent trades panel."""
        if not self.latest_trades:
            return Panel("Loading trades...", title="Recent Trades", border_style="green")
        
        trades_table = Table(show_header=True, show_edge=False, pad_edge=False)
        trades_table.add_column("Time", style="dim", width=8)
        trades_table.add_column("Side", style="white", width=4)
        trades_table.add_column("Price", style="white", width=10, justify="right")
        trades_table.add_column("Size", style="white", width=10, justify="right")
        
        for trade in self.latest_trades[-10:]:
            time_str = trade['timestamp'].strftime("%H:%M:%S")
            is_buy = not trade['is_buyer_maker']
            side_color = "green" if is_buy else "red"
            side_text = "BUY" if is_buy else "SELL"
            
            trades_table.add_row(
                time_str,
                f"[{side_color}]{side_text}[/{side_color}]",
                f"{trade['price']:.4f}",
                f"{trade['quantity']:.4f}"
            )
        
        return Panel(trades_table, title="Recent Trades", border_style="green")
    
    def create_main_chart_panel(self) -> Panel:
        """Create the main price chart panel."""
        # Get kline data
        klines_data = self.ws_manager.get_latest_klines(self.chart_symbol, self.current_timeframe, 50)
        
        if not klines_data:
            return Panel("Loading chart data...", title=f"Chart - {self.chart_symbol}", border_style="cyan")
        
        # Convert to CandleData objects
        candles = []
        for kline in klines_data:
            candle = CandleData(
                open_time=datetime.fromtimestamp(kline['open_time'] / 1000),
                close_time=datetime.fromtimestamp(kline['close_time'] / 1000),
                open=kline['open'],
                high=kline['high'],
                low=kline['low'],
                close=kline['close'],
                volume=kline['volume'],
                trades=kline['trades']
            )
            candles.append(candle)
        
        return self.chart_renderer.render_candlestick_chart(
            candles, self.chart_symbol, self.current_timeframe
        )
    
    def create_position_panel(self) -> Panel:
        """Create positions panel."""
        positions = self.trading_service.get_open_positions()
        
        if not positions:
            return Panel("No open positions", title="Positions", border_style="yellow")
        
        pos_table = Table(show_header=True, show_edge=False, pad_edge=False)
        pos_table.add_column("Symbol", style="cyan", width=8)
        pos_table.add_column("Side", style="white", width=4)
        pos_table.add_column("Size", style="white", width=8, justify="right")
        pos_table.add_column("Entry", style="white", width=8, justify="right")
        pos_table.add_column("PnL", style="white", width=10, justify="right")
        
        for position in positions[:5]:  # Show top 5
            pnl_color = "green" if position.pnl >= 0 else "red"
            side_color = "green" if position.side.value == "buy" else "red"
            
            pos_table.add_row(
                position.symbol,
                f"[{side_color}]{position.side.value.upper()}[/{side_color}]",
                f"{position.quantity:.4f}",
                f"{position.entry_price:.4f}",
                f"[{pnl_color}]{position.pnl:+.2f}[/{pnl_color}]"
            )
        
        return Panel(pos_table, title="Open Positions", border_style="yellow")
    
    def create_quick_order_panel(self) -> Panel:
        """Create quick order panel."""
        current_price = self.ws_manager.get_latest_price(self.current_symbol) or 0
        
        content_lines = [
            f"Symbol: [bold]{self.current_symbol}[/bold]",
            f"Price: [bold]${current_price:.4f}[/bold]",
            "",
            "[green]Quick Actions:[/green]",
            "[dim]O - Place Order[/dim]",
            "[dim]M - Market Buy[/dim]",
            "[dim]N - Market Sell[/dim]",
            "[dim]L - Limit Order[/dim]",
            "[dim]C - Close Position[/dim]"
        ]
        
        return Panel("\n".join(content_lines), title="Quick Order", border_style="blue")
    
    def create_market_stats_panel(self) -> Panel:
        """Create market statistics panel."""
        stats = self.ws_manager.get_symbol_statistics(self.current_symbol)
        
        if not stats:
            return Panel("Loading stats...", title="Market Stats", border_style="white")
        
        stats_table = Table(show_header=False, show_edge=False, pad_edge=False)
        stats_table.add_column("Metric", style="cyan", width=12)
        stats_table.add_column("Value", style="white")
        
        price_change_color = "green" if stats.get('price_change_24h', 0) > 0 else "red"
        
        stats_table.add_row("24h Change", f"[{price_change_color}]{stats.get('price_change_24h', 0):+.2f}%[/{price_change_color}]")
        stats_table.add_row("24h High", f"${stats.get('high_24h', 0):.4f}")
        stats_table.add_row("24h Low", f"${stats.get('low_24h', 0):.4f}")
        stats_table.add_row("24h Volume", f"{stats.get('volume_24h', 0):,.0f}")
        stats_table.add_row("Tick Count", f"{stats.get('tick_count', 0):,}")
        
        return Panel(stats_table, title="Market Stats", border_style="white")
    
    def create_watchlist_tab(self) -> Layout:
        """Create watchlist tab."""
        layout = Layout()
        
        layout.split_row(
            Layout(name="watchlist", ratio=2),
            Layout(name="details", ratio=1)
        )
        
        layout["watchlist"].update(self.watchlist_viz.create_watchlist_panel())
        
        # Symbol details
        layout["details"].split_column(
            Layout(self.watchlist_viz.create_symbol_detail_panel(self.current_symbol), name="details"),
            Layout(self.watchlist_viz.create_alerts_panel(), name="alerts")
        )
        
        return layout
    
    def create_charts_tab(self) -> Layout:
        """Create advanced charts tab."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="chart", ratio=2),
            Layout(name="indicators", ratio=1)
        )
        
        # Main chart
        layout["chart"].split_row(
            Layout(self.create_main_chart_panel(), name="main_chart", ratio=2),
            Layout(self.chart_renderer.render_multi_timeframe_view(self.chart_symbol), name="multi_tf", ratio=1)
        )
        
        # Indicators and market depth
        layout["indicators"].split_row(
            Layout(self.chart_renderer.render_indicator_panel(self.chart_symbol, self.current_timeframe), name="indicators"),
            Layout(self.market_depth_viz.create_market_depth_panel(
                self.chart_symbol,
                self.latest_order_book['bids'] if self.latest_order_book else [],
                self.latest_order_book['asks'] if self.latest_order_book else []
            ), name="depth")
        )
        
        return layout
    
    def create_orders_tab(self) -> Layout:
        """Create orders management tab."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="active_orders"),
            Layout(name="order_history")
        )
        
        # Active orders
        active_orders = self.order_manager.get_active_orders()
        layout["active_orders"].update(self.create_active_orders_panel(active_orders))
        
        # Order history  
        order_history = self.order_manager.get_order_history(limit=20)
        layout["order_history"].update(self.create_order_history_panel(order_history))
        
        return layout
    
    def create_active_orders_panel(self, orders) -> Panel:
        """Create active orders panel."""
        if not orders:
            return Panel("No active orders", title="Active Orders", border_style="green")
        
        orders_table = Table(show_header=True, show_edge=False, pad_edge=False)
        orders_table.add_column("Symbol", style="cyan", width=10)
        orders_table.add_column("Side", style="white", width=4)
        orders_table.add_column("Type", style="white", width=8)
        orders_table.add_column("Quantity", style="white", width=10, justify="right")
        orders_table.add_column("Price", style="white", width=10, justify="right")
        orders_table.add_column("Status", style="white", width=10)
        orders_table.add_column("Time", style="white", width=8)
        
        for order in orders:
            side_color = "green" if order.side == OrderSide.BUY else "red"
            status_color = "yellow" if order.status.value == "SUBMITTED" else "green"
            
            orders_table.add_row(
                order.symbol,
                f"[{side_color}]{order.side.value}[/{side_color}]",
                order.order_type.value,
                f"{order.quantity:.4f}",
                f"{order.price:.4f}" if order.price else "MARKET",
                f"[{status_color}]{order.status.value}[/{status_color}]",
                order.created_time.strftime("%H:%M:%S")
            )
        
        return Panel(orders_table, title="Active Orders", border_style="green")
    
    def create_order_history_panel(self, orders) -> Panel:
        """Create order history panel."""
        if not orders:
            return Panel("No order history", title="Order History", border_style="blue")
        
        history_table = Table(show_header=True, show_edge=False, pad_edge=False)
        history_table.add_column("Symbol", style="cyan", width=10)
        history_table.add_column("Side", style="white", width=4)
        history_table.add_column("Quantity", style="white", width=10, justify="right")
        history_table.add_column("Price", style="white", width=10, justify="right")
        history_table.add_column("Status", style="white", width=10)
        history_table.add_column("Time", style="white", width=12)
        
        for order in orders[-10:]:  # Last 10 orders
            side_color = "green" if order.side == OrderSide.BUY else "red"
            status_color = {
                "FILLED": "green",
                "CANCELLED": "yellow", 
                "REJECTED": "red"
            }.get(order.status.value, "white")
            
            history_table.add_row(
                order.symbol,
                f"[{side_color}]{order.side.value}[/{side_color}]",
                f"{order.quantity:.4f}",
                f"{order.avg_fill_price or order.price:.4f}" if (order.avg_fill_price or order.price) else "MARKET",
                f"[{status_color}]{order.status.value}[/{status_color}]",
                (order.filled_time or order.cancelled_time or order.created_time).strftime("%m-%d %H:%M")
            )
        
        return Panel(history_table, title="Order History", border_style="blue")
    
    def create_scanner_tab(self) -> Layout:
        """Create market scanner tab."""
        layout = Layout()
        
        layout.split_row(
            Layout(name="scanner_results", ratio=2),
            Layout(name="scanner_controls", ratio=1)
        )
        
        # Scanner results
        layout["scanner_results"].update(
            self.watchlist_viz.create_market_scanner_panel(self.scan_results)
        )
        
        # Scanner controls and performance
        layout["scanner_controls"].split_column(
            Layout(self.create_scanner_controls_panel(), name="controls"),
            Layout(self.watchlist_viz.create_performance_panel(), name="performance")
        )
        
        return layout
    
    def create_scanner_controls_panel(self) -> Panel:
        """Create scanner controls panel."""
        content = [
            "[bold]Market Scanner[/bold]",
            "",
            "[green]Available Scans:[/green]",
            "[dim]F1 - Momentum (>5% gain)[/dim]",
            "[dim]F2 - Volume Spike (>2x avg)[/dim]", 
            "[dim]F3 - Oversold (RSI <30)[/dim]",
            "[dim]F4 - Breakout Patterns[/dim]",
            "[dim]F5 - Custom Scan[/dim]",
            "",
            f"[dim]Last scan: {len(self.scan_results)} results[/dim]"
        ]
        
        return Panel("\n".join(content), title="Scanner Controls", border_style="yellow")
    
    def create_main_layout(self) -> Layout:
        """Create the main terminal layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="tabs", size=4),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=2)
        )
        
        # Header and tabs
        layout["header"].update(self.create_header_panel())
        layout["tabs"].update(self.create_tab_header())
        
        # Main content based on current tab
        if self.current_tab == 0:  # Trading
            layout["main"].update(self.create_trading_tab())
        elif self.current_tab == 1:  # Watchlist
            layout["main"].update(self.create_watchlist_tab())
        elif self.current_tab == 2:  # Charts
            layout["main"].update(self.create_charts_tab())
        elif self.current_tab == 3:  # Orders
            layout["main"].update(self.create_orders_tab())
        elif self.current_tab == 4:  # Scanner
            layout["main"].update(self.create_scanner_tab())
        
        # Footer
        footer_text = Text.assemble(
            ("Professional Trading Terminal", "bold blue"),
            (" | ", "dim"),
            (f"Mode: {Config.TRADING_MODE.upper()}", "bold yellow"),
            (" | ", "dim"),
            (f"Updates: {self.last_update.strftime('%H:%M:%S')}", "dim")
        )
        layout["footer"].update(Align.center(footer_text))
        
        return layout
    
    def check_keyboard_input(self):
        """Check for keyboard input."""
        try:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1)
                
                # Tab navigation
                if key in '12345':
                    self.current_tab = int(key) - 1
                
                # Symbol change
                elif key.lower() == 's':
                    self._handle_symbol_change()
                
                # Timeframe change
                elif key.lower() == 't':
                    self._handle_timeframe_change()
                
                # Order placement
                elif key.lower() == 'o':
                    asyncio.create_task(self._handle_order_placement())
                
                # Market buy
                elif key.lower() == 'm':
                    asyncio.create_task(self._handle_market_buy())
                
                # Market sell
                elif key.lower() == 'n':
                    asyncio.create_task(self._handle_market_sell())
                
                # Scanner functions
                elif key in ['F1', 'F2', 'F3', 'F4', 'F5']:
                    asyncio.create_task(self._handle_scanner(key))
                
                # Quit
                elif key.lower() == 'q':
                    self.is_running = False
                
                return key
        except:
            pass
        return None
    
    def _handle_symbol_change(self):
        """Handle symbol change."""
        # This would be implemented with a proper input handler
        # For now, just cycle through some popular symbols
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT']
        current_index = symbols.index(self.current_symbol) if self.current_symbol in symbols else 0
        next_index = (current_index + 1) % len(symbols)
        
        old_symbol = self.current_symbol
        self.current_symbol = symbols[next_index]
        self.chart_symbol = self.current_symbol
        
        # Subscribe to new symbol
        asyncio.create_task(self.ws_manager.subscribe_symbol(self.current_symbol))
        asyncio.create_task(self.multi_symbol_monitor.add_symbol(self.current_symbol))
        
        logger.info(f"Symbol changed from {old_symbol} to {self.current_symbol}")
    
    def _handle_timeframe_change(self):
        """Handle timeframe change."""
        current_index = self.timeframes.index(self.current_timeframe) if self.current_timeframe in self.timeframes else 0
        next_index = (current_index + 1) % len(self.timeframes)
        self.current_timeframe = self.timeframes[next_index]
        logger.info(f"Timeframe changed to {self.current_timeframe}")
    
    async def _handle_order_placement(self):
        """Handle order placement."""
        # This would open an order dialog in a real implementation
        logger.info("Order placement dialog requested")
    
    async def _handle_market_buy(self):
        """Handle quick market buy."""
        # Quick market buy with default size
        logger.info(f"Quick market buy requested for {self.current_symbol}")
    
    async def _handle_market_sell(self):
        """Handle quick market sell."""
        # Quick market sell
        logger.info(f"Quick market sell requested for {self.current_symbol}")
    
    async def _handle_scanner(self, scan_type: str):
        """Handle market scanner."""
        try:
            criteria = ScanCriteria()
            
            if scan_type == 'F1':  # Momentum
                criteria.min_price_change = 5.0
            elif scan_type == 'F2':  # Volume spike
                criteria.min_volume_24h = 1000000
            elif scan_type == 'F3':  # Oversold
                criteria.max_rsi = 30
                criteria.require_oversold = True
            elif scan_type == 'F4':  # Breakout
                criteria.require_breakout = True
            
            self.scan_results = await self.multi_symbol_monitor.scan_market(criteria)
            logger.info(f"Market scan completed: {len(self.scan_results)} results")
            
        except Exception as e:
            logger.error(f"Scanner error: {e}")
    
    async def update_data(self):
        """Update all data sources."""
        try:
            # Update trading service data
            analysis = await self.trading_service.analyze_market(self.current_symbol)
            
            # Update last update time
            self.last_update = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating data: {e}")
    
    async def run(self):
        """Run the professional trading terminal."""
        if not await self.initialize():
            return
        
        self.is_running = True
        console.print("[green]🚀 Starting Professional Trading Terminal[/green]")
        console.print("[yellow]Press 1-5 for tabs, S for symbol, T for timeframe, O for orders, Q to quit[/yellow]")
        
        # Set terminal to non-blocking mode
        old_settings = None
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
        except:
            pass
        
        try:
            with Live(self.create_main_layout(), console=console, refresh_per_second=4) as live:
                last_update_time = time.time()
                
                while self.is_running:
                    try:
                        # Check for keyboard input
                        if old_settings is not None:
                            self.check_keyboard_input()
                        
                        # Update data periodically
                        current_time = time.time()
                        if current_time - last_update_time >= self.update_interval:
                            await self.update_data()
                            last_update_time = current_time
                        
                        # Update display
                        live.update(self.create_main_layout())
                        
                        # Short sleep to prevent high CPU usage
                        await asyncio.sleep(0.25)
                        
                    except KeyboardInterrupt:
                        self.is_running = False
                        break
                    except Exception as e:
                        logger.error(f"Error in main loop: {e}")
                        await asyncio.sleep(1)
        
        finally:
            # Restore terminal settings
            if old_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except:
                    pass
            
            await self.shutdown()


# CLI interface
@click.command()
@click.option('--symbol', default='BTCUSDT', help='Initial trading symbol')
@click.option('--balance', default=10000.0, help='Initial balance')
def professional_terminal_cli(symbol: str, balance: float):
    """Launch the Professional Trading Terminal."""
    
    async def run_terminal():
        terminal = ProfessionalTradingTerminal(balance)
        terminal.current_symbol = symbol.upper()
        terminal.chart_symbol = symbol.upper()
        
        try:
            await terminal.run()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.error(f"Terminal error: {e}")
    
    # Run the async function
    asyncio.run(run_terminal())


def main():
    """Main entry point."""
    professional_terminal_cli()


if __name__ == '__main__':
    main()