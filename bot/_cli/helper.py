#!/usr/bin/env python3

import argparse
from argparse import RawTextHelpFormatter

# PYTHON_ARGCOMPLETE_OK
import argcomplete
from argcomplete.completers import EnvironCompleter


class Helper:
    """Guide for arguments."""

    def __init__(self):
        """Initialize helper.

        test: ./_cli/__main__.py -h
        activate-global-python-argcomplete --user
        eval "$(register-python-argcomplete ~/venv/bin/eblocbroker)"

        __ https://github.com/kislyuk/argcomplete
        __ https://stackoverflow.com/questions/14597466/custom-tab-completion-in-python-argparse
        """
        self.parser = argparse.ArgumentParser(
            "eblocbroker",
            epilog="Type 'eblocbroker <command> --help' for specific options and more information\nabout each command.",
            usage="usage: %(prog)s [-h] command [<options>...]",
            formatter_class=RawTextHelpFormatter,
        )
        self.parser._positionals.title = "Commands"
        self.parser._optionals.title = "Options"
        self.subparsers = self.parser.add_subparsers(dest="command", metavar="command [<options>...]")
        self.subparsers.add_parser("about", help="alpy-bot metadata")
        self.init()
        argcomplete.autocomplete(self.parser)

    def get_args(self):
        return self.parser.parse_args()

    def get_parser(self) -> argparse.ArgumentParser:
        return self.parser

    def init(self):
        obj = self.subparsers.add_parser("init", help="Initialize the ebloc-broker project")
        obj.add_argument(
            "--base", action="store_true", help="Set cfg.py file with initial values"
        ).completer = EnvironCompleter
        obj.set_defaults(is_base=None)
