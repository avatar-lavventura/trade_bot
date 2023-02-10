#!/usr/bin/env python3

import sys


def main():
    fn = sys.argv[1]
    _type = sys.argv[2]
    with open(fn) as f:
        for line in f:
            _line = line.rstrip()
            print(f"{_line},{_line.replace(_type, '').replace('BINANCE:', '')},{_type},")


if __name__ == "__main__":
    main()
