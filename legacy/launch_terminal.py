#!/usr/bin/env python3
"""
Simple launcher for the Professional Trading Terminal
Handles async execution properly and provides clear error messages.
"""

import sys
import asyncio
import argparse
from rich.console import Console

console = Console()

async def launch_terminal(symbol: str = "BTCUSDT", balance: float = 10000.0):
    """Launch the professional trading terminal."""
    try:
        console.print("[cyan]🚀 Launching Professional Trading Terminal...[/cyan]")
        
        # Import the terminal class
        from professional_terminal import ProfessionalTradingTerminal
        
        # Create and configure terminal
        terminal = ProfessionalTradingTerminal(balance)
        terminal.current_symbol = symbol.upper()
        terminal.chart_symbol = symbol.upper()
        
        console.print(f"[green]✓ Terminal configured for {symbol.upper()} with ${balance:,.2f} balance[/green]")
        
        # Run the terminal
        await terminal.run()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 Terminal stopped by user[/yellow]")
    except ImportError as e:
        console.print(f"\n[red]❌ Import error: {e}[/red]")
        console.print("[yellow]💡 Make sure all dependencies are installed: pip install -r requirements.txt[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error launching terminal: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Professional Trading Terminal - Fox Pro Style",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_terminal.py
  python launch_terminal.py --symbol ETHUSDT --balance 50000
  python launch_terminal.py --symbol BNBUSDT --balance 25000

Navigation:
  1-5: Switch tabs (Trading/Watchlist/Charts/Orders/Scanner)
  S: Change symbol
  T: Change timeframe  
  O: Place order
  Q: Quit

Features:
  - Real-time WebSocket data feeds
  - Professional order book visualization
  - Multi-symbol watchlist and scanner
  - Advanced charting with technical analysis
  - Professional order management
  - Risk management and alerts
        """
    )
    
    parser.add_argument(
        '--symbol', 
        default='BTCUSDT',
        help='Trading symbol (default: BTCUSDT)'
    )
    
    parser.add_argument(
        '--balance', 
        type=float,
        default=10000.0,
        help='Initial balance (default: 10000.0)'
    )
    
    parser.add_argument(
        '--test-deps',
        action='store_true',
        help='Test dependencies only (don\'t launch terminal)'
    )
    
    args = parser.parse_args()
    
    # Test dependencies if requested
    if args.test_deps:
        console.print("[cyan]🔍 Testing dependencies...[/cyan]")
        try:
            from test_terminal import test_imports
            if test_imports():
                console.print("[green]🎉 All dependencies are working![/green]")
                sys.exit(0)
            else:
                console.print("[red]❌ Dependency test failed[/red]")
                sys.exit(1)
        except ImportError:
            console.print("[red]❌ Cannot import test module[/red]")
            sys.exit(1)
    
    # Show startup info
    console.print("[bold blue]🏛️ Professional Trading Terminal[/bold blue]")
    console.print(f"Symbol: [bold]{args.symbol}[/bold] | Balance: [bold]${args.balance:,.2f}[/bold]")
    console.print("[dim]Press Ctrl+C to stop the terminal[/dim]\n")
    
    # Launch terminal
    try:
        asyncio.run(launch_terminal(args.symbol, args.balance))
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Failed to start: {e}[/red]")
        sys.exit(1)

if __name__ == '__main__':
    main()