#!/usr/bin/env python3

import websocket


def on_message(ws, message):
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
                print(f"==> event_time={_item[1]}")
            elif _item[0] == "s":
                print(f"==> symbol={_item[1]}")
            elif _item[0] == "S":
                print(f"==> side={_item[1]}")
            elif _item[0] == "o":
                print(f"==> order_type={_item[1]}")
            elif _item[0] == "o":
                print(f"==> order_type={_item[1]}")
            elif _item[0] == "f":
                print(f"==> time_in_force={_item[1]}")
            elif _item[0] == "q":
                print(f"==> order_quantity={_item[1]}")
            elif _item[0] == "p":
                print(f"==> price={_item[1]}")
            elif _item[0] == "ap":
                print(f"==> average_price={_item[1]}")
            elif _item[0] == "X":
                print(f"==> order_status={_item[1]}")
            elif _item[0] == "l":
                print(f"==> order_last_filled_quantity={_item[1]}")
            elif _item[0] == "z":
                print(f"==> order_filled_accumulated_quantity={_item[1]}")
            elif _item[0] == "T":
                print(f"==> order_trade_time={_item[1]}")
            else:
                print(item)

    print("----------------------")
    # print(message)


def on_close():
    print("Closed")


# symbol = "btcusdt"
# interval = "1m"
socket = "wss://fstream.binance.com/ws/!forceOrder@arr"
ws = websocket.WebSocketApp(socket, on_message=on_message, on_close=on_close)

ws.run_forever()
