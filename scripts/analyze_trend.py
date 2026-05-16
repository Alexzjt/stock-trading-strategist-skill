import akshare as ak
import pandas as pd
import argparse
import json
import sys
import requests
from datetime import datetime, timedelta

def fetch_from_tencent(symbol):
    """
    Fallback method to fetch historical daily K-lines from Tencent Finance.
    Returns standard dataframe compatible with akshare.
    """
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,365,qfq"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if data.get("code") != 0:
            return pd.DataFrame()
            
        stock_data = data.get("data", {}).get(symbol, {})
        # qfqday for A-shares, day for HK/US (if qfq is not available)
        kline_list = stock_data.get("qfqday", stock_data.get("day", []))
        
        if not kline_list:
            return pd.DataFrame()
            
        # Ensure all rows have exactly 6 columns to prevent pandas errors
        kline_list = [row[:6] for row in kline_list]
        df = pd.DataFrame(kline_list, columns=["日期", "开盘", "收盘", "最高", "最低", "成交量"])
        for col in ["开盘", "收盘", "最高", "最低", "成交量"]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        # Silently handle Tencent fallback failures (could print for debugging)
        return pd.DataFrame()


# ──────────────────────────────────────────────
# Volume Analysis Helpers
# ──────────────────────────────────────────────

def analyze_volume(df, idx):
    """
    Analyze volume at a given index relative to recent averages.
    Returns a dict with volume metrics and assessment.
    """
    vol = float(df.iloc[idx]['成交量'])

    # 5-day and 10-day volume moving averages (calculated up to the previous day)
    lookback_5 = df['成交量'].iloc[max(0, idx-5):idx].mean() if idx >= 1 else vol
    lookback_10 = df['成交量'].iloc[max(0, idx-10):idx].mean() if idx >= 1 else vol

    vol_ratio_5 = round(vol / lookback_5, 2) if lookback_5 > 0 else None
    vol_ratio_10 = round(vol / lookback_10, 2) if lookback_10 > 0 else None

    # Assessment
    assessment = "正常"
    if vol_ratio_5 and vol_ratio_5 >= 2.0:
        assessment = "显著放量 (>=2x)"
    elif vol_ratio_5 and vol_ratio_5 >= 1.5:
        assessment = "温和放量 (1.5x)"
    elif vol_ratio_5 and vol_ratio_5 <= 0.5:
        assessment = "显著缩量 (<=0.5x)"
    elif vol_ratio_5 and vol_ratio_5 <= 0.7:
        assessment = "温和缩量 (<=0.7x)"

    return {
        "volume": vol,
        "vol_ma5": round(lookback_5, 2) if lookback_5 else None,
        "vol_ma10": round(lookback_10, 2) if lookback_10 else None,
        "vol_ratio_vs_5d": vol_ratio_5,
        "vol_ratio_vs_10d": vol_ratio_10,
        "assessment": assessment
    }


# ──────────────────────────────────────────────
# K-Line Pattern Detection (works on any index)
# ──────────────────────────────────────────────

def detect_patterns_at(df, idx):
    """
    Detect candlestick patterns at a given index using the row at idx
    and its neighbours. Returns a list of pattern description strings.
    Requires at least idx >= 2 for 3-K-line patterns.
    """
    patterns = []

    if idx < 1 or idx >= len(df):
        return patterns

    t = df.iloc[idx]    # "today" (target bar)
    y = df.iloc[idx-1]  # previous bar

    t_open, t_close = float(t['开盘']), float(t['收盘'])
    t_high, t_low = float(t['最高']), float(t['最低'])
    y_open, y_close = float(y['开盘']), float(y['收盘'])
    y_high, y_low = float(y['最高']), float(y['最低'])

    t_body = abs(t_close - t_open)
    y_body = abs(y_close - y_open)
    t_range = t_high - t_low if t_high != t_low else 0.01
    y_range = y_high - y_low if y_high != y_low else 0.01

    # Short-term trend context (use MA10 at that date)
    ma10_val = float(t['MA10']) if pd.notna(t['MA10']) else t_close
    is_uptrend = t_close > ma10_val
    is_downtrend = t_close < ma10_val

    # ----- Single K-line patterns -----

    lower_shadow = min(t_open, t_close) - t_low
    upper_shadow = t_high - max(t_open, t_close)

    # Hammer / Hanging Man
    if t_body > 0 and lower_shadow > 2 * t_body and upper_shadow < 0.3 * t_body:
        if is_downtrend:
            patterns.append("锤子线 (Hammer) - 下跌趋势中探底回升，看涨反转信号")
        elif is_uptrend:
            patterns.append("上吊线 (Hanging Man) - 高位出现长下影，诱多看跌信号")

    # Shooting Star (流星线)
    if t_body > 0 and upper_shadow > 2 * t_body and lower_shadow < 0.3 * t_body:
        if is_uptrend:
            patterns.append("流星线 (Shooting Star) - 冲高回落，看跌反转信号")

    # Doji (十字星)
    if t_body <= t_range * 0.1:
        if is_uptrend:
            patterns.append("十字星 (Doji) - 高位出现，警惕上涨疲态")
        elif is_downtrend:
            patterns.append("十字星 (Doji) - 低位出现，多空力量暂时均衡")

    # ----- Double K-line patterns -----

    # Bullish Engulfing (看涨吞没)
    if is_downtrend and y_close < y_open and t_close > t_open:
        if t_open <= y_close and t_close >= y_open:
            patterns.append("看涨吞没 (Bullish Engulfing) - 底部反转信号")

    # Bearish Engulfing (看跌吞没)
    if is_uptrend and y_close > y_open and t_close < t_open:
        if t_open >= y_close and t_close <= y_open:
            patterns.append("看跌吞没 (Bearish Engulfing) - 顶部反转预警")

    # Dark Cloud Cover (乌云盖顶)
    if is_uptrend and y_close > y_open and t_close < t_open:
        y_mid = (y_open + y_close) / 2
        if t_open > y_high and t_close < y_mid:
            patterns.append("乌云盖顶 (Dark Cloud Cover) - 标准顶部反转，空头砸穿阳线1/2以上")
        elif t_open > y_close and t_close < y_mid:
            patterns.append("类乌云盖顶 (Near Dark Cloud) - 阴线深入前阳线1/2以上，但开盘未超前日最高")

    # Piercing Pattern (刺透形态)
    if is_downtrend and y_close < y_open and t_close > t_open:
        y_mid = (y_open + y_close) / 2
        if t_open < y_low and t_close > y_mid:
            patterns.append("刺透形态 (Piercing Pattern) - 底部反转信号")

    # Harami (包孕线)
    if y_body > 0:
        if t_body < y_body * 0.5:
            if max(t_open, t_close) <= max(y_open, y_close) and min(t_open, t_close) >= min(y_open, y_close):
                if is_uptrend:
                    patterns.append("包孕线 (Harami) - 高位趋势刹车，上涨动力衰竭")
                elif is_downtrend:
                    patterns.append("包孕线 (Harami) - 低位趋势刹车，下跌动力衰竭")

    # Tweezers Top / Bottom (平头形态)
    if abs(t_high - y_high) / t_range < 0.02 and is_uptrend:
        patterns.append("平头顶 (Tweezers Top) - 连续两日高点相同，顶部阻力信号")
    if abs(t_low - y_low) / t_range < 0.02 and is_downtrend:
        patterns.append("平头底 (Tweezers Bottom) - 连续两日低点相同，底部支撑信号")

    # ----- Triple K-line patterns (need idx >= 2) -----
    if idx >= 2:
        d2 = df.iloc[idx-2]  # two days before target
        d2_open, d2_close = float(d2['开盘']), float(d2['收盘'])
        d2_body = abs(d2_close - d2_open)

        # Evening Star (黄昏星): big yang + small body (gap up) + big yin
        if d2_close > d2_open and d2_body > 0:
            if y_body < d2_body * 0.3 and min(y_open, y_close) > d2_close:
                if t_close < t_open and t_close < (d2_open + d2_close) / 2:
                    patterns.append("黄昏星 (Evening Star) - 经典三K线顶部反转，可靠性极高")

        # Morning Star (启明星): big yin + small body (gap down) + big yang
        if d2_close < d2_open and d2_body > 0:
            if y_body < d2_body * 0.3 and max(y_open, y_close) < d2_close:
                if t_close > t_open and t_close > (d2_open + d2_close) / 2:
                    patterns.append("启明星 (Morning Star) - 经典三K线底部反转，可靠性极高")

        # Three Black Crows (三只乌鸦)
        if (d2_close < d2_open and y_close < y_open and t_close < t_open
                and y_close < d2_close and t_close < y_close):
            patterns.append("三只乌鸦 (Three Black Crows) - 连续三根阴线，极度看跌")

        # Three White Soldiers (红三兵)
        if (d2_close > d2_open and y_close > y_open and t_close > t_open
                and y_close > d2_close and t_close > y_close):
            patterns.append("红三兵 (Three White Soldiers) - 连续三根阳线，强势看涨")

    return patterns


# ──────────────────────────────────────────────
# K-line row to dict helper
# ──────────────────────────────────────────────

def row_to_dict(row, df, idx):
    """Convert a dataframe row + its index into a clean dict for JSON output."""
    d = {
        "date": str(row['日期']),
        "open": float(row['开盘']),
        "close": float(row['收盘']),
        "high": float(row['最高']),
        "low": float(row['最低']),
        "volume": float(row['成交量']),
        "change_pct": None,
    }
    # Daily change %
    if idx >= 1:
        prev_close = float(df.iloc[idx-1]['收盘'])
        if prev_close > 0:
            d["change_pct"] = round((d["close"] - prev_close) / prev_close * 100, 2)

    # Add candle color description for readability
    if d["close"] > d["open"]:
        d["candle"] = "阳线"
    elif d["close"] < d["open"]:
        d["candle"] = "阴线"
    else:
        d["candle"] = "十字"

    for ma in ['MA10', 'MA50', 'MA200']:
        d[ma] = round(float(row[ma]), 3) if pd.notna(row[ma]) else None
    return d


# ──────────────────────────────────────────────
# Volume-Price Relationship (量价关系)
# ──────────────────────────────────────────────

def assess_volume_price(row_dict, vol_info):
    """
    Combine price action and volume to give a volume-price relationship verdict.
    """
    if vol_info["vol_ratio_vs_5d"] is None:
        return "数据不足"

    price_up = row_dict["change_pct"] is not None and row_dict["change_pct"] > 0
    price_down = row_dict["change_pct"] is not None and row_dict["change_pct"] < 0
    vol_surge = vol_info["vol_ratio_vs_5d"] >= 1.5
    vol_shrink = vol_info["vol_ratio_vs_5d"] <= 0.7

    if price_up and vol_surge:
        return "量价齐升 — 上涨有量支撑，健康"
    elif price_up and vol_shrink:
        return "价升量缩 — 上涨缺乏量能，警惕虚涨"
    elif price_down and vol_surge:
        return "放量下跌 — 空方力量强烈，危险信号"
    elif price_down and vol_shrink:
        return "缩量下跌 — 卖压减弱，可能接近支撑"
    elif price_up:
        return "温和上涨 — 量能平稳"
    elif price_down:
        return "温和下跌 — 量能平稳"
    else:
        return "平盘整理"


# ──────────────────────────────────────────────
# Main Analysis (supports --date)
# ──────────────────────────────────────────────

def fetch_data(symbol):
    """
    Fetch stock data, parse symbol, calculate MAs. Returns (prefixed_symbol, df) or raises.
    """
    original_symbol = symbol.strip()

    # Parse Symbol and standardize prefix
    if symbol.isdigit() and len(symbol) == 6:
        if symbol.startswith('6') or symbol.startswith('5'):
            symbol = 'sh' + symbol
        else:
            symbol = 'sz' + symbol
    elif symbol.isalpha():
        symbol = 'us' + symbol.upper()
    # otherwise assume it already has 'hk', 'us', 'sh', 'sz' prefixes

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=500)).strftime("%Y%m%d")

    df = pd.DataFrame()

    # Try akshare first
    try:
        if symbol.startswith('sh') or symbol.startswith('sz'):
            df = ak.stock_zh_a_hist(
                symbol=symbol.replace('sh', '').replace('sz', ''),
                period="daily", start_date=start_date, end_date=end_date, adjust="qfq"
            )
        elif symbol.startswith('hk'):
            df = ak.stock_hk_hist(
                symbol=symbol.replace('hk', ''),
                period="daily", start_date=start_date, end_date=end_date, adjust="qfq"
            )
        elif symbol.startswith('us'):
            us_sym = symbol.replace('us', '')
            df = ak.stock_us_hist(
                symbol=us_sym, period="daily",
                start_date=start_date, end_date=end_date, adjust="qfq"
            )
    except Exception:
        pass

    # Fallback to Tencent if akshare returned empty or failed
    if df.empty:
        df = fetch_from_tencent(symbol)

    if df.empty:
        raise ValueError(f"No data for {original_symbol} ({symbol}). Both Akshare and Tencent failed.")

    # Calculate Moving Averages
    df['MA10'] = df['收盘'].rolling(window=10).mean()
    df['MA50'] = df['收盘'].rolling(window=50).mean()
    df['MA200'] = df['收盘'].rolling(window=200).mean()

    # Ensure date column is string for matching
    df['日期'] = df['日期'].astype(str)

    return symbol, df


def analyze_at_date(symbol_str, target_date=None, context_days=5):
    """
    Full analysis at a specific date (or latest if target_date is None).
    Returns a rich JSON-serializable dict.
    """
    symbol, df = fetch_data(symbol_str)

    # Locate target index
    if target_date:
        # Normalize date format (accept YYYY-MM-DD or YYYYMMDD)
        target_date_str = target_date.replace('-', '').replace('/', '')
        # Try to match
        matches = df[df['日期'].str.replace('-', '') == target_date_str]
        if matches.empty:
            # Find the nearest trading day
            df['_date_parsed'] = pd.to_datetime(df['日期'])
            target_dt = pd.to_datetime(target_date_str)
            diffs = (df['_date_parsed'] - target_dt).abs()
            nearest_idx = diffs.idxmin()
            target_idx = nearest_idx
            df.drop(columns=['_date_parsed'], inplace=True)
        else:
            target_idx = matches.index[0]
    else:
        target_idx = len(df) - 1

    # Context window
    ctx_start = max(0, target_idx - context_days)
    ctx_end = min(len(df) - 1, target_idx + context_days)

    # Target day data
    target_row = df.iloc[target_idx]
    target_dict = row_to_dict(target_row, df, target_idx)

    # Volume analysis at target date
    vol_info = analyze_volume(df, target_idx)
    vol_price = assess_volume_price(target_dict, vol_info)

    # K-line patterns at target date
    patterns = detect_patterns_at(df, target_idx)

    # Trend assessment at that date
    ma10_val = float(target_row['MA10']) if pd.notna(target_row['MA10']) else None
    ma50_val = float(target_row['MA50']) if pd.notna(target_row['MA50']) else None
    ma200_val = float(target_row['MA200']) if pd.notna(target_row['MA200']) else None
    close = float(target_row['收盘'])

    short_trend = "Neutral"
    if ma10_val:
        short_trend = "Uptrend" if close > ma10_val else "Downtrend"

    # Context K-lines
    context_klines = []
    for i in range(ctx_start, ctx_end + 1):
        row = df.iloc[i]
        kline = row_to_dict(row, df, i)
        kline["is_target"] = (i == target_idx)
        # Volume info for context
        ctx_vol = analyze_volume(df, i)
        kline["volume_assessment"] = ctx_vol["assessment"]
        kline["vol_ratio_vs_5d"] = ctx_vol["vol_ratio_vs_5d"]
        # Patterns for context rows too
        ctx_patterns = detect_patterns_at(df, i)
        kline["patterns"] = ctx_patterns if ctx_patterns else []
        context_klines.append(kline)

    result = {
        "symbol": symbol,
        "analysis_mode": "historical" if target_date else "realtime",
        "target_date": target_dict,
        "trend": {
            "short_term": short_trend,
            "vs_MA50": "Above" if (ma50_val and close > ma50_val) else "Below" if ma50_val else "N/A",
            "vs_MA200": "Above" if (ma200_val and close > ma200_val) else "Below" if ma200_val else "N/A",
            "MA10": round(ma10_val, 3) if ma10_val else None,
            "MA50": round(ma50_val, 3) if ma50_val else None,
            "MA200": round(ma200_val, 3) if ma200_val else None,
        },
        "volume_analysis": vol_info,
        "volume_price_relationship": vol_price,
        "candlestick_patterns": patterns,
        "context_klines": context_klines,
    }

    return result


# ──────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stock trend analysis with historical date replay, volume, and K-line patterns.",
        epilog="Examples:\n"
               "  python analyze_trend.py 000967                     # Latest day\n"
               "  python analyze_trend.py 000967 --date 2026-03-12   # Replay March 12\n"
               "  python analyze_trend.py 600519 --date 20260310 --context 10  # 10 days context\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("symbol", type=str, help="Stock symbol (e.g., 000967, 600519, hk00700, AAPL)")
    parser.add_argument("--date", type=str, default=None,
                        help="Target date for historical replay (YYYY-MM-DD or YYYYMMDD). Omit for latest.")
    parser.add_argument("--context", type=int, default=5,
                        help="Number of trading days before/after target to show (default: 5)")

    args = parser.parse_args()

    try:
        analysis = analyze_at_date(args.symbol, target_date=args.date, context_days=args.context)
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)
