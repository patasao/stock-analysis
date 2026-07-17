import streamlit as st

from dashboard.charts import build_overview_chart
from dashboard.components import ENTRY_LEVEL_TONE, EXIT_LEVEL_TONE, TONE_BADGE_COLOR, quality_warnings
from dashboard.data import get_analysis
from dashboard.theme import is_dark_theme


def render(symbol, period, interval, ema_short, ema_long):
    if not symbol:
        return

    with st.spinner(f"Loading data for {symbol}..."):
        analysis = get_analysis(symbol, period, interval, ema_short, ema_long)

    if not analysis:
        st.error(f"Ticker '{symbol}' not found or data unavailable.")
        return

    data = analysis['df']
    quality_warnings(analysis.get('quality_warnings', []))

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Price", f"${analysis['curr_price']:,.2f}", f"{analysis['price_change_pct']:+.2f}%")
        col2.metric(f"EMA {ema_short}", f"${analysis['ema_short_val']:,.2f}")
        col3.metric("20D Support", f"${analysis['sup_val']:,.2f}")
        col4.metric("20D Resistance", f"${analysis['res_val']:,.2f}")

        entry_tone = ENTRY_LEVEL_TONE.get(analysis['entry_level'], "neutral")
        exit_tone = EXIT_LEVEL_TONE.get(analysis['exit_level'], "neutral")
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            st.badge(
                f"Entry: {analysis['entry_level']} · {analysis['pos_size']}",
                color=TONE_BADGE_COLOR.get(entry_tone, "gray"),
            )
        with b_col2:
            st.badge(
                f"Exit: {analysis['exit_level']} · {analysis['exit_action']}",
                color=TONE_BADGE_COLOR.get(exit_tone, "gray"),
            )
        st.caption("Full breakdown, checklist, and backtest on the Technicals tab →")

    fig = build_overview_chart(data, symbol, ema_short, ema_long, dark=is_dark_theme())
    st.plotly_chart(fig, use_container_width=True)
