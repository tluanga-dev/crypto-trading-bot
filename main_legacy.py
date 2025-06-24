#!/usr/bin/env python3
"""
Cryptocurrency Algorithmic Trading Bot
"""

import sys
import time
import asyncio
from typing import Dict, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from datetime import datetime

# Import our modules
from config import Config
from binance_client import BinanceClient
from data_analyzer import DataAnalyzer
from strategy import StrategyManager
from portfolio import Portfolio
from logger import trading_logger, get_logger

# Initialize console and logger
console = Console()
logger = get_logger("main")

class TradingBot:
    """Main trading bot class."""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.binance_client = None
        self.data_analyzer = DataAnalyzer()
        self.strategy_manager = StrategyManager()
        self.portfolio = Portfolio(initial_balance)
        self.is_running = False
        self.last_analysis_time = None
        
    def initialize(self):
        """Initialize the trading bot."""
        try:
            logger.info("Initializing trading bot...")
            
            # Initialize Binance client
            self.binance_client = BinanceClient()
            
            # Print configuration summary
            Config.print_config_summary()
            
            # Log system startup
            trading_logger.log_system_event("BOT_INITIALIZED", f"Balance: {self.initial_balance}")
            
            logger.info("Trading bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize trading bot: {e}")
            return False
    
    def analyze_market(self, symbol: str) -> Dict:
        """Analyze market for a given symbol."""
        try:
            # Get market data
            klines = self.binance_client.get_klines(
                symbol=symbol,
                interval=Config.ANALYSIS_TIMEFRAME,
                limit=Config.ANALYSIS_LOOKBACK_PERIODS
            )
            
            # Convert to DataFrame and add indicators
            df = self.data_analyzer.klines_to_dataframe(klines)
            df = self.data_analyzer.add_technical_indicators(df)
            df = self.data_analyzer.calculate_signals(df)
            
            # Get market summary
            market_summary = self.data_analyzer.get_market_summary(df)
            
            # Get trend analysis
            trend_analysis = self.data_analyzer.analyze_trend(df)
            
            # Get strategy signal
            strategy_signal = self.strategy_manager.get_signal(df)
            
            # Log market data
            trading_logger.log_market_data(
                symbol=symbol,
                price=market_summary['current_price'],
                volume=market_summary['volume_24h'],
                indicators={
                    'RSI': market_summary['rsi'],
                    'MACD': market_summary['macd']
                }
            )
            
            return {
                'symbol': symbol,
                'market_summary': market_summary,
                'trend_analysis': trend_analysis,
                'strategy_signal': strategy_signal,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market for {symbol}: {e}")
            return None
    
    def execute_signal(self, analysis: Dict):
        """Execute trading signal if conditions are met."""
        try:
            signal = analysis['strategy_signal']
            symbol = analysis['symbol']
            
            if signal['action'] == 'hold':
                return
            
            # Log the signal
            trading_logger.log_trade_signal(symbol, signal)
            
            # Check if we should enter a new position
            if signal['action'] in ['buy', 'sell']:
                # Calculate position size
                position_size = self.portfolio.calculate_position_size(signal['confidence'])
                
                # Check risk management
                can_trade, reason = self.portfolio.can_open_position(position_size)
                
                if not can_trade:
                    trading_logger.log_risk_event("TRADE_BLOCKED", reason)
                    logger.warning(f"Trade blocked: {reason}")
                    return
                
                # Check if we already have a position for this symbol
                existing_position = self.portfolio.get_position_by_symbol(symbol)
                if existing_position:
                    logger.info(f"Already have position for {symbol}, skipping")
                    return
                
                # In testnet mode, simulate the trade
                if Config.is_testnet_mode():
                    self._simulate_trade(symbol, signal, position_size)
                else:
                    self._execute_real_trade(symbol, signal, position_size)
                    
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    def _simulate_trade(self, symbol: str, signal: Dict, position_size: float):
        """Simulate trade execution for testnet/paper trading."""
        try:
            from portfolio import Position
            
            # Create simulated position
            position = Position(
                symbol=symbol,
                side=signal['action'],
                quantity=position_size / signal['entry_price'],
                entry_price=signal['entry_price'],
                stop_loss=signal.get('stop_loss'),
                take_profit=signal.get('take_profit')
            )
            
            # Add to portfolio
            self.portfolio.add_position(position)
            
            # Log the simulated trade
            trading_logger.log_position_opened(
                symbol, signal['action'], position.quantity, signal['entry_price']
            )
            
            logger.info(f"Simulated {signal['action']} position opened for {symbol}")
            
        except Exception as e:
            logger.error(f"Error simulating trade: {e}")
    
    def _execute_real_trade(self, symbol: str, signal: Dict, position_size: float):
        """Execute real trade on Binance."""
        try:
            # This is where you would place actual orders
            # For safety, this requires explicit confirmation
            
            logger.warning("REAL TRADING MODE - This will place actual orders!")
            response = input(f"Execute {signal['action']} order for {symbol}? (yes/no): ")
            
            if response.lower() != 'yes':
                logger.info("Real trade cancelled by user")
                return
            
            # Place the order (implement based on your trading logic)
            quantity = position_size / signal['entry_price']
            
            order = self.binance_client.place_order(
                symbol=symbol,
                side=signal['action'].upper(),
                order_type='MARKET',
                quantity=quantity
            )
            
            trading_logger.log_order_placed(
                symbol, signal['action'], quantity, signal['entry_price'], order.get('orderId')
            )
            
            logger.info(f"Real order placed: {order}")
            
        except Exception as e:
            logger.error(f"Error executing real trade: {e}")
            trading_logger.log_api_error("PLACE_ORDER", str(e), symbol)
    
    def check_exit_conditions(self):
        """Check if any open positions should be closed."""
        try:
            open_positions = self.portfolio.get_open_positions()
            
            for position in open_positions:
                # Get current market data
                ticker = self.binance_client.get_symbol_ticker(position.symbol)
                current_price = float(ticker['price'])
                
                # Update position PnL
                position.update_pnl(current_price)
                
                # Check exit conditions
                should_exit = self.strategy_manager.should_exit_position(
                    None, position.to_dict()  # We'd need to pass market data here
                )
                
                if should_exit:
                    # Close position
                    closed_position = self.portfolio.close_position(position.symbol, current_price)
                    
                    if closed_position:
                        trading_logger.log_position_closed(
                            position.symbol, position.side, position.quantity,
                            current_price, closed_position.pnl
                        )
                        
                        logger.info(f"Position closed: {position.symbol} PnL: {closed_position.pnl:.4f}")
                
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
    
    def run_analysis_cycle(self, symbol: str):
        """Run a single analysis cycle."""
        try:
            logger.debug(f"Running analysis cycle for {symbol}")
            
            # Analyze market
            analysis = self.analyze_market(symbol)
            
            if analysis:
                # Execute signal if applicable
                self.execute_signal(analysis)
                
                # Check exit conditions for open positions
                self.check_exit_conditions()
                
                # Update last analysis time
                self.last_analysis_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error in analysis cycle: {e}")
    
    def get_status_display(self) -> Table:
        """Create status display table."""
        table = Table(title="Trading Bot Status")
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        # Portfolio metrics
        portfolio_summary = self.portfolio.get_portfolio_summary()
        
        table.add_row("Portfolio Value", f"${portfolio_summary['portfolio_value']:.2f}")
        table.add_row("Unrealized PnL", f"${portfolio_summary['unrealized_pnl']:.2f}")
        table.add_row("Open Positions", str(portfolio_summary['open_positions']))
        table.add_row("Trading Mode", Config.TRADING_MODE.upper())
        table.add_row("Active Strategy", self.strategy_manager.active_strategy)
        
        if self.last_analysis_time:
            table.add_row("Last Analysis", self.last_analysis_time.strftime("%H:%M:%S"))
        
        return table


# CLI Commands
@click.group()
def cli():
    """Cryptocurrency Algorithmic Trading Bot"""
    pass

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Trading symbol')
@click.option('--balance', default=10000.0, help='Initial balance')
@click.option('--strategy', default='rsi_macd', help='Trading strategy')
def analyze(symbol: str, balance: float, strategy: str):
    """Analyze market for a specific symbol."""
    bot = TradingBot(balance)
    
    if not bot.initialize():
        console.print("[red]Failed to initialize bot[/red]")
        sys.exit(1)
    
    # Set strategy
    try:
        bot.strategy_manager.set_active_strategy(strategy)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(f"Available strategies: {bot.strategy_manager.get_available_strategies()}")
        sys.exit(1)
    
    console.print(f"[blue]Analyzing {symbol} with {strategy} strategy...[/blue]")
    
    analysis = bot.analyze_market(symbol)
    
    if analysis:
        # Display results
        console.print(Panel(f"Market Analysis for {symbol}", style="bold blue"))
        
        market = analysis['market_summary']
        trend = analysis['trend_analysis']
        signal = analysis['strategy_signal']
        
        # Market summary table
        market_table = Table(title="Market Summary")
        market_table.add_column("Metric", style="cyan")
        market_table.add_column("Value", style="white")
        
        market_table.add_row("Current Price", f"${market['current_price']:.4f}")
        market_table.add_row("24h Change", f"{market['price_change_24h']:.2f}%")
        market_table.add_row("RSI", f"{market['rsi']:.2f}")
        market_table.add_row("MACD", f"{market['macd']:.6f}")
        market_table.add_row("Support", f"${market['support_level']:.4f}")
        market_table.add_row("Resistance", f"${market['resistance_level']:.4f}")
        
        console.print(market_table)
        
        # Signal table
        signal_table = Table(title="Trading Signal")
        signal_table.add_column("Metric", style="cyan")
        signal_table.add_column("Value", style="white")
        
        action_color = "green" if signal['action'] == 'buy' else "red" if signal['action'] == 'sell' else "yellow"
        signal_table.add_row("Action", f"[{action_color}]{signal['action'].upper()}[/{action_color}]")
        signal_table.add_row("Confidence", f"{signal['confidence']:.2f}")
        signal_table.add_row("Reason", signal['reason'])
        
        console.print(signal_table)
        
        # Trend analysis
        console.print(f"[bold]Trend:[/bold] {trend['trend'].upper()} ({trend['strength']})")
    
    else:
        console.print("[red]Failed to analyze market[/red]")

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Trading symbol')
@click.option('--balance', default=10000.0, help='Initial balance')
@click.option('--strategy', default='rsi_macd', help='Trading strategy')
@click.option('--interval', default=60, help='Analysis interval in seconds')
def run(symbol: str, balance: float, strategy: str, interval: int):
    """Run the trading bot continuously."""
    bot = TradingBot(balance)
    
    if not bot.initialize():
        console.print("[red]Failed to initialize bot[/red]")
        sys.exit(1)
    
    # Set strategy
    try:
        bot.strategy_manager.set_active_strategy(strategy)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    
    console.print(f"[green]Starting trading bot for {symbol}...[/green]")
    console.print(f"Strategy: {strategy}, Interval: {interval}s")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]")
    
    bot.is_running = True
    
    try:
        with Live(bot.get_status_display(), refresh_per_second=1) as live:
            while bot.is_running:
                # Run analysis cycle
                bot.run_analysis_cycle(symbol)
                
                # Update display
                live.update(bot.get_status_display())
                
                # Wait for next cycle
                time.sleep(interval)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping bot...[/yellow]")
        bot.is_running = False
        
        # Print final portfolio summary
        summary = bot.portfolio.get_portfolio_summary()
        console.print(Panel(f"Final Portfolio Summary", style="bold blue"))
        console.print(f"Final Value: ${summary['portfolio_value']:.2f}")
        console.print(f"Total Return: {summary['performance_metrics']['total_return']*100:.2f}%")

@cli.command()
@click.option('--symbol', default='BTCUSDT', help='Trading symbol')
@click.option('--strategy', default='rsi_macd', help='Trading strategy')
def backtest(symbol: str, strategy: str):
    """Run backtest on historical data."""
    bot = TradingBot()
    
    if not bot.initialize():
        console.print("[red]Failed to initialize bot[/red]")
        sys.exit(1)
    
    console.print(f"[blue]Running backtest for {symbol} with {strategy} strategy...[/blue]")
    
    try:
        results = bot.strategy_manager.backtest_strategy(None, strategy)
        
        if 'error' in results:
            console.print(f"[red]Backtest failed: {results['error']}[/red]")
            return
        
        # Display results
        backtest_table = Table(title="Backtest Results")
        backtest_table.add_column("Metric", style="cyan")
        backtest_table.add_column("Value", style="white")
        
        backtest_table.add_row("Strategy", results['strategy'])
        backtest_table.add_row("Total Signals", str(results['total_signals']))
        backtest_table.add_row("Buy Signals", str(results['buy_signals']))
        backtest_table.add_row("Sell Signals", str(results['sell_signals']))
        backtest_table.add_row("Signal Frequency", f"{results['signal_frequency']*100:.1f}%")
        backtest_table.add_row("Avg Confidence", f"{results['avg_confidence']:.2f}")
        
        console.print(backtest_table)
        
    except Exception as e:
        console.print(f"[red]Backtest error: {e}[/red]")

@cli.command()
def strategies():
    """List available trading strategies."""
    bot = TradingBot()
    strategies = bot.strategy_manager.get_available_strategies()
    
    console.print("[blue]Available Trading Strategies:[/blue]")
    for strategy in strategies:
        console.print(f"  • {strategy}")

if __name__ == '__main__':
    cli()