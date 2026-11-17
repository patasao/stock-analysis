import pandas as pd
import streamlit as st

from analysis_core import format_compact_number, format_percent, is_finite
from dashboard.charts import build_multi_indicator_chart, build_volatility_scale_figure
from dashboard.components import ENTRY_LEVEL_TONE, EXIT_LEVEL_TONE, condition_checkbox, quality_warnings, score_banner
from dashboard.data import SET_SECTOR_PROXY_STOCKS, get_analysis, get_fundamental_snapshot, get_market_regime, get_relative_strength, get_thai_market_context
from dashboard.help_text import TECH_HELP
from dashboard.theme import is_dark_theme


def _final_trade_action(technical_action, is_thai):
    if technical_action != "Buy":
        return technical_action, "The technical setup does not currently qualify as Buy."
    expected_market = "Thailand" if is_thai else "US"
    if st.session_state.get("regime_market", "US") != expected_market:
        return "Wait", f"Select {expected_market} in Market Regime Assessment so the market/sector review matches this ticker."

    required = {
        "rate_assessment": "Not reviewed",
        "economic_events": "Not reviewed",
        "earnings_window": "Not reviewed",
        "macro_risk": "Not reviewed",
        "rotation_catalyst": "Not reviewed",
    }
    if is_thai:
        required["thai_flows"] = "Not reviewed"
    missing = [key for key, default in required.items() if st.session_state.get(key, default) == default]
    if not st.session_state.get("company_catalyst", "").strip():
        missing.append("company catalyst review")
    if missing:
        return "Wait", "Complete the Market Regime Assessment and record the company catalyst before finalizing the trade."
    if st.session_state.get("macro_risk") == "High":
        return "No Trade", "Macro/geopolitical risk is marked High."
    if st.session_state.get("economic_events") == "High uncertainty" or st.session_state.get("earnings_window") == "High uncertainty":
        return "Wait", "Event timing or risk is uncertain; reassess before entry."
    if st.session_state.get("economic_events") == "Event within 7 days" or st.session_state.get("earnings_window") == "Earnings within 7 days":
        return "Wait", "A major event is within 7 days; reassess after the event or reduce event exposure."
    return "Buy", "Technical, relative-strength, sector, and manual event/catalyst reviews are complete."


def render(symbol, period, interval, ema_short, ema_long):
    if not symbol:
        return

    analysis = get_analysis(symbol, period, interval, ema_short, ema_long)
    if not analysis:
        st.error(f"Ticker '{symbol}' not found or data unavailable.")
        return

    data = analysis['df']
    currency = "฿" if symbol.upper().endswith(".BK") else "$"

    with st.container(border=True):
        st.subheader("Advanced Technical Indicators")

        t_col1, t_col2, t_col3, t_col4 = st.columns(4)
        rsi_status = "Overbought ⚠️" if analysis['rsi_val'] > 70 else "Oversold ⚠️" if analysis['rsi_val'] < 30 else "Neutral"
        atr_pct = (analysis['atr_val'] / analysis['curr_price'] * 100) if analysis['curr_price'] else 0.0
        t_col1.metric("RSI (14)", f"{analysis['rsi_val']:.2f}", rsi_status, help=TECH_HELP["RSI (14)"])
        t_col2.metric("Trend (EMA)", analysis['trend'], analysis['trend_detail'], help=TECH_HELP["Trend (EMA)"])
        t_col3.metric("Sentiment", analysis['sentiment'], analysis['sentiment_detail'], help=TECH_HELP["Sentiment"])
        t_col4.metric("ATR (14)", f"{currency}{analysis['atr_val']:,.2f}", f"{atr_pct:.1f}% of price", help=TECH_HELP["ATR (14)"])

        # Keyed by span so an adjustable Short/Long EMA that lands on 50, 100, or
        # 200 naturally dedupes against the fixed EMA card instead of showing
        # two identical cards.
        ema_by_span = {}
        ema_by_span[ema_short] = (f"EMA {ema_short}", analysis['ema_short_val'], TECH_HELP["EMA 20"])
        ema_by_span[ema_long] = (f"EMA {ema_long}", analysis['ema_long_val'], TECH_HELP["EMA 50"])
        ema_by_span.setdefault(50, ("EMA 50", analysis['ema_50_val'], TECH_HELP["EMA 50"]))
        ema_by_span.setdefault(100, ("EMA 100", analysis['ema_100_val'], TECH_HELP["EMA 100"]))
        ema_by_span.setdefault(200, ("EMA 200", analysis['ema_200_val'], TECH_HELP["EMA 200"]))

        ema_cols = st.columns(len(ema_by_span))
        for col, span in zip(ema_cols, sorted(ema_by_span)):
            label, value, help_text = ema_by_span[span]
            col.metric(label, f"{currency}{value:,.2f}", help=help_text)

        quality_warnings(analysis.get('quality_warnings', []))

    with st.container(border=True):
        st.subheader("Fundamentals, Relative Strength, and Market Regime")
        fund = get_fundamental_snapshot(symbol)
        rel_strength = get_relative_strength(symbol)
        is_thai = symbol.upper().endswith(".BK")
        regime = get_thai_market_context() if is_thai else get_market_regime()

        if "Error" in fund:
            st.warning(f"Fundamental data unavailable: {fund['Error']}")
        else:
            f1, f2, f3, f4, f5 = st.columns(5)
            f1.metric("Market Cap", format_compact_number(fund.get("Market Cap"), currency=currency), help=TECH_HELP["Market Cap"])
            f2.metric("Forward P/E", f"{fund.get('Forward P/E'):.2f}" if is_finite(fund.get("Forward P/E")) else "N/A", help=TECH_HELP["Forward P/E"])
            f3.metric("PEG", f"{fund.get('PEG'):.2f}" if is_finite(fund.get("PEG")) else "N/A", help=TECH_HELP["PEG"])
            f4.metric("Revenue Growth", format_percent(fund.get("Revenue Growth")), help=TECH_HELP["Revenue Growth"])
            f5.metric("Debt/Equity", f"{fund.get('Debt/Equity'):.1f}" if is_finite(fund.get("Debt/Equity")) else "N/A", help=TECH_HELP["Debt/Equity"])
            st.caption(f"Sector: {fund.get('Sector', 'N/A')} | Industry: {fund.get('Industry', 'N/A')}")

        r_cols = st.columns(4)
        if "Error" in rel_strength:
            r_cols[0].warning(f"Relative strength unavailable: {rel_strength['Error']}")
        else:
            keys = (["20D vs SET sector proxy", "50D vs SET sector proxy", "20D vs own sector basket", "50D vs own sector basket"]
                    if symbol.upper().endswith(".BK") else
                    ["20D vs SPY", "50D vs SPY", "100D vs SPY", "50D vs sector ETF"])
            for col, key in zip(r_cols, keys):
                value = rel_strength.get(key)
                col.metric(key, f"{value:+.1f}%" if is_finite(value) else "N/A", help=TECH_HELP["Relative Strength"])

        m_cols = st.columns(4)
        if "Error" in regime:
            m_cols[0].warning(f"Market regime unavailable: {regime['Error']}")
        elif is_thai:
            m_cols[0].metric("SET proxy regime", regime.get("Regime", "N/A"))
            m_cols[1].metric("SET proxy 20D", f"{regime['SET sector basket proxy 20D']:+.1f}%" if is_finite(regime.get("SET sector basket proxy 20D")) else "N/A")
            m_cols[2].metric("Breadth proxy", f"{regime['Breadth proxy (% above 50D)']:.1f}%" if is_finite(regime.get("Breadth proxy (% above 50D)")) else "N/A")
            m_cols[3].metric("Realized volatility", f"{regime['Realized volatility (annualized)']:.1f}%" if is_finite(regime.get("Realized volatility (annualized)")) else "N/A")
        else:
            m_cols[0].metric("Regime", regime.get("Regime", "N/A"), help=TECH_HELP["Regime"])
            m_cols[1].metric("SPY vs EMA200", f"{regime.get('SPY vs EMA200', 0.0):+.1f}%", help=TECH_HELP["SPY vs EMA200"])
            m_cols[2].metric("QQQ vs EMA200", f"{regime.get('QQQ vs EMA200', 0.0):+.1f}%", help=TECH_HELP["QQQ vs EMA200"])
            m_cols[3].metric("VIX", f"{regime.get('VIX'):.2f}" if is_finite(regime.get("VIX")) else "N/A", help=TECH_HELP["VIX"])

    with st.container(border=True):
        st.subheader("Trade Plan and Backtest Check")
        setup = analysis.get("setup_type", "No confirmed setup")
        st.caption(f"Setup: {setup} · Technical levels use the selected {interval} regular-session bars. Entry reference is the setup level/zone, not automatically the latest close. Verify catalyst and event risk in Market Regime Assessment before acting.")
        final_action, final_reason = _final_trade_action(analysis["entry_level"], is_thai)
        p1, p2, p3, p4, p5 = st.columns(5)
        confirmed_entry = is_finite(analysis.get("suggested_entry"))
        conditional_plan = not confirmed_entry and is_finite(analysis.get("watch_entry"))
        display_entry_value = analysis.get("suggested_entry") if confirmed_entry else analysis.get("watch_entry") if conditional_plan else None
        display_stop_value = analysis.get("stop_loss") if confirmed_entry else analysis.get("watch_stop") if conditional_plan else None
        display_tp1_value = analysis.get("tp1") if confirmed_entry else analysis.get("watch_tp1") if conditional_plan else None
        display_tp2_value = analysis.get("tp2") if confirmed_entry else analysis.get("watch_tp2") if conditional_plan else None
        display_rr1 = analysis.get("rr_tp1") if confirmed_entry else analysis.get("watch_rr_tp1") if conditional_plan else None
        display_rr2 = analysis.get("rr_tp2") if confirmed_entry else analysis.get("watch_rr_tp2") if conditional_plan else None
        entry_display = f"{currency}{display_entry_value:,.2f}" if is_finite(display_entry_value) else "N/A"
        stop_display = f"{currency}{display_stop_value:,.2f}" if is_finite(display_stop_value) else "N/A"
        rr1_display = f"{display_rr1:.2f}R" if is_finite(display_rr1) and is_finite(display_tp1_value) else "N/A"
        rr2_display = f"{display_rr2:.2f}R" if is_finite(display_rr2) and is_finite(display_tp2_value) else "N/A"
        rr_display = f"{rr1_display} / {rr2_display}" if rr1_display != "N/A" or rr2_display != "N/A" else "N/A"
        entry_label = "Setup Entry Reference" if confirmed_entry else "Conditional Entry Watch" if conditional_plan else "Setup Entry Reference"
        stop_label = "Technical Stop" if confirmed_entry else "Stop if Triggered" if conditional_plan else "Technical Stop"
        tp1_display = f"{currency}{display_tp1_value:,.2f}" if is_finite(display_tp1_value) else "N/A"
        tp2_display = f"{currency}{display_tp2_value:,.2f}" if is_finite(display_tp2_value) else "N/A"
        p1.metric(entry_label, entry_display, help="Pullback/retest: support or moving-average zone. Breakout: prior resistance after confirmation. Conditional watch levels require the stated price and volume confirmation before entry.")
        p2.metric(stop_label, stop_display, help=TECH_HELP["Stop"])
        p3.metric("TP1" + (" if triggered" if conditional_plan else ""), tp1_display, help="First overhead resistance or other identifiable technical target. If R/R is below 1.5R, the setup is not qualified.")
        p4.metric("TP2" + (" if triggered" if conditional_plan else ""), tp2_display, help="Next major overhead resistance, higher-timeframe level, or a labeled measured-move target. If unavailable or below 2R, the setup is not qualified.")
        p5.metric("R/R (TP1 / TP2)", rr_display, help=TECH_HELP["Reward/Risk"])
        st.write(f"**Technical action: {analysis['entry_level']} · Final action: {final_action}.** {final_reason}")
        if confirmed_entry:
            st.caption("Trade management: if the technical stop trades, exit and do not widen it. After TP1, consider tightening the stop toward breakeven based on price action; TP2 is the next technical target.")
        elif conditional_plan:
            st.caption(f"Conditional watch plan only — not a confirmed entry. {analysis.get('watch_condition', '')} The current action remains Wait until the setup confirms and the TP1/TP2 reward-to-risk rules are met.")
        else:
            st.caption("No confirmed setup or nearby constructive support zone. Prices remain N/A until a pullback, breakout, or retest meets its confirmation rules; the latest close is not used as an entry.")
        if is_thai:
            ticker = symbol.upper().removesuffix(".BK")
            proxy_sector = next((name for name, names in SET_SECTOR_PROXY_STOCKS.items() if ticker in names), None)
            if proxy_sector:
                sector_name = proxy_sector
            elif "Error" not in fund:
                sector_name = f"{fund.get('Industry') or fund.get('Sector') or 'Not available'} (verify SET group)"
            else:
                sector_name = "Not available; verify SET group"
        else:
            sector_name = fund.get("Sector", "N/A") if "Error" not in fund else "N/A"
        company = fund.get("Name") if "Error" not in fund else None
        catalyst_note = st.session_state.get("company_catalyst", "").strip() or "Not reviewed"
        risk_note = "Price reaching the technical stop invalidates the setup; verify liquidity, overhead resistance, and event risk."
        plan = pd.DataFrame([
            ("Stock", f"{symbol} / {company}" if company else symbol),
            ("Sector", sector_name),
            ("Setup", f"{setup} / {analysis.get('watch_setup_type')} (conditional)" if conditional_plan else setup),
            ("Entry", entry_display + (" (conditional; wait for confirmation)" if conditional_plan else "")),
            ("Stop Loss", stop_display),
            ("TP1", tp1_display),
            ("TP2", tp2_display + (" (measured move)" if analysis.get("tp2_measured_move") else "")),
            ("R/R", rr_display),
            ("Catalyst", catalyst_note),
            ("Risk", risk_note),
            ("Action", final_action),
        ], columns=["Item", "Plan"])
        st.dataframe(plan, use_container_width=True, hide_index=True)

        bt = analysis.get("backtest", {})
        if bt.get("entry_count", 0) == 0:
            st.info(bt.get("message", "No backtest entries available."))
        else:
            st.caption("Backtest includes technical setup, stop/target, volume, and historical broad-market/sector relative-strength checks. Company catalysts and event risk are reviewed manually and cannot be backtested from this data feed.")
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Backtest Entries", bt["entry_count"], help=TECH_HELP["Backtest Entries"])
            b2.metric("20D Win Rate", f"{bt['win_rate_20d']:.1f}%", help=TECH_HELP["20D Win Rate"])
            b3.metric("Avg 20D Return", f"{bt['avg_return_20d']:+.2f}%", help=TECH_HELP["Avg 20D Return"])
            b4.metric("Worst 20D Adverse", f"{bt['worst_adverse_20d']:.2f}%", help=TECH_HELP["Worst 20D Adverse"])
            b5, b6, b7 = st.columns(3)
            b5.metric("20D Stop Hit Rate", f"{bt['stop_hit_rate_20d']:.1f}%")
            b6.metric("20D TP1 Hit Rate", f"{bt['tp1_hit_rate_20d']:.1f}%")
            b7.metric("20D TP2 Hit Rate", f"{bt['tp2_hit_rate_20d']:.1f}%")
            with st.expander("Backtest by setup type"):
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
                **The Goal:** Rank setups using price structure, support, relative strength inputs, volume confirmation, trend and momentum. Market regime and sector strength add context; event risk must be reviewed separately. This score is not a prediction.
                """)

            score_banner(
                "Buy Candidate" if analysis['entry_level'] == "Buy" else analysis['entry_level'],
                analysis['pos_size'],
                ENTRY_LEVEL_TONE.get(analysis['entry_level'], "neutral"),
            )

            st.write("")
            st.write(f"**Setup checks:** {analysis['core_score']}/5 · **Trend/momentum/relative-strength checks:** {analysis['supp_score']}/9")
            if analysis['risk_fail_rsi']: st.error("Risk: RSI extended (>75); wait for a better entry.")
            if analysis['risk_fail_ema20']: st.error("Risk: Price extended more than 10% above short EMA; avoid chasing.")
            if analysis['wide_candle']: st.error("Risk: Today's high-low range exceeds 2 ATR; wait for a tighter setup and efficient stop.")

            with st.expander("🔍 View Checklist Details"):
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    st.write("**Core Conditions**")
                    condition_checkbox("Improving price structure", analysis['c1'], analysis['trend_detail'], "Trend (EMA)")
                    condition_checkbox("Holding meaningful support", analysis['c2'], f"support {currency}{analysis['sup_val']:,.2f}", "Support")
                    condition_checkbox("Momentum improving", analysis['c3'], f"RSI {analysis['rsi_val']:.1f}", "RSI (14)")
                    condition_checkbox("Volume appropriate for setup", analysis['c4'], f"{analysis['vol_ratio']:.2f}x average", "Volume Setup")
                    condition_checkbox("Trend confirmation", analysis['c5'], f"EMA{ema_short}/${ema_long}", "Trend (EMA)")

                with c_col2:
                    st.write("**Supporting Conditions**")
                    condition_checkbox(f"Above EMA{ema_long}", analysis['s1'], f"price > EMA{ema_long}", "Trend (EMA)")
                    condition_checkbox("Above EMA100", analysis['s2'], "price > EMA100", "Trend (EMA)")
                    condition_checkbox("Meaningful trend (ADX)", analysis['s3'], f"{analysis['adx_val']:.1f}", "ADX > 20")
                    condition_checkbox("Above Bollinger middle", analysis['s4'], "trend support", "Above BB Middle")
                    condition_checkbox("Healthy RSI range", analysis['s5'], f"{analysis['rsi_val']:.1f}", "RSI (14)")
                    condition_checkbox("Volume confirms setup", analysis['s6'], f"{analysis['vol_ratio']:.2f}x", "Volume Setup")
                    condition_checkbox("Above EMA200", analysis['s7'], "long-term trend", "Trend (EMA)")
                    condition_checkbox("Outperforming broad market", analysis['s8'], f"50D RS {analysis['rs_market_50']:+.2f}pp" if is_finite(analysis['rs_market_50']) else "RS unavailable", "Relative Strength")
                    condition_checkbox("Outperforming own sector", analysis['s9'], f"50D RS {analysis['rs_sector_50']:+.2f}pp" if is_finite(analysis['rs_sector_50']) else "sector RS unavailable", "Relative Strength")

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
            st.write(f"**Exit / review conditions:** {analysis['exit_score']}/5")
            condition_checkbox("Price below EMA20 and EMA50", analysis['ex1'], "trend deterioration", "Trend (EMA)")
            condition_checkbox("MACD bearish", analysis['ex2'], "momentum weakening", "MACD > Signal")
            condition_checkbox("RSI excessively extended", analysis['ex3'], ">75", "RSI (14)")
            condition_checkbox("Price at upper Bollinger Band", analysis['ex4'], "extension", "Above BB Middle")
            stop_value = f"stop {currency}{analysis['stop_loss']:,.2f}" if is_finite(analysis.get("stop_loss")) else "no active setup stop"
            condition_checkbox("Technical stop traded", analysis['ex5'], stop_value, "Stop")

    with st.container(border=True):
        st.subheader("📊 Interactive Multi-Indicator Analysis")

        selected_indicators = st.multiselect(
            "Select indicators to overlay or view:",
            options=["EMAs (20, 50, 100, 200)", "Bollinger Bands", "Support/Resistance", "RSI", "MACD", "ADX", "ATR"],
            default=["EMAs (20, 50, 100, 200)", "RSI", "MACD"],
            help="Choose which overlays and oscillator panels to show in the combined technical chart."
        )

        fig_multi = build_multi_indicator_chart(data, selected_indicators, ema_short=ema_short, ema_long=ema_long, dark=is_dark_theme(), currency="THB" if is_thai else "USD")
        st.plotly_chart(fig_multi, use_container_width=True)
