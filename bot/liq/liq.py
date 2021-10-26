#!/usr/bin/env python3

from bot.user_setup import check_binance_obj

client, balances = check_binance_obj()


class Fetch_liq:
    def _futures_coin_liquidation_orders(self, **params):
        """Get all liquidation orders

        __ https://binance-docs.github.io/apidocs/delivery/en/#user-39-s-force-orders-user_data
        """
        # return client._request_futures_api('get', 'forceOrders', signed=True, data=params)
        return client._request_futures_coin_api("get", "forceOrders", data=params, signed=True)

    def get_future_coin_liquidation_orders(self, symbol=None):
        return self._futures_coin_liquidation_orders(symbol=symbol, autoCloseType="LIQUIDATION", limit=100)


def main():
    # https://github.com/sammchardy/python-binance/issues/873
    cf = Fetch_liq()
    print(cf.get_future_coin_liquidation_orders(symbol="BTCUSD_PERP"))


if __name__ == "__main__":
    main()
