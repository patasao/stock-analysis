import streamlit as st

from dashboard.charts import build_overview_chart
from dashboard.components import quality_warnings
from dashboard.data import get_analysis
from dashboard.theme import is_dark_theme

INDEXES = [
    ("^GSPC", "S&P 500"),
    ("^IXIC", "NASDAQ Composite"),
    ("^DJI", "Dow Jones Industrial Average"),
    ("^RUT", "Russell 2000"),
    ("^VIX", "CBOE Volatility Index (VIX)"),
]


def render(period, interval, ema_short, ema_long):
    st.subheader("🌐 Major Market Indexes")
    dark = is_dark_theme()

    for symbol, name in INDEXES:
        with st.container(border=True):
            st.markdown(f"### {name} ({symbol})")

            with st.spinner(f"Loading {name}..."):
                analysis = get_analysis(symbol, period, interval, ema_short, ema_long)

            if not analysis:
                st.error(f"Data unavailable for {symbol}.")
                continue

            data = analysis['df']
            quality_warnings(analysis.get('quality_warnings', []))

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Level", f"{analysis['curr_price']:,.2f}", f"{analysis['price_change_pct']:+.2f}%")
            col2.metric(f"EMA {ema_short}", f"{analysis['ema_short_val']:,.2f}")
            col3.metric("RSI (14)", f"{analysis['rsi_val']:.2f}")
            col4.metric("Trend (EMA)", analysis['trend'], analysis['trend_detail'])

            fig = build_overview_chart(data, symbol, ema_short, ema_long, dark=dark)
            st.plotly_chart(fig, use_container_width=True)
