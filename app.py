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
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    
    # Support/Resistance (20-day)
    df['Resistance'] = df['High'].rolling(window=20).max()
    df['Support'] = df['Low'].rolling(window=20).min()
    
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
        prev_close = float(data['Close'].iloc[-2])
        price_change = curr_price - prev_close
        price_change_pct = (price_change / prev_close) * 100
        
        ema_short_val = float(data['EMA_1'].iloc[-1])
        ema_long_val = float(data['EMA_2'].iloc[-1])
        atr_val = float(data['ATR'].iloc[-1])
        rsi_val = float(data['RSI'].iloc[-1])
        res_val = float(data['Resistance'].iloc[-1])
        sup_val = float(data['Support'].iloc[-1])
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔍 Technicals", "⭐ PS's Analysis"])
        
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
            
            # RSI Chart
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='magenta', width=1.5), name="RSI"))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
            fig_rsi.update_layout(title="RSI (14)", template="plotly_dark", height=250, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_rsi, use_container_width=True)
            
            # MACD Chart
            fig_macd = make_subplots(rows=1, cols=1)
            fig_macd.add_trace(go.Scatter(x=data.index, y=data['MACD'], line=dict(color='cyan', width=1), name="MACD"))
            fig_macd.add_trace(go.Scatter(x=data.index, y=data['Signal_Line'], line=dict(color='orange', width=1), name="Signal"))
            colors = ['green' if x >= 0 else 'red' for x in data['MACD_Hist']]
            fig_macd.add_trace(go.Bar(x=data.index, y=data['MACD_Hist'], marker_color=colors, name="Histogram"))
            fig_macd.update_layout(title="MACD", template="plotly_dark", height=250, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_macd, use_container_width=True)

        with tab3:
            st.subheader("PS's Custom Analysis")
            st.warning("⚠️ **Notice:** This analysis is for **educational purposes only**. This is a personal strategy simulator, not financial advice or an investment recommendation. Always conduct your own research and consider market risks before trading.")
            st.info("Strategy-based entry limits and cost-averaging simulator.")
            
            # PS Strategy Logic
            today_open = float(data['Open'].iloc[-1])
            yest_low = float(data['Low'].iloc[-2])
            yest_open = float(data['Open'].iloc[-2])

            # PS Limit Buy I = (today's open + % change from yest's open to yest's lowest)
            pct_change_yest = (yest_low - yest_open) / yest_open if yest_open != 0 else 0
            r_limit_i = today_open * (1 + pct_change_yest)
            
            # PS Limit Buy II = Limit buy I - 3%
            r_limit_ii = r_limit_i * 0.97
            
            # ATR/EMA Limits
            limit_i = ema_short_val
            limit_ii = ema_short_val - (0.5 * atr_val)
            limit_iii = ema_short_val - (1.0 * atr_val)

            # Simulator Inputs
            p_col1, p_col2, p_col3 = st.columns(3)
            avg_cost = p_col1.number_input("Your Average Cost ($)", value=0.0, step=0.1, format="%.2f")
            num_shares = p_col2.number_input("Shares Owned", value=0.0, step=1.0)
            buy_amt = p_col3.number_input("Planned Buy (Shares)", value=0.0, step=1.0)

            def calc_new_avg(old_avg, old_qty, buy_price, buy_qty):
                if old_qty + buy_qty == 0: return 0
                return ((old_avg * old_qty) + (buy_price * buy_qty)) / (old_qty + buy_qty)

            def get_avg_display(new_avg, old_avg):
                if old_avg == 0:
                    return f"New Avg: **${new_avg:,.2f}**"
                if new_avg < old_avg:
                    return f"New Avg: **${new_avg:,.2f}** 🟢 ↓"
                elif new_avg > old_avg:
                    return f"New Avg: **${new_avg:,.2f}** 🔴 ↑"
                else:
                    return f"New Avg: **${new_avg:,.2f}**"

            st.write("### Entry Targets")
            l_col1, l_col2 = st.columns(2)
            
            with l_col1:
                st.metric("PS Limit I", f"${r_limit_i:,.2f}", help="Today's Open + % change from Yesterday's Open to Yesterday's Low")
                new_avg = calc_new_avg(avg_cost, num_shares, r_limit_i, buy_amt)
                st.caption(get_avg_display(new_avg, avg_cost))
            
            with l_col2:
                st.metric("PS Limit II", f"${r_limit_ii:,.2f}", help="PS Limit I - 3%")
                new_avg = calc_new_avg(avg_cost, num_shares, r_limit_ii, buy_amt)
                st.caption(get_avg_display(new_avg, avg_cost))

            st.write("---")
            st.write("### ATR/EMA Entry Targets")
            a_col1, a_col2, a_col3 = st.columns(3)
            
            with a_col1:
                st.metric("EMA 20 Limit", f"${limit_i:,.2f}", help="Current Short EMA (20-day) value")
                new_avg = calc_new_avg(avg_cost, num_shares, limit_i, buy_amt)
                st.caption(get_avg_display(new_avg, avg_cost))
                
            with a_col2:
                st.metric("ATR Limit II", f"${limit_ii:,.2f}", help="EMA 20 - (0.5 * ATR)")
                new_avg = calc_new_avg(avg_cost, num_shares, limit_ii, buy_amt)
                st.caption(get_avg_display(new_avg, avg_cost))
                
            with a_col3:
                st.metric("ATR Limit III", f"${limit_iii:,.2f}", help="EMA 20 - (1.0 * ATR)")
                new_avg = calc_new_avg(avg_cost, num_shares, limit_iii, buy_amt)
                st.caption(get_avg_display(new_avg, avg_cost))

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
