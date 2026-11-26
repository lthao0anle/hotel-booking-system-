"""Lịch đặt của MỘT phòng: tập các khoảng thời gian nửa mở [start, end)
KHÔNG giao nhau, lưu trong BST (AVL) với khóa là ngày bắt đầu (check-in).

Điều kiện giao nhau của [A, B) và [C, D):   A < D  và  C < B.

Ý tưởng kiểm tra xung đột O(log n):
    Vì các khoảng trong lịch không giao nhau, khi sắp theo ngày bắt đầu thì
    ngày kết thúc cũng tăng dần. Do đó, trong số các khoảng có start < B,
    khoảng có start LỚN NHẤT (phần tử "lower" của B trong BST) cũng là khoảng
    có end lớn nhất. Khoảng mới [A, B) xung đột  <=>  khoảng đó tồn tại và
    có end > A. Chỉ cần MỘT lần tìm kiếm trên cây -> O(log n).

Bất biến (invariant) được lớp này tự bảo vệ: `add` từ chối mọi khoảng gây
xung đột, nên lập luận trên luôn đúng.
"""

from hotel.data_structures.avl_tree import AVLTree


class IntervalSchedule:
    def __init__(self, start_of, end_of):
        """start_of(item) / end_of(item) trích ngày bắt đầu / kết thúc của phần tử."""
        self._tree = AVLTree()
        self._start_of = start_of
        self._end_of = end_of

    def find_conflict(self, start, end):
        """Phần tử đang chiếm một phần [start, end), hoặc None — O(log n)."""
        if not start < end:
            raise ValueError("Ngày bắt đầu phải nhỏ hơn ngày kết thúc")
        candidate = self._tree.lower_entry(end)
        if candidate is None:
            return None
        item = candidate[1]
        return item if self._end_of(item) > start else None

    def is_free(self, start, end):
        return self.find_conflict(start, end) is None

    def find_covering(self, moment):
        """Phần tử có start <= moment < end, hoặc None — O(log n)."""
        candidate = self._tree.floor_entry(moment)
        if candidate is None:
            return None
        item = candidate[1]
        return item if self._end_of(item) > moment else None

    def add(self, item):
        """Thêm phần tử; ném ValueError nếu xung đột — O(log n)."""
        start, end = self._start_of(item), self._end_of(item)
        conflict = self.find_conflict(start, end)
        if conflict is not None:
            raise ValueError("Khoảng thời gian bị trùng với một lịch đã có")
        self._tree.insert(start, item)

    def remove(self, item):
        """Xóa phần tử (tìm theo ngày bắt đầu) — O(log n)."""
        start = self._start_of(item)
        if self._tree.get(start) is not item:
            raise KeyError("Phần tử không có trong lịch")
        self._tree.remove(start)

    def items_starting_between(self, low, high):
        """Các phần tử có ngày bắt đầu trong [low, high] — O(log n + r)."""
        return [item for _, item in self._tree.range_items(low, high)]

    def items(self):
        return self._tree.values()

    @property
    def height(self):
        return self._tree.height

    def __len__(self):
        return len(self._tree)

    def __contains__(self, item):
        return self._tree.get(self._start_of(item)) is item
