#!/usr/bin/env python3

import websocket

from ebloc_broker.broker._utils._log import log


class Liq:
    def __init__(self):
        # symbol = "btcusdt"
        # interval = "1m"
        self.socket = "wss://fstream.binance.com/ws/!forceOrder@arr"
        self.ws = websocket.WebSocketApp(self.socket, on_message=self.on_message, on_close=self.on_close)
        self.symbol: str = ""
        self.order_quantity = 0
        self.event_time: int = 0
        self.average_price: float = 0.0
        self.side = ""
        self.order_type = ""
        self.time_in_force = ""
        self.price: float = 0.0
        self.order_status = ""
        self.order_last_filled_quantity = 0.0
        self.order_filled_accumulated_quantity = 0
        self.order_trade_time = 0

    def on_message(self, ws, message):
        """Fetch liquidation Order Streams.
            "s":"BTCUSDT",                   // Symbol
            "S":"SELL",                      // Side
            "o":"LIMIT",                     // Order Type
            "f":"IOC",                       // Time in Force
            "q":"0.014",                     // Original Quantity
            "p":"9910",                      // Price
            "ap":"9910",                     // Average Price
            "X":"FILLED",                    // Order Status
            "l":"0.014",                     // Order Last Filled Quantity
            "z":"0.014",                     // Order Filled Accumulated Quantity
           "T":1568014460893,              // Order Trade Time

        __ https://binance-docs.github.io/apidocs/futures/en/#liquidation-order-streams
        """

        for item in message.split(","):
            item = item.replace("}", "").replace("{", "").replace('"', "").replace("o:s:", "s:")
            if "forceOrder" not in item:
                _item = item.split(":")
                if _item[0] == "E":
                    self.event_time = int(_item[1])
                elif _item[0] == "s":
                    self.symbol = _item[1]
                elif _item[0] == "S":
                    self.side = _item[1]
                elif _item[0] == "o":
                    self.order_type = _item[1]
                elif _item[0] == "f":
                    self.time_in_force = _item[1]
                elif _item[0] == "q":
                    self.order_quantity = float(_item[1])
                elif _item[0] == "p":
                    self.price = _item[1]
                elif _item[0] == "ap":
                    self.average_price = float(_item[1])
                elif _item[0] == "X":
                    self.order_status = _item[1]
                elif _item[0] == "l":
                    self.order_last_filled_quantity = _item[1]
                elif _item[0] == "z":
                    self.order_filled_accumulated_quantity = _item[1]
                elif _item[0] == "T":
                    self.order_trade_time = _item[1]
                # else:
                #     print(item)

        amount = int(self.order_quantity * self.average_price)
        if amount > 10000 and self.symbol not in ["BTCUSDT", "ETHUSDT", "BNBUSDT"] and "BUSDT" not in self.symbol:
            log(f"==> symbol={self.symbol}")
            log(f"==> side={self.side} | ", end="")
            if self.side == "BUY":
                log("shorts liquadated")
            else:
                log("longs liquadated")

            log(f"==> order_quantity={self.order_quantity}")
            log(f"==> event_time={self.event_time}")
            log(f"==> order_last_filled_quantity={self.order_last_filled_quantity}")
            log(f"==> order_filled_accumulated_quantity={self.order_filled_accumulated_quantity}")
            log(f"==> order_trade_time={self.order_trade_time}")
            log(f"==> price={self.price}")
            log(f"==> average_price={self.average_price}")
            log(f"==> liq_amount={amount}")
            # log(f"==> time_in_force={self.time_in_force}")
            # log(f"==> order_type={self.order_type}")
            # log(f"==> order_status={self.order_status}")
            log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
        # print(message)

    def on_close(self):
        print("closed")


liq = Liq()
liq.ws.run_forever()
