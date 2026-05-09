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
    data = yf.download(symbol, period="1y", interval="1d")
    
    if not data.empty:
        # Latest data for display
        latest_data = data.iloc[-1]
        current_price = latest_data['Close']
        
        # --- 2. OHLC Chart ---
        fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="OHLC"
        )])
        fig.update_layout(title=f"{symbol} Price Movement", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- 3. Analysis & Limit Buy Predictions ---
        # Logic: Using EMA (Exponential Moving Average) and ATR (Average True Range) 
        # to find pull-back entry points.
        data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
        # Simple ATR calculation for volatility-based limits
        high_low = data['High'] - data['Low']
        atrs = high_low.rolling(14).mean()
        latest_atr = atrs.iloc[-1]

        # Prediction Metrics
        # Buy I: 20-day EMA (Normal pullback)
        limit_i = data['EMA_20'].iloc[-1]
        # Buy II: 20-day EMA minus 0.5 * ATR (Deep pullback)
        limit_ii = limit_i - (0.5 * latest_atr)
        # Buy III: 20-day EMA minus 1.0 * ATR (Major correction/Support level)
        limit_iii = limit_i - (1.0 * latest_atr)

        # Force these variables to be single float values
        current_price_val = float(current_price.iloc[0] if isinstance(current_price, pd.Series) else current_price)
        limit_i_val = float(limit_i.iloc[0] if isinstance(limit_i, pd.Series) else limit_i)
        limit_ii_val = float(limit_ii.iloc[0] if isinstance(limit_ii, pd.Series) else limit_ii)
        limit_iii_val = float(limit_iii.iloc[0] if isinstance(limit_iii, pd.Series) else limit_iii)

        st.subheader("Price & Predicted Buy Levels")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"${current_price_val:,.2f}")
        col2.metric("Limit Buy I (EMA 20)", f"${limit_i_val:,.2f}")
        col3.metric("Limit Buy II (Soft Support)", f"${limit_ii_val:,.2f}")
        col4.metric("Limit Buy III (Strong Support)", f"${limit_iii_val:,.2f}")

        # --- 4. Support, Resistance & Trend ---
        # Calculation for S&R based on recent 20-day highs/lows
        resistance = data['High'].rolling(window=20).max().iloc[-1]
        support = data['Low'].rolling(window=20).min().iloc[-1]
        
        # Trend Logic: Price vs EMA 50
        ema_50 = data['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
        trend = "Bullish 🟢" if current_price > ema_50 else "Bearish 🔴"

        st.write("---")
        st.subheader("Market Structure")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.write(f"**Current Trend:** {trend}")
        m_col2.write(f"**20D Resistance:** ${resistance:,.2f}")
        m_col3.write(f"**20D Support:** ${support:,.2f}")

        # Visualization for S&R
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Price', line=dict(color='royalblue')))
        fig2.add_hline(y=resistance, line_dash="dash", line_color="red", annotation_text="Resistance")
        fig2.add_hline(y=support, line_dash="dash", line_color="green", annotation_text="Support")
        fig2.update_layout(title="Trend & Support/Resistance Levels")
        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.error("Invalid Symbol or No Data Found.")