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
    
    # Intraday Drawdown (20-day average)
    df['Intraday_Drawdown_Pct'] = (df['Low'] - df['Open']) / df['Open']
    df['Avg_Drawdown'] = df['Intraday_Drawdown_Pct'].rolling(window=20).mean()
    
    return df

# --- Recommendation Logic ---
@st.cache_data(ttl=3600)
def get_recommendations():
    # Predefined list of popular tickers
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'PYPL', 'DIS', 'ADBE', 'CRM', 'INTC', 'SBUX', 'V', 'MA', 'AVGO', 'COST', 'JPM']
    try:
        # Fetch data for all tickers (1y to cover YTD and EMAs)
        data = yf.download(tickers, period="1y", interval="1d", group_by='ticker')
        recommendations = []
        
        # Calculate dates for MTD and YTD
        today = datetime.now()
        first_day_month = today.replace(day=1)
        first_day_year = today.replace(month=1, day=1)

        for ticker in tickers:
            try:
                if ticker not in data.columns.levels[0]: continue
                ticker_data = data[ticker].dropna()
                if len(ticker_data) < 50: continue # Need at least 50 days for EMA 50
                
                # Latest Close
                end_price = float(ticker_data['Close'].iloc[-1])
                
                # 5-day performance
                start_price_5d = float(ticker_data['Close'].iloc[-5]) if len(ticker_data) >= 5 else float(ticker_data['Close'].iloc[0])
                perf_5d = ((end_price - start_price_5d) / start_price_5d) * 100
                
                # MTD performance
                mtd_data = ticker_data[ticker_data.index >= first_day_month.strftime('%Y-%m-%d')]
                if not mtd_data.empty:
                    start_price_mtd = float(mtd_data['Close'].iloc[0])
                    perf_mtd = ((end_price - start_price_mtd) / start_price_mtd) * 100
                else:
                    perf_mtd = 0.0

                # YTD performance
                ytd_data = ticker_data[ticker_data.index >= first_day_year.strftime('%Y-%m-%d')]
                if not ytd_data.empty:
                    start_price_ytd = float(ytd_data['Close'].iloc[0])
                    perf_ytd = ((end_price - start_price_ytd) / start_price_ytd) * 100
                else:
                    perf_ytd = 0.0
                
                # EMAs
                ema_20 = ticker_data['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
                ema_50 = ticker_data['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                
                # PS Limit Buy Logic
                drawdowns = (ticker_data['Low'] - ticker_data['Open']) / ticker_data['Open']
                avg_drawdown = drawdowns.rolling(window=20).mean().iloc[-1]
                
                limit_i = end_price * (1 + avg_drawdown)
                limit_ii = limit_i * 0.97
                
                recommendations.append({
                    "Ticker": ticker,
                    "5D %": perf_5d,
                    "MTD %": perf_mtd,
                    "YTD %": perf_ytd,
                    "Price": end_price,
                    "Limit I": limit_i,
                    "Limit II": limit_ii,
                    "EMA 20": ema_20,
                    "EMA 50": ema_50
                })
            except:
                continue
            
        # Return full dataframe of recommendations
        df_rec = pd.DataFrame(recommendations)
        return df_rec
    except Exception as e:
        return pd.DataFrame() # Return empty DF on error

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
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔍 Technicals", "⭐ PS's Analysis", "🚀 Recommend Stocks"])
        
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
            
            # RSI Section
            with st.expander("ℹ️ Understanding RSI & Strategy"):
                st.markdown("""
                **Relative Strength Index (RSI):**
                - **What it is:** A momentum oscillator that measures the speed and change of price movements. It ranges from 0 to 100.
                - **Strategy:**
                    - **Overbought (>70):** Suggests the stock may be overvalued and a pullback or reversal could be imminent.
                    - **Oversold (<30):** Suggests the stock may be undervalued and a bounce or recovery could be coming.
                    - **Centerline (50):** Above 50 indicates bullish momentum; below 50 indicates bearish momentum.
                """)

            # RSI Chart
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='magenta', width=1.5), name="RSI"))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
            fig_rsi.update_layout(title="RSI (14)", template="plotly_dark", height=250, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_rsi, use_container_width=True)
            
            # MACD Section
            with st.expander("ℹ️ Understanding MACD & Strategy"):
                st.markdown("""
                **Moving Average Convergence Divergence (MACD):**
                - **What it is:** A trend-following momentum indicator that shows the relationship between two moving averages of a security’s price.
                - **Strategy:**
                    - **Signal Line Crossover:** A bullish signal occurs when the MACD line crosses above the Signal line; a bearish signal when it crosses below.
                    - **Zero Line Crossover:** MACD crossing above zero indicates an strengthening uptrend; below zero indicates a strengthening downtrend.
                    - **Histogram:** Shows the distance between MACD and Signal line. Expanding bars indicate increasing momentum.
                """)

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
            avg_drawdown_val = float(data['Avg_Drawdown'].iloc[-1])
            
            # PS Limit Buy I = Current Price * (1 + Average Intraday Drawdown %)
            # Note: avg_drawdown_val is typically negative
            r_limit_i = curr_price * (1 + avg_drawdown_val)
            
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
                st.metric("PS Limit I", f"${r_limit_i:,.2f}", help=f"Current Price * (1 + {avg_drawdown_val:.2%} Avg 20D Drawdown)")
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

        with tab4:
            st.subheader("🚀 Recommended Stocks")
            st.write("Analyze and rank top performers with strategy-based buy targets. Targets **above** current price are greyed out.")
            
            # Sorting Selection
            sort_col = st.radio("Rank by performance:", ["5D %", "MTD %", "YTD %"], horizontal=True)
            
            with st.spinner(f"Analyzing market opportunities by {sort_col}..."):
                rec_df = get_recommendations()
            
            if not rec_df.empty:
                # Sort based on user selection
                display_df = rec_df.sort_values(by=sort_col, ascending=False).head(10).copy()
                
                # Conditional Styling Function
                def style_buys(val, current_price):
                    if val > current_price:
                        return 'color: #888888; text-decoration: line-through;'
                    return ''

                # We apply styling to specific columns
                styled_df = display_df.style.apply(
                    lambda row: [
                        style_buys(row[col], row['Price']) if col in ['Limit I', 'Limit II', 'EMA 20', 'EMA 50'] else ''
                        for col in row.index
                    ], axis=1
                ).format({
                    "5D %": "{:,.2f}%",
                    "MTD %": "{:,.2f}%",
                    "YTD %": "{:,.2f}%",
                    "Price": "${:,.2f}",
                    "Limit I": "${:,.2f}",
                    "Limit II": "${:,.2f}",
                    "EMA 20": "${:,.2f}",
                    "EMA 50": "${:,.2f}"
                })
                
                st.dataframe(styled_df, use_container_width=True, height=400)
                st.info(f"💡 **Tip:** Ranked by **{sort_col}**. Greyed-out targets with strikethrough are currently above the market price.")
            else:
                st.error("Could not fetch recommendations at this time.")

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
