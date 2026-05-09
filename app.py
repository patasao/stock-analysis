import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- Configuration & Styling ---
st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide")

# Title
st.title("📈 Stock Insight Dashboard")

# 1. Input Box (Main Page)
symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, NVDA, BTC-USD)", value="AAPL").upper()

if symbol:
    # --- Data Fetching ---
    data = yf.download(symbol, period="1y", interval="1d")
    
    if not data.empty:
        # --- 2. Technical Analysis Calculations ---
        data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
        data['EMA_50'] = data['Close'].ewm(span=50, adjust=False).mean()
        
        # Calculate ATR for volatility
        high_low = data['High'] - data['Low']
        atrs = high_low.rolling(14).mean()
        
        # --- Helper Function for Robust Extraction ---
        def get_last_val(series):
            """Safely extracts the last numeric value from a Series or MultiIndex DataFrame column."""
            last_row = series.iloc[-1]
            if hasattr(last_row, 'values'):
                return float(last_row.values.flatten()[0])
            return float(last_row)

        # --- Extraction using Helper ---
        current_price_val = get_last_val(data['Close'])
        ema_20_val = get_last_val(data['EMA_20'])
        ema_50_val = get_last_val(data['EMA_50'])
        latest_atr_val = get_last_val(atrs)
        
        # Prediction Metrics
        limit_i = ema_20_val
        limit_ii = ema_20_val - (0.5 * latest_atr_val)
        limit_iii = ema_20_val - (1.0 * latest_atr_val)

        # Resistance and Support (20-day Highs/Lows)
        resistance_val = get_last_val(data['High'].rolling(window=20).max())
        support_val = get_last_val(data['Low'].rolling(window=20).min())

        # --- 3. UI Display: Metrics Row ---
        st.write("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"${current_price_val:,.2f}")
        col2.metric("Limit Buy I (EMA 20)", f"${limit_i:,.2f}")
        col3.metric("Limit Buy II", f"${limit_ii:,.2f}")
        col4.metric("Limit Buy III", f"${limit_iii:,.2f}")

        # --- 4. Main OHLC Chart ---
        # Note: chart data usually needs flattening if multi-indexed
        def flatten_col(col):
            return col.values.flatten() if hasattr(col, 'values') else col

        fig_ohlc = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=flatten_col(data['Open']),
            high=flatten_col(data['High']),
            low=flatten_col(data['Low']),
            close=flatten_col(data['Close']),
            name="OHLC"
        )])
        fig_ohlc.update_layout(
            title=f"{symbol} Price Action",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=600
        )
        st.plotly_chart(fig_ohlc, width="stretch")

        # --- 5. Market Structure & Trend Chart ---
        trend_status = "Bullish 🟢" if current_price_val > ema_50_val else "Bearish 🔴"

        st.subheader("Trend & Structure Analysis")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.info(f"**Current Trend:** {trend_status}")
        m_col2.error(f"**Resistance:** ${resistance_val:,.2f}")
        m_col3.success(f"**Support:** ${support_val:,.2f}")

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=data.index, y=flatten_col(data['Close']), name='Price', line=dict(color='royalblue')))
        fig_trend.add_trace(go.Scatter(x=data.index, y=flatten_col(data['EMA_50']), name='EMA 50 (Trend)', line=dict(color='orange', dash='dot')))
        
        # Horizontal lines for S/R
        fig_trend.add_hline(y=resistance_val, line_dash="dash", line_color="red", annotation_text="Resistance")
        fig_trend.add_hline(y=support_val, line_dash="dash", line_color="green", annotation_text="Support")
        
        fig_trend.update_layout(title="Trendline & Support/Resistance", template="plotly_dark")
        st.plotly_chart(fig_trend, width="stretch")

        # --- 6. Methodology ---
        with st.expander("Methodology"):
            st.write(f"""
            - **EMA 20:** Short-term momentum anchor used for **Limit Buy I**.
            - **ATR:** Volatility subtraction from the EMA 20 for **Limit II & III**.
            - **EMA 50:** Long-term trend filter.
            """)

    else:
        st.error("Ticker not found. Please try a valid symbol like 'AAPL' or 'NVDA'.")