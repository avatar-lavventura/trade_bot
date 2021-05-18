#!/usr/bin/env python3

import asyncio
import itertools
import threading
import time

__all__ = ["EventLoopThread", "get_event_loop", "stop_event_loop", "run_coroutine"]


"""doc: https://stackoverflow.com/a/58616001/2402577

This is not thread safe, you can't simply use loop.run_until_complete() from
arbitrary threads. An asyncio loop is thread specific. Any real-life WSGI
deployment will be using threads. Instead of calling asyncio.get_event_loop()
you'd have to create a new event loop per thread.

That's... overkill however. not thread safe means that things can break because
multiple threads are altering the same data structures unless you take threading
into account. The asyncio event loop implementation is not thread safe apart
from a few explicitly documented functions. The code here doesn't create a new
event loop per thread, nor does it pass coroutines to the single thread
correctly. Note that I also posted an answer to this question that addresses
these issues better.

In fact, that's how most WSGI setups will work; either the main thread is going
to busy dispatching requests, or the Flask server is imported as a module in a
WSGI server, and you can't start an event loop here either.

Here is an implementation of a module that will run such an event loop thread,
and gives you the utilities to schedule coroutines to be run in that loop:
"""


class EventLoopThread(threading.Thread):
    loop = None
    _count = itertools.count(0)

    def __init__(self):
        name = f"{type(self).__name__}-{next(self._count)}"
        super().__init__(name=name, daemon=True)

    def __repr__(self):
        loop, r, c, d = self.loop, False, True, False
        if loop is not None:
            r, c, d = loop.is_running(), loop.is_closed(), loop.get_debug()
        return f"<{type(self).__name__} {self.name} id={self.ident} running={r} closed={c} debug={d}>"

    def run(self):
        self.loop = loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_forever()
        finally:
            try:
                shutdown_asyncgens = loop.shutdown_asyncgens()
            except AttributeError:
                pass
            else:
                loop.run_until_complete(shutdown_asyncgens)
            loop.close()
            asyncio.set_event_loop(None)

    def stop(self):
        loop, self.loop = self.loop, None
        if loop is None:
            return
        loop.call_soon_threadsafe(loop.stop)
        self.join()


_lock = threading.Lock()
_loop_thread = None


def get_event_loop():
    global _loop_thread

    if _loop_thread is None:
        with _lock:
            if _loop_thread is None:
                _loop_thread = EventLoopThread()
                _loop_thread.start()
                # give the thread up to a second to produce a loop
                deadline = time.time() + 1
                while not _loop_thread.loop and time.time() < deadline:
                    time.sleep(0.001)

    return _loop_thread.loop


def stop_event_loop():
    global _loop_thread
    with _lock:
        if _loop_thread is not None:
            _loop_thread.stop()
            _loop_thread = None


def run_coroutine(coro):
    """Run the coroutine in the event loop running in a separate thread

    Returns a Future, call Future.result() to get the output

    """
    return asyncio.run_coroutine_threadsafe(coro, get_event_loop())
