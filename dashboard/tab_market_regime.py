import pandas as pd
import streamlit as st

from .data import get_market_regime, get_sector_screen, get_thai_market_context

SET_SECTORS = (
    "Agro & Food Industry", "Consumer Products", "Financials", "Industrials",
    "Property & Construction", "Resources", "Services", "Technology",
)


def render():
    st.subheader("Market Regime Assessment")
    st.caption("Use regime and sector strength to rank candidates; neither is an automatic buy signal.")
    market = st.radio("Market", ["US", "Thailand"], horizontal=True, key="regime_market")

    regime = get_market_regime() if market == "US" else get_thai_market_context()
    if "Error" in regime:
        st.warning(f"Market data unavailable: {regime['Error']}")
    elif market == "Thailand":
        cols = st.columns(5)
        cols[0].metric("SET Regime (proxy)", regime.get("Regime", "N/A"))
        cols[1].metric("Basket 20D", f"{regime['SET sector basket proxy 20D']:+.1f}%" if regime.get("SET sector basket proxy 20D") is not None else "N/A")
        cols[2].metric("Basket 50D", f"{regime['SET sector basket proxy 50D']:+.1f}%" if regime.get("SET sector basket proxy 50D") is not None else "N/A")
        cols[3].metric("Breadth proxy", f"{regime['Breadth proxy (% above 50D)']:.1f}%" if regime.get("Breadth proxy (% above 50D)") is not None else "N/A", help="Share of the selected basket stocks trading above their 50-day average; not full SET market breadth.")
        cols[4].metric("Realized volatility", f"{regime['Realized volatility (annualized)']:.1f}%" if regime.get("Realized volatility (annualized)") is not None else "N/A")
        st.caption(f"Calculated from {regime.get('Stocks in breadth sample', 0)} selected liquid SET stocks. This is a market proxy, not the official SET index.")
    else:
        cols = st.columns(5)
        cols[0].metric("Major Index Trend", regime.get("Regime", "N/A"))
        cols[1].metric("SPY vs EMA200", f"{regime.get('SPY vs EMA200', 0):+.1f}%")
        cols[2].metric("Market Breadth Proxy", f"{regime['Breadth Proxy vs EMA200']:+.1f}%" if regime.get("Breadth Proxy vs EMA200") is not None else "N/A", help="NYSE Composite vs its 200-day EMA, an index-level breadth proxy; not the percentage of constituents above their averages.")
        cols[3].metric("Volatility (VIX)", f"{regime['VIX']:.1f}" if regime.get("VIX") is not None else "N/A")
        cols[4].metric("10Y Treasury Yield", f"{regime['10Y Treasury Yield']:.2f}%" if regime.get("10Y Treasury Yield") is not None else "N/A")
        st.caption(f"SPY 20D return: {regime.get('SPY 20D Return', 0):+.1f}% · SPY 50D return: {regime.get('SPY 50D Return', 0):+.1f}% · QQQ vs EMA200: {regime.get('QQQ vs EMA200', 0):+.1f}%")

    st.markdown("### Sector Screening")
    screen = get_sector_screen(market)
    if isinstance(screen, dict):
        st.warning(f"Sector data unavailable: {screen.get('Error', 'Unknown error')}")
    else:
        screen_df = pd.DataFrame(screen)
        percent_columns = [column for column in screen_df.columns if "Return" in column or "Relative" in column]
        st.dataframe(
            screen_df.style.format({column: "{:+.2f}%" for column in percent_columns}, na_rep="N/A"),
            use_container_width=True,
            hide_index=True,
        )
        if market == "US":
            st.caption("US coverage: all 11 S&P 500 sectors via sector ETFs. Relative strength ranks sectors, not individual buy signals.")
        else:
            st.caption("Thailand coverage: eight major SET groups represented by equal-weight baskets of selected liquid stocks. Returns are historical stock-basket proxies, not official SET sector-index returns. The comparison baseline equally weights the available sector baskets; coverage shows how many basket stocks had at least 50 trading days of history.")

    if market == "Thailand":
        st.markdown("**Major SET sector groups:** " + " · ".join(SET_SECTORS))

    st.markdown("### Events and Macro Risk Review")
    st.caption("The market-data feed does not provide a dependable economic, earnings, or geopolitical event calendar. Review these items before selecting Buy.")
    c1, c2 = st.columns(2)
    with c1:
        rate_label = "US Treasury yield trend" if market == "US" else "Thai interest rates / government bond yield trend"
        st.selectbox(rate_label, ["Not reviewed", "Falling", "Stable", "Rising", "Uncertain"], key="rate_assessment")
        st.selectbox("Major economic events / central-bank decisions", ["Not reviewed", "No near-term event", "Event within 7 days", "Event within 30 days", "High uncertainty"], key="economic_events")
        st.selectbox("Earnings season / upcoming results", ["Not reviewed", "Outside earnings window", "Earnings within 7 days", "Earnings within 30 days", "High uncertainty"], key="earnings_window")
    with c2:
        if market == "Thailand":
            st.selectbox("Foreign net flows / local institutional flows", ["Not reviewed", "Foreign net buying", "Foreign net selling", "Mixed", "Unavailable"], key="thai_flows")
        st.selectbox("Major geopolitical or macro risks", ["Not reviewed", "Low", "Moderate", "Elevated", "High"], key="macro_risk")
        st.selectbox("Sector rotation / fresh catalysts", ["Not reviewed", "Improving with catalyst", "Improving", "Mixed", "Weakening"], key="rotation_catalyst")
        st.text_area("Company catalyst and source/date", placeholder="Record the catalyst, source, and date; enter 'none' if no fresh catalyst.", key="company_catalyst")
        st.text_area("Key event or macro-risk notes", placeholder="Record source, date, affected sector, and expected impact.", key="macro_notes")

    st.info("Before a trade, confirm the stock's sector and relative strength, setup type, entry zone, support-based stop, TP1/TP2, R/R, catalyst, and event risk. For US stocks, use the regular-session close as the technical reference; for Thai stocks, use the SET regular close. Intraday and extended-hours quotes are not substituted for the regular close.")
