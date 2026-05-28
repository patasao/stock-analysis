---
name: stock-analysis
description: Analyzes stocks using PS Strategy (Intraday Drawdown), RSI, MACD, and EMAs. Use when evaluating entry points, identifying market momentum, or calculating cost-averaging scenarios.
---

# Stock Analysis Skill

This skill provides specialized procedural knowledge for analyzing stock price action and identifying efficient entry points based on the "PS Strategy".

## Core Strategy: PS Analysis

### PS Limit Buy I
Calculated based on the 20-day Average Intraday Drawdown.
- **Formula:** `Current Price * (1 + 20D Avg Intraday Drawdown %)`
- **Data Source:** Requires 20 days of OHLC data to calculate average `(Low - Open) / Open`.

### PS Limit Buy II
- **Formula:** `PS Limit Buy I * 0.97`
- **Strategic Intent:** Provides a 3% conservative safety buffer below the primary entry target.

## Technical Indicators

### RSI (Relative Strength Index)
- **Overbought (>70):** Indicates potential overvaluation; expect pullbacks.
- **Oversold (<30):** Indicates potential undervaluation; expect recovery.
- **Centerline (50):** Momentum filter. Above 50 is bullish; below 50 is bearish.

### MACD (Moving Average Convergence Divergence)
- **Signal Line Crossover:** Bullish when MACD crosses above Signal; Bearish when below.
- **Zero Line:** Indicates broad trend strength.
- **Histogram:** Visualizes momentum expansion/contraction.

## Workflow Integration
When asked to analyze a stock or suggest entry points:
1. Fetch historical data (minimum 50 days for EMA/MACD/RSI).
2. Calculate the 20-day Average Intraday Drawdown.
3. Apply the PS Limit formulas.
4. Cross-reference with RSI/MACD levels for confirmation.
