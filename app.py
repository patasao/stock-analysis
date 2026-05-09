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
        # --- Helper Function for Robust Extraction ---
        def get_val(series, index=-1):
            """Safely extracts a numeric value from a Series or MultiIndex column."""
            try:
                row = series.iloc[index]
                if hasattr(row, 'values'):
                    return float(row.values.flatten()[0])
                return float(row)
            except:
                return 0.0

        # --- Technical Analysis Calculations (Original) ---
        data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
        data['EMA_50'] = data['Close'].ewm(span=50, adjust=False).mean()
        high_low = data['High'] - data['Low']
        atrs = high_low.rolling(14).mean()

        # Value Extraction
        current_price_val = get_val(data['Close'], -1)
        ema_20_val = get_val(data['EMA_20'], -1)
        ema_50_val = get_val(data['EMA_50'], -1)
        latest_atr_val = get_val(atrs, -1)
        resistance_val = get_val(data['High'].rolling(window=20).max(), -1)
        support_val = get_val(data['Low'].rolling(window=20).min(), -1)

        # Original Limit Buys
        limit_i = ema_20_val
        limit_ii = ema_20_val - (0.5 * latest_atr_val)
        limit_iii = ema_20_val - (1.0 * latest_atr_val)

        # --- PS's Analysis Calculations ---
        today_low = get_val(data['Low'], -1)
        yest_low = get_val(data['Low'], -2)
        yest_open = get_val(data['Open'], -2)
        yest_close = get_val(data['Close'], -2)

        r_limit_i = (current_price_val + today_low) / 2
        v_factor = 1 - (abs(yest_low - yest_open) / yest_open) if yest_open != 0 else 1
        r_limit_ii = v_factor * yest_close
        r_limit_iii = yest_close * 0.95

        # --- 2. UI Display: General Metrics Row ---
        st.write("---")
        st.subheader("General Technical Indicators")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"${current_price_val:,.2f}")
        col2.metric("Limit Buy I (EMA 20)", f"${limit_i:,.2f}")
        col3.metric("Limit Buy II (ATR)", f"${limit_ii:,.2f}")
        col4.metric("Limit Buy III (ATR)", f"${limit_iii:,.2f}")

        # --- 3. Main OHLC Chart ---
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
        fig_ohlc.update_layout(title=f"{symbol} Price Action", xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
        st.plotly_chart(fig_ohlc, width="stretch")

        # --- 4. Market Structure & Trend Analysis (KPI Cards) ---
        trend_status = "Bullish 🟢" if current_price_val > ema_50_val else "Bearish 🔴"
        st.subheader("Trend & Structure Analysis")
        m_col1, m_col2, m_col3 = st.columns(3)       
        # Trend KPI
        m_col1.metric("Current Trend", trend_status)        
        # Resistance KPI (Red delta to signify a "ceiling")
        m_col2.metric("20D Resistance", f"${resistance_val:,.2f}")        
        # Support KPI (Green delta to signify a "floor")
        m_col3.metric("20D Support", f"${support_val:,.2f}")

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=data.index, y=flatten_col(data['Close']), name='Price'))
        fig_trend.add_trace(go.Scatter(x=data.index, y=flatten_col(data['EMA_50']), name='EMA 50', line=dict(dash='dot')))
        fig_trend.add_hline(y=resistance_val, line_dash="dash", line_color="red")
        fig_trend.add_hline(y=support_val, line_dash="dash", line_color="green")
        fig_trend.update_layout(title="Trendline & Support/Resistance", template="plotly_dark", height=400)
        st.plotly_chart(fig_trend, width="stretch")

        # --- 5. PS's Analysis (NOW AT BOTTOM) ---
        st.write("---")
        with st.expander("⭐ PS's Analysis", expanded=True):
            st.warning("Notice: For educational purposes only. This is a personal strategy, not an investment recommendation. Always consider market risks and your own financial situation before trading.")
            
            p_col1, p_col2, p_col3 = st.columns(3)
            avg_cost = p_col1.number_input("Your Average Cost ($)", value=0.0, step=0.01)
            num_shares = p_col2.number_input("Shares Currently Owned", value=0.0, step=0.0001)
            buy_amt = p_col3.number_input("Planned Buy (Shares)", value=0.0, step=0.0001)

            def calc_new_avg(old_avg, old_qty, buy_price, buy_qty):
                if old_qty + buy_qty == 0: return 0
                return ((old_avg * old_qty) + (buy_price * buy_qty)) / (old_qty + buy_qty)

            l_col1, l_col2, l_col3 = st.columns(3)
            
            # Limit I
            new_avg_i = calc_new_avg(avg_cost, num_shares, r_limit_i, buy_amt)
            l_col1.metric("Rainey Limit I", f"${r_limit_i:,.2f}")
            l_col1.caption(f"New Avg: **${new_avg_i:,.2f}**")

            # Limit II
            new_avg_ii = calc_new_avg(avg_cost, num_shares, r_limit_ii, buy_amt)
            l_col2.metric("Rainey Limit II", f"${r_limit_ii:,.2f}")
            l_col2.caption(f"New Avg: **${new_avg_ii:,.2f}**")

            # Limit III
            new_avg_iii = calc_new_avg(avg_cost, num_shares, r_limit_iii, buy_amt)
            l_col3.metric("Rainey Limit III", f"${r_limit_iii:,.2f}")
            l_col3.caption(f"New Avg: **${new_avg_iii:,.2f}**")

    else:
        st.error("Ticker not found. Please try a valid symbol.")

# --- Footer ---
st.write("---")
st.markdown(
    """
    <div style="text-align: center; color: #888888; font-size: 0.8em;">
        Developed with the assistance of <strong>Gemini</strong> (Google AI).
    </div>
    """,
    unsafe_allow_html=True
)