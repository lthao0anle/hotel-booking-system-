"""Cây nhị phân tìm kiếm tự cân bằng (AVL Tree).

Đây là một BST thông thường (mọi khóa ở cây con trái < khóa của nút < mọi khóa
ở cây con phải), được bổ sung thao tác xoay (rotation) sau mỗi lần chèn/xóa
để chênh lệch chiều cao hai cây con không vượt quá 1.

Lý do cần cân bằng: các đơn đặt phòng thường được tạo theo thứ tự ngày tăng
dần; với BST thường, cây sẽ suy biến thành danh sách liên kết và mọi thao tác
trở thành O(n). AVL đảm bảo chiều cao h = O(log n) nên các thao tác dưới đây
đạt O(log n) trong MỌI trường hợp.

Độ phức tạp (n = số nút):
    insert / remove / get        : O(log n)
    lower_entry / floor_entry    : O(log n)
    range_items(lo, hi)          : O(log n + r)   (r = số kết quả)
    items (duyệt trung thứ tự)   : O(n)
"""


class _AVLNode:
    __slots__ = ("key", "value", "left", "right", "height")

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.height = 1


def _height(node):
    return node.height if node is not None else 0


def _update_height(node):
    node.height = 1 + max(_height(node.left), _height(node.right))


def _balance_factor(node):
    return _height(node.left) - _height(node.right)


def _rotate_right(y):
    x = y.left
    y.left = x.right
    x.right = y
    _update_height(y)
    _update_height(x)
    return x


def _rotate_left(x):
    y = x.right
    x.right = y.left
    y.left = x
    _update_height(x)
    _update_height(y)
    return y


def _rebalance(node):
    _update_height(node)
    balance = _balance_factor(node)
    if balance > 1:                                   # lệch trái
        if _balance_factor(node.left) < 0:            # trường hợp Trái-Phải
            node.left = _rotate_left(node.left)
        return _rotate_right(node)
    if balance < -1:                                  # lệch phải
        if _balance_factor(node.right) > 0:           # trường hợp Phải-Trái
            node.right = _rotate_right(node.right)
        return _rotate_left(node)
    return node


class AVLTree:
    def __init__(self):
        self._root = None
        self._size = 0

    # ----------------------------- Truy vấn ----------------------------- #
    def get(self, key, default=None):
        node = self._root
        while node is not None:
            if key < node.key:
                node = node.left
            elif key > node.key:
                node = node.right
            else:
                return node.value
        return default

    def contains(self, key):
        sentinel = object()
        return self.get(key, sentinel) is not sentinel

    def lower_entry(self, key):
        """Cặp (khóa, giá trị) có khóa LỚN NHẤT mà nhỏ hơn hẳn `key`, hoặc None."""
        best = None
        node = self._root
        while node is not None:
            if node.key < key:
                best = node
                node = node.right
            else:
                node = node.left
        return None if best is None else (best.key, best.value)

    def floor_entry(self, key):
        """Cặp (khóa, giá trị) có khóa LỚN NHẤT mà nhỏ hơn hoặc bằng `key`, hoặc None."""
        best = None
        node = self._root
        while node is not None:
            if node.key <= key:
                best = node
                node = node.right
            else:
                node = node.left
        return None if best is None else (best.key, best.value)

    def range_items(self, low, high):
        """Các cặp (khóa, giá trị) với low <= khóa <= high, theo thứ tự tăng dần."""
        result = []
        self._collect_range(self._root, low, high, result)
        return result

    def items(self):
        """Duyệt trung thứ tự (in-order) không đệ quy — các khóa tăng dần."""
        stack = []
        node = self._root
        while stack or node is not None:
            while node is not None:
                stack.append(node)
                node = node.left
            node = stack.pop()
            yield node.key, node.value
            node = node.right

    def values(self):
        return [value for _, value in self.items()]

    @property
    def height(self):
        return _height(self._root)

    def __len__(self):
        return self._size

    def __contains__(self, key):
        return self.contains(key)

    # --------------------------- Cập nhật ------------------------------- #
    def insert(self, key, value):
        """Chèn khóa mới. Ném KeyError nếu khóa đã tồn tại."""
        self._root = self._insert(self._root, key, value)
        self._size += 1

    def remove(self, key):
        """Xóa khóa và trả về giá trị tương ứng. Ném KeyError nếu không có."""
        removed = []
        self._root = self._remove(self._root, key, removed)
        self._size -= 1
        return removed[0]

    # --------------------------- Nội bộ --------------------------------- #
    def _insert(self, node, key, value):
        if node is None:
            return _AVLNode(key, value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            raise KeyError(f"Khóa {key!r} đã tồn tại trong cây")
        return _rebalance(node)

    def _remove(self, node, key, removed):
        if node is None:
            raise KeyError(f"Không tìm thấy khóa {key!r}")
        if key < node.key:
            node.left = self._remove(node.left, key, removed)
        elif key > node.key:
            node.right = self._remove(node.right, key, removed)
        else:
            removed.append(node.value)
            if node.left is None:
                return node.right
            if node.right is None:
                return node.left
            successor = node.right
            while successor.left is not None:
                successor = successor.left
            node.key, node.value = successor.key, successor.value
            node.right = self._remove(node.right, successor.key, [])
        return _rebalance(node)

    def _collect_range(self, node, low, high, result):
        if node is None:
            return
        if low < node.key:
            self._collect_range(node.left, low, high, result)
        if low <= node.key <= high:
            result.append((node.key, node.value))
        if node.key < high:
            self._collect_range(node.right, low, high, result)
