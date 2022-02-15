#!/usr/bin/env python3

from os import path

balance_fn = path.expanduser("~/.bot/balance.log")
#: seconds to sleep for next balance check
SLEEP_INTERVAL = 20
TYPE = None
discord_message = ""
locked_balance = 0.0
discord_message_full = ""
discord_sent_message = None
