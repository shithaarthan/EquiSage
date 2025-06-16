# In stock_analyzer/technicals.py

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import os
from typing import Dict, Any
import pprint

# --- Configuration & Helper (no changes needed here) ---
DATA_PERIOD = "1y"
DATA_INTERVAL = "1d"
CHART_OUTPUT_DIR = "charts"
os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)

def _create_technical_summary(df: pd.DataFrame) -> Dict[str, Any]:
    # This function is correct.
    latest = df.iloc[-1]
    summary = {}
    # ... (rest of the function is the same)
    rsi = latest.get('RSI_14')
    if rsi is not None:
        rsi_signal = "Neutral"
        if rsi > 70: rsi_signal = "Overbought"
        elif rsi < 30: rsi_signal = "Oversold"
        summary['RSI (14)'] = f"{rsi:.2f} ({rsi_signal})"
    macd = latest.get('MACD_12_26_9')
    signal = latest.get('MACDs_12_26_9')
    if macd is not None and signal is not None:
        trend = "Bullish Crossover" if macd > signal else "Bearish Crossover"
        summary['MACD'] = f"Signal: {trend}"
    close = latest['Close']
    sma50 = latest.get('SMA_50')
    sma200 = latest.get('SMA_200')
    if sma50 is not None and sma200 is not None:
        trend_short = "Above" if close > sma50 else "Below"
        trend_long = "Above" if close > sma200 else "Below"
        summary['Price vs 50-Day MA'] = f"{trend_short} (SMA: {sma50:.2f})"
        summary['Price vs 200-Day MA'] = f"{trend_long} (SMA: {sma200:.2f})"
    return summary


def fetch_technical_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs technical analysis for a stock with robust data handling and correct plotting.
    """
    print("---NODE: Performing Technical Analysis---")
    
    try:
        stock_ticker = state["stock_ticker"]
    except KeyError as e:
        print(f"Error: Missing 'stock_ticker' in state - {e}")
        return {}

    print(f"Fetching historical data for {stock_ticker}...")
    
    try:
        # Data fetching and cleaning part is now correct
        df_raw = yf.download(
            stock_ticker, period=DATA_PERIOD, interval=DATA_INTERVAL,
            progress=False, auto_adjust=False, actions=False
        )
        if df_raw.empty:
            return {"technical_analysis": {"error": "No data found."}}
        if isinstance(df_raw.columns, pd.MultiIndex):
            df_raw.columns = df_raw.columns.get_level_values(0)
            print("MultiIndex detected and flattened.")
        df = df_raw[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

        # Indicator calculation is correct
        df.ta.rsi(append=True)
        df.ta.macd(append=True)
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        
        # Summary creation is correct
        summary = _create_technical_summary(df)
        
        # === THE FIX IS HERE ===
        # Create a new DataFrame with just the data we want to plot (last 6 months)
        plot_df = df.tail(120).copy()
        
        # Now, create the 'addplot' list using data from this new, sliced DataFrame
        addplots = [
            mpf.make_addplot(plot_df['SMA_50'], color='blue', width=0.7),
            mpf.make_addplot(plot_df['SMA_200'], color='orange', width=0.7),
            mpf.make_addplot(plot_df['RSI_14'], panel=2, color='purple', ylabel='RSI'),
        ]
        # =======================

        chart_path = os.path.join(CHART_OUTPUT_DIR, f"{stock_ticker.replace('.', '_')}_chart.png")
        title = f"{state.get('company_name', stock_ticker)}\n"
        title += f"RSI: {summary.get('RSI (14)', 'N/A')} | Price vs 50D MA: {summary.get('Price vs 50-Day MA', 'N/A').split(' ')[0]}"

        # Finally, plot the sliced DataFrame
        mpf.plot(
            plot_df, # Use the sliced DataFrame here
            type='candle',
            style='yahoo',
            title=title,
            ylabel='Price (INR)',
            volume=True,
            addplot=addplots,
            panel_ratios=(3,1,1),
            figsize=(12, 7),
            savefig=chart_path
        )
        print(f"Chart saved to: {chart_path}")
        
        return {
            "technical_analysis": {
                "summary": summary,
                "chart_path": chart_path
            }
        }

    except Exception as e:
        print(f"An unexpected error occurred during technical analysis for {stock_ticker}: {e}")
        return {"technical_analysis": {"error": f"Analysis failed: {e}"}}

# --- Self-testing block (remains the same) ---
if __name__ == '__main__':
    print("---Testing Technical Analysis Module (Robust Version)---")
    
    test_state = {
        "stock_ticker": "TATAMOTORS.NS",
        "company_name": "Tata Motors Ltd."
    }
    
    result = fetch_technical_analysis(test_state)
    pprint.pprint(result)

    if result.get("technical_analysis", {}).get("chart_path"):
        chart_file = result["technical_analysis"]["chart_path"]
        if os.path.exists(chart_file):
            print(f"\nSUCCESS: Chart file created at '{chart_file}'")
        else:
            print(f"\nFAILURE: Chart file was not created.")