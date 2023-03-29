#!/usr/bin/env python3

import os
import sys
import time
from contextlib import suppress
from typing import Tuple

from broker._utils._log import _console_clear, log, ok  # flake8: noqa
from broker._utils.tools import _date, _timestamp, decimal_count, print_tb
from broker.errors import QuietExit

from bot import cfg
from bot.bar_ohlcv import _fetch_ohlcv
from bot.config import config, exchange
from bot.fund_time import Fund
from bot.take_profit import TakeProfit

TP = TakeProfit()
fund = Fund()


class BotHelperAsync:
    def __init__(self) -> None:
        self.CROSS_READ_FLAG = False

    async def close(self):
        """Close the async function.

        __ https://stackoverflow.com/a/54528397/2402577
        """
        await exchange.close()

    def _update_timestamp_status(self, key) -> None:
        #: fetch the timestamp when iteration started
        latest_ts = config._env.status["timestamp"]
        config._env._ts.add_single_key("latest", latest_ts)
        del_list = []
        for asset_timestamp in config.timestamp[key]:
            if asset_timestamp not in config.asset_list:
                ts = int(config.timestamp[key][asset_timestamp])
                if len(str(ts)) == 13 and ts <= latest_ts * 1000:
                    del_list.append(asset_timestamp)
                elif ts <= latest_ts:
                    del_list.append(asset_timestamp)

        for asset in del_list:
            if asset not in config.SPOT_IGNORE_LIST:
                del config.timestamp[key][asset]

    def update_timestamp_status(self) -> None:
        self._update_timestamp_status(f"{cfg.TYPE}_timestamp")
        # if cfg.TYPE == "usdt" and config.cfg["root"]["busd"]["status"] == "on":
        #     self._update_timestamp_status("busd_timestamp")

    async def fetch_symbol_percent_change(self, symbol, tf, price=None):
        bar_price = await fund._bar_ohlcv(symbol, tf)
        # print(bar_price)
        try:
            bar_price = bar_price[0]  # time, open, high, low, close, volume
        except Exception as e:
            raise KeyboardInterrupt from e

        if price:
            asset_price = price
        else:
            if symbol in cfg.PRICES:
                if symbol == "BTCUSDT":
                    asset_price = int(cfg.PRICES[symbol])
                else:
                    asset_price = cfg.PRICES[symbol]
            else:
                asset_price = await self.spot_fetch_ticker(symbol)

        high = bar_price[2]
        low = bar_price[3]
        # TODO: check here
        if asset_price < low:
            bar_price = high  # high
        else:
            bar_price = low  # low

        # if tf == "1d":
        #     bar_price = low  # low

        percent = ((asset_price - bar_price) / bar_price) * 100
        return asset_price, float(format(percent, ".2f"))

    async def analyze_positions(self, name, lost, pos_count, free) -> None:
        c = "red" if float(lost) < 0 < float(cfg.locked_balance) else "green"
        msg = ""
        lost = float(lost)
        real_pos_count = config._env._status.find_one("real_pos_count")["value"]
        if name == "mBTC":
            msg += "\n-=-=-=-=-=-= "
            if lost != 0:
                lost_usdt = lost / 1000 * cfg.PRICES["BTCUSDT"]
                msg += f"[{c}]{format(lost_usdt, '.2f')}$({lost})[/{c}] "

            msg += f"locked=[cy]{format(float(cfg.locked_balance), '.2f')}%[/cy] "
            if free > 0:
                _free_usdt = float(free) * cfg.PRICES["BTCUSDT"]
                free = format(free * 1000, ".4f")
                msg = f"{msg}free_btc=[cy]{free}[/cy]([cy]{format(_free_usdt, '.2f')}$[/cy]) "

            _total = cfg.SUM_BTC + abs(lost) / 1000
            _total = format(_total, ".5f")
            msg += f"[ib]{_total}[/ib]"
        else:
            msg += "[ib]-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=[/ib] "
            msg += f"[{c}]{abs(lost)}{name}[/{c}] locked=[cy]{cfg.locked_balance}%[/cy] "
            if free > 1:
                msg = f"{msg}free=[cy]{free}{name}[/cy] "

        if float(cfg.locked_balance) > 0:
            if real_pos_count > 1:
                log(msg, end="")
            else:
                log("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- ", "bold black", end="")

            output = config._env.stats.find_one(cfg.CURRENT_DATE)
            if pos_count > 2:
                if output:
                    log(f"pos=[blue]{pos_count}[/blue] perf=[blue]{output['value']}[/blue]")
                else:
                    log(f"pos=[blue]{pos_count}[/blue]")
            elif output:
                log(f"perf=[blue]{output['value']}[/blue]")
            else:
                log()

    async def restart(self):
        log()
        log(f"#> -=-=-=-=-=-=-=-=-=- [g]RESTARTING[/g] {_date()} -=-=-=-=-=-=-=-=-=- [blue]<#", is_write=False)
        os.execv(sys.argv[0], sys.argv)

    async def _discord_sent_msg(self, msg):
        try:
            if cfg.discord_sent_msg:
                await cfg.discord_sent_msg.edit(content=msg)
            else:
                cfg.discord_sent_msg = await self.channel.send(msg)
        except Exception as e:
            sub_str = str(e).partition("\n")[0]
            log(f"E: discord: {sub_str}")
            if "Service Unavailable" in str(e):
                self.restart()

            with suppress(Exception):
                await cfg.discord_sent_msg.delete()

            cfg.discord_message = f"`{_date(_format='%m-%d %H:%M:%S')}`\n"
            cfg.discord_sent_msg = None

    async def per_str(percent):
        return f"([red]{percent}%[/red])" if percent < 0 else f"([g]+{percent}%[/g])"

    async def carry_me_to_run_app(self, percent_1h, percent_1d):
        # TODO: carry this function to run_app print BTC change
        if percent_1h and percent_1d:
            per_str_c_1h = per_str(percent_1h)
            per_str_c_1d = per_str(percent_1d)
            c = "m" if symbol == "BTCUSDT" else "cy"
            if float(lost) > 0:
                log(
                    f" * {symbol}=[{c}]{asset_price}[/{c}] {per_str_c_1h} {per_str_c_1d}",
                    end="",
                    is_write=False,
                )

    async def _discord_send(self, msg, lost, pos_count, name, free) -> None:
        _time = _date(_format="%m-%d %H:%M:%S")
        cfg.locked_balance = 100 if float(cfg.locked_balance) > 99.3 else format(cfg.locked_balance, ".2f")
        await self.analyze_positions(name.replace(" ", ""), lost, pos_count, free)
        if (
            cfg.discord_message
            and len(cfg.discord_message) > 11
            or (cfg.TYPE == "btc" and cfg.discord_message_full and len(cfg.discord_message_full) >= 11)
        ):
            if cfg.TYPE == "usdt":
                flag = False
                width1 = max(len(v) for v in config.WATCHLIST)
                for symbol in config.WATCHLIST:
                    if not flag:
                        flag = True
                        msg = f"{msg}\n```"

                    # TODO: store percent_1h and percent_1d in mongodb for BTC
                    percent_1h = ""
                    percent_1d = ""
                    try:
                        time.sleep(exchange.binance.rateLimit / 1000)  # time.sleep wants seconds
                        asset_price, percent_1h = await self.fetch_symbol_percent_change(symbol, tf="1h")
                        time.sleep(exchange.binance.rateLimit / 1000)  # time.sleep wants seconds
                        asset_price, percent_1d = await self.fetch_symbol_percent_change(symbol, tf="1d")
                        if percent_1h:
                            per_str_1h = f"{percent_1h}" if percent_1h < 0 else f"+{percent_1h}"

                        if percent_1d:
                            per_str_1d = f"{percent_1d}" if percent_1d < 0 else f"+{percent_1d}"

                        if percent_1h and percent_1d:
                            per_str = f"{per_str_1h}  {per_str_1d}"
                        else:
                            per_str = ""
                    except Exception as e:
                        log(f"E: {symbol} {e}")
                        # print_tb(e)

                    if symbol in "BTCUSDT":
                        if percent_1h and percent_1d:
                            per_str_c_1h = (
                                f"([red]{percent_1h}%[/red])" if percent_1h < 0 else f"([g]+{percent_1h}%[/g])"
                            )
                            per_str_c_1d = (
                                f"([red]{percent_1d}%[/red])" if percent_1d < 0 else f"([g]+{percent_1d}%[/g])"
                            )
                            c = "m" if symbol == "BTCUSDT" else "cy"
                            # if float(lost) > 0:
                            #     log(
                            #         f" * {symbol}=[{c}]{asset_price}[/{c}] {per_str_c_1h} {per_str_c_1d}",
                            #         end="",
                            #         is_write=False,
                            #     )
                        elif float(lost) > 0:
                            log(
                                f" * {symbol}=[{c}]{asset_price}[/{c}]",
                                end="",
                                is_write=False,
                            )
                    elif "BTC" in symbol:
                        asset_price = "{:.8f}".format(asset_price).lstrip("0.")

                    target_str = ""
                    if symbol in config.WATCHLIST_TARGET:
                        target_str = f"🎯{config.WATCHLIST_TARGET[symbol]}"

                    if symbol in config.WATCHLIST_TARGET or symbol in config.WATCHLIST_BAR:
                        msg = f"{msg}\n{symbol:<{width1}} {asset_price:>{6}} {per_str}"
                        ohlcv = fund.RECORDS_BAR_1D[symbol]
                        df = _fetch_ohlcv(ohlcv, is_compact=True)
                        msg = f"{msg} {target_str}\n{df}"
                    else:
                        if symbol == "BTCUSDT":
                            ohlcv = fund.RECORDS_BAR_1D[symbol]
                            # high = ohlcv[0][2]
                            df = _fetch_ohlcv(ohlcv, is_compact=True)
                            # msg = f"{msg}\n                   1h%   24h%\n"
                            # msg = f"{msg}{symbol:<{width1}} {asset_price:>{6}} {per_str}"
                            msg = f"{msg}\n"
                            msg = f"{msg}{symbol} {asset_price:>{6}} {per_str}"
                            msg = f"{msg}\n{df}"
                        else:
                            msg = f"{msg}\n{symbol:<{width1}} {asset_price:>{6}} {per_str}"

                    msg = f"{msg}\n–––––––––––––"

                if flag and msg:
                    if "03:00:" in _time:
                        _time = _time[:-3]
                        msg = f"=> `{_time}`"
                    else:
                        msg = f"{msg}\n```"
                        if not config.cfg["root"]["balance_silent"]:
                            msg = f"{msg}=> `{_time}`"

                    if config.estimated_balance() and ("03:00:" in _time or not config.cfg["root"]["balance_silent"]):
                        msg = f"{msg}  :moneybag:`{config.estimated_balance()}`"
                        msg = f"{msg} w=`${int(cfg.WITHDRAWN)}`\n\t\t"
                        msg = f"{msg}:dollar:`{int(config.estimated_balance() + cfg.WITHDRAWN)}`"

            if "03:00:" in _time:
                if config.estimated_balance():
                    await self._discord_sent_msg(msg)
            else:
                await self._discord_sent_msg(msg)

    ########
    # SPOT #
    ########
    async def _fetch_isolated_balance(self) -> float:
        """Fetch margin balance.

        ipdb> balances["info"]["assets"][0]["quoteAsset"] {'asset': 'USDT',
        'borrowEnabled': True, 'borrowed': '0', 'free': '2.1602058', 'interest':
        '0', 'locked': '0', 'netAsset': '2.1602058', 'netAssetOfBtc':
        '0.0001003', 'repayEnabled': True, 'totalAsset': '2.1602058'}
        """
        try:
            balances = await exchange.margin_isolated.fetch_balance()
        except Exception as e:
            raise QuietExit("warning: cannot fetch isolated balance") from e

        return float(balances["info"]["totalNetAssetOfBtc"])

    async def _fetch_balance(self) -> None:
        pos_count = 0
        real_pos_count = 0
        ongoing_positions = []
        cfg.BALANCES = await exchange.spot.fetch_balance()
        for symbol in cfg.BALANCES:
            if symbol not in cfg.ignore_list and cfg.BALANCES[symbol]["total"] > 0:
                ongoing_positions.append(symbol)
                if symbol not in cfg.STABLE_COINS:
                    real_pos_count += 1
                    if symbol not in config.SPOT_IGNORE_LIST:
                        pos_count += 1

        del_list = []
        key = f"{cfg.TYPE}_timestamp"
        for asset_timestamp in config.timestamp[key]:
            if asset_timestamp != "base" and asset_timestamp not in ongoing_positions:
                del_list.append(asset_timestamp)

        for asset in del_list:
            del config.timestamp[key][asset]

        config._env._status.add_single_key("count", pos_count)
        config._env._status.add_single_key("real_pos_count", real_pos_count)

    async def _fetch_margin_cross_balance(self):
        """Fetch margin balance in cross and estimated in btc."""
        balances = await exchange.margin_cross.fetch_balance()
        if balances["total"]["BNB"] > 0:
            cfg.BNB_QTY += balances["total"]["BNB"]
            if cfg.BNBUSDT == 0:
                await exchange.set_bnbusdt()

            if cfg.BNBUSDT > 0:
                cfg.BNB_BALANCE += cfg.BNB_QTY * cfg.BNBUSDT

        return float(balances["info"]["totalNetAssetOfBtc"])

    async def read_margin_cross_balance(self):
        if not self.CROSS_READ_FLAG:
            self.CROSS_READ_FLAG = True
            cfg.BALANCE_FLAG = True
            cfg.MARGIN_BAL_BTC = await self._fetch_margin_cross_balance()
            if cfg.MARGIN_BAL_BTC:
                cfg.MARGIN_BAL = int(float(cfg.MARGIN_BAL_BTC) * cfg.PRICES["BTCUSDT"])

    async def spot_balance(self, is_limit=True) -> Tuple[float, float, float, float]:
        """Calculate USDT balance in spot."""
        self.CROSS_READ_FLAG = False
        cfg.BNB_QTY = 0
        cfg.BNB_BALANCE = 0
        own_usdt: float = 0
        sum_usdt: float = 0
        sum_busd: float = 0
        sum_btc: float = 0
        only_usdt: float = 0
        only_btc: float = 0
        count: int = 0
        config.asset_list = []
        try:
            await self._fetch_balance()
        except Exception as e:
            if "Account has insufficient balance" in str(e):
                log("", is_write=False)

            log(f"E: {e}", is_write=False)

        for balance in cfg.BALANCES["info"]["balances"]:
            asset = balance["asset"]
            locked = float(balance["locked"])
            if float(balance["free"]) != 0 or locked != 0:
                quantity = float(balance["free"]) + locked
                if asset == "BTC":
                    only_btc = quantity
                    # TODO: store only_btc in mongodb for bal.py to fetch from
                    sum_btc += quantity
                    config._env.estimated_balance.add_single_key("only_btc", only_btc)
                elif asset not in cfg.STABLE_COINS:
                    price = await self.spot_fetch_ticker(f"{asset}{cfg.TYPE.upper()}")
                    if cfg.TYPE == "usdt":
                        usdt_amount = quantity * float(price)
                        if usdt_amount > 1:  # below 1$ would not be count as open position
                            config.btc_quantity[asset] = float(balance["free"]) + locked
                            config.asset_list.append(asset)
                            if asset not in config.SPOT_IGNORE_LIST:
                                count += 1
                    elif cfg.TYPE == "btc":
                        sum_btc += quantity * float(price)
                        usdt_amount = quantity * float(price) * cfg.PRICES["BTCUSDT"]
                        if usdt_amount > 1:
                            config.btc_quantity[asset] = float(balance["free"]) + locked
                            config.asset_list.append(asset)
                            if asset not in config.SPOT_IGNORE_LIST:
                                count += 1

                    sum_usdt += usdt_amount
                elif asset.lower() == "usdt":
                    only_usdt = quantity
                    sum_usdt += quantity
                elif asset.lower() == "busd":
                    sum_busd += quantity
                if asset.lower() == "bnb":
                    cfg.BNB_QTY += quantity
                    if cfg.BNBUSDT == 0:
                        output = await exchange.spot.fetch_ticker("BNBUSDT")
                        cfg.BNBUSDT = output["close"]

                    if cfg.BNBUSDT > 0:
                        cfg.BNB_BALANCE += quantity * cfg.BNBUSDT

        ts = config._env.status["timestamp"]
        config._env.estimated_balance.add_single_key("only_usdt", only_usdt)
        own_usdt = sum_btc * cfg.PRICES["BTCUSDT"]
        pos_count: int = config._env._status.find_one("count")["value"]
        real_pos_count: int = config._env._status.find_one("real_pos_count")["value"]
        if real_pos_count == 0:
            _console_clear()

        if sum_btc > 0.00002 and pos_count > 0:
            log(
                f" * btc=[m]%.8f[/m] [blue]==[/blue] [m]%.2f$[/m] [blue]*[/blue] "
                f"bnb=[cy]%.2f$[/cy] | [blue]{_date(_type='hour')}[/blue] {ts}" % (sum_btc, own_usdt, cfg.BNB_BALANCE)
            )
            cfg.SUM_BTC = sum_btc

        sum_usdt = float(format(sum_usdt, ".2f"))
        sum_busd = float(format(sum_busd, ".2f"))
        _sum_usdt = format(sum_usdt, ".2f")
        _da = f"[blue]{_date(_type='hour')}[/blue]"
        if not cfg.BALANCE_FLAG or "03:00:" in _da:
            await self.read_margin_cross_balance()

        if config._env.cross == "on":
            await self.read_margin_cross_balance()

        if len(config.asset_list) == 0 or config.env[cfg.TYPE].is_manual_trade:
            config.timestamp[f"{cfg.TYPE}_timestamp"] = {}  #: cleans timestamp.yaml file
            if cfg.TYPE == "usdt":
                #: estimated balance:
                _total_balance = float(_sum_usdt) + float(sum_busd)
                if cfg.MARGIN_BAL > 0.1:
                    _total_balance += float(cfg.MARGIN_BAL)
                    log(f"cross_usdt={cfg.MARGIN_BAL} | ", "bold", end="")
                else:
                    cfg.MARGIN_BAL = 0

                if config._env.cross == "on":
                    if (
                        config.env[cfg.TYPE].is_manual_trade
                        and abs(
                            _total_balance - float(config._env.estimated_balance.find_one("total_balance")["value"])
                        )
                        >= 100
                    ):
                        await self.read_margin_cross_balance()
                        _total_balance = float(_sum_usdt) + float(sum_busd) + float(cfg.MARGIN_BAL)

                    sum_btc += cfg.MARGIN_BAL_BTC

                if float(_total_balance) < 1 and config._env.isolated == "on":
                    _total_balance += await self._fetch_isolated_balance() * cfg.PRICES["BTCUSDT"]

                _total_balance = format(_total_balance, ".2f")
                _bnb = f"bnb=[cy]{format(cfg.BNB_BALANCE, '.2f')}[/cy]"
                perf_str = ""
                output = config._env.stats.find_one(cfg.CURRENT_DATE)
                if output:
                    perf_str = f"perf=[blue]{output['value']}[/blue]"

                log(
                    f":heavy_dollar_sign: [cy]${_total_balance}[/cy] | {_bnb} | {perf_str} | {_da} [italic cyan]{_timestamp()}"
                )
                config._env.estimated_balance.add_single_key("total_balance", _total_balance)
            elif cfg.TYPE == "btc":  #: calculating the estimated balance
                print_str = ":bee: "
                if only_btc > 0:
                    print_str += f"btc={only_btc} "

                # print(cfg.FIRST_PRINT_CYCLE)  # delete me
                if cfg.FIRST_PRINT_CYCLE:
                    if print_str != ":bee: ":
                        log(f"{print_str}| {_date()}")

                if cfg.MARGIN_BAL > 0.1:
                    own_usdt += float(cfg.MARGIN_BAL)
                    if sum_busd > 0.1:
                        print_str += f"busd={sum_busd + cfg.MARGIN_BAL} "
                    else:
                        print_str += f"cross_usdt={cfg.MARGIN_BAL} | "
                else:
                    cfg.MARGIN_BAL = 0

                own_usdt += sum_busd + only_usdt
                if config._env.cross == "on":
                    if (
                        config.env[cfg.TYPE].is_manual_trade
                        and abs(own_usdt - float(config._env.estimated_balance.find_one("total_balance")["value"]))
                        >= 100
                    ):
                        await self.read_margin_cross_balance()
                        own_usdt = sum_btc * cfg.PRICES["BTCUSDT"] + sum_busd + float(cfg.MARGIN_BAL)

                    sum_btc += cfg.MARGIN_BAL_BTC

                if config._env.isolated == "on":
                    own_usdt += await self._fetch_isolated_balance() * cfg.PRICES["BTCUSDT"]

                log(print_str, end="")
                if sum_busd > 0:
                    log(
                        "%.8f BTC[blue] ≈[/blue] [cy]$%.2f[/cy] "
                        % (sum_btc + (sum_busd / cfg.PRICES["BTCUSDT"]), own_usdt),
                        "bold",
                        end="",
                    )
                else:
                    log(
                        "%.8f BTC[blue] ≈[/blue] [cy]$%.2f[/cy] " % (sum_btc, own_usdt),
                        "bold",
                        end="",
                    )

                log(f"| bnb={format(cfg.BNB_BALANCE, '.2f')} | [bold]{_da}")
                config._env.estimated_balance.add_single_key("total_balance", own_usdt)
        elif cfg.TYPE == "usdt":
            busd_str = ""
            if sum_busd > 0.1:
                busd_str = f"| busd={sum_busd} "

            config._env.estimated_balance.add_single_key("total_balance", _sum_usdt)
            log(
                f" * usdt={_sum_usdt} {busd_str}[blue]*[/blue] "
                f"bnb=[cy]{format(cfg.BNB_BALANCE, '.2f')}[/cy] | {_da} {ts}"
            )

        if cfg.BNB_BALANCE < 0.5 and config.cfg["root"][cfg.TYPE]["auto_buy_bnb"] == "on":
            try:
                await self.buy_bnb()
            except Exception as e:
                if "InsufficientFunds" in str(e) or "insufficient balance" in str(e):
                    log(f"E: {e}")
                else:
                    print_tb(e)

        config.sum_usdt = sum_usdt
        if sum_usdt > 1.0 and pos_count == 0 and config._env.status["balance"] != sum_usdt:
            config._env.status["balance"] = sum_usdt

        if cfg.TYPE == "btc":
            config._env.status["balance"] = float(format(sum_btc, ".8f"))

        if cfg.TYPE == "usdt":
            _sum = sum_usdt + sum_busd
        else:
            _sum = sum_btc

        lost: float = 0
        cfg.locked_balance: float = 0
        cfg.discord_message = f"`{_date(_type='compact')}`\n"
        cfg.discord_message_full = f"`{_date(_type='compact')}`\n"
        if cfg.BALANCES:
            new_asset_list = []  # TODO: order asset based on their position size sort the list based on its size
            for asset in config.asset_list:
                balance = cfg.BALANCES[asset]["total"]
                if balance > 0:
                    new_asset_list.append(asset)

            for asset in config.asset_list:
                balance = cfg.BALANCES[asset]["total"]
                if balance > 0:
                    output = await self.spot_limit(asset, balance, _sum, is_limit)
                    lost += float(output)
                else:
                    log(f"{asset} balance is zero")
        else:
            for asset in config.asset_list:
                output = await self.spot_limit(asset, config.btc_quantity[asset], _sum, is_limit)
                lost += float(output)

        if cfg.TYPE == "usdt":
            free = format(float(config.env["usdt"].status["free"]), ".2f")
            if lost > -5:
                _msg = cfg.discord_message
            else:
                _msg = cfg.discord_message_full
        else:
            free = format(float(config.env["btc"].status["free"]), ".5f")
            if lost > -0.0001:
                _msg = cfg.discord_message
            else:
                _msg = cfg.discord_message_full

        cfg.locked_balance = min(float(cfg.locked_balance), 100)
        if cfg.locked_balance == 0:
            locked_per = ""
        else:
            if cfg.locked_balance >= 99.90:
                cfg.locked_balance = 100
                locked_per = ":lock:=`100%`"
            else:
                locked_per = f":lock:=`{format(cfg.locked_balance, '.2f')}%`"

        pos_str = ""
        if pos_count > 2:
            pos_str = f" | pos=**{pos_count}**"
        elif real_pos_count == 0:  # or (config.env[cfg.TYPE].is_manual_trade and real_pos_count == 0):
            log()  # to overwrite printed balance

        free = float(free)
        if cfg.TYPE == "usdt":
            _free = ""
            if free > 1:
                _free = f"| free=`{free}` "

            # total = round(abs(lost) + sum_usdt)
            if sum_busd > 0.1:
                if round(sum_usdt) > 0:
                    msg = (
                        f"{_msg}`{format(lost, '.2f')}$` usdt=`{round(sum_usdt)}` | busd=`{sum_busd}` {_free}"
                        f"{locked_per}"
                    )
                else:
                    llost = ""
                    if lost > 0:
                        llost = f"`${format(lost, '.2f')}` "

                    msg = (
                        f"{_msg}**:money_with_wings: `{_total_balance}`** {llost}| busd=`{sum_busd}` {_free}"
                        f"{locked_per}"
                    )
            elif int(sum_usdt) > 0:
                goal = round(float(sum_usdt) + float(abs(lost)))
                pnl = ""
                if lost > 0:
                    pnl = f"gain=`+{format(lost, '.2f')}` "
                    # pnl = f"lost=`{format(lost, '.2f')}` "

                if round(sum_usdt) != round(goal) and lost < 0:
                    msg = f"{_msg}**:lion_face: `{round(sum_usdt)}$`** {pnl}:dart:=`{goal}` {_free}{locked_per}"
                else:
                    msg = f"{_msg}**:lion_face: `{round(sum_usdt)}$`** {pnl} {_free}{locked_per}"
            else:
                if _msg[-1] == "\n":
                    msg = f"{_msg[:-1]}"
                else:
                    msg = f"{_msg}"

            config._env.balance_sum.add_single_key("btc", 0)
            config._env.balance_sum.add_single_key("usdt", format(sum_usdt, ".2f"))
        else:
            msg = _msg
            if free > 0:
                msg = f"{msg}free=`{free}` (`${format(free * cfg.PRICES['BTCUSDT'], '.2f')}`) "

            lost_usdt = format(float(lost) * cfg.PRICES["BTCUSDT"], ".2f")
            s_btc = format(sum_btc, ".5f")
            _b = float(s_btc) * cfg.PRICES["BTCUSDT"]
            u_btc = f"`${format(_b, '.2f')}`"
            if float(lost_usdt) < 0:
                msg = (
                    f"{msg}btc=**`{s_btc}` {u_btc} ** (**`{format(own_usdt, '.2f')}`:moneybag:**)\n"
                    f"**lost=`{lost_usdt}`** {locked_per} {pos_str}"
                )
            elif float(lost_usdt) == 0:
                # TODO: record this msg and print if a position opens in next cycle
                msg = (
                    f":bee: btc=`{s_btc}` ≈ {u_btc} + `${int(float(own_usdt) -_b)}` => **`${format(own_usdt, '.2f')}`**"
                )
            else:
                msg = (
                    f"{msg}btc=**`{format(sum_btc, '.5f')}`** (**`{format(own_usdt, '.2f')}`:moneybag:**)\n"
                    f"**gain=`+{lost_usdt}$`** {locked_per} {pos_str}"
                )

            config._env.balance_sum.add_single_key("btc", format(sum_btc, ".8f"))
            config._env.balance_sum.add_single_key("usdt", format(own_usdt, ".2f"))

        output = config._env.stats.find_one(cfg.CURRENT_DATE)
        if output:
            msg = f"{msg} perf=**{output['value']}**"

        if cfg.TYPE == "usdt":
            await self._discord_send(msg, format(lost, ".2f"), pos_count, "$", free)
        else:
            pnl = format(lost * 1000, ".5f")
            await self._discord_send(msg, pnl, pos_count, " mBTC", free)

        cfg.FIRST_PRINT_CYCLE = False
        config._env._status.add_single_key("count", count)
        self.update_timestamp_status()
        return own_usdt, sum_usdt, only_usdt, only_btc

    async def buy_bnb(self) -> bool:
        cfg.BNB_BALANCE = float(format(cfg.BNB_BALANCE, ".6f"))
        if cfg.TYPE == "btc":
            asset = "BNBBTC"
            amount: float = 0.0001104088
        else:
            asset = "BNBUSDT"
            amount: float = 10.3

        if float(config._env.status["free"]) < amount:
            return False

        output = await self.spot_fetch_ticker(asset)
        _amount = float(format(amount / output, ".3f"))
        log(
            f"#> buying minimum amount of [g]BNB[/g] bnb_balance={cfg.BNB_BALANCE} -- to_buy={_amount}",
            is_write=False,
            end="",
        )
        order = await exchange.spot.create_market_buy_order(asset, _amount)
        log(ok(), is_write=False)
        order = order["info"]
        for item in ["timeInForce", "orderListId", "price", "status", "type", "origQty", "executedQty"]:
            with suppress(Exception):
                del order[item]

        if order["symbol"] == "BNBBTC":
            for item in ["fills", "selfTradePreventionMode", "clientOrderId", "side", "workingTime"]:
                with suppress(Exception):
                    del order[item]

        log(order, is_write=False)
        return True

    async def spot_order(self, quantity, symbol, side, is_return=False, from_ex=False):
        if not from_ex:
            log(f"==> market_buy_order_quantity={quantity}")

        try:
            return await exchange.spot.create_market_buy_order(symbol, quantity)
        except Exception as e:
            _e = str(e)
            if "Account has insufficient balance" in _e:
                log("E: Account has insufficient balance for requested action", is_write=False)
                if is_return or from_ex or config._env.status["free"] < cfg.MINIMUM_POSITION[cfg.TYPE] * 4:
                    return

                quantity = quantity / 4  # re-try with much smalleer position size
                log(f"==> re-opening [green]{side}[/green] 1/4_of_quantity={quantity} for {symbol}")
                return await self.spot_order(quantity, symbol, side, is_return=True, from_ex=True)
            elif "Precision is over the maximum defined for this asset" in _e or "Filter failure: LOT_SIZE" in _e:
                log(f"E: {e} qty={quantity}")
                decimal = decimal_count(quantity)
                _quantity = f"{float(quantity):.{decimal - 1}f}"
                log(f"==> re-opening [green]{side}[/green] order qty={_quantity}")
                if float(_quantity) > 0:
                    return await self.spot_order(_quantity, symbol, side, from_ex=True)
                else:
                    log("E: quantity is zero, nothing to do", is_write=False)
            elif "Filter failure: MIN_NOTIONAL" in _e and quantity >= 0.1:
                quantity += 0.1
                #: fixes if its overrounded, ex: 1.2000000000000002
                quantity = float("{:.1f}".format(quantity))
                log(f"==> re-opening [green]{side}[/green] order qty={quantity}")
                return await self.spot_order(quantity, symbol, side, from_ex=True)
            else:
                print_tb(e)
                raise e

    async def spot_fetch_ticker(self, asset, is_bid_price=False) -> float:
        if not is_bid_price and asset in cfg.PRICES:
            if cfg.PRICES[asset] != 0:
                return cfg.PRICES[asset]

        try:
            if asset == "BTCUSDT":
                try:
                    #: helps to reduce request load to binance
                    price_ticker = await exchange.bitmex.fetch_ticker("BTC/USDT:USDT")
                except:
                    price_ticker = await exchange.spot.fetch_ticker(asset)
            else:
                price_ticker = await exchange.spot.fetch_ticker(asset)

            if is_bid_price:
                return float(price_ticker["info"]["bidPrice"])

            #: record prices in case could be used in the same cycle
            cfg.PRICES[asset] = price_ticker["last"]
            return float(price_ticker["last"])
        except Exception as e:
            if "binance does not have market symbol" in str(e):
                try:
                    if "USDT" in asset:
                        asset = asset.replace("USDT", "BUSD")
                        return await self.spot_fetch_ticker(asset, is_bid_price)
                    elif "BTC" in asset:
                        asset = asset.replace("BTC", "BUSD")
                        return await self.spot_fetch_ticker(asset, is_bid_price)
                except Exception:
                    # breakpoint()  # DEBUG
                    # TODO: maybe add taking price from mexc?
                    # return await self.spot_fetch_ticker(asset, is_bid_price)
                    raise e

            if "Connection reset by peer" in str(e):
                # TODO: maybe restart again or recall the function
                time.sleep(5)
                return await self.spot_fetch_ticker(asset, is_bid_price)

            print(str(e))
            raise e

    async def new_limit_order(self, asset, limit_price, market="BTC"):
        """Create new limit order with the added quantity."""
        symbol = f"{asset}/{market}"
        open_orders = await exchange.spot.fetch_open_orders(symbol)
        for order in open_orders:
            with suppress(Exception):
                # the order may already closed if there was a rapid change
                await exchange.spot.cancel_order(order["id"], symbol)

        try:
            balance = await self.fetch_balance(asset)
            # TODO: also call fetch_balance on discord balance
            response = await exchange.spot.create_limit_sell_order(symbol, balance, limit_price)
            log("==> [green]new_limit_order[/green]=", end="")
            if "info" in response:
                response = response["info"]

            with suppress(Exception):
                del response["status"]
                del response["clientOrderId"]
                del response["timeInForce"]
                del response["cummulativeQuoteQty"]
                del response["orderListId"]
                del response["executedQty"]
                del response["fills"]
                del response["selfTradePreventionMode"]
                del response["workingTime"]

            log(response, "bold cyan")
        except Exception as e:
            if type(e).__name__ != "InvalidOrder":
                log(f"E: Failed to create order with {symbol} [cy]{type(e).__name__}[/cy] {e}")
                raise e

    async def fetch_balance(self, code) -> float:
        self._fetch_balance()
        return cfg.BALANCES[code]["total"]

    async def _fetch_balance(self):
        key = f"{cfg.TYPE}_timestamp"
        pos_count = 0
        del_list = []
        ongoing_positions = []
        try:
            cfg.BALANCES = await exchange.spot.fetch_balance()
            for symbol in cfg.BALANCES:
                if symbol not in cfg.ignore_list and cfg.BALANCES[symbol]["total"] > 0:
                    ongoing_positions.append(symbol)
                    if symbol not in cfg.STABLE_COINS and symbol not in config.SPOT_IGNORE_LIST:
                        pos_count += 1

            for asset_timestamp in config.timestamp[key]:
                if asset_timestamp != "base" and asset_timestamp not in ongoing_positions:
                    del_list.append(asset_timestamp)

            for asset in del_list:
                del config.timestamp[key][asset]

            config.env[cfg.TYPE]._status.add_single_key("count", pos_count)
        except Exception as e:
            log(f"E: {e}")
