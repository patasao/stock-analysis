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


def format_compact_number(value, currency="$", suffix=""):
    if not is_finite(value):
        return "N/A"
    value = float(value)
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"{currency}{value / 1_000_000_000_000:.2f}T{suffix}"
    if abs_value >= 1_000_000_000:
        return f"{currency}{value / 1_000_000_000:.2f}B{suffix}"
    if abs_value >= 1_000_000:
        return f"{currency}{value / 1_000_000:.2f}M{suffix}"
    return f"{currency}{value:,.0f}{suffix}"


def format_percent(value):
    if not is_finite(value):
        return "N/A"
    value = float(value)
    return f"{value * 100:.1f}%" if abs(value) <= 2 else f"{value:.1f}%"


def calculate_indicators(df, ema_span_1=20, ema_span_2=50):
    df = df.copy()
    df['EMA_1'] = df['Close'].ewm(span=ema_span_1, adjust=False).mean()
    df['EMA_2'] = df['Close'].ewm(span=ema_span_2, adjust=False).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
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
    ema_20_val = finite_float(row['EMA_20'])
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
    row_pos = idx if idx >= 0 else len(data) - 1
    start_idx = max(0, row_pos - 20)
    avg_vol = finite_float(data['Volume'].iloc[start_idx:row_pos].mean())
    if avg_vol <= 0:
        avg_vol = finite_float(data['Volume'].iloc[max(0, row_pos - 19):row_pos + 1].mean())
    vol_ratio = finite_float(row['Volume']) / avg_vol if avg_vol > 0 else 0.0

    high_52w = finite_float(row['High_52w'], curr_price)
    bb_mid = finite_float(row['BB_Mid'], curr_price)
    # Setup checks emphasize price structure, confirmation, and avoiding an
    # extended entry. Scores are decision support; external catalyst/event data
    # is not inferred from price history.
    recent_window = data.iloc[max(0, row_pos - 9):row_pos + 1]
    prior_window = data.iloc[max(0, row_pos - 19):max(0, row_pos - 9)]
    recent_low = finite_float(recent_window['Low'].min(), sup_val)
    prior_high = finite_float(data['High'].iloc[max(0, row_pos - 20):row_pos].max(), res_val)
    ema20_slope = ema_20_val > finite_float(data['EMA_20'].iloc[max(0, row_pos - 5)])
    higher_highs = bool(len(prior_window) >= 5 and recent_window['High'].max() > prior_window['High'].max())
    higher_lows = bool(len(prior_window) >= 5 and recent_window['Low'].min() > prior_window['Low'].min())
    structure_improving = curr_price > ema_20_val and ema20_slope and (higher_highs or higher_lows or curr_price > ema_50_val)

    prior_breakout_level = prior_high
    breakout = bool(prior_breakout_level and curr_price > prior_breakout_level)
    breakout_confirmed = breakout and vol_ratio >= 1.2 and curr_price <= prior_breakout_level + max(0.5 * atr_val, 0.01)

    # Look for a recent close-confirmed breakout followed by a touch and hold
    # of that same level. This prevents labeling any price near its highs a retest.
    historical_breakouts = []
    hist_start = max(20, row_pos - 10)
    for breakout_pos in range(hist_start, row_pos):
        level = finite_float(data['High'].iloc[max(0, breakout_pos - 20):breakout_pos].max())
        breakout_close = finite_float(data['Close'].iloc[breakout_pos])
        breakout_volume = finite_float(data['Volume'].iloc[breakout_pos])
        breakout_avg_volume = finite_float(data['Volume'].iloc[max(0, breakout_pos - 20):breakout_pos].mean())
        if level and breakout_close > level and breakout_avg_volume and breakout_volume >= 1.2 * breakout_avg_volume:
            historical_breakouts.append(level)
    retest_level = historical_breakouts[-1] if historical_breakouts else None
    retest_setup = bool(
        retest_level and curr_price >= retest_level and
        finite_float(row['Low']) <= retest_level + max(0.5 * atr_val, 0.01) and
        curr_price <= retest_level + max(1.0 * atr_val, 0.01) and
        curr_price >= ema_20_val and vol_ratio <= 1.2
    )

    support_zones = [value for value in [ema_20_val, ema_50_val, sup_val] if 0 < value <= curr_price]
    pullback_level = min(support_zones, key=lambda value: abs(curr_price - value)) if support_zones else None
    support_holds = bool(
        pullback_level and finite_float(row['Low']) <= pullback_level + max(0.5 * atr_val, 0.01) and
        curr_price >= pullback_level and curr_price >= ema_20_val
    )
    pullback_setup = bool(
        structure_improving and support_holds and vol_ratio <= 1.0 and
        (macd_val > signal_val or rsi_val > finite_float(data['RSI'].iloc[max(0, row_pos - 3)]))
    )
    breakout = breakout_confirmed
    c1 = structure_improving
    c2 = support_holds
    c3 = macd_val > signal_val or (rsi_val >= 50 and rsi_val > finite_float(data['RSI'].iloc[max(0, row_pos - 3)]))
    c4 = vol_ratio >= 1.2 if breakout else vol_ratio <= 1.2
    c5 = curr_price > ema_50_val or (curr_price > ema_20_val and ema20_slope)
    core_score = sum([c1, c2, c3, c4, c5])

    s1 = curr_price > ema_long_val
    s2 = curr_price > ema_100_val
    s3 = adx_val > 18
    s4 = curr_price > bb_mid
    s5 = 45 <= rsi_val <= 70
    s6 = vol_ratio >= 1.2 if breakout else vol_ratio <= 1.3
    s7 = curr_price > ema_200_val
    rs_market_50 = None
    rs_sector_50 = None
    if row_pos >= 50:
        prior_stock = finite_float(data['Close'].iloc[row_pos - 50])
        if prior_stock:
            if 'Benchmark_Market_Close' in data:
                market_now = finite_float(row.get('Benchmark_Market_Close'))
                market_then = finite_float(data['Benchmark_Market_Close'].iloc[row_pos - 50])
                if market_now and market_then:
                    rs_market_50 = ((curr_price / prior_stock) - (market_now / market_then)) * 100
            if 'Benchmark_Sector_Close' in data:
                sector_now = finite_float(row.get('Benchmark_Sector_Close'))
                sector_then = finite_float(data['Benchmark_Sector_Close'].iloc[row_pos - 50])
                if sector_now and sector_then:
                    rs_sector_50 = ((curr_price / prior_stock) - (sector_now / sector_then)) * 100
    s8 = rs_market_50 is not None and rs_market_50 > 0
    s9 = rs_sector_50 is not None and rs_sector_50 > 0
    supp_score = sum([s1, s2, s3, s4, s5, s6, s7, s8, s9])

    risk_fail_rsi = rsi_val > 75
    risk_fail_ema20 = ema20_dist > 0.10
    candle_range = finite_float(row['High']) - finite_float(row['Low'])
    wide_candle = atr_val > 0 and candle_range > 2.0 * atr_val

    bb_upper = finite_float(row['BB_Upper'])
    ex1 = curr_price < ema_20_val and curr_price < ema_50_val
    ex2 = macd_val < signal_val
    ex3 = rsi_val > 75
    ex4 = curr_price >= bb_upper if bb_upper else False

    # Entry reference follows the setup: pullbacks use a tested support/EMA
    # zone, retests use the recently broken level, and confirmed breakouts use
    # prior resistance. No entry price is emitted without a confirmed setup.
    if breakout_confirmed:
        setup_type = "Breakout"
        setup_level = prior_breakout_level
        suggested_entry = setup_level
    elif retest_setup:
        setup_type = "Breakout retest"
        setup_level = retest_level
        suggested_entry = setup_level
    elif pullback_setup:
        setup_type = "Pullback"
        setup_level = pullback_level
        suggested_entry = setup_level
    else:
        setup_type = "No confirmed setup"
        setup_level = None
        suggested_entry = None

    # The stop sits below the actual setup invalidation level, with a small
    # ATR buffer. It is not based on a fixed percentage of entry.
    trade_entry = suggested_entry if suggested_entry is not None else curr_price
    stop_basis = setup_level if setup_level is not None else (min(recent_low, sup_val) if sup_val else recent_low)
    calculated_stop = stop_basis - (0.1 * atr_val)
    stop_loss = calculated_stop if setup_level is not None else None
    risk_per_share = max(trade_entry - calculated_stop, 0.0) if setup_level is not None else 0.0
    # A trade is invalid as soon as its technical stop trades, even if the
    # closing price later recovers above support.
    ex5 = setup_level is not None and finite_float(row['Low']) <= calculated_stop
    exit_score = sum([ex1, ex2, ex3, ex4, ex5])
    exit_level, exit_color, exit_action = "Hold", "gray", "Maintain position; honor the technical stop"
    if ex5:
        exit_level, exit_color, exit_action = "SELL / REDUCE", "red", "Technical stop hit; exit the invalidated setup"
    elif ex1 and ex2:
        exit_level, exit_color, exit_action = "SELL / REDUCE", "red", "Trend and momentum deteriorated; exit or reduce"
    elif exit_score >= 1:
        exit_level, exit_color, exit_action = "CAUTION", "orange", "Review support, event risk, and stop discipline"

    # Targets must map to observable price structure. Identify prior local
    # swing highs, then use the nearest overhead level for TP1 and the next
    # higher level for TP2. A breakout can use a measured-move projection when
    # there is no second overhead swing high.
    highs = data['High'].iloc[max(0, row_pos - 252):max(0, row_pos - 1)].astype(float)
    local_high = highs.eq(highs.rolling(5, center=True, min_periods=3).max())
    target_levels = sorted({round(float(level), 6) for level in highs[local_high].dropna() if setup_level is not None and float(level) > trade_entry})
    if setup_level is not None and res_val > trade_entry and setup_type != "Breakout":
        target_levels.append(float(res_val))
    target_levels = sorted(set(target_levels))
    tp1 = target_levels[0] if target_levels else None
    tp2 = next((level for level in target_levels if tp1 is not None and level > tp1 + max(atr_val, 0.01)), None)
    measured_move = False
    if tp2 is None and setup_type == "Breakout":
        base = data.iloc[max(0, row_pos - 20):row_pos]
        base_height = finite_float(base['High'].max()) - finite_float(base['Low'].min()) if len(base) else 0.0
        projection = trade_entry + base_height
        if base_height > 0 and projection > (tp1 or trade_entry):
            tp2 = projection
            measured_move = True
    target_resistance = tp1
    reward_per_share = max(tp1 - trade_entry, 0.0) if tp1 is not None else 0.0
    rr_tp1 = reward_per_share / risk_per_share if risk_per_share else 0.0
    rr_tp2 = max(tp2 - trade_entry, 0.0) / risk_per_share if risk_per_share and tp2 is not None else 0.0

    resistance_too_close = tp1 is None or rr_tp1 < 1.5 or tp2 is None or rr_tp2 < 2.0
    price_away_from_entry = setup_level is not None and curr_price > trade_entry + (0.5 * atr_val)
    extended = risk_fail_rsi or risk_fail_ema20 or resistance_too_close or price_away_from_entry or wide_candle
    setup_score = core_score + supp_score
    entry_level, pos_size, color = "Avoid", "No Trade", "red"
    if ex5:
        entry_level, pos_size = "Avoid", "No Trade: setup invalidated at technical stop"
    elif price_away_from_entry or risk_fail_rsi or risk_fail_ema20 or wide_candle:
        entry_level, pos_size = "Wait", "Extended / wide candle; wait for setup entry"
    elif setup_level is None and structure_improving and setup_score >= 6:
        entry_level, pos_size, color = "Wait", "Wait for pullback, breakout, or retest confirmation", "orange"
    elif setup_level is None:
        entry_level, pos_size = "Avoid", "No Trade: no confirmed entry setup"
    elif resistance_too_close:
        entry_level, pos_size = "Avoid", "No Trade: targets/RR do not meet minimums"
    elif risk_per_share > 0 and setup_score >= 10 and s8 and s9 and (pullback_setup or breakout_confirmed or retest_setup):
        entry_level, pos_size, color = "Buy", "Qualified setup; size to account risk", "green"
    elif structure_improving and setup_score >= 6:
        entry_level, pos_size, color = "Wait", "Wait for confirmation or better entry", "orange"

    return {
        "curr_price": curr_price, "price_change_pct": price_change_pct,
        "ema_short_val": ema_short_val, "ema_long_val": ema_long_val,
        "ema_20_val": ema_20_val, "ema_50_val": ema_50_val, "ema_100_val": ema_100_val, "ema_200_val": ema_200_val,
        "atr_val": atr_val, "rsi_val": rsi_val, "res_val": res_val, "sup_val": sup_val,
        "trend": trend, "trend_detail": trend_detail, "sentiment": sentiment, "sentiment_detail": sentiment_detail,
        "dd_20d": finite_float(row['Drawdown_20d']), "du_20d": finite_float(row['Drawup_20d']),
        "avg_dd": finite_float(row['Avg_Drawdown']), "avg_du": finite_float(row['Avg_Drawup']),
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
        "s8": s8, "s9": s9, "rs_market_50": rs_market_50, "rs_sector_50": rs_sector_50,
        "wide_candle": wide_candle,
        "structure_improving": structure_improving, "support_holds": support_holds,
        "breakout_confirmed": breakout_confirmed, "pullback_setup": pullback_setup,
        "retest_setup": retest_setup, "extended": extended,
        "setup_type": setup_type, "setup_level": setup_level,
        "price_away_from_entry": price_away_from_entry,
        "macd_val": macd_val, "signal_val": signal_val,
        "suggested_entry": suggested_entry, "stop_loss": stop_loss, "target_resistance": target_resistance,
        "tp1": tp1, "tp2": tp2, "rr_tp1": rr_tp1, "rr_tp2": rr_tp2,
        "tp2_measured_move": measured_move,
        "risk_per_share": risk_per_share, "reward_per_share": reward_per_share,
        "reward_risk": rr_tp1,
    }


def summarize_backtest(data):
    rows = []
    if len(data) < 280:
        return {"entry_count": 0, "message": "Need at least 280 daily bars for a meaningful 20-day signal backtest."}
    for idx in range(252, len(data) - 20):
        signal = evaluate_strategy_row(data, idx)
        if signal['entry_level'] != "Buy":
            continue
        entry_price = signal['suggested_entry']
        stop_price = signal['stop_loss']
        if not entry_price or stop_price >= entry_price:
            continue
        entry_window = data.iloc[idx + 1:idx + 21]
        fills = entry_window[(entry_window['Low'] <= entry_price) & (entry_window['High'] >= entry_price)]
        if fills.empty:
            continue
        fill_pos = data.index.get_loc(fills.index[0])
        holding_window = data.iloc[fill_pos + 1:fill_pos + 21]
        if len(holding_window) < 20:
            continue
        ret_5d = (finite_float(data['Close'].iloc[fill_pos + 5], entry_price) - entry_price) / entry_price * 100
        ret_20d = (finite_float(data['Close'].iloc[fill_pos + 20], entry_price) - entry_price) / entry_price * 100
        future_low = finite_float(holding_window['Low'].min(), entry_price)
        future_high = finite_float(holding_window['High'].max(), entry_price)
        rows.append({
            "level": signal['setup_type'],
            "ret_5d": ret_5d,
            "ret_20d": ret_20d,
            "max_adverse": (future_low - entry_price) / entry_price * 100,
            "stop_hit": future_low <= stop_price,
            "tp1_hit": signal['tp1'] is not None and future_high >= signal['tp1'],
            "tp2_hit": signal['tp2'] is not None and future_high >= signal['tp2'],
        })
    if not rows:
        return {"entry_count": 0, "message": "No historical setups filled at the planned entry under the current rules."}
    bt = pd.DataFrame(rows)
    return {
        "entry_count": int(len(bt)),
        "win_rate_20d": float((bt['ret_20d'] > 0).mean() * 100),
        "avg_return_5d": float(bt['ret_5d'].mean()),
        "avg_return_20d": float(bt['ret_20d'].mean()),
        "worst_adverse_20d": float(bt['max_adverse'].min()),
        "stop_hit_rate_20d": float(bt['stop_hit'].mean() * 100),
        "tp1_hit_rate_20d": float(bt['tp1_hit'].mean() * 100),
        "tp2_hit_rate_20d": float(bt['tp2_hit'].mean() * 100),
        "by_level": bt.groupby('level')['ret_20d'].agg(['count', 'mean']).reset_index(),
    }
