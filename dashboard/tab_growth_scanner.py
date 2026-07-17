import streamlit as st

from dashboard.components import ENTRY_LEVEL_TONE, condition_checkbox, score_banner
from dashboard.data import get_sp500_tickers, load_and_analyze_sp500

HORIZON_KEY_MAP = {
    "20D High Growth": "growth_20d",
    "50D High Growth": "growth_50d",
    "100D High Growth": "growth_100d",
    "200D High Growth": "growth_200d",
}


def render():
    st.subheader("🚀 Top 20 High Growth Stocks from S&P500")
    st.caption("Scanner uses the current S&P 500 membership list. Use this for current discovery, not historical backtests, because it has survivorship bias.")

    tickers = get_sp500_tickers()
    with st.spinner("Fetching S&P 500 stock data & scanning growth (this can take up to 25s on first run)..."):
        sp500_data = load_and_analyze_sp500(tickers)

    if not sp500_data:
        st.error("No data fetched for S&P 500 stocks.")
        return

    with st.container(border=True):
        st.markdown("### 🔍 Filter by Core Buying Conditions")
        f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)

        c1_filter = f_col1.selectbox("Drawdown >= 8% (c1)", ["Pass Only", "All"], index=0, key="f_c1")
        c2_filter = f_col2.selectbox("Within ±6% EMA20 (c2)", ["Pass Only", "All"], index=0, key="f_c2")
        c3_filter = f_col3.selectbox("RSI 42-58 (c3)", ["Pass Only", "All"], index=0, key="f_c3")
        c4_filter = f_col4.selectbox("Vol Ratio >= 1.6x (c4)", ["Pass Only", "All"], index=0, key="f_c4")
        c5_filter = f_col5.selectbox("MACD > Signal (c5)", ["Pass Only", "All"], index=0, key="f_c5")

        st.markdown("### 📈 Select Growth Horizon")
        growth_horizon = st.radio(
            "Sort and display by:",
            options=["20D High Growth", "50D High Growth", "100D High Growth", "200D High Growth"],
            horizontal=True,
            key="growth_horiz"
        )

    filtered_stocks = []
    for stock in sp500_data:
        if c1_filter == "Pass Only" and not stock['c1']:
            continue
        if c2_filter == "Pass Only" and not stock['c2']:
            continue
        if c3_filter == "Pass Only" and not stock['c3']:
            continue
        if c4_filter == "Pass Only" and not stock['c4']:
            continue
        if c5_filter == "Pass Only" and not stock['c5']:
            continue
        filtered_stocks.append(stock)

    sort_key = HORIZON_KEY_MAP[growth_horizon]
    top_stocks = sorted(filtered_stocks, key=lambda x: x[sort_key], reverse=True)[:20]

    if not top_stocks:
        st.warning("⚠️ No stocks match the selected core condition filters. Try changing some filters to 'All'.")
        return

    st.markdown(f"Showing **Top {len(top_stocks)}** S&P 500 stocks sorted by chosen growth:")

    for stock in top_stocks:
        with st.container(border=True):
            h_col1, h_col2 = st.columns([2, 1])
            h_col1.markdown(f"### **{stock['ticker']}**")
            h_col2.markdown(f"### **${stock['curr_price']:,.2f}**")

            st.write("**% Growth**")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("20D", f"{stock['growth_20d']:+.1f}%")
            m2.metric("50D", f"{stock['growth_50d']:+.1f}%")
            m3.metric("100D", f"{stock['growth_100d']:+.1f}%")
            m4.metric("200D", f"{stock['growth_200d']:+.1f}%")

            st.write("**EMAs**")
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("EMA20", f"${stock['ema20']:,.2f}")
            e2.metric("EMA50", f"${stock['ema50']:,.2f}")
            e3.metric("EMA100", f"${stock['ema100']:,.2f}")
            e4.metric("EMA200", f"${stock['ema200']:,.2f}")

            st.write("")
            score_banner(
                stock['entry_level'],
                f"{stock['total_score']}/12 Score | Pos: {stock['pos_size']}",
                ENTRY_LEVEL_TONE.get(stock['entry_level'], "neutral"),
            )

            with st.expander("🔍 View Core Conditions Checklist Details"):
                det_col1, det_col2 = st.columns(2)
                with det_col1:
                    condition_checkbox("Drawdown >= 8%", stock['c1'], f"{stock['drawdown_10d']:.1%}", "Drawdown >= 8%")
                    condition_checkbox("Within +/-6% EMA20", stock['c2'], f"{stock['ema20_dist']:.1%}", "Within +/-6% EMA20")
                    condition_checkbox("RSI 42-58", stock['c3'], f"{stock['rsi_val']:.1f}", "RSI 42-58")
                with det_col2:
                    condition_checkbox("Vol Ratio >= 1.6x", stock['c4'], f"{stock['vol_ratio']:.1f}x", "Vol Ratio >= 1.6x")
                    condition_checkbox("MACD > Signal", stock['c5'], "core", "MACD > Signal")
                    st.write(f"Core score: **{stock['core_score']}/5**")
