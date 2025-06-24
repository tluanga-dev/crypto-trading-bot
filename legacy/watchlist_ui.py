"""
Professional Watchlist and Market Scanner UI
Rich terminal interface for multi-symbol monitoring and market scanning.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import asyncio

from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Console
from rich.layout import Layout
from rich.align import Align
from rich.bar import Bar
from rich.progress import Progress, BarColumn, TextColumn

from multi_symbol_monitor import get_multi_symbol_monitor, SymbolData, ScanCriteria, SymbolFilter
from market_depth import get_market_depth_visualizer


class WatchlistVisualizer:
    """Creates rich visualizations for watchlist and market scanner."""
    
    def __init__(self):
        self.monitor = get_multi_symbol_monitor()
        self.console = Console()
        self.sort_column = 'change_24h'
        self.sort_descending = True
        
    def create_watchlist_panel(self, max_symbols: int = 20) -> Panel:
        """Create the main watchlist panel."""
        watchlist_data = self.monitor.get_watchlist_data()
        
        if not watchlist_data:
            return Panel(
                "No symbols in watchlist\nUse 'add SYMBOL' to add symbols",
                title="Watchlist",
                border_style="cyan"
            )
        
        # Sort data
        watchlist_data = self._sort_symbols(watchlist_data)[:max_symbols]
        
        # Create table
        table = Table(show_header=True, show_edge=False, pad_edge=False)
        table.add_column("Symbol", style="cyan", width=12)
        table.add_column("Price", style="white", width=10, justify="right")
        table.add_column("24h %", style="white", width=8, justify="right")
        table.add_column("24h Vol", style="white", width=12, justify="right")
        table.add_column("Spread", style="white", width=8, justify="right")
        table.add_column("RSI", style="white", width=6, justify="right")
        table.add_column("Signal", style="white", width=8, justify="center")
        table.add_column("Alerts", style="white", width=6, justify="center")
        
        for data in watchlist_data:
            # Price change color
            change_color = "green" if data.price_change_24h > 0 else "red" if data.price_change_24h < 0 else "white"
            
            # RSI color
            rsi_color = "red" if data.rsi and data.rsi > 70 else "green" if data.rsi and data.rsi < 30 else "yellow"
            rsi_text = f"{data.rsi:.1f}" if data.rsi else "-"
            
            # Signal display
            signal_text = ""
            signal_color = "white"
            if data.signal_action:
                signal_color = "green" if data.signal_action.upper() == "BUY" else "red" if data.signal_action.upper() == "SELL" else "yellow"
                confidence_stars = "★" * min(int(data.signal_confidence or 0 * 5), 5) if data.signal_confidence else ""
                signal_text = f"{data.signal_action.upper()[:3]}{confidence_stars}"
            
            # Alerts indicator
            alerts = []
            if data.has_price_alert:
                alerts.append("💰")
            if data.has_volume_alert:
                alerts.append("📊")
            if data.has_signal_alert:
                alerts.append("🎯")
            alert_text = "".join(alerts) if alerts else "-"
            
            # Spread calculation
            spread_pct = (data.spread / data.last_price * 100) if data.last_price and data.spread else 0
            
            # Volume formatting
            volume_str = self._format_volume(data.volume_24h)
            
            table.add_row(
                f"[bold]{data.symbol}[/bold]",
                f"${data.last_price:.4f}",
                f"[{change_color}]{data.price_change_24h:+.2f}%[/{change_color}]",
                volume_str,
                f"{spread_pct:.3f}%",
                f"[{rsi_color}]{rsi_text}[/{rsi_color}]",
                f"[{signal_color}]{signal_text}[/{signal_color}]",
                alert_text
            )
        
        # Add summary row
        if watchlist_data:
            avg_change = sum(d.price_change_24h for d in watchlist_data) / len(watchlist_data)
            total_volume = sum(d.volume_24h for d in watchlist_data)
            avg_change_color = "green" if avg_change > 0 else "red" if avg_change < 0 else "white"
            
            table.add_row(
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                ""
            )
            table.add_row(
                f"[bold]AVG ({len(watchlist_data)})[/bold]",
                "",
                f"[{avg_change_color}]{avg_change:+.2f}%[/{avg_change_color}]",
                self._format_volume(total_volume),
                "",
                "",
                "",
                ""
            )
        
        return Panel(table, title="📈 Watchlist", border_style="cyan")
    
    def create_market_scanner_panel(self, scan_results: List[SymbolData]) -> Panel:
        """Create market scanner results panel."""
        if not scan_results:
            return Panel(
                "No scan results\nUse 'scan' command to run market scanner",
                title="Market Scanner",
                border_style="yellow"
            )
        
        # Create table
        table = Table(show_header=True, show_edge=False, pad_edge=False)
        table.add_column("Rank", style="dim", width=4)
        table.add_column("Symbol", style="cyan", width=12)
        table.add_column("Price", style="white", width=10, justify="right")
        table.add_column("24h %", style="white", width=8, justify="right")
        table.add_column("Volume", style="white", width=12, justify="right")
        table.add_column("Category", style="white", width=8)
        table.add_column("Flags", style="white", width=15)
        
        for i, data in enumerate(scan_results[:20], 1):  # Top 20 results
            # Price change color
            change_color = "green" if data.price_change_24h > 0 else "red" if data.price_change_24h < 0 else "white"
            
            # Category
            category = SymbolFilter.get_category(data.symbol)
            category_color = {
                "major": "blue",
                "defi": "green", 
                "stable": "yellow",
                "meme": "magenta",
                "alt": "white"
            }.get(category, "white")
            
            # Technical flags
            flags = []
            if data.is_oversold:
                flags.append("[green]OS[/green]")
            if data.is_overbought:
                flags.append("[red]OB[/red]")
            if data.is_trending_up:
                flags.append("[green]↗[/green]")
            if data.is_trending_down:
                flags.append("[red]↘[/red]")
            if data.is_breaking_resistance:
                flags.append("[yellow]⬆RES[/yellow]")
            if data.is_breaking_support:
                flags.append("[yellow]⬇SUP[/yellow]")
            
            flags_text = " ".join(flags) if flags else "-"
            
            table.add_row(
                f"{i}",
                f"[bold]{data.symbol}[/bold]",
                f"${data.last_price:.4f}",
                f"[{change_color}]{data.price_change_24h:+.2f}%[/{change_color}]",
                self._format_volume(data.volume_24h),
                f"[{category_color}]{category.upper()}[/{category_color}]",
                flags_text
            )
        
        scan_time = self.monitor.last_scan_time
        time_str = scan_time.strftime("%H:%M:%S") if scan_time else "Never"
        title = f"🔍 Market Scanner ({len(scan_results)} results) - Last: {time_str}"
        
        return Panel(table, title=title, border_style="yellow")
    
    def create_symbol_detail_panel(self, symbol: str) -> Panel:
        """Create detailed view for a specific symbol."""
        data = self.monitor.symbol_data.get(symbol)
        if not data:
            return Panel(f"No data for {symbol}", title=f"Symbol Details - {symbol}", border_style="red")
        
        # Create detail table
        detail_table = Table(show_header=False, show_edge=False, pad_edge=False)
        detail_table.add_column("Metric", style="cyan", width=20)
        detail_table.add_column("Value", style="white", width=15)
        detail_table.add_column("Status", style="white", width=15)
        
        # Basic info
        change_color = "green" if data.price_change_24h > 0 else "red" if data.price_change_24h < 0 else "white"
        detail_table.add_row("Symbol", f"[bold]{data.symbol}[/bold]", "")
        detail_table.add_row("Price", f"${data.last_price:.4f}", "")
        detail_table.add_row("24h Change", f"[{change_color}]{data.price_change_24h:+.2f}%[/{change_color}]", "")
        detail_table.add_row("24h High", f"${data.high_24h:.4f}", "")
        detail_table.add_row("24h Low", f"${data.low_24h:.4f}", "")
        detail_table.add_row("24h Volume", self._format_volume(data.volume_24h), "")
        
        # Spread info
        spread_pct = (data.spread / data.last_price * 100) if data.last_price and data.spread else 0
        spread_color = "green" if spread_pct < 0.1 else "yellow" if spread_pct < 0.2 else "red"
        detail_table.add_row("Best Bid", f"${data.bid:.4f}", "")
        detail_table.add_row("Best Ask", f"${data.ask:.4f}", "")
        detail_table.add_row("Spread", f"[{spread_color}]{spread_pct:.3f}%[/{spread_color}]", "")
        
        # Technical indicators
        if data.rsi:
            rsi_color = "red" if data.rsi > 70 else "green" if data.rsi < 30 else "yellow"
            rsi_status = "Overbought" if data.rsi > 70 else "Oversold" if data.rsi < 30 else "Neutral"
            detail_table.add_row("RSI", f"[{rsi_color}]{data.rsi:.1f}[/{rsi_color}]", f"[{rsi_color}]{rsi_status}[/{rsi_color}]")
        
        if data.macd is not None:
            macd_color = "green" if data.macd > 0 else "red"
            detail_table.add_row("MACD", f"[{macd_color}]{data.macd:.6f}[/{macd_color}]", "")
        
        # Signal info
        if data.signal_action:
            signal_color = "green" if data.signal_action.upper() == "BUY" else "red" if data.signal_action.upper() == "SELL" else "yellow"
            confidence_pct = (data.signal_confidence or 0) * 100
            detail_table.add_row("Signal", f"[{signal_color}]{data.signal_action.upper()}[/{signal_color}]", 
                               f"[{signal_color}]{confidence_pct:.1f}%[/{signal_color}]")
        
        # Alerts
        alert_count = 0
        if symbol in self.monitor.price_alerts:
            alert_count += len(self.monitor.price_alerts[symbol])
        if symbol in self.monitor.volume_alerts:
            alert_count += 1
        
        detail_table.add_row("Active Alerts", f"{alert_count}", "")
        detail_table.add_row("Trade Count", f"{data.trade_count:,}", "")
        detail_table.add_row("Category", SymbolFilter.get_category(symbol).upper(), "")
        
        # Last update
        if data.last_update:
            time_ago = datetime.now() - data.last_update
            detail_table.add_row("Last Update", f"{time_ago.seconds}s ago", "")
        
        return Panel(detail_table, title=f"📊 Symbol Details - {symbol}", border_style="blue")
    
    def create_alerts_panel(self) -> Panel:
        """Create alerts management panel."""
        # Count alerts
        total_price_alerts = sum(len(alerts) for alerts in self.monitor.price_alerts.values())
        total_volume_alerts = len(self.monitor.volume_alerts)
        total_signal_alerts = len(self.monitor.signal_alerts)
        
        if total_price_alerts == 0 and total_volume_alerts == 0 and total_signal_alerts == 0:
            return Panel(
                "No active alerts\nUse 'alert price SYMBOL PRICE' to set alerts",
                title="Active Alerts",
                border_style="magenta"
            )
        
        # Create alerts table
        alerts_table = Table(show_header=True, show_edge=False, pad_edge=False)
        alerts_table.add_column("Symbol", style="cyan", width=12)
        alerts_table.add_column("Type", style="white", width=8)
        alerts_table.add_column("Target", style="white", width=12, justify="right")
        alerts_table.add_column("Current", style="white", width=12, justify="right")
        alerts_table.add_column("Status", style="white", width=10)
        
        # Add price alerts
        for symbol, alerts in self.monitor.price_alerts.items():
            current_price = self.monitor.symbol_data.get(symbol, SymbolData(symbol="")).last_price
            
            for alert in alerts:
                alert_type = f"Price {alert['type']}"
                target_price = alert['price']
                
                # Determine status
                if alert['type'] == 'above':
                    status = "✅ TRIGGERED" if current_price >= target_price else "⏳ Waiting"
                    status_color = "green" if current_price >= target_price else "yellow"
                else:  # below
                    status = "✅ TRIGGERED" if current_price <= target_price else "⏳ Waiting"
                    status_color = "green" if current_price <= target_price else "yellow"
                
                alerts_table.add_row(
                    symbol,
                    alert_type,
                    f"${target_price:.4f}",
                    f"${current_price:.4f}",
                    f"[{status_color}]{status}[/{status_color}]"
                )
        
        # Add volume alerts
        for symbol, alert in self.monitor.volume_alerts.items():
            current_volume = self.monitor.symbol_data.get(symbol, SymbolData(symbol="")).volume_24h
            threshold = alert['threshold']
            
            status = "✅ TRIGGERED" if current_volume > threshold else "⏳ Waiting"
            status_color = "green" if current_volume > threshold else "yellow"
            
            alerts_table.add_row(
                symbol,
                "Volume",
                self._format_volume(threshold),
                self._format_volume(current_volume),
                f"[{status_color}]{status}[/{status_color}]"
            )
        
        title = f"🚨 Active Alerts ({total_price_alerts + total_volume_alerts + total_signal_alerts})"
        return Panel(alerts_table, title=title, border_style="magenta")
    
    def create_performance_panel(self) -> Panel:
        """Create monitoring performance panel."""
        stats = self.monitor.get_performance_stats()
        
        perf_table = Table(show_header=False, show_edge=False, pad_edge=False)
        perf_table.add_column("Metric", style="cyan", width=20)
        perf_table.add_column("Value", style="white")
        
        perf_table.add_row("Monitored Symbols", f"{stats['monitored_symbols']}")
        perf_table.add_row("Watchlist Size", f"{stats['watchlist_size']}")
        perf_table.add_row("Updates/Second", f"{stats['updates_per_second']:.1f}")
        perf_table.add_row("Total Updates", f"{stats['total_updates']:,}")
        perf_table.add_row("Uptime", f"{stats['uptime_seconds']:.0f}s")
        perf_table.add_row("Price Alerts", f"{stats['active_price_alerts']}")
        perf_table.add_row("Volume Alerts", f"{stats['active_volume_alerts']}")
        
        if stats['last_scan_time']:
            scan_age = (datetime.now() - stats['last_scan_time']).seconds
            perf_table.add_row("Last Scan", f"{scan_age}s ago")
            perf_table.add_row("Scan Results", f"{stats['scan_results_count']}")
        
        return Panel(perf_table, title="⚡ Performance", border_style="green")
    
    def _sort_symbols(self, symbols: List[SymbolData]) -> List[SymbolData]:
        """Sort symbols by the current sort column."""
        if self.sort_column == 'symbol':
            return sorted(symbols, key=lambda x: x.symbol, reverse=self.sort_descending)
        elif self.sort_column == 'price':
            return sorted(symbols, key=lambda x: x.last_price, reverse=self.sort_descending)
        elif self.sort_column == 'change_24h':
            return sorted(symbols, key=lambda x: x.price_change_24h, reverse=self.sort_descending)
        elif self.sort_column == 'volume':
            return sorted(symbols, key=lambda x: x.volume_24h, reverse=self.sort_descending)
        else:
            return symbols
    
    def set_sort(self, column: str, descending: bool = True):
        """Set the sort column and order."""
        self.sort_column = column
        self.sort_descending = descending
    
    def _format_volume(self, volume: float) -> str:
        """Format volume with appropriate units."""
        if volume >= 1_000_000_000:
            return f"{volume / 1_000_000_000:.2f}B"
        elif volume >= 1_000_000:
            return f"{volume / 1_000_000:.1f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.1f}K"
        else:
            return f"{volume:.0f}"


# Singleton instance
_watchlist_visualizer: Optional[WatchlistVisualizer] = None

def get_watchlist_visualizer() -> WatchlistVisualizer:
    """Get the singleton watchlist visualizer."""
    global _watchlist_visualizer
    if _watchlist_visualizer is None:
        _watchlist_visualizer = WatchlistVisualizer()
    return _watchlist_visualizer