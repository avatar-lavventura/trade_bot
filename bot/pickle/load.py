#!/usr/bin/env python3

import asyncio
import pickle

exchange = None
_file = ".secret.pk"
with open(_file, "rb") as f:
    exchange = pickle.load(f)


async def func():
    output = await exchange.fetch_positions()
    print(output)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(func())
    loop.run_forever()
    loop.close()
