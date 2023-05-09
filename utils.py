import datetime
from datetime import date
from functools import lru_cache

import requests
import pandas as pd
from FinMind.data import DataLoader


BASE_DATA_PATH = "data/"

FINMIND_TOKEN = open("finmind_token.txt", "r").read().strip()


def download_twse_stock_id():
    """
    下載股票代號
    """
    link = "https://quality.data.gov.tw/dq_download_json.php?nid=11549&md5_url=bb878d47ffbe7b83bfc1b41d0b24946e"
    r = requests.get(link)
    print(r.text)
    data = pd.DataFrame(r.json())
    data.to_csv(BASE_DATA_PATH + "/stock_id.csv", index=False, encoding="utf-8-sig")


def get_history_data_by_stock_no(stock_no: str, from_data: date):
    api = DataLoader()
    api.login_by_token(api_token=FINMIND_TOKEN)
    df = api.taiwan_stock_dividend(
        stock_id=stock_no, start_date=from_data.strftime("%Y-%m-%d")
    )
    return df


@lru_cache(maxsize=None)
def get_all_stock_info():
    api = DataLoader()
    api.login_by_token(api_token=FINMIND_TOKEN)
    df = api.taiwan_stock_info()
    return df


@lru_cache(maxsize=None)
def get_stock_name_by_stock_no(stock_no: str):
    print(type(stock_no))
    all_stock_df = get_all_stock_info()
    return all_stock_df.loc[all_stock_df["stock_id"] == stock_no]["stock_name"].values[
        0
    ]


@lru_cache(maxsize=None)
def get_latest_stock_price_by_stock_no(stock_no: str) -> float:
    api = DataLoader()
    api.login_by_token(api_token=FINMIND_TOKEN)
    df = api.taiwan_stock_daily(
        stock_id=stock_no,
        start_date=(datetime.datetime.now() - datetime.timedelta(days=5)).strftime(
            "%Y-%m-%d"
        ),
    )
    return df["close"].iloc[-1]


if __name__ == "__main__":
    print(get_latest_stock_price_by_stock_no("2412"))
