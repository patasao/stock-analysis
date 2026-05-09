# 📈 Stock Insight Dashboard

A professional-grade financial analysis web application built with **Streamlit** and **Python**. This dashboard provides real-time market data, technical indicators, and a specialized custom trading strategy simulator.

## 🚀 Live Demo
[View Live App](https://ps-stock-analysis.streamlit.app/)

## ✨ Features
*   **Real-Time Data:** Powered by `yfinance` for up-to-the-minute stock and crypto price action.
*   **Technical Indicators:** 
    *   Exponential Moving Averages (EMA 20 & 50) for trend identification.
    *   ATR-based volatility bands.
    *   20-Day Support and Resistance discovery.
*   **Interactive Charts:** High-fidelity Candlestick and Trendline charts using `Plotly`.
*   **PS's Analysis:** A proprietary trading module that calculates custom entry limits and simulates "New Average Cost" for portfolio scaling.

## 📋 Requirements
The following libraries are required to run the dashboard:
*   `streamlit`
*   `yfinance`
*   `pandas`
*   `plotly`

## 📊 Strategy Logic: PS's Analysis
The dashboard includes a specialized section for personal strategy evaluation:
*   **Limit I:** Mid-point between current price and the day's low.
*   **Limit II:** Volatility-adjusted entry based on the prior day's price spread.
*   **Limit III:** Fixed 5% retracement from the previous close.
*   **Cost Averaging:** Dynamic calculation of your new position basis when scaling into a trade.

## ⚠️ Disclaimer
This analysis represents a personal trading strategy and does not constitute financial advice. Investment involves risk; please conduct your own due diligence before committing capital.

## 🤖 AI
Gemini
---