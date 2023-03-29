#!/usr/bin/env python3

from bot import cfg
from bot.config import config


class TP_calculate(Exception):
    pass


class TakeProfit:
    def __init__(self):
        self.take_profit: float = config.take_profit

    def error_msg(self, price, decimal):
        return f"limit_price={price} and decimal={decimal} are calculated wrong"

    def get_profit_amount(self, amount=0) -> float:
        amount = abs(float(amount))
        if self.take_profit < 0.006:
            if (cfg.TYPE == "usdt" and amount > 400) or (cfg.TYPE == "btc" and amount > 0.005):
                return 1.000 + 0.0095  # 0.95% profit

        return 1.000 + self.take_profit

    def get_long_tp(self, entry_price, isolated_wallet, decimal) -> float:
        price = float(f"{float(entry_price) * self.get_profit_amount(isolated_wallet):.{decimal}f}")
        if price <= entry_price:
            raise TP_calculate(error_msg(price, decimal))

        return price

    def get_short_tp(self, entry_price, isolated_wallet, decimal) -> float:
        price = float(f"{float(entry_price) * self.get_profit_amount(isolated_wallet):.{decimal}f}")
        if price >= entry_price:
            raise TP_calculate(error_msg(price, decimal))

        return price
