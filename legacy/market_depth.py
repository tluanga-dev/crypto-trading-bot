"""
Market Depth (Order Book) Visualization Module
Professional order book display with bid/ask levels, market depth, and liquidity analysis.
"""

from typing import List, Tuple, Dict, Optional
from datetime import datetime
from collections import deque
import statistics

from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.bar import Bar
from rich.progress import Progress, BarColumn, TextColumn
from rich.console import Console
from rich.align import Align

from websocket_manager import get_websocket_manager
from events import get_event_subscriber


class OrderBookLevel:
    """Represents a single level in the order book."""
    
    def __init__(self, price: float, quantity: float, side: str):
        self.price = price
        self.quantity = quantity
        self.side = side  # 'bid' or 'ask'
        self.timestamp = datetime.now()
    
    @property
    def total_value(self) -> float:
        """Calculate total value at this level."""
        return self.price * self.quantity


class MarketDepthAnalyzer:
    """Analyzes market depth and liquidity metrics."""
    
    def __init__(self, max_history: int = 100):
        self.spread_history = deque(maxlen=max_history)
        self.depth_history = deque(maxlen=max_history)
        self.imbalance_history = deque(maxlen=max_history)
        
    def analyze_order_book(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]) -> Dict:
        """Analyze order book for liquidity and market microstructure."""
        if not bids or not asks:
            return {}
        
        # Convert to OrderBookLevel objects
        bid_levels = [OrderBookLevel(price, qty, 'bid') for price, qty in bids]
        ask_levels = [OrderBookLevel(price, qty, 'ask') for price, qty in asks]
        
        # Best bid and ask
        best_bid = max(bid_levels, key=lambda x: x.price)
        best_ask = min(ask_levels, key=lambda x: x.price)
        
        # Spread calculations
        spread_absolute = best_ask.price - best_bid.price
        spread_percentage = (spread_absolute / best_bid.price) * 100
        
        # Market depth calculations
        bid_depth_5 = sum(level.total_value for level in bid_levels[:5])
        ask_depth_5 = sum(level.total_value for level in ask_levels[:5])
        total_depth_5 = bid_depth_5 + ask_depth_5
        
        bid_depth_10 = sum(level.total_value for level in bid_levels[:10])
        ask_depth_10 = sum(level.total_value for level in ask_levels[:10])
        total_depth_10 = bid_depth_10 + ask_depth_10
        
        # Market imbalance
        bid_volume = sum(level.quantity for level in bid_levels[:10])
        ask_volume = sum(level.quantity for level in ask_levels[:10])
        total_volume = bid_volume + ask_volume
        imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
        
        # Liquidity score (higher is better)
        liquidity_score = total_depth_10 / spread_absolute if spread_absolute > 0 else 0
        
        # Update history
        self.spread_history.append(spread_percentage)
        self.depth_history.append(total_depth_10)
        self.imbalance_history.append(imbalance)
        
        # Average calculations
        avg_spread = statistics.mean(self.spread_history) if self.spread_history else 0
        avg_depth = statistics.mean(self.depth_history) if self.depth_history else 0
        avg_imbalance = statistics.mean(self.imbalance_history) if self.imbalance_history else 0
        
        return {
            'best_bid': best_bid.price,
            'best_ask': best_ask.price,
            'spread_absolute': spread_absolute,
            'spread_percentage': spread_percentage,
            'bid_depth_5': bid_depth_5,
            'ask_depth_5': ask_depth_5,
            'total_depth_5': total_depth_5,
            'bid_depth_10': bid_depth_10,
            'ask_depth_10': ask_depth_10,
            'total_depth_10': total_depth_10,
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'imbalance': imbalance,
            'liquidity_score': liquidity_score,
            'avg_spread': avg_spread,
            'avg_depth': avg_depth,
            'avg_imbalance': avg_imbalance
        }


class MarketDepthVisualizer:
    """Creates rich visualizations for market depth and order book."""
    
    def __init__(self):
        self.analyzer = MarketDepthAnalyzer()
        self.console = Console()
        
    def create_order_book_panel(self, symbol: str, bids: List[Tuple[float, float]], 
                               asks: List[Tuple[float, float]], max_levels: int = 10) -> Panel:
        """Create a professional order book visualization panel."""
        if not bids or not asks:
            return Panel("No order book data available", title=f"Order Book - {symbol}", border_style="yellow")
        
        # Limit to max_levels
        bids = bids[:max_levels]
        asks = asks[:max_levels]
        
        # Analyze the order book
        analysis = self.analyzer.analyze_order_book(bids, asks)
        
        # Create the order book table
        table = Table(show_header=True, show_edge=False, pad_edge=False)
        table.add_column("Total", style="dim", width=10, justify="right")
        table.add_column("Size", style="red", width=12, justify="right")
        table.add_column("Price", style="white", width=12, justify="right")
        table.add_column("Price", style="white", width=12, justify="right")
        table.add_column("Size", style="green", width=12, justify="right")
        table.add_column("Total", style="dim", width=10, justify="right")
        
        # Calculate cumulative volumes for depth visualization
        ask_cumulative = []
        total_ask = 0
        for price, qty in reversed(asks):
            total_ask += qty
            ask_cumulative.insert(0, total_ask)
        
        bid_cumulative = []
        total_bid = 0
        for price, qty in bids:
            total_bid += qty
            bid_cumulative.append(total_bid)
        
        # Find the maximum volumes for scaling bars
        max_ask_vol = max([qty for _, qty in asks]) if asks else 1
        max_bid_vol = max([qty for _, qty in bids]) if bids else 1
        max_vol = max(max_ask_vol, max_bid_vol)
        
        # Add asks (top of book, highest prices first)
        for i, (price, qty) in enumerate(reversed(asks)):
            total = ask_cumulative[len(asks) - 1 - i]
            
            # Create volume bar
            bar_width = int((qty / max_vol) * 10) if max_vol > 0 else 0
            volume_bar = "█" * bar_width + "░" * (10 - bar_width)
            
            table.add_row(
                f"{total:.2f}",
                f"[red]{volume_bar}[/red] {qty:.4f}",
                f"[red]{price:.4f}[/red]",
                "",
                "",
                ""
            )
        
        # Add spread indicator
        if 'spread_absolute' in analysis:
            spread_color = "green" if analysis['spread_percentage'] < 0.1 else "yellow" if analysis['spread_percentage'] < 0.2 else "red"
            table.add_row(
                "",
                "",
                f"[{spread_color}]↕ {analysis['spread_absolute']:.4f}[/{spread_color}]",
                f"[{spread_color}]({analysis['spread_percentage']:.3f}%)[/{spread_color}]",
                "",
                ""
            )
        
        # Add bids (bottom of book, highest prices first)
        for i, (price, qty) in enumerate(bids):
            total = bid_cumulative[i]
            
            # Create volume bar
            bar_width = int((qty / max_vol) * 10) if max_vol > 0 else 0
            volume_bar = "█" * bar_width + "░" * (10 - bar_width)
            
            table.add_row(
                "",
                "",
                "",
                f"[green]{price:.4f}[/green]",
                f"[green]{volume_bar}[/green] {qty:.4f}",
                f"{total:.2f}"
            )
        
        # Create title with spread info
        title = f"Order Book - {symbol}"
        if 'spread_percentage' in analysis:
            title += f" | Spread: {analysis['spread_percentage']:.3f}%"
        
        return Panel(table, title=title, border_style="blue")
    
    def create_market_depth_panel(self, symbol: str, bids: List[Tuple[float, float]], 
                                 asks: List[Tuple[float, float]]) -> Panel:
        """Create market depth analysis panel."""
        if not bids or not asks:
            return Panel("No market depth data available", title=f"Market Depth - {symbol}", border_style="cyan")
        
        analysis = self.analyzer.analyze_order_book(bids, asks)
        
        # Create depth analysis table
        depth_table = Table(show_header=False, show_edge=False, pad_edge=False)
        depth_table.add_column("Metric", style="cyan", width=20)
        depth_table.add_column("Value", style="white", width=15)
        depth_table.add_column("Avg", style="dim", width=15)
        
        # Depth metrics
        depth_table.add_row("Best Bid", f"${analysis.get('best_bid', 0):.4f}", "")
        depth_table.add_row("Best Ask", f"${analysis.get('best_ask', 0):.4f}", "")
        depth_table.add_row("Spread", f"{analysis.get('spread_percentage', 0):.3f}%", 
                           f"{analysis.get('avg_spread', 0):.3f}%")
        
        # Volume imbalance
        imbalance = analysis.get('imbalance', 0)
        imbalance_color = "green" if imbalance > 0.1 else "red" if imbalance < -0.1 else "yellow"
        depth_table.add_row("Volume Imbalance", 
                           f"[{imbalance_color}]{imbalance*100:+.1f}%[/{imbalance_color}]",
                           f"{analysis.get('avg_imbalance', 0)*100:+.1f}%")
        
        # Depth metrics
        depth_table.add_row("Bid Depth (5)", f"${analysis.get('bid_depth_5', 0):,.0f}", "")
        depth_table.add_row("Ask Depth (5)", f"${analysis.get('ask_depth_5', 0):,.0f}", "")
        depth_table.add_row("Total Depth (10)", f"${analysis.get('total_depth_10', 0):,.0f}", 
                           f"${analysis.get('avg_depth', 0):,.0f}")
        
        # Liquidity score
        liquidity_score = analysis.get('liquidity_score', 0)
        liquidity_color = "green" if liquidity_score > 1000000 else "yellow" if liquidity_score > 100000 else "red"
        depth_table.add_row("Liquidity Score", f"[{liquidity_color}]{liquidity_score:,.0f}[/{liquidity_color}]", "")
        
        return Panel(depth_table, title=f"Market Depth Analysis - {symbol}", border_style="cyan")
    
    def create_depth_chart(self, symbol: str, bids: List[Tuple[float, float]], 
                          asks: List[Tuple[float, float]], height: int = 15) -> Panel:
        """Create ASCII depth chart visualization."""
        if not bids or not asks:
            return Panel("No depth chart data available", title=f"Depth Chart - {symbol}", border_style="magenta")
        
        # Limit to reasonable number of levels
        bids = bids[:20]
        asks = asks[:20]
        
        # Calculate cumulative volumes
        bid_levels = []
        cumulative_bid = 0
        for price, qty in bids:
            cumulative_bid += qty
            bid_levels.append((price, cumulative_bid))
        
        ask_levels = []
        cumulative_ask = 0
        for price, qty in reversed(asks):
            cumulative_ask += qty
            ask_levels.append((price, cumulative_ask))
        ask_levels.reverse()
        
        # Find price range
        all_prices = [price for price, _ in bid_levels + ask_levels]
        min_price = min(all_prices)
        max_price = max(all_prices)
        price_range = max_price - min_price
        
        if price_range == 0:
            return Panel("Insufficient price range for chart", title=f"Depth Chart - {symbol}", border_style="magenta")
        
        # Find max volume for scaling
        all_volumes = [vol for _, vol in bid_levels + ask_levels]
        max_volume = max(all_volumes) if all_volumes else 1
        
        # Create chart lines
        chart_lines = []
        chart_width = 60
        
        for i in range(height):
            # Calculate price level for this line
            price = max_price - (i / height) * price_range
            
            # Find volumes at this price level
            bid_vol = 0
            ask_vol = 0
            
            # Find closest bid level
            for bid_price, bid_volume in bid_levels:
                if bid_price <= price:
                    bid_vol = bid_volume
                    break
            
            # Find closest ask level  
            for ask_price, ask_volume in ask_levels:
                if ask_price >= price:
                    ask_vol = ask_volume
                    break
            
            # Scale volumes to chart width
            bid_width = int((bid_vol / max_volume) * chart_width / 2) if max_volume > 0 else 0
            ask_width = int((ask_vol / max_volume) * chart_width / 2) if max_volume > 0 else 0
            
            # Create the line
            bid_bar = "█" * bid_width
            ask_bar = "█" * ask_width
            
            # Center alignment
            bid_section = f"{bid_bar:>{chart_width//2}}"
            ask_section = f"{ask_bar:<{chart_width//2}}"
            
            price_label = f"{price:.4f}"
            line = f"[green]{bid_section}[/green][white]|[/white][red]{ask_section}[/red] {price_label}"
            chart_lines.append(line)
        
        # Add labels
        chart_lines.append("")
        chart_lines.append(f"{'BIDS':<{chart_width//2}} {'ASKS':<{chart_width//2}}")
        chart_lines.append(f"{'(green)':<{chart_width//2}} {'(red)':<{chart_width//2}}")
        
        chart_content = "\n".join(chart_lines)
        return Panel(chart_content, title=f"Cumulative Depth Chart - {symbol}", border_style="magenta")
    
    def create_market_pulse_panel(self, symbol: str) -> Panel:
        """Create a market pulse panel showing recent order book activity."""
        ws_manager = get_websocket_manager()
        recent_trades = ws_manager.get_recent_trades(symbol, 10)
        
        if not recent_trades:
            return Panel("No recent trade data", title=f"Market Pulse - {symbol}", border_style="yellow")
        
        # Create trade flow visualization
        pulse_table = Table(show_header=True, show_edge=False, pad_edge=False)
        pulse_table.add_column("Time", style="dim", width=8)
        pulse_table.add_column("Side", style="white", width=4)
        pulse_table.add_column("Price", style="white", width=10, justify="right")
        pulse_table.add_column("Size", style="white", width=10, justify="right")
        pulse_table.add_column("Value", style="white", width=12, justify="right")
        
        total_buy_volume = 0
        total_sell_volume = 0
        total_buy_value = 0
        total_sell_value = 0
        
        for trade in reversed(recent_trades[-10:]):  # Show last 10 trades
            time_str = trade['timestamp'].strftime("%H:%M:%S")
            is_buy = not trade['is_buyer_maker']  # Market buy if buyer is not maker
            side = "BUY" if is_buy else "SELL"
            side_color = "green" if is_buy else "red"
            
            price = trade['price']
            size = trade['quantity']
            value = price * size
            
            if is_buy:
                total_buy_volume += size
                total_buy_value += value
            else:
                total_sell_volume += size
                total_sell_value += value
            
            pulse_table.add_row(
                time_str,
                f"[{side_color}]{side}[/{side_color}]",
                f"{price:.4f}",
                f"{size:.4f}",
                f"${value:.2f}"
            )
        
        # Add summary
        total_volume = total_buy_volume + total_sell_volume
        buy_ratio = (total_buy_volume / total_volume * 100) if total_volume > 0 else 0
        sell_ratio = (total_sell_volume / total_volume * 100) if total_volume > 0 else 0
        
        pulse_table.add_row("", "", "", "", "")
        pulse_table.add_row(
            "SUMMARY",
            f"[green]{buy_ratio:.1f}%[/green]/[red]{sell_ratio:.1f}%[/red]",
            "",
            f"{total_volume:.4f}",
            f"${total_buy_value + total_sell_value:.2f}"
        )
        
        return Panel(pulse_table, title=f"Market Pulse - {symbol} (Last 10 Trades)", border_style="yellow")


# Singleton instance
_market_depth_visualizer: Optional[MarketDepthVisualizer] = None

def get_market_depth_visualizer() -> MarketDepthVisualizer:
    """Get the singleton market depth visualizer."""
    global _market_depth_visualizer
    if _market_depth_visualizer is None:
        _market_depth_visualizer = MarketDepthVisualizer()
    return _market_depth_visualizer