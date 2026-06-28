import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import math

# --- Configuration & Styling ---
st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide")

# --- CSS for modern look ---
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #F0F8FF;
        padding: 15px;
        border-radius: 10px;
        border: none;
    }
    /* Targeting the labels and values specifically for high contrast on light background */
    [data-testid="stMetricLabel"] {
        color: #000000 !important;
    }
    [data-testid="stMetricValue"] {
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Fetching (Cached) ---
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def fetch_stock_data(symbol, period="1y", interval="1d"):
    try:
        data = yf.download(symbol, period=period, interval=interval)
        if data.empty:
            return None
        
        # Handle yfinance MultiIndex columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        return data
    except Exception as e:
        return None

# --- Technical Indicator Calculations ---
def calculate_indicators(df, ema_span_1=20, ema_span_2=50):
    df = df.copy()
    
    # EMAs
    df['EMA_1'] = df['Close'].ewm(span=ema_span_1, adjust=False).mean()
    df['EMA_2'] = df['Close'].ewm(span=ema_span_2, adjust=False).mean()
    df['EMA_100'] = df['Close'].ewm(span=100, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # ATR (14-period, Wilder smoothing)
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    
    # RSI (14-period, Wilder smoothing)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, pd.NA)
    df['RSI'] = 100 - (100 / (1 + rs))
    df.loc[(loss == 0) & (gain > 0), 'RSI'] = 100
    df.loc[(loss == 0) & (gain == 0), 'RSI'] = 50
    
    # Stochastic RSI
    rsi_min = df['RSI'].rolling(window=14).min()
    rsi_max = df['RSI'].rolling(window=14).max()
    df['Stoch_RSI'] = (df['RSI'] - rsi_min) / (rsi_max - rsi_min) * 100
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    
    # Support/Resistance (20-day)
    df['Resistance'] = df['High'].rolling(window=20).max()
    df['Support'] = df['Low'].rolling(window=20).min()
    
    # 20-Day Drawdown and Drawup
    df['Drawdown_20d'] = (df['Close'] - df['Resistance']) / df['Resistance'] * 100
    df['Drawup_20d'] = (df['Close'] - df['Support']) / df['Support'] * 100
    
    # Bollinger Bands (20-day)
    df['BB_Mid'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (2 * df['BB_Std'])
    df['BB_Lower'] = df['BB_Mid'] - (2 * df['BB_Std'])
    
    # ADX (14-period, Wilder smoothing)
    up_move = df['High'].diff()
    down_move = -df['Low'].diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
    smoothed_tr = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smoothed_tr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smoothed_tr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    df['ADX'] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    
    # 52-Week High
    df['High_52w'] = df['High'].rolling(window=252, min_periods=1).max()
    
    # 10-Day High (for Drawdown)
    df['High_10d'] = df['High'].rolling(window=10, min_periods=1).max()
    
    # Intraday Drawdown/Drawup (20-day average)
    df['Intraday_Drawdown_Pct'] = ((df['Low'] - df['Open']) / df['Open']) * 100
    df['Intraday_Drawup_Pct'] = ((df['High'] - df['Open']) / df['Open']) * 100
    df['Avg_Drawdown'] = df['Intraday_Drawdown_Pct'].rolling(window=20).mean()
    df['Avg_Drawup'] = df['Intraday_Drawup_Pct'].rolling(window=20).mean()
    df['Lowest_Drawdown'] = df['Intraday_Drawdown_Pct'].rolling(window=20).min()
    df['Highest_Drawdown'] = df['Intraday_Drawdown_Pct'].rolling(window=20).max()
    df['Lowest_Drawup'] = df['Intraday_Drawup_Pct'].rolling(window=20).min()
    df['Highest_Drawup'] = df['Intraday_Drawup_Pct'].rolling(window=20).max()
    
    return df

def is_finite(value):
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False

def finite_float(value, default=0.0):
    return float(value) if is_finite(value) else default

def format_compact_number(value):
    if not is_finite(value):
        return "N/A"
    value = float(value)
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.0f}"

def format_percent(value):
    return f"{float(value) * 100:.1f}%" if is_finite(value) and abs(float(value)) <= 2 else f"{float(value):.1f}%" if is_finite(value) else "N/A"

def inspect_data_quality(df, symbol):
    warnings = []
    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required if col not in df.columns]
    if missing:
        warnings.append(f"{symbol}: missing required columns: {', '.join(missing)}.")
        return warnings

    if len(df) < 252:
        warnings.append(f"{symbol}: less than one trading year of data; 52-week and 200-day signals may be immature.")

    latest_ts = df.index[-1]
    if hasattr(latest_ts, "to_pydatetime"):
        latest_dt = latest_ts.to_pydatetime().replace(tzinfo=None)
        age_days = (datetime.now() - latest_dt).days
        if age_days > 5:
            warnings.append(f"{symbol}: latest bar is {latest_dt.date()}, which may be stale.")

    null_counts = df[required].tail(60).isna().sum()
    bad_cols = [f"{col}={int(count)}" for col, count in null_counts.items() if count > 0]
    if bad_cols:
        warnings.append(f"{symbol}: missing values in recent OHLCV data ({', '.join(bad_cols)}).")

    if finite_float(df['Volume'].tail(20).mean()) == 0:
        warnings.append(f"{symbol}: recent volume is zero or unavailable; volume-ratio signals are unreliable.")

    return warnings

def evaluate_strategy_row(data, idx=-1):
    row = data.iloc[idx]
    prev_row = data.iloc[idx - 1] if idx != 0 else row

    curr_price = finite_float(row['Close'])
    prev_close = finite_float(prev_row['Close'], curr_price)
    price_change_pct = ((curr_price - prev_close) / prev_close) * 100 if prev_close else 0.0

    ema_short_val = finite_float(row['EMA_1'])
    ema_long_val = finite_float(row['EMA_2'])
    ema_100_val = finite_float(row['EMA_100'])
    ema_200_val = finite_float(row['EMA_200'])
    rsi_val = finite_float(row['RSI'], 50.0)
    res_val = finite_float(row['Resistance'])
    sup_val = finite_float(row['Support'])
    macd_val = finite_float(row['MACD'])
    signal_val = finite_float(row['Signal_Line'])
    atr_val = finite_float(row['ATR'])
    adx_val = finite_float(row['ADX'])
    stoch_rsi = finite_float(row['Stoch_RSI'], 50.0)

    trend = "Uptrend" if ema_short_val > ema_long_val else "Downtrend"
    trend_detail = "Bullish Alignment" if curr_price > ema_short_val > ema_long_val else "Bearish Alignment" if curr_price < ema_short_val < ema_long_val else "Neutral/Mixed"
    is_bullish = macd_val > signal_val and rsi_val > 50
    sentiment = "Bullish" if is_bullish else "Bearish"
    sentiment_detail = "MACD & RSI Positive" if is_bullish else "Momentum/RSI Weak"

    high_10d = finite_float(row['High_10d'], curr_price)
    drawdown_10d = (curr_price - high_10d) / high_10d if high_10d else 0.0
    ema20_dist = (curr_price - ema_short_val) / ema_short_val if ema_short_val else 0.0
    start_idx = max(0, idx - 19) if idx >= 0 else max(0, len(data) - 20)
    end_idx = idx + 1 if idx >= 0 else len(data)
    avg_vol = finite_float(data['Volume'].iloc[start_idx:end_idx].mean())
    latest_vol = finite_float(row['Volume'])
    vol_ratio = latest_vol / avg_vol if avg_vol > 0 else 0.0

    c1 = drawdown_10d <= -0.08
    c2 = abs(ema20_dist) <= 0.06
    c3 = 42 <= rsi_val <= 58
    c4 = vol_ratio >= 1.6
    c5 = macd_val > signal_val
    core_score = sum([c1, c2, c3, c4, c5])

    high_52w = finite_float(row['High_52w'], curr_price)
    bb_mid = finite_float(row['BB_Mid'], curr_price)
    s1 = curr_price > ema_long_val
    s2 = macd_val > signal_val
    s3 = (0.78 * high_52w) <= curr_price <= (0.94 * high_52w) if high_52w else False
    s4 = curr_price > ema_100_val
    s5 = adx_val > 20
    s6 = curr_price > bb_mid
    s7 = stoch_rsi < 75
    supp_score = sum([s1, s2, s3, s4, s5, s6, s7])

    risk_fail_rsi = rsi_val > 68
    risk_fail_ema20 = ema20_dist > 0.08
    entry_level = "Avoid"
    pos_size = "No Entry (Risk/Core Failure)" if risk_fail_rsi or risk_fail_ema20 or not (c1 and c2) else "0%"
    color = "red"
    if not (risk_fail_rsi or risk_fail_ema20 or not (c1 and c2)):
        if core_score >= 4 and supp_score >= 3:
            entry_level, pos_size, color = "A+", "Full size (100%)", "green"
        elif core_score >= 4 and supp_score >= 2:
            entry_level, pos_size, color = "A", "70-80%", "lightgreen"
        elif core_score >= 4:
            entry_level, pos_size, color = "B", "50-60%", "orange"
        elif core_score == 3:
            entry_level, pos_size, color = "C", "30-40%", "yellow"

    bb_upper = finite_float(row['BB_Upper'])
    ex1 = curr_price < ema_short_val
    ex2 = macd_val < signal_val
    ex3 = rsi_val > 70
    ex4 = curr_price >= bb_upper if bb_upper else False
    ex5 = curr_price >= (res_val * 0.98) if res_val else False
    exit_score = sum([ex1, ex2, ex3, ex4, ex5])
    exit_level, exit_color, exit_action = "Hold", "gray", "Maintain Position"
    if exit_score >= 3 or ex1:
        exit_level, exit_color, exit_action = "SELL / REDUCE", "red", "Exit or Trim 50-100%"
    elif exit_score >= 1:
        exit_level, exit_color, exit_action = "CAUTION", "orange", "Tighten Stop Loss"

    avg_dd = finite_float(row['Avg_Drawdown'])
    suggested_entry = curr_price * (1 + avg_dd / 100) if avg_dd else curr_price
    stop_loss = suggested_entry * 0.92
    target_resistance = res_val if res_val > suggested_entry else suggested_entry + (2 * (suggested_entry - stop_loss))
    risk_per_share = max(suggested_entry - stop_loss, 0.0)
    reward_per_share = max(target_resistance - suggested_entry, 0.0)
    reward_risk = reward_per_share / risk_per_share if risk_per_share else 0.0

    return {
        "curr_price": curr_price,
        "price_change_pct": price_change_pct,
        "ema_short_val": ema_short_val,
        "ema_long_val": ema_long_val,
        "ema_100_val": ema_100_val,
        "ema_200_val": ema_200_val,
        "atr_val": atr_val,
        "rsi_val": rsi_val,
        "res_val": res_val,
        "sup_val": sup_val,
        "trend": trend,
        "trend_detail": trend_detail,
        "sentiment": sentiment,
        "sentiment_detail": sentiment_detail,
        "dd_20d": finite_float(row['Drawdown_20d']),
        "du_20d": finite_float(row['Drawup_20d']),
        "avg_dd": avg_dd,
        "avg_du": finite_float(row['Avg_Drawup']),
        "lowest_dd": finite_float(row['Lowest_Drawdown']),
        "highest_dd": finite_float(row['Highest_Drawdown']),
        "lowest_du": finite_float(row['Lowest_Drawup']),
        "highest_du": finite_float(row['Highest_Drawup']),
        "entry_level": entry_level,
        "pos_size": pos_size,
        "color": color,
        "core_score": core_score,
        "supp_score": supp_score,
        "risk_fail_rsi": risk_fail_rsi,
        "risk_fail_ema20": risk_fail_ema20,
        "exit_level": exit_level,
        "exit_color": exit_color,
        "exit_action": exit_action,
        "exit_score": exit_score,
        "ex1": ex1, "ex2": ex2, "ex3": ex3, "ex4": ex4, "ex5": ex5,
        "drawdown_10d": drawdown_10d,
        "ema20_dist": ema20_dist,
        "vol_ratio": vol_ratio,
        "adx_val": adx_val,
        "stoch_rsi": stoch_rsi,
        "c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5,
        "s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6, "s7": s7,
        "macd_val": macd_val,
        "signal_val": signal_val,
        "suggested_entry": suggested_entry,
        "stop_loss": stop_loss,
        "target_resistance": target_resistance,
        "risk_per_share": risk_per_share,
        "reward_per_share": reward_per_share,
        "reward_risk": reward_risk
    }

def summarize_backtest(data):
    rows = []
    if len(data) < 280:
        return {"entry_count": 0, "message": "Need at least 280 daily bars for a meaningful 20-day signal backtest."}

    for idx in range(252, len(data) - 20):
        signal = evaluate_strategy_row(data, idx)
        if signal['entry_level'] == "Avoid":
            continue
        entry_price = finite_float(data['Close'].iloc[idx])
        if not entry_price:
            continue
        ret_5d = (finite_float(data['Close'].iloc[idx + 5], entry_price) - entry_price) / entry_price * 100
        ret_20d = (finite_float(data['Close'].iloc[idx + 20], entry_price) - entry_price) / entry_price * 100
        future_low = finite_float(data['Low'].iloc[idx + 1:idx + 21].min(), entry_price)
        max_adverse = (future_low - entry_price) / entry_price * 100
        rows.append({"level": signal['entry_level'], "ret_5d": ret_5d, "ret_20d": ret_20d, "max_adverse": max_adverse})

    if not rows:
        return {"entry_count": 0, "message": "No non-Avoid historical entries found under the current rules."}

    bt = pd.DataFrame(rows)
    return {
        "entry_count": int(len(bt)),
        "win_rate_20d": float((bt['ret_20d'] > 0).mean() * 100),
        "avg_return_5d": float(bt['ret_5d'].mean()),
        "avg_return_20d": float(bt['ret_20d'].mean()),
        "worst_adverse_20d": float(bt['max_adverse'].min()),
        "by_level": bt.groupby('level')['ret_20d'].agg(['count', 'mean']).reset_index()
    }

@st.cache_data(ttl=86400)
def get_fundamental_snapshot(symbol):
    try:
        info = yf.Ticker(symbol).get_info()
        return {
            "Market Cap": info.get("marketCap"),
            "Trailing P/E": info.get("trailingPE"),
            "Forward P/E": info.get("forwardPE"),
            "PEG": info.get("pegRatio"),
            "Revenue Growth": info.get("revenueGrowth"),
            "Earnings Growth": info.get("earningsGrowth"),
            "Gross Margin": info.get("grossMargins"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Debt/Equity": info.get("debtToEquity"),
            "ROE": info.get("returnOnEquity"),
            "Sector": info.get("sector"),
            "Industry": info.get("industry")
        }
    except Exception as exc:
        return {"Error": str(exc)}

@st.cache_data(ttl=3600)
def get_relative_strength(symbol, period="1y"):
    benchmarks = ["SPY", "QQQ"]
    try:
        data = yf.download([symbol] + benchmarks, period=period, interval="1d", progress=False)
        close = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
        results = {}
        for days in [20, 50, 100, 200]:
            if len(close) <= days or symbol not in close:
                continue
            stock_ret = (close[symbol].iloc[-1] / close[symbol].iloc[-days - 1] - 1) * 100
            for benchmark in benchmarks:
                if benchmark in close:
                    bench_ret = (close[benchmark].iloc[-1] / close[benchmark].iloc[-days - 1] - 1) * 100
                    results[f"{days}D vs {benchmark}"] = float(stock_ret - bench_ret)
        return results
    except Exception as exc:
        return {"Error": str(exc)}

@st.cache_data(ttl=3600)
def get_market_regime():
    try:
        data = yf.download(["SPY", "QQQ", "^VIX"], period="1y", interval="1d", progress=False)
        close = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
        spy = close["SPY"].dropna()
        qqq = close["QQQ"].dropna()
        vix = close["^VIX"].dropna()
        spy_ema200 = spy.ewm(span=200, adjust=False).mean().iloc[-1]
        qqq_ema200 = qqq.ewm(span=200, adjust=False).mean().iloc[-1]
        regime = "Risk-On" if spy.iloc[-1] > spy_ema200 and qqq.iloc[-1] > qqq_ema200 else "Risk-Off / Defensive"
        return {
            "Regime": regime,
            "SPY vs EMA200": float((spy.iloc[-1] / spy_ema200 - 1) * 100),
            "QQQ vs EMA200": float((qqq.iloc[-1] / qqq_ema200 - 1) * 100),
            "VIX": float(vix.iloc[-1]) if len(vix) else None
        }
    except Exception as exc:
        return {"Error": str(exc)}

def get_analysis(symbol, period, interval, ema_short, ema_long):
    data = fetch_stock_data(symbol, period, interval)
    if data is None or len(data) < 2:
        return None
    
    data = calculate_indicators(data, ema_short, ema_long)
    
    # Value Extraction (Latest)
    curr_price = float(data['Close'].iloc[-1])
    open_price = float(data['Open'].iloc[-1])
    prev_close = float(data['Close'].iloc[-2])
    price_change = curr_price - prev_close
    price_change_pct = (price_change / prev_close) * 100
    
    ema_short_val = float(data['EMA_1'].iloc[-1])
    ema_long_val = float(data['EMA_2'].iloc[-1])
    ema_100_val = float(data['EMA_100'].iloc[-1])
    atr_val = float(data['ATR'].iloc[-1])
    rsi_val = float(data['RSI'].iloc[-1])
    res_val = float(data['Resistance'].iloc[-1])
    sup_val = float(data['Support'].iloc[-1])
    
    macd_val = float(data['MACD'].iloc[-1])
    signal_val = float(data['Signal_Line'].iloc[-1])
    
    # Trend & Sentiment
    trend = "Uptrend 📈" if ema_short_val > ema_long_val else "Downtrend 📉"
    trend_detail = "Bullish Alignment" if curr_price > ema_short_val > ema_long_val else "Bearish Alignment" if curr_price < ema_short_val < ema_long_val else "Neutral/Mixed"
    
    is_bullish = macd_val > signal_val and rsi_val > 50
    sentiment = "Bullish 🐂" if is_bullish else "Bearish 🐻"
    sentiment_detail = "MACD & RSI Positive" if is_bullish else "Momentum/RSI Weak"
    
    # Drawdown/Drawup
    dd_20d = float(data['Drawdown_20d'].iloc[-1])
    du_20d = float(data['Drawup_20d'].iloc[-1])
    avg_dd = float(data['Avg_Drawdown'].iloc[-1])
    avg_du = float(data['Avg_Drawup'].iloc[-1])
    lowest_dd = float(data['Lowest_Drawdown'].iloc[-1])
    highest_dd = float(data['Highest_Drawdown'].iloc[-1])
    lowest_du = float(data['Lowest_Drawup'].iloc[-1])
    highest_du = float(data['Highest_Drawup'].iloc[-1])
    
    # Scoring System Logic
    high_10d = data['High_10d'].iloc[-1]
    drawdown_10d = (curr_price - high_10d) / high_10d
    c1 = drawdown_10d <= -0.08
    ema20_dist = (curr_price - ema_short_val) / ema_short_val
    c2 = abs(ema20_dist) <= 0.06
    c3 = 42 <= rsi_val <= 58
    latest_vol = data['Volume'].iloc[-1]
    avg_vol = data['Volume'].rolling(20).mean().iloc[-1]
    vol_ratio = latest_vol / avg_vol if avg_vol > 0 else 0
    c4 = vol_ratio >= 1.6
    c5 = macd_val > signal_val
    core_score = sum([c1, c2, c3, c4, c5])
    
    s1 = curr_price > ema_long_val
    s2 = macd_val > signal_val
    high_52w = data['High_52w'].iloc[-1]
    s3 = (0.78 * high_52w) <= curr_price <= (0.94 * high_52w)
    s4 = curr_price > ema_100_val
    adx_val = data['ADX'].iloc[-1]
    s5 = adx_val > 20
    bb_mid = data['BB_Mid'].iloc[-1]
    s6 = curr_price > bb_mid
    stoch_rsi = data['Stoch_RSI'].iloc[-1]
    s7 = stoch_rsi < 75
    supp_score = sum([s1, s2, s3, s4, s5, s6, s7])
    
    risk_fail_rsi = rsi_val > 68
    risk_fail_ema20 = ema20_dist > 0.08
    
    entry_level = "Avoid"
    pos_size = "0%"
    color = "red"
    if risk_fail_rsi or risk_fail_ema20 or not (c1 and c2):
        entry_level = "Avoid"
        pos_size = "No Entry (Risk/Core Failure)"
        color = "red"
    elif core_score >= 4 and supp_score >= 3:
        entry_level = "A+"
        pos_size = "Full size (100%)"
        color = "green"
    elif core_score >= 4 and supp_score >= 2:
        entry_level = "A"
        pos_size = "70-80%"
        color = "lightgreen"
    elif core_score >= 4:
        entry_level = "B"
        pos_size = "50-60%"
        color = "orange"
    elif core_score == 3:
        entry_level = "C"
        pos_size = "30-40%"
        color = "yellow"

    # Exit Logic
    ex1 = curr_price < ema_short_val
    ex2 = macd_val < signal_val
    ex3 = rsi_val > 70
    bb_upper = data['BB_Upper'].iloc[-1]
    ex4 = curr_price >= bb_upper
    ex5 = curr_price >= (res_val * 0.98)
    exit_score = sum([ex1, ex2, ex3, ex4, ex5])
    
    exit_level = "Hold"
    exit_color = "gray"
    exit_action = "Maintain Position"
    if exit_score >= 3 or ex1:
        exit_level = "SELL / REDUCE"
        exit_color = "red"
        exit_action = "Exit or Trim 50-100%"
    elif exit_score >= 1:
        exit_level = "CAUTION"
        exit_color = "orange"
        exit_action = "Tighten Stop Loss"
        
    return {
        "df": data,
        "curr_price": curr_price,
        "price_change_pct": price_change_pct,
        "ema_short_val": ema_short_val,
        "ema_long_val": ema_long_val,
        "ema_100_val": ema_100_val,
        "ema_200_val": float(data['EMA_200'].iloc[-1]) if 'EMA_200' in data.columns else 0.0,
        "rsi_val": rsi_val,
        "res_val": res_val,
        "sup_val": sup_val,
        "trend": trend,
        "trend_detail": trend_detail,
        "sentiment": sentiment,
        "sentiment_detail": sentiment_detail,
        "dd_20d": dd_20d,
        "du_20d": du_20d,
        "avg_dd": avg_dd,
        "avg_du": avg_du,
        "lowest_dd": lowest_dd,
        "highest_dd": highest_dd,
        "lowest_du": lowest_du,
        "highest_du": highest_du,
        "entry_level": entry_level,
        "pos_size": pos_size,
        "color": color,
        "core_score": core_score,
        "supp_score": supp_score,
        "risk_fail_rsi": risk_fail_rsi,
        "risk_fail_ema20": risk_fail_ema20,
        "exit_level": exit_level,
        "exit_color": exit_color,
        "exit_action": exit_action,
        "exit_score": exit_score,
        "ex1": ex1, "ex2": ex2, "ex3": ex3, "ex4": ex4, "ex5": ex5,
        "drawdown_10d": drawdown_10d,
        "ema20_dist": ema20_dist,
        "vol_ratio": vol_ratio,
        "adx_val": adx_val,
        "stoch_rsi": stoch_rsi,
        "c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5,
        "s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6, "s7": s7,
        "macd_val": macd_val,
        "signal_val": signal_val
    }

def render_volatility_scale(lowest_dd, avg_dd, avg_du, highest_du):
    """Render the intraday drawdown/drawup scale bar using native Streamlit + Plotly."""
    import math

    def is_valid(val):
        try:
            return val is not None and not math.isnan(float(val)) and not math.isinf(float(val))
        except (TypeError, ValueError):
            return False

    if not all(is_valid(v) for v in [lowest_dd, avg_dd, avg_du, highest_du]):
        st.warning("Volatility scale data unavailable.")
        return

    lowest_dd  = float(lowest_dd)
    avg_dd     = float(avg_dd)
    avg_du     = float(avg_du)
    highest_du = float(highest_du)

    # --- Plotly horizontal bar chart ---
    # Two segments: [lowest_dd → 0] in red, [0 → highest_du] in green
    # We draw them as stacked horizontal bars on a single invisible y-axis row.

    fig = go.Figure()

    # Red segment (drawdown zone): width = abs(lowest_dd), starts at lowest_dd
    fig.add_trace(go.Bar(
        x=[abs(lowest_dd)],
        y=[""],
        base=[lowest_dd],
        orientation="h",
        marker=dict(
            color="rgba(204,34,34,0.85)",
            line=dict(width=0),
        ),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Green segment (drawup zone): width = highest_du, starts at 0
    fig.add_trace(go.Bar(
        x=[highest_du],
        y=[""],
        base=[0],
        orientation="h",
        marker=dict(
            color="rgba(31,173,74,0.85)",
            line=dict(width=0),
        ),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Marker lines for the 5 key points
    markers = [
        (lowest_dd,  "#ff3333", "▼"),
        (avg_dd,     "#ff9999", "▼"),
        (0.0,        "#ffffff", "▼"),
        (avg_du,     "#99ffb0", "▼"),
        (highest_du, "#1fad4a", "▼"),
    ]
    for x_val, color, _ in markers:
        fig.add_vline(
            x=x_val,
            line=dict(color=color, width=2, dash="dot"),
        )

    # Annotations for each marker (label above the bar)
    label_data = [
        (lowest_dd,  "#000000", f"Lowest DD<br><b>{lowest_dd:.2f}%</b>",   "bottom"),
        (avg_dd,     "#000000", f"Avg DD<br><b>{avg_dd:.2f}%</b>",         "bottom"),
        (0.0,        "#000000", f"Open<br><b>0.00%</b>",                    "bottom"),
        (avg_du,     "#000000", f"Avg DU<br><b>+{avg_du:.2f}%</b>",        "bottom"),
        (highest_du, "#000000", f"Highest DU<br><b>+{highest_du:.2f}%</b>","bottom"),
    ]

    for x_val, color, text, yanchor in label_data:
        fig.add_annotation(
            x=x_val,
            y=0,
            yref="paper",
            text=text,
            showarrow=False,
            font=dict(color=color, size=11),
            align="center",
            yanchor="top",
            yshift=-8,
        )

    padding = abs(highest_du - lowest_dd) * 0.05
    fig.update_layout(
        barmode="overlay",
        height=110,
        margin=dict(l=0, r=0, t=10, b=60),
        # paper_bgcolor="rgba(0,0,0,0)",
        # plot_bgcolor="rgba(26,28,35,0.6)",
        xaxis=dict(
            range=[lowest_dd - padding, highest_du + padding],
            showgrid=False,
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.3)",
            zerolinewidth=2,
            tickformat=".1f",
            ticksuffix="%",
            tickfont=dict(color="rgba(255,255,255,0.5)", size=10),
        ),
        yaxis=dict(visible=False),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

from analysis_core import (
    calculate_indicators,
    evaluate_strategy_row,
    finite_float,
    format_compact_number,
    format_percent,
    inspect_data_quality,
    is_finite,
    summarize_backtest,
)

def get_analysis(symbol, period, interval, ema_short, ema_long):
    data = fetch_stock_data(symbol, period, interval)
    if data is None or len(data) < 2:
        return None

    data = calculate_indicators(data, ema_short, ema_long)
    analysis = evaluate_strategy_row(data)
    analysis["df"] = data
    analysis["quality_warnings"] = inspect_data_quality(data, symbol)
    analysis["backtest"] = summarize_backtest(data)
    return analysis

TECH_HELP = {
    "RSI (14)": "Relative Strength Index using a 14-period Wilder calculation. Above 70 is often extended; below 30 is often oversold.",
    "Trend (EMA)": "Compares short and long exponential moving averages to identify the current trend bias.",
    "Sentiment": "Momentum label based on MACD versus signal line and RSI above or below 50.",
    "EMA 20": "Short-term exponential moving average. Often used as dynamic support/resistance for active trends.",
    "EMA 50": "Medium-term exponential moving average. Often used to judge institutional trend support.",
    "EMA 100": "Longer-term exponential moving average. Helps separate short pullbacks from deeper trend weakness.",
    "Market Cap": "Company equity value calculated as share price times shares outstanding.",
    "Forward P/E": "Expected price-to-earnings ratio based on forward earnings estimates.",
    "PEG": "P/E adjusted for expected growth. Lower can imply cheaper growth, but estimates can be unreliable.",
    "Revenue Growth": "Most recent reported revenue growth rate from Yahoo Finance fundamentals.",
    "Debt/Equity": "Leverage ratio comparing total debt to shareholder equity.",
    "Relative Strength": "Stock return minus benchmark return over the selected window. Positive means the stock outperformed.",
    "Regime": "Broad market condition based on SPY and QQQ trading above or below their EMA200.",
    "SPY vs EMA200": "Percent distance of SPY from its 200-day exponential moving average.",
    "QQQ vs EMA200": "Percent distance of QQQ from its 200-day exponential moving average.",
    "VIX": "CBOE volatility index. Higher values generally indicate higher market stress.",
    "Suggested Entry": "Current price adjusted by the stock's average 20-day intraday drawdown from open to low.",
    "Stop": "Risk-control level set 8% below the suggested entry.",
    "Target": "Uses 20-day resistance when above entry; otherwise falls back to a 2R target.",
    "Reward/Risk": "Potential reward divided by risk per share. Values above 2R are generally more attractive.",
    "Backtest Entries": "Historical non-Avoid signals found using the current rules.",
    "20D Win Rate": "Percentage of historical signals with a positive 20-trading-day return.",
    "Avg 20D Return": "Average 20-trading-day return after historical non-Avoid signals.",
    "Worst 20D Adverse": "Worst low-to-entry move during the 20 trading days after historical signals.",
    "20D Drawdown": "Current close compared with the highest high in the last 20 trading days.",
    "20D Drawup": "Current close compared with the lowest low in the last 20 trading days.",
    "Drawdown >= 8%": "Core entry rule: price has pulled back at least 8% from the 10-day high.",
    "Within +/-6% EMA20": "Core entry rule: price is not too stretched from EMA20.",
    "RSI 42-58": "Core entry rule: RSI is in a neutral reset zone, not overbought or deeply weak.",
    "Vol Ratio >= 1.6x": "Core entry rule: latest volume is at least 1.6 times the recent 20-day average.",
    "MACD > Signal": "Momentum rule: MACD line is above its signal line.",
    "Above EMA50": "Supporting trend rule: price is above the medium-term EMA.",
    "78%-94% of 52W High": "Supporting relative-position rule: stock is below its high but not deeply broken.",
    "Above EMA100": "Supporting trend rule: price remains above the longer-term EMA100.",
    "ADX > 20": "Supporting trend-strength rule: ADX above 20 suggests a more defined trend.",
    "Above BB Middle": "Supporting volatility rule: price is above the Bollinger middle band.",
    "Stoch RSI < 75": "Supporting momentum rule: stochastic RSI is not too extended.",
    "Price below EMA 20": "Exit rule: close below EMA20 can indicate a short-term trend break.",
    "MACD Bearish Crossover": "Exit rule: MACD below signal suggests momentum deterioration.",
    "RSI Overbought": "Exit rule: RSI above 70 can signal an extended move vulnerable to reversal.",
    "Price at Upper Bollinger Band": "Exit rule: price at the upper band can indicate volatility extension.",
    "Price near 20D Resistance": "Exit rule: price is within 2% of the 20-day resistance level.",
}

def condition_checkbox(label, passed, value_text, help_key):
    st.checkbox(
        f"{label} ({value_text})",
        value=bool(passed),
        disabled=True,
        help=TECH_HELP[help_key],
    )

# --- Sidebar ---
st.sidebar.title("🛠️ Configuration")
symbol = st.sidebar.text_input("Stock Symbol", value="AAPL").upper()
period = st.sidebar.selectbox("Period", options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
interval = st.sidebar.selectbox("Interval", options=["1d", "1wk", "1mo"], index=0)

st.sidebar.subheader("Indicator Settings")
ema_short = st.sidebar.slider("Short EMA Span", 5, 50, 20)
ema_long = st.sidebar.slider("Long EMA Span", 20, 200, 50)

# --- Main Page Execution ---
st.title("📈 Stock Insight Dashboard")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔍 Technicals", "📋 Multi-Stock Analysis", "🚀 High Growth Stocks"])

with tab1:
    if symbol:
        with st.spinner(f"Loading data for {symbol}..."):
            analysis = get_analysis(symbol, period, interval, ema_short, ema_long)
        
        if analysis:
            data = analysis['df']
            for warning in analysis.get('quality_warnings', []):
                st.warning(warning)
            # Metrics Row
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Price", f"${analysis['curr_price']:,.2f}", f"{analysis['price_change_pct']:+.2f}%")
            col2.metric(f"EMA {ema_short}", f"${analysis['ema_short_val']:,.2f}")
            col3.metric("20D Support", f"${analysis['sup_val']:,.2f}")
            col4.metric("20D Resistance", f"${analysis['res_val']:,.2f}")
            
            # Main Candlestick Chart
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=data.index, open=data['Open'], high=data['High'], 
                low=data['Low'], close=data['Close'], name="Price"
            ))
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA_1'], line=dict(color='orange', width=1), name=f'EMA {ema_short}'))
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA_2'], line=dict(color='blue', width=1), name=f'EMA {ema_long}'))
            
            fig.update_layout(
                title=f"{symbol} Price Action", 
                yaxis_title="Price",
                xaxis_rangeslider_visible=False, 
                template="plotly_dark", 
                height=600,
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Ticker '{symbol}' not found or data unavailable.")

with tab2:
    if symbol:
        analysis = get_analysis(symbol, period, interval, ema_short, ema_long)
        if analysis:
            data = analysis['df']
            st.subheader("Advanced Technical Indicators")
            
            # KPI Cards for Technicals
            t_col1, t_col2, t_col3 = st.columns(3)
            
            # RSI KPI
            rsi_status = "Overbought ⚠️" if analysis['rsi_val'] > 70 else "Oversold ⚠️" if analysis['rsi_val'] < 30 else "Neutral"
            t_col1.metric("RSI (14)", f"{analysis['rsi_val']:.2f}", rsi_status, help=TECH_HELP["RSI (14)"])
            
            # Trend KPI
            t_col2.metric("Trend (EMA)", analysis['trend'], analysis['trend_detail'], help=TECH_HELP["Trend (EMA)"])
            
            # Bullish/Bearish KPI
            t_col3.metric("Sentiment", analysis['sentiment'], analysis['sentiment_detail'], help=TECH_HELP["Sentiment"])

            # EMA Targets row
            e_col1, e_col2, e_col3 = st.columns(3)
            e_col1.metric("EMA 20", f"${analysis['ema_short_val']:,.2f}", help=TECH_HELP["EMA 20"])
            e_col2.metric("EMA 50", f"${analysis['ema_long_val']:,.2f}", help=TECH_HELP["EMA 50"])
            e_col3.metric("EMA 100", f"${analysis['ema_100_val']:,.2f}", help=TECH_HELP["EMA 100"])

            for warning in analysis.get('quality_warnings', []):
                st.warning(warning)

            st.write("---")
            st.subheader("Fundamentals, Relative Strength, and Market Regime")
            fund = get_fundamental_snapshot(symbol)
            rel_strength = get_relative_strength(symbol)
            regime = get_market_regime()

            if "Error" in fund:
                st.warning(f"Fundamental data unavailable: {fund['Error']}")
            else:
                f1, f2, f3, f4, f5 = st.columns(5)
                f1.metric("Market Cap", format_compact_number(fund.get("Market Cap")), help=TECH_HELP["Market Cap"])
                f2.metric("Forward P/E", f"{fund.get('Forward P/E'):.2f}" if is_finite(fund.get("Forward P/E")) else "N/A", help=TECH_HELP["Forward P/E"])
                f3.metric("PEG", f"{fund.get('PEG'):.2f}" if is_finite(fund.get("PEG")) else "N/A", help=TECH_HELP["PEG"])
                f4.metric("Revenue Growth", format_percent(fund.get("Revenue Growth")), help=TECH_HELP["Revenue Growth"])
                f5.metric("Debt/Equity", f"{fund.get('Debt/Equity'):.1f}" if is_finite(fund.get("Debt/Equity")) else "N/A", help=TECH_HELP["Debt/Equity"])
                st.caption(f"Sector: {fund.get('Sector', 'N/A')} | Industry: {fund.get('Industry', 'N/A')}")

            r_cols = st.columns(4)
            if "Error" in rel_strength:
                r_cols[0].warning(f"Relative strength unavailable: {rel_strength['Error']}")
            else:
                for col, key in zip(r_cols, ["20D vs SPY", "50D vs SPY", "100D vs SPY", "200D vs SPY"]):
                    col.metric(key, f"{rel_strength.get(key, 0.0):+.1f}%", help=TECH_HELP["Relative Strength"])

            m_cols = st.columns(4)
            if "Error" in regime:
                m_cols[0].warning(f"Market regime unavailable: {regime['Error']}")
            else:
                m_cols[0].metric("Regime", regime.get("Regime", "N/A"), help=TECH_HELP["Regime"])
                m_cols[1].metric("SPY vs EMA200", f"{regime.get('SPY vs EMA200', 0.0):+.1f}%", help=TECH_HELP["SPY vs EMA200"])
                m_cols[2].metric("QQQ vs EMA200", f"{regime.get('QQQ vs EMA200', 0.0):+.1f}%", help=TECH_HELP["QQQ vs EMA200"])
                m_cols[3].metric("VIX", f"{regime.get('VIX'):.2f}" if is_finite(regime.get("VIX")) else "N/A", help=TECH_HELP["VIX"])

            st.write("---")
            st.subheader("Trade Plan and Backtest Check")
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Suggested Entry", f"${analysis['suggested_entry']:,.2f}", help=TECH_HELP["Suggested Entry"])
            p2.metric("Stop", f"${analysis['stop_loss']:,.2f}", help=TECH_HELP["Stop"])
            p3.metric("Target", f"${analysis['target_resistance']:,.2f}", help=TECH_HELP["Target"])
            p4.metric("Reward/Risk", f"{analysis['reward_risk']:.2f}R", help=TECH_HELP["Reward/Risk"])

            bt = analysis.get("backtest", {})
            if bt.get("entry_count", 0) == 0:
                st.info(bt.get("message", "No backtest entries available."))
            else:
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Backtest Entries", bt["entry_count"], help=TECH_HELP["Backtest Entries"])
                b2.metric("20D Win Rate", f"{bt['win_rate_20d']:.1f}%", help=TECH_HELP["20D Win Rate"])
                b3.metric("Avg 20D Return", f"{bt['avg_return_20d']:+.2f}%", help=TECH_HELP["Avg 20D Return"])
                b4.metric("Worst 20D Adverse", f"{bt['worst_adverse_20d']:.2f}%", help=TECH_HELP["Worst 20D Adverse"])
                with st.expander("Backtest by score level"):
                    st.dataframe(bt["by_level"], use_container_width=True, hide_index=True)

            # 20-Day Drawdown/Drawup metrics
            d_col1, d_col2 = st.columns(2)
            d_col1.metric("20D Drawdown", f"{analysis['dd_20d']:.2f}%", help=TECH_HELP["20D Drawdown"])
            d_col2.metric("20D Drawup", f"{analysis['du_20d']:.2f}%", help=TECH_HELP["20D Drawup"])

            st.write("")
            st.markdown("### 📊 Intraday Volatility Spectrum (20-Day)")
            render_volatility_scale(
                analysis['lowest_dd'],
                analysis['avg_dd'],
                analysis['avg_du'],
                analysis['highest_du']
            )

            st.write("---")
            buy_col, sell_col = st.columns(2)
            
            with buy_col:
                st.subheader("🎯 Buying Score (Entry Rules)")
                
                with st.expander("ℹ️ How the Scoring System Works"):
                    st.markdown("""
                    **The Goal:** This system combines 12 technical filters to find "high-probability" setups where momentum meets value.
                    """)

                # Display Scoring
                st.markdown(f"""
                <div style="background-color: {analysis['color']}; padding: 20px; border-radius: 10px; text-align: center; color: black;">
                    <h1 style="margin: 0;">{analysis['entry_level']}</h1>
                    <p style="margin: 0; font-weight: bold;">{analysis['pos_size']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("") 
                st.write(f"**Core Conditions:** {analysis['core_score']}/5")
                st.write(f"**Supporting Conditions:** {analysis['supp_score']}/7")
                if analysis['risk_fail_rsi']: st.error("⚠️ Risk: RSI too high (> 68)")
                if analysis['risk_fail_ema20']: st.error("⚠️ Risk: Too far above EMA20 (> 8%)")

                # Details Expander
                with st.expander("🔍 View Checklist Details"):
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        st.write("**Core Conditions**")
                        condition_checkbox("Drawdown >= 8%", analysis['c1'], f"{analysis['drawdown_10d']:.1%}", "Drawdown >= 8%")
                        condition_checkbox("Within +/-6% EMA20", analysis['c2'], f"{analysis['ema20_dist']:.1%}", "Within +/-6% EMA20")
                        condition_checkbox("RSI 42-58", analysis['c3'], f"{analysis['rsi_val']:.1f}", "RSI 42-58")
                        condition_checkbox("Vol Ratio >= 1.6x", analysis['c4'], f"{analysis['vol_ratio']:.1f}x", "Vol Ratio >= 1.6x")
                        condition_checkbox("MACD > Signal", analysis['c5'], "core", "MACD > Signal")
                    
                    with c_col2:
                        st.write("**Supporting Conditions**")
                        condition_checkbox("Above EMA50", analysis['s1'], "price > EMA50", "Above EMA50")
                        condition_checkbox("MACD > Signal", analysis['s2'], "support", "MACD > Signal")
                        condition_checkbox("78%-94% of 52W High", analysis['s3'], "range", "78%-94% of 52W High")
                        condition_checkbox("Above EMA100", analysis['s4'], "price > EMA100", "Above EMA100")
                        condition_checkbox("ADX > 20", analysis['s5'], f"{analysis['adx_val']:.1f}", "ADX > 20")
                        condition_checkbox("Above BB Middle", analysis['s6'], "price > mid", "Above BB Middle")
                        condition_checkbox("Stoch RSI < 75", analysis['s7'], f"{analysis['stoch_rsi']:.1f}", "Stoch RSI < 75")

            with sell_col:
                st.subheader("🚩 Selling Score (Exit Rules)")
                
                with st.expander("ℹ️ How the Exit Strategy Works"):
                    st.markdown("""
                    **The Goal:** To protect capital and lock in gains using a systematic approach.
                    """)

                # Display Exit Scoring
                st.markdown(f"""
                <div style="background-color: {analysis['exit_color']}; padding: 20px; border-radius: 10px; text-align: center; color: white;">
                    <h2 style="margin: 0;">{analysis['exit_level']}</h2>
                    <p style="margin: 0; font-weight: bold;">{analysis['exit_action']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("") 
                st.write(f"**Exit Signals Triggered:** {analysis['exit_score']}/5")
                condition_checkbox("Price below EMA 20", analysis['ex1'], "trend break", "Price below EMA 20")
                condition_checkbox("MACD Bearish Crossover", analysis['ex2'], "momentum", "MACD Bearish Crossover")
                condition_checkbox("RSI Overbought", analysis['ex3'], ">70", "RSI Overbought")
                condition_checkbox("Price at Upper Bollinger Band", analysis['ex4'], "extension", "Price at Upper Bollinger Band")
                condition_checkbox("Price near 20D Resistance", analysis['ex5'], "within 2%", "Price near 20D Resistance")

            st.write("---")
            st.subheader("📊 Interactive Multi-Indicator Analysis")
            
            selected_indicators = st.multiselect(
                "Select indicators to overlay or view:",
                options=["EMAs (20, 50, 100)", "Bollinger Bands", "Support/Resistance", "RSI", "MACD", "ADX"],
                default=["EMAs (20, 50, 100)", "RSI"],
                help="Choose which overlays and oscillator panels to show in the combined technical chart."
            )

            # Unified Chart Logic
            rows = 1
            if "RSI" in selected_indicators: rows += 1
            if "MACD" in selected_indicators: rows += 1
            if "ADX" in selected_indicators: rows += 1
            
            row_heights = [0.5] + [0.15] * (rows - 1)
            
            fig_multi = make_subplots(
                rows=rows, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.05,
                row_heights=row_heights
            )

            # Main Price Chart
            fig_multi.add_trace(go.Candlestick(
                x=data.index, open=data['Open'], high=data['High'], 
                low=data['Low'], close=data['Close'], name="Price"
            ), row=1, col=1)

            if "EMAs (20, 50, 100)" in selected_indicators:
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['EMA_1'], line=dict(color='orange', width=1.5), name="EMA 20"), row=1, col=1)
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['EMA_2'], line=dict(color='blue', width=1.5), name="EMA 50"), row=1, col=1)
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['EMA_100'], line=dict(color='purple', width=1.5), name="EMA 100"), row=1, col=1)

            if "Bollinger Bands" in selected_indicators:
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['BB_Upper'], line=dict(color='rgba(173, 216, 230, 0.4)', width=1), name="BB Upper"), row=1, col=1)
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['BB_Lower'], line=dict(color='rgba(173, 216, 230, 0.4)', width=1), fill='tonexty', name="BB Lower"), row=1, col=1)

            if "Support/Resistance" in selected_indicators:
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['Resistance'], line=dict(color='red', width=1, dash='dash'), name="20D Res"), row=1, col=1)
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['Support'], line=dict(color='green', width=1, dash='dash'), name="20D Sup"), row=1, col=1)

            current_row = 2
            if "RSI" in selected_indicators:
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='magenta', width=1.5), name="RSI"), row=current_row, col=1)
                fig_multi.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
                fig_multi.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)
                fig_multi.update_yaxes(title_text="RSI", row=current_row, col=1)
                current_row += 1

            if "MACD" in selected_indicators:
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['MACD'], line=dict(color='cyan', width=1), name="MACD"), row=current_row, col=1)
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['Signal_Line'], line=dict(color='orange', width=1), name="Signal"), row=current_row, col=1)
                hist_colors = ['green' if x >= 0 else 'red' for x in data['MACD_Hist']]
                fig_multi.add_trace(go.Bar(x=data.index, y=data['MACD_Hist'], marker_color=hist_colors, name="Histogram"), row=current_row, col=1)
                fig_multi.update_yaxes(title_text="MACD", row=current_row, col=1)
                current_row += 1

            if "ADX" in selected_indicators:
                fig_multi.add_trace(go.Scatter(x=data.index, y=data['ADX'], line=dict(color='yellow', width=1.5), name="ADX"), row=current_row, col=1)
                fig_multi.add_hline(y=25, line_dash="dash", line_color="white", row=current_row, col=1)
                fig_multi.update_yaxes(title_text="ADX", row=current_row, col=1)
                current_row += 1

            fig_multi.update_layout(
                height=400 + (rows * 150),
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_multi, use_container_width=True)
        else:
            st.error(f"Ticker '{symbol}' not found or data unavailable.")

with tab3:
    st.subheader("Multi-Stock Technical Comparison")
    multi_input = st.text_input("Enter Ticker Symbols (comma-separated)", value="AAPL, TSLA, MSFT, GOOGL, NVDA, AMD, META")
    
    if multi_input:
        symbols = [s.strip().upper() for s in multi_input.split(",") if s.strip()]
        
        if symbols:
            with st.spinner(f"Analyzing {len(symbols)} stocks..."):
                results = []
                for s in symbols:
                    res = get_analysis(s, period, interval, ema_short, ema_long)
                    if res:
                        results.append({
                            "Symbol": s,
                            "Price": res['curr_price'],
                            "20D Support": res['sup_val'],
                            "20D Resistance": res['res_val'],
                            "EMA20": res['ema_short_val'],
                            "EMA50": res['ema_long_val'],
                            "RSI (14)": res['rsi_val'],
                            "Trend (EMA)": res['trend'],
                            "Sentiment": res['sentiment'],
                            "Avg Intraday DD": res['avg_dd'],
                            "Avg Intraday DU": res['avg_du'],
                            "Buying Score": res['entry_level'],
                            "Selling Score": res['exit_level']
                        })
                
                if results:
                    df_multi = pd.DataFrame(results)
                    
                    # Formatting
                    st.dataframe(
                        df_multi.style.format({
                            "Price": "${:,.2f}",
                            "20D Support": "${:,.2f}",
                            "20D Resistance": "${:,.2f}",
                            "EMA20": "${:,.2f}",
                            "EMA50": "${:,.2f}",
                            "RSI (14)": "{:.2f}",
                            "Avg Intraday DD": "{:.2f}%",
                            "Avg Intraday DU": "{:.2f}%"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("No valid data found for the entered tickers.")

with tab4:
    st.subheader("🚀 Top 20 High Growth Stocks from S&P500")
    st.caption("Scanner uses the current S&P 500 membership list. Use this for current discovery, not historical backtests, because it has survivorship bias.")
    
    # 1. Fetch S&P500 tickers & data
    @st.cache_data(ttl=86400)
    def get_sp500_tickers():
        try:
            tables = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
            df = tables[0]
            tickers = df['Symbol'].tolist()
            tickers = [t.replace('.', '-') for t in tickers]
            return tickers
        except Exception as e:
            return [
                "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK-B", "LLY", "AVGO", "JPM",
                "TSLA", "V", "UNH", "XOM", "MA", "HD", "PG", "COST", "JNJ", "ABBV",
                "BAC", "MRK", "AMD", "ADBE", "CRM", "NFLX", "CVX", "WMT", "TMO", "PEP",
                "DIS", "KO", "ACN", "INTC", "ORCL", "CSCO", "MCD", "WFC", "XOM", "TXN"
            ]

    @st.cache_data(ttl=3600)
    def load_and_analyze_sp500(tickers):
        data = yf.download(tickers, period="2y", interval="1d", group_by="column")
        results = []
        for ticker in tickers:
            try:
                # Extract ticker data
                ticker_df = pd.DataFrame()
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    if col in data.columns and ticker in data[col].columns:
                        ticker_df[col] = data[col][ticker]
                
                if len(ticker_df) < 200:
                    continue
                
                ticker_df = ticker_df.dropna(subset=['Close'])
                if len(ticker_df) < 150:
                    continue
                
                df_ind = calculate_indicators(ticker_df)
                
                # Calculate growth
                def get_growth(days):
                    if len(df_ind) <= days:
                        return 0.0
                    c_curr = df_ind['Close'].iloc[-1]
                    c_prev = df_ind['Close'].iloc[-days-1]
                    if pd.isna(c_curr) or pd.isna(c_prev) or c_prev == 0:
                        return 0.0
                    return float((c_curr - c_prev) / c_prev * 100)
                
                g_20 = get_growth(20)
                g_50 = get_growth(50)
                g_100 = get_growth(100)
                g_200 = get_growth(200)
                
                signal = evaluate_strategy_row(df_ind)
                color_map = {
                    "red": "#FFCCCC",
                    "green": "#CCFFCC",
                    "lightgreen": "#E5FFE5",
                    "orange": "#FFE5CC",
                    "yellow": "#FFFFCC"
                }
                
                results.append({
                    "ticker": ticker,
                    "curr_price": signal['curr_price'],
                    "growth_20d": g_20,
                    "growth_50d": g_50,
                    "growth_100d": g_100,
                    "growth_200d": g_200,
                    "ema20": signal['ema_short_val'],
                    "ema50": signal['ema_long_val'],
                    "ema100": signal['ema_100_val'],
                    "ema200": signal['ema_200_val'],
                    "core_score": signal['core_score'],
                    "supp_score": signal['supp_score'],
                    "total_score": signal['core_score'] + signal['supp_score'],
                    "entry_level": signal['entry_level'],
                    "pos_size": signal['pos_size'],
                    "color": color_map.get(signal['color'], "#FFCCCC"),
                    "c1": signal['c1'], "c2": signal['c2'], "c3": signal['c3'], "c4": signal['c4'], "c5": signal['c5'],
                    "drawdown_10d": signal['drawdown_10d'],
                    "ema20_dist": signal['ema20_dist'],
                    "rsi_val": signal['rsi_val'],
                    "vol_ratio": signal['vol_ratio'],
                    "macd_val": signal['macd_val'],
                    "signal_val": signal['signal_val']
                })
            except Exception as e:
                continue
        return results
    
    tickers = get_sp500_tickers()
    with st.spinner("Fetching S&P 500 stock data & scanning growth (this can take up to 25s on first run)..."):
        sp500_data = load_and_analyze_sp500(tickers)
    
    if not sp500_data:
        st.error("No data fetched for S&P 500 stocks.")
    else:
        # Filter Slicers
        st.markdown("### 🔍 Filter by Core Buying Conditions")
        f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
        
        c1_filter = f_col1.selectbox("Drawdown >= 8% (c1)", ["Pass Only", "All"], index=0, key="f_c1")
        c2_filter = f_col2.selectbox("Within ±6% EMA20 (c2)", ["Pass Only", "All"], index=0, key="f_c2")
        c3_filter = f_col3.selectbox("RSI 42-58 (c3)", ["Pass Only", "All"], index=0, key="f_c3")
        c4_filter = f_col4.selectbox("Vol Ratio >= 1.6x (c4)", ["Pass Only", "All"], index=0, key="f_c4")
        c5_filter = f_col5.selectbox("MACD > Signal (c5)", ["Pass Only", "All"], index=0, key="f_c5")
        
        # Radio button selection for growth
        st.markdown("### 📈 Select Growth Horizon")
        growth_horizon = st.radio(
            "Sort and display by:",
            options=["20D High Growth", "50D High Growth", "100D High Growth", "200D High Growth"],
            horizontal=True,
            key="growth_horiz"
        )
        
        # Apply filter logic
        filtered_stocks = []
        for stock in sp500_data:
            if c1_filter == "Pass Only" and not stock['c1']:
                continue
            if c2_filter == "Pass Only" and not stock['c2']:
                continue
            if c3_filter == "Pass Only" and not stock['c3']:
                continue
            if c4_filter == "Pass Only" and not stock['c4']:
                continue
            if c5_filter == "Pass Only" and not stock['c5']:
                continue
            filtered_stocks.append(stock)
            
        horizon_key_map = {
            "20D High Growth": "growth_20d",
            "50D High Growth": "growth_50d",
            "100D High Growth": "growth_100d",
            "200D High Growth": "growth_200d"
        }
        sort_key = horizon_key_map[growth_horizon]
        
        top_stocks = sorted(filtered_stocks, key=lambda x: x[sort_key], reverse=True)[:20]
        
        if not top_stocks:
            st.warning("⚠️ No stocks match the selected core condition filters. Try changing some filters to 'All'.")
        else:
            st.markdown(f"Showing **Top {len(top_stocks)}** S&P 500 stocks sorted by chosen growth:")
            
            # Display cards in 1-column layout
            for stock in top_stocks:
                with st.container(border=True):
                    h_col1, h_col2 = st.columns([2, 1])
                    h_col1.markdown(f"### **{stock['ticker']}**")
                    h_col2.markdown(f"### **${stock['curr_price']:,.2f}**")
                    
                    st.write("**% Growth**")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("20D", f"{stock['growth_20d']:+.1f}%")
                    m2.metric("50D", f"{stock['growth_50d']:+.1f}%")
                    m3.metric("100D", f"{stock['growth_100d']:+.1f}%")
                    m4.metric("200D", f"{stock['growth_200d']:+.1f}%")
                    
                    st.write("**EMAs**")
                    e1, e2, e3, e4 = st.columns(4)
                    e1.metric("EMA20", f"${stock['ema20']:,.2f}")
                    e2.metric("EMA50", f"${stock['ema50']:,.2f}")
                    e3.metric("EMA100", f"${stock['ema100']:,.2f}")
                    e4.metric("EMA200", f"${stock['ema200']:,.2f}")
                    
                    st.write("")
                    # Score Banner
                    score_banner_html = f"""
                    <div style="background-color: {stock['color']}; padding: 12px; border-radius: 8px; text-align: center; color: black; font-weight: bold; margin-bottom: 12px;">
                        Buying Score: {stock['entry_level']} ({stock['total_score']}/12 Score) | Pos: {stock['pos_size']}
                    </div>
                    """
                    st.markdown(score_banner_html, unsafe_allow_html=True)
                    
                    with st.expander("🔍 View Core Conditions Checklist Details"):
                        det_col1, det_col2 = st.columns(2)
                        with det_col1:
                            st.write(f"{'✅' if stock['c1'] else '❌'} Drawdown >= 8% ({stock['drawdown_10d']:.1%})")
                            st.write(f"{'✅' if stock['c2'] else '❌'} Within ±6% EMA20 ({stock['ema20_dist']:.1%})")
                            st.write(f"{'✅' if stock['c3'] else '❌'} RSI 42-58 ({stock['rsi_val']:.1f})")
                        with det_col2:
                            st.write(f"{'✅' if stock['c4'] else '❌'} Vol Ratio >= 1.6x ({stock['vol_ratio']:.1f}x)")
                            st.write(f"{'✅' if stock['c5'] else '❌'} MACD > Signal")
                            st.write(f"Core score: **{stock['core_score']}/5**")

# --- Footer ---
st.write("---")
st.markdown(
    """
    <div style="text-align: center; color: #888888; font-size: 0.8em;">
        Stock Insight Dashboard | Built with Streamlit & yfinance | Powered by Gemini
    </div>
    """,
    unsafe_allow_html=True
)
