#!/usr/bin/env python3

from ebloc_broker.broker._utils._log import log

from bot.config import config


def percent(amount, ratio):
    return float(format(amount * ratio / 100, ".2f"))


def main():
    free_usdt = config.status["root"]["usdt"]["free"]
    log(f"free_usdt={free_usdt}", "bold")
    for i in range(1, 10):
        output = percent(free_usdt, i / 10)
        log(f" * [yellow]%{i / 10}[/yellow] -> {output}")

    for i in range(1, 6):
        output = percent(free_usdt, i)
        log(f" * [yellow]%{i}[/yellow] -> {output}")


if __name__ == "__main__":
    main()
