# Stock Insight Dashboard

A Streamlit dashboard for technical stock screening, strategy scoring, market-context checks, and watchlist comparison.

## Features

- Real-time OHLCV data through `yfinance`.
- Candlestick charts with EMA, Bollinger Bands, support/resistance, RSI, MACD, and ADX overlays.
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

- `app.py` - Streamlit user interface and data-fetching integration.
- `analysis_core.py` - Pure indicator, scoring, risk, data-quality, and backtest logic.
- `test_analysis_core.py` - Unit tests for the reusable analysis engine.
- `requirements.txt` - Python dependencies.

## Strategy Notes

The scoring model is rule-based. It should be treated as a decision-support tool, not a trading recommendation. The backtest summary is intentionally simple and should be expanded before using the strategy with real capital.

Important limitations:

- Yahoo Finance data can be delayed, adjusted, incomplete, or unavailable.
- The S&P 500 scanner uses the current index membership list, so it is suitable for current screening but not historical backtesting.
- Technical signals should be validated against fundamentals, market regime, liquidity, earnings dates, and position-level risk.

## Disclaimer

This project is for education and research only. It is not financial advice.
