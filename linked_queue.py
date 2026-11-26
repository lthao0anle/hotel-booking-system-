"""Hàng đợi FIFO (Queue) cài đặt bằng danh sách liên kết.

Dùng cho danh sách chờ của khách thường (đến trước phục vụ trước).

Độ phức tạp: enqueue O(1), dequeue O(1), peek O(1).
"""


class _QueueNode:
    __slots__ = ("value", "next")

    def __init__(self, value):
        self.value = value
        self.next = None


class LinkedQueue:
    def __init__(self):
        self._front = None
        self._rear = None
        self._size = 0

    def enqueue(self, value):
        """Thêm vào cuối hàng — O(1)."""
        node = _QueueNode(value)
        if self._rear is None:
            self._front = self._rear = node
        else:
            self._rear.next = node
            self._rear = node
        self._size += 1

    def dequeue(self):
        """Lấy phần tử ở đầu hàng — O(1)."""
        if self._front is None:
            raise IndexError("Hàng đợi rỗng")
        node = self._front
        self._front = node.next
        if self._front is None:
            self._rear = None
        self._size -= 1
        return node.value

    def peek(self):
        if self._front is None:
            raise IndexError("Hàng đợi rỗng")
        return self._front.value

    def is_empty(self):
        return self._size == 0

    def __len__(self):
        return self._size

    def __iter__(self):
        """Duyệt từ đầu hàng tới cuối hàng (không làm thay đổi hàng đợi)."""
        current = self._front
        while current is not None:
            yield current.value
            current = current.next

    def remove_first(self, predicate):
        """Xóa và trả về phần tử đầu tiên thỏa predicate, hoặc None."""
        previous = None
        current = self._front
        while current is not None:
            if predicate(current.value):
                if previous is None:
                    self._front = current.next
                else:
                    previous.next = current.next
                if current is self._rear:
                    self._rear = previous
                self._size -= 1
                return current.value
            previous, current = current, current.next
        return None

