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
        self.assertIn(signal["entry_level"], {"A+", "A", "B", "C", "Avoid"})
        self.assertGreaterEqual(signal["core_score"], 0)
        self.assertGreaterEqual(signal["supp_score"], 0)
        self.assertGreater(signal["risk_per_share"], 0)
        self.assertGreaterEqual(signal["reward_risk"], 0)

    def test_data_quality_flags_short_history(self):
        warnings = inspect_data_quality(make_ohlcv(rows=40), "TEST")
        self.assertTrue(any("less than one trading year" in warning for warning in warnings))

    def test_backtest_summary_shape(self):
        df = calculate_indicators(make_ohlcv())
        summary = summarize_backtest(df)
        self.assertIn("entry_count", summary)
        if summary["entry_count"] > 0:
            self.assertIn("win_rate_20d", summary)
            self.assertIn("by_level", summary)


if __name__ == "__main__":
    unittest.main()
