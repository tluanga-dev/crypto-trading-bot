"""
Advanced Charting System with Multiple Timeframes
Professional ASCII charts with technical indicators, volume analysis, and multi-timeframe support.
"""

import math
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass
import statistics

from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Console
from rich.layout import Layout
from rich.align import Align

from websocket_manager import get_websocket_manager
from data_analyzer import DataAnalyzer


@dataclass
class CandleData:
    """Represents a single candlestick."""
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int
    is_bullish: bool = None
    body_size: float = None
    wick_top: float = None
    wick_bottom: float = None
    
    def __post_init__(self):
        self.is_bullish = self.close > self.open
        self.body_size = abs(self.close - self.open)
        self.wick_top = self.high - max(self.open, self.close)
        self.wick_bottom = min(self.open, self.close) - self.low


@dataclass
class TechnicalLevel:
    """Represents a technical analysis level."""
    price: float
    level_type: str  # 'support', 'resistance', 'pivot'
    strength: float  # 0.0 to 1.0
    touches: int
    last_touch: datetime


class TechnicalAnalyzer:
    """Advanced technical analysis for charting."""
    
    def __init__(self):
        self.support_resistance_cache = {}
        self.trend_lines_cache = {}
        
    def find_support_resistance(self, candles: List[CandleData], lookback: int = 20) -> List[TechnicalLevel]:
        """Find support and resistance levels."""
        if len(candles) < lookback:
            return []
        
        levels = []
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        
        # Find local maxima (resistance)
        for i in range(lookback, len(candles) - lookback):
            current_high = candles[i].high
            is_resistance = True
            
            # Check if it's a local maximum
            for j in range(i - lookback, i + lookback + 1):
                if j != i and candles[j].high > current_high:
                    is_resistance = False
                    break
            
            if is_resistance:
                # Count how many times this level was tested
                touches = sum(1 for c in candles if abs(c.high - current_high) / current_high < 0.005)
                strength = min(touches / 5.0, 1.0)  # Normalize to 0-1
                
                levels.append(TechnicalLevel(
                    price=current_high,
                    level_type='resistance',
                    strength=strength,
                    touches=touches,
                    last_touch=candles[i].close_time
                ))
        
        # Find local minima (support)
        for i in range(lookback, len(candles) - lookback):
            current_low = candles[i].low
            is_support = True
            
            # Check if it's a local minimum
            for j in range(i - lookback, i + lookback + 1):
                if j != i and candles[j].low < current_low:
                    is_support = False
                    break
            
            if is_support:
                # Count how many times this level was tested
                touches = sum(1 for c in candles if abs(c.low - current_low) / current_low < 0.005)
                strength = min(touches / 5.0, 1.0)  # Normalize to 0-1
                
                levels.append(TechnicalLevel(
                    price=current_low,
                    level_type='support',
                    strength=strength,
                    touches=touches,
                    last_touch=candles[i].close_time
                ))
        
        # Sort by strength and return top levels
        levels.sort(key=lambda x: x.strength, reverse=True)
        return levels[:10]  # Return top 10 levels
    
    def detect_patterns(self, candles: List[CandleData]) -> Dict[str, Any]:
        """Detect common candlestick patterns."""
        if len(candles) < 3:
            return {}
        
        patterns = {}
        recent_candles = candles[-3:]  # Look at last 3 candles
        
        # Doji pattern
        last_candle = recent_candles[-1]
        if last_candle.body_size / last_candle.close < 0.01:  # Body is <1% of price
            patterns['doji'] = {
                'type': 'reversal',
                'strength': 0.7,
                'description': 'Doji - Indecision'
            }
        
        # Hammer/Hanging Man
        if (last_candle.wick_bottom > last_candle.body_size * 2 and 
            last_candle.wick_top < last_candle.body_size * 0.5):
            pattern_type = 'hammer' if last_candle.is_bullish else 'hanging_man'
            patterns[pattern_type] = {
                'type': 'reversal',
                'strength': 0.8,
                'description': f'{pattern_type.replace("_", " ").title()}'
            }
        
        # Shooting Star
        if (last_candle.wick_top > last_candle.body_size * 2 and 
            last_candle.wick_bottom < last_candle.body_size * 0.5):
            patterns['shooting_star'] = {
                'type': 'reversal',
                'strength': 0.8,
                'description': 'Shooting Star'
            }
        
        # Engulfing patterns (requires 2 candles)
        if len(recent_candles) >= 2:
            prev_candle = recent_candles[-2]
            
            # Bullish engulfing
            if (not prev_candle.is_bullish and last_candle.is_bullish and
                last_candle.open < prev_candle.close and last_candle.close > prev_candle.open):
                patterns['bullish_engulfing'] = {
                    'type': 'reversal',
                    'strength': 0.9,
                    'description': 'Bullish Engulfing'
                }
            
            # Bearish engulfing
            if (prev_candle.is_bullish and not last_candle.is_bullish and
                last_candle.open > prev_candle.close and last_candle.close < prev_candle.open):
                patterns['bearish_engulfing'] = {
                    'type': 'reversal',
                    'strength': 0.9,
                    'description': 'Bearish Engulfing'
                }
        
        return patterns
    
    def calculate_trend_strength(self, candles: List[CandleData], period: int = 20) -> Dict[str, float]:
        """Calculate trend strength indicators."""
        if len(candles) < period:
            return {'trend': 0.0, 'strength': 0.0}
        
        recent_candles = candles[-period:]
        closes = [c.close for c in recent_candles]
        
        # Calculate linear regression
        x_values = list(range(len(closes)))
        n = len(closes)
        
        sum_x = sum(x_values)
        sum_y = sum(closes)
        sum_xy = sum(x * y for x, y in zip(x_values, closes))
        sum_x2 = sum(x * x for x in x_values)
        
        # Linear regression slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # R-squared for trend strength
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in closes)
        
        # Predicted values
        intercept = (sum_y - slope * sum_x) / n
        y_pred = [slope * x + intercept for x in x_values]
        ss_res = sum((y - y_p) ** 2 for y, y_p in zip(closes, y_pred))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Normalize slope to trend direction
        price_range = max(closes) - min(closes)
        normalized_slope = slope / (price_range / period) if price_range > 0 else 0
        
        return {
            'trend': max(-1.0, min(1.0, normalized_slope)),  # -1 (down) to +1 (up)
            'strength': max(0.0, min(1.0, r_squared))  # 0 (weak) to 1 (strong)
        }


class AdvancedChartRenderer:
    """Renders advanced ASCII charts with technical analysis."""
    
    def __init__(self, width: int = 80, height: int = 20):
        self.width = width
        self.height = height
        self.analyzer = TechnicalAnalyzer()
        self.data_analyzer = DataAnalyzer()
        
    def render_candlestick_chart(self, candles: List[CandleData], symbol: str, 
                                interval: str = "1m", show_volume: bool = True) -> Panel:
        """Render advanced candlestick chart with technical analysis."""
        if not candles:
            return Panel("No data available", title=f"{symbol} Chart", border_style="red")
        
        # Limit candles to chart width
        display_candles = candles[-self.width:]
        
        # Find price range
        all_prices = []
        for candle in display_candles:
            all_prices.extend([candle.high, candle.low])
        
        if not all_prices:
            return Panel("Insufficient data", title=f"{symbol} Chart", border_style="red")
        
        price_min = min(all_prices)
        price_max = max(all_prices)
        price_range = price_max - price_min if price_max > price_min else 1
        
        # Find technical levels
        tech_levels = self.analyzer.find_support_resistance(candles)
        
        # Calculate technical indicators
        trend_data = self.analyzer.calculate_trend_strength(candles)
        patterns = self.analyzer.detect_patterns(candles)
        
        # Create chart matrix
        chart_height = self.height - 4  # Reserve space for volume and labels
        chart = [[' ' for _ in range(self.width)] for _ in range(chart_height)]
        
        # Draw candlesticks
        for i, candle in enumerate(display_candles):
            if i >= self.width:
                break
            
            # Scale prices to chart height
            open_y = int((price_max - candle.open) / price_range * (chart_height - 1))
            close_y = int((price_max - candle.close) / price_range * (chart_height - 1))
            high_y = int((price_max - candle.high) / price_range * (chart_height - 1))
            low_y = int((price_max - candle.low) / price_range * (chart_height - 1))
            
            # Ensure values are within bounds
            open_y = max(0, min(chart_height - 1, open_y))
            close_y = max(0, min(chart_height - 1, close_y))
            high_y = max(0, min(chart_height - 1, high_y))
            low_y = max(0, min(chart_height - 1, low_y))
            
            # Draw wicks (thin lines)
            for y in range(high_y, low_y + 1):
                if y < chart_height:
                    chart[y][i] = '│'
            
            # Draw body
            body_top = min(open_y, close_y)
            body_bottom = max(open_y, close_y)
            
            if candle.is_bullish:
                body_char = '█'  # Solid for bullish
            else:
                body_char = '░'  # Hollow for bearish
            
            # If body is just one pixel, use special character
            if body_top == body_bottom:
                chart[body_top][i] = '─'  # Doji line
            else:
                for y in range(body_top, body_bottom + 1):
                    if y < chart_height:
                        chart[y][i] = body_char
        
        # Draw support/resistance levels
        for level in tech_levels[:5]:  # Show top 5 levels
            level_y = int((price_max - level.price) / price_range * (chart_height - 1))
            if 0 <= level_y < chart_height:
                # Draw horizontal line
                for x in range(self.width):
                    if chart[level_y][x] == ' ':
                        chart[level_y][x] = '─' if level.level_type == 'support' else '═'
        
        # Convert chart to text with colors
        chart_lines = []
        for row in chart:
            line_parts = []
            for char in row:
                if char == '█':  # Bullish candle
                    line_parts.append('[green]█[/green]')
                elif char == '░':  # Bearish candle
                    line_parts.append('[red]░[/red]')
                elif char == '│':  # Wick
                    line_parts.append('[white]│[/white]')
                elif char == '─':  # Support or doji
                    line_parts.append('[yellow]─[/yellow]')
                elif char == '═':  # Resistance
                    line_parts.append('[red]═[/red]')
                else:
                    line_parts.append(char)
            chart_lines.append(''.join(line_parts))
        
        # Add price scale on the right
        for i, line in enumerate(chart_lines):
            price_at_level = price_max - (i / (chart_height - 1)) * price_range
            chart_lines[i] = f"{line} {price_at_level:8.4f}"
        
        # Add volume bars if requested
        if show_volume:
            volumes = [c.volume for c in display_candles]
            max_volume = max(volumes) if volumes else 1
            
            volume_line = ""
            for i, candle in enumerate(display_candles):
                if i >= self.width:
                    break
                volume_height = int((candle.volume / max_volume) * 3) if max_volume > 0 else 0
                volume_char = ['', '▁', '▃', '▆'][min(volume_height, 3)]
                color = 'green' if candle.is_bullish else 'red'
                volume_line += f'[{color}]{volume_char}[/{color}]'
            
            chart_lines.append('')
            chart_lines.append(f"Volume: {volume_line}")
        
        # Add technical analysis summary
        chart_lines.append('')
        
        # Trend information
        trend_direction = "↗ Uptrend" if trend_data['trend'] > 0.1 else "↘ Downtrend" if trend_data['trend'] < -0.1 else "→ Sideways"
        trend_color = "green" if trend_data['trend'] > 0.1 else "red" if trend_data['trend'] < -0.1 else "yellow"
        strength_pct = trend_data['strength'] * 100
        
        chart_lines.append(f"Trend: [{trend_color}]{trend_direction}[/{trend_color}] | Strength: {strength_pct:.1f}%")
        
        # Pattern detection
        if patterns:
            pattern_texts = []
            for pattern_name, pattern_info in patterns.items():
                pattern_color = "yellow" if pattern_info['type'] == 'reversal' else "blue"
                pattern_texts.append(f"[{pattern_color}]{pattern_info['description']}[/{pattern_color}]")
            chart_lines.append(f"Patterns: {' | '.join(pattern_texts)}")
        
        # Support/Resistance levels
        if tech_levels:
            levels_text = []
            for level in tech_levels[:3]:  # Show top 3
                level_color = "green" if level.level_type == 'support' else "red"
                levels_text.append(f"[{level_color}]{level.level_type.title()}: {level.price:.4f}[/{level_color}]")
            chart_lines.append(f"Key Levels: {' | '.join(levels_text)}")
        
        # Chart statistics
        current_price = display_candles[-1].close
        price_change = ((current_price - display_candles[0].open) / display_candles[0].open) * 100
        price_color = "green" if price_change > 0 else "red"
        
        total_volume = sum(c.volume for c in display_candles)
        avg_volume = total_volume / len(display_candles)
        
        chart_lines.append('')
        chart_lines.append(f"Current: ${current_price:.4f} | Change: [{price_color}]{price_change:+.2f}%[/{price_color}] | Avg Vol: {avg_volume:,.0f}")
        
        chart_content = '\n'.join(chart_lines)
        
        # Create title with timeframe info
        title = f"📈 {symbol} ({interval.upper()}) - {len(display_candles)} candles"
        
        return Panel(chart_content, title=title, border_style="cyan")
    
    def render_multi_timeframe_view(self, symbol: str, timeframes: List[str] = None) -> Panel:
        """Render multiple timeframes in a compact view."""
        if timeframes is None:
            timeframes = ['1m', '5m', '15m', '1h']
        
        ws_manager = get_websocket_manager()
        
        # Create table for multi-timeframe view
        tf_table = Table(show_header=True, show_edge=False, pad_edge=False)
        tf_table.add_column("Timeframe", style="cyan", width=10)
        tf_table.add_column("Open", style="white", width=10, justify="right")
        tf_table.add_column("High", style="green", width=10, justify="right")
        tf_table.add_column("Low", style="red", width=10, justify="right")
        tf_table.add_column("Close", style="white", width=10, justify="right")
        tf_table.add_column("Change %", style="white", width=10, justify="right")
        tf_table.add_column("Trend", style="white", width=8, justify="center")
        tf_table.add_column("Pattern", style="white", width=15)
        
        for tf in timeframes:
            klines_data = ws_manager.get_latest_klines(symbol, tf, 50)
            
            if not klines_data:
                tf_table.add_row(tf.upper(), "No data", "", "", "", "", "", "")
                continue
            
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
            
            if candles:
                latest = candles[-1]
                first = candles[0]
                
                # Calculate change
                change_pct = ((latest.close - first.open) / first.open) * 100
                change_color = "green" if change_pct > 0 else "red"
                
                # Get trend
                trend_data = self.analyzer.calculate_trend_strength(candles)
                if trend_data['trend'] > 0.2:
                    trend_display = "[green]↗[/green]"
                elif trend_data['trend'] < -0.2:
                    trend_display = "[red]↘[/red]"
                else:
                    trend_display = "[yellow]→[/yellow]"
                
                # Get patterns
                patterns = self.analyzer.detect_patterns(candles)
                pattern_text = list(patterns.keys())[0] if patterns else "-"
                
                tf_table.add_row(
                    tf.upper(),
                    f"{latest.open:.4f}",
                    f"{latest.high:.4f}",
                    f"{latest.low:.4f}",
                    f"{latest.close:.4f}",
                    f"[{change_color}]{change_pct:+.2f}%[/{change_color}]",
                    trend_display,
                    pattern_text[:15]
                )
        
        return Panel(tf_table, title=f"📊 Multi-Timeframe Analysis - {symbol}", border_style="blue")
    
    def render_indicator_panel(self, symbol: str, interval: str = "1m") -> Panel:
        """Render technical indicators panel."""
        ws_manager = get_websocket_manager()
        klines_data = ws_manager.get_latest_klines(symbol, interval, 100)
        
        if not klines_data:
            return Panel("No data for indicators", title=f"Technical Indicators - {symbol}", border_style="yellow")
        
        # Prepare data for analysis
        df_data = []
        for kline in klines_data:
            df_data.append({
                'timestamp': datetime.fromtimestamp(kline['open_time'] / 1000),
                'open': kline['open'],
                'high': kline['high'],
                'low': kline['low'],
                'close': kline['close'],
                'volume': kline['volume']
            })
        
        # Calculate indicators using DataAnalyzer
        analysis = self.data_analyzer.calculate_comprehensive_analysis(df_data)
        
        # Create indicators table
        indicators_table = Table(show_header=False, show_edge=False, pad_edge=False)
        indicators_table.add_column("Indicator", style="cyan", width=15)
        indicators_table.add_column("Value", style="white", width=12, justify="right")
        indicators_table.add_column("Signal", style="white", width=12)
        indicators_table.add_column("Strength", style="white", width=10)
        
        # RSI
        rsi = analysis.get('rsi', 50)
        rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
        rsi_color = "red" if rsi > 70 else "green" if rsi < 30 else "yellow"
        indicators_table.add_row("RSI", f"{rsi:.1f}", f"[{rsi_color}]{rsi_signal}[/{rsi_color}]", "")
        
        # MACD
        macd = analysis.get('macd', 0)
        macd_signal_val = analysis.get('macd_signal', 0)
        macd_signal = "Bullish" if macd > macd_signal_val else "Bearish"
        macd_color = "green" if macd > macd_signal_val else "red"
        indicators_table.add_row("MACD", f"{macd:.6f}", f"[{macd_color}]{macd_signal}[/{macd_color}]", "")
        
        # Bollinger Bands
        bb_upper = analysis.get('bollinger_upper', 0)
        bb_lower = analysis.get('bollinger_lower', 0)
        current_price = df_data[-1]['close'] if df_data else 0
        
        if bb_upper and bb_lower:
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            bb_signal = "Overbought" if bb_position > 0.8 else "Oversold" if bb_position < 0.2 else "Normal"
            bb_color = "red" if bb_position > 0.8 else "green" if bb_position < 0.2 else "yellow"
            indicators_table.add_row("Bollinger", f"{bb_position:.2f}", f"[{bb_color}]{bb_signal}[/{bb_color}]", "")
        
        # Moving averages
        sma_20 = analysis.get('sma_20', 0)
        sma_50 = analysis.get('sma_50', 0)
        
        if sma_20 and sma_50:
            ma_signal = "Bullish" if sma_20 > sma_50 else "Bearish"
            ma_color = "green" if sma_20 > sma_50 else "red"
            indicators_table.add_row("MA Cross", f"{sma_20:.4f}", f"[{ma_color}]{ma_signal}[/{ma_color}]", "")
        
        # Volume analysis
        volumes = [d['volume'] for d in df_data[-20:]]  # Last 20 periods
        avg_volume = statistics.mean(volumes) if volumes else 0
        current_volume = df_data[-1]['volume'] if df_data else 0
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        volume_signal = "High" if volume_ratio > 1.5 else "Low" if volume_ratio < 0.5 else "Normal"
        volume_color = "yellow" if volume_ratio > 1.5 else "blue" if volume_ratio < 0.5 else "white"
        indicators_table.add_row("Volume", f"{volume_ratio:.2f}x", f"[{volume_color}]{volume_signal}[/{volume_color}]", "")
        
        return Panel(indicators_table, title=f"📈 Technical Indicators - {symbol} ({interval.upper()})", border_style="green")


# Singleton instance
_advanced_chart_renderer: Optional[AdvancedChartRenderer] = None

def get_advanced_chart_renderer() -> AdvancedChartRenderer:
    """Get the singleton advanced chart renderer."""
    global _advanced_chart_renderer
    if _advanced_chart_renderer is None:
        _advanced_chart_renderer = AdvancedChartRenderer()
    return _advanced_chart_renderer