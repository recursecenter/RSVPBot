import threading

class Atom:
    def __init__(self, value):
        self._value = value
        self.lock = threading.Lock()

    @property
    def value(self):
        with self.lock:
            return self._value

    @value.setter
    def value(self, value):
        with self.lock:
            self._value = value
