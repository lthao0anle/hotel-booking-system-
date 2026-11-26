"""Ngăn xếp (Stack) LIFO cài đặt bằng danh sách liên kết.

Dùng để lưu các thao tác hủy đặt phòng, phục vụ chức năng hoàn tác (undo).

Độ phức tạp: push O(1), pop O(1), peek O(1).
"""


class _StackNode:
    __slots__ = ("value", "below")

    def __init__(self, value, below):
        self.value = value
        self.below = below


class Stack:
    def __init__(self):
        self._top = None
        self._size = 0

    def push(self, value):
        """Đẩy phần tử lên đỉnh — O(1)."""
        self._top = _StackNode(value, self._top)
        self._size += 1

    def pop(self):
        """Lấy phần tử ở đỉnh — O(1)."""
        if self._top is None:
            raise IndexError("Ngăn xếp rỗng")
        node = self._top
        self._top = node.below
        self._size -= 1
        return node.value

    def peek(self):
        if self._top is None:
            raise IndexError("Ngăn xếp rỗng")
        return self._top.value

    def is_empty(self):
        return self._size == 0

    def __len__(self):
        return self._size

    def __iter__(self):
        """Duyệt từ đỉnh xuống đáy."""
        current = self._top
        while current is not None:
            yield current.value
            current = current.below
