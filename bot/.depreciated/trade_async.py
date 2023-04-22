#!/usr/bin/env python3


async def both_side_order(self) -> None:
    """Both side order for futures."""
    symbol = self.strategy.symbol.replace("/USDT", "USDT")
    if await self.is_usdt_open(symbol):
        raise Exception(f"already open position for {symbol}")

    try:
        if self.strategy.size == 0:
            raise Exception("position size is less than zero")

        await self._order(quantity=self.strategy.size)
    except Exception as e:
        print_tb(str(e))
        raise e


async def is_usdt_open(self, symbol=None) -> bool:
    if not symbol:
        return False

    positions = await helper.exchange.future.fetch_positions()
    self.get_exchange_future_timestamp()
    for position in positions:
        initial_margin = abs(float(position["info"]["isolatedWallet"]))
        if initial_margin > 0 and symbol.replace("/", "") == position["symbol"].replace("/", ""):
            return True

    return False
