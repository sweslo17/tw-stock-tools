from datetime import date, datetime
from typing import Dict

import pandas as pd
from pydantic import BaseModel, Field
from nicegui import ui
from nicegui.events import ValueChangeEventArguments, UploadEventArguments
from loguru import logger
import json

import utils


def default(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()


class EarningEvent(BaseModel):
    cal_quantity: int = Field(..., title="用來計算的股數")
    cash_dividend: float
    stock_dividend: float
    dividend_date: date


class StockHolding(BaseModel):
    quantity: int = 0
    avg_price: float = 0


class StockInfo(BaseModel):
    holding: StockHolding
    holding_date: date


class UserRecord(BaseModel):
    buying_histories: list[StockInfo] = Field(default_factory=list)
    current_holding: StockHolding
    earning_events: list[EarningEvent] = Field(default_factory=list)
    cash_earning: float = 0
    stock_no: str
    stock_name: str

    def avg_buying_price(self):
        total_quantity = 0
        total_price = 0
        for buying_history in self.buying_histories:
            total_quantity += buying_history.holding.quantity
            total_price += (
                buying_history.holding.quantity * buying_history.holding.avg_price
            )
        return total_price / total_quantity

    def total_buying_quantity(self):
        return sum(
            [
                buying_history.holding.quantity
                for buying_history in self.buying_histories
            ]
        )

    def total_buying_price(self):
        return sum(
            [
                buying_history.holding.quantity * buying_history.holding.avg_price
                for buying_history in self.buying_histories
            ]
        )

    def total_current_price(self):
        return self.current_holding.avg_price * self.current_holding.quantity

    def total_earning(self):
        return (
            self.cash_earning + self.total_current_price() - self.total_buying_price()
        )


class StockHoldingData(BaseModel):
    record: Dict[str, UserRecord] = Field(default_factory=dict)

    def append_holding(self, stock_no, hold_date, quantity, avg_price):
        if stock_no not in self.record:
            stock_name = utils.get_stock_name_by_stock_no(stock_no)
            self.record[stock_no] = UserRecord(
                stock_no=stock_no, stock_name=stock_name, current_holding=StockHolding()
            )
        self.record[stock_no].buying_histories.append(
            StockInfo(
                holding_date=hold_date,
                holding=StockHolding(avg_price=avg_price, quantity=quantity * 1000),
            )
        )

    def gen_holding_table_rows(self):
        output = []
        for stock_no, user_record in self.record.items():
            for buying_history in user_record.buying_histories:
                output.append(
                    {
                        "stock_no": stock_no,
                        "stock_name": user_record.stock_name,
                        "hold_date": buying_history.holding_date,
                        "quantity": buying_history.holding.quantity,
                        "avg_price": buying_history.holding.avg_price,
                    }
                )
        return output

    def gen_earning_table_rows(self):
        output = []
        for stock_no, user_record in self.record.items():
            stock_dividend = (
                user_record.current_holding.quantity
                - user_record.total_buying_quantity()
            )
            output.append(
                {
                    "stock_no": stock_no,
                    "stock_name": user_record.stock_name,
                    "quantity": user_record.current_holding.quantity,
                    "current_price": user_record.current_holding.avg_price,
                    "total_earning": f"{user_record.total_earning():.2f}",
                    "cash_earning": user_record.cash_earning,
                    "stock_dividend": stock_dividend,
                }
            )
        return output

    def gen_statistic_table_rows(self):
        output = []
        total_value = sum(
            [
                user_record.total_current_price()
                for stock_no, user_record in self.record.items()
            ]
        )
        total_earning = sum(
            [
                user_record.total_earning()
                for stock_no, user_record in self.record.items()
            ]
        )
        total_cash_dividend = sum(
            [user_record.cash_earning for stock_no, user_record in self.record.items()]
        )
        total_buying_price = sum(
            [
                user_record.total_buying_price()
                for stock_no, user_record in self.record.items()
            ]
        )
        output.append(
            {
                "total_value": f"{total_value:.2f}",
                "total_earning": f"{total_earning:.2f}",
                "total_cash_dividend": f"{total_cash_dividend:.2f}",
                "total_earning_rate": f"{total_earning/total_buying_price*100:.2f}%",
            }
        )
        return output


class StockInputAction:
    def __init__(self, stock_no="", hold_date=""):
        self.stock_no = stock_no
        self.hold_date = hold_date
        self.quantity = 1
        self.avg_price = 0
        self.stock_holding = StockHoldingData()
        self.earning_table_obj = self.__init_earning_table()
        self.holding_table_obj = self.__init_holding_table()
        self.statistic_table_obj = self.__init_statistic_table()
        self.tree_obj = []
        self.status_row = ui.row()
        with ui.row():
            self.history_table()
            self.data_table()
            self.statistic_table()
            self.dividend_history_tree()

    def __init_earning_table(self):
        return {
            "columns": [
                {
                    "name": "股票號碼",
                    "label": "股票號碼",
                    "field": "stock_no",
                    "required": True,
                    "sortable": True,
                },
                {
                    "name": "股票名稱",
                    "label": "股票名稱",
                    "field": "stock_name",
                    "required": False,
                },
                {
                    "name": "總持有股數",
                    "label": "總持有股數",
                    "field": "quantity",
                    "required": False,
                },
                {
                    "name": "現在價格",
                    "label": "現在價格",
                    "field": "current_price",
                    "required": False,
                },
                {
                    "name": "總共損益",
                    "label": "總共損益",
                    "field": "total_earning",
                    "required": False,
                },
                {
                    "name": "現金股利",
                    "label": "現金股利",
                    "field": "cash_earning",
                    "required": False,
                },
                {
                    "name": "股票股利",
                    "label": "股票股利",
                    "field": "stock_dividend",
                    "required": False,
                },
            ],
            "rows": [],
        }

    def __init_holding_table(self):
        return {
            "columns": [
                {
                    "name": "stock_no",
                    "label": "stock_no",
                    "field": "stock_no",
                    "required": True,
                    "sortable": True,
                },
                {
                    "name": "股票名稱",
                    "label": "stock_name",
                    "field": "stock_name",
                    "required": False,
                },
                {
                    "name": "hold_date",
                    "label": "hold_date",
                    "field": "hold_date",
                    "required": False,
                },
                {
                    "name": "quantity",
                    "label": "quantity",
                    "field": "quantity",
                    "required": False,
                },
                {
                    "name": "avg_price",
                    "label": "avg_price",
                    "field": "avg_price",
                    "required": False,
                },
            ],
            "rows": [],
        }

    def __init_statistic_table(self):
        return {
            "columns": [
                {
                    "name": "股票總市值",
                    "label": "股票總市值",
                    "field": "total_value",
                    "required": True,
                },
                {
                    "name": "總獲利",
                    "label": "總獲利",
                    "field": "total_earning",
                    "required": False,
                },
                {
                    "name": "總配息",
                    "label": "總配息",
                    "field": "total_cash_dividend",
                    "required": False,
                },
                {
                    "name": "投入獲利率(%)",
                    "label": "投入獲利率(%)",
                    "field": "total_earning_rate",
                    "required": False,
                },
            ],
            "rows": [],
        }

    def init_data(self):
        self.quantity = 1
        self.stock_no = ""
        self.hold_date = ""
        self.avg_price = 0
        self.stock_holding = StockHoldingData()
        # init tables
        self.earning_table_obj = self.__init_earning_table()
        self.holding_table_obj = self.__init_holding_table()
        self.statistic_table_obj = self.__init_statistic_table()
        self.tree_obj = []
        self.history_table.refresh()
        self.data_table.refresh()
        self.statistic_table.refresh()
        self.dividend_history_tree.refresh()

    def start_loading(self):
        with self.status_row:
            ui.spinner(size="lg")

    def stop_loading(self):
        self.status_row.clear()

    @staticmethod
    def _find_earliest_date(histories: list[StockInfo]):
        if len(histories) == 0:
            return
        earliest_date = histories[0].holding_date
        for history in histories:
            cur_date = history.holding_date
            if cur_date < earliest_date:
                earliest_date = cur_date
        return earliest_date

    def add_stock(self, event: ValueChangeEventArguments):
        self.start_loading()
        self.stock_holding.append_holding(
            self.stock_no, self.hold_date, self.quantity, self.avg_price
        )
        self.holding_table_obj["rows"] = self.stock_holding.gen_holding_table_rows()
        self.history_table.refresh()
        self.write_history()
        self.stop_loading()

    def calculate_earning(self):
        self.start_loading()
        self.init_current_holding()
        for stock_no, user_record in self.stock_holding.record.items():
            self.calculate_earning_by_user_record(stock_no, user_record)
            logger.info(
                json.dumps(
                    user_record.dict(), indent=4, ensure_ascii=False, default=default
                )
            )
        self.earning_table_obj["rows"] = self.stock_holding.gen_earning_table_rows()
        self.data_table.refresh()
        self.statistic_table_obj["rows"] = self.stock_holding.gen_statistic_table_rows()
        self.statistic_table.refresh()
        self.tree_obj = self.gen_history_tree(self.stock_holding.record)
        self.dividend_history_tree.refresh()
        self.stop_loading()

    @ui.refreshable
    def dividend_history_tree(self):
        ui.tree(self.tree_obj, label_key="id")

    @ui.refreshable
    def history_table(self):
        ui.table(
            title="購買歷史",
            columns=self.holding_table_obj["columns"],
            rows=self.holding_table_obj["rows"],
            row_key="stock_no",
        )

    @ui.refreshable
    def data_table(self):
        ui.table(
            title="損益狀況",
            columns=self.earning_table_obj["columns"],
            rows=self.earning_table_obj["rows"],
            row_key="stock_no",
        )

    @ui.refreshable
    def statistic_table(self):
        ui.table(
            title="統計看板",
            columns=self.statistic_table_obj["columns"],
            rows=self.statistic_table_obj["rows"],
        )

    def write_history(self):
        df = pd.DataFrame(
            columns=["stock_no", "stock_name", "hold_date", "quantity", "avg_price"]
        )
        with open("holding_history.csv", "w") as f:
            for stock_no, user_record in self.stock_holding.record.items():
                for buying_history in user_record.buying_histories:
                    df = pd.concat(
                        [
                            df,
                            pd.DataFrame(
                                [
                                    {
                                        "stock_no": stock_no,
                                        "stock_name": user_record.stock_name,
                                        "hold_date": buying_history.holding_date,
                                        "quantity": buying_history.holding.quantity,
                                        "avg_price": buying_history.holding.avg_price,
                                    }
                                ]
                            ),
                        ]
                    )
            df.to_csv(f, index=False)

    def load_history(self, event: UploadEventArguments):
        df = pd.read_csv(event.content, dtype=str)
        for index, row in df.iterrows():
            print(row["stock_no"], row["hold_date"], row["quantity"], row["avg_price"])
            self.stock_holding.append_holding(
                row["stock_no"],
                row["hold_date"],
                int(row["quantity"]) / 1000,
                float(row["avg_price"]),
            )
            self.holding_table_obj["rows"] = self.stock_holding.gen_holding_table_rows()
        self.history_table.refresh()

    @staticmethod
    def get_current_price(stock_no):
        return utils.get_latest_stock_price_by_stock_no(stock_no)

    def gen_history_tree(self, record: dict[str, UserRecord]):
        tree = []
        for stock_no, user_record in record.items():
            children = []
            for earning_event in user_record.earning_events:
                children.append(
                    {
                        "id": f"{earning_event.dividend_date} "
                        + f"計算股數：{earning_event.cal_quantity}, "
                        + f"配股：{earning_event.stock_dividend}, "
                        + f"配息：{earning_event.cash_dividend}"
                    }
                )
            tree.append(
                {
                    "id": f"{stock_no}, {user_record.stock_name}",
                    "children": children,
                }
            )
        return tree

    def calculate_earning_by_user_record(self, stock_no: str, user_record: UserRecord):
        print(stock_no)
        earliest_holding_date = self._find_earliest_date(user_record.buying_histories)
        dividend_df = utils.get_history_data_by_stock_no(
            stock_no, earliest_holding_date
        )
        # sort holding_histories by origin_holding_date
        sorted_buying_histories = sorted(
            user_record.buying_histories, key=lambda x: x.holding_date
        )
        for idx, history in enumerate(sorted_buying_histories):
            user_record.current_holding.quantity += history.holding.quantity
            dividend_start_date = history.holding_date.strftime("%Y-%m-%d")
            if idx == len(sorted_buying_histories) - 1:  # last element
                dividend_end_date = datetime.now().strftime("%Y-%m-%d")
            else:
                dividend_end_date = sorted_buying_histories[
                    idx + 1
                ].holding_date.strftime("%Y-%m-%d")
            apply_dividend = dividend_df[
                (dividend_df["CashExDividendTradingDate"] > dividend_start_date)
                & (dividend_df["CashExDividendTradingDate"] < dividend_end_date)
            ]
            for div_idx, row in apply_dividend.iterrows():
                before_quantity = user_record.current_holding.quantity
                if row["CashEarningsDistribution"] > 0:
                    user_record.cash_earning += int(
                        row["CashEarningsDistribution"] * before_quantity
                    )
                if row["StockEarningsDistribution"] > 0:
                    user_record.current_holding.quantity += int(
                        row["StockEarningsDistribution"] * before_quantity * 0.1
                    )
                user_record.earning_events.append(
                    EarningEvent(
                        cal_quantity=before_quantity,
                        cash_dividend=row["CashEarningsDistribution"],
                        stock_dividend=row["StockEarningsDistribution"],
                        dividend_date=row["CashExDividendTradingDate"],
                    )
                )
            user_record.current_holding.avg_price = self.get_current_price(
                stock_no=stock_no
            )

    def init_current_holding(self):
        for stock_no, user_record in self.stock_holding.record.items():
            user_record.current_holding.quantity = 0
            user_record.current_holding.avg_price = 0
            user_record.earning_events = []
            user_record.cash_earning = 0


stock_input_action = StockInputAction()
ui.button("更新損益", on_click=stock_input_action.calculate_earning)
with ui.left_drawer(bordered=True):
    ui.label("輸入區域")
    ui.input(label="股票號碼", placeholder="e.g. 2330").bind_value(
        stock_input_action, "stock_no"
    )
    income_stock_date = ui.label()
    ui.date(value="2020-01-01").bind_value(stock_input_action, "hold_date")
    ui.number(label="購買張數").bind_value(stock_input_action, "quantity")
    ui.number(label="平均價格").bind_value(stock_input_action, "avg_price")
    ui.button("確認", on_click=stock_input_action.add_stock)
    ui.button("reset", on_click=stock_input_action.init_data)
    ui.upload(on_upload=stock_input_action.load_history)
ui.run()
