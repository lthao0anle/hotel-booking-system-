"""Bảng băm (Hash Table) tự cài đặt, xử lý va chạm bằng chaining.

Mỗi bucket là một danh sách liên kết đơn các cặp (key, value).
Khi hệ số tải (size / capacity) vượt quá 0.75, bảng được nhân đôi (rehash)
để giữ chiều dài chuỗi trung bình là hằng số.

Độ phức tạp:
    put / get / remove / contains : O(1) trung bình, O(n) xấu nhất
    rehash                        : O(n), nhưng khấu hao O(1) mỗi lần put
"""

_INITIAL_CAPACITY = 16
_MAX_LOAD_FACTOR = 0.75
_HASH_BASE = 31
_HASH_MOD = (1 << 61) - 1


class _Entry:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next_entry):
        self.key = key
        self.value = value
        self.next = next_entry


def polynomial_hash(key):
    """Hàm băm đa thức cho chuỗi: h = (c0*B^(n-1) + ... + c(n-1)) mod M.

    Với khóa không phải chuỗi, chuyển về chuỗi bằng repr() để vẫn dùng chung
    một hàm băm tự cài đặt.
    """
    text = key if isinstance(key, str) else repr(key)
    value = 0
    for char in text:
        value = (value * _HASH_BASE + ord(char)) % _HASH_MOD
    return value


class HashTable:
    def __init__(self, capacity=_INITIAL_CAPACITY):
        self._capacity = max(1, capacity)
        self._buckets = [None] * self._capacity
        self._size = 0

    def put(self, key, value):
        """Thêm mới hoặc ghi đè giá trị của key."""
        index = self._index_of(key)
        entry = self._buckets[index]
        while entry is not None:
            if entry.key == key:
                entry.value = value
                return
            entry = entry.next
        self._buckets[index] = _Entry(key, value, self._buckets[index])
        self._size += 1
        if self._size / self._capacity > _MAX_LOAD_FACTOR:
            self._resize(self._capacity * 2)

    def get(self, key, default=None):
        entry = self._find_entry(key)
        return default if entry is None else entry.value

    def contains(self, key):
        return self._find_entry(key) is not None

    def remove(self, key):
        """Xóa key. Trả về True nếu key tồn tại."""
        index = self._index_of(key)
        previous = None
        entry = self._buckets[index]
        while entry is not None:
            if entry.key == key:
                if previous is None:
                    self._buckets[index] = entry.next
                else:
                    previous.next = entry.next
                self._size -= 1
                return True
            previous, entry = entry, entry.next
        return False

    def keys(self):
        return [key for key, _ in self.items()]

    def values(self):
        return [value for _, value in self.items()]

    def items(self):
        for head in self._buckets:
            entry = head
            while entry is not None:
                yield entry.key, entry.value
                entry = entry.next

    def __len__(self):
        return self._size

    def __contains__(self, key):
        return self.contains(key)

    # ------------------------------------------------------------------ #
    def _index_of(self, key):
        return polynomial_hash(key) % self._capacity

    def _find_entry(self, key):
        entry = self._buckets[self._index_of(key)]
        while entry is not None:
            if entry.key == key:
                return entry
            entry = entry.next
        return None

    def _resize(self, new_capacity):
        old_items = list(self.items())
        self._capacity = new_capacity
        self._buckets = [None] * new_capacity
        self._size = 0
        for key, value in old_items:
            index = self._index_of(key)
            self._buckets[index] = _Entry(key, value, self._buckets[index])
            self._size += 1
