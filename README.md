# 📈 Stock Insight Dashboard

A professional-grade financial analysis web application built with **Streamlit** and **Python**. This dashboard provides real-time market data, advanced technical indicators, and a specialized custom trading strategy simulator.

## 🚀 Live Demo
[View Live App](https://ps-stock-analysis.streamlit.app/)

## ✨ Features
*   **Real-Time Data:** Powered by `yfinance` for up-to-the-minute stock and crypto price action.
*   **Advanced Technical Indicators:** 
    *   **Trend:** Exponential Moving Averages (EMA 20 & 50) with **Trend KPI cards** (Uptrend/Downtrend).
    *   **Momentum:** Relative Strength Index (RSI 14) and MACD (Moving Average Convergence Divergence) with **integrated strategy guides** and **Sentiment KPIs**.
    *   **Volatility:** ATR-based entry limits.
    *   **Structure:** 20-Day Support and Resistance discovery.
*   **Interactive Visualizations:** High-fidelity Candlestick and technical charts using `Plotly`.
*   **Educational Integration:** In-app strategy guides and tooltips explaining RSI, MACD, Trading Entry Rules, and EMA targets.
*   **Performance Optimized:** Integrated `@st.cache_data` for data fetching and responsive UI.
*   **Trading Entry Rules (Composite Strategy):** A sophisticated rule-based engine that evaluates stock setups using a 12-point scoring system (Core & Supporting conditions). Features include:
    *   **Automated Scoring:** Real-time calculation of entry strength (A+, A, B, C, or Avoid).
    *   **Position Sizing:** Integrated guidance based on setup quality.
    *   **Risk Management:** Automated "Risk Fails" for overbought conditions or extended prices.
*   **Recommend Stocks:** An automated scanner that identifies top-performing stocks from the **S&P 500** with **industry/sector filtering**. Includes:
    *   **Interactive Slicers:** Real-time filters for **Volume Ratio**, **RSI**, and **52W High %** proximity.
    *   **Momentum Defaults:** Pre-configured high-probability scanning criteria (Vol > 1.5x, RSI 30-70, 52W High > -5%).
    *   **Opportunity Gallery:** Visual card-based layout for high-impact analysis.
    *   **Performance Matrix:** Simultaneous display of **5D, 1M, and 1Y** returns on every card.
    *   **Interactive Sorting:** Rank performers by performance timeframes (5D, 1M, 1Y).
    *   **Strategic Buy Targets:** Integrated **EMA 20, 50, and 100** targets with **dynamic visual cues** (✅ for active dips).

## 🛠️ Local Setup

Follow these steps to run the dashboard locally:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/stock-analysis.git
   cd stock-analysis
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

## 📋 Requirements
The core libraries used in this project are:
*   `streamlit` - Web framework
*   `yfinance` - Financial data API
*   `pandas` - Data manipulation
*   `plotly` - Interactive charts
*   `lxml` - For scraping Wikipedia tables

## 📊 Strategy Logic: Composite Entry System
The dashboard utilizes a multi-factor model to rank stock opportunities, organized into three tabs:
1.  **Overview:** Real-time metrics and price action chart.
2.  **Technicals:** Detailed RSI, MACD, and **Trading Entry Scoring System**.
3.  **Recommend Stocks:** Automated high-conviction momentum scanner.

### Scoring Criteria
*   **Core Conditions (5):** Focused on drawdown (>= 8% from 10D high), EMA20 alignment, RSI stability (42-58), volume expansion (>= 1.6x), and MACD crossovers.
*   **Supporting Conditions (7):** Includes trend alignment (EMA50/100), relative strength (52W high proximity), ADX strength, and volatility bands (Bollinger).

### Risk Management
*   **Hard Overrides:** Automatic "Avoid" signal if RSI > 68 or price is > 8% above EMA 20.
*   **Safety Standards:** Mandatory stop-loss guidance (-8% to -10%) and position capping (15% per stock).

## ⚠️ Disclaimer
This analysis represents a personal trading strategy and does not constitute financial advice. Investment involves risk; please conduct your own due diligence before committing capital.

## 🤖 AI Collaboration
Developed with the support of **Gemini (Google AI)** to optimize performance, refine the UI/UX, and ensure robust error handling.
