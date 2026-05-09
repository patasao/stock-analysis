import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- Configuration & Styling ---
st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide")
st.title("📈 Stock Insight Dashboard")

# 1. Input Box
symbol = st.sidebar.text_input("Enter Stock Symbol (e.g., AAPL, MSFT, TSLA)", value="AAPL").upper()

if symbol:
    # --- Data Fetching ---
    # Fetching 1 year of daily data
    data = yf.download(symbol, period="1y", interval="1d")
    
    if not data.empty:
        # --- 2. Technical Analysis Calculations ---
        # Calculate EMA 20 and EMA 50
        data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
        data['EMA_50'] = data['Close'].ewm(span=50, adjust=False).mean()
        
        # Calculate ATR (Average True Range) for volatility-based limits
        high_low = data['High'] - data['Low']
        atrs = high_low.rolling(14).mean()
        
        # --- Value Extractions (Forcing Float conversion to avoid Series errors) ---
        current_price_val = float(data['Close'].iloc[-1])
        ema_20_val = float(data['EMA_20'].iloc[-1])
        ema_50_val = float(data['EMA_50'].iloc[-1])
        latest_atr_val = float(atrs.iloc[-1])
        
        # Prediction Metrics (Limit Buy levels)
        limit_i = ema_20_val
        limit_ii = ema_20_val - (0.5 * latest_atr_val)
        limit_iii = ema_20_val - (1.0 * latest_atr_val)

        # Resistance and Support (20-day Highs/Lows)
        resistance_val = float(data['High'].rolling(window=20).max().iloc[-1])
        support_val = float(data['Low'].rolling(window=20).min().iloc[-1])

        # --- 3. UI Display: Metrics Table ---
        st.subheader(f"Market Data: {symbol}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"${current_price_val:,.2f}")
        col2.metric("Limit Buy I (EMA 20)", f"${limit_i:,.2f}")
        col3.metric("Limit Buy II (Soft Support)", f"${limit_ii:,.2f}")
        col4.metric("Limit Buy III (Strong Support)", f"${limit_iii:,.2f}")

        # --- 4. Main OHLC Chart ---
        fig_ohlc = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="OHLC"
        )])
        fig_ohlc.update_layout(
            title=f"{symbol} Candlestick Chart",
            xaxis_rangeslider_visible=False,
            template="plotly_dark"
        )
        st.plotly_chart(fig_ohlc, width="stretch")

        # --- 5. Market Structure (Trend & Support/Resistance) ---
        trend = "Bullish 🟢" if current_price_val > ema_50_val else "Bearish 🔴"

        st.write("---")
        st.subheader("Market Structure & Trend")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.write(f"**Current Trend (vs EMA 50):** {trend}")
        m_col2.write(f"**20D Resistance:** ${resistance_val:,.2f}")
        m_col3.write(f"**20D Support:** ${support_val:,.2f}")

        # Trend & S/R Visual Chart
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Price', line=dict(color='royalblue')))
        fig_trend.add_trace(go.Scatter(x=data.index, y=data['EMA_50'], name='EMA 50 (Trend)', line=dict(color='orange', dash='dot')))
        
        # Horizontal lines for S/R
        fig_trend.add_hline(y=resistance_val, line_dash="dash", line_color="red", annotation_text="Resistance")
        fig_trend.add_hline(y=support_val, line_dash="dash", line_color="green", annotation_text="Support")
        
        fig_trend.update_layout(title="Trendline & S/R Analysis", template="plotly_dark")
        st.plotly_chart(fig_trend, width="stretch")

        # --- 6. Analysis Logic Table (Data Breakdown) ---
        with st.expander("View Calculation Details"):
            st.write("""
            - **Limit Buy I:** Set at the 20-day Exponential Moving Average (EMA).
            - **Limit Buy II/III:** Calculated using Average True Range (ATR) to adjust for current market volatility.
            - **Trend:** Determined by whether the price is above (Bullish) or below (Bearish) the 50-day EMA.
            """)

    else:
        st.error("Invalid Symbol or No Data Found. Please check the ticker and try again.")