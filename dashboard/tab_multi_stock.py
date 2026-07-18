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

        ema_short_col = f"EMA{ema_short}"
        ema_long_col = f"EMA{ema_long}" if ema_long != ema_short else f"EMA{ema_long} (Long)"

        with st.spinner(f"Analyzing {len(symbols)} stocks..."):
            results = []
            for s in symbols:
                res = get_analysis(s, period, interval, ema_short, ema_long)
                if res:
                    results.append({
                        "Symbol": s,
                        "Price": res['curr_price'],
                        "20D Support": res['sup_val'],
                        "20D Resistance": res['res_val'],
                        ema_short_col: res['ema_short_val'],
                        ema_long_col: res['ema_long_val'],
                        "RSI (14)": res['rsi_val'],
                        "Trend (EMA)": res['trend'],
                        "Sentiment": res['sentiment'],
                        "Avg Intraday DD": res['avg_dd'],
                        "Avg Intraday DU": res['avg_du'],
                        "Buying Score": res['entry_level'],
                        "Selling Score": res['exit_level']
                    })

        if not results:
            st.warning("No valid data found for the entered tickers.")
            return

        df_multi = pd.DataFrame(results)

        styled = (
            df_multi.style
            .format({
                "Price": "${:,.2f}",
                "20D Support": "${:,.2f}",
                "20D Resistance": "${:,.2f}",
                ema_short_col: "${:,.2f}",
                ema_long_col: "${:,.2f}",
                "RSI (14)": "{:.2f}",
                "Avg Intraday DD": "{:.2f}%",
                "Avg Intraday DU": "{:.2f}%"
            })
            .map(_tone_style(ENTRY_LEVEL_TONE), subset=["Buying Score"])
            .map(_tone_style(EXIT_LEVEL_TONE), subset=["Selling Score"])
        )

        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True
        )
