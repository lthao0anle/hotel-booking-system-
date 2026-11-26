"""Danh sách liên kết đơn (Singly Linked List) tự cài đặt.

Dùng để lưu lịch sử lưu trú của khách hàng: lượt đặt mới nhất được chèn
vào đầu danh sách nên thao tác thêm luôn là O(1).

Độ phức tạp:
    push_front  : O(1)
    push_back   : O(1)   (nhờ giữ con trỏ tail)
    find        : O(m)
    remove_first: O(m)
    duyệt       : O(m)   (m = số phần tử)
"""


class _ListNode:
    __slots__ = ("value", "next")

    def __init__(self, value, next_node=None):
        self.value = value
        self.next = next_node


class SinglyLinkedList:
    def __init__(self):
        self._head = None
        self._tail = None
        self._size = 0

    def push_front(self, value):
        """Chèn vào đầu danh sách — O(1)."""
        node = _ListNode(value, self._head)
        self._head = node
        if self._tail is None:
            self._tail = node
        self._size += 1

    def push_back(self, value):
        """Chèn vào cuối danh sách — O(1)."""
        node = _ListNode(value)
        if self._tail is None:
            self._head = self._tail = node
        else:
            self._tail.next = node
            self._tail = node
        self._size += 1

    def peek_front(self):
        if self._head is None:
            raise IndexError("Danh sách rỗng")
        return self._head.value

    def find(self, predicate):
        """Trả về phần tử đầu tiên thỏa predicate, hoặc None — O(m)."""
        current = self._head
        while current is not None:
            if predicate(current.value):
                return current.value
            current = current.next
        return None

    def remove_first(self, predicate):
        """Xóa phần tử đầu tiên thỏa predicate. Trả về True nếu xóa được — O(m)."""
        previous = None
        current = self._head
        while current is not None:
            if predicate(current.value):
                self._unlink(previous, current)
                return True
            previous, current = current, current.next
        return False

    def _unlink(self, previous, current):
        if previous is None:
            self._head = current.next
        else:
            previous.next = current.next
        if current is self._tail:
            self._tail = previous
        self._size -= 1

    def to_list(self):
        return [value for value in self]

    def is_empty(self):
        return self._size == 0

    def __len__(self):
        return self._size

    def __iter__(self):
        current = self._head
        while current is not None:
            yield current.value
            current = current.next
