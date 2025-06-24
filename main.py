#!/usr/bin/env python3
"""
Rich Terminal Interface for Cryptocurrency Trading Bot
Uses the core trading service with beautiful terminal UI
"""

import asyncio
import sys
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.columns import Columns
from rich.align import Align
from rich.status import Status

# Import our core service and models
from trading_service import TradingService, create_trading_service
from models import MarketAnalysis, PositionData, TradingSignal, SignalAction
from events import get_event_subscriber, EventSubscriber
from config import Config
from logger import get_logger

# Initialize console and logger
console = Console()
logger = get_logger("cli")

class TradingCLI:
    """Rich terminal interface for the trading bot."""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.trading_service = create_trading_service(initial_balance)
        self.event_subscriber = get_event_subscriber()
        self.is_running = False
        self.current_symbol = Config.DEFAULT_SYMBOL
        self.last_update = datetime.now()
        
        # UI state
        self.latest_analysis: Optional[MarketAnalysis] = None
        self.latest_portfolio = None
        self.latest_positions = []
        self.recent_events = []
        
        # Subscribe to events
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers for real-time updates."""
        
        def on_market_data(event):
            # Update market data in UI
            self.last_update = datetime.now()
        
        def on_signal_generated(event):
            signal = event.signal
            self.recent_events.append({
                'time': event.timestamp,
                'type': 'Signal',
                'message': f"{event.symbol}: {signal.action.upper()} (confidence: {signal.confidence:.2f})",
                'color': 'green' if signal.action == 'buy' else 'red' if signal.action == 'sell' else 'yellow'
            })
            # Keep only last 10 events
            if len(self.recent_events) > 10:
                self.recent_events.pop(0)
        
        def on_position_opened(event):
            position = event.position
            self.recent_events.append({
                'time': event.timestamp,
                'type': 'Position',
                'message': f"Opened {position.side.upper()} {position.symbol} @ {position.entry_price}",
                'color': 'green'
            })
            if len(self.recent_events) > 10:
                self.recent_events.pop(0)
        
        def on_position_closed(event):
            position = event.position
            pnl_color = 'green' if position.pnl > 0 else 'red'
            self.recent_events.append({
                'time': event.timestamp,
                'type': 'Position',
                'message': f"Closed {position.symbol} PnL: {position.pnl:.4f}",
                'color': pnl_color
            })
            if len(self.recent_events) > 10:
                self.recent_events.pop(0)
        
        def on_risk_event(event):
            self.recent_events.append({
                'time': event.timestamp,
                'type': 'Risk',
                'message': f"{event.risk_type}: {event.message}",
                'color': 'yellow' if event.severity == 'warning' else 'red'
            })
            if len(self.recent_events) > 10:
                self.recent_events.pop(0)
        
        # Subscribe to events
        self.event_subscriber.on_market_data(on_market_data)
        self.event_subscriber.on_signal_generated(on_signal_generated)
        self.event_subscriber.on_position_opened(on_position_opened)
        self.event_subscriber.on_position_closed(on_position_closed)
        self.event_subscriber.on_risk_event(on_risk_event)
    
    async def initialize(self):
        """Initialize the trading service."""
        with Status("Initializing trading service...", console=console, spinner="dots"):
            success = await self.trading_service.initialize()
            if not success:
                console.print("[red]❌ Failed to initialize trading service[/red]")
                return False
        
        console.print("[green]✅ Trading service initialized successfully[/green]")
        return True
    
    def create_market_panel(self) -> Panel:
        """Create market analysis panel."""
        if not self.latest_analysis:
            return Panel("No market data available", title="Market Analysis", border_style="blue")
        
        analysis = self.latest_analysis
        market = analysis.market_summary
        signal = analysis.strategy_signal
        trend = analysis.trend_analysis
        
        # Market data table
        market_table = Table(show_header=False, show_edge=False, pad_edge=False)
        market_table.add_column("Metric", style="cyan", width=20)
        market_table.add_column("Value", style="white")
        
        # Price info
        price_change_color = "green" if market.price_change_24h > 0 else "red"
        market_table.add_row("Symbol", f"[bold]{analysis.symbol}[/bold]")
        market_table.add_row("Price", f"${market.current_price:.4f}")
        market_table.add_row("24h Change", f"[{price_change_color}]{market.price_change_24h:+.2f}%[/{price_change_color}]")
        market_table.add_row("Volume", f"{market.volume_24h:,.0f}")
        
        # Technical indicators
        rsi_color = "red" if market.rsi > 70 else "green" if market.rsi < 30 else "yellow"
        market_table.add_row("RSI", f"[{rsi_color}]{market.rsi:.1f}[/{rsi_color}]")
        market_table.add_row("MACD", f"{market.macd:.6f}")
        market_table.add_row("Support", f"${market.support_level:.4f}")
        market_table.add_row("Resistance", f"${market.resistance_level:.4f}")
        
        # Signal info
        signal_color = "green" if signal.action == SignalAction.BUY else "red" if signal.action == SignalAction.SELL else "yellow"
        market_table.add_row("Signal", f"[{signal_color}]{signal.action.upper()}[/{signal_color}]")
        market_table.add_row("Confidence", f"{signal.confidence:.2f}")
        market_table.add_row("Trend", f"[bold]{trend.trend.upper()}[/bold] ({trend.strength})")
        
        return Panel(market_table, title=f"Market Analysis - {analysis.symbol}", border_style="blue")
    
    def create_portfolio_panel(self) -> Panel:
        """Create portfolio summary panel."""
        if not self.latest_portfolio:
            return Panel("No portfolio data available", title="Portfolio", border_style="green")
        
        portfolio = self.latest_portfolio
        
        # Portfolio table
        portfolio_table = Table(show_header=False, show_edge=False, pad_edge=False)
        portfolio_table.add_column("Metric", style="cyan", width=20)
        portfolio_table.add_column("Value", style="white")
        
        # Balance info
        pnl_color = "green" if portfolio.unrealized_pnl >= 0 else "red"
        total_return = portfolio.performance_metrics.total_return * 100
        return_color = "green" if total_return >= 0 else "red"
        
        portfolio_table.add_row("Initial Balance", f"${portfolio.initial_balance:,.2f}")
        portfolio_table.add_row("Current Balance", f"${portfolio.current_balance:,.2f}")
        portfolio_table.add_row("Unrealized PnL", f"[{pnl_color}]{portfolio.unrealized_pnl:+.2f}[/{pnl_color}]")
        portfolio_table.add_row("Portfolio Value", f"[bold]${portfolio.portfolio_value:,.2f}[/bold]")
        portfolio_table.add_row("Total Return", f"[{return_color}]{total_return:+.2f}%[/{return_color}]")
        
        # Performance metrics
        metrics = portfolio.performance_metrics
        win_rate_color = "green" if metrics.win_rate >= 0.6 else "yellow" if metrics.win_rate >= 0.4 else "red"
        
        portfolio_table.add_row("Open Positions", str(portfolio.open_positions))
        portfolio_table.add_row("Total Trades", str(metrics.total_trades))
        portfolio_table.add_row("Win Rate", f"[{win_rate_color}]{metrics.win_rate*100:.1f}%[/{win_rate_color}]")
        if metrics.total_trades > 0:
            portfolio_table.add_row("Avg Win", f"${metrics.avg_win:.2f}")
            portfolio_table.add_row("Avg Loss", f"${metrics.avg_loss:.2f}")
        
        return Panel(portfolio_table, title="Portfolio Summary", border_style="green")
    
    def create_positions_panel(self) -> Panel:
        """Create open positions panel."""
        if not self.latest_positions:
            return Panel("No open positions", title="Open Positions", border_style="yellow")
        
        # Positions table
        positions_table = Table()
        positions_table.add_column("Symbol", style="cyan")
        positions_table.add_column("Side", style="white")
        positions_table.add_column("Quantity", style="white", justify="right")
        positions_table.add_column("Entry Price", style="white", justify="right")
        positions_table.add_column("PnL", style="white", justify="right")
        positions_table.add_column("Duration", style="white", justify="right")
        
        for position in self.latest_positions:
            pnl_color = "green" if position.pnl >= 0 else "red"
            side_color = "green" if position.side.value == "buy" else "red"
            
            # Calculate duration
            duration = datetime.now() - position.entry_time
            duration_str = str(duration).split('.')[0]  # Remove microseconds
            
            positions_table.add_row(
                position.symbol,
                f"[{side_color}]{position.side.value.upper()}[/{side_color}]",
                f"{position.quantity:.6f}",
                f"${position.entry_price:.4f}",
                f"[{pnl_color}]{position.pnl:+.4f}[/{pnl_color}]",
                duration_str
            )
        
        return Panel(positions_table, title="Open Positions", border_style="yellow")
    
    def create_events_panel(self) -> Panel:
        """Create recent events panel."""
        if not self.recent_events:
            return Panel("No recent events", title="Recent Events", border_style="magenta")
        
        events_table = Table(show_header=False, show_edge=False, pad_edge=False)
        events_table.add_column("Time", style="dim", width=8)
        events_table.add_column("Type", style="bold", width=8)
        events_table.add_column("Message", style="white")
        
        for event in reversed(self.recent_events[-8:]):  # Show last 8 events
            time_str = event['time'].strftime("%H:%M:%S")
            color = event['color']
            events_table.add_row(
                time_str,
                f"[{color}]{event['type']}[/{color}]",
                f"[{color}]{event['message']}[/{color}]"
            )
        
        return Panel(events_table, title="Recent Events", border_style="magenta")
    
    def create_status_panel(self) -> Panel:
        """Create status panel."""
        uptime = timedelta(seconds=int(self.trading_service.get_uptime_seconds()))
        
        status_table = Table(show_header=False, show_edge=False, pad_edge=False)
        status_table.add_column("Item", style="cyan", width=15)
        status_table.add_column("Value", style="white")
        
        status_table.add_row("Trading Mode", Config.TRADING_MODE.upper())
        status_table.add_row("Active Strategy", self.trading_service.get_active_strategy())
        status_table.add_row("Monitoring", "✅ Active" if self.trading_service.is_monitoring else "❌ Stopped")
        status_table.add_row("Uptime", str(uptime))
        status_table.add_row("Last Update", self.last_update.strftime("%H:%M:%S"))
        
        return Panel(status_table, title="System Status", border_style="white")
    
    def create_dashboard(self) -> Layout:
        """Create the main dashboard layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        layout["header"].update(
            Align.center(
                Text("🚀 Cryptocurrency Trading Bot", style="bold blue"),
                vertical="middle"
            )
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(self.create_market_panel(), name="market"),
            Layout(self.create_portfolio_panel(), name="portfolio")
        )
        
        layout["right"].split_column(
            Layout(self.create_positions_panel(), name="positions"),
            Layout(self.create_events_panel(), name="events"),
            Layout(self.create_status_panel(), name="status")
        )
        
        # Footer with controls
        footer_text = Text.assemble(
            ("Press ", "dim"),
            ("q", "bold red"),
            (" to quit, ", "dim"),
            ("a", "bold green"),
            (" to analyze, ", "dim"),
            ("p", "bold yellow"),
            (" to open position, ", "dim"),
            ("c", "bold blue"),
            (" to close position", "dim")
        )
        layout["footer"].update(Align.center(footer_text, vertical="middle"))
        
        return layout
    
    async def update_data(self):
        """Update dashboard data."""
        try:
            # Get latest analysis
            analysis = self.trading_service.get_last_analysis(self.current_symbol)
            if not analysis:
                analysis = await self.trading_service.analyze_market(self.current_symbol)
            self.latest_analysis = analysis
            
            # Get portfolio summary
            self.latest_portfolio = self.trading_service.get_portfolio_summary()
            
            # Get open positions
            self.latest_positions = self.trading_service.get_open_positions()
            
        except Exception as e:
            logger.error(f"Error updating data: {e}")
    
    async def run_dashboard(self, symbol: str, update_interval: int = 10):
        """Run the live dashboard."""
        self.current_symbol = symbol
        self.is_running = True
        
        console.print(f"[green]🚀 Starting trading dashboard for {symbol}[/green]")
        console.print("[dim]Loading initial data...[/dim]")
        
        # Initial data load
        await self.update_data()
        
        # Start monitoring
        asyncio.create_task(self.trading_service.start_monitoring(30))
        
        with Live(self.create_dashboard(), console=console, refresh_per_second=2) as live:
            last_update = time.time()
            
            while self.is_running:
                try:
                    # Update data periodically
                    current_time = time.time()
                    if current_time - last_update >= update_interval:
                        await self.update_data()
                        last_update = current_time
                    
                    # Update dashboard
                    live.update(self.create_dashboard())
                    
                    # Short sleep to prevent high CPU usage
                    await asyncio.sleep(0.5)
                    
                except KeyboardInterrupt:
                    self.is_running = False
                    break
                except Exception as e:
                    logger.error(f"Error in dashboard loop: {e}")
                    await asyncio.sleep(1)
        
        # Cleanup
        self.trading_service.stop_monitoring()
        console.print("\n[yellow]📊 Dashboard stopped[/yellow]")
    
    async def interactive_mode(self, symbol: str):
        """Run interactive mode with commands."""
        self.current_symbol = symbol
        
        console.print(f"[green]🎮 Starting interactive mode for {symbol}[/green]")
        console.print("[dim]Available commands: analyze, position, close, portfolio, strategies, quit[/dim]")
        
        while True:
            try:
                command = console.input("\n[bold blue]crypto-bot>[/bold blue] ").strip().lower()
                
                if command in ['quit', 'exit', 'q']:
                    break
                
                elif command in ['analyze', 'a']:
                    await self.analyze_command(symbol)
                
                elif command in ['position', 'p']:
                    await self.position_command(symbol)
                
                elif command in ['close', 'c']:
                    await self.close_command(symbol)
                
                elif command in ['portfolio', 'pf']:
                    await self.portfolio_command()
                
                elif command in ['strategies', 's']:
                    self.strategies_command()
                
                elif command == 'help':
                    self.help_command()
                
                else:
                    console.print(f"[red]Unknown command: {command}[/red]")
                    console.print("[dim]Type 'help' for available commands[/dim]")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        console.print("\n[yellow]👋 Interactive mode ended[/yellow]")
    
    async def analyze_command(self, symbol: str):
        """Analyze market command."""
        with Status(f"Analyzing {symbol}...", console=console):
            analysis = await self.trading_service.analyze_market(symbol)
        
        # Display analysis
        market_panel = self.create_market_panel()
        console.print(market_panel)
    
    async def position_command(self, symbol: str):
        """Open position command."""
        strategies = self.trading_service.get_available_strategies()
        active_strategy = self.trading_service.get_active_strategy()
        
        console.print(f"Available strategies: {', '.join(strategies)}")
        console.print(f"Active strategy: [bold]{active_strategy}[/bold]")
        
        if Confirm.ask("Open position with current strategy?"):
            with Status("Executing position...", console=console):
                result = await self.trading_service.execute_position(symbol)
            
            if result.status == "success":
                console.print(f"[green]✅ {result.message}[/green]")
            else:
                console.print(f"[yellow]⚠️  {result.message}[/yellow]")
    
    async def close_command(self, symbol: str):
        """Close position command."""
        positions = self.trading_service.get_open_positions()
        symbol_positions = [p for p in positions if p.symbol == symbol]
        
        if not symbol_positions:
            console.print(f"[yellow]No open positions for {symbol}[/yellow]")
            return
        
        if Confirm.ask(f"Close position for {symbol}?"):
            with Status("Closing position...", console=console):
                result = await self.trading_service.close_position(symbol)
            
            if result.status == "success":
                console.print(f"[green]✅ {result.message}[/green]")
            else:
                console.print(f"[red]❌ {result.message}[/red]")
    
    async def portfolio_command(self):
        """Show portfolio command."""
        portfolio_panel = self.create_portfolio_panel()
        positions_panel = self.create_positions_panel()
        
        console.print(Columns([portfolio_panel, positions_panel]))
    
    def strategies_command(self):
        """Show strategies command."""
        strategies = self.trading_service.get_available_strategies()
        active = self.trading_service.get_active_strategy()
        
        table = Table(title="Available Strategies")
        table.add_column("Strategy", style="cyan")
        table.add_column("Status", style="white")
        
        for strategy in strategies:
            status = "[green]Active[/green]" if strategy == active else ""
            table.add_row(strategy, status)
        
        console.print(table)
    
    def help_command(self):
        """Show help command."""
        help_table = Table(title="Available Commands")
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")
        
        help_table.add_row("analyze, a", "Analyze market for current symbol")
        help_table.add_row("position, p", "Open new trading position")
        help_table.add_row("close, c", "Close existing position")
        help_table.add_row("portfolio, pf", "Show portfolio summary")
        help_table.add_row("strategies, s", "List available strategies")
        help_table.add_row("quit, q", "Exit the program")
        
        console.print(help_table)

# CLI Commands
@click.group()
def cli():
    """🚀 Cryptocurrency Trading Bot - Rich Terminal Interface"""
    pass

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Trading symbol')
@click.option('--balance', default=10000.0, help='Initial balance')
async def dashboard(symbol: str, balance: float):
    """Run the live trading dashboard with real-time updates."""
    trading_cli = TradingCLI(balance)
    
    if not await trading_cli.initialize():
        sys.exit(1)
    
    try:
        await trading_cli.run_dashboard(symbol.upper())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    finally:
        await trading_cli.trading_service.shutdown()

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Trading symbol')
@click.option('--balance', default=10000.0, help='Initial balance')
async def interactive(symbol: str, balance: float):
    """Run interactive command-line interface."""
    trading_cli = TradingCLI(balance)
    
    if not await trading_cli.initialize():
        sys.exit(1)
    
    try:
        await trading_cli.interactive_mode(symbol.upper())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    finally:
        await trading_cli.trading_service.shutdown()

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Trading symbol')
@click.option('--balance', default=10000.0, help='Initial balance')
@click.option('--strategy', default='rsi_macd', help='Trading strategy')
async def analyze(symbol: str, balance: float, strategy: str):
    """Quick market analysis for a symbol."""
    trading_cli = TradingCLI(balance)
    
    if not await trading_cli.initialize():
        sys.exit(1)
    
    try:
        trading_cli.trading_service.set_active_strategy(strategy)
        await trading_cli.analyze_command(symbol.upper())
    finally:
        await trading_cli.trading_service.shutdown()

def main():
    """Main entry point."""
    # Run the async CLI
    import asyncio
    
    def run_async_command():
        asyncio.run(cli())
    
    # Patch click to support async
    import inspect
    for name, command in cli.commands.items():
        if inspect.iscoroutinefunction(command.callback):
            def make_sync(async_func):
                def sync_func(*args, **kwargs):
                    return asyncio.run(async_func(*args, **kwargs))
                return sync_func
            command.callback = make_sync(command.callback)
    
    cli()

if __name__ == '__main__':
    main()