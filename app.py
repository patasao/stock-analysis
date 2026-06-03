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
        st.error(f"Error fetching data: {e}")
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


if symbol:
    with st.spinner(f"Loading data for {symbol}..."):
        data = fetch_stock_data(symbol, period, interval)
    
    if data is not None:
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
        
        # Tabs
        tab1, tab2 = st.tabs(["📊 Overview", "🔍 Technicals"])
        
        with tab1:
            # Metrics Row
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Price", f"${curr_price:,.2f}", f"{price_change_pct:+.2f}%")
            col2.metric(f"EMA {ema_short}", f"${ema_short_val:,.2f}")
            col3.metric("20D Support", f"${sup_val:,.2f}")
            col4.metric("20D Resistance", f"${res_val:,.2f}")
            
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
            
        with tab2:
            st.subheader("Advanced Technical Indicators")
            
            # KPI Cards for Technicals
            t_col1, t_col2, t_col3 = st.columns(3)
            
            # RSI KPI
            rsi_val = float(data['RSI'].iloc[-1])
            rsi_status = "Overbought ⚠️" if rsi_val > 70 else "Oversold ⚠️" if rsi_val < 30 else "Neutral"
            t_col1.metric("RSI (14)", f"{rsi_val:.2f}", rsi_status)
            
            # Trend KPI
            ema_20 = float(data['EMA_1'].iloc[-1])
            ema_long_val = float(data['EMA_2'].iloc[-1])
            trend = "Uptrend 📈" if ema_20 > ema_long_val else "Downtrend 📉"
            trend_delta = "Bullish Alignment" if curr_price > ema_20 > ema_long_val else "Bearish Alignment" if curr_price < ema_20 < ema_long_val else "Neutral/Mixed"
            t_col2.metric("Trend (EMA)", trend, trend_delta)
            
            # Bullish/Bearish KPI
            macd_val = float(data['MACD'].iloc[-1])
            signal_val = float(data['Signal_Line'].iloc[-1])
            is_bullish = macd_val > signal_val and rsi_val > 50
            sentiment = "Bullish 🐂" if is_bullish else "Bearish 🐻"
            sentiment_detail = "MACD & RSI Positive" if is_bullish else "Momentum/RSI Weak"
            t_col3.metric("Sentiment", sentiment, sentiment_detail)

            # EMA Targets row
            e_col1, e_col2, e_col3 = st.columns(3)
            e_col1.metric("EMA 20", f"${ema_short_val:,.2f}", help="Short-term momentum support")
            e_col2.metric("EMA 50", f"${ema_long_val:,.2f}", help="Medium-term institutional support")
            e_col3.metric("EMA 100", f"${ema_100_val:,.2f}", help="Long-term value support")

            # 20-Day Drawdown/Drawup metrics
            d_col1, d_col2, d_col3, d_col4 = st.columns(4)
            dd_20d = float(data['Drawdown_20d'].iloc[-1])
            du_20d = float(data['Drawup_20d'].iloc[-1])
            avg_dd = float(data['Avg_Drawdown'].iloc[-1])
            avg_du = float(data['Avg_Drawup'].iloc[-1])
            
            d_col1.metric("20D Drawdown", f"{dd_20d:.2f}%", help="Current decline from 20-day high")
            d_col2.metric("20D Drawup", f"{du_20d:.2f}%", help="Current rise from 20-day low")
            d_col3.metric("Avg Intraday DD", f"{avg_dd:.2f}%", help="20-day average of (Low - Open) / Open")
            d_col4.metric("Avg Intraday DU", f"{avg_du:.2f}%", help="20-day average of (High - Open) / Open")

            # Entry Targets Row
            t_col1, t_col2 = st.columns(2)
            limit_buy_1 = open_price * (1 + (avg_dd / 100))
            t_col1.metric("Limit Buy I", f"${limit_buy_1:,.2f}", help="Today's Open * (1 + Avg Intraday DD%)")
            t_col2.metric("Limit Buy II", f"${limit_buy_1 * 0.97:,.2f}", help="Limit Buy I * 0.97 (3% Safety Buffer)")

            st.write("---")
            buy_col, sell_col = st.columns(2)
            
            with buy_col:
                st.subheader("🎯 Buying Score (Entry Rules)")
                
                with st.expander("ℹ️ How the Scoring System Works"):
                    st.markdown("""
                    **The Goal:** This system combines 12 technical filters to find "high-probability" setups where momentum meets value.
                    
                    **1. Core Conditions (The Foundation):**
                    - **Drawdown:** We look for a >= 8% pullback from recent highs to avoid "buying the top."
                    - **EMA20 Alignment:** Price should be within ±6% of the EMA20. If it's too far above, it's overextended.
                    - **RSI (42-58):** This "sweet spot" ensures the stock has momentum but isn't overbought.
                    - **Volume Ratio (>= 1.6x):** High volume confirms that "big money" (institutions) is entering the position.
                    
                    **2. Supporting Conditions (The Conviction):**
                    - These indicators (EMA50/100, ADX, Bollinger Bands) measure the strength of the underlying trend. The more conditions met, the higher the "Relative Strength."
                    
                    **3. Risk Overrides (The Safety):**
                    - If the **RSI is > 68** or the price is **> 8% above the EMA20**, the system will automatically signal **Avoid**, regardless of other scores. This prevents FOMO (Fear Of Missing Out) buying.
                    """)

                with st.expander("ℹ️ Understanding Entry Price Targets (EMAs)"):
                    st.markdown("""
                    **Why use EMAs as Buy Targets?**
                    Institutions and algorithms often use Moving Averages as support levels to build large positions.
                    
                    - **EMA 20 (Fast):** The "Momentum Line." Best for aggressive traders looking for quick bounces in strong uptrends.
                    - **EMA 50 (Medium):** The "Institutional Line." This is where major funds often defend their positions. It's the most common "buy the dip" level.
                    - **EMA 100 (Slow):** The "Value Line." Provides a high margin of safety. Buying here often represents a significant correction within a long-term bull market.
                    """)
                
                # Scoring System Logic
                # Core Conditions
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
                
                core_conditions = [c1, c2, c3, c4, c5]
                core_score = sum(core_conditions)
                
                # Supporting Conditions
                s1 = curr_price > ema_long_val # EMA50
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
                
                supporting_conditions = [s1, s2, s3, s4, s5, s6, s7]
                supp_score = sum(supporting_conditions)
                
                # Risk Rules
                risk_fail_rsi = rsi_val > 68
                risk_fail_ema20 = ema20_dist > 0.08
                
                # Entry Strength
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

                # Display Scoring
                st.markdown(f"""
                <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: black;">
                    <h1 style="margin: 0;">{entry_level}</h1>
                    <p style="margin: 0; font-weight: bold;">{pos_size}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("") # Add some spacing
                st.write(f"**Core Conditions:** {core_score}/5")
                st.write(f"**Supporting Conditions:** {supp_score}/7")
                if risk_fail_rsi: st.error("⚠️ Risk: RSI too high (> 68)")
                if risk_fail_ema20: st.error("⚠️ Risk: Too far above EMA20 (> 8%)")

                # Details Expander
                with st.expander("🔍 View Checklist Details"):
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        st.write("**Core Conditions**")
                        st.write(f"{'✅' if c1 else '❌'} Drawdown >= 8% ({drawdown_10d:.1%})")
                        st.write(f"{'✅' if c2 else '❌'} Within ±6% EMA20 ({ema20_dist:.1%})")
                        st.write(f"{'✅' if c3 else '❌'} RSI 42-58 ({rsi_val:.1f})")
                        st.write(f"{'✅' if c4 else '❌'} Vol Ratio >= 1.6x ({vol_ratio:.1f}x)")
                        st.write(f"{'✅' if c5 else '❌'} MACD > Signal")
                    
                    with c_col2:
                        st.write("**Supporting Conditions**")
                        st.write(f"{'✅' if s1 else '❌'} Above EMA50")
                        st.write(f"{'✅' if s2 else '❌'} MACD > Signal")
                        st.write(f"{'✅' if s3 else '❌'} 78%-94% of 52W High")
                        st.write(f"{'✅' if s4 else '❌'} Above EMA100")
                        st.write(f"{'✅' if s5 else '❌'} ADX > 20 ({adx_val:.1f})")
                        st.write(f"{'✅' if s6 else '❌'} Above BB Middle")
                        st.write(f"{'✅' if s7 else '❌'} Stoch RSI < 75 ({stoch_rsi:.1f})")

            with sell_col:
                st.subheader("🚩 Selling Score (Exit Rules)")
                
                with st.expander("ℹ️ How the Exit Strategy Works"):
                    st.markdown("""
                    **The Goal:** To protect capital and lock in gains using a systematic approach rather than emotional decision-making.
                    
                    **1. Protective Exits (Defense):**
                    - **Hard Stop (-8% to -10%):** The absolute maximum loss allowed. 
                    - **Trailing Stop (EMA 20):** If the price closes below the EMA 20, the short-term trend has likely broken.
                    
                    **2. Offensive Exits (Profit Taking):**
                    - **Resistance/Targets:** Selling near the 20D Resistance or at +15-20% gains.
                    - **Bollinger Band Extension:** Selling when price is outside the Upper BB (overextended).
                    
                    **3. Momentum Exits (Trend Change):**
                    - **MACD Bearish Cross:** When the blue line crosses below the orange line.
                    - **RSI Reversal:** When RSI drops back below 70 after being overbought.
                    """)

                # Exit Logic
                # 1. Trailing Stop
                ex1 = curr_price < ema_short_val
                # 2. MACD Cross
                ex2 = macd_val < signal_val
                # 3. RSI Overbought Reversal
                ex3 = rsi_val > 70
                # 4. Bollinger Band Exit
                bb_upper = data['BB_Upper'].iloc[-1]
                ex4 = curr_price >= bb_upper
                # 5. Resistance Exit
                ex5 = curr_price >= (res_val * 0.98) # Within 2% of resistance

                exit_score = sum([ex1, ex2, ex3, ex4, ex5])
                
                exit_level = "Hold"
                exit_color = "gray"
                exit_action = "Maintain Position"
                
                if exit_score >= 3 or ex1: # EMA 20 break is a strong signal
                    exit_level = "SELL / REDUCE"
                    exit_color = "red"
                    exit_action = "Exit or Trim 50-100%"
                elif exit_score >= 1:
                    exit_level = "CAUTION"
                    exit_color = "orange"
                    exit_action = "Tighten Stop Loss"
                
                # Display Exit Scoring
                st.markdown(f"""
                <div style="background-color: {exit_color}; padding: 20px; border-radius: 10px; text-align: center; color: white;">
                    <h2 style="margin: 0;">{exit_level}</h2>
                    <p style="margin: 0; font-weight: bold;">{exit_action}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("") # Add some spacing
                st.write(f"**Exit Signals Triggered:** {exit_score}/5")
                st.write(f"{'🔴' if ex1 else '⚪'} Price below EMA 20 (Trend Break)")
                st.write(f"{'🔴' if ex2 else '⚪'} MACD Bearish Crossover")
                st.write(f"{'🔴' if ex3 else '⚪'} RSI Overbought (>70)")
                st.write(f"{'🔴' if ex4 else '⚪'} Price at Upper Bollinger Band")
                st.write(f"{'🔴' if ex5 else '⚪'} Price near 20D Resistance")

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

            st.info("""
            **Pro Tip:** Use the legend to toggle specific lines off if the chart feels too busy. Double-click an item in the legend to isolate it.
            """)


    else:
        st.error(f"Ticker '{symbol}' not found or data unavailable.")

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
