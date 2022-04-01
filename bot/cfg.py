#!/usr/bin/env python3

from os import path

STABLE_COINS = ["USDT", "BNB", "ETH", "PAX", "PAXG", "BUSD", "TUSD", "USDC"]
balance_fn = path.expanduser("~/.bot/balance.log")
#: seconds to sleep for next balance check
SLEEP_INTERVAL = 20
TYPE: str = ""
discord_message = ".\n"
locked_balance = 0
discord_message_full = ".\n"
discord_sent_message = None
