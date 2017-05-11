from threading import Thread
import os
import sys
import traceback

sys.path.insert(0, os.getcwd())

from bot import run_bot
from poller import run_poller

def keep_alive(f):
    def wrapped():
        while True:
            try:
                f()
            except BaseException as e:
                #traceback.print_exc(*sys.exc_info())
                print(traceback.format_exc())

    return wrapped

def when_ready(server):
    # TODO: daemon threads are stopped abruptly when the process is killed.
    # we need to do some sort of graceful shutdown to make sure that all
    # database transactions are flushed. Maybe by using Event:
    # (https://docs.python.org/3/library/threading.html#threading.Event)
    bot = Thread(target=keep_alive(run_bot))
    bot.daemon = True
    bot.start()

    poller = Thread(target=keep_alive(run_poller))
    poller.daemon = True
    poller.start()
