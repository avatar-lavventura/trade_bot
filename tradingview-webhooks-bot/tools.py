#!/usr/bin/env python3

import os
import sys
import threading
import traceback
from datetime import datetime

import pytz
from pygments import formatters, highlight, lexers
from pytz import timezone
from rich.traceback import install
from termcolor import colored

install()  # for rich

log_files = {}


class COLOR:
    BOLD = "\033[1m"
    PURPLE = "\033[95m"
    BLUE = "\033[94m"
    RED = "\033[91m"
    DEFAULT = "\033[99m"
    GREY = "\033[90m"
    YELLOW = "\033[93m"
    BLACK = "\033[90m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    MAGENTA = "\033[95m"
    WHITE = "'\033[97m"
    END = "\033[0m"


def WHERE(back=0):
    try:
        frame = sys._getframe(back + 1)
    except:
        frame = sys._getframe(1)
    return f"{os.path.basename(frame.f_code.co_filename)}:{frame.f_lineno}"


def _time():
    _format = "%Y-%m-%d %H:%M:%S"
    country_time = datetime.now(timezone("Europe/Istanbul"))
    return country_time.strftime(_format)


def timestamp_to_local(posix_time: int, zone="Europe/Istanbul"):
    ts = posix_time / 1000.0
    tz = pytz.timezone(zone)
    return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M:%S")


def utc_to_local(utc_dt, zone="Europe/Istanbul"):
    # dt.strftime("%d/%m/%Y") # to get the date
    local_tz = pytz.timezone(zone)
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


def _colorize_traceback(string=None):
    """Logs the traceback."""
    tb_text = "".join(traceback.format_exc())
    lexer = lexers.get_lexer_by_name("pytb", stripall=True)
    # to check: print $terminfo[colors]
    formatter = formatters.get_formatter_by_name("terminal")
    tb_colored = highlight(tb_text, lexer, formatter)
    if not string:
        log(f"{[WHERE(1)]} ", "blue", None)
    else:
        log(f"[{WHERE(1)} {string}] ", "blue", None, end=False)

    _tb_colored = tb_colored.rstrip()
    if not _tb_colored:
        log(_tb_colored)


def print_color(text, color=None, is_bold=True, end=None):
    if str(text)[0:3] in ["==>", "#> ", "## "]:
        print(colored(f"{COLOR.BOLD}{str(text)[0:3]}{COLOR.END}", color="blue"), end="", flush=True)
        text = text[3:]
    elif str(text)[0:2] == "E:":
        print(colored(f"{COLOR.BOLD}E:{COLOR.END}", color="red"), end="", flush=True)
        text = text[2:]

    if end is None:
        if is_bold:
            print(colored(f"{COLOR.BOLD}{text}{COLOR.END}", color))
        else:
            print(colored(text, color))
    elif end == "":
        if is_bold:
            print(colored(f"{COLOR.BOLD}{text}{COLOR.END}", color), end="", flush=True)
        else:
            print(colored(text, color), end="")


def log(text="", color=None, filename=None, end=None, is_bold=True, flush=False):
    text = str(text)
    is_arrow = False
    is_error = False
    _len = None

    if text == "[ ok ]":
        text = f"[ {COLOR.GREEN}ok{COLOR.END} ]"

    if not color:
        if text[:3] in ["==>", "#> ", "## ", " * "]:
            _len = 3
            _color = "blue"
            is_arrow = True
        elif text[:8] in ["Warning:"]:
            _len = 8
            _color = "yellow"
            is_arrow = True
        elif text[:2] == "E:":
            _len = 2
            _color = "red"
            is_error = True
        elif text == "SUCCESS":
            color = "green"
        elif text in ["FAILED", "ERROR"]:
            color = "red"

    filename = "program.log"
    f = open(filename, "a")
    if color:
        if is_bold:
            _text = f"{COLOR.BOLD}{text}{COLOR.END}"
        else:
            _text = text

        if threading.current_thread().name == "MainThread":
            if is_arrow or is_error:
                print(
                    colored(f"{COLOR.BOLD}{text[:_len]}{COLOR.END}", color=_color)
                    + f"{COLOR.BOLD}{text[_len:]}{COLOR.END}",
                    end=end,
                    flush=flush,
                )
            else:
                print_color(colored(text, color), color, is_bold, end)

        if is_bold:
            _text = f"{COLOR.BOLD}{text[_len:]}{COLOR.END}"
        else:
            _text = text[_len:]

        if is_arrow or is_error:
            f.write(colored(f"{COLOR.BOLD}{text[:_len]}{COLOR.END}", color=_color) + colored(_text, color))
        else:
            f.write(colored(_text, color))
    else:
        text_write = ""
        if is_arrow or is_error:
            text_write = (
                colored(f"{COLOR.BOLD}{text[:_len]}{COLOR.END}", color=_color) + f"{COLOR.BOLD}{text[_len:]}{COLOR.END}"
            )
        else:
            text_write = text

        print(text_write, end=end, flush=flush)
        f.write(text_write)

    if end is None:
        f.write("\n")

    f.close()
