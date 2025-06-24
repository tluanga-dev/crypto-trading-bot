"""
Test script to validate professional terminal dependencies and basic functionality.
"""

import sys
import asyncio
import traceback
from rich.console import Console

console = Console()

def test_imports():
    """Test all imports for the professional terminal."""
    console.print("[cyan]🔍 Testing Professional Trading Terminal Dependencies...[/cyan]")
    
    try:
        console.print("✓ Testing basic imports...")
        import asyncio
        import time
        import json
        from datetime import datetime
        from typing import Dict, Optional, List
        console.print("  [green]✓ Basic Python modules[/green]")
        
        console.print("✓ Testing Rich UI components...")
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.layout import Layout
        from rich.text import Text
        from rich.live import Live
        from rich.align import Align
        console.print("  [green]✓ Rich UI components[/green]")
        
        console.print("✓ Testing Click CLI...")
        import click
        console.print("  [green]✓ Click CLI[/green]")
        
        console.print("✓ Testing WebSocket support...")
        import websockets
        console.print("  [green]✓ WebSocket support[/green]")
        
        console.print("✓ Testing professional terminal modules...")
        
        try:
            from websocket_manager import get_websocket_manager
            console.print("  [green]✓ WebSocket Manager[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠ WebSocket Manager: {e}[/yellow]")
        
        try:
            from market_depth import get_market_depth_visualizer
            console.print("  [green]✓ Market Depth Visualizer[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠ Market Depth: {e}[/yellow]")
        
        try:
            from multi_symbol_monitor import get_multi_symbol_monitor
            console.print("  [green]✓ Multi-Symbol Monitor[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠ Multi-Symbol Monitor: {e}[/yellow]")
        
        try:
            from watchlist_ui import get_watchlist_visualizer
            console.print("  [green]✓ Watchlist UI[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠ Watchlist UI: {e}[/yellow]")
        
        try:
            from advanced_charting import get_advanced_chart_renderer
            console.print("  [green]✓ Advanced Charting[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠ Advanced Charting: {e}[/yellow]")
        
        try:
            from order_management import get_order_manager
            console.print("  [green]✓ Order Management[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠ Order Management: {e}[/yellow]")
        
        console.print("✓ Testing existing modules...")
        from trading_service import create_trading_service
        from events import get_event_subscriber
        from config import Config
        from logger import get_logger
        console.print("  [green]✓ Core trading modules[/green]")
        
        console.print("\n[green]🎉 All critical dependencies are available![/green]")
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Import error: {e}[/red]")
        console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return False

async def test_basic_functionality():
    """Test basic async functionality."""
    console.print("\n[cyan]🔍 Testing Basic Async Functionality...[/cyan]")
    
    try:
        # Test WebSocket manager creation
        console.print("✓ Testing WebSocket manager...")
        from websocket_manager import get_websocket_manager
        ws_manager = get_websocket_manager()
        console.print("  [green]✓ WebSocket manager created[/green]")
        
        # Test trading service creation
        console.print("✓ Testing trading service...")
        from trading_service import create_trading_service
        trading_service = create_trading_service(10000.0)
        console.print("  [green]✓ Trading service created[/green]")
        
        # Test configuration
        console.print("✓ Testing configuration...")
        from config import Config
        console.print(f"  [green]✓ Trading mode: {Config.TRADING_MODE}[/green]")
        console.print(f"  [green]✓ Default symbol: {Config.DEFAULT_SYMBOL}[/green]")
        
        console.print("\n[green]🎉 Basic functionality test passed![/green]")
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Functionality test failed: {e}[/red]")
        console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return False

def test_environment():
    """Test environment configuration."""
    console.print("\n[cyan]🔍 Testing Environment Configuration...[/cyan]")
    
    try:
        import os
        from config import Config
        
        # Check if .env file exists
        if os.path.exists('.env'):
            console.print("  [green]✓ .env file found[/green]")
        else:
            console.print("  [yellow]⚠ .env file not found (using defaults)[/yellow]")
        
        # Check trading mode
        console.print(f"  [green]✓ Trading mode: {Config.TRADING_MODE}[/green]")
        
        # Check API keys (don't print actual values)
        if hasattr(Config, 'BINANCE_API_KEY') and Config.BINANCE_API_KEY:
            console.print("  [green]✓ Binance API key configured[/green]")
        else:
            console.print("  [yellow]⚠ Binance API key not configured (testnet mode recommended)[/yellow]")
        
        console.print("\n[green]🎉 Environment configuration checked![/green]")
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Environment test failed: {e}[/red]")
        return False

async def main():
    """Main test function."""
    console.print("[bold blue]🚀 Professional Trading Terminal - Dependency Test[/bold blue]")
    console.print("=" * 60)
    
    # Test imports
    import_success = test_imports()
    
    if not import_success:
        console.print("\n[red]❌ Import tests failed. Please install missing dependencies.[/red]")
        console.print("[yellow]Run: pip install -r requirements.txt[/yellow]")
        sys.exit(1)
    
    # Test environment
    env_success = test_environment()
    
    # Test basic functionality
    func_success = await test_basic_functionality()
    
    console.print("\n" + "=" * 60)
    
    if import_success and func_success:
        console.print("[bold green]🎉 All tests passed! Ready to run Professional Trading Terminal![/bold green]")
        console.print("\n[cyan]To launch the terminal, run:[/cyan]")
        console.print("[bold]python professional_terminal.py --symbol ETHUSDT --balance 50000[/bold]")
    else:
        console.print("[bold red]❌ Some tests failed. Please check the issues above.[/bold red]")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())