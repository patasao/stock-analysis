# Stock Insight Dashboard

A Streamlit dashboard for technical stock screening, strategy scoring, market-context checks, and watchlist comparison.

## Features

- Real-time OHLCV data through `yfinance`.
- Candlestick charts with EMA (20/50/100/200), Bollinger Bands, support/resistance, RSI, MACD, and ADX overlays.
- Wilder-style RSI, ATR, and ADX calculations.
- Shared rule engine for single-stock analysis, multi-stock comparison, S&P 500 scanning, tests, and backtest checks.
- Entry scoring with core and supporting technical conditions.
- Exit scoring based on EMA trend break, MACD weakness, RSI extension, Bollinger extension, and resistance proximity.
- Data-quality warnings for stale bars, missing OHLCV data, short history, and unreliable volume.
- Fundamentals and valuation snapshot: market cap, P/E, PEG, revenue growth, debt/equity, sector, and industry.
- Relative strength versus SPY and QQQ over 20D, 50D, 100D, and 200D windows.
- Market-regime check using SPY/QQQ EMA200 status and VIX.
- Risk/reward trade plan with suggested entry, stop, target, risk per share, and reward/risk ratio.
- Simple historical signal check showing non-Avoid entries, 20D win rate, average return, and worst adverse move.
- S&P 500 scanner with an explicit survivorship-bias warning.
- Consistent color-coded Buying/Selling Score badges across every tab, adapting to the active light/dark theme.

## Layout

All configuration (ticker, period, interval, EMA spans) lives in one control bar at the top of the page — there is no sidebar. Below it, four tabs cover the workflow:

- **📊 Overview** — price snapshot, entry/exit signal at a glance, price chart.
- **🔍 Technicals** — full indicator/fundamentals/trade-plan/backtest breakdown, buy/sell score checklists, and an interactive multi-indicator chart.
- **📋 Multi-Stock Analysis** — side-by-side comparison table for a custom ticker list.
- **🚀 High Growth Stocks** — S&P 500 growth scanner with core-condition filters.

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
  - `config_bar.py` - Renders the top configuration bar (symbol, period, interval, EMA spans).
  - `data.py` - All `yfinance`-backed fetchers (cached) plus `get_analysis()`, which composes `analysis_core` into a single result dict.
  - `charts.py` - Plotly figure builders (candlestick, multi-indicator, volatility scale). No Streamlit dependency, theme-aware via a `dark` flag.
  - `theme.py` - Detects the active Streamlit light/dark theme for chart styling.
  - `components.py` - Shared UI pieces: the color-coded score banner, condition checklist, and tone-to-color maps.
  - `help_text.py` - Tooltip copy shown throughout the app.
  - `tab_overview.py`, `tab_technicals.py`, `tab_multi_stock.py`, `tab_growth_scanner.py` - One `render()` per tab.

## Strategy Notes

The scoring model is rule-based. It should be treated as a decision-support tool, not a trading recommendation. The backtest summary is intentionally simple and should be expanded before using the strategy with real capital.

Important limitations:

- Yahoo Finance data can be delayed, adjusted, incomplete, or unavailable.
- The S&P 500 scanner uses the current index membership list, so it is suitable for current screening but not historical backtesting.
- Technical signals should be validated against fundamentals, market regime, liquidity, earnings dates, and position-level risk.

## Disclaimer

This project is for education and research only. It is not financial advice.
