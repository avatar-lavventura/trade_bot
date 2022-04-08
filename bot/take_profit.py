#!/usr/bin/env python3

from bot import cfg
from bot.config import config


class TP_calculate(Exception):
    pass


class TakeProfit:
    def __init__(self):
        self.take_profit: float = config.take_profit

    def get_profit_amount(self, amount=0) -> float:
        amount = abs(float(amount))
        if self.take_profit < 0.006:
            if (cfg.TYPE == "usdt" and amount > 200) or (cfg.TYPE == "btc" and amount > 0.004):
                return 1.000 + 0.0076  # % 0.76

        return 1.000 + self.take_profit

    def get_long_tp(self, entry_price, isolated_wallet, decimal) -> float:
        price = float(f"{float(entry_price) * self.get_profit_amount(isolated_wallet):.{decimal}f}")
        if price <= entry_price:
            raise TP_calculate(f"limit_price={price}, decimal={decimal} calculated wrong")

        return price

    def get_short_tp(self, entry_price, isolated_wallet, decimal) -> float:
        price = float(f"{float(entry_price) * self.get_profit_amount(isolated_wallet):.{decimal}f}")
        if price >= entry_price:
            raise TP_calculate(f"limit_price={price}, decimal={decimal} calculated wrong")

        return price
