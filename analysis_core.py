from datetime import datetime
import math

import pandas as pd


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
    if not is_finite(value):
        return "N/A"
    value = float(value)
    return f"{value * 100:.1f}%" if abs(value) <= 2 else f"{value:.1f}%"


def calculate_indicators(df, ema_span_1=20, ema_span_2=50):
    df = df.copy()
    df['EMA_1'] = df['Close'].ewm(span=ema_span_1, adjust=False).mean()
    df['EMA_2'] = df['Close'].ewm(span=ema_span_2, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_100'] = df['Close'].ewm(span=100, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, pd.NA)
    df['RSI'] = 100 - (100 / (1 + rs))
    df.loc[(loss == 0) & (gain > 0), 'RSI'] = 100
    df.loc[(loss == 0) & (gain == 0), 'RSI'] = 50

    rsi_min = df['RSI'].rolling(window=14).min()
    rsi_max = df['RSI'].rolling(window=14).max()
    df['Stoch_RSI'] = (df['RSI'] - rsi_min) / (rsi_max - rsi_min).replace(0, pd.NA) * 100

    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']

    df['Resistance'] = df['High'].rolling(window=20).max()
    df['Support'] = df['Low'].rolling(window=20).min()
    df['Drawdown_20d'] = (df['Close'] - df['Resistance']) / df['Resistance'] * 100
    df['Drawup_20d'] = (df['Close'] - df['Support']) / df['Support'] * 100

    df['BB_Mid'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (2 * df['BB_Std'])
    df['BB_Lower'] = df['BB_Mid'] - (2 * df['BB_Std'])

    up_move = df['High'].diff()
    down_move = -df['Low'].diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
    smoothed_tr = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smoothed_tr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smoothed_tr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    df['ADX'] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    df['High_52w'] = df['High'].rolling(window=252, min_periods=1).max()
    df['High_10d'] = df['High'].rolling(window=10, min_periods=1).max()
    df['Intraday_Drawdown_Pct'] = ((df['Low'] - df['Open']) / df['Open']) * 100
    df['Intraday_Drawup_Pct'] = ((df['High'] - df['Open']) / df['Open']) * 100
    df['Avg_Drawdown'] = df['Intraday_Drawdown_Pct'].rolling(window=20).mean()
    df['Avg_Drawup'] = df['Intraday_Drawup_Pct'].rolling(window=20).mean()
    df['Lowest_Drawdown'] = df['Intraday_Drawdown_Pct'].rolling(window=20).min()
    df['Highest_Drawdown'] = df['Intraday_Drawdown_Pct'].rolling(window=20).max()
    df['Lowest_Drawup'] = df['Intraday_Drawup_Pct'].rolling(window=20).min()
    df['Highest_Drawup'] = df['Intraday_Drawup_Pct'].rolling(window=20).max()
    return df


def inspect_data_quality(df, symbol):
    warnings = []
    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required if col not in df.columns]
    if missing:
        return [f"{symbol}: missing required columns: {', '.join(missing)}."]
    if len(df) < 252:
        warnings.append(f"{symbol}: less than one trading year of data; 52-week and 200-day signals may be immature.")
    latest_ts = df.index[-1]
    if hasattr(latest_ts, "to_pydatetime"):
        latest_dt = latest_ts.to_pydatetime().replace(tzinfo=None)
        if (datetime.now() - latest_dt).days > 5:
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
    ema_50_val = finite_float(row['EMA_50'])
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
    vol_ratio = finite_float(row['Volume']) / avg_vol if avg_vol > 0 else 0.0

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

    return {
        "curr_price": curr_price, "price_change_pct": price_change_pct,
        "ema_short_val": ema_short_val, "ema_long_val": ema_long_val,
        "ema_50_val": ema_50_val, "ema_100_val": ema_100_val, "ema_200_val": ema_200_val,
        "atr_val": atr_val, "rsi_val": rsi_val, "res_val": res_val, "sup_val": sup_val,
        "trend": trend, "trend_detail": trend_detail, "sentiment": sentiment, "sentiment_detail": sentiment_detail,
        "dd_20d": finite_float(row['Drawdown_20d']), "du_20d": finite_float(row['Drawup_20d']),
        "avg_dd": avg_dd, "avg_du": finite_float(row['Avg_Drawup']),
        "lowest_dd": finite_float(row['Lowest_Drawdown']), "highest_dd": finite_float(row['Highest_Drawdown']),
        "lowest_du": finite_float(row['Lowest_Drawup']), "highest_du": finite_float(row['Highest_Drawup']),
        "entry_level": entry_level, "pos_size": pos_size, "color": color,
        "core_score": core_score, "supp_score": supp_score,
        "risk_fail_rsi": risk_fail_rsi, "risk_fail_ema20": risk_fail_ema20,
        "exit_level": exit_level, "exit_color": exit_color, "exit_action": exit_action,
        "exit_score": exit_score, "ex1": ex1, "ex2": ex2, "ex3": ex3, "ex4": ex4, "ex5": ex5,
        "drawdown_10d": drawdown_10d, "ema20_dist": ema20_dist, "vol_ratio": vol_ratio,
        "adx_val": adx_val, "stoch_rsi": stoch_rsi,
        "c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5,
        "s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6, "s7": s7,
        "macd_val": macd_val, "signal_val": signal_val,
        "suggested_entry": suggested_entry, "stop_loss": stop_loss, "target_resistance": target_resistance,
        "risk_per_share": risk_per_share, "reward_per_share": reward_per_share,
        "reward_risk": reward_per_share / risk_per_share if risk_per_share else 0.0,
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
        rows.append({
            "level": signal['entry_level'],
            "ret_5d": ret_5d,
            "ret_20d": ret_20d,
            "max_adverse": (future_low - entry_price) / entry_price * 100,
        })
    if not rows:
        return {"entry_count": 0, "message": "No non-Avoid historical entries found under the current rules."}
    bt = pd.DataFrame(rows)
    return {
        "entry_count": int(len(bt)),
        "win_rate_20d": float((bt['ret_20d'] > 0).mean() * 100),
        "avg_return_5d": float(bt['ret_5d'].mean()),
        "avg_return_20d": float(bt['ret_20d'].mean()),
        "worst_adverse_20d": float(bt['max_adverse'].min()),
        "by_level": bt.groupby('level')['ret_20d'].agg(['count', 'mean']).reset_index(),
    }
