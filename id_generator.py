"""Bộ sinh mã tăng dần, ví dụ KH001, KH002... hoặc BK00001, BK00002..."""


class SequenceGenerator:
    def __init__(self, prefix, width, current=0):
        self._prefix = prefix
        self._width = width
        self._current = current

    @property
    def current(self):
        return self._current

    def restore(self, current):
        """Khôi phục bộ đếm khi nạp dữ liệu từ file."""
        self._current = max(self._current, int(current))

    def next_number(self):
        self._current += 1
        return self._current

    def next_id(self):
        return f"{self._prefix}{self.next_number():0{self._width}d}"
