#!/usr/bin/env python3

import sys

from broker._utils.tools import print_tb

from bot._cli.helper import Helper

try:
    helper = Helper()
    parser = helper.get_parser()
    _args = parser.parse_args()
    console_fn = __file__.replace("__main__", "console")
except KeyboardInterrupt:
    sys.exit(1)


def about():
    from os.path import expanduser

    from broker._utils._log import log

    try:
        fn = "~/.bot/config.yaml"
        with open(expanduser(fn), "r") as f:
            flag = True
            indent = 2
            for line in f:
                if flag:
                    if "  " in line[:2]:
                        flag = False
                        if "    " in line[:4]:
                            indent = 4

                if "cfg" not in line and " " * indent in line[:indent]:
                    line = line[indent:]
                    log(line.rstrip(), is_write=False)
    except KeyboardInterrupt:
        sys.exit(1)


def get_tag_version() -> str:
    from subprocess import check_output

    __version__ = check_output(["git", "describe", "--tags", "--abbrev=0"])
    return __version__.decode("utf-8").replace("\n", "")


def main():  # noqa
    try:
        globals()[_args.command]()
    except KeyError:
        print(f"ebloc-broker {get_tag_version()} - Blockchain based autonomous computational resource broker\n")
        parser.print_help()
    except Exception as e:
        print_tb(e)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
