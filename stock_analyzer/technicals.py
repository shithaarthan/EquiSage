import matplotlib
# Set the backend to a non-interactive one BEFORE importing plotting libraries
matplotlib.use('Agg')

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import numpy as np
import os
from typing import Dict, Any, List
import pprint
from scipy.signal import argrelextrema

DATA_PERIOD = "1y"
DATA_INTERVAL = "1d"
CHART_OUTPUT_DIR = "charts"
os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)

def _find_support_resistance(prices: pd.Series, order: int = 5) -> (List[float], List[float]):
    """Find support and resistance levels using local extrema."""
    try:
        local_min_indices = argrelextrema(prices.values, np.less_equal, order=order)[0]
        local_max_indices = argrelextrema(prices.values, np.greater_equal, order=order)[0]
        support_levels = prices.iloc[local_min_indices].tail(3).tolist()
        resistance_levels = prices.iloc[local_max_indices].tail(3).tolist()
        return sorted(support_levels, reverse=True), sorted(resistance_levels)
    except Exception as e:
        print(f"Could not find S/R levels: {e}")
        return [], []

def _create_technical_summary(df: pd.DataFrame, support_levels: List, resistance_levels: List) -> Dict[str, Any]:
    latest = df.iloc[-1]
    summary = {}
    rsi = latest.get('RSI_14')
    macd = latest.get('MACD_12_26_9')
    macds = latest.get('MACDs_12_26_9')
    sma50 = latest.get('SMA_50')
    sma200 = latest.get('SMA_200')
    close = latest['Close']
    
    rsi_signal = "Neutral"
    if rsi is not None:
        if rsi > 70: rsi_signal = "Overbought"
        elif rsi < 30: rsi_signal = "Oversold"
    summary['RSI (14)'] = f"{rsi:.2f} ({rsi_signal})" if rsi is not None else "N/A"

    macd_signal = "Neutral"
    if macd is not None and macds is not None:
        if macd > macds: macd_signal = "Bullish Crossover"
        elif macd < macds: macd_signal = "Bearish Crossover"
    summary['MACD'] = f"Signal: {macd_signal}"

    if sma50 is not None and sma200 is not None:
        if close > sma50 > sma200: bias = "Strong Bullish"
        elif close < sma50 < sma200: bias = "Strong Bearish"
        elif close > sma50: bias = "Short-term Bullish"
        else: bias = "Mixed/Bearish"
        summary['Trend Bias'] = bias
        summary['Price vs 50D SMA'] = f"{'Above' if close > sma50 else 'Below'} ({sma50:.2f})"
        summary['Price vs 200D SMA'] = f"{'Above' if close > sma200 else 'Below'} ({sma200:.2f})"

    if support_levels:
        summary['Key Support'] = ", ".join([f"{s:.2f}" for s in support_levels])
    if resistance_levels:
        summary['Key Resistance'] = ", ".join([f"{r:.2f}" for r in resistance_levels])

    return summary

def fetch_technical_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    print("---NODE: Performing Analyst-Grade Technical Analysis---")
    try:
        stock_ticker = state["stock_ticker"]
        company_name = state.get("company_name", stock_ticker)
    except KeyError as e:
        print(f"Error: Missing 'stock_ticker' in state - {e}")
        return {"technical_analysis": {"error": f"Missing ticker: {e}"}}

    print(f"Fetching historical data for {stock_ticker}...")

    try:
        df_raw = yf.download(
            stock_ticker, period=DATA_PERIOD, interval=DATA_INTERVAL,
            progress=False, auto_adjust=True, actions=False
        )
        if df_raw.empty:
            return {"technical_analysis": {"error": "No technical data found for this ticker."}}
        
        if isinstance(df_raw.columns, pd.MultiIndex):
            print("MultiIndex detected, flattening columns.")
            df_raw.columns = df_raw.columns.get_level_values(0)

        df = df_raw[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

        df.ta.rsi(append=True)
        df.ta.macd(append=True)
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        df.ta.bbands(append=True)

        support_levels, resistance_levels = _find_support_resistance(df['Close'].tail(120), order=5)
        summary = _create_technical_summary(df, support_levels, resistance_levels)
        plot_df = df.tail(120).copy()
        hlines = dict(hlines=support_levels + resistance_levels, 
                      colors=['g']*len(support_levels) + ['r']*len(resistance_levels), 
                      linestyle='--')

        addplots = [
            mpf.make_addplot(plot_df['SMA_50'], color='blue', width=0.8),
            mpf.make_addplot(plot_df['SMA_200'], color='orange', width=0.8),
            mpf.make_addplot(plot_df['RSI_14'], panel=2, color='purple', ylabel='RSI')
        ]
        
        chart_path = os.path.join(CHART_OUTPUT_DIR, f"{stock_ticker.replace('.', '_')}_chart.png")
        title = f"Technical Analysis for {company_name}\nTrend: {summary.get('Trend Bias', 'N/A')}"

        mpf.plot(
            plot_df, type='candle', style='yahoo', title=title,
            ylabel='Price (INR)', volume=True, addplot=addplots,
            panel_ratios=(4, 1), figsize=(12, 7),
            savefig=chart_path, hlines=hlines
        )
        print(f"Chart saved to: {chart_path}")

        return {"technical_analysis": {"summary": summary, "chart_path": chart_path}}

    except Exception as e:
        print(f"Technical analysis failed for {stock_ticker}: {e}")
        import traceback
        traceback.print_exc()
        return {"technical_analysis": {"error": f"Analysis failed: {e}"}}