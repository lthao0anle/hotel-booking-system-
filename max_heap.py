"""Hàng đợi ưu tiên (Priority Queue) cài đặt bằng Max-Heap trên mảng.

Phần tử có khóa ưu tiên LỚN NHẤT luôn nằm ở gốc (chỉ số 0).
Với nút ở chỉ số i: con trái = 2i + 1, con phải = 2i + 2, cha = (i - 1) // 2.

Hàm `priority_key(item)` trả về một giá trị so sánh được (thường là tuple),
ví dụ `(vip_level, -sequence)` để cùng cấp VIP thì ai đến trước được ưu tiên.

Độ phức tạp (k = số phần tử):
    push : O(log k)   — sift-up
    pop  : O(log k)   — sift-down
    peek : O(1)
"""


class MaxHeap:
    def __init__(self, priority_key):
        self._items = []
        self._priority_key = priority_key

    def push(self, item):
        self._items.append(item)
        self._sift_up(len(self._items) - 1)

    def pop(self):
        if not self._items:
            raise IndexError("Hàng đợi ưu tiên rỗng")
        top = self._items[0]
        last = self._items.pop()
        if self._items:
            self._items[0] = last
            self._sift_down(0)
        return top

    def peek(self):
        if not self._items:
            raise IndexError("Hàng đợi ưu tiên rỗng")
        return self._items[0]

    def is_empty(self):
        return not self._items

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        """Duyệt theo thứ tự lưu trong mảng heap (KHÔNG theo độ ưu tiên)."""
        return iter(list(self._items))

    def to_sorted_list(self):
        """Danh sách theo thứ tự ưu tiên giảm dần, không làm thay đổi heap — O(k log k)."""
        clone = MaxHeap(self._priority_key)
        clone._items = list(self._items)
        result = []
        while not clone.is_empty():
            result.append(clone.pop())
        return result

    def remove_at(self, index):
        """Xóa phần tử tại chỉ số `index` và khôi phục tính chất heap — O(log k)."""
        if not 0 <= index < len(self._items):
            raise IndexError("Chỉ số nằm ngoài phạm vi heap")
        removed = self._items[index]
        last = self._items.pop()
        if index < len(self._items):
            self._items[index] = last
            self._sift_up(index)
            self._sift_down(index)
        return removed

    def remove_first(self, predicate):
        """Tìm phần tử đầu tiên thỏa predicate và xóa ở O(log k) bước vun đống."""
        for index, item in enumerate(self._items):
            if predicate(item):
                return self.remove_at(index)
        return None

    def update_key_at(self, index):
        """Khôi phục tính chất heap sau khi khóa ưu tiên tại `index` thay đổi — O(log k)."""
        if not 0 <= index < len(self._items):
            raise IndexError("Chỉ số nằm ngoài phạm vi heap")
        self._sift_up(index)
        self._sift_down(index)


    # ------------------------------------------------------------------ #
    def _higher(self, i, j):
        return self._priority_key(self._items[i]) > self._priority_key(self._items[j])

    def _swap(self, i, j):
        self._items[i], self._items[j] = self._items[j], self._items[i]

    def _sift_up(self, index):
        while index > 0:
            parent = (index - 1) // 2
            if not self._higher(index, parent):
                break
            self._swap(index, parent)
            index = parent

    def _sift_down(self, index):
        size = len(self._items)
        while True:
            largest = index
            left, right = 2 * index + 1, 2 * index + 2
            if left < size and self._higher(left, largest):
                largest = left
            if right < size and self._higher(right, largest):
                largest = right
            if largest == index:
                return
            self._swap(index, largest)
            index = largest
