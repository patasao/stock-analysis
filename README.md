# Stock Insight Dashboard

A Streamlit dashboard for technical stock screening, setup scoring, market-regime and sector assessment, and watchlist comparison.

## Features

- Real-time OHLCV data through `yfinance`.
- Candlestick charts with EMA (20/50/100/200 by default, dropdown-selectable), Bollinger Bands, support/resistance, RSI, MACD, and ADX overlays.
- Wilder-style RSI, ATR, and ADX calculations.
- Shared rule engine for single-stock analysis, multi-stock comparison, tests, and historical checks.
- Setup scoring outputs Buy Candidate / Wait / Avoid from price structure, pullback/breakout/retest confirmation, volume, moving-average trend, momentum, and relative strength versus the broad market and own-sector proxy.
- Final trade action stays at Wait until event risk and catalyst review is completed; this data feed does not provide dependable event calendars.
- Exit review based on technical invalidation at support, EMA structure, MACD deterioration, and extension.
- Data-quality warnings for stale bars, missing OHLCV data, short history, and unreliable volume.
- Fundamentals and valuation snapshot: market cap, P/E, PEG, revenue growth, debt/equity, sector, and industry.
- US relative strength versus SPY and the stock's sector ETF; Thai relative strength versus SET stock-basket and own-sector proxies.
- US market-regime assessment using index trends, a breadth proxy, VIX, and 10-year Treasury yield. Thai market context uses SET stock-basket trend, constituent-basket breadth, and realized volatility proxies.
- Trade plan shows confirmed setup levels when rules trigger and a separately labeled conditional pullback watch plan when structure is constructive; it never substitutes the latest close for an entry, and Buy qualification still requires identifiable targets meeting the 1.5R/2R rules.
- Historical check of Buy setups showing 20D return, adverse move, stop-hit rate, and target-hit rates.
- Sector screening across all 11 US S&P 500 sectors and major SET groups.
- Color-coded technical setup and exit signals, adapting to the active light/dark theme.

## Layout

All configuration (ticker, period, interval, Short/Long EMA Span) lives in one control bar at the top of the page — there is no sidebar. EMA spans are dropdown selects with common periods (5–50 for Short, 20–200 for Long); a fixed EMA 50 always appears too, even if the Long EMA Span dropdown is set elsewhere. Below the config bar, four tabs cover the workflow:

- **📊 Overview** — price snapshot, entry/exit signal at a glance, price chart.
- **🔍 Technicals** — full indicator/fundamentals/trade-plan/backtest breakdown, buy/sell score checklists, and an interactive multi-indicator chart (defaults to EMAs, RSI, and MACD).
- **📋 Multi-Stock Analysis** — side-by-side comparison table for a custom ticker list.
- **🌐 Market Regime Assessment** — major index trend, breadth proxy, volatility, rates, sector rotation, sector screening, and manual event-risk review.

The default theme is light (`.streamlit/config.toml`); charts and score colors adapt automatically if you switch to Streamlit's dark theme from the settings menu.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
.venv\Scripts\python.exe -m unittest test_analysis_core.py
```

## Project Structure

- `app.py` - Thin entrypoint: page config, top configuration bar, tab layout.
- `analysis_core.py` - Pure indicator, scoring, risk, data-quality, and backtest logic (fully unit-tested, no Streamlit dependency).
- `test_analysis_core.py` - Unit tests for the reusable analysis engine.
- `requirements.txt` - Python dependencies.
- `.streamlit/config.toml` - Native theme configuration.
- `dashboard/` - Streamlit UI layer, split by responsibility:
  - `config_bar.py` - Renders the top configuration bar (symbol, period, interval, EMA span dropdowns).
  - `data.py` - All `yfinance`-backed fetchers (cached) plus `get_analysis()`, which composes `analysis_core` into a single result dict.
  - `charts.py` - Plotly figure builders (candlestick, multi-indicator, volatility scale). No Streamlit dependency, theme-aware via a `dark` flag.
  - `theme.py` - Detects the active Streamlit light/dark theme for chart styling.
  - `components.py` - Shared UI pieces: the color-coded score banner, condition checklist, and tone-to-color maps.
  - `help_text.py` - Tooltip copy shown throughout the app.
  - `tab_overview.py`, `tab_technicals.py`, `tab_multi_stock.py`, `tab_market_regime.py` - One `render()` per tab.

## Strategy Notes

The scoring model is rule-based. It should be treated as a decision-support tool, not a trading recommendation. The backtest summary is intentionally simple and should be expanded before using the strategy with real capital.

Important limitations:

- Yahoo Finance data can be delayed, incomplete, or unavailable. OHLC prices are requested without dividend/split adjustment so plan prices reflect quoted regular-session bars.
- The breadth figure is an index-level proxy, not the percentage of individual stocks above their moving averages.
- Thai sector trends use equally weighted baskets of selected liquid stocks because Yahoo Finance does not provide reliable historical sector-index series; basket returns are proxies rather than official SET sector-index returns.
- Economic, earnings, and geopolitical calendars are not supplied automatically; review event dates and risks manually. The final action remains Wait until this review and a catalyst note are entered.
- Technical signals should be validated against fundamentals, liquidity, events, and position-level risk.
- Backtest stop and target hit rates compare future highs/lows independently; they do not model execution order, costs, or slippage.

## Disclaimer

This project is for education and research only. It is not financial advice.
