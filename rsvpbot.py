#Do this early in case anything depends on .env
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from threading import Thread
import traceback
import signal

from bot import run_bot
from poller import run_poller
import atom

running = atom.Atom(True)

def shutdown(signum, frame):
    running.value = False
    print("RSVPBot shutting down...")

def keep_alive(f, *args):
    def wrapped():
        while True:
            try:
                f(*args)
            except Exception as e:
                print(traceback.format_exc())

    return wrapped

def start():
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    bot = Thread(target=keep_alive(run_bot, running))
    bot.start()

    poller = Thread(target=keep_alive(run_poller, running))
    poller.start()

    bot.join()
    poller.join()


if __name__ == "__main__":
    start()
