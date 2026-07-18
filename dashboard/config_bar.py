import streamlit as st


def render_config_bar():
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns(5)
        symbol = col1.text_input("Stock Symbol", value="AAPL").upper()
        period = col2.selectbox("Period", options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
        interval = col3.selectbox("Interval", options=["1d", "1wk", "1mo"], index=0)
        ema_short = col4.selectbox("Short EMA Span", options=[5, 8, 9, 10, 12, 20, 26, 34, 50], index=5)
        ema_long = col5.selectbox("Long EMA Span", options=[20, 50, 100, 150, 200], index=1)

    return symbol, period, interval, ema_short, ema_long
