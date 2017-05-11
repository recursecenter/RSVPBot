from threading import Thread
import os
import sys

sys.path.insert(0, os.getcwd())

from bot import run_bot
from poller import run_poller

def when_ready(server):
    # TODO: daemon threads are stopped abruptly when the process is killed.
    # we need to do some sort of graceful shutdown to make sure that all
    # database transactions are flushed. Maybe by using Event:
    # (https://docs.python.org/3/library/threading.html#threading.Event)
    bot = Thread(target=run_bot)
    bot.daemon = True
    bot.start()

    poller = Thread(target=run_poller)
    poller.daemon = True
    poller.start()
