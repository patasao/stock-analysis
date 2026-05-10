import yfinance as yf
import pandas as pd

def test_download():
    symbol = "AAPL"
    data = yf.download(symbol, period="5d", interval="1d")
    print(f"Columns: {data.columns}")
    if isinstance(data.columns, pd.MultiIndex):
        print("MultiIndex detected")
        data.columns = data.columns.get_level_values(0)
        print(f"Flattened Columns: {data.columns}")
    print(data.head())

if __name__ == "__main__":
    test_download()
