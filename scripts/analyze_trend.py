import akshare as ak
import pandas as pd
import argparse
import json
import sys
from datetime import datetime, timedelta

def analyze_stock(symbol: str):
    """
    Fetch recent daily stock data and calculate 50-day and 200-day moving averages.
    This script provides basic context for the trading strategist.
    """
    try:
        # Check if it's A-share
        # akshare format: sh600000 or sz000001
        if symbol.isdigit() and len(symbol) == 6:
            if symbol.startswith('6'):
                symbol = 'sh' + symbol
            else:
                symbol = 'sz' + symbol
        
        # Fetch historical data
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        df = ak.stock_zh_a_hist(symbol=symbol.replace('sh', '').replace('sz', ''), period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df.empty:
            return {"error": f"No data found for symbol {symbol}"}
        
        # Calculate moving averages
        df['MA50'] = df['收盘'].rolling(window=50).mean()
        df['MA200'] = df['收盘'].rolling(window=200).mean()
        
        # Get latest data
        latest = df.iloc[-1]
        
        result = {
            "symbol": symbol,
            "date": str(latest['日期']),
            "close": float(latest['收盘']),
            "open": float(latest['开盘']),
            "high": float(latest['最高']),
            "low": float(latest['最低']),
            "volume": float(latest['成交量']),
            "MA50": float(latest['MA50']) if not pd.isna(latest['MA50']) else None,
            "MA200": float(latest['MA200']) if not pd.isna(latest['MA200']) else None,
            "trend_vs_MA50": "Above" if latest['收盘'] > latest['MA50'] else "Below",
            "trend_vs_MA200": "Above" if latest['收盘'] > latest['MA200'] else "Below",
        }
        
        return result

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get basic stock analysis data.")
    parser.add_argument("symbol", type=str, help="Stock symbol (e.g., 600519)")
    args = parser.parse_args()
    
    analysis = analyze_stock(args.symbol)
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
