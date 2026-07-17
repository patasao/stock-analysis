import pandas as pd
import streamlit as st
import yfinance as yf

from analysis_core import (
    calculate_indicators,
    evaluate_strategy_row,
    inspect_data_quality,
    summarize_backtest,
)


@st.cache_data(ttl=3600)  # Cache data for 1 hour
def fetch_stock_data(symbol, period="1y", interval="1d"):
    try:
        data = yf.download(symbol, period=period, interval=interval)
        if data.empty:
            return None

        # Handle yfinance MultiIndex columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        return data
    except Exception:
        return None


def get_analysis(symbol, period, interval, ema_short, ema_long):
    data = fetch_stock_data(symbol, period, interval)
    if data is None or len(data) < 2:
        return None

    data = calculate_indicators(data, ema_short, ema_long)
    analysis = evaluate_strategy_row(data)
    analysis["df"] = data
    analysis["quality_warnings"] = inspect_data_quality(data, symbol)
    analysis["backtest"] = summarize_backtest(data)
    return analysis


@st.cache_data(ttl=86400)
def get_fundamental_snapshot(symbol):
    try:
        info = yf.Ticker(symbol).get_info()
        return {
            "Market Cap": info.get("marketCap"),
            "Trailing P/E": info.get("trailingPE"),
            "Forward P/E": info.get("forwardPE"),
            "PEG": info.get("pegRatio"),
            "Revenue Growth": info.get("revenueGrowth"),
            "Earnings Growth": info.get("earningsGrowth"),
            "Gross Margin": info.get("grossMargins"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Debt/Equity": info.get("debtToEquity"),
            "ROE": info.get("returnOnEquity"),
            "Sector": info.get("sector"),
            "Industry": info.get("industry"),
        }
    except Exception as exc:
        return {"Error": str(exc)}


@st.cache_data(ttl=3600)
def get_relative_strength(symbol, period="1y"):
    benchmarks = ["SPY", "QQQ"]
    try:
        data = yf.download([symbol] + benchmarks, period=period, interval="1d", progress=False)
        close = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
        results = {}
        for days in [20, 50, 100, 200]:
            if len(close) <= days or symbol not in close:
                continue
            stock_ret = (close[symbol].iloc[-1] / close[symbol].iloc[-days - 1] - 1) * 100
            for benchmark in benchmarks:
                if benchmark in close:
                    bench_ret = (close[benchmark].iloc[-1] / close[benchmark].iloc[-days - 1] - 1) * 100
                    results[f"{days}D vs {benchmark}"] = float(stock_ret - bench_ret)
        return results
    except Exception as exc:
        return {"Error": str(exc)}


@st.cache_data(ttl=3600)
def get_market_regime():
    try:
        data = yf.download(["SPY", "QQQ", "^VIX"], period="1y", interval="1d", progress=False)
        close = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
        spy = close["SPY"].dropna()
        qqq = close["QQQ"].dropna()
        vix = close["^VIX"].dropna()
        spy_ema200 = spy.ewm(span=200, adjust=False).mean().iloc[-1]
        qqq_ema200 = qqq.ewm(span=200, adjust=False).mean().iloc[-1]
        regime = "Risk-On" if spy.iloc[-1] > spy_ema200 and qqq.iloc[-1] > qqq_ema200 else "Risk-Off / Defensive"
        return {
            "Regime": regime,
            "SPY vs EMA200": float((spy.iloc[-1] / spy_ema200 - 1) * 100),
            "QQQ vs EMA200": float((qqq.iloc[-1] / qqq_ema200 - 1) * 100),
            "VIX": float(vix.iloc[-1]) if len(vix) else None,
        }
    except Exception as exc:
        return {"Error": str(exc)}


@st.cache_data(ttl=86400)
def get_sp500_tickers():
    try:
        tables = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = tables[0]
        tickers = df['Symbol'].tolist()
        tickers = [t.replace('.', '-') for t in tickers]
        return tickers
    except Exception:
        return [
            "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK-B", "LLY", "AVGO", "JPM",
            "TSLA", "V", "UNH", "XOM", "MA", "HD", "PG", "COST", "JNJ", "ABBV",
            "BAC", "MRK", "AMD", "ADBE", "CRM", "NFLX", "CVX", "WMT", "TMO", "PEP",
            "DIS", "KO", "ACN", "INTC", "ORCL", "CSCO", "MCD", "WFC", "XOM", "TXN",
        ]


@st.cache_data(ttl=3600)
def load_and_analyze_sp500(tickers):
    data = yf.download(tickers, period="2y", interval="1d", group_by="column")
    results = []
    for ticker in tickers:
        try:
            # Extract ticker data
            ticker_df = pd.DataFrame()
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in data.columns and ticker in data[col].columns:
                    ticker_df[col] = data[col][ticker]

            if len(ticker_df) < 200:
                continue

            ticker_df = ticker_df.dropna(subset=['Close'])
            if len(ticker_df) < 150:
                continue

            df_ind = calculate_indicators(ticker_df)

            def get_growth(days):
                if len(df_ind) <= days:
                    return 0.0
                c_curr = df_ind['Close'].iloc[-1]
                c_prev = df_ind['Close'].iloc[-days - 1]
                if pd.isna(c_curr) or pd.isna(c_prev) or c_prev == 0:
                    return 0.0
                return float((c_curr - c_prev) / c_prev * 100)

            g_20 = get_growth(20)
            g_50 = get_growth(50)
            g_100 = get_growth(100)
            g_200 = get_growth(200)

            signal = evaluate_strategy_row(df_ind)

            results.append({
                "ticker": ticker,
                "curr_price": signal['curr_price'],
                "growth_20d": g_20,
                "growth_50d": g_50,
                "growth_100d": g_100,
                "growth_200d": g_200,
                "ema20": signal['ema_short_val'],
                "ema50": signal['ema_long_val'],
                "ema100": signal['ema_100_val'],
                "ema200": signal['ema_200_val'],
                "core_score": signal['core_score'],
                "supp_score": signal['supp_score'],
                "total_score": signal['core_score'] + signal['supp_score'],
                "entry_level": signal['entry_level'],
                "pos_size": signal['pos_size'],
                "c1": signal['c1'], "c2": signal['c2'], "c3": signal['c3'], "c4": signal['c4'], "c5": signal['c5'],
                "drawdown_10d": signal['drawdown_10d'],
                "ema20_dist": signal['ema20_dist'],
                "rsi_val": signal['rsi_val'],
                "vol_ratio": signal['vol_ratio'],
                "macd_val": signal['macd_val'],
                "signal_val": signal['signal_val'],
            })
        except Exception:
            continue
    return results
