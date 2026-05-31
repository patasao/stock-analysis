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
@st.cache_data(ttl=86400)  # Cache S&P 500 list for 24 hours
def get_sp500_tickers():
    # Try multiple reliable sources for robustness
    sources = [
        "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
        "https://raw.githubusercontent.com/datasets/s-p-500-companies/main/data/constituents.csv",
        "https://raw.githubusercontent.com/fja05/sp500-constituents/master/constituents.csv"
    ]
    
    last_error = ""
    for url in sources:
        try:
            import requests
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            # Normalize column names: look for symbol/ticker and sector/industry
            cols = {col.lower(): col for col in df.columns}
            ticker_col = next((cols[c] for c in ['symbol', 'ticker', 'symbol'] if c in cols), df.columns[0])
            sector_col = next((cols[c] for c in ['sector', 'gics sector', 'industry'] if c in cols), df.columns[1])
            
            df = df[[ticker_col, sector_col]]
            df.columns = ['Ticker', 'Sector']
            df['Ticker'] = df['Ticker'].str.replace('.', '-', regex=False)
            df['Index'] = 'S&P 500'
            return df
        except Exception as e:
            last_error = str(e)
            continue
            
    # Fallback to Wikipedia if CSVs fail
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {'User-Agent': 'Mozilla/5.0'}
        import requests
        response = requests.get(url, headers=headers, timeout=10)
        # Try different table indices as Wikipedia structure can shift
        tables = pd.read_html(response.text)
        for df in tables:
            if 'Symbol' in df.columns or 'Ticker' in df.columns:
                ticker_col = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
                sector_col = 'GICS Sector' if 'GICS Sector' in df.columns else ([c for c in df.columns if 'Sector' in c][0] if [c for c in df.columns if 'Sector' in c] else None)
                if sector_col:
                    df = df[[ticker_col, sector_col]]
                    df.columns = ['Ticker', 'Sector']
                    df['Ticker'] = df['Ticker'].str.replace('.', '-', regex=False)
                    df['Index'] = 'S&P 500'
                    return df
    except Exception as e:
        st.warning(f"⚠️ S&P 500 Source Error: {last_error if last_error else str(e)}")
        st.info("Using built-in limited S&P 500 list for core functionality.")
        return pd.DataFrame([
            {"Ticker": "AAPL", "Sector": "Information Technology", "Index": "S&P 500"},
            {"Ticker": "MSFT", "Sector": "Information Technology", "Index": "S&P 500"},
            {"Ticker": "NVDA", "Sector": "Information Technology", "Index": "S&P 500"},
            {"Ticker": "GOOGL", "Sector": "Communication Services", "Index": "S&P 500"},
            {"Ticker": "AMZN", "Sector": "Consumer Discretionary", "Index": "S&P 500"},
            {"Ticker": "META", "Sector": "Communication Services", "Index": "S&P 500"},
            {"Ticker": "TSLA", "Sector": "Consumer Discretionary", "Index": "S&P 500"}
        ])

@st.cache_data(ttl=86400)
def get_nasdaq100_tickers():
    try:
        # Wikipedia is usually more reliable for NASDAQ-100 as there isn't a single standard CSV repo as stable as the S&P 500 one
        # But we will use a common community-maintained one if available, or stick to a robust requests-based scrape
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        headers = {'User-Agent': 'Mozilla/5.0'}
        import requests
        response = requests.get(url, headers=headers)
        tables = pd.read_html(response.text)
        # Usually the 4th table on this page
        df = tables[4] 
        # Wikipedia table columns: 'Ticker' and 'GICS Sector' (or similar)
        # We need to find the right column names as they vary
        ticker_col = [col for col in df.columns if 'Symbol' in col or 'Ticker' in col][0]
        sector_col = [col for col in df.columns if 'Sector' in col][0]
        
        df = df[[ticker_col, sector_col]]
        df.columns = ['Ticker', 'Sector']
        df['Index'] = 'NASDAQ-100'
        return df
    except Exception as e:
        # Fallback for NASDAQ-100
        return pd.DataFrame([
            {"Ticker": "AAPL", "Sector": "Information Technology", "Index": "NASDAQ-100"},
            {"Ticker": "MSFT", "Sector": "Information Technology", "Index": "NASDAQ-100"},
            {"Ticker": "NVDA", "Sector": "Information Technology", "Index": "NASDAQ-100"},
            {"Ticker": "AMZN", "Sector": "Consumer Discretionary", "Index": "NASDAQ-100"},
            {"Ticker": "META", "Sector": "Communication Services", "Index": "NASDAQ-100"}
        ])

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
    
    # Intraday Drawdown (20-day average)
    df['Intraday_Drawdown_Pct'] = (df['Low'] - df['Open']) / df['Open']
    df['Avg_Drawdown'] = df['Intraday_Drawdown_Pct'].rolling(window=20).mean()
    
    return df

# --- Recommendation Logic ---
@st.cache_data(ttl=3600)
def get_recommendations(tickers_df):
    if tickers_df.empty:
        return pd.DataFrame()
        
    tickers = tickers_df['Ticker'].tolist()
    sector_map = dict(zip(tickers_df['Ticker'], tickers_df['Sector']))
    index_map = dict(zip(tickers_df['Ticker'], tickers_df['Index']))
    
    try:
        # Fetch data for all tickers (1y to cover YTD and EMAs)
        data = yf.download(tickers, period="1y", interval="1d", group_by='ticker', threads=True)
        recommendations = []
        
        # Calculate dates for MTD and YTD
        today = datetime.now()
        first_day_month = today.replace(day=1)
        first_day_year = today.replace(month=1, day=1)

        # Handle the case where yf returns a single ticker dataframe if only one ticker is passed or fails
        if isinstance(data.columns, pd.Index) and not isinstance(data.columns, pd.MultiIndex):
            return pd.DataFrame()

        available_tickers = data.columns.levels[0] if isinstance(data.columns, pd.MultiIndex) else []

        for ticker in tickers:
            try:
                if ticker not in available_tickers: continue
                ticker_data = data[ticker].dropna()
                if len(ticker_data) < 50: continue # Need at least 50 days for EMA 50
                
                # Latest Close
                end_price = float(ticker_data['Close'].iloc[-1])
                
                # 5-day performance
                start_price_5d = float(ticker_data['Close'].iloc[-5]) if len(ticker_data) >= 5 else float(ticker_data['Close'].iloc[0])
                perf_5d = ((end_price - start_price_5d) / start_price_5d) * 100
                
                # 1M performance (approx 21 trading days)
                if len(ticker_data) >= 21:
                    start_price_1m = float(ticker_data['Close'].iloc[-21])
                    perf_1m = ((end_price - start_price_1m) / start_price_1m) * 100
                else:
                    perf_1m = 0.0

                # 1Y performance (approx 252 trading days)
                if len(ticker_data) >= 252:
                    start_price_1y = float(ticker_data['Close'].iloc[-252])
                    perf_1y = ((end_price - start_price_1y) / start_price_1y) * 100
                else:
                    # Fallback to earliest available if less than a year
                    start_price_1y = float(ticker_data['Close'].iloc[0])
                    perf_1y = ((end_price - start_price_1y) / start_price_1y) * 100
                
                # EMAs
                ema_20 = ticker_data['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
                ema_50 = ticker_data['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                ema_100 = ticker_data['Close'].ewm(span=100, adjust=False).mean().iloc[-1]
                
                # RSI calculation
                delta = ticker_data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi_series = 100 - (100 / (1 + rs))
                latest_rsi = rsi_series.iloc[-1]
                
                # Volume Ratio (Latest vs 20D Avg)
                avg_vol = ticker_data['Volume'].tail(20).mean()
                latest_vol = ticker_data['Volume'].iloc[-1]
                vol_ratio = latest_vol / avg_vol if avg_vol > 0 else 0
                
                # 52-Week High and Distance
                high_52w = ticker_data['High'].tail(252).max()
                dist_52w = ((end_price - high_52w) / high_52w) * 100
                
                recommendations.append({
                    "Ticker": ticker,
                    "Index": index_map.get(ticker, "Unknown"),
                    "Sector": sector_map.get(ticker, "Unknown"),
                    "Price": end_price,
                    "5D %": perf_5d,
                    "1M %": perf_1m,
                    "1Y %": perf_1y,
                    "RSI": latest_rsi,
                    "Vol Ratio": vol_ratio,
                    "52W High %": dist_52w,
                    "EMA 20": ema_20,
                    "EMA 50": ema_50,
                    "EMA 100": ema_100
                })
            except:
                continue
            
        # Return full dataframe of recommendations
        df_rec = pd.DataFrame(recommendations)
        return df_rec
    except Exception as e:
        st.error(f"Error in recommendations: {e}")
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

# Fetch market data for recommendations
sp500_df = get_sp500_tickers()

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
        ema_100_val = float(data['EMA_100'].iloc[-1])
        atr_val = float(data['ATR'].iloc[-1])
        rsi_val = float(data['RSI'].iloc[-1])
        res_val = float(data['Resistance'].iloc[-1])
        sup_val = float(data['Support'].iloc[-1])
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔍 Technicals", "🚀 Recommend Stocks"])
        
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

            st.write("---")
            st.subheader("🎯 Trading Entry Rules (Composite Strategy)")
            
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
            score_col1, score_col2 = st.columns([1, 2])
            with score_col1:
                st.markdown(f"""
                <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: black;">
                    <h1 style="margin: 0;">{entry_level}</h1>
                    <p style="margin: 0; font-weight: bold;">{pos_size}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with score_col2:
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

            st.info("""
            **Additional Risk Rules:**
            - Maximum position size per stock = 15% of Growth Portfolio
            - Always set Stop Loss at -8% to -10% from entry price
            """)

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
            st.subheader("🚀 Recommended Stocks (S&P 500)")
            st.write("Analyze and rank top performers from the S&P 500 with advanced technical indicators.")
            
            # Educational Content for Recommendations
            with st.expander("ℹ️ How to interpret these indicators"):
                st.markdown("""
                **Advanced Technical Metrics:**
                - **Volume Ratio:** Current volume divided by the 20-day average. 
                    - *> 1.0x:* Indicates higher than usual interest (breakouts or heavy selling).
                    - *> 2.0x:* Often signals "Institutional Buying" or a significant news event.
                - **RSI (14):** Momentum indicator (0-100).
                    - *High (>70):* Strong momentum, but watch for pullbacks.
                    - *Low (<30):* Potential oversold bounce opportunity.
                - **52W High %:** How far the price is from its 1-year peak.
                    - *Closer to 0%:* Indicates extreme "Relative Strength" (stocks hitting new highs often keep going).
                    - *Large Negative:* Deep value or a broken trend.
                
                **Strategy Tip:** Look for stocks with a **Volume Ratio > 1.2x** and **52W High % > -5%** for high-probability momentum setups.
                """)
            
            # Build the dataframe for S&P 500
            combined_market_df = sp500_df
            
            if not combined_market_df.empty:
                # Sector Selection
                sectors = sorted(combined_market_df['Sector'].unique().tolist())
                selected_sector = st.selectbox("Filter by Industry:", ["All"] + sectors)
                
                # Technical Filters (Slicers)
                st.write("**Technical Filters:**")
                f_col1, f_col2, f_col3 = st.columns(3)
                
                vol_threshold = f_col1.number_input("Min Volume Ratio", value=1.5, step=0.1, help="Current Volume / 20D Avg Volume")
                rsi_range = f_col2.slider("RSI (14) Range", 0, 100, (30, 70), help="Momentum range (30-70 is standard momentum)")
                high_threshold = f_col3.slider("Max Distance to 52W High (%)", -100, 0, -5, help="Closer to 0 is stronger relative strength")

                # Sorting Selection
                st.write("**Rank by performance timeframe:**")
                sort_col = st.radio("Select timeframe:", ["5D %", "1M %", "1Y %"], horizontal=True)
                
                with st.spinner(f"Scanning S&P 500 for setups by {sort_col}..."):
                    rec_df = get_recommendations(combined_market_df)
                
                if not rec_df.empty:
                    # Apply technical filters based on slicers
                    filtered_df = rec_df[
                        (rec_df['Vol Ratio'] >= vol_threshold) & 
                        (rec_df['RSI'] >= rsi_range[0]) & (rec_df['RSI'] <= rsi_range[1]) &
                        (rec_df['52W High %'] >= high_threshold)
                    ]

                    # Filter by sector if not "All"
                    if selected_sector != "All":
                        filtered_df = filtered_df[filtered_df['Sector'] == selected_sector]
                        
                    # Sort based on user selection and take top 10
                    display_df = filtered_df.sort_values(by=sort_col, ascending=False).head(10).copy()
                    
                    if not display_df.empty:
                        st.write("---")
                        st.write(f"### 🔥 Top {len(display_df)} Momentum Opportunities ({selected_sector})")
                        st.caption(f"Filters: Volume > {vol_threshold}x, RSI {rsi_range[0]}-{rsi_range[1]}, 52W High > {high_threshold}%")
                        
                        # Create a grid of cards (2 columns)
                        for i in range(0, len(display_df), 2):
                            cols = st.columns(2)
                            for j in range(2):
                                if i + j < len(display_df):
                                    row = display_df.iloc[i + j]
                                    with cols[j]:
                                        # Card Container
                                        with st.container(border=True):
                                            header_col1, header_col2 = st.columns([1, 1.2])
                                            header_col1.subheader(f"{row['Ticker']}")
                                            header_col1.caption(f"{row['Sector']}")
                                            
                                            # Price & Main Sort Metric
                                            header_col2.metric("Price", f"${row['Price']:,.2f}")
                                            
                                            # Performance Metrics Row
                                            p_col1, p_col2, p_col3 = st.columns(3)
                                            p_col1.metric("5D", "", f"{row['5D %']:+.2f}%")
                                            p_col2.metric("1M", "", f"{row['1M %']:+.2f}%")
                                            p_col3.metric("1Y", "", f"{row['1Y %']:+.2f}%")
                                            
                                            st.divider()
                                            
                                            # Technical Highlights
                                            t_col1, t_col2, t_col3 = st.columns(3)
                                            t_col1.markdown(f"**RSI**\n{row['RSI']:.1f}")
                                            t_col2.markdown(f"**Volume**\n{row['Vol Ratio']:.1f}x")
                                            t_col3.markdown(f"**52W High**\n{row['52W High %']:.1f}%")
                                            
                                            st.divider()
                                            
                                            # Buy Targets
                                            st.markdown("**Entry Targets:**")
                                            tar_col1, tar_col2, tar_col3 = st.columns(3)
                                            
                                            def format_target(val, curr):
                                                if val < curr:
                                                    return f"✅ **${val:,.2f}**"
                                                return f"~~${val:,.2f}~~"

                                            tar_col1.markdown(f"EMA 20: {format_target(row['EMA 20'], row['Price'])}")
                                            tar_col2.markdown(f"EMA 50: {format_target(row['EMA 50'], row['Price'])}")
                                            tar_col3.markdown(f"EMA 100: {format_target(row['EMA 100'], row['Price'])}")

                        st.info(f"💡 **Tip:** ✅ indicates targets below current market price (active dips). Strikethrough indicates targets already exceeded.")
                    else:
                        st.warning(f"No stocks found for the selection.")
                else:
                    st.error("Could not fetch recommendations at this time.")
            else:
                st.warning("S&P 500 data is unavailable.")

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
