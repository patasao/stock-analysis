import streamlit as st

from dashboard import tab_growth_scanner, tab_multi_stock, tab_overview, tab_technicals
from dashboard.config_bar import render_config_bar

st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide")

st.title("📈 Stock Insight Dashboard")

symbol, period, interval, ema_short, ema_long = render_config_bar()

tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔍 Technicals", "📋 Multi-Stock Analysis", "🚀 High Growth Stocks"])

with tab1:
    tab_overview.render(symbol, period, interval, ema_short, ema_long)

with tab2:
    tab_technicals.render(symbol, period, interval, ema_short, ema_long)

with tab3:
    tab_multi_stock.render(period, interval, ema_short, ema_long)

with tab4:
    tab_growth_scanner.render()

st.divider()
st.markdown(
    """
    <div style="text-align: center; color: #888888; font-size: 0.8em;">
        Stock Insight Dashboard | Built with Streamlit & yfinance | Powered by Claude, Gemini, Codex
    </div>
    """,
    unsafe_allow_html=True
)
