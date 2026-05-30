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
*   **Performance Optimized:** Integrated `@st.cache_data` for efficient data fetching and responsive UI.
*   **PS's Analysis:** A proprietary trading module that calculates custom entry limits and simulates "New Average Cost" for portfolio scaling.
*   **Recommend Stocks:** An automated scanner that identifies top-performing stocks from the **S&P 500** with **industry/sector filtering**. Includes:
    *   **Opportunity Gallery:** Visual card-based layout for high-impact analysis.
    *   **Performance Matrix:** Simultaneous display of **5D, 1M, and 1Y** returns on every card.
    *   **Technical Metrics:** RSI, Volume Ratio, and Distance to 52-Week High.
    *   **Interactive Sorting:** Rank performers by performance (5D, 1M, 1Y) or technical factors (RSI, Volume).
    *   **Strategic Buy Targets:** Integrated PS Strategy + EMA targets with **dynamic visual cues** (✅ for active dips).

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

## 📊 Strategy Logic: PS's Analysis
The dashboard includes a specialized section for personal strategy evaluation, organized into four tabs:
1.  **Overview:** Real-time metrics and price action chart.
2.  **Technicals:** Detailed RSI and MACD analysis with **Live KPI Cards** and warning signs (⚠️).
3.  **PS's Analysis:** Strategy-based entry targets and cost-averaging simulator.
4.  **Recommend Stocks:** Automated top 10 performance scanner using the **S&P 500** dataset. Features include:
    *   **Visual Cards:** Grid-based layout replacing flat tables for better scanning.
    *   **Comprehensive Performance:** 5D, 1M, and 1Y deltas shown for every stock.
    *   **Advanced Indicators:** Includes Volume Ratio (>1x indicates high interest) and 52W High % (proximity to yearly peaks).
    *   **Industry Filtering:** Drill down into specific sectors (e.g., Tech, Health Care, Energy).
    *   **Strategic Buy Targets:** Integrated targets with **dynamic visual cues**.


### Entry Targets
*   **PS Limit I:** Current Price adjusted by the 20-day Average Intraday Drawdown percentage.
*   **PS Limit II:** A 3% reduction from PS Limit I.
*   **ATR/EMA Targets:** Includes EMA 20, ATR Limit II (EMA 20 - 0.5 * ATR), and ATR Limit III (EMA 20 - 1.0 * ATR).

### Cost Averaging Simulator
Dynamic calculation of your new position basis with real-time feedback:
*   **Tooltips:** Detailed calculation methods visible on hover (i).
*   **Trend Indicators:** Visual cues (🟢 ↓ or 🔴 ↑) showing if the new average is better or worse than your current cost.

$$NewAvg = \frac{(CurrentAvg \times CurrentQty) + (LimitPrice \times PurchaseQty)}{CurrentQty + PurchaseQty}$$

## ⚠️ Disclaimer
This analysis represents a personal trading strategy and does not constitute financial advice. Investment involves risk; please conduct your own due diligence before committing capital.

## 🤖 AI Collaboration
Developed with the support of **Gemini (Google AI)** to optimize performance, refine the UI/UX, and ensure robust error handling.
