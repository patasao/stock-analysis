import unittest

import pandas as pd

from analysis_core import (
    calculate_indicators,
    evaluate_strategy_row,
    inspect_data_quality,
    summarize_backtest,
)


def make_ohlcv(rows=320):
    dates = pd.bdate_range("2025-01-01", periods=rows)
    close = pd.Series([100 + (i * 0.08) + ((i % 9) - 4) * 0.4 for i in range(rows)], index=dates)
    open_ = close.shift(1).fillna(close.iloc[0]) * 1.001
    high = pd.concat([open_, close], axis=1).max(axis=1) * 1.025
    low = pd.concat([open_, close], axis=1).min(axis=1) * 0.975
    volume = pd.Series([1_000_000 + (i % 20) * 10_000 for i in range(rows)], index=dates)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume})


class AnalysisCoreTests(unittest.TestCase):
    def test_calculate_indicators_adds_expected_columns(self):
        df = calculate_indicators(make_ohlcv())
        expected = {"RSI", "ATR", "ADX", "EMA_1", "EMA_2", "BB_Upper", "High_52w", "Avg_Drawdown"}
        self.assertTrue(expected.issubset(df.columns))
        self.assertTrue(df["RSI"].dropna().between(0, 100).all())

    def test_evaluate_strategy_row_returns_scoring_and_trade_plan(self):
        df = calculate_indicators(make_ohlcv())
        signal = evaluate_strategy_row(df)
        self.assertIn(signal["entry_level"], {"Buy", "Wait", "Avoid"})
        self.assertGreaterEqual(signal["core_score"], 0)
        self.assertGreaterEqual(signal["supp_score"], 0)
        self.assertGreaterEqual(signal["risk_per_share"], 0)
        self.assertGreaterEqual(signal["reward_risk"], 0)
        if signal["suggested_entry"] is None:
            self.assertIsNone(signal["stop_loss"])
            self.assertEqual(signal["risk_per_share"], 0)
            self.assertNotEqual(signal["entry_level"], "Buy")
        else:
            self.assertLess(signal["stop_loss"], signal["suggested_entry"])
        if signal["tp1"] is None or signal["tp2"] is None:
            self.assertNotEqual(signal["entry_level"], "Buy")
        else:
            self.assertGreater(signal["tp2"], signal["tp1"])
            self.assertGreaterEqual(signal["rr_tp2"], signal["rr_tp1"])
        self.assertGreater(signal["atr_val"], 0)
        self.assertFalse(signal["s8"])  # no benchmark history means relative strength is unverified
        self.assertFalse(signal["s9"])
        self.assertIn(signal["setup_type"], {"Pullback", "Breakout retest", "Breakout", "No confirmed setup"})
        if signal["entry_level"] == "Buy":
            self.assertLessEqual(abs(signal["suggested_entry"] - signal["curr_price"]), signal["atr_val"] * 0.5)

    def test_data_quality_flags_short_history(self):
        warnings = inspect_data_quality(make_ohlcv(rows=40), "TEST")
        self.assertTrue(any("less than one trading year" in warning for warning in warnings))

    def test_relative_strength_checks_require_benchmarks_and_compare_returns(self):
        df = calculate_indicators(make_ohlcv())
        df["Benchmark_Market_Close"] = 100.0
        df["Benchmark_Sector_Close"] = 100.0
        stronger = evaluate_strategy_row(df)
        self.assertGreater(stronger["rs_market_50"], 0)
        self.assertGreater(stronger["rs_sector_50"], 0)
        self.assertTrue(stronger["s8"])
        self.assertTrue(stronger["s9"])

        df["Benchmark_Market_Close"] = pd.Series(range(100, 100 + len(df)), index=df.index)
        df["Benchmark_Sector_Close"] = pd.Series(range(100, 100 + len(df)), index=df.index)
        weaker = evaluate_strategy_row(df)
        self.assertLess(weaker["rs_market_50"], 0)
        self.assertFalse(weaker["s8"])
        self.assertFalse(weaker["s9"])

    def test_backtest_summary_shape(self):
        df = calculate_indicators(make_ohlcv())
        summary = summarize_backtest(df)
        self.assertIn("entry_count", summary)
        if summary["entry_count"] > 0:
            self.assertIn("win_rate_20d", summary)
            self.assertIn("by_level", summary)
            self.assertIn("stop_hit_rate_20d", summary)
            self.assertIn("tp1_hit_rate_20d", summary)


if __name__ == "__main__":
    unittest.main()
