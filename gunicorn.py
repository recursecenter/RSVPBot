from threading import Thread
import os
import sys

sys.path.insert(0, os.getcwd())

import bot

def when_ready(server):
    t = Thread(target=bot.run_bot)
    # TODO: daemon threads are stopped abruptly when the process is killed.
    # we need to do some sort of graceful shutdown to make sure that all
    # database transactions are flushed. Maybe by using Event:
    # (https://docs.python.org/3/library/threading.html#threading.Event)
    t.daemon = True
    t.start()
