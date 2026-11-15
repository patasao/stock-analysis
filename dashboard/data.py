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
        data = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
        if data.empty:
            return None

        # Handle yfinance MultiIndex columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Drop a trailing placeholder row for a day that hasn't traded yet
        # (all-NaN OHLC), so the latest row always reflects the last fully
        # completed session instead of surfacing as a data-quality warning.
        ohlc_cols = [c for c in ['Open', 'High', 'Low', 'Close'] if c in data.columns]
        while len(data) and ohlc_cols and data[ohlc_cols].iloc[-1].isna().all():
            data = data.iloc[:-1]

        if data.empty:
            return None

        return data
    except Exception:
        return None


def get_analysis(symbol, period, interval, ema_short, ema_long):
    chart_data = fetch_stock_data(symbol, period, interval)
    warmup_data = fetch_stock_data(symbol, "5y", interval)
    if chart_data is None or len(chart_data) < 2:
        return None
    if warmup_data is None:
        warmup_data = chart_data
    # Preserve enough earlier bars for long moving averages, RSI/ADX, and
    # relative-strength lookbacks even when the user selects a short chart.
    data = pd.concat([warmup_data, chart_data]).sort_index()
    data = data[~data.index.duplicated(keep="last")]

    benchmark_data = get_relative_benchmark_history(symbol)
    if not benchmark_data.empty:
        for column in ["Benchmark_Market_Close", "Benchmark_Sector_Close"]:
            if column in benchmark_data:
                data[column] = benchmark_data[column].reindex(data.index, method="ffill")
    data = calculate_indicators(data, ema_short, ema_long)
    analysis = evaluate_strategy_row(data)
    analysis["df"] = data.reindex(chart_data.index)
    analysis["quality_warnings"] = inspect_data_quality(data, symbol)
    # Backtests always use daily regular-session bars, regardless of the
    # presentation interval selected for the technical chart.
    daily_data = fetch_stock_data(symbol, "5y", "1d")
    if daily_data is not None and len(daily_data) >= 2:
        daily_benchmarks = get_relative_benchmark_history(symbol)
        if not daily_benchmarks.empty:
            for column in ["Benchmark_Market_Close", "Benchmark_Sector_Close"]:
                if column in daily_benchmarks:
                    daily_data[column] = daily_benchmarks[column].reindex(daily_data.index, method="ffill")
        daily_data = calculate_indicators(daily_data, ema_short, ema_long)
        analysis["backtest"] = summarize_backtest(daily_data)
    else:
        analysis["backtest"] = {"entry_count": 0, "message": "Daily history unavailable for the current-rule backtest."}
    return analysis


@st.cache_data(ttl=86400)
def get_fundamental_snapshot(symbol):
    try:
        info = yf.Ticker(symbol).get_info()
        return {
            "Name": info.get("longName") or info.get("shortName"),
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
    try:
        if symbol.upper().endswith(".BK"):
            raw_ticker = symbol.upper().removesuffix(".BK")
            sector = next((name for name, names in SET_SECTOR_PROXY_STOCKS.items() if raw_ticker in names), None)
            close = get_thai_sector_proxy_history()
            if symbol.upper() not in close:
                extra = yf.download(symbol.upper(), period=period, interval="1d", auto_adjust=False, progress=False)
                extra_close = extra["Close"] if isinstance(extra.columns, pd.MultiIndex) else extra
                close[symbol.upper()] = extra_close.iloc[:, 0] if isinstance(extra_close, pd.DataFrame) else extra_close
            stock = close[symbol.upper()].dropna() if symbol.upper() in close else pd.Series(dtype=float)

            def basket_daily_return(sectors):
                names = list(dict.fromkeys(f"{ticker}.BK" for group in sectors for ticker in SET_SECTOR_PROXY_STOCKS[group] if ticker != raw_ticker))
                names = [ticker for ticker in names if ticker in close]
                if not names:
                    return pd.Series(dtype=float)
                valid_names = [ticker for ticker in names if close[ticker].dropna().shape[0] >= 21]
                return close[valid_names].pct_change(fill_method=None).mean(axis=1, skipna=True).dropna() if valid_names else pd.Series(dtype=float)

            benchmarks = {
                "SET sector proxy": basket_daily_return(list(SET_SECTOR_PROXY_STOCKS)),
                "own sector basket": basket_daily_return([sector]) if sector else pd.Series(dtype=float),
            }
        else:
            sector = None
            sector_etfs = {
                "Technology": "XLK", "Healthcare": "XLV", "Financial Services": "XLF",
                "Consumer Cyclical": "XLY", "Communication Services": "XLC", "Industrials": "XLI",
                "Consumer Defensive": "XLP", "Energy": "XLE", "Utilities": "XLU", "Real Estate": "XLRE",
                "Basic Materials": "XLB",
            }
            fund = get_fundamental_snapshot(symbol)
            sector_etf = sector_etfs.get(fund.get("Sector")) if "Error" not in fund else None
            tickers = list(dict.fromkeys([symbol, "SPY", "QQQ"] + ([sector_etf] if sector_etf else [])))
            data = yf.download(tickers, period=period, interval="1d", auto_adjust=False, progress=False)
            close = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
            stock = close[symbol].dropna() if symbol in close else pd.Series(dtype=float)
            benchmarks = {benchmark: close[benchmark].dropna().pct_change(fill_method=None) for benchmark in ["SPY", "QQQ"] if benchmark in close}
            if sector_etf and sector_etf in close:
                benchmarks["sector ETF"] = close[sector_etf].dropna().pct_change(fill_method=None)
        results = {}
        for days in [20, 50, 100, 200]:
            if len(stock) <= days:
                continue
            stock_window = stock.pct_change(fill_method=None).dropna().tail(days)
            if len(stock_window) < days:
                continue
            stock_ret = float(((1 + stock_window).prod() - 1) * 100)
            for benchmark, returns in benchmarks.items():
                aligned = pd.concat([stock_window.rename("stock"), returns.rename("benchmark")], axis=1).dropna().tail(days)
                if len(aligned) == days:
                    bench_ret = float(((1 + aligned["benchmark"]).prod() - 1) * 100)
                    results[f"{days}D vs {benchmark}"] = stock_ret - bench_ret
        return results
    except Exception as exc:
        return {"Error": str(exc)}


@st.cache_data(ttl=3600)
def get_market_regime():
    try:
        data = yf.download(["SPY", "QQQ", "^VIX", "^TNX", "^NYA"], period="1y", interval="1d", auto_adjust=False, progress=False)
        close = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
        spy = close["SPY"].dropna()
        qqq = close["QQQ"].dropna()
        vix = close["^VIX"].dropna()
        spy_ema200 = spy.ewm(span=200, adjust=False).mean().iloc[-1]
        qqq_ema200 = qqq.ewm(span=200, adjust=False).mean().iloc[-1]
        regime = "Risk-On" if spy.iloc[-1] > spy_ema200 and qqq.iloc[-1] > qqq_ema200 else "Risk-Off / Defensive"
        spy_ret20 = float((spy.iloc[-1] / spy.iloc[-21] - 1) * 100) if len(spy) > 21 else 0.0
        spy_ret50 = float((spy.iloc[-1] / spy.iloc[-51] - 1) * 100) if len(spy) > 51 else 0.0
        breadth = None
        if "^NYA" in close:
            nya = close["^NYA"].dropna()
            breadth = float((nya.iloc[-1] / nya.ewm(span=200, adjust=False).mean().iloc[-1] - 1) * 100) if len(nya) >= 200 else None
        return {
            "Regime": regime,
            "SPY vs EMA200": float((spy.iloc[-1] / spy_ema200 - 1) * 100),
            "QQQ vs EMA200": float((qqq.iloc[-1] / qqq_ema200 - 1) * 100),
            "VIX": float(vix.iloc[-1]) if len(vix) else None,
            "SPY 20D Return": spy_ret20,
            "SPY 50D Return": spy_ret50,
            "Breadth Proxy vs EMA200": breadth,
            "10Y Treasury Yield": float(close["^TNX"].dropna().iloc[-1] / 10) if "^TNX" in close and close["^TNX"].notna().any() else None,
        }
    except Exception as exc:
        return {"Error": str(exc)}


US_SECTOR_ETFS = {
    "Information Technology": "XLK", "Health Care": "XLV", "Financials": "XLF",
    "Consumer Discretionary": "XLY", "Communication Services": "XLC", "Industrials": "XLI",
    "Consumer Staples": "XLP", "Energy": "XLE", "Utilities": "XLU",
    "Real Estate": "XLRE", "Materials": "XLB",
}

SET_SECTORS = [
    "Agro & Food Industry", "Consumer Products", "Financials", "Industrials",
    "Property & Construction", "Resources", "Services", "Technology",
]

# Yahoo Finance does not provide usable daily histories for SET industry and
# sector index symbols. These liquid listed names are therefore used to build
# clearly labeled equal-weight sector proxies instead of returning empty rows.
SET_SECTOR_PROXY_STOCKS = {
    "Agro & Food Industry": ["AAI", "BTG", "CBG", "CPF", "GFPT", "OSP", "TU"],
    "Consumer Products": ["DDD", "KAMART", "KCG", "MC", "SABINA", "SNNP", "TACC"],
    "Financials": ["BBL", "KBANK", "KTB", "KTC", "MTC", "SCB", "TIDLOR", "TTB"],
    "Industrials": ["AH", "IVL", "PTTGC", "SAT", "SCGP", "STANLY", "TASCO"],
    "Property & Construction": ["AMATA", "AP", "CK", "CPN", "LH", "SIRI", "STECON", "WHA"],
    "Resources": ["BANPU", "BCP", "BGRIM", "GPSC", "GULF", "PTT", "PTTEP", "TOP"],
    "Services": ["AOT", "BDMS", "BEM", "BH", "BTS", "CENTEL", "CPALL", "CRC"],
    "Technology": ["ADVANC", "BE8", "COM7", "DELTA", "HANA", "KCE", "SYNEX", "TRUE"],
}

US_SECTOR_ETFS_BY_NAME = {
    "Technology": "XLK", "Healthcare": "XLV", "Health Care": "XLV",
    "Financial Services": "XLF", "Financials": "XLF",
    "Consumer Cyclical": "XLY", "Consumer Discretionary": "XLY",
    "Communication Services": "XLC", "Industrials": "XLI",
    "Consumer Defensive": "XLP", "Consumer Staples": "XLP",
    "Energy": "XLE", "Utilities": "XLU", "Real Estate": "XLRE",
    "Basic Materials": "XLB", "Materials": "XLB",
}


@st.cache_data(ttl=3600)
def get_relative_benchmark_history(symbol):
    """Return broad-market and sector proxy price histories for scoring/backtests."""
    try:
        if symbol.upper().endswith(".BK"):
            raw_ticker = symbol.upper().removesuffix(".BK")
            sector = next((name for name, names in SET_SECTOR_PROXY_STOCKS.items() if raw_ticker in names), None)
            close = get_thai_sector_proxy_history()
            group_returns = {}
            sector_daily = None
            for group, names in SET_SECTOR_PROXY_STOCKS.items():
                tickers = [f"{ticker}.BK" for ticker in names if ticker != raw_ticker and f"{ticker}.BK" in close]
                if not tickers:
                    continue
                returns = close[tickers].pct_change(fill_method=None).mean(axis=1, skipna=True)
                group_returns[group] = returns
                if group == sector:
                    sector_daily = returns
            if not group_returns:
                return pd.DataFrame()
            market_daily = pd.concat(group_returns, axis=1).mean(axis=1, skipna=True)
            market_index = (1 + market_daily.fillna(0)).cumprod() * 100
            result = pd.DataFrame({"Benchmark_Market_Close": market_index})
            if sector_daily is not None:
                result["Benchmark_Sector_Close"] = (1 + sector_daily.fillna(0)).cumprod() * 100
            return result

        fund = get_fundamental_snapshot(symbol)
        sector_etf = US_SECTOR_ETFS_BY_NAME.get(fund.get("Sector")) if "Error" not in fund else None
        tickers = ["SPY"] + ([sector_etf] if sector_etf else [])
        data = yf.download(tickers, period="5y", interval="1d", auto_adjust=False, progress=False)
        close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data
        if isinstance(close, pd.Series):
            close = close.to_frame()
        result = pd.DataFrame(index=close.index)
        if "SPY" in close:
            result["Benchmark_Market_Close"] = close["SPY"]
        if sector_etf and sector_etf in close:
            result["Benchmark_Sector_Close"] = close[sector_etf]
        return result
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_thai_sector_proxy_history():
    symbols = list(dict.fromkeys(f"{ticker}.BK" for names in SET_SECTOR_PROXY_STOCKS.values() for ticker in names))
    data = yf.download(symbols, period="1y", interval="1d", auto_adjust=False, progress=False)
    close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data
    close.columns = [str(column).upper() for column in close.columns]
    return close


@st.cache_data(ttl=3600)
def get_thai_market_context():
    try:
        close = get_thai_sector_proxy_history()
        sector_returns = {}
        eligible_stocks = []
        for sector, names in SET_SECTOR_PROXY_STOCKS.items():
            symbols = [f"{ticker}.BK" for ticker in names if f"{ticker}.BK" in close]
            valid = [ticker for ticker in symbols if close[ticker].dropna().shape[0] >= 51]
            eligible_stocks.extend(valid)
            if valid:
                sector_returns[sector] = close[valid].pct_change(fill_method=None).mean(axis=1, skipna=True)
        group_returns = pd.concat(sector_returns, axis=1).mean(axis=1, skipna=True).dropna() if sector_returns else pd.Series(dtype=float)
        proxy = (1 + group_returns).cumprod()
        breadth = None
        if eligible_stocks:
            above_50d = [close[ticker].dropna().iloc[-1] > close[ticker].dropna().tail(50).mean() for ticker in eligible_stocks]
            breadth = float(sum(above_50d) / len(above_50d) * 100)
        volatility = float(group_returns.tail(20).std() * (252 ** 0.5) * 100) if len(group_returns) >= 20 else None
        ret20 = float((proxy.iloc[-1] / proxy.iloc[-21] - 1) * 100) if len(proxy) > 20 else None
        ret50 = float((proxy.iloc[-1] / proxy.iloc[-51] - 1) * 100) if len(proxy) > 50 else None
        ema50 = proxy.ewm(span=50, adjust=False).mean().iloc[-1] if len(proxy) >= 50 else None
        regime = "Risk-On proxy" if ema50 is not None and proxy.iloc[-1] > ema50 and breadth is not None and breadth >= 50 else "Risk-Off proxy" if ema50 is not None and proxy.iloc[-1] < ema50 and breadth is not None and breadth < 50 else "Mixed / incomplete"
        return {"Regime": regime, "SET sector basket proxy 20D": ret20, "SET sector basket proxy 50D": ret50,
                "Breadth proxy (% above 50D)": breadth, "Realized volatility (annualized)": volatility,
                "Stocks in breadth sample": len(eligible_stocks)}
    except Exception as exc:
        return {"Error": str(exc)}


@st.cache_data(ttl=3600)
def get_sector_screen(market="US"):
    try:
        if market == "US":
            mapping = US_SECTOR_ETFS
            tickers = list(mapping.values()) + ["SPY"]
            data = yf.download(tickers, period="1y", interval="1d", auto_adjust=False, progress=False)
            close = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
        else:
            mapping = SET_SECTOR_PROXY_STOCKS
            close = get_thai_sector_proxy_history()
        if market == "Thailand":
            sector_returns = {}
            coverage = {}
            for sector, names in mapping.items():
                symbols = [f"{ticker}.BK" for ticker in names if f"{ticker}.BK" in close]
                prices = close[symbols].dropna(how="all") if symbols else pd.DataFrame()
                valid = [column for column in prices if prices[column].dropna().shape[0] >= 51]
                coverage[sector] = len(valid)
                if not valid:
                    sector_returns[sector] = None
                    continue
                daily_returns = prices[valid].pct_change(fill_method=None)
                basket_daily = daily_returns.mean(axis=1, skipna=True).dropna()
                basket_index = (1 + basket_daily).cumprod()
                if len(basket_index) >= 51:
                    sector_returns[sector] = {
                        "20D Return": float((basket_index.iloc[-1] / basket_index.iloc[-21] - 1) * 100),
                        "50D Return": float((basket_index.iloc[-1] / basket_index.iloc[-51] - 1) * 100),
                        "daily": basket_daily,
                    }
                else:
                    sector_returns[sector] = None
            # Give each major SET group equal weight in the broad-market proxy.
            group_daily = [values["daily"].rename(sector) for sector, values in sector_returns.items() if values]
            if group_daily:
                market_daily = pd.concat(group_daily, axis=1).mean(axis=1, skipna=True).dropna()
                market_index = (1 + market_daily).cumprod()
                market_20d = float((market_index.iloc[-1] / market_index.iloc[-21] - 1) * 100) if len(market_index) > 20 else None
            else:
                market_20d = None
            results = []
            for sector in mapping:
                values = sector_returns[sector]
                results.append({
                    "Sector": sector,
                    "Coverage": f"{coverage[sector]}/{len(mapping[sector])} stocks with 50D history",
                    "20D Return": values["20D Return"] if values else None,
                    "50D Return": values["50D Return"] if values else None,
                    "Relative to SET sector proxy (20D)": values["20D Return"] - market_20d if values and market_20d is not None else None,
                    "Trend": "Improving" if values and values["20D Return"] > 0 and values["50D Return"] > 0 else "Weak / mixed" if values else "Historical data unavailable",
                })
            return results

        benchmark = "SPY"
        results = []
        for sector, ticker in mapping.items():
            if ticker not in close or benchmark not in close:
                results.append({"Sector": sector, "Ticker": ticker, "20D Return": None, "50D Return": None, "Relative to Market (20D)": None, "Trend": "Data unavailable"})
                continue
            series = close[ticker].dropna()
            bench = close[benchmark].dropna()
            if len(series) < 51 or len(bench) < 21:
                results.append({"Sector": sector, "Ticker": ticker, "20D Return": None, "50D Return": None, "Relative to Market (20D)": None, "Trend": "Insufficient history"})
                continue
            r20 = float((series.iloc[-1] / series.iloc[-21] - 1) * 100)
            r50 = float((series.iloc[-1] / series.iloc[-51] - 1) * 100)
            b20 = float((bench.iloc[-1] / bench.iloc[-21] - 1) * 100)
            ema50 = series.ewm(span=50, adjust=False).mean().iloc[-1]
            results.append({"Sector": sector, "Ticker": ticker, "20D Return": r20, "50D Return": r50,
                            "Relative to Market (20D)": r20 - b20,
                            "Trend": "Improving / above 50D" if series.iloc[-1] > ema50 and r20 > 0 else "Weak / mixed"})
        return results
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
    data = yf.download(tickers, period="2y", interval="1d", group_by="column", auto_adjust=False, progress=False)
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
