import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

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
    
    # ATR (14-period)
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    # RSI (14-period)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
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
    
    # ADX (14-period)
    plus_dm = df['High'].diff()
    minus_dm = df['Low'].diff()
    plus_dm = plus_dm.where(plus_dm > 0, 0)
    minus_dm = minus_dm.where(minus_dm < 0, 0).abs()
    
    tr = true_range.rolling(14).mean() # Simplified smooth TR
    plus_di = 100 * (plus_dm.rolling(14).mean() / tr)
    minus_di = 100 * (minus_dm.rolling(14).mean() / tr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    df['ADX'] = dx.rolling(14).mean()
    
    # 52-Week High
    df['High_52w'] = df['High'].rolling(window=252, min_periods=1).max()
    
    # 10-Day High (for Drawdown)
    df['High_10d'] = df['High'].rolling(window=10, min_periods=1).max()
    
    # Intraday Drawdown/Drawup (20-day average)
    df['Intraday_Drawdown_Pct'] = ((df['Low'] - df['Open']) / df['Open']) * 100
    df['Intraday_Drawup_Pct'] = ((df['High'] - df['Open']) / df['Open']) * 100
    df['Avg_Drawdown'] = df['Intraday_Drawdown_Pct'].rolling(window=20).mean()
    df['Avg_Drawup'] = df['Intraday_Drawup_Pct'].rolling(window=20).mean()
    
    return df

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

tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔍 Technicals", "📋 Multi-Stock Analysis"])

with tab1:
    if symbol:
        with st.spinner(f"Loading data for {symbol}..."):
            analysis = get_analysis(symbol, period, interval, ema_short, ema_long)
        
        if analysis:
            data = analysis['df']
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
            t_col1.metric("RSI (14)", f"{analysis['rsi_val']:.2f}", rsi_status)
            
            # Trend KPI
            t_col2.metric("Trend (EMA)", analysis['trend'], analysis['trend_detail'])
            
            # Bullish/Bearish KPI
            t_col3.metric("Sentiment", analysis['sentiment'], analysis['sentiment_detail'])

            # EMA Targets row
            e_col1, e_col2, e_col3 = st.columns(3)
            e_col1.metric("EMA 20", f"${analysis['ema_short_val']:,.2f}", help="Short-term momentum support")
            e_col2.metric("EMA 50", f"${analysis['ema_long_val']:,.2f}", help="Medium-term institutional support")
            e_col3.metric("EMA 100", f"${analysis['ema_100_val']:,.2f}", help="Long-term value support")

            # 20-Day Drawdown/Drawup metrics
            d_col1, d_col2, d_col3, d_col4 = st.columns(4)
            d_col1.metric("20D Drawdown", f"{analysis['dd_20d']:.2f}%", help="Current decline from 20-day high")
            d_col2.metric("20D Drawup", f"{analysis['du_20d']:.2f}%", help="Current rise from 20-day low")
            d_col3.metric("Avg Intraday DD", f"{analysis['avg_dd']:.2f}%", help="20-day average of (Low - Open) / Open")
            d_col4.metric("Avg Intraday DU", f"{analysis['avg_du']:.2f}%", help="20-day average of (High - Open) / Open")

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
                        st.write(f"{'✅' if analysis['c1'] else '❌'} Drawdown >= 8% ({analysis['drawdown_10d']:.1%})")
                        st.write(f"{'✅' if analysis['c2'] else '❌'} Within ±6% EMA20 ({analysis['ema20_dist']:.1%})")
                        st.write(f"{'✅' if analysis['c3'] else '❌'} RSI 42-58 ({analysis['rsi_val']:.1f})")
                        st.write(f"{'✅' if analysis['c4'] else '❌'} Vol Ratio >= 1.6x ({analysis['vol_ratio']:.1f}x)")
                        st.write(f"{'✅' if analysis['c5'] else '❌'} MACD > Signal")
                    
                    with c_col2:
                        st.write("**Supporting Conditions**")
                        st.write(f"{'✅' if analysis['s1'] else '❌'} Above EMA50")
                        st.write(f"{'✅' if analysis['s2'] else '❌'} MACD > Signal")
                        st.write(f"{'✅' if analysis['s3'] else '❌'} 78%-94% of 52W High")
                        st.write(f"{'✅' if analysis['s4'] else '❌'} Above EMA100")
                        st.write(f"{'✅' if analysis['s5'] else '❌'} ADX > 20 ({analysis['adx_val']:.1f})")
                        st.write(f"{'✅' if analysis['s6'] else '❌'} Above BB Middle")
                        st.write(f"{'✅' if analysis['s7'] else '❌'} Stoch RSI < 75 ({analysis['stoch_rsi']:.1f})")

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
                st.write(f"{'🔴' if analysis['ex1'] else '⚪'} Price below EMA 20 (Trend Break)")
                st.write(f"{'🔴' if analysis['ex2'] else '⚪'} MACD Bearish Crossover")
                st.write(f"{'🔴' if analysis['ex3'] else '⚪'} RSI Overbought (>70)")
                st.write(f"{'🔴' if analysis['ex4'] else '⚪'} Price at Upper Bollinger Band")
                st.write(f"{'🔴' if analysis['ex5'] else '⚪'} Price near 20D Resistance")

            st.write("---")
            st.subheader("📊 Interactive Multi-Indicator Analysis")
            
            selected_indicators = st.multiselect(
                "Select indicators to overlay or view:",
                options=["EMAs (20, 50, 100)", "Bollinger Bands", "Support/Resistance", "RSI", "MACD", "ADX"],
                default=["EMAs (20, 50, 100)", "RSI"]
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
