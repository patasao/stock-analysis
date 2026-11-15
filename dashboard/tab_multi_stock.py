import pandas as pd
import streamlit as st

from dashboard.components import ENTRY_LEVEL_TONE, EXIT_LEVEL_TONE, TONE_COLORS
from dashboard.data import get_analysis


def _tone_style(tone_map):
    def _style(value):
        tone = tone_map.get(value, "neutral")
        bg, fg = TONE_COLORS.get(tone, TONE_COLORS["neutral"])
        return f"background-color: {bg}; color: {fg}"
    return _style


def render(period, interval, ema_short, ema_long):
    with st.container(border=True):
        st.subheader("Multi-Stock Technical Comparison")
        multi_input = st.text_input("Enter Ticker Symbols (comma-separated)", value="AAPL, TSLA, MSFT, GOOGL, NVDA, AMD, META")

        if not multi_input:
            return

        symbols = [s.strip().upper() for s in multi_input.split(",") if s.strip()]
        if not symbols:
            return

        with st.spinner(f"Analyzing {len(symbols)} stocks..."):
            results = []
            for s in symbols:
                res = get_analysis(s, period, interval, ema_short, ema_long)
                if res:
                    currency = "฿" if s.endswith(".BK") else "$"
                    results.append({
                        "Symbol": s,
                        "Current Price": f"{currency}{res['curr_price']:,.2f}",
                        "20D Support": f"{currency}{res['sup_val']:,.2f}",
                        "20D Resistance": f"{currency}{res['res_val']:,.2f}",
                        "EMA20": f"{currency}{res['ema_20_val']:,.2f}",
                        "EMA50": f"{currency}{res['ema_50_val']:,.2f}",
                        "EMA100": f"{currency}{res['ema_100_val']:,.2f}",
                        "EMA200": f"{currency}{res['ema_200_val']:,.2f}",
                        "Technical Setup": "Buy Candidate" if res['entry_level'] == "Buy" else res['entry_level'],
                        "Selling Score": res['exit_level']
                    })

        if not results:
            st.warning("No valid data found for the entered tickers.")
            return

        df_multi = pd.DataFrame(results)

        styled = (
            df_multi.style
            .map(_tone_style(ENTRY_LEVEL_TONE), subset=["Technical Setup"])
            .map(_tone_style(EXIT_LEVEL_TONE), subset=["Selling Score"])
        )

        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True
        )
