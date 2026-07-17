import streamlit as st

from analysis_core import format_compact_number, format_percent, is_finite
from dashboard.charts import build_multi_indicator_chart, build_volatility_scale_figure
from dashboard.components import ENTRY_LEVEL_TONE, EXIT_LEVEL_TONE, condition_checkbox, quality_warnings, score_banner
from dashboard.data import get_analysis, get_fundamental_snapshot, get_market_regime, get_relative_strength
from dashboard.help_text import TECH_HELP
from dashboard.theme import is_dark_theme


def render(symbol, period, interval, ema_short, ema_long):
    if not symbol:
        return

    analysis = get_analysis(symbol, period, interval, ema_short, ema_long)
    if not analysis:
        st.error(f"Ticker '{symbol}' not found or data unavailable.")
        return

    data = analysis['df']

    with st.container(border=True):
        st.subheader("Advanced Technical Indicators")

        t_col1, t_col2, t_col3 = st.columns(3)
        rsi_status = "Overbought ⚠️" if analysis['rsi_val'] > 70 else "Oversold ⚠️" if analysis['rsi_val'] < 30 else "Neutral"
        t_col1.metric("RSI (14)", f"{analysis['rsi_val']:.2f}", rsi_status, help=TECH_HELP["RSI (14)"])
        t_col2.metric("Trend (EMA)", analysis['trend'], analysis['trend_detail'], help=TECH_HELP["Trend (EMA)"])
        t_col3.metric("Sentiment", analysis['sentiment'], analysis['sentiment_detail'], help=TECH_HELP["Sentiment"])

        e_col1, e_col2, e_col3, e_col4 = st.columns(4)
        e_col1.metric("EMA 20", f"${analysis['ema_short_val']:,.2f}", help=TECH_HELP["EMA 20"])
        e_col2.metric("EMA 50", f"${analysis['ema_long_val']:,.2f}", help=TECH_HELP["EMA 50"])
        e_col3.metric("EMA 100", f"${analysis['ema_100_val']:,.2f}", help=TECH_HELP["EMA 100"])
        e_col4.metric("EMA 200", f"${analysis['ema_200_val']:,.2f}", help=TECH_HELP["EMA 200"])

        quality_warnings(analysis.get('quality_warnings', []))

    with st.container(border=True):
        st.subheader("Fundamentals, Relative Strength, and Market Regime")
        fund = get_fundamental_snapshot(symbol)
        rel_strength = get_relative_strength(symbol)
        regime = get_market_regime()

        if "Error" in fund:
            st.warning(f"Fundamental data unavailable: {fund['Error']}")
        else:
            f1, f2, f3, f4, f5 = st.columns(5)
            f1.metric("Market Cap", format_compact_number(fund.get("Market Cap")), help=TECH_HELP["Market Cap"])
            f2.metric("Forward P/E", f"{fund.get('Forward P/E'):.2f}" if is_finite(fund.get("Forward P/E")) else "N/A", help=TECH_HELP["Forward P/E"])
            f3.metric("PEG", f"{fund.get('PEG'):.2f}" if is_finite(fund.get("PEG")) else "N/A", help=TECH_HELP["PEG"])
            f4.metric("Revenue Growth", format_percent(fund.get("Revenue Growth")), help=TECH_HELP["Revenue Growth"])
            f5.metric("Debt/Equity", f"{fund.get('Debt/Equity'):.1f}" if is_finite(fund.get("Debt/Equity")) else "N/A", help=TECH_HELP["Debt/Equity"])
            st.caption(f"Sector: {fund.get('Sector', 'N/A')} | Industry: {fund.get('Industry', 'N/A')}")

        r_cols = st.columns(4)
        if "Error" in rel_strength:
            r_cols[0].warning(f"Relative strength unavailable: {rel_strength['Error']}")
        else:
            for col, key in zip(r_cols, ["20D vs SPY", "50D vs SPY", "100D vs SPY", "200D vs SPY"]):
                col.metric(key, f"{rel_strength.get(key, 0.0):+.1f}%", help=TECH_HELP["Relative Strength"])

        m_cols = st.columns(4)
        if "Error" in regime:
            m_cols[0].warning(f"Market regime unavailable: {regime['Error']}")
        else:
            m_cols[0].metric("Regime", regime.get("Regime", "N/A"), help=TECH_HELP["Regime"])
            m_cols[1].metric("SPY vs EMA200", f"{regime.get('SPY vs EMA200', 0.0):+.1f}%", help=TECH_HELP["SPY vs EMA200"])
            m_cols[2].metric("QQQ vs EMA200", f"{regime.get('QQQ vs EMA200', 0.0):+.1f}%", help=TECH_HELP["QQQ vs EMA200"])
            m_cols[3].metric("VIX", f"{regime.get('VIX'):.2f}" if is_finite(regime.get("VIX")) else "N/A", help=TECH_HELP["VIX"])

    with st.container(border=True):
        st.subheader("Trade Plan and Backtest Check")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Suggested Entry", f"${analysis['suggested_entry']:,.2f}", help=TECH_HELP["Suggested Entry"])
        p2.metric("Stop", f"${analysis['stop_loss']:,.2f}", help=TECH_HELP["Stop"])
        p3.metric("Target", f"${analysis['target_resistance']:,.2f}", help=TECH_HELP["Target"])
        p4.metric("Reward/Risk", f"{analysis['reward_risk']:.2f}R", help=TECH_HELP["Reward/Risk"])

        bt = analysis.get("backtest", {})
        if bt.get("entry_count", 0) == 0:
            st.info(bt.get("message", "No backtest entries available."))
        else:
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Backtest Entries", bt["entry_count"], help=TECH_HELP["Backtest Entries"])
            b2.metric("20D Win Rate", f"{bt['win_rate_20d']:.1f}%", help=TECH_HELP["20D Win Rate"])
            b3.metric("Avg 20D Return", f"{bt['avg_return_20d']:+.2f}%", help=TECH_HELP["Avg 20D Return"])
            b4.metric("Worst 20D Adverse", f"{bt['worst_adverse_20d']:.2f}%", help=TECH_HELP["Worst 20D Adverse"])
            with st.expander("Backtest by score level"):
                st.dataframe(bt["by_level"], use_container_width=True, hide_index=True)

        d_col1, d_col2 = st.columns(2)
        d_col1.metric("20D Drawdown", f"{analysis['dd_20d']:.2f}%", help=TECH_HELP["20D Drawdown"])
        d_col2.metric("20D Drawup", f"{analysis['du_20d']:.2f}%", help=TECH_HELP["20D Drawup"])

        st.write("")
        st.markdown("#### 📊 Intraday Volatility Spectrum (20-Day)")
        vol_fig = build_volatility_scale_figure(
            analysis['lowest_dd'],
            analysis['avg_dd'],
            analysis['avg_du'],
            analysis['highest_du'],
            dark=is_dark_theme(),
        )
        if vol_fig is None:
            st.warning("Volatility scale data unavailable.")
        else:
            st.plotly_chart(vol_fig, use_container_width=True, config={"displayModeBar": False})

    with st.container(border=True):
        buy_col, sell_col = st.columns(2)

        with buy_col:
            st.subheader("🎯 Buying Score (Entry Rules)")

            with st.expander("ℹ️ How the Scoring System Works"):
                st.markdown("""
                **The Goal:** This system combines 12 technical filters to find "high-probability" setups where momentum meets value.
                """)

            score_banner(
                analysis['entry_level'],
                analysis['pos_size'],
                ENTRY_LEVEL_TONE.get(analysis['entry_level'], "neutral"),
            )

            st.write("")
            st.write(f"**Core Conditions:** {analysis['core_score']}/5")
            st.write(f"**Supporting Conditions:** {analysis['supp_score']}/7")
            if analysis['risk_fail_rsi']: st.error("⚠️ Risk: RSI too high (> 68)")
            if analysis['risk_fail_ema20']: st.error("⚠️ Risk: Too far above EMA20 (> 8%)")

            with st.expander("🔍 View Checklist Details"):
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    st.write("**Core Conditions**")
                    condition_checkbox("Drawdown >= 8%", analysis['c1'], f"{analysis['drawdown_10d']:.1%}", "Drawdown >= 8%")
                    condition_checkbox("Within +/-6% EMA20", analysis['c2'], f"{analysis['ema20_dist']:.1%}", "Within +/-6% EMA20")
                    condition_checkbox("RSI 42-58", analysis['c3'], f"{analysis['rsi_val']:.1f}", "RSI 42-58")
                    condition_checkbox("Vol Ratio >= 1.6x", analysis['c4'], f"{analysis['vol_ratio']:.1f}x", "Vol Ratio >= 1.6x")
                    condition_checkbox("MACD > Signal", analysis['c5'], "core", "MACD > Signal")

                with c_col2:
                    st.write("**Supporting Conditions**")
                    condition_checkbox("Above EMA50", analysis['s1'], "price > EMA50", "Above EMA50")
                    condition_checkbox("MACD > Signal", analysis['s2'], "support", "MACD > Signal")
                    condition_checkbox("78%-94% of 52W High", analysis['s3'], "range", "78%-94% of 52W High")
                    condition_checkbox("Above EMA100", analysis['s4'], "price > EMA100", "Above EMA100")
                    condition_checkbox("ADX > 20", analysis['s5'], f"{analysis['adx_val']:.1f}", "ADX > 20")
                    condition_checkbox("Above BB Middle", analysis['s6'], "price > mid", "Above BB Middle")
                    condition_checkbox("Stoch RSI < 75", analysis['s7'], f"{analysis['stoch_rsi']:.1f}", "Stoch RSI < 75")

        with sell_col:
            st.subheader("🚩 Selling Score (Exit Rules)")

            with st.expander("ℹ️ How the Exit Strategy Works"):
                st.markdown("""
                **The Goal:** To protect capital and lock in gains using a systematic approach.
                """)

            score_banner(
                analysis['exit_level'],
                analysis['exit_action'],
                EXIT_LEVEL_TONE.get(analysis['exit_level'], "neutral"),
            )

            st.write("")
            st.write(f"**Exit Signals Triggered:** {analysis['exit_score']}/5")
            condition_checkbox("Price below EMA 20", analysis['ex1'], "trend break", "Price below EMA 20")
            condition_checkbox("MACD Bearish Crossover", analysis['ex2'], "momentum", "MACD Bearish Crossover")
            condition_checkbox("RSI Overbought", analysis['ex3'], ">70", "RSI Overbought")
            condition_checkbox("Price at Upper Bollinger Band", analysis['ex4'], "extension", "Price at Upper Bollinger Band")
            condition_checkbox("Price near 20D Resistance", analysis['ex5'], "within 2%", "Price near 20D Resistance")

    with st.container(border=True):
        st.subheader("📊 Interactive Multi-Indicator Analysis")

        selected_indicators = st.multiselect(
            "Select indicators to overlay or view:",
            options=["EMAs (20, 50, 100, 200)", "Bollinger Bands", "Support/Resistance", "RSI", "MACD", "ADX"],
            default=["EMAs (20, 50, 100, 200)", "RSI"],
            help="Choose which overlays and oscillator panels to show in the combined technical chart."
        )

        fig_multi = build_multi_indicator_chart(data, selected_indicators, dark=is_dark_theme())
        st.plotly_chart(fig_multi, use_container_width=True)
