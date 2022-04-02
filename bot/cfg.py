#!/usr/bin/env python3

from os import path

STABLE_COINS = ["USDT", "BNB", "ETH", "PAXG", "BUSD", "TUSD", "USDC"]
balance_fn = path.expanduser("~/.bot/balance.log")
SLEEP_INTERVAL: int = 20  # seconds to sleep for next balance check
TYPE: str = ""
discord_message: str = ".\n"
discord_message_full: str = ".\n"
discord_print: bool = False
locked_balance = 0
discord_sent_message = None
