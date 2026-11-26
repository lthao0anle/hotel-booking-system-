#!/usr/bin/env python3
"""
HỆ THỐNG QUẢN LÝ ĐẶT PHÒNG KHÁCH SẠN — BẢN GỘP 1 FILE DUY NHẤT (ALL-IN-ONE)
Học phần: Cấu trúc Dữ liệu và Giải thuật (MI3060)

Chỉ cần gửi 1 file này cho người khác, máy có cài Python 3.10+ là chạy được ngay:
  - Chạy menu dòng lệnh (CLI) : python hotel_booking_all_in_one.py
  - Chạy giao diện đồ họa     : python hotel_booking_all_in_one.py --gui
  - Chạy minh họa tự động     : python hotel_booking_all_in_one.py --demo
  - Chạy đo hiệu năng         : python hotel_booking_all_in_one.py --benchmark
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum, IntEnum
import json
from pathlib import Path
import random
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk


# ============================================================================
# MODULE: hotel/models/enums.py
# ============================================================================
"""Các kiểu liệt kê (enum) dùng chung cho các thực thể."""



class RoomType(Enum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    SUITE = "SUITE"

    @property
    def label(self):
        return {"SINGLE": "Đơn", "DOUBLE": "Đôi", "SUITE": "Suite"}[self.value]

    @property
    def order(self):
        """Thứ tự dùng khi sắp xếp/nhóm theo loại phòng."""
        return {"SINGLE": 0, "DOUBLE": 1, "SUITE": 2}[self.value]


class RoomStatus(Enum):
    """Trạng thái hiển thị của phòng TẠI MỘT NGÀY cụ thể."""
    EMPTY = "EMPTY"
    BOOKED = "BOOKED"
    MAINTENANCE = "MAINTENANCE"

    @property
    def label(self):
        return {"EMPTY": "TRỐNG", "BOOKED": "ĐÃ ĐẶT", "MAINTENANCE": "BẢO TRÌ"}[self.value]


class BookingStatus(Enum):
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"

    @property
    def label(self):
        return {
            "CONFIRMED": "Đã xác nhận",
            "CHECKED_IN": "Đang ở",
            "CHECKED_OUT": "Đã trả phòng",
            "CANCELLED": "Đã hủy",
        }[self.value]


class VipLevel(IntEnum):
    NORMAL = 0
    SILVER = 1
    GOLD = 2
    PLATINUM = 3

    @property
    def label(self):
        return {0: "Thường", 1: "Silver", 2: "Gold", 3: "Platinum"}[int(self)]


class ServiceType(Enum):
    CLEANING = "CLEANING"
    FOOD = "FOOD"
    MEDICAL = "MEDICAL"
    OTHER = "OTHER"

    @property
    def label(self):
        return {"CLEANING": "Dọn phòng", "FOOD": "Đồ ăn", "MEDICAL": "Y tế", "OTHER": "Khác"}[self.value]


class UrgencyLevel(IntEnum):
    LOW = 1
    NORMAL = 2
    EMERGENCY = 3

    @property
    def label(self):
        return {1: "Thấp", 2: "Bình thường", 3: "Khẩn cấp"}[int(self)]


class ServiceStatus(Enum):
    WAITING = "WAITING"
    DONE = "DONE"

    @property
    def label(self):
        return {"WAITING": "Đang chờ", "DONE": "Đã xử lý"}[self.value]


class PaymentMethod(Enum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    CARD = "CARD"
    E_WALLET = "E_WALLET"

    @property
    def label(self):
        return {
            "CASH": "Tiền mặt",
            "BANK_TRANSFER": "Chuyển khoản",
            "CARD": "Thẻ ngân hàng",
            "E_WALLET": "Ví điện tử",
        }[self.value]


class PaymentStatus(Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"

    @property
    def label(self):
        return {
            "UNPAID": "Chưa thanh toán",
            "PAID": "Đã thanh toán",
            "REFUNDED": "Đã hoàn tiền",
        }[self.value]


# ============================================================================
# MODULE: hotel/config.py
# ============================================================================
"""Cấu hình chung của hệ thống."""



PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_FILE = PROJECT_ROOT / "data" / "hotel_data.json"

# Sơ đồ khách sạn mặc định: 8 tầng × 10 phòng.
DEFAULT_FLOORS = 8
DEFAULT_ROOMS_PER_FLOOR = 10

# Giá cơ bản / đêm (VND) theo loại phòng; mỗi tầng cao hơn cộng thêm phụ phí.
BASE_PRICE_BY_TYPE = {
    RoomType.SINGLE: 500_000,
    RoomType.DOUBLE: 800_000,
    RoomType.SUITE: 1_500_000,
}
FLOOR_SURCHARGE = 50_000

ROOM_DESCRIPTION_BY_TYPE = {
    RoomType.SINGLE: "1 giường đơn, phòng tắm riêng, Wi-Fi",
    RoomType.DOUBLE: "1 giường đôi hoặc 2 giường đơn, TV, minibar",
    RoomType.SUITE: "Phòng khách riêng, bồn tắm, view thành phố",
}

# Đơn giá dịch vụ nội bộ phát sinh (VND / lượt) dùng khi tính tổng chi phí thanh toán.
SERVICE_PRICE_BY_TYPE = {
    ServiceType.CLEANING: 50_000,
    ServiceType.FOOD: 150_000,
    ServiceType.MEDICAL: 200_000,
    ServiceType.OTHER: 100_000,
}

# Tỷ lệ chiết khấu / giảm giá theo hạng VIP khi thanh toán hóa đơn.
VIP_DISCOUNT_RATES = {
    VipLevel.NORMAL: 0.0,
    VipLevel.SILVER: 0.03,
    VipLevel.GOLD: 0.05,
    VipLevel.PLATINUM: 0.10,
}

# Mốc tổng số tiền đã thanh toán tích lũy (VND) để tự động xét và nâng hạng VIP.
VIP_SPENDING_THRESHOLDS = {
    VipLevel.NORMAL: 0,
    VipLevel.SILVER: 3_000_000,
    VipLevel.GOLD: 8_000_000,
    VipLevel.PLATINUM: 15_000_000,
}


def evaluate_vip_level_by_spending(total_paid):
    """Xác định hạng VIP tương ứng với tổng số tiền đã thanh toán tích lũy (VND)."""
    paid = max(0, int(total_paid or 0))
    if paid >= VIP_SPENDING_THRESHOLDS[VipLevel.PLATINUM]:
        return VipLevel.PLATINUM
    if paid >= VIP_SPENDING_THRESHOLDS[VipLevel.GOLD]:
        return VipLevel.GOLD
    if paid >= VIP_SPENDING_THRESHOLDS[VipLevel.SILVER]:
        return VipLevel.SILVER
    return VipLevel.NORMAL


def get_vip_tier_progress(current_vip, total_paid):
    """Tính tiến độ tích lũy chi tiêu và số tiền còn thiếu để lên hạng VIP tiếp theo."""
    vip = VipLevel(int(current_vip))
    paid = max(0, int(total_paid or 0))
    earned_vip = evaluate_vip_level_by_spending(paid)
    effective_vip = VipLevel(max(int(vip), int(earned_vip)))

    next_vip = None
    next_threshold = None
    amount_to_next_vip = 0
    progress_percent = 100.0

    if effective_vip < VipLevel.PLATINUM:
        next_vip = VipLevel(int(effective_vip) + 1)
        next_threshold = VIP_SPENDING_THRESHOLDS[next_vip]
        current_floor = VIP_SPENDING_THRESHOLDS[effective_vip]
        amount_to_next_vip = max(0, next_threshold - paid)
        span = max(1, next_threshold - current_floor)
        if paid <= current_floor:
            progress_percent = round(min(100.0, (paid / max(1, next_threshold)) * 100.0), 1)
        else:
            progress_percent = round(min(100.0, ((paid - current_floor) / span) * 100.0), 1)

    return {
        "current_vip": vip,
        "earned_vip": earned_vip,
        "effective_vip": effective_vip,
        "total_paid": paid,
        "discount_rate": VIP_DISCOUNT_RATES.get(vip, 0.0),
        "next_vip": next_vip,
        "next_threshold": next_threshold,
        "amount_to_next_vip": amount_to_next_vip,
        "progress_percent": progress_percent,
    }


# Giới hạn nghiệp vụ.
MAX_STAY_NIGHTS = 30


# ============================================================================
# MODULE: hotel/models/date_utils.py
# ============================================================================
"""Tiện ích ngày tháng: định dạng hiển thị dd/mm/yyyy, lưu trữ ISO yyyy-mm-dd."""


DISPLAY_FORMAT = "%d/%m/%Y"
_ACCEPTED_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


def parse_date(text):
    """Chuyển chuỗi (dd/mm/yyyy hoặc yyyy-mm-dd) thành `date`; ném ValueError nếu sai."""
    cleaned = (text or "").strip()
    for fmt in _ACCEPTED_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Ngày không hợp lệ: '{text}'. Định dạng đúng: dd/mm/yyyy")


def format_date(value):
    return value.strftime(DISPLAY_FORMAT)


def to_iso(value):
    return value.isoformat()


def from_iso(text):
    return date.fromisoformat(text)


# ============================================================================
# MODULE: hotel/data_structures/matrix_2d.py
# ============================================================================
"""Mảng hai chiều kích thước cố định (rows × cols).

Lưu trên một mảng một chiều liên tục: phần tử (r, c) nằm ở chỉ số r * cols + c,
giống cách bố trí "row-major" của mảng 2 chiều trong C.

Dùng để lưu danh sách phòng theo tầng: rooms[tầng][số phòng].

Độ phức tạp: get / set O(1), duyệt toàn bộ O(rows × cols).
"""


class Matrix2D:
    def __init__(self, rows, cols, fill=None):
        if rows <= 0 or cols <= 0:
            raise ValueError("Kích thước mảng 2 chiều phải dương")
        self._rows = rows
        self._cols = cols
        self._cells = [fill] * (rows * cols)

    @property
    def rows(self):
        return self._rows

    @property
    def cols(self):
        return self._cols

    def get(self, row, col):
        return self._cells[self._offset(row, col)]

    def set(self, row, col, value):
        self._cells[self._offset(row, col)] = value

    def in_bounds(self, row, col):
        return 0 <= row < self._rows and 0 <= col < self._cols

    def row(self, row):
        """Trả về các phần tử của một hàng (một tầng) — O(cols)."""
        start = self._offset(row, 0)
        return self._cells[start:start + self._cols]

    def __iter__(self):
        """Duyệt theo thứ tự hàng (tầng) rồi tới cột (phòng)."""
        return iter(list(self._cells))

    def __len__(self):
        return self._rows * self._cols

    def _offset(self, row, col):
        if not self.in_bounds(row, col):
            raise IndexError(f"Vị trí ({row}, {col}) nằm ngoài mảng {self._rows}x{self._cols}")
        return row * self._cols + col


# ============================================================================
# MODULE: hotel/data_structures/avl_tree.py
# ============================================================================
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


# ============================================================================
# MODULE: hotel/data_structures/interval_schedule.py
# ============================================================================
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


# ============================================================================
# MODULE: hotel/data_structures/linked_list.py
# ============================================================================
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


# ============================================================================
# MODULE: hotel/data_structures/linked_queue.py
# ============================================================================
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


# ============================================================================
# MODULE: hotel/data_structures/hash_table.py
# ============================================================================
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


# ============================================================================
# MODULE: hotel/data_structures/max_heap.py
# ============================================================================
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


# ============================================================================
# MODULE: hotel/data_structures/stack.py
# ============================================================================
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


# ============================================================================
# MODULE: hotel/algorithms/merge_sort.py
# ============================================================================
"""Merge Sort — sắp xếp trộn, ỔN ĐỊNH (giữ thứ tự các phần tử bằng nhau).

Chia đôi mảng, sắp xếp đệ quy hai nửa rồi trộn hai nửa đã sắp xếp.

Độ phức tạp: thời gian O(n log n) mọi trường hợp; bộ nhớ phụ O(n).
"""


def _identity(item):
    return item


def merge_sort(items, key=_identity, reverse=False):
    """Trả về danh sách MỚI đã sắp xếp; không làm thay đổi `items`."""
    data = list(items)
    if len(data) <= 1:
        return data
    buffer = [None] * len(data)
    _merge_sort_rec(data, buffer, 0, len(data), key, reverse)
    return data


def _merge_sort_rec(data, buffer, low, high, key, reverse):
    if high - low <= 1:
        return
    mid = (low + high) // 2
    _merge_sort_rec(data, buffer, low, mid, key, reverse)
    _merge_sort_rec(data, buffer, mid, high, key, reverse)
    _merge(data, buffer, low, mid, high, key, reverse)


def _comes_first(right_item, left_item, key, reverse):
    """True nếu phần tử bên phải phải đứng TRƯỚC phần tử bên trái.

    Chỉ trả về True khi nhỏ hơn/lớn hơn HẲN để đảm bảo tính ổn định.
    """
    if reverse:
        return key(right_item) > key(left_item)
    return key(right_item) < key(left_item)


def _merge(data, buffer, low, mid, high, key, reverse):
    i, j, k = low, mid, low
    while i < mid and j < high:
        if _comes_first(data[j], data[i], key, reverse):
            buffer[k] = data[j]
            j += 1
        else:
            buffer[k] = data[i]
            i += 1
        k += 1
    while i < mid:
        buffer[k] = data[i]
        i += 1
        k += 1
    while j < high:
        buffer[k] = data[j]
        j += 1
        k += 1
    data[low:high] = buffer[low:high]


# ============================================================================
# MODULE: hotel/algorithms/quick_sort.py
# ============================================================================
"""Quick Sort — sắp xếp nhanh, phân hoạch 3 phần (Dutch National Flag).

- Chọn chốt (pivot) bằng trung vị của 3 phần tử (đầu, giữa, cuối) để tránh
  trường hợp xấu khi dữ liệu đã gần sắp xếp.
- Phân hoạch 3 phần: < pivot | = pivot | > pivot. Giá phòng lặp lại rất nhiều
  (nhiều phòng cùng loại cùng giá), phân hoạch 2 phần thông thường sẽ suy
  biến về O(n²) với dữ liệu nhiều khóa trùng; phân hoạch 3 phần thì không.
- Đệ quy vào phần nhỏ hơn, lặp với phần lớn hơn -> độ sâu ngăn xếp O(log n).

Độ phức tạp: O(n log n) trung bình, O(n²) xấu nhất (rất hiếm); KHÔNG ổn định.
"""


def _identity(item):
    return item


def quick_sort(items, key=_identity, reverse=False):
    """Trả về danh sách MỚI đã sắp xếp; không làm thay đổi `items`."""
    data = list(items)
    keys = [key(item) for item in data]
    _quick_sort_rec(data, keys, 0, len(data) - 1, reverse)
    return data


def _before(a, b, reverse):
    return a > b if reverse else a < b


def _swap(data, keys, i, j):
    data[i], data[j] = data[j], data[i]
    keys[i], keys[j] = keys[j], keys[i]


def _median_of_three(keys, low, high, reverse):
    mid = (low + high) // 2
    a, b, c = keys[low], keys[mid], keys[high]
    if _before(a, b, reverse):
        if _before(b, c, reverse):
            return mid
        return high if _before(a, c, reverse) else low
    if _before(a, c, reverse):
        return low
    return high if _before(b, c, reverse) else mid


def _partition3(data, keys, low, high, reverse):
    """Trả về (lt, gt) sao cho keys[low:lt] < pivot, keys[lt:gt+1] == pivot, keys[gt+1:] > pivot."""
    pivot_index = _median_of_three(keys, low, high, reverse)
    pivot = keys[pivot_index]
    lt, i, gt = low, low, high
    while i <= gt:
        if _before(keys[i], pivot, reverse):
            _swap(data, keys, lt, i)
            lt += 1
            i += 1
        elif _before(pivot, keys[i], reverse):
            _swap(data, keys, i, gt)
            gt -= 1
        else:
            i += 1
    return lt, gt


def _quick_sort_rec(data, keys, low, high, reverse):
    while low < high:
        lt, gt = _partition3(data, keys, low, high, reverse)
        if lt - low < high - gt:
            _quick_sort_rec(data, keys, low, lt - 1, reverse)
            low = gt + 1
        else:
            _quick_sort_rec(data, keys, gt + 1, high, reverse)
            high = lt - 1


# ============================================================================
# MODULE: hotel/algorithms/binary_search.py
# ============================================================================
"""Tìm kiếm nhị phân trên mảng ĐÃ SẮP XẾP TĂNG DẦN theo `key`.

Độ phức tạp: O(log n) cho mỗi hàm.
"""


def _identity(item):
    return item


def lower_bound(sorted_items, target, key=_identity):
    """Chỉ số nhỏ nhất i sao cho key(sorted_items[i]) >= target (hoặc len nếu không có)."""
    low, high = 0, len(sorted_items)
    while low < high:
        mid = (low + high) // 2
        if key(sorted_items[mid]) < target:
            low = mid + 1
        else:
            high = mid
    return low


def upper_bound(sorted_items, target, key=_identity):
    """Chỉ số nhỏ nhất i sao cho key(sorted_items[i]) > target (hoặc len nếu không có)."""
    low, high = 0, len(sorted_items)
    while low < high:
        mid = (low + high) // 2
        if key(sorted_items[mid]) <= target:
            low = mid + 1
        else:
            high = mid
    return low


def binary_search(sorted_items, target, key=_identity):
    """Chỉ số của một phần tử có key == target, hoặc -1 nếu không có."""
    index = lower_bound(sorted_items, target, key)
    if index < len(sorted_items) and key(sorted_items[index]) == target:
        return index
    return -1


def range_search(sorted_items, low_target, high_target, key=_identity):
    """Các phần tử có low_target <= key <= high_target — O(log n + r)."""
    start = lower_bound(sorted_items, low_target, key)
    end = upper_bound(sorted_items, high_target, key)
    return sorted_items[start:end]


def find_closest(sorted_items, target, key=_identity):
    """Tìm phần tử có khóa gần `target` nhất trên mảng đã sắp tăng dần — O(log n).

    Nếu có hai phần tử cách đều `target`, ưu tiên phần tử có khóa nhỏ hơn
    (tiết kiệm ngân sách cho khách hàng). Trả về None nếu mảng rỗng.
    """
    n = len(sorted_items)
    if n == 0:
        return None
    idx = lower_bound(sorted_items, target, key)
    if idx == 0:
        return sorted_items[0]
    if idx == n:
        return sorted_items[n - 1]
    before = sorted_items[idx - 1]
    after = sorted_items[idx]
    if abs(target - key(before)) <= abs(key(after) - target):
        return before
    return after


# ============================================================================
# MODULE: hotel/algorithms/naive.py
# ============================================================================
"""Các giải thuật "ngây thơ" dùng làm mốc so sánh trong benchmark (Chương 4).

KHÔNG được dùng trong nghiệp vụ chính; chỉ phục vụ đo đạc hiệu năng.
"""


def _identity(item):
    return item


def selection_sort(items, key=_identity):
    """Sắp xếp chọn — O(n²)."""
    data = list(items)
    size = len(data)
    for i in range(size - 1):
        smallest = i
        for j in range(i + 1, size):
            if key(data[j]) < key(data[smallest]):
                smallest = j
        data[i], data[smallest] = data[smallest], data[i]
    return data


def linear_search(items, predicate):
    """Tìm tuần tự phần tử đầu tiên thỏa predicate — O(n)."""
    for item in items:
        if predicate(item):
            return item
    return None


def linear_find_conflict(intervals, start, end, start_of, end_of):
    """Kiểm tra xung đột bằng cách duyệt toàn bộ danh sách — O(n)."""
    for item in intervals:
        if start < end_of(item) and start_of(item) < end:
            return item
    return None


def linear_extract_max(items, priority_key):
    """Lấy và xóa phần tử ưu tiên cao nhất trong danh sách thường — O(k)."""
    best = 0
    for index in range(1, len(items)):
        if priority_key(items[index]) > priority_key(items[best]):
            best = index
    return items.pop(best)


# ============================================================================
# MODULE: hotel/models/room.py
# ============================================================================
"""Thực thể Phòng (Room)."""




def make_room_id(floor, room_number):
    """Mã phòng: 'P' + tầng + số phòng 2 chữ số, ví dụ tầng 2 phòng 5 -> 'P205'."""
    return f"P{floor}{room_number:02d}"


def parse_room_id(room_id):
    """Tách mã phòng thành (tầng, số phòng). Chấp nhận 'P205', 'p205' hoặc '205'."""
    text = (room_id or "").strip().upper()
    if text.startswith("P"):
        text = text[1:]
    if len(text) < 3 or not text.isdigit():
        raise ValueError(f"Mã phòng không hợp lệ: '{room_id}'")
    return int(text[:-2]), int(text[-2:])


@dataclass
class Room:
    floor: int
    room_number: int
    room_type: RoomType
    price_per_night: int
    description: str = ""
    under_maintenance: bool = False

    @property
    def room_id(self):
        return make_room_id(self.floor, self.room_number)

    def to_dict(self):
        return {
            "floor": self.floor,
            "room_number": self.room_number,
            "room_type": self.room_type.value,
            "price_per_night": self.price_per_night,
            "description": self.description,
            "under_maintenance": self.under_maintenance,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            floor=data["floor"],
            room_number=data["room_number"],
            room_type=RoomType(data["room_type"]),
            price_per_night=data["price_per_night"],
            description=data.get("description", ""),
            under_maintenance=data.get("under_maintenance", False),
        )


# ============================================================================
# MODULE: hotel/models/booking.py
# ============================================================================
"""Thực thể Đơn đặt phòng (Booking). Khoảng lưu trú là nửa mở [check_in, check_out)."""




@dataclass
class Booking:
    booking_id: str
    customer_id: str
    room_id: str
    check_in: date
    check_out: date
    price_per_night: int
    created_at: date
    status: BookingStatus = BookingStatus.CONFIRMED
    vip_level_at_booking: int | None = None

    @property
    def num_nights(self):
        return (self.check_out - self.check_in).days

    @property
    def total_price(self):
        return self.num_nights * self.price_per_night

    @property
    def is_active(self):
        """Booking còn đang giữ lịch phòng (CONFIRMED hoặc CHECKED_IN)."""
        return self.status in (BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN)

    def overlaps(self, check_in, check_out):
        """Hai khoảng [A, B) và [C, D) giao nhau  <=>  A < D và C < B."""
        return self.check_in < check_out and check_in < self.check_out

    def to_dict(self):
        data = {
            "booking_id": self.booking_id,
            "customer_id": self.customer_id,
            "room_id": self.room_id,
            "check_in": to_iso(self.check_in),
            "check_out": to_iso(self.check_out),
            "price_per_night": self.price_per_night,
            "created_at": to_iso(self.created_at),
            "status": self.status.value,
        }
        if self.vip_level_at_booking is not None:
            data["vip_level_at_booking"] = int(self.vip_level_at_booking)
        return data

    @classmethod
    def from_dict(cls, data):
        vip_at_bk = data.get("vip_level_at_booking")
        return cls(
            booking_id=data["booking_id"],
            customer_id=data["customer_id"],
            room_id=data["room_id"],
            check_in=from_iso(data["check_in"]),
            check_out=from_iso(data["check_out"]),
            price_per_night=data["price_per_night"],
            created_at=from_iso(data["created_at"]),
            status=BookingStatus(data["status"]),
            vip_level_at_booking=int(vip_at_bk) if vip_at_bk is not None else None,
        )


# ============================================================================
# MODULE: hotel/models/customer.py
# ============================================================================
"""Thực thể Khách hàng (Customer).

Lịch sử lưu trú được lưu bằng danh sách liên kết đơn: lượt đặt mới nhất ở đầu.
"""




@dataclass
class Customer:
    customer_id: str
    full_name: str
    cccd: str
    phone: str
    vip_level: VipLevel = VipLevel.NORMAL
    manual_vip_level: VipLevel | None = None
    history: SinglyLinkedList = field(default_factory=SinglyLinkedList, repr=False, compare=False)

    def __post_init__(self):
        self.vip_level = VipLevel(int(self.vip_level))
        if self.manual_vip_level is None:
            self.manual_vip_level = self.vip_level
        else:
            self.manual_vip_level = VipLevel(int(self.manual_vip_level))

    @property
    def is_vip(self):
        return self.vip_level > VipLevel.NORMAL

    def add_booking_to_history(self, booking):
        """Chèn lượt đặt mới vào ĐẦU lịch sử — O(1)."""
        self.history.push_front(booking)

    def to_dict(self):
        return {
            "customer_id": self.customer_id,
            "full_name": self.full_name,
            "cccd": self.cccd,
            "phone": self.phone,
            "vip_level": int(self.vip_level),
            "manual_vip_level": int(self.manual_vip_level),
            # Lưu theo thứ tự cũ -> mới để khi nạp lại chỉ cần push_front lần lượt.
            "history": [booking.booking_id for booking in reversed(self.history.to_list())],
        }

    @classmethod
    def from_dict(cls, data):
        vip = VipLevel(data.get("vip_level", 0))
        manual_vip = VipLevel(data.get("manual_vip_level", int(vip)))
        return cls(
            customer_id=data["customer_id"],
            full_name=data["full_name"],
            cccd=data["cccd"],
            phone=data["phone"],
            vip_level=vip,
            manual_vip_level=manual_vip,
        )


# ============================================================================
# MODULE: hotel/models/waiting_entry.py
# ============================================================================
"""Thực thể Mục chờ (WaitingEntry) — khách chờ phòng khi hết phòng."""




@dataclass
class WaitingEntry:
    entry_id: str
    customer_id: str
    room_type: RoomType
    check_in: date
    check_out: date
    priority: int          # = cấp VIP của khách tại thời điểm vào hàng chờ (0..3)
    sequence: int          # số thứ tự vào hàng, dùng để phá hòa (ai đến trước phục vụ trước)
    requested_at: date

    def priority_key(self):
        """Khóa cho Max-Heap: VIP cao hơn trước; cùng cấp thì sequence nhỏ (đến sớm) trước."""
        return (self.priority, -self.sequence)

    def to_dict(self):
        return {
            "entry_id": self.entry_id,
            "customer_id": self.customer_id,
            "room_type": self.room_type.value,
            "check_in": to_iso(self.check_in),
            "check_out": to_iso(self.check_out),
            "priority": self.priority,
            "sequence": self.sequence,
            "requested_at": to_iso(self.requested_at),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            entry_id=data["entry_id"],
            customer_id=data["customer_id"],
            room_type=RoomType(data["room_type"]),
            check_in=from_iso(data["check_in"]),
            check_out=from_iso(data["check_out"]),
            priority=data["priority"],
            sequence=data["sequence"],
            requested_at=from_iso(data["requested_at"]),
        )


# ============================================================================
# MODULE: hotel/models/service_request.py
# ============================================================================
"""Thực thể Yêu cầu dịch vụ nội bộ (ServiceRequest)."""




@dataclass
class ServiceRequest:
    request_id: str
    room_id: str
    customer_id: str        # có thể rỗng nếu do nhân viên tạo
    service_type: ServiceType
    urgency: UrgencyLevel
    note: str
    sequence: int           # thứ tự gửi, dùng phá hòa khi cùng độ khẩn
    requested_at: date
    status: ServiceStatus = ServiceStatus.WAITING

    def priority_key(self):
        """Khóa cho Max-Heap: khẩn hơn trước; cùng độ khẩn thì gửi trước xử lý trước."""
        return (int(self.urgency), -self.sequence)

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "room_id": self.room_id,
            "customer_id": self.customer_id,
            "service_type": self.service_type.value,
            "urgency": int(self.urgency),
            "note": self.note,
            "sequence": self.sequence,
            "requested_at": to_iso(self.requested_at),
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            request_id=data["request_id"],
            room_id=data["room_id"],
            customer_id=data.get("customer_id", ""),
            service_type=ServiceType(data["service_type"]),
            urgency=UrgencyLevel(data["urgency"]),
            note=data.get("note", ""),
            sequence=data["sequence"],
            requested_at=from_iso(data["requested_at"]),
            status=ServiceStatus(data.get("status", "WAITING")),
        )


# ============================================================================
# MODULE: hotel/models/cancel_action.py
# ============================================================================
"""Thực thể Thao tác hủy (CancelAction) — phần tử của ngăn xếp hoàn tác."""




@dataclass
class CancelAction:
    booking_id: str
    room_id: str
    booking_snapshot: dict   # bản sao Booking.to_dict() NGAY TRƯỚC khi hủy
    cancelled_by: str        # "STAFF" hoặc "CUSTOMER"
    cancelled_at: date

    def to_dict(self):
        return {
            "booking_id": self.booking_id,
            "room_id": self.room_id,
            "booking_snapshot": dict(self.booking_snapshot),
            "cancelled_by": self.cancelled_by,
            "cancelled_at": to_iso(self.cancelled_at),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            booking_id=data["booking_id"],
            room_id=data["room_id"],
            booking_snapshot=dict(data["booking_snapshot"]),
            cancelled_by=data.get("cancelled_by", "STAFF"),
            cancelled_at=from_iso(data["cancelled_at"]),
        )


# ============================================================================
# MODULE: hotel/models/payment.py
# ============================================================================
"""Thực thể Giao dịch Thanh toán (PaymentTransaction)."""




@dataclass
class PaymentTransaction:
    payment_id: str
    booking_id: str
    customer_id: str
    room_id: str
    room_cost: int
    service_cost: int
    extra_fee: int
    discount_amount: int
    total_amount: int
    payment_method: PaymentMethod
    paid_at: date
    status: PaymentStatus = PaymentStatus.PAID
    note: str = ""

    @property
    def gross_amount(self):
        """Tổng chi phí trước khi trừ chiết khấu VIP."""
        return self.room_cost + self.service_cost + self.extra_fee

    def to_dict(self):
        return {
            "payment_id": self.payment_id,
            "booking_id": self.booking_id,
            "customer_id": self.customer_id,
            "room_id": self.room_id,
            "room_cost": self.room_cost,
            "service_cost": self.service_cost,
            "extra_fee": self.extra_fee,
            "discount_amount": self.discount_amount,
            "total_amount": self.total_amount,
            "payment_method": self.payment_method.value,
            "paid_at": to_iso(self.paid_at),
            "status": self.status.value,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            payment_id=data["payment_id"],
            booking_id=data["booking_id"],
            customer_id=data["customer_id"],
            room_id=data["room_id"],
            room_cost=int(data.get("room_cost", 0)),
            service_cost=int(data.get("service_cost", 0)),
            extra_fee=int(data.get("extra_fee", 0)),
            discount_amount=int(data.get("discount_amount", 0)),
            total_amount=int(data.get("total_amount", 0)),
            payment_method=PaymentMethod(data.get("payment_method", "CASH")),
            paid_at=from_iso(data["paid_at"]),
            status=PaymentStatus(data.get("status", "PAID")),
            note=data.get("note", ""),
        )


# ============================================================================
# MODULE: hotel/services/errors.py
# ============================================================================
"""Ngoại lệ nghiệp vụ. Lớp giao diện bắt `HotelError` để hiển thị thông báo thân thiện."""


class HotelError(Exception):
    """Lỗi nghiệp vụ chung (dữ liệu nhập sai, thao tác không hợp lệ...)."""


class NotFoundError(HotelError):
    """Không tìm thấy đối tượng (phòng, khách, booking...)."""


class RoomUnavailableError(HotelError):
    """Phòng không thể đặt trong khoảng ngày yêu cầu."""

    def __init__(self, message, conflicting_booking=None):
        super().__init__(message)
        self.conflicting_booking = conflicting_booking


# ============================================================================
# MODULE: hotel/services/id_generator.py
# ============================================================================
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


# ============================================================================
# MODULE: hotel/services/room_service.py
# ============================================================================
"""Chức năng 1 & 3: Quản lý phòng theo tầng (Mảng 2D) và Lọc/Sắp xếp/Tìm kiếm phòng.

Độ phức tạp mục tiêu:
- Truy cập phòng theo (tầng, số phòng) hoặc mã phòng (vd 'P205') : O(1) qua Matrix2D
- Sắp xếp danh sách phòng theo giá (Merge Sort / Quick Sort)     : O(R log R)
- Tìm phòng theo khoảng giá [min, max] trên mảng đã sắp          : O(log R + k) qua Binary Search
- Tìm phòng có giá gần nhất với ngân sách (budget)               : O(log R) qua Binary Search
- Lọc theo loại phòng + tìm theo ngưỡng giá                      : O(log R_t + k) nhờ nhóm theo loại
"""



def _price_key(room):
    return room.price_per_night


def _default_room_type(room_number, rooms_per_floor):
    """Phân bổ loại phòng mặc định trong mỗi tầng:
    40% đầu là SINGLE, 40% tiếp theo là DOUBLE, 20% cuối là SUITE.
    """
    single_limit = max(1, (rooms_per_floor * 4) // 10)
    double_limit = max(single_limit + 1, (rooms_per_floor * 8) // 10)
    if room_number <= single_limit:
        return RoomType.SINGLE
    if room_number <= double_limit:
        return RoomType.DOUBLE
    return RoomType.SUITE


class RoomService:
    def __init__(self, floors=DEFAULT_FLOORS, rooms_per_floor=DEFAULT_ROOMS_PER_FLOOR):
        self._matrix = Matrix2D(floors, rooms_per_floor)
        self._sorted_by_price = []
        self._sorted_by_type = {room_type: [] for room_type in RoomType}
        self._initialize_default_rooms()

    @property
    def floors(self):
        return self._matrix.rows

    @property
    def rooms_per_floor(self):
        return self._matrix.cols

    @property
    def matrix(self):
        return self._matrix

    # ------------------- Khởi tạo & nạp sơ đồ ma trận ------------------- #
    def _initialize_default_rooms(self):
        for floor in range(1, self.floors + 1):
            for number in range(1, self.rooms_per_floor + 1):
                rtype = _default_room_type(number, self.rooms_per_floor)
                price = BASE_PRICE_BY_TYPE[rtype] + (floor - 1) * FLOOR_SURCHARGE
                room = Room(
                    floor=floor,
                    room_number=number,
                    room_type=rtype,
                    price_per_night=price,
                    description=ROOM_DESCRIPTION_BY_TYPE[rtype],
                )
                self._matrix.set(floor - 1, number - 1, room)
        self._rebuild_sorted_index()

    def load_rooms(self, floors, rooms_per_floor, room_list):
        """Khôi phục ma trận phòng từ dữ liệu lưu trữ."""
        self._matrix = Matrix2D(floors, rooms_per_floor)
        self._initialize_default_rooms()
        for room in room_list:
            if not self._matrix.in_bounds(room.floor - 1, room.room_number - 1):
                raise HotelError(f"Vị trí phòng {room.room_id} nằm ngoài sơ đồ khách sạn")
            self._matrix.set(room.floor - 1, room.room_number - 1, room)
        self._rebuild_sorted_index()

    def _rebuild_sorted_index(self):
        """Cập nhật chỉ mục đã sắp theo giá bằng Merge Sort — O(R log R)."""
        all_rooms = list(self._matrix)
        self._sorted_by_price = merge_sort(all_rooms, key=_price_key)
        self._sorted_by_type = {
            rtype: [r for r in self._sorted_by_price if r.room_type == rtype]
            for rtype in RoomType
        }

    # -------------------- Truy cập O(1) trên Mảng 2D -------------------- #
    def get_room_by_coords(self, floor, room_number):
        """Truy cập trực tiếp phòng theo (tầng, số phòng) — O(1)."""
        row, col = floor - 1, room_number - 1
        if not self._matrix.in_bounds(row, col):
            raise NotFoundError(
                f"Không tồn tại phòng ở tầng {floor}, số {room_number} "
                f"(khách sạn có {self.floors} tầng × {self.rooms_per_floor} phòng)"
            )
        return self._matrix.get(row, col)

    def get_room(self, room_id):
        """Truy cập trực tiếp phòng theo mã phòng (vd 'P205') — O(1) nhờ ánh xạ tọa độ."""
        try:
            floor, room_number = parse_room_id(room_id)
        except ValueError as exc:
            raise NotFoundError(str(exc)) from exc
        return self.get_room_by_coords(floor, room_number)

    def floor_rooms(self, floor):
        """Danh sách phòng của một tầng (1..floors) — O(rooms_per_floor)."""
        if not 1 <= floor <= self.floors:
            raise NotFoundError(f"Tầng {floor} không hợp lệ (1..{self.floors})")
        return self._matrix.row(floor - 1)

    def all_rooms(self):
        """Danh sách toàn bộ phòng theo thứ tự tầng -> số phòng."""
        return list(self._matrix)

    # ------------------------- Cập nhật phòng --------------------------- #
    def set_maintenance(self, room_id, under_maintenance):
        """Đặt hoặc gỡ trạng thái bảo trì cho phòng — O(1)."""
        room = self.get_room(room_id)
        room.under_maintenance = bool(under_maintenance)
        return room

    def update_room_price(self, room_id, new_price):
        """Cập nhật giá phòng và tái lập chỉ mục sắp xếp — O(R log R)."""
        if new_price <= 0:
            raise HotelError("Giá phòng phải lớn hơn 0")
        room = self.get_room(room_id)
        room.price_per_night = int(new_price)
        self._rebuild_sorted_index()
        return room

    # ---------- Sắp xếp O(R log R) & Tìm kiếm nhị phân O(log R) --------- #
    def sort_rooms(self, rooms=None, by="price", reverse=False, algorithm="merge"):
        """Sắp xếp danh sách phòng bằng Merge Sort (ổn định) hoặc Quick Sort — O(R log R).

        Tham số `by`:
            - "price": sắp theo giá/đêm
            - "type_price": sắp theo loại phòng rồi theo giá
            - "room_id": sắp theo tầng và số phòng
        """
        target = self.all_rooms() if rooms is None else list(rooms)
        if by == "price":
            key_fn = _price_key
        elif by == "type_price":
            key_fn = lambda r: (r.room_type.order, r.price_per_night, r.floor, r.room_number)
        elif by == "room_id":
            key_fn = lambda r: (r.floor, r.room_number)
        else:
            raise HotelError(f"Tiêu chí sắp xếp không hợp lệ: {by}")

        sorter = quick_sort if algorithm == "quick" else merge_sort
        return sorter(target, key=key_fn, reverse=reverse)

    def filter_by_price_range(self, min_price=0, max_price=float("inf"), room_type=None):
        """Tìm phòng trong khoảng giá [min_price, max_price] bằng Binary Search — O(log R + k).

        Nếu truyền `room_type`, tìm trực tiếp trên mảng con đã phân nhóm theo loại phòng.
        """
        if min_price > max_price:
            raise HotelError("Giá tối thiểu không được lớn hơn giá tối đa")
        sorted_pool = (
            self._sorted_by_type[room_type]
            if room_type is not None
            else self._sorted_by_price
        )
        return range_search(sorted_pool, min_price, max_price, key=_price_key)

    def find_closest_to_budget(self, budget, room_type=None, candidates=None):
        """Tìm phòng có giá gần nhất với `budget` bằng Binary Search — O(log R).

        - Nếu `candidates` là None: tìm trực tiếp trên mảng đã sort sẵn trong O(log R).
        - Nếu truyền `candidates` (ví dụ tập phòng trống): sắp bằng Merge Sort rồi Binary Search.
        """
        if budget <= 0:
            raise HotelError("Ngân sách phải lớn hơn 0")
        if candidates is not None:
            pool = [
                r for r in candidates
                if room_type is None or r.room_type == room_type
            ]
            sorted_pool = merge_sort(pool, key=_price_key)
        else:
            sorted_pool = (
                self._sorted_by_type[room_type]
                if room_type is not None
                else self._sorted_by_price
            )
        return find_closest(sorted_pool, budget, key=_price_key)

    def find_exact_price(self, price, room_type=None):
        """Kiểm tra và trả về một phòng có giá đúng bằng `price` bằng Binary Search — O(log R)."""
        sorted_pool = (
            self._sorted_by_type[room_type]
            if room_type is not None
            else self._sorted_by_price
        )
        idx = binary_search(sorted_pool, price, key=_price_key)
        return None if idx == -1 else sorted_pool[idx]


# ============================================================================
# MODULE: hotel/services/customer_service.py
# ============================================================================
"""Chức năng 5: Quản lý khách hàng (Hash Table) và Lịch sử lưu trú (Linked List).

Độ phức tạp mục tiêu:
- Tra cứu khách hàng theo Mã KH / CCCD / SĐT : O(1) trung bình (HashTable chaining)
- Đăng ký khách hàng mới                     : O(1) trung bình
- Thêm lượt đặt vào đầu lịch sử lưu trú      : O(1) (SinglyLinkedList.push_front)
- Duyệt lịch sử lưu trú của một khách        : O(m) với m là số lượt đặt của khách đó
"""



def _clean_text(value, field_name):
    cleaned = (value or "").strip()
    if not cleaned:
        raise HotelError(f"{field_name} không được để trống")
    return cleaned


def _normalize_digits(raw_value, is_phone=False):
    """Chuẩn hóa chuỗi số (bỏ khoảng trắng, dấu gạch ngang, dấu chấm, ngoặc và đổi +84 -> 0)."""
    text = (raw_value or "").strip()
    for ch in (" ", "-", ".", "(", ")"):
        text = text.replace(ch, "")
    if is_phone and text.startswith("+84"):
        text = "0" + text[3:]
    return text


def _clean_digits(value, field_name, min_len=8, max_len=15, is_phone=False):
    cleaned = _normalize_digits(value, is_phone=is_phone)
    if not cleaned.isdigit() or not (min_len <= len(cleaned) <= max_len):
        raise HotelError(
            f"{field_name} phải gồm từ {min_len} đến {max_len} chữ số "
            f"(ví dụ: 0901234567 hoặc +84 901 234 567; nhận: '{value}')"
        )
    return cleaned


class CustomerService:
    def __init__(self):
        self._by_id = HashTable()
        self._by_cccd = HashTable()
        self._by_phone = HashTable()
        self._id_gen = SequenceGenerator("KH", 3)

    @property
    def id_generator(self):
        return self._id_gen

    # ---------------------- Đăng ký & Cập nhật -------------------------- #
    def register_customer(self, full_name, cccd, phone, vip_level=VipLevel.NORMAL):
        """Đăng ký khách hàng mới — O(1) trung bình."""
        name = _clean_text(full_name, "Họ tên")
        cccd_norm = _clean_digits(cccd, "Số CCCD", min_len=8, max_len=15, is_phone=False)
        phone_norm = _clean_digits(phone, "Số điện thoại", min_len=8, max_len=15, is_phone=True)
        vip = VipLevel(int(vip_level))

        if self._by_cccd.contains(cccd_norm):
            existing = self._by_cccd.get(cccd_norm)
            raise HotelError(f"CCCD {cccd_norm} đã được đăng ký cho khách {existing.customer_id} ({existing.full_name})")
        if self._by_phone.contains(phone_norm):
            existing = self._by_phone.get(phone_norm)
            raise HotelError(f"SĐT {phone_norm} đã được đăng ký cho khách {existing.customer_id} ({existing.full_name})")

        customer = Customer(
            customer_id=self._id_gen.next_id(),
            full_name=name,
            cccd=cccd_norm,
            phone=phone_norm,
            vip_level=vip,
        )
        self._index_customer(customer)
        return customer

    def _index_customer(self, customer):
        self._by_id.put(customer.customer_id, customer)
        self._by_cccd.put(customer.cccd, customer)
        self._by_phone.put(customer.phone, customer)

    def set_vip_level(self, customer_id, vip_level, is_manual=True):
        """Cập nhật cấp VIP của khách hàng — O(1) trung bình."""
        customer = self.get_customer(customer_id)
        new_vip = VipLevel(int(vip_level))
        customer.vip_level = new_vip
        if is_manual:
            customer.manual_vip_level = new_vip
            for booking in customer.history:
                if getattr(booking, "status", None) is not None and str(booking.status) != "BookingStatus.CANCELLED":
                    booking.vip_level_at_booking = int(new_vip)
        return customer

    def evaluate_and_update_vip(self, customer_identifier, total_paid, allow_downgrade=False):
        """Đánh giá tổng chi tiêu đã thanh toán và tự động cập nhật hạng VIP cho khách hàng."""
        customer = self.lookup(customer_identifier)
        earned_vip = evaluate_vip_level_by_spending(total_paid)
        old_vip = customer.vip_level
        if allow_downgrade:
            target_vip = earned_vip
        else:
            floor_vip = getattr(customer, "manual_vip_level", old_vip)
            target_vip = VipLevel(max(int(floor_vip), int(earned_vip)))

        changed = target_vip != old_vip
        upgraded = target_vip > old_vip
        if changed:
            customer.vip_level = target_vip

        return {
            "customer": customer,
            "old_vip": old_vip,
            "new_vip": customer.vip_level,
            "earned_vip": earned_vip,
            "total_paid": max(0, int(total_paid or 0)),
            "upgraded": upgraded,
            "changed": changed,
        }

    def get_vip_progress(self, customer_identifier, total_paid=0):
        """Tính tiến độ tích lũy và số tiền còn thiếu để lên hạng VIP tiếp theo."""
        customer = self.lookup(customer_identifier)
        progress = get_vip_tier_progress(customer.vip_level, total_paid)
        return {
            "customer": customer,
            "customer_id": customer.customer_id,
            **progress,
        }

    def update_phone(self, customer_id, new_phone):
        """Đổi số điện thoại và cập nhật bảng băm — O(1) trung bình."""
        customer = self.get_customer(customer_id)
        phone_norm = _clean_digits(new_phone, "Số điện thoại", min_len=8, max_len=15, is_phone=True)
        existing = self._by_phone.get(phone_norm)
        if existing is not None and existing.customer_id != customer.customer_id:
            raise HotelError(f"SĐT {phone_norm} đã thuộc về khách {existing.customer_id}")
        self._by_phone.remove(customer.phone)
        customer.phone = phone_norm
        self._by_phone.put(phone_norm, customer)
        return customer

    # ---------------------- Tra cứu O(1) trung bình --------------------- #
    def get_customer(self, customer_id):
        """Tra cứu theo mã khách hàng (vd 'KH001'), hoặc dự phòng theo CCCD/SĐT — O(1) trung bình."""
        key = (customer_id or "").strip()
        customer = self._by_id.get(key.upper())
        if customer is None:
            norm_phone = _normalize_digits(key, is_phone=True)
            norm_digits = _normalize_digits(key, is_phone=False)
            customer = (
                self._by_cccd.get(key)
                or self._by_phone.get(key)
                or self._by_cccd.get(norm_digits)
                or self._by_phone.get(norm_phone)
            )
        if customer is None:
            raise NotFoundError(f"Không tìm thấy khách hàng có mã/CCCD/SĐT '{customer_id}'")
        return customer

    def find_by_cccd(self, cccd):
        """Tra cứu theo CCCD — O(1) trung bình. Trả về Customer hoặc None."""
        raw = (cccd or "").strip()
        return self._by_cccd.get(raw) or self._by_cccd.get(_normalize_digits(raw, is_phone=False))

    def find_by_phone(self, phone):
        """Tra cứu theo SĐT — O(1) trung bình. Trả về Customer hoặc None."""
        raw = (phone or "").strip()
        return self._by_phone.get(raw) or self._by_phone.get(_normalize_digits(raw, is_phone=True))

    def lookup(self, identifier):
        """Tra cứu linh hoạt theo Mã KH, CCCD hoặc SĐT — O(1) trung bình."""
        key = (identifier or "").strip()
        if not key:
            raise NotFoundError("Thông tin tra cứu khách hàng đang để trống")
        norm_phone = _normalize_digits(key, is_phone=True)
        norm_digits = _normalize_digits(key, is_phone=False)
        customer = (
            self._by_id.get(key.upper())
            or self._by_cccd.get(key)
            or self._by_phone.get(key)
            or self._by_cccd.get(norm_digits)
            or self._by_phone.get(norm_phone)
        )
        if customer is None:
            raise NotFoundError(f"Không tìm thấy khách hàng với mã/CCCD/SĐT '{identifier}'")
        return customer

    # --------------- Lịch sử lưu trú (SinglyLinkedList) ----------------- #
    def record_booking(self, customer_id, booking):
        """Chèn đơn đặt phòng vào ĐẦU danh sách liên kết lịch sử — O(1)."""
        customer = self.get_customer(customer_id)
        # Tránh nhân bản nút trong lịch sử khi hoàn tác (undo) một đơn đã từng lưu
        if customer.history.find(lambda b: b.booking_id == booking.booking_id) is None:
            customer.add_booking_to_history(booking)
        return customer

    def get_stay_history(self, customer_id):
        """Duyệt danh sách liên kết lịch sử của khách (mới nhất -> cũ nhất) — O(m)."""
        customer = self.get_customer(customer_id)
        return customer.history.to_list()

    def all_customers(self):
        return self._by_id.values()

    def load_customers(self, customers, sequence_value, bookings_by_id):
        """Khôi phục các bảng băm và danh sách liên kết lịch sử khi nạp file JSON."""
        self._by_id = HashTable()
        self._by_cccd = HashTable()
        self._by_phone = HashTable()
        self._id_gen.restore(sequence_value)
        for item in customers:
            customer = Customer.from_dict(item)
            for booking_id in item.get("history", []):
                booking = bookings_by_id.get(booking_id)
                if booking is not None:
                    customer.add_booking_to_history(booking)
            self._index_customer(customer)
            if customer.customer_id.startswith("KH") and customer.customer_id[2:].isdigit():
                self._id_gen.restore(int(customer.customer_id[2:]))

    def __len__(self):
        return len(self._by_id)


# ============================================================================
# MODULE: hotel/services/booking_service.py
# ============================================================================
"""Chức năng 2: Quản lý đặt phòng và kiểm tra xung đột ngày bằng BST (AVL Tree).

Độ phức tạp mục tiêu (n = số đơn đặt đang hiệu lực của một phòng):
- Kiểm tra xung đột khoảng ngày [check_in, check_out) trên 1 phòng : O(log n)
- Chèn đơn đặt phòng mới vào lịch phòng (BST theo check_in)        : O(log n)
- Xóa đơn đặt phòng khỏi lịch phòng (khi hủy)                      : O(log n)
- Tra cứu đơn đặt phòng theo mã booking_id                         : O(1) trung bình (HashTable)
"""




def _start_of(booking):
    return booking.check_in


def _end_of(booking):
    return booking.check_out


def validate_date_range(check_in, check_out):
    """Kiểm tra tính hợp lệ của khoảng ngày [check_in, check_out)."""
    if not isinstance(check_in, date) or not isinstance(check_out, date):
        raise HotelError("Ngày nhận phòng và trả phòng phải là kiểu date hợp lệ")
    if check_in >= check_out:
        raise HotelError(
            f"Ngày nhận phòng ({format_date(check_in)}) phải trước ngày trả phòng ({format_date(check_out)})"
        )
    nights = (check_out - check_in).days
    if nights > MAX_STAY_NIGHTS:
        raise HotelError(f"Số đêm lưu trú ({nights}) vượt quá giới hạn tối đa ({MAX_STAY_NIGHTS} đêm)")


class BookingService:
    def __init__(self, room_service, customer_service):
        self._room_service = room_service
        self._customer_service = customer_service
        self._schedules = HashTable()       # room_id -> IntervalSchedule (BST/AVL)
        self._bookings_by_id = HashTable()  # booking_id -> Booking
        self._id_gen = SequenceGenerator("BK", 5)
        self._vip_sync_callback = None
        self._init_room_schedules()

    def set_vip_sync_callback(self, callback):
        """Đăng ký hàm đồng bộ hạng VIP tự động mỗi khi phát sinh/thay đổi đơn đặt phòng."""
        self._vip_sync_callback = callback

    def _init_room_schedules(self):
        for room in self._room_service.all_rooms():
            if not self._schedules.contains(room.room_id):
                self._schedules.put(room.room_id, IntervalSchedule(_start_of, _end_of))

    def _schedule_of(self, room_id):
        schedule = self._schedules.get(room_id)
        if schedule is None:
            # Đảm bảo phòng hợp lệ trước khi tạo lịch
            room = self._room_service.get_room(room_id)
            schedule = IntervalSchedule(_start_of, _end_of)
            self._schedules.put(room.room_id, schedule)
        return schedule

    @property
    def id_generator(self):
        return self._id_gen

    # -------------- Kiểm tra xung đột & Tìm phòng trống ----------------- #
    def find_conflict(self, room_id, check_in, check_out):
        """Tìm booking đang xung đột với [check_in, check_out) tại `room_id` — O(log n)."""
        validate_date_range(check_in, check_out)
        room = self._room_service.get_room(room_id)
        return self._schedule_of(room.room_id).find_conflict(check_in, check_out)

    def is_room_available(self, room_id, check_in, check_out):
        """Kiểm tra phòng có trống và không bảo trì trong [check_in, check_out) — O(log n)."""
        validate_date_range(check_in, check_out)
        room = self._room_service.get_room(room_id)
        if room.under_maintenance:
            return False
        return self._schedule_of(room.room_id).is_free(check_in, check_out)

    def room_status_on(self, room_id, on_date):
        """Trạng thái phòng tại một ngày cụ thể `on_date` — O(log n)."""
        room = self._room_service.get_room(room_id)
        if room.under_maintenance:
            return RoomStatus.MAINTENANCE
        covering = self._schedule_of(room.room_id).find_covering(on_date)
        return RoomStatus.BOOKED if covering is not None else RoomStatus.EMPTY

    def active_booking_on(self, room_id, on_date):
        """Đơn đặt phòng đang chiếm `room_id` tại ngày `on_date` (nếu có) — O(log n)."""
        room = self._room_service.get_room(room_id)
        return self._schedule_of(room.room_id).find_covering(on_date)

    def find_available_rooms(
        self,
        check_in,
        check_out,
        room_type=None,
        min_price=0,
        max_price=float("inf"),
    ):
        """Tìm danh sách phòng trống trong [check_in, check_out) kết hợp lọc loại & giá.

        Bước 1: Dùng Binary Search trên mảng phòng đã sort để lấy các phòng thuộc
                loại `room_type` và khoảng giá `[min_price, max_price]` — O(log R + c).
        Bước 2: Với mỗi phòng ứng viên, kiểm tra xung đột trên BST lịch phòng — O(c log n).
        Kết quả trả về đã được sắp sẵn theo giá tăng dần.
        """
        validate_date_range(check_in, check_out)
        candidates = self._room_service.filter_by_price_range(
            min_price=min_price,
            max_price=max_price,
            room_type=room_type,
        )
        available = []
        for room in candidates:
            if not room.under_maintenance and self._schedule_of(room.room_id).is_free(check_in, check_out):
                available.append(room)
        return available

    # -------------------- Đặt phòng / Check-in / Check-out --------------- #
    def create_booking(self, customer_id, room_id, check_in, check_out, created_at=None):
        """Tạo đơn đặt phòng mới và chèn vào BST lịch phòng — O(log n)."""
        validate_date_range(check_in, check_out)
        customer = self._customer_service.get_customer(customer_id)
        room = self._room_service.get_room(room_id)

        if room.under_maintenance:
            raise RoomUnavailableError(f"Phòng {room.room_id} đang trong trạng thái BẢO TRÌ")

        schedule = self._schedule_of(room.room_id)
        conflict = schedule.find_conflict(check_in, check_out)
        if conflict is not None:
            raise RoomUnavailableError(
                f"Phòng {room.room_id} đã có đơn {conflict.booking_id} từ "
                f"{format_date(conflict.check_in)} đến {format_date(conflict.check_out)}",
                conflicting_booking=conflict,
            )

        booking = Booking(
            booking_id=self._id_gen.next_id(),
            customer_id=customer.customer_id,
            room_id=room.room_id,
            check_in=check_in,
            check_out=check_out,
            price_per_night=room.price_per_night,
            created_at=created_at or date.today(),
            status=BookingStatus.CONFIRMED,
            vip_level_at_booking=int(customer.vip_level),
        )
        schedule.add(booking)
        self._bookings_by_id.put(booking.booking_id, booking)
        self._customer_service.record_booking(customer.customer_id, booking)
        if self._vip_sync_callback is not None:
            try:
                self._vip_sync_callback(customer.customer_id)
            except Exception:
                pass
        return booking

    def get_booking(self, booking_id):
        """Tra cứu đơn đặt phòng theo mã — O(1) trung bình."""
        key = (booking_id or "").strip().upper()
        booking = self._bookings_by_id.get(key)
        if booking is None:
            raise NotFoundError(f"Không tìm thấy đơn đặt phòng '{booking_id}'")
        return booking

    def check_in(self, booking_id):
        """Nhận phòng (chuyển trạng thái CONFIRMED -> CHECKED_IN) — O(1)."""
        booking = self.get_booking(booking_id)
        if booking.status != BookingStatus.CONFIRMED:
            raise HotelError(
                f"Chỉ có thể nhận phòng cho đơn ở trạng thái 'Đã xác nhận' "
                f"(hiện tại: {booking.status.label})"
            )
        booking.status = BookingStatus.CHECKED_IN
        return booking

    def check_out(self, booking_id):
        """Trả phòng (chuyển CHECKED_IN -> CHECKED_OUT và giải phóng lịch phòng trên BST) — O(log n)."""
        booking = self.get_booking(booking_id)
        if booking.status != BookingStatus.CHECKED_IN:
            raise HotelError(
                f"Chỉ có thể trả phòng cho đơn đang ở trạng thái 'Đang ở' "
                f"(hiện tại: {booking.status.label})"
            )
        self.detach_booking_from_schedule(booking)
        booking.status = BookingStatus.CHECKED_OUT
        return booking

    # --------- Hỗ trợ Hủy & Hoàn tác trên BST (dùng bởi UndoService) ---- #
    def detach_booking_from_schedule(self, booking):
        """Gỡ booking khỏi BST lịch phòng khi hủy — O(log n)."""
        schedule = self._schedule_of(booking.room_id)
        if booking in schedule:
            schedule.remove(booking)

    def attach_booking_to_schedule(self, booking):
        """Đưa booking trở lại BST lịch phòng khi hoàn tác hủy — O(log n)."""
        room = self._room_service.get_room(booking.room_id)
        if room.under_maintenance:
            raise RoomUnavailableError(
                f"Không thể hoàn tác vì phòng {room.room_id} hiện đang bảo trì"
            )
        schedule = self._schedule_of(room.room_id)
        conflict = schedule.find_conflict(booking.check_in, booking.check_out)
        if conflict is not None:
            raise RoomUnavailableError(
                f"Không thể hoàn tác: khoảng ngày {format_date(booking.check_in)} - "
                f"{format_date(booking.check_out)} tại phòng {room.room_id} đã bị đơn "
                f"{conflict.booking_id} chiếm",
                conflicting_booking=conflict,
            )
        schedule.add(booking)

    # ------------------------- Truy vấn danh sách ----------------------- #
    def bookings_for_room(self, room_id, start_from=None, start_to=None):
        """Danh sách các booking đang hiệu lực của một phòng theo thứ tự ngày nhận tăng dần."""
        room = self._room_service.get_room(room_id)
        schedule = self._schedule_of(room.room_id)
        if start_from is not None and start_to is not None:
            return schedule.items_starting_between(start_from, start_to)
        return schedule.items()

    def all_bookings(self):
        return self._bookings_by_id.values()

    def bookings_by_id_map(self):
        return self._bookings_by_id

    def load_bookings(self, booking_dicts, sequence_value):
        """Khôi phục bảng băm và các cây BST lịch phòng từ dữ liệu lưu trữ."""
        self._schedules = HashTable()
        self._bookings_by_id = HashTable()
        self._init_room_schedules()
        self._id_gen.restore(sequence_value)

        for item in booking_dicts:
            booking = Booking.from_dict(item)
            self._bookings_by_id.put(booking.booking_id, booking)
            if booking.is_active:
                self._schedule_of(booking.room_id).add(booking)
            if booking.booking_id.startswith("BK") and booking.booking_id[2:].isdigit():
                self._id_gen.restore(int(booking.booking_id[2:]))


# ============================================================================
# MODULE: hotel/services/waiting_service.py
# ============================================================================
"""Chức năng 4: Quản lý danh sách chờ khi hết phòng (Queue & Priority Queue).

Thiết kế kết hợp 2 cấu trúc tự cài đặt đúng theo yêu cầu đề bài:
- Khách VIP (`vip_level >= 1`) : lưu trong `MaxHeap` (Priority Queue) với khóa
  `(priority, -sequence)` -> Thêm `O(log k)`, lấy khách ưu tiên cao nhất `O(log k)`,
  xem đầu hàng `O(1)`.
- Khách thường (`vip_level == 0`) : lưu trong `LinkedQueue` (FIFO Queue)
  -> Thêm `O(1)`, lấy ra `O(1)`, xem đầu hàng `O(1)`.
Khi có phòng trống, hệ thống luôn ưu tiên phục vụ khách trong `MaxHeap` (VIP) trước,
sau đó mới đến `LinkedQueue` (khách thường).
"""




def _entry_priority_key(entry):
    return entry.priority_key()


class WaitingService:
    def __init__(self, customer_service):
        self._customer_service = customer_service
        self._vip_heap = MaxHeap(_entry_priority_key)
        self._normal_queue = LinkedQueue()
        self._id_gen = SequenceGenerator("WL", 4)
        self._seq_gen = SequenceGenerator("SEQ", 1)

    @property
    def id_generator(self):
        return self._id_gen

    @property
    def sequence_generator(self):
        return self._seq_gen

    # ------------------ Thao tác Hàng đợi & Heap cốt lõi ---------------- #
    def enqueue(self, customer_id, room_type, check_in, check_out, requested_at=None):
        """Thêm khách vào danh sách chờ: O(log k) với khách VIP, O(1) với khách thường."""
        validate_date_range(check_in, check_out)
        customer = self._customer_service.get_customer(customer_id)
        rtype = room_type if isinstance(room_type, RoomType) else RoomType(room_type)

        entry = WaitingEntry(
            entry_id=self._id_gen.next_id(),
            customer_id=customer.customer_id,
            room_type=rtype,
            check_in=check_in,
            check_out=check_out,
            priority=int(customer.vip_level),
            sequence=self._seq_gen.next_number(),
            requested_at=requested_at or date.today(),
        )
        if entry.priority > 0:
            self._vip_heap.push(entry)
        else:
            self._normal_queue.enqueue(entry)
        return entry

    def peek_next(self):
        """Xem khách có độ ưu tiên cao nhất đang chờ — O(1)."""
        if not self._vip_heap.is_empty():
            return self._vip_heap.peek()
        if not self._normal_queue.is_empty():
            return self._normal_queue.peek()
        return None

    def pop_next(self):
        """Lấy khách ưu tiên cao nhất ra khỏi hàng chờ — O(log k) với VIP, O(1) với thường."""
        if not self._vip_heap.is_empty():
            return self._vip_heap.pop()
        if not self._normal_queue.is_empty():
            return self._normal_queue.dequeue()
        raise HotelError("Danh sách chờ hiện đang trống")

    def remove_entry(self, entry_id):
        """Xóa một mục chờ theo mã `entry_id`."""
        key = (entry_id or "").strip().upper()
        removed = self._vip_heap.remove_first(lambda e: e.entry_id == key)
        if removed is not None:
            return removed
        removed = self._normal_queue.remove_first(lambda e: e.entry_id == key)
        if removed is not None:
            return removed
        raise NotFoundError(f"Không tìm thấy mục chờ '{entry_id}'")

    def update_customer_priority(self, customer_id, new_priority):
        """Cập nhật mức ưu tiên cho các mục chờ của khách hàng — O(log k) mỗi lần vun đống."""
        cid = (customer_id or "").strip().upper()
        new_prio = int(new_priority)
        updated_count = 0

        if new_prio <= 0:
            # Hạ từ VIP về khách thường (0): chuyển khỏi Max-Heap sang LinkedQueue theo đúng thứ tự sequence
            downgraded = []
            while True:
                removed = self._vip_heap.remove_first(lambda e: e.customer_id == cid)
                if removed is None:
                    break
                removed.priority = 0
                downgraded.append(removed)
                updated_count += 1

            for entry in self._normal_queue:
                if entry.customer_id == cid and entry.priority != 0:
                    entry.priority = 0
                    updated_count += 1

            if downgraded:
                combined_normal = merge_sort(
                    list(self._normal_queue) + downgraded,
                    key=lambda e: e.sequence,
                )
                self._normal_queue = LinkedQueue()
                for entry in combined_normal:
                    self._normal_queue.enqueue(entry)
            return updated_count

        # Trường hợp new_prio > 0: cập nhật các mục đang ở trong VIP Max-Heap
        matching_vip = [entry for entry in self._vip_heap if entry.customer_id == cid]
        for target_entry in matching_vip:
            target_entry.priority = new_prio
            for current_idx, heap_entry in enumerate(self._vip_heap):
                if heap_entry is target_entry:
                    self._vip_heap.update_key_at(current_idx)
                    break
            updated_count += 1

        # Nếu khách từ thường (0) lên VIP (>0), chuyển từ Queue thường sang VIP Max-Heap
        while True:
            moved = self._normal_queue.remove_first(lambda e: e.customer_id == cid)
            if moved is None:
                break
            moved.priority = new_prio
            self._vip_heap.push(moved)
            updated_count += 1

        return updated_count

    # --------- Tự động phân phòng khi có phòng trống trở lại ------------ #
    def try_fulfill_waiting_list(self, booking_service, room_type_filter=None):
        """Duyệt danh sách chờ theo đúng thứ tự ưu tiên (VIP trước, thường sau)
        và tự động đặt phòng nếu có phòng trống phù hợp.

        Trả về danh sách các cặp `(waiting_entry, created_booking)`.
        """
        fulfilled = []
        deferred_vip = []
        deferred_normal = []

        while not self._vip_heap.is_empty():
            entry = self._vip_heap.pop()
            if room_type_filter is not None and entry.room_type != room_type_filter:
                deferred_vip.append(entry)
                continue
            available = booking_service.find_available_rooms(
                entry.check_in, entry.check_out, room_type=entry.room_type
            )
            if available:
                chosen_room = available[0]
                booking = booking_service.create_booking(
                    customer_id=entry.customer_id,
                    room_id=chosen_room.room_id,
                    check_in=entry.check_in,
                    check_out=entry.check_out,
                )
                fulfilled.append((entry, booking))
            else:
                deferred_vip.append(entry)

        for entry in deferred_vip:
            self._vip_heap.push(entry)

        while not self._normal_queue.is_empty():
            entry = self._normal_queue.dequeue()
            if room_type_filter is not None and entry.room_type != room_type_filter:
                deferred_normal.append(entry)
                continue
            available = booking_service.find_available_rooms(
                entry.check_in, entry.check_out, room_type=entry.room_type
            )
            if available:
                chosen_room = available[0]
                booking = booking_service.create_booking(
                    customer_id=entry.customer_id,
                    room_id=chosen_room.room_id,
                    check_in=entry.check_in,
                    check_out=entry.check_out,
                )
                fulfilled.append((entry, booking))
            else:
                deferred_normal.append(entry)

        for entry in deferred_normal:
            self._normal_queue.enqueue(entry)

        return fulfilled

    # -------------------------- Truy vấn & Nạp -------------------------- #
    def list_waiting_ordered(self):
        """Danh sách toàn bộ khách đang chờ theo đúng thứ tự phục vụ (VIP giảm dần -> Thường FIFO)."""
        return self._vip_heap.to_sorted_list() + list(self._normal_queue)

    def vip_count(self):
        return len(self._vip_heap)

    def normal_count(self):
        return len(self._normal_queue)

    def __len__(self):
        return len(self._vip_heap) + len(self._normal_queue)

    def to_Reference_list(self):
        return [entry.to_dict() for entry in self.list_waiting_ordered()]

    def load_waiting_entries(self, entry_dicts, id_seq, order_seq):
        self._vip_heap = MaxHeap(_entry_priority_key)
        self._normal_queue = LinkedQueue()
        self._id_gen.restore(id_seq)
        self._seq_gen.restore(order_seq)

        # Sắp lại theo sequence tăng dần bằng Merge Sort trước khi đưa vào Queue thường để bảo toàn FIFO
        entries = merge_sort(
            [WaitingEntry.from_dict(item) for item in entry_dicts],
            key=lambda e: e.sequence,
        )
        for entry in entries:
            if entry.priority > 0:
                self._vip_heap.push(entry)
            else:
                self._normal_queue.enqueue(entry)
            self._seq_gen.restore(entry.sequence)
            if entry.entry_id.startswith("WL") and entry.entry_id[2:].isdigit():
                self._id_gen.restore(int(entry.entry_id[2:]))


# ============================================================================
# MODULE: hotel/services/undo_service.py
# ============================================================================
"""Chức năng 6: Hủy đặt phòng và Hoàn tác (Undo) bằng Ngăn xếp (Stack).

Độ phức tạp mục tiêu:
- Lưu thao tác hủy vào Stack (push)          : O(1)
- Lấy thao tác hủy gần nhất từ Stack (pop)   : O(1)
- Xem thao tác hủy sắp hoàn tác (peek)       : O(1)
- Cập nhật lịch phòng trên BST khi hủy/undo  : O(log n)
"""




class UndoService:
    def __init__(self, booking_service):
        self._booking_service = booking_service
        self._undo_stack = Stack()

    def cancel_booking(self, booking_id, cancelled_by="STAFF", cancelled_at=None):
        """Hủy một đơn đặt phòng và đẩy bản chụp trạng thái vào Stack — O(1) stack + O(log n) BST."""
        booking = self._booking_service.get_booking(booking_id)
        if booking.status == BookingStatus.CANCELLED:
            raise HotelError(f"Đơn đặt phòng {booking.booking_id} đã ở trạng thái ĐÃ HỦY")
        if booking.status == BookingStatus.CHECKED_OUT:
            raise HotelError(
                f"Không thể hủy đơn {booking.booking_id} vì khách đã trả phòng (CHECKED_OUT)"
            )

        snapshot = booking.to_dict()
        self._booking_service.detach_booking_from_schedule(booking)
        booking.status = BookingStatus.CANCELLED

        action = CancelAction(
            booking_id=booking.booking_id,
            room_id=booking.room_id,
            booking_snapshot=snapshot,
            cancelled_by=cancelled_by,
            cancelled_at=cancelled_at or date.today(),
        )
        self._undo_stack.push(action)
        return action

    def peek_last_cancellation(self):
        """Xem thao tác hủy gần nhất trên đỉnh Stack mà không xóa — O(1)."""
        if self._undo_stack.is_empty():
            return None
        return self._undo_stack.peek()

    def undo_last_cancellation(self):
        """Hoàn tác thao tác hủy gần nhất: pop Stack O(1) + chèn lại vào BST O(log n)."""
        if self._undo_stack.is_empty():
            raise HotelError("Ngăn xếp hoàn tác đang trống — không có thao tác hủy nào để hoàn tác")

        action = self._undo_stack.pop()
        booking = self._booking_service.get_booking(action.booking_id)
        previous_status = BookingStatus(action.booking_snapshot["status"])

        try:
            self._booking_service.attach_booking_to_schedule(booking)
        except Exception:
            # Nếu không thể khôi phục (do phòng đã bị người khác đặt chồng), trả lại vào Stack
            self._undo_stack.push(action)
            raise

        booking.status = previous_status
        return action, booking

    def history(self):
        """Danh sách các thao tác hủy đang lưu trong Stack (từ mới nhất xuống cũ nhất)."""
        return list(self._undo_stack)

    def __len__(self):
        return len(self._undo_stack)

    def load_actions(self, action_dicts):
        """Khôi phục ngăn xếp hoàn tác từ dữ liệu JSON (action_dicts lưu từ đỉnh xuống đáy)."""
        self._undo_stack = Stack()
        for item in reversed(action_dicts):
            self._undo_stack.push(CancelAction.from_dict(item))


# ============================================================================
# MODULE: hotel/services/service_request_service.py
# ============================================================================
"""Chức năng 7: Quản lý yêu cầu dịch vụ nội bộ (Dọn phòng, Đồ ăn, Y tế...) bằng Priority Queue.

Độ phức tạp mục tiêu (s = số yêu cầu đang chờ xử lý):
- Thêm yêu cầu dịch vụ mới (push vào Max-Heap) : O(log s)
- Lấy yêu cầu khẩn nhất để xử lý (pop)         : O(log s)
- Xem yêu cầu khẩn nhất (peek)                 : O(1)

Thứ tự ưu tiên: EMERGENCY (3) > NORMAL (2) > LOW (1).
Cùng độ khẩn: yêu cầu gửi sớm hơn (sequence nhỏ hơn) được phục vụ trước.
"""




def _request_priority_key(req):
    return req.priority_key()


DEFAULT_URGENCY_BY_SERVICE = {
    ServiceType.MEDICAL: UrgencyLevel.EMERGENCY,
    ServiceType.FOOD: UrgencyLevel.NORMAL,
    ServiceType.CLEANING: UrgencyLevel.LOW,
    ServiceType.OTHER: UrgencyLevel.NORMAL,
}


class ServiceRequestService:
    def __init__(self, room_service, customer_service):
        self._room_service = room_service
        self._customer_service = customer_service
        self._pending_heap = MaxHeap(_request_priority_key)
        self._completed_list = SinglyLinkedList()
        self._id_gen = SequenceGenerator("SR", 4)
        self._seq_gen = SequenceGenerator("SRSEQ", 1)

    @property
    def id_generator(self):
        return self._id_gen

    @property
    def sequence_generator(self):
        return self._seq_gen

    def submit_request(
        self,
        room_id,
        service_type,
        urgency=None,
        note="",
        customer_id="",
        requested_at=None,
    ):
        """Gửi một yêu cầu dịch vụ mới vào Max-Heap — O(log s)."""
        room = self._room_service.get_room(room_id)
        stype = service_type if isinstance(service_type, ServiceType) else ServiceType(service_type)
        if urgency is None:
            ulevel = DEFAULT_URGENCY_BY_SERVICE[stype]
        else:
            ulevel = urgency if isinstance(urgency, UrgencyLevel) else UrgencyLevel(int(urgency))

        cid = ""
        if customer_id and customer_id.strip():
            cid = self._customer_service.get_customer(customer_id).customer_id

        request = ServiceRequest(
            request_id=self._id_gen.next_id(),
            room_id=room.room_id,
            customer_id=cid,
            service_type=stype,
            urgency=ulevel,
            note=(note or "").strip(),
            sequence=self._seq_gen.next_number(),
            requested_at=requested_at or date.today(),
            status=ServiceStatus.WAITING,
        )
        self._pending_heap.push(request)
        return request

    def peek_next(self):
        """Xem yêu cầu dịch vụ có độ khẩn cao nhất — O(1)."""
        if self._pending_heap.is_empty():
            return None
        return self._pending_heap.peek()

    def process_next(self):
        """Xử lý yêu cầu dịch vụ khẩn nhất (pop khỏi Max-Heap) — O(log s)."""
        if self._pending_heap.is_empty():
            raise HotelError("Hiện không có yêu cầu dịch vụ nào đang chờ xử lý")
        request = self._pending_heap.pop()
        request.status = ServiceStatus.DONE
        self._completed_list.push_front(request)
        return request

    def pending_requests_ordered(self):
        """Danh sách yêu cầu đang chờ theo thứ tự ưu tiên giảm dần — O(s log s)."""
        return self._pending_heap.to_sorted_list()

    def completed_requests(self):
        """Danh sách các yêu cầu đã hoàn thành (mới nhất trước)."""
        return self._completed_list.to_list()

    def all_requests(self):
        """Danh sách toàn bộ yêu cầu dịch vụ (cả đang chờ và đã hoàn thành)."""
        return list(self._pending_heap) + self._completed_list.to_list()

    def pending_count(self):
        return len(self._pending_heap)

    def completed_count(self):
        return len(self._completed_list)

    def load_requests(self, pending_dicts, completed_dicts, id_seq, order_seq):
        self._pending_heap = MaxHeap(_request_priority_key)
        self._completed_list = SinglyLinkedList()
        self._id_gen.restore(id_seq)
        self._seq_gen.restore(order_seq)

        for item in pending_dicts:
            req = ServiceRequest.from_dict(item)
            self._pending_heap.push(req)
            self._seq_gen.restore(req.sequence)
            if req.request_id.startswith("SR") and req.request_id[2:].isdigit():
                self._id_gen.restore(int(req.request_id[2:]))

        # completed_dicts lưu từ mới -> cũ, nạp ngược lại bằng push_front
        for item in reversed(completed_dicts):
            req = ServiceRequest.from_dict(item)
            self._completed_list.push_front(req)
            self._seq_gen.restore(req.sequence)
            if req.request_id.startswith("SR") and req.request_id[2:].isdigit():
                self._id_gen.restore(int(req.request_id[2:]))


# ============================================================================
# MODULE: hotel/services/payment_service.py
# ============================================================================
"""Chức năng 8: Quản lý thanh toán — Tính tổng chi phí, xử lý thanh toán, lưu trữ & tra cứu giao dịch.

Cấu trúc dữ liệu & Giải thuật sử dụng:
- Bảng băm (`HashTable` chaining):
    + `_by_payment_id`  : Tra cứu giao dịch theo mã thanh toán (TT00001) — O(1) trung bình.
    + `_by_booking_id`  : Tra cứu danh sách giao dịch của một đơn đặt phòng (BK00001) — O(1) trung bình.
    + `_by_customer_id` : Tra cứu lịch sử giao dịch theo mã khách hàng (KH001) — O(1) trung bình.
- Danh sách liên kết đơn (`SinglyLinkedList`):
    + `_transactions`   : Lưu trữ chuỗi giao dịch theo thời gian (mới nhất ở đầu `push_front` — O(1)).
- Sắp xếp (`merge_sort`):
    + Sắp xếp danh sách giao dịch theo tổng tiền, ngày thanh toán hoặc mã giao dịch — O(p log p).
"""




def _parse_payment_method(method):
    if isinstance(method, PaymentMethod):
        return method
    raw = (str(method) if method is not None else "").strip().upper()
    aliases = {
        "1": PaymentMethod.CASH,
        "CASH": PaymentMethod.CASH,
        "TIEN_MAT": PaymentMethod.CASH,
        "TIỀN MẶT": PaymentMethod.CASH,
        "2": PaymentMethod.BANK_TRANSFER,
        "BANK_TRANSFER": PaymentMethod.BANK_TRANSFER,
        "TRANSFER": PaymentMethod.BANK_TRANSFER,
        "CHUYEN_KHOAN": PaymentMethod.BANK_TRANSFER,
        "CHUYỂN KHOẢN": PaymentMethod.BANK_TRANSFER,
        "3": PaymentMethod.CARD,
        "CARD": PaymentMethod.CARD,
        "CREDIT_CARD": PaymentMethod.CARD,
        "THE": PaymentMethod.CARD,
        "THẺ": PaymentMethod.CARD,
        "THẺ NGÂN HÀNG": PaymentMethod.CARD,
        "THE_NGAN_HANG": PaymentMethod.CARD,
        "4": PaymentMethod.E_WALLET,
        "E_WALLET": PaymentMethod.E_WALLET,
        "WALLET": PaymentMethod.E_WALLET,
        "VI_DIEN_TU": PaymentMethod.E_WALLET,
        "VÍ ĐIỆN TỬ": PaymentMethod.E_WALLET,
    }
    if raw in aliases:
        return aliases[raw]
    raise HotelError(
        f"Phương thức thanh toán '{method}' không hợp lệ "
        f"(chọn CASH, BANK_TRANSFER, CARD hoặc E_WALLET)"
    )


def _parse_payment_status(status):
    if isinstance(status, PaymentStatus):
        return status
    raw = (str(status) if status is not None else "").strip().upper()
    try:
        return PaymentStatus(raw)
    except ValueError as exc:
        raise HotelError(
            f"Trạng thái thanh toán '{status}' không hợp lệ (chọn UNPAID, PAID hoặc REFUNDED)"
        ) from exc


class PaymentService:
    def __init__(
        self,
        room_service,
        customer_service,
        booking_service,
        service_request_service=None,
        waiting_service=None,
    ):
        self._room_service = room_service
        self._customer_service = customer_service
        self._booking_service = booking_service
        self._service_request_service = service_request_service
        self._waiting_service = waiting_service

        self._by_payment_id = HashTable()   # payment_id -> PaymentTransaction
        self._by_booking_id = HashTable()   # booking_id -> SinglyLinkedList[PaymentTransaction]
        self._by_customer_id = HashTable()  # customer_id -> SinglyLinkedList[PaymentTransaction]
        self._transactions = SinglyLinkedList()
        self._id_gen = SequenceGenerator("TT", 5)

        if self._booking_service is not None and hasattr(self._booking_service, "set_vip_sync_callback"):
            self._booking_service.set_vip_sync_callback(self.sync_customer_vip)

    @property
    def id_generator(self):
        return self._id_gen

    # -------------------- 1. Tính tổng chi phí hóa đơn -------------------- #
    def _match_booking_for_request(self, req, room_bookings):
        """Xác định duy nhất một đơn đặt phòng chịu phí cho yêu cầu dịch vụ `req`."""
        if req.customer_id:
            candidates = [b for b in room_bookings if b.customer_id == req.customer_id]
        else:
            candidates = list(room_bookings)

        if not candidates:
            return None

        status_rank = {
            BookingStatus.CHECKED_IN: 3,
            BookingStatus.CONFIRMED: 2,
            BookingStatus.CHECKED_OUT: 1,
        }

        covering = [b for b in candidates if b.check_in <= req.requested_at <= b.check_out]
        if covering:
            # Ưu tiên:
            # 1. Đơn đang ở (CHECKED_IN) tại phòng
            # 2. Ngày yêu cầu nằm trọn trong nửa mở [check_in, check_out) (tránh tính trùng ngày trả phòng
            #    khi khách cũ trả phòng và khách mới nhận phòng trong cùng một ngày)
            # 3. Trạng thái ưu tiên cao hơn (CHECKED_IN > CONFIRMED > CHECKED_OUT)
            # 4. Ngày check_in mới nhất
            return max(
                covering,
                key=lambda b: (
                    1 if b.status == BookingStatus.CHECKED_IN else 0,
                    1 if b.check_in <= req.requested_at < b.check_out else 0,
                    status_rank.get(b.status, 0),
                    b.check_in,
                    b.booking_id,
                ),
            )

        def _distance_days(b):
            if req.requested_at < b.check_in:
                return (b.check_in - req.requested_at).days
            return (req.requested_at - b.check_out).days

        return max(
            candidates,
            key=lambda b: (
                status_rank.get(b.status, 0),
                -_distance_days(b),
                b.check_in,
                b.booking_id,
            ),
        )

    def _service_requests_for_booking(self, booking):
        """Lấy các yêu cầu dịch vụ nội bộ phát sinh thuộc về đơn đặt phòng `booking`."""
        if self._service_request_service is None or booking.status == BookingStatus.CANCELLED:
            return []

        all_reqs = self._service_request_service.all_requests()
        room_bookings = [
            b
            for b in self._booking_service.all_bookings()
            if b.room_id == booking.room_id and b.status != BookingStatus.CANCELLED
        ]

        matched = []
        for req in all_reqs:
            if req.room_id != booking.room_id:
                continue
            owner = self._match_booking_for_request(req, room_bookings)
            if owner is not None and owner.booking_id == booking.booking_id:
                matched.append(req)

        return merge_sort(matched, key=lambda r: r.sequence)

    def calculate_total_cost(self, booking_id, extra_fee=0):
        """Tính tổng chi phí chi tiết cho một đơn đặt phòng.

        Bao gồm:
        - Tiền phòng (`room_cost` = số đêm × đơn giá phòng / đêm)
        - Phí dịch vụ nội bộ (`service_cost` = tổng phí các yêu cầu Dọn phòng, Đồ ăn, Y tế, Khác)
        - Phụ phí phát sinh khác (`extra_fee`)
        - Chiết khấu theo hạng VIP của khách hàng (`discount_amount`)
        - Tổng chi phí thực thu (`total_amount`)
        """
        if isinstance(extra_fee, bool):
            raise HotelError("Phụ phí phát sinh phải là số nguyên không âm")
        try:
            extra_fee_val = int(extra_fee or 0)
        except (ValueError, TypeError) as exc:
            raise HotelError("Phụ phí phát sinh phải là số nguyên không âm") from exc
        if extra_fee_val < 0:
            raise HotelError("Phụ phí phát sinh không được nhỏ hơn 0")

        booking = self._booking_service.get_booking(booking_id)
        customer = self._customer_service.get_customer(booking.customer_id)
        room = self._room_service.get_room(booking.room_id)

        room_cost = booking.total_price
        reqs = self._service_requests_for_booking(booking)
        service_items = []
        for req in reqs:
            fee = SERVICE_PRICE_BY_TYPE.get(req.service_type, 0)
            service_items.append(
                {
                    "request_id": req.request_id,
                    "service_type": req.service_type,
                    "urgency": req.urgency,
                    "status": req.status,
                    "fee": fee,
                    "note": req.note,
                }
            )
        service_cost = sum(item["fee"] for item in service_items)

        existing_payments = self.get_payments_by_booking(booking.booking_id)
        paid_txs = [tx for tx in existing_payments if tx.status == PaymentStatus.PAID]
        paid_extra_fee = sum(tx.extra_fee for tx in paid_txs)
        effective_extra_fee = max(extra_fee_val, paid_extra_fee)

        gross_amount = room_cost + service_cost + effective_extra_fee
        base_vip_val = (
            int(booking.vip_level_at_booking)
            if getattr(booking, "vip_level_at_booking", None) is not None
            else int(customer.vip_level)
        )
        if getattr(customer, "manual_vip_level", None) is not None:
            base_vip_val = max(base_vip_val, int(customer.manual_vip_level))
        booking_vip_level = VipLevel(base_vip_val)
        discount_rate = VIP_DISCOUNT_RATES.get(booking_vip_level, 0.0)

        if not paid_txs:
            discount_amount = int(round(gross_amount * discount_rate))
            total_amount = max(0, gross_amount - discount_amount)
            paid_amount = 0
            remaining_amount = total_amount
        else:
            paid_gross = sum(tx.gross_amount for tx in paid_txs)
            paid_discount = sum(tx.discount_amount for tx in paid_txs)
            paid_amount = sum(tx.total_amount for tx in paid_txs)
            delta_gross = max(0, gross_amount - paid_gross)
            delta_discount = int(round(delta_gross * discount_rate))
            discount_amount = paid_discount + delta_discount
            remaining_amount = max(0, delta_gross - delta_discount)
            total_amount = paid_amount + remaining_amount

        active_tx = paid_txs[0] if paid_txs else None
        is_fully_paid = active_tx is not None and remaining_amount == 0

        if is_fully_paid:
            payment_status = PaymentStatus.PAID
        elif any(tx.status == PaymentStatus.REFUNDED for tx in existing_payments) and active_tx is None:
            payment_status = PaymentStatus.REFUNDED
        else:
            payment_status = PaymentStatus.UNPAID

        prior_spending = (
            self.get_customer_effective_spending(
                customer.customer_id, exclude_unpaid_booking_id=booking.booking_id
            )
            if not is_fully_paid
            else self.get_customer_effective_spending(customer.customer_id)
        )
        customer_total_paid = prior_spending
        projected_total_paid = prior_spending + remaining_amount
        qualifying_after = max(
            projected_total_paid,
            self.get_customer_qualifying_spending(customer.customer_id),
        )
        earned_after = evaluate_vip_level_by_spending(qualifying_after)
        projected_vip = VipLevel(max(int(customer.vip_level), int(earned_after)))
        applied_discount_rate = (
            round(discount_amount / gross_amount, 4)
            if (is_fully_paid and gross_amount > 0)
            else discount_rate
        )

        return {
            "booking": booking,
            "customer": customer,
            "room": room,
            "num_nights": booking.num_nights,
            "price_per_night": booking.price_per_night,
            "room_cost": room_cost,
            "service_items": service_items,
            "service_cost": service_cost,
            "extra_fee": effective_extra_fee,
            "gross_amount": gross_amount,
            "vip_level": booking_vip_level,
            "discount_rate": discount_rate,
            "applied_discount_rate": applied_discount_rate,
            "discount_amount": discount_amount,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount,
            "is_paid": is_fully_paid,
            "payment_status": payment_status,
            "active_payment": active_tx,
            "customer_total_paid": customer_total_paid,
            "projected_total_paid": projected_total_paid,
            "projected_vip_level": projected_vip,
            "will_upgrade_vip": projected_vip > booking_vip_level,
        }

    # -------------------- 2. Xử lý & Lưu trữ giao dịch -------------------- #
    def process_payment(
        self,
        booking_id,
        payment_method=PaymentMethod.CASH,
        extra_fee=0,
        note="",
        paid_at=None,
    ):
        """Xử lý thanh toán cho đơn đặt phòng, lưu giao dịch và tự động xét nâng hạng VIP tích lũy."""
        booking = self._booking_service.get_booking(booking_id)
        if booking.status == BookingStatus.CANCELLED:
            raise HotelError(
                f"Không thể thanh toán cho đơn đặt phòng {booking.booking_id} vì đơn đã bị hủy"
            )

        method = _parse_payment_method(payment_method)
        paid_txs = self.get_active_payments_for_booking(booking.booking_id)
        bill = self.calculate_total_cost(booking.booking_id, extra_fee=extra_fee)

        if paid_txs and bill["remaining_amount"] <= 0:
            raise HotelError(
                f"Đơn đặt phòng {booking.booking_id} đã được thanh toán "
                f"(Mã giao dịch: {paid_txs[0].payment_id})"
            )

        paid_room_cost = sum(t.room_cost for t in paid_txs)
        paid_service_cost = sum(t.service_cost for t in paid_txs)
        paid_extra_fee = sum(t.extra_fee for t in paid_txs)
        paid_discount = sum(t.discount_amount for t in paid_txs)

        tx = PaymentTransaction(
            payment_id=self._id_gen.next_id(),
            booking_id=booking.booking_id,
            customer_id=booking.customer_id,
            room_id=booking.room_id,
            room_cost=max(0, bill["room_cost"] - paid_room_cost),
            service_cost=max(0, bill["service_cost"] - paid_service_cost),
            extra_fee=max(0, bill["extra_fee"] - paid_extra_fee),
            discount_amount=max(0, bill["discount_amount"] - paid_discount),
            total_amount=bill["remaining_amount"],
            payment_method=method,
            paid_at=paid_at or date.today(),
            status=PaymentStatus.PAID,
            note=(note or "").strip(),
        )
        self._store_transaction(tx)
        self.sync_customer_vip(booking.customer_id)
        return tx

    def _store_transaction(self, tx):
        """Lưu giao dịch vào 3 bảng băm chỉ mục O(1) và đầu danh sách liên kết đơn O(1)."""
        self._by_payment_id.put(tx.payment_id, tx)

        booking_list = self._by_booking_id.get(tx.booking_id)
        if booking_list is None:
            booking_list = SinglyLinkedList()
            self._by_booking_id.put(tx.booking_id, booking_list)
        booking_list.push_front(tx)

        customer_list = self._by_customer_id.get(tx.customer_id)
        if customer_list is None:
            customer_list = SinglyLinkedList()
            self._by_customer_id.put(tx.customer_id, customer_list)
        customer_list.push_front(tx)

        self._transactions.push_front(tx)

    def refund_payment(self, identifier, reason=""):
        """Hoàn tiền cho một giao dịch thanh toán (theo mã TT... hoặc mã đơn BK...)."""
        key = (identifier or "").strip().upper()
        if not key:
            raise HotelError("Vui lòng nhập mã giao dịch hoặc mã đơn đặt phòng cần hoàn tiền")

        tx = self._by_payment_id.get(key)
        if tx is None:
            tx = self.get_active_payment_for_booking(key)
        if tx is None:
            raise NotFoundError(
                f"Không tìm thấy giao dịch thanh toán đang hiệu lực cho '{identifier}'"
            )
        if tx.status == PaymentStatus.REFUNDED:
            raise HotelError(f"Giao dịch {tx.payment_id} đã ở trạng thái Đã hoàn tiền")

        tx.status = PaymentStatus.REFUNDED
        clean_reason = (reason or "").strip()
        if clean_reason:
            tx.note = f"{tx.note} | Hoàn tiền: {clean_reason}" if tx.note else f"Hoàn tiền: {clean_reason}"
        try:
            self.sync_customer_vip(tx.customer_id, allow_downgrade=False)
        except NotFoundError:
            pass
        return tx

    # -------------------- 3. Tra cứu giao dịch thanh toán ---------------- #
    def get_payment(self, payment_id):
        """Tra cứu trực tiếp giao dịch theo mã `payment_id` (vd TT00001) — O(1) trung bình."""
        key = (payment_id or "").strip().upper()
        tx = self._by_payment_id.get(key)
        if tx is None:
            raise NotFoundError(f"Không tìm thấy giao dịch thanh toán '{payment_id}'")
        return tx

    def get_payments_by_booking(self, booking_id):
        """Lấy danh sách các giao dịch của một đơn đặt phòng — O(1) trung bình."""
        key = (booking_id or "").strip().upper()
        ll = self._by_booking_id.get(key)
        return ll.to_list() if ll is not None else []

    def get_active_payments_for_booking(self, booking_id):
        """Trả về danh sách các giao dịch PAID đang hiệu lực của đơn đặt phòng — O(1) trung bình."""
        return [
            tx
            for tx in self.get_payments_by_booking(booking_id)
            if tx.status == PaymentStatus.PAID
        ]

    def get_active_payment_for_booking(self, booking_id):
        """Trả về giao dịch PAID hiện hành mới nhất của đơn đặt phòng (hoặc None) — O(1) trung bình."""
        active = self.get_active_payments_for_booking(booking_id)
        return active[0] if active else None

    def is_booking_paid(self, booking_id):
        """Kiểm tra đơn đặt phòng đã được thanh toán đầy đủ hay chưa."""
        active = self.get_active_payments_for_booking(booking_id)
        if not active:
            return False
        bill = self.calculate_total_cost(booking_id)
        return bill["is_paid"]

    def get_payments_by_customer(self, customer_identifier):
        """Tra cứu lịch sử giao dịch thanh toán của khách hàng (theo Mã KH / CCCD / SĐT) — O(1) TB."""
        customer = self._customer_service.lookup(customer_identifier)
        ll = self._by_customer_id.get(customer.customer_id)
        return ll.to_list() if ll is not None else []

    def get_customer_paid_transactions_total(self, customer_identifier):
        """Tính tổng số tiền từ các giao dịch thanh toán PAID của một khách hàng."""
        customer = self._customer_service.lookup(customer_identifier)
        ll = self._by_customer_id.get(customer.customer_id)
        if ll is None:
            return 0
        return sum(tx.total_amount for tx in ll if tx.status == PaymentStatus.PAID)

    def get_customer_booking_spending(self, customer_identifier, exclude_booking_id=None):
        """Tính tổng giá trị các đơn đặt phòng đang hiệu lực (không bị hủy / hoàn tiền) của khách."""
        customer = self._customer_service.lookup(customer_identifier)
        total = 0
        for b in customer.history:
            if b.status == BookingStatus.CANCELLED:
                continue
            if exclude_booking_id is not None and b.booking_id == exclude_booking_id:
                continue
            txs = self.get_payments_by_booking(b.booking_id)
            has_paid = any(tx.status == PaymentStatus.PAID for tx in txs)
            has_refunded = any(tx.status == PaymentStatus.REFUNDED for tx in txs)
            if has_refunded and not has_paid:
                continue
            total += b.total_price
        return total

    def get_customer_effective_spending(self, customer_identifier, exclude_unpaid_booking_id=None):
        """Tính tổng chi tiêu lũy kế thực tế (đơn đã TT tính theo số tiền TT, đơn chưa TT tính theo giá đặt)."""
        customer = self._customer_service.lookup(customer_identifier)
        total = 0
        counted_booking_ids = set()
        for b in customer.history:
            if b.status == BookingStatus.CANCELLED:
                continue
            counted_booking_ids.add(b.booking_id)
            txs = self.get_payments_by_booking(b.booking_id)
            paid_amt = sum(tx.total_amount for tx in txs if tx.status == PaymentStatus.PAID)
            has_refunded = any(tx.status == PaymentStatus.REFUNDED for tx in txs)
            if paid_amt > 0:
                total += paid_amt
            elif has_refunded:
                continue
            else:
                if exclude_unpaid_booking_id is not None and b.booking_id == exclude_unpaid_booking_id:
                    continue
                total += b.total_price

        ll = self._by_customer_id.get(customer.customer_id)
        if ll is not None:
            for tx in ll:
                if tx.status == PaymentStatus.PAID and tx.booking_id not in counted_booking_ids:
                    total += tx.total_amount
        return total

    def get_customer_qualifying_spending(self, customer_identifier):
        """Tổng chi tiêu dùng để xét nâng hạng VIP tự động = max(đã thanh toán, tổng đặt phòng hiệu lực)."""
        paid_tx_total = self.get_customer_paid_transactions_total(customer_identifier)
        booking_total = self.get_customer_booking_spending(customer_identifier)
        effective_total = self.get_customer_effective_spending(customer_identifier)
        return max(paid_tx_total, booking_total, effective_total)

    def get_customer_total_paid(self, customer_identifier):
        """Tính tổng chi tiêu lũy kế của khách hàng (bao gồm giao dịch PAID và đơn đặt phòng hiệu lực)."""
        return self.get_customer_effective_spending(customer_identifier)

    def get_customer_vip_progress(self, customer_identifier):
        """Lấy thông tin chi tiêu tích lũy và tiến độ lên hạng VIP tiếp theo của khách."""
        customer = self._customer_service.lookup(customer_identifier)
        ll = self._by_customer_id.get(customer.customer_id)
        paid_txs = [tx for tx in ll if tx.status == PaymentStatus.PAID] if ll is not None else []
        effective_paid = self.get_customer_effective_spending(customer.customer_id)
        qualifying_spending = self.get_customer_qualifying_spending(customer.customer_id)
        progress = get_vip_tier_progress(customer.vip_level, qualifying_spending)
        progress["total_paid"] = effective_paid
        progress["qualifying_spending"] = qualifying_spending
        return {
            "customer": customer,
            "customer_id": customer.customer_id,
            "paid_transaction_count": len(paid_txs),
            **progress,
        }

    def sync_customer_vip(self, customer_identifier, allow_downgrade=False):
        """Tự động xét và nâng hạng VIP cho khách hàng khi tổng chi tiêu đặt phòng / thanh toán đạt mốc.

        Đồng bộ ngay mức độ ưu tiên trong `WaitingService` (chuyển từ LinkedQueue sang MaxHeap
        hoặc vun lại đống MaxHeap nếu khách đang nằm trong danh sách chờ).
        """
        customer = self._customer_service.lookup(customer_identifier)
        qualifying_spending = self.get_customer_qualifying_spending(customer.customer_id)
        res = self._customer_service.evaluate_and_update_vip(
            customer.customer_id,
            qualifying_spending,
            allow_downgrade=allow_downgrade,
        )
        res["total_paid"] = self.get_customer_effective_spending(customer.customer_id)
        res["qualifying_spending"] = qualifying_spending
        if res["changed"] and self._waiting_service is not None:
            self._waiting_service.update_customer_priority(
                customer.customer_id, int(res["new_vip"])
            )
        return res

    def lookup_payments(self, query):
        """Tra cứu thanh toán đa năng theo Mã GD (TT...), Mã đơn (BK...), Mã KH/CCCD/SĐT hoặc Mã phòng."""
        raw = (query or "").strip()
        if not raw:
            raise NotFoundError("Từ khóa tra cứu thanh toán không được để trống")
        upper = raw.upper()

        # 1. Tra cứu O(1) theo mã giao dịch TT...
        tx = self._by_payment_id.get(upper)
        if tx is not None:
            return [tx]

        # 2. Tra cứu O(1) theo mã đơn đặt phòng BK...
        by_booking = self.get_payments_by_booking(upper)
        if by_booking:
            return by_booking

        # 3. Tra cứu O(1) theo khách hàng (Mã KH / CCCD / SĐT)
        try:
            customer = self._customer_service.lookup(raw)
            by_cust = self._by_customer_id.get(customer.customer_id)
            if by_cust is not None and len(by_cust) > 0:
                return by_cust.to_list()
        except NotFoundError:
            pass

        # 4. Tra cứu theo mã phòng hoặc tên khách hàng
        matched = []
        raw_lower = raw.lower()
        for item in self._transactions:
            if item.room_id.upper() == upper:
                matched.append(item)
                continue
            try:
                cust_name = self._customer_service.get_customer(item.customer_id).full_name.lower()
                if raw_lower in cust_name:
                    matched.append(item)
            except NotFoundError:
                pass

        if not matched:
            raise NotFoundError(f"Không tìm thấy giao dịch thanh toán nào khớp với '{query}'")
        return matched

    def filter_transactions(
        self,
        payment_method=None,
        status=None,
        start_date=None,
        end_date=None,
    ):
        """Lọc danh sách giao dịch theo phương thức, trạng thái và khoảng ngày thanh toán."""
        if start_date is not None and end_date is not None and start_date > end_date:
            raise HotelError("Ngày bắt đầu lọc không được lớn hơn ngày kết thúc")
        method_filter = _parse_payment_method(payment_method) if payment_method is not None else None
        status_filter = _parse_payment_status(status) if status is not None else None
        result = []
        for tx in self._transactions:
            if method_filter is not None and tx.payment_method != method_filter:
                continue
            if status_filter is not None and tx.status != status_filter:
                continue
            if start_date is not None and tx.paid_at < start_date:
                continue
            if end_date is not None and tx.paid_at > end_date:
                continue
            result.append(tx)
        return result

    def sort_transactions(self, transactions=None, by="paid_at", reverse=False):
        """Sắp xếp danh sách giao dịch bằng Merge Sort O(p log p)."""
        items = list(transactions) if transactions is not None else self.all_transactions()
        field_key = (by or "paid_at").strip().lower()
        key_map = {
            "paid_at": lambda tx: (tx.paid_at, tx.payment_id),
            "date": lambda tx: (tx.paid_at, tx.payment_id),
            "total_amount": lambda tx: (tx.total_amount, tx.payment_id),
            "amount": lambda tx: (tx.total_amount, tx.payment_id),
            "payment_id": lambda tx: tx.payment_id,
            "id": lambda tx: tx.payment_id,
            "booking_id": lambda tx: (tx.booking_id, tx.payment_id),
        }
        if field_key not in key_map:
            raise HotelError(
                f"Tiêu chí sắp xếp giao dịch '{by}' không hợp lệ "
                f"(chọn paid_at, total_amount, payment_id hoặc booking_id)"
            )
        return merge_sort(items, key=key_map[field_key], reverse=reverse)

    def all_transactions(self):
        """Toàn bộ giao dịch lưu trong SinglyLinkedList (mới nhất -> cũ nhất)."""
        return self._transactions.to_list()

    def payment_summary(self):
        """Thống kê tổng hợp tình hình thanh toán và công nợ."""
        by_method = {m: 0 for m in PaymentMethod}
        count_by_method = {m: 0 for m in PaymentMethod}
        total_collected = 0
        total_refunded = 0
        total_discount = 0
        total_service_fee = 0
        paid_count = 0
        refunded_count = 0

        for tx in self._transactions:
            if tx.status == PaymentStatus.PAID:
                paid_count += 1
                total_collected += tx.total_amount
                total_discount += tx.discount_amount
                total_service_fee += tx.service_cost + tx.extra_fee
                by_method[tx.payment_method] += tx.total_amount
                count_by_method[tx.payment_method] += 1
            elif tx.status == PaymentStatus.REFUNDED:
                refunded_count += 1
                total_refunded += tx.total_amount

        unpaid_bookings = []
        unpaid_estimated_total = 0
        for booking in self._booking_service.all_bookings():
            if booking.status == BookingStatus.CANCELLED:
                continue
            bill = self.calculate_total_cost(booking.booking_id)
            if bill["remaining_amount"] > 0:
                unpaid_bookings.append(booking)
                unpaid_estimated_total += bill["remaining_amount"]

        return {
            "total_transactions": len(self._transactions),
            "paid_transactions": paid_count,
            "refunded_transactions": refunded_count,
            "total_collected": total_collected,
            "total_refunded": total_refunded,
            "total_discount": total_discount,
            "total_service_fee": total_service_fee,
            "revenue_by_method": by_method,
            "count_by_method": count_by_method,
            "unpaid_bookings_count": len(unpaid_bookings),
            "unpaid_estimated_total": unpaid_estimated_total,
        }

    # -------------------- 4. Khôi phục từ JSON Persistence --------------- #
    def load_payments(self, payment_dicts, sequence_value):
        """Khôi phục các bảng băm và danh sách liên kết giao dịch khi đọc file JSON."""
        self._by_payment_id = HashTable()
        self._by_booking_id = HashTable()
        self._by_customer_id = HashTable()
        self._transactions = SinglyLinkedList()
        self._id_gen.restore(sequence_value)

        # payment_dicts được lưu từ mới nhất -> cũ nhất; nạp ngược để giữ đúng thứ tự push_front
        touched_customers = set()
        for item in reversed(payment_dicts):
            tx = PaymentTransaction.from_dict(item)
            self._store_transaction(tx)
            touched_customers.add(tx.customer_id)
            if tx.payment_id.startswith("TT") and tx.payment_id[2:].isdigit():
                self._id_gen.restore(int(tx.payment_id[2:]))

        for cust in self._customer_service.all_customers():
            try:
                self.sync_customer_vip(cust.customer_id, allow_downgrade=False)
            except NotFoundError:
                pass
        for cid in touched_customers:
            try:
                self.sync_customer_vip(cid, allow_downgrade=False)
            except NotFoundError:
                pass

    def __len__(self):
        return len(self._transactions)


# ============================================================================
# MODULE: hotel/services/report_service.py
# ============================================================================
"""Chức năng mở rộng: Thống kê doanh thu, tỷ lệ lấp đầy và top khách hàng."""




class ReportService:
    def __init__(self, room_service, customer_service, booking_service, payment_service=None):
        self._room_service = room_service
        self._customer_service = customer_service
        self._booking_service = booking_service
        self._payment_service = payment_service

    def revenue_summary(self):
        """Thống kê doanh thu tổng, theo loại phòng và theo tháng (YYYY-MM).

        Chỉ tính các đơn không bị hủy (CONFIRMED, CHECKED_IN, CHECKED_OUT).
        """
        by_type = {rtype: 0 for rtype in RoomType}
        nights_by_type = {rtype: 0 for rtype in RoomType}
        by_month = {}
        realized_revenue = 0      # Đã nhận/trả phòng (CHECKED_IN + CHECKED_OUT)
        confirmed_revenue = 0     # Đã xác nhận (CONFIRMED)
        active_count = 0
        cancelled_count = 0

        for booking in self._booking_service.all_bookings():
            if booking.status == BookingStatus.CANCELLED:
                cancelled_count += 1
                continue
            active_count += 1
            amount = booking.total_price
            if booking.status in (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT):
                realized_revenue += amount
            else:
                confirmed_revenue += amount

            room = self._room_service.get_room(booking.room_id)
            by_type[room.room_type] += amount
            nights_by_type[room.room_type] += booking.num_nights

            month_key = booking.check_in.strftime("%Y-%m")
            by_month[month_key] = by_month.get(month_key, 0) + amount

        sorted_months = merge_sort(list(by_month.items()), key=lambda kv: kv[0])
        return {
            "total_revenue": realized_revenue + confirmed_revenue,
            "realized_revenue": realized_revenue,
            "confirmed_revenue": confirmed_revenue,
            "active_bookings": active_count,
            "cancelled_bookings": cancelled_count,
            "revenue_by_type": by_type,
            "nights_by_type": nights_by_type,
            "revenue_by_month": sorted_months,
        }

    def occupancy_on(self, target_date=None):
        """Tỷ lệ lấp đầy phòng tại một ngày cụ thể."""
        on_date = target_date or date.today()
        rooms = self._room_service.all_rooms()
        total = len(rooms)
        booked = 0
        maintenance = 0
        empty = 0

        for room in rooms:
            status = self._booking_service.room_status_on(room.room_id, on_date)
            if status == RoomStatus.BOOKED:
                booked += 1
            elif status == RoomStatus.MAINTENANCE:
                maintenance += 1
            else:
                empty += 1

        bookable = max(1, total - maintenance)
        return {
            "date": on_date,
            "total_rooms": total,
            "booked_rooms": booked,
            "empty_rooms": empty,
            "maintenance_rooms": maintenance,
            "occupancy_rate": round((booked / total) * 100.0, 2) if total else 0.0,
            "effective_occupancy_rate": round((booked / bookable) * 100.0, 2),
        }

    def top_customers(self, limit=5):
        """Top khách hàng theo tổng chi tiêu và số đêm lưu trú (sắp bằng Merge Sort)."""
        stats = []
        for customer in self._customer_service.all_customers():
            history = customer.history.to_list()
            active = [b for b in history if b.status != BookingStatus.CANCELLED]
            total_spent = sum(b.total_price for b in active)
            total_nights = sum(b.num_nights for b in active)
            if self._payment_service is not None:
                try:
                    self._payment_service.sync_customer_vip(customer.customer_id, allow_downgrade=False)
                except Exception:
                    pass
                total_paid = self._payment_service.get_customer_total_paid(customer.customer_id)
            else:
                try:
                    self._customer_service.evaluate_and_update_vip(
                        customer.customer_id, total_spent, allow_downgrade=False
                    )
                except Exception:
                    pass
                total_paid = total_spent
            stats.append(
                {
                    "customer": customer,
                    "booking_count": len(active),
                    "total_nights": total_nights,
                    "total_spent": total_spent,
                    "total_paid": total_paid,
                }
            )
        ranked = merge_sort(
            stats,
            key=lambda item: (item["total_spent"], item["total_nights"], item["booking_count"]),
            reverse=True,
        )
        return ranked[: max(0, limit)]


# ============================================================================
# MODULE: hotel/services/storage_service.py
# ============================================================================
"""Chức năng lưu trữ bền vững: Đọc/ghi toàn bộ trạng thái hệ thống ra file JSON.

Khi nạp lại từ file JSON, các cấu trúc dữ liệu nền tảng (Matrix2D, AVLTree/BST,
HashTable, SinglyLinkedList, MaxHeap, LinkedQueue, Stack) đều được tái lập đầy đủ.
"""




class StorageService:
    def __init__(self, data_file):
        self._data_file = Path(data_file)

    @property
    def data_file(self):
        return self._data_file

    def exists(self):
        return self._data_file.is_file()

    def save(
        self,
        room_service,
        customer_service,
        booking_service,
        waiting_service,
        undo_service,
        service_request_service,
        payment_service=None,
    ):
        """Lưu toàn bộ trạng thái hiện tại ra file JSON."""
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "floors": room_service.floors,
                "rooms_per_floor": room_service.rooms_per_floor,
                "customer_seq": customer_service.id_generator.current,
                "booking_seq": booking_service.id_generator.current,
                "waiting_id_seq": waiting_service.id_generator.current,
                "waiting_order_seq": waiting_service.sequence_generator.current,
                "service_id_seq": service_request_service.id_generator.current,
                "service_order_seq": service_request_service.sequence_generator.current,
                "payment_seq": payment_service.id_generator.current if payment_service is not None else 0,
            },
            "rooms": [room.to_dict() for room in room_service.all_rooms()],
            "bookings": [booking.to_dict() for booking in booking_service.all_bookings()],
            "customers": [customer.to_dict() for customer in customer_service.all_customers()],
            "waiting_entries": [entry.to_dict() for entry in waiting_service.list_waiting_ordered()],
            "undo_stack": [action.to_dict() for action in undo_service.history()],
            "service_requests": {
                "pending": [req.to_dict() for req in service_request_service.pending_requests_ordered()],
                "completed": [req.to_dict() for req in service_request_service.completed_requests()],
            },
            "payments": (
                [tx.to_dict() for tx in payment_service.all_transactions()]
                if payment_service is not None
                else []
            ),
        }
        temp_file = self._data_file.with_suffix(".tmp")
        temp_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_file.replace(self._data_file)

    def load(
        self,
        room_service,
        customer_service,
        booking_service,
        waiting_service,
        undo_service,
        service_request_service,
        payment_service=None,
    ):
        """Nạp dữ liệu từ file JSON và khôi phục toàn bộ các cấu trúc dữ liệu."""
        if not self.exists():
            return False

        try:
            raw = json.loads(self._data_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Nội dung JSON gốc phải là một đối tượng (dict)")
            meta = raw.get("meta", {})
            if not isinstance(meta, dict):
                raise ValueError("Trường 'meta' trong file JSON không hợp lệ")

            floors = int(meta.get("floors", room_service.floors))
            rooms_per_floor = int(meta.get("rooms_per_floor", room_service.rooms_per_floor))
            rooms = [Room.from_dict(item) for item in raw.get("rooms", [])]
            room_service.load_rooms(floors, rooms_per_floor, rooms)

            booking_service.load_bookings(
                raw.get("bookings", []),
                meta.get("booking_seq", 0),
            )

            customer_service.load_customers(
                raw.get("customers", []),
                meta.get("customer_seq", 0),
                booking_service.bookings_by_id_map(),
            )

            waiting_service.load_waiting_entries(
                raw.get("waiting_entries", []),
                meta.get("waiting_id_seq", 0),
                meta.get("waiting_order_seq", 0),
            )

            undo_service.load_actions(raw.get("undo_stack", []))

            sr_data = raw.get("service_requests", {})
            if not isinstance(sr_data, dict):
                raise ValueError("Trường 'service_requests' trong file JSON không hợp lệ")
            service_request_service.load_requests(
                sr_data.get("pending", []),
                sr_data.get("completed", []),
                meta.get("service_id_seq", 0),
                meta.get("service_order_seq", 0),
            )

            if payment_service is not None:
                payments_data = raw.get("payments", [])
                if not isinstance(payments_data, list):
                    raise ValueError("Trường 'payments' trong file JSON không hợp lệ")
                payment_service.load_payments(
                    payments_data,
                    meta.get("payment_seq", 0),
                )
        except HotelError:
            raise
        except (json.JSONDecodeError, KeyError, ValueError, TypeError, OSError) as exc:
            raise HotelError(
                f"Không thể nạp file dữ liệu '{self._data_file}': dữ liệu bị hỏng hoặc sai định dạng ({exc})"
            ) from exc
        return True


# ============================================================================
# MODULE: hotel/services/seed_service.py
# ============================================================================
"""Khởi tạo bộ dữ liệu mẫu tiếng Việt phong phú để minh họa ngay các cấu trúc dữ liệu."""




def seed_sample_data(manager, reference_date=None):
    """Tạo dữ liệu mẫu cho khách sạn (khách hàng, đặt phòng, hàng chờ, undo, dịch vụ)."""
    today = reference_date or date.today()

    # 1. Đặt 1 phòng ở trạng thái bảo trì để minh họa sơ đồ tầng
    manager.set_room_maintenance("P104", True)

    # 2. Đăng ký khách hàng mẫu (từ Thường đến Platinum VIP)
    c1 = manager.register_customer("Nguyễn Văn An", "001200012345", "0901234567", VipLevel.NORMAL)
    c2 = manager.register_customer("Trần Thị Bích", "001200023456", "0912345678", VipLevel.SILVER)
    c3 = manager.register_customer("Lê Hoàng Nam", "001200034567", "0923456789", VipLevel.GOLD)
    c4 = manager.register_customer("Phạm Minh Châu", "001200045678", "0934567890", VipLevel.PLATINUM)
    c5 = manager.register_customer("Hoàng Đức Thịnh", "001200056789", "0945678901", VipLevel.NORMAL)
    c6 = manager.register_customer("Vũ Ngọc Mai", "001200067890", "0956789012", VipLevel.GOLD)

    # 3. Tạo các đơn đặt phòng (bao gồm đã trả, đang ở, sắp nhận)
    b_past = manager.book_room(
        c4.customer_id,
        "P509",
        today - timedelta(days=5),
        today - timedelta(days=2),
    )
    manager.check_in(b_past.booking_id)
    manager.check_out(b_past.booking_id)

    b_stay1 = manager.book_room(
        c1.customer_id,
        "P101",
        today - timedelta(days=1),
        today + timedelta(days=2),
    )
    manager.check_in(b_stay1.booking_id)

    b_stay2 = manager.book_room(
        c3.customer_id,
        "P205",
        today,
        today + timedelta(days=3),
    )
    manager.check_in(b_stay2.booking_id)

    manager.book_room(
        c2.customer_id,
        "P306",
        today + timedelta(days=1),
        today + timedelta(days=4),
    )
    manager.book_room(
        c4.customer_id,
        "P410",
        today,
        today + timedelta(days=4),
    )

    # Tạo 1 đơn rồi hủy để có sẵn phần tử trong Undo Stack minh họa hoàn tác
    b_cancel = manager.book_room(
        c5.customer_id,
        "P102",
        today + timedelta(days=2),
        today + timedelta(days=5),
    )
    manager.cancel_booking(b_cancel.booking_id, cancelled_by="STAFF", auto_fulfill=False)

    # 4. Thêm khách vào danh sách chờ (khách thường + khách VIP để minh họa Max-Heap vs Queue)
    manager.add_to_waiting_list(
        c5.customer_id,
        RoomType.SUITE,
        today + timedelta(days=1),
        today + timedelta(days=3),
    )
    manager.add_to_waiting_list(
        c2.customer_id,
        RoomType.SUITE,
        today + timedelta(days=1),
        today + timedelta(days=3),
    )
    manager.add_to_waiting_list(
        c6.customer_id,
        RoomType.SUITE,
        today + timedelta(days=1),
        today + timedelta(days=3),
    )

    # 5. Gửi các yêu cầu dịch vụ nội bộ với độ khẩn khác nhau (LOW, NORMAL, EMERGENCY)
    manager.submit_service_request(
        room_id="P101",
        service_type=ServiceType.CLEANING,
        urgency=UrgencyLevel.LOW,
        note="Thay khăn tắm và dọn phòng buổi sáng",
        customer_id=c1.customer_id,
    )
    manager.submit_service_request(
        room_id="P205",
        service_type=ServiceType.FOOD,
        urgency=UrgencyLevel.NORMAL,
        note="2 suất phở bò + 2 nước cam lên phòng",
        customer_id=c3.customer_id,
    )
    manager.submit_service_request(
        room_id="P410",
        service_type=ServiceType.MEDICAL,
        urgency=UrgencyLevel.EMERGENCY,
        note="Khách bị sốt cao, cần hỗ trợ y tế ngay",
        customer_id=c4.customer_id,
    )

    # 6. Tạo các giao dịch thanh toán mẫu (minh họa Quản lý thanh toán: HashTable + SinglyLinkedList)
    manager.process_payment(
        booking_id=b_past.booking_id,
        payment_method=PaymentMethod.CARD,
        extra_fee=0,
        note="Thanh toán khi trả phòng P509 (giảm 10% hạng Platinum)",
        paid_at=today - timedelta(days=2),
    )
    manager.process_payment(
        booking_id=b_stay1.booking_id,
        payment_method=PaymentMethod.BANK_TRANSFER,
        extra_fee=0,
        note="Thanh toán trước tiền phòng P101 và phí dọn phòng",
        paid_at=today,
    )


# ============================================================================
# MODULE: hotel/services/hotel_manager.py
# ============================================================================
"""Lớp điều phối nghiệp vụ trung tâm (HotelManager — Facade Pattern).

Kết nối toàn bộ các dịch vụ chuyên biệt của Tầng Nghiệp vụ:
- RoomService           (Mảng 2D, Merge Sort, Quick Sort, Binary Search)
- CustomerService       (Bảng băm Chaining, Danh sách liên kết đơn)
- BookingService        (Cây nhị phân tìm kiếm cân bằng AVL / IntervalSchedule)
- WaitingService        (Hàng đợi ưu tiên Max-Heap cho VIP + Queue FIFO cho khách thường)
- UndoService           (Ngăn xếp LIFO cho hoàn tác hủy phòng)
- ServiceRequestService (Hàng đợi ưu tiên Max-Heap cho yêu cầu dịch vụ nội bộ)
- PaymentService        (Bảng băm Chaining + Danh sách liên kết đơn cho quản lý thanh toán)
- ReportService         (Thống kê doanh thu, tỷ lệ lấp đầy, top khách hàng)
- StorageService        (Lưu trữ & khôi phục dữ liệu JSON)
"""




class HotelManager:
    def __init__(
        self,
        floors=DEFAULT_FLOORS,
        rooms_per_floor=DEFAULT_ROOMS_PER_FLOOR,
        data_file=DEFAULT_DATA_FILE,
        auto_save=True,
        seed_if_empty=False,
        load_existing=True,
    ):
        self.rooms = RoomService(floors=floors, rooms_per_floor=rooms_per_floor)
        self.customers = CustomerService()
        self.bookings = BookingService(self.rooms, self.customers)
        self.waiting = WaitingService(self.customers)
        self.undo = UndoService(self.bookings)
        self.service_requests = ServiceRequestService(self.rooms, self.customers)
        self.payments = PaymentService(
            self.rooms,
            self.customers,
            self.bookings,
            self.service_requests,
            self.waiting,
        )
        self.reports = ReportService(self.rooms, self.customers, self.bookings, self.payments)

        self._storage = StorageService(data_file) if data_file is not None else None
        self._auto_save = bool(auto_save and self._storage is not None)

        if load_existing and self._storage is not None and self._storage.exists():
            self.load()
        elif seed_if_empty:
            self.reset_with_sample_data()

    # ---------------------- Lưu trữ & Khởi tạo mẫu ---------------------- #
    def save(self):
        if self._storage is not None:
            self._storage.save(
                self.rooms,
                self.customers,
                self.bookings,
                self.waiting,
                self.undo,
                self.service_requests,
                self.payments,
            )

    def _maybe_save(self):
        if self._auto_save:
            self.save()

    def load(self):
        if self._storage is None:
            return False
        loaded = self._storage.load(
            self.rooms,
            self.customers,
            self.bookings,
            self.waiting,
            self.undo,
            self.service_requests,
            self.payments,
        )
        if loaded:
            any_changed = False
            for cust in self.customers.all_customers():
                try:
                    res = self.payments.sync_customer_vip(cust.customer_id, allow_downgrade=False)
                    if res.get("changed"):
                        any_changed = True
                except Exception:
                    pass
            if any_changed:
                self._maybe_save()
        return loaded

    def reset_with_sample_data(self, reference_date=None):
        """Xóa dữ liệu cũ và nạp lại bộ dữ liệu mẫu chuẩn."""
        floors, per_floor = self.rooms.floors, self.rooms.rooms_per_floor
        self.rooms = RoomService(floors=floors, rooms_per_floor=per_floor)
        self.customers = CustomerService()
        self.bookings = BookingService(self.rooms, self.customers)
        self.waiting = WaitingService(self.customers)
        self.undo = UndoService(self.bookings)
        self.service_requests = ServiceRequestService(self.rooms, self.customers)
        self.payments = PaymentService(
            self.rooms,
            self.customers,
            self.bookings,
            self.service_requests,
            self.waiting,
        )
        self.reports = ReportService(self.rooms, self.customers, self.bookings, self.payments)

        prev_auto = self._auto_save
        self._auto_save = False
        try:
            seed_sample_data(self, reference_date=reference_date)
        finally:
            self._auto_save = prev_auto
        self._maybe_save()

    # ------------------- 1. Phòng & Sơ đồ tầng (Matrix2D) --------------- #
    def get_room(self, room_id):
        return self.rooms.get_room(room_id)

    def get_room_by_coords(self, floor, room_number):
        return self.rooms.get_room_by_coords(floor, room_number)

    def floor_map(self, on_date=None):
        """Trả về sơ đồ ma trận toàn khách sạn tại ngày `on_date`.

        Mỗi phần tử là dict `{"room": Room, "status": RoomStatus, "booking": Booking|None}`.
        """
        target = on_date or date.today()
        grid = []
        for floor in range(1, self.rooms.floors + 1):
            row_items = []
            for room in self.rooms.floor_rooms(floor):
                status = self.bookings.room_status_on(room.room_id, target)
                booking = self.bookings.active_booking_on(room.room_id, target)
                row_items.append({"room": room, "status": status, "booking": booking})
            grid.append(row_items)
        return grid

    def set_room_maintenance(self, room_id, under_maintenance):
        room = self.rooms.set_maintenance(room_id, under_maintenance)
        self._maybe_save()
        return room

    # ----------- 2 & 3. Tìm kiếm, Lọc & Sắp xếp phòng ------------------- #
    def find_available_rooms(
        self,
        check_in,
        check_out,
        room_type=None,
        min_price=0,
        max_price=float("inf"),
        sort_by="price",
        reverse=False,
        algorithm="merge",
    ):
        available = self.bookings.find_available_rooms(
            check_in=check_in,
            check_out=check_out,
            room_type=room_type,
            min_price=min_price,
            max_price=max_price,
        )
        return self.rooms.sort_rooms(available, by=sort_by, reverse=reverse, algorithm=algorithm)

    def sort_rooms(self, rooms=None, by="price", reverse=False, algorithm="merge"):
        return self.rooms.sort_rooms(rooms=rooms, by=by, reverse=reverse, algorithm=algorithm)

    def filter_rooms_by_price(self, min_price=0, max_price=float("inf"), room_type=None):
        return self.rooms.filter_by_price_range(min_price, max_price, room_type=room_type)

    def suggest_room_by_budget(self, budget, room_type=None, check_in=None, check_out=None):
        """Gợi ý phòng có giá gần ngân sách nhất (kết hợp lọc trống nếu có khoảng ngày)."""
        candidates = None
        if check_in is not None and check_out is not None:
            candidates = self.bookings.find_available_rooms(
                check_in=check_in,
                check_out=check_out,
                room_type=room_type,
            )
        return self.rooms.find_closest_to_budget(
            budget=budget,
            room_type=room_type,
            candidates=candidates,
        )

    # ---------------- 4. Khách hàng & Lịch sử (HashTable + LL) ---------- #
    def register_customer(self, full_name, cccd, phone, vip_level=0):
        customer = self.customers.register_customer(full_name, cccd, phone, vip_level)
        self._maybe_save()
        return customer

    def lookup_customer(self, identifier):
        return self.customers.lookup(identifier)

    def set_customer_vip(self, customer_id, vip_level):
        customer = self.customers.set_vip_level(customer_id, vip_level)
        self.waiting.update_customer_priority(customer.customer_id, int(customer.vip_level))
        self._maybe_save()
        return customer

    def customer_stay_history(self, customer_id):
        return self.customers.get_stay_history(customer_id)

    def customer_total_paid(self, customer_identifier):
        return self.payments.get_customer_total_paid(customer_identifier)

    def customer_vip_progress(self, customer_identifier):
        return self.payments.get_customer_vip_progress(customer_identifier)

    def sync_customer_vip(self, customer_identifier, allow_downgrade=False):
        res = self.payments.sync_customer_vip(
            customer_identifier, allow_downgrade=allow_downgrade
        )
        if res["changed"]:
            self._maybe_save()
        return res

    # ---------------- 5. Đặt phòng / Nhận / Trả (BST/AVL) --------------- #
    def book_room(self, customer_id, room_id, check_in, check_out, created_at=None):
        booking = self.bookings.create_booking(
            customer_id=customer_id,
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            created_at=created_at,
        )
        try:
            self.payments.sync_customer_vip(booking.customer_id, allow_downgrade=False)
        except Exception:
            pass
        self._maybe_save()
        return booking

    def book_by_type_or_wait(self, customer_id, room_type, check_in, check_out):
        """Đặt phòng theo loại; nếu hết phòng trống thì tự động xếp vào hàng chờ.

        Trả về tuple `("BOOKED", Booking)` hoặc `("WAITING", WaitingEntry)`.
        """
        available = self.bookings.find_available_rooms(
            check_in=check_in,
            check_out=check_out,
            room_type=room_type,
        )
        if available:
            booking = self.book_room(customer_id, available[0].room_id, check_in, check_out)
            return "BOOKED", booking
        entry = self.add_to_waiting_list(customer_id, room_type, check_in, check_out)
        return "WAITING", entry

    def check_in(self, booking_id):
        booking = self.bookings.check_in(booking_id)
        self._maybe_save()
        return booking

    def check_out(self, booking_id, auto_fulfill=False):
        booking = self.bookings.check_out(booking_id)
        if auto_fulfill:
            room = self.rooms.get_room(booking.room_id)
            fulfilled = self.waiting.try_fulfill_waiting_list(
                self.bookings, room_type_filter=room.room_type
            )
            for _entry, new_bk in fulfilled:
                try:
                    self.payments.sync_customer_vip(new_bk.customer_id, allow_downgrade=False)
                except Exception:
                    pass
        self._maybe_save()
        return booking

    # ---------------- 6. Hủy đặt phòng & Hoàn tác (Stack) --------------- #
    def cancel_booking(self, booking_id, cancelled_by="STAFF", auto_fulfill=False):
        booking_obj = self.bookings.get_booking(booking_id)
        cancelled_cid = booking_obj.customer_id
        action = self.undo.cancel_booking(booking_id, cancelled_by=cancelled_by)
        active_txs = self.payments.get_active_payments_for_booking(action.booking_id)
        if active_txs:
            action.booking_snapshot["refunded_payment_ids"] = [tx.payment_id for tx in active_txs]
            action.booking_snapshot["previous_payment_notes"] = {
                tx.payment_id: tx.note for tx in active_txs
            }
            for tx in active_txs:
                self.payments.refund_payment(tx.payment_id, reason="Tự động hoàn tiền khi hủy đơn")
        try:
            self.payments.sync_customer_vip(cancelled_cid, allow_downgrade=False)
        except Exception:
            pass
        fulfilled = []
        if auto_fulfill:
            room = self.rooms.get_room(action.room_id)
            fulfilled = self.waiting.try_fulfill_waiting_list(
                self.bookings, room_type_filter=room.room_type
            )
            for _entry, new_bk in fulfilled:
                try:
                    self.payments.sync_customer_vip(new_bk.customer_id, allow_downgrade=False)
                except Exception:
                    pass
        self._maybe_save()
        return action, fulfilled

    def undo_last_cancellation(self):
        action, booking = self.undo.undo_last_cancellation()
        refunded_ids = action.booking_snapshot.get("refunded_payment_ids", [])
        prev_notes = action.booking_snapshot.get("previous_payment_notes", {})
        for pid in refunded_ids:
            try:
                tx = self.payments.get_payment(pid)
                if tx.status == PaymentStatus.REFUNDED:
                    tx.status = PaymentStatus.PAID
                    if pid in prev_notes:
                        tx.note = prev_notes[pid]
            except Exception:
                pass
        try:
            self.payments.sync_customer_vip(booking.customer_id, allow_downgrade=False)
        except Exception:
            pass
        self._maybe_save()
        return action, booking

    # ---------------- 7. Danh sách chờ (Queue + Max-Heap) --------------- #
    def add_to_waiting_list(self, customer_id, room_type, check_in, check_out):
        entry = self.waiting.enqueue(customer_id, room_type, check_in, check_out)
        self._maybe_save()
        return entry

    def process_waiting_list(self, room_type=None):
        fulfilled = self.waiting.try_fulfill_waiting_list(
            self.bookings, room_type_filter=room_type
        )
        if fulfilled:
            for _entry, new_bk in fulfilled:
                try:
                    self.payments.sync_customer_vip(new_bk.customer_id, allow_downgrade=False)
                except Exception:
                    pass
            self._maybe_save()
        return fulfilled

    def pop_next_waiting(self):
        entry = self.waiting.pop_next()
        self._maybe_save()
        return entry

    # ---------------- 8. Yêu cầu dịch vụ nội bộ (Max-Heap) -------------- #
    def submit_service_request(
        self,
        room_id,
        service_type,
        urgency=None,
        note="",
        customer_id="",
        requested_at=None,
    ):
        resolved_cid = (customer_id or "").strip()
        if not resolved_cid:
            target_date = requested_at or date.today()
            room_key = (room_id or "").strip().upper()
            checked_in_bookings = [
                b
                for b in self.bookings.all_bookings()
                if b.room_id == room_key
                and b.status == BookingStatus.CHECKED_IN
                and b.check_in <= target_date <= b.check_out
            ]
            if checked_in_bookings:
                resolved_cid = checked_in_bookings[0].customer_id
            else:
                try:
                    active_bk = self.bookings.active_booking_on(room_id, target_date)
                    if active_bk is not None:
                        resolved_cid = active_bk.customer_id
                except Exception:
                    pass

        req = self.service_requests.submit_request(
            room_id=room_id,
            service_type=service_type,
            urgency=urgency,
            note=note,
            customer_id=resolved_cid,
            requested_at=requested_at,
        )
        self._maybe_save()
        return req

    def process_next_service_request(self):
        req = self.service_requests.process_next()
        self._maybe_save()
        return req

    # ---------------- 9. Quản lý thanh toán (HashTable + LL) ------------ #
    def calculate_booking_cost(self, booking_id, extra_fee=0):
        """Tính tổng chi phí chi tiết (tiền phòng + dịch vụ + phụ phí - chiết khấu VIP)."""
        return self.payments.calculate_total_cost(booking_id, extra_fee=extra_fee)

    def process_payment(
        self,
        booking_id,
        payment_method=PaymentMethod.CASH,
        extra_fee=0,
        note="",
        paid_at=None,
        auto_check_out=False,
    ):
        """Xử lý thanh toán cho đơn đặt phòng, lưu giao dịch và tùy chọn trả phòng luôn."""
        tx = self.payments.process_payment(
            booking_id=booking_id,
            payment_method=payment_method,
            extra_fee=extra_fee,
            note=note,
            paid_at=paid_at,
        )
        if auto_check_out:
            booking = self.bookings.get_booking(booking_id)
            if booking.status == BookingStatus.CHECKED_IN:
                self.bookings.check_out(booking.booking_id)
        self._maybe_save()
        return tx

    def refund_payment(self, identifier, reason=""):
        """Hoàn tiền cho một giao dịch thanh toán (theo mã TT... hoặc mã đơn BK...)."""
        tx = self.payments.refund_payment(identifier, reason=reason)
        self._maybe_save()
        return tx

    def get_payment(self, payment_id):
        """Tra cứu trực tiếp giao dịch theo mã TT... — O(1) trung bình."""
        return self.payments.get_payment(payment_id)

    def lookup_payments(self, query):
        """Tra cứu giao dịch theo Mã GD (TT...), Mã đơn (BK...), Mã KH/CCCD/SĐT hoặc Mã phòng."""
        return self.payments.lookup_payments(query)

    def payments_for_booking(self, booking_id):
        return self.payments.get_payments_by_booking(booking_id)

    def payments_for_customer(self, customer_identifier):
        return self.payments.get_payments_by_customer(customer_identifier)

    def filter_payments(
        self,
        payment_method=None,
        status=None,
        start_date=None,
        end_date=None,
    ):
        return self.payments.filter_transactions(
            payment_method=payment_method,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

    def sort_payments(self, payments=None, by="paid_at", reverse=False):
        return self.payments.sort_transactions(transactions=payments, by=by, reverse=reverse)

    def all_payments(self):
        return self.payments.all_transactions()


# ============================================================================
# MODULE: hotel/ui/formatter.py
# ============================================================================
"""Định dạng bảng biểu, tiền tệ VND và sơ đồ ma trận phòng trực quan."""




def format_vnd(amount):
    """Định dạng số tiền sang chuỗi VND, ví dụ 1500000 -> '1.500.000 đ'."""
    return f"{int(amount):,}".replace(",", ".") + " đ"


def render_table(headers, rows):
    """Vẽ bảng ASCII căn lề tự động từ danh sách tiêu đề và các dòng."""
    str_headers = [str(h) for h in headers]
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(h) for h in str_headers]
    for row in str_rows:
        for idx, cell in enumerate(row):
            if idx < len(widths):
                widths[idx] = max(widths[idx], len(cell))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(str_headers)) + " |"
    lines = [sep, header_line, sep]
    if not str_rows:
        empty_msg = "(Không có dữ liệu)"
        total_inner = sum(widths) + 3 * (len(widths) - 1)
        lines.append("| " + empty_msg.center(total_inner) + " |")
    else:
        for row in str_rows:
            lines.append(
                "| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(widths))) + " |"
            )
    lines.append(sep)
    return "\n".join(lines)


def render_floor_matrix(floor_grid, on_date=None):
    """Vẽ sơ đồ ma trận phòng theo tầng (tầng cao ở trên hoặc tầng 1..N rõ ràng).

    Ký hiệu trạng thái:
        [ ] TRỐNG       [X] ĐÃ ĐẶT       [!] BẢO TRÌ
    Ký hiệu loại phòng:
        S = Đơn (Single), D = Đôi (Double), U = Suite
    """
    target = on_date or date.today()
    type_code = {"SINGLE": "Đơn", "DOUBLE": "Đôi", "SUITE": "Suite"}
    status_mark = {
        RoomStatus.EMPTY: "TRỐNG ",
        RoomStatus.BOOKED: "ĐÃ ĐẶT",
        RoomStatus.MAINTENANCE: "BẢO TRÌ",
    }

    lines = [
        f"=== SƠ ĐỒ MA TRẬN PHÒNG KHÁCH SẠN (Ngày kiểm tra: {format_date(target)}) ===",
        "Chú thích: [Mã phòng | Loại | Trạng thái]",
        "-" * 88,
    ]
    for floor_index in range(len(floor_grid) - 1, -1, -1):
        row = floor_grid[floor_index]
        floor_no = floor_index + 1
        cells = []
        for cell in row:
            room = cell["room"]
            status = cell["status"]
            t_short = type_code[room.room_type.value]
            s_short = status_mark[status]
            cells.append(f"[{room.room_id}:{t_short}:{s_short}]")
        # Chia 5 phòng mỗi dòng để vừa khung màn hình console
        mid = len(cells) // 2 if len(cells) > 5 else len(cells)
        lines.append(f"Tầng {floor_no:02d} (01..{mid:02d}): " + " ".join(cells[:mid]))
        if mid < len(cells):
            lines.append(f"        ({mid + 1:02d}..{len(cells):02d}): " + " ".join(cells[mid:]))
        lines.append("-" * 88)
    return "\n".join(lines)


def format_rooms_table(rooms, manager=None, on_date=None):
    target = on_date or date.today()
    headers = ["Mã phòng", "Tầng", "Số", "Loại phòng", "Giá / đêm", "Trạng thái", "Mô tả tiện nghi"]
    rows = []
    for room in rooms:
        if manager is not None:
            status_label = manager.bookings.room_status_on(room.room_id, target).label
        else:
            status_label = "BẢO TRÌ" if room.under_maintenance else "TRỐNG"
        rows.append(
            [
                room.room_id,
                room.floor,
                f"{room.room_number:02d}",
                room.room_type.label,
                format_vnd(room.price_per_night),
                status_label,
                room.description,
            ]
        )
    return render_table(headers, rows)


def format_bookings_table(bookings, customer_service=None):
    headers = [
        "Mã đơn",
        "Mã KH",
        "Tên khách hàng",
        "Phòng",
        "Nhận phòng",
        "Trả phòng",
        "Số đêm",
        "Tổng tiền",
        "Trạng thái",
    ]
    rows = []
    for b in bookings:
        cname = ""
        if customer_service is not None:
            try:
                cname = customer_service.get_customer(b.customer_id).full_name
            except Exception:
                cname = "-"
        rows.append(
            [
                b.booking_id,
                b.customer_id,
                cname,
                b.room_id,
                format_date(b.check_in),
                format_date(b.check_out),
                b.num_nights,
                format_vnd(b.total_price),
                b.status.label,
            ]
        )
    return render_table(headers, rows)


def format_customers_table(customers, payment_service=None):
    if payment_service is None:
        headers = ["Mã KH", "Họ và tên", "Số CCCD", "Số điện thoại", "Hạng VIP", "Số lượt đặt"]
    else:
        headers = [
            "Mã KH",
            "Họ và tên",
            "Số CCCD",
            "Số điện thoại",
            "Hạng VIP",
            "Số đơn",
            "Tích lũy đã TT",
            "Tiến độ nâng VIP",
        ]
    rows = []
    for c in customers:
        base_row = [
            c.customer_id,
            c.full_name,
            c.cccd,
            c.phone,
            f"{c.vip_level.label} ({int(c.vip_level)})",
            len(c.history),
        ]
        if payment_service is not None:
            prog = payment_service.get_customer_vip_progress(c.customer_id)
            if prog["next_vip"] is not None:
                next_info = f"Còn {format_vnd(prog['amount_to_next_vip'])} -> {prog['next_vip'].label}"
            else:
                next_info = "Đạt đỉnh (Platinum)"
            base_row.extend([format_vnd(prog["total_paid"]), next_info])
        rows.append(base_row)
    return render_table(headers, rows)


def format_vip_policy_table():
    """Bảng quy định mốc tích lũy tự động nâng hạng VIP và quyền lợi chiết khấu."""
    headers = ["Hạng thành viên", "Mức ưu tiên", "Mốc tích lũy đã thanh toán", "Chiết khấu hóa đơn", "Quyền lợi hàng chờ"]
    rows = []
    for level in VipLevel:
        threshold = VIP_SPENDING_THRESHOLDS.get(level, 0)
        rate_pct = int(round(VIP_DISCOUNT_RATES.get(level, 0.0) * 100))
        thresh_str = "Mặc định (< 3.000.000 đ)" if level == VipLevel.NORMAL else f">= {format_vnd(threshold)}"
        queue_benefit = (
            "LinkedQueue (FIFO thường)"
            if level == VipLevel.NORMAL
            else f"Max-Heap VIP (Ưu tiên mức {int(level)})"
        )
        rows.append([level.label, int(level), thresh_str, f"Giảm {rate_pct}%", queue_benefit])
    return render_table(headers, rows)


def format_waiting_table(entries, customer_service=None):
    headers = [
        "Thứ tự",
        "Mã chờ",
        "Mã KH",
        "Tên khách",
        "Hạng ưu tiên",
        "Loại phòng",
        "Nhận phòng",
        "Trả phòng",
        "Cấu trúc lưu",
    ]
    rows = []
    for idx, e in enumerate(entries, start=1):
        cname = ""
        vip_label = f"Mức {e.priority}"
        if customer_service is not None:
            try:
                cust = customer_service.get_customer(e.customer_id)
                cname = cust.full_name
                vip_label = f"{cust.vip_level.label} ({e.priority})"
            except Exception:
                cname = "-"
        ds_name = "Max-Heap (VIP)" if e.priority > 0 else "LinkedQueue (FIFO)"
        rows.append(
            [
                idx,
                e.entry_id,
                e.customer_id,
                cname,
                vip_label,
                e.room_type.label,
                format_date(e.check_in),
                format_date(e.check_out),
                ds_name,
            ]
        )
    return render_table(headers, rows)


def format_service_requests_table(requests):
    headers = [
        "Mã YC",
        "Phòng",
        "Mã KH",
        "Loại dịch vụ",
        "Độ khẩn",
        "Trạng thái",
        "Ghi chú",
    ]
    rows = []
    for req in requests:
        rows.append(
            [
                req.request_id,
                req.room_id,
                req.customer_id or "-",
                req.service_type.label,
                f"{req.urgency.label} ({int(req.urgency)})",
                req.status.label,
                req.note,
            ]
        )
    return render_table(headers, rows)


def format_undo_stack_table(actions):
    headers = ["Vị trí Stack", "Mã đơn bị hủy", "Phòng", "Người hủy", "Ngày hủy", "Trạng thái trước hủy"]
    rows = []
    for idx, act in enumerate(actions):
        pos = "ĐỈNH (Top)" if idx == 0 else f"Đáy -{idx}"
        rows.append(
            [
                pos,
                act.booking_id,
                act.room_id,
                act.cancelled_by,
                format_date(act.cancelled_at),
                act.booking_snapshot.get("status", ""),
            ]
        )
    return render_table(headers, rows)


def format_bill_detail(bill):
    """Hiển thị bảng kê chi tiết tổng chi phí (hóa đơn thanh toán) của một đơn đặt phòng."""
    booking = bill["booking"]
    customer = bill["customer"]
    room = bill["room"]
    pct = int(round(bill["discount_rate"] * 100))
    applied_pct = int(round(bill.get("applied_discount_rate", bill["discount_rate"]) * 100))
    discount_label = (
        f"4. Giảm giá VIP ({applied_pct}% lúc TT)"
        if bill["is_paid"] and applied_pct != pct
        else f"4. Giảm giá VIP ({applied_pct}%)"
    )

    lines = [
        f"=== BẢNG KÊ TỔNG CHI PHÍ / HÓA ĐƠN ĐẶT PHÒNG ({booking.booking_id}) ===",
    ]
    info_rows = [
        ["Mã đơn đặt phòng", f"{booking.booking_id} ({booking.status.label})"],
        ["Khách hàng", f"{customer.customer_id} - {customer.full_name} (SĐT: {customer.phone})"],
        ["Hạng thành viên VIP", f"{customer.vip_level.label} (Chiết khấu {pct}%)"],
        ["Tích lũy đã thanh toán", format_vnd(bill.get("customer_total_paid", 0))],
        ["Phòng lưu trú", f"{room.room_id} - Loại {room.room_type.label} (Tầng {room.floor})"],
        ["Thời gian lưu trú", f"{format_date(booking.check_in)} -> {format_date(booking.check_out)} ({bill['num_nights']} đêm)"],
        [
            "1. Tiền phòng",
            f"{bill['num_nights']} đêm × {format_vnd(bill['price_per_night'])} = {format_vnd(bill['room_cost'])}",
        ],
    ]
    if bill["service_items"]:
        srv_desc = ", ".join(
            f"{item['request_id']}:{item['service_type'].label}({format_vnd(item['fee'])})"
            for item in bill["service_items"]
        )
        info_rows.append(["2. Phí dịch vụ nội bộ", f"{format_vnd(bill['service_cost'])} [{srv_desc}]"])
    else:
        info_rows.append(["2. Phí dịch vụ nội bộ", "0 đ (Không phát sinh)"])

    info_rows.extend(
        [
            ["3. Phụ phí phát sinh khác", format_vnd(bill["extra_fee"])],
            ["Tổng tạm tính (1 + 2 + 3)", format_vnd(bill["gross_amount"])],
            [discount_label, f"- {format_vnd(bill['discount_amount'])}"],
            ["TỔNG CHI PHÍ PHẢI THANH TOÁN", format_vnd(bill["total_amount"])],
            [
                "Trạng thái thanh toán",
                f"{bill['payment_status'].label}"
                + (
                    f" (Mã GD: {bill['active_payment'].payment_id} - {bill['active_payment'].payment_method.label})"
                    if bill["active_payment"] is not None and bill["remaining_amount"] == 0
                    else (
                        f" (Đã thu {format_vnd(bill['paid_amount'])}, còn phải thu: {format_vnd(bill['remaining_amount'])})"
                        if bill["paid_amount"] > 0
                        else f" (Còn phải thu: {format_vnd(bill['remaining_amount'])})"
                    )
                ),
            ],
        ]
    )
    if bill.get("will_upgrade_vip") and not bill["is_paid"]:
        info_rows.append(
            [
                "Xét nâng hạng VIP tự động",
                f"Sau thanh toán đạt {format_vnd(bill['projected_total_paid'])} -> Tự động lên VIP {bill['projected_vip_level'].label}",
            ]
        )
    lines.append(render_table(["Khoản mục chi phí", "Chi tiết / Số tiền"], info_rows))
    return "\n".join(lines)


def format_payments_table(payments, customer_service=None):
    """Hiển thị bảng danh sách các giao dịch thanh toán đã lưu."""
    headers = [
        "Mã GD",
        "Mã đơn",
        "Mã KH",
        "Tên khách hàng",
        "Phòng",
        "Tiền phòng",
        "Phí DV+Phụ phí",
        "Giảm VIP",
        "Tổng thanh toán",
        "Phương thức",
        "Ngày TT",
        "Trạng thái",
    ]
    rows = []
    for tx in payments:
        cname = ""
        if customer_service is not None:
            try:
                cname = customer_service.get_customer(tx.customer_id).full_name
            except Exception:
                cname = "-"
        rows.append(
            [
                tx.payment_id,
                tx.booking_id,
                tx.customer_id,
                cname,
                tx.room_id,
                format_vnd(tx.room_cost),
                format_vnd(tx.service_cost + tx.extra_fee),
                format_vnd(tx.discount_amount),
                format_vnd(tx.total_amount),
                tx.payment_method.label,
                format_date(tx.paid_at),
                tx.status.label,
            ]
        )
    return render_table(headers, rows)


# ============================================================================
# MODULE: hotel/benchmark.py
# ============================================================================
"""Đánh giá hiệu năng thực nghiệm (Chương 4 — Mục 4.3).

So sánh thời gian thực thi giữa cách tiếp cận ngây thơ (Naive) và cấu trúc dữ liệu
tối ưu tự cài đặt trên tập dữ liệu >= 1.000 bản ghi.
"""




def _ms(seconds):
    return round(seconds * 1000.0, 3)


def benchmark_room_access(num_floors=50, rooms_per_floor=40, queries=2_000):
    """1. Truy cập phòng (n = 2.000 phòng, 2.000 truy vấn): Tuyến tính O(n) vs Matrix2D O(1)."""
    matrix = Matrix2D(num_floors, rooms_per_floor)
    flat_list = []
    for r in range(num_floors):
        for c in range(rooms_per_floor):
            item = (r + 1, c + 1, f"P{r + 1}{c + 1:02d}")
            matrix.set(r, c, item)
            flat_list.append(item)

    rng = random.Random(42)
    coords = [(rng.randrange(num_floors), rng.randrange(rooms_per_floor)) for _ in range(queries)]

    t0 = time.perf_counter()
    for r, c in coords:
        target_f, target_n = r + 1, c + 1
        linear_search(flat_list, lambda x: x[0] == target_f and x[1] == target_n)
    naive_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    for r, c in coords:
        matrix.get(r, c)
    opt_time = time.perf_counter() - t0

    return {
        "operation": f"1. Truy cập phòng ({num_floors * rooms_per_floor} phòng, {queries} truy vấn)",
        "naive_name": "Duyệt mảng O(n)",
        "opt_name": "Matrix2D O(1)",
        "naive_ms": _ms(naive_time),
        "opt_ms": _ms(opt_time),
        "speedup": round(naive_time / max(opt_time, 1e-9), 1),
    }


def benchmark_interval_conflict(n_intervals=2_000, queries=2_000):
    """2. Kiểm tra xung đột ngày (n = 2.000 lịch, 2.000 truy vấn): Mảng O(n) vs BST/AVL O(log n)."""
    base = date(2025, 1, 1)
    intervals = []
    schedule = IntervalSchedule(lambda x: x[0], lambda x: x[1])
    for i in range(n_intervals):
        start = base + timedelta(days=i * 3)
        end = start + timedelta(days=2)
        iv = (start, end, i)
        intervals.append(iv)
        schedule.add(iv)

    rng = random.Random(42)
    query_ranges = []
    for _ in range(queries):
        offset = rng.randrange(0, n_intervals * 3)
        q_start = base + timedelta(days=offset)
        q_end = q_start + timedelta(days=2)
        query_ranges.append((q_start, q_end))

    t0 = time.perf_counter()
    naive_hits = 0
    for qs, qe in query_ranges:
        if linear_find_conflict(intervals, qs, qe, lambda x: x[0], lambda x: x[1]) is not None:
            naive_hits += 1
    naive_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    opt_hits = 0
    for qs, qe in query_ranges:
        if schedule.find_conflict(qs, qe) is not None:
            opt_hits += 1
    opt_time = time.perf_counter() - t0

    assert naive_hits == opt_hits, "Kết quả kiểm tra xung đột giữa Naive và BST phải khớp tuyệt đối"
    return {
        "operation": f"2. Kiểm tra xung đột ngày ({n_intervals} booking, {queries} truy vấn)",
        "naive_name": "Duyệt tuần tự O(n)",
        "opt_name": "BST/AVL O(log n)",
        "naive_ms": _ms(naive_time),
        "opt_ms": _ms(opt_time),
        "speedup": round(naive_time / max(opt_time, 1e-9), 1),
    }


def benchmark_sorting(n_items=2_000):
    """3. Sắp xếp danh sách phòng theo giá (n = 2.000): Selection Sort O(n²) vs Merge/Quick Sort O(n log n)."""
    rng = random.Random(42)
    items = [(rng.choice([500_000, 650_000, 800_000, 950_000, 1_500_000, 1_700_000]) + rng.randint(0, 50) * 10_000, i) for i in range(n_items)]

    t0 = time.perf_counter()
    s_sel = selection_sort(items, key=lambda x: x[0])
    naive_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    s_merge = merge_sort(items, key=lambda x: x[0])
    merge_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    s_quick = quick_sort(items, key=lambda x: x[0])
    quick_time = time.perf_counter() - t0

    assert [x[0] for x in s_sel] == [x[0] for x in s_merge] == [x[0] for x in s_quick]
    return [
        {
            "operation": f"3a. Sắp xếp phòng theo giá ({n_items} bản ghi)",
            "naive_name": "Selection Sort O(n²)",
            "opt_name": "Merge Sort O(n log n)",
            "naive_ms": _ms(naive_time),
            "opt_ms": _ms(merge_time),
            "speedup": round(naive_time / max(merge_time, 1e-9), 1),
        },
        {
            "operation": f"3b. Sắp xếp phòng theo giá ({n_items} bản ghi)",
            "naive_name": "Selection Sort O(n²)",
            "opt_name": "Quick Sort 3-way O(n log n)",
            "naive_ms": _ms(naive_time),
            "opt_ms": _ms(quick_time),
            "speedup": round(naive_time / max(quick_time, 1e-9), 1),
        },
    ]


def benchmark_price_search(n_items=5_000, queries=2_000):
    """4. Tìm phòng theo giá trên mảng đã sắp (n = 5.000, 2.000 truy vấn): Linear O(n) vs Binary Search O(log n)."""
    sorted_items = [(500_000 + i * 500, f"P{i:04d}") for i in range(n_items)]
    rng = random.Random(42)
    targets = [500_000 + rng.randrange(n_items) * 500 for _ in range(queries)]

    t0 = time.perf_counter()
    for target in targets:
        linear_search(sorted_items, lambda x: x[0] == target)
    naive_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    for target in targets:
        idx = binary_search(sorted_items, target, key=lambda x: x[0])
        assert idx != -1
        find_closest(sorted_items, target, key=lambda x: x[0])
    opt_time = time.perf_counter() - t0

    return {
        "operation": f"4. Tìm kiếm phòng theo giá ({n_items} phòng, {queries} truy vấn)",
        "naive_name": "Linear Search O(n)",
        "opt_name": "Binary Search O(log n)",
        "naive_ms": _ms(naive_time),
        "opt_ms": _ms(opt_time),
        "speedup": round(naive_time / max(opt_time, 1e-9), 1),
    }


def benchmark_priority_queue(n_waiting=2_000):
    """5. Hàng chờ VIP & Dịch vụ (k = 2.000 phần tử, push + pop hết): Mảng O(k²) vs Max-Heap O(k log k)."""
    rng = random.Random(42)
    entries = [(rng.randint(0, 3), -seq, f"KH{seq:04d}") for seq in range(n_waiting)]
    key_fn = lambda x: (x[0], x[1])

    t0 = time.perf_counter()
    naive_list = []
    for item in entries:
        naive_list.append(item)
    naive_order = [linear_extract_max(naive_list, key_fn) for _ in range(n_waiting)]
    naive_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    heap = MaxHeap(key_fn)
    for item in entries:
        heap.push(item)
    heap_order = [heap.pop() for _ in range(n_waiting)]
    opt_time = time.perf_counter() - t0

    assert naive_order == heap_order, "Thứ tự lấy ra từ Max-Heap phải khớp tuyệt đối với đặc tả ưu tiên"
    return {
        "operation": f"5. Hàng đợi ưu tiên VIP ({n_waiting} push + {n_waiting} pop)",
        "naive_name": "Mảng thường O(k)/pop",
        "opt_name": "Max-Heap O(log k)/pop",
        "naive_ms": _ms(naive_time),
        "opt_ms": _ms(opt_time),
        "speedup": round(naive_time / max(opt_time, 1e-9), 1),
    }


def benchmark_customer_lookup(n_customers=3_000, queries=2_000):
    """6. Tra cứu khách hàng theo CCCD (n = 3.000 khách, 2.000 truy vấn): Mảng O(n) vs Hash Table O(1)."""
    cust_list = []
    table = HashTable()
    for i in range(n_customers):
        cccd = f"001200{i:06d}"
        record = (cccd, f"Khách hàng {i}")
        cust_list.append(record)
        table.put(cccd, record)

    rng = random.Random(42)
    query_keys = [f"001200{rng.randrange(n_customers):06d}" for _ in range(queries)]

    t0 = time.perf_counter()
    for key in query_keys:
        linear_search(cust_list, lambda x: x[0] == key)
    naive_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    for key in query_keys:
        res = table.get(key)
        assert res is not None
    opt_time = time.perf_counter() - t0

    return {
        "operation": f"6. Tra cứu khách theo CCCD ({n_customers} KH, {queries} truy vấn)",
        "naive_name": "Duyệt tuần tự O(n)",
        "opt_name": "Hash Table O(1) avg",
        "naive_ms": _ms(naive_time),
        "opt_ms": _ms(opt_time),
        "speedup": round(naive_time / max(opt_time, 1e-9), 1),
    }


def benchmark_payment_lookup(n_payments=3_000, queries=2_000):
    """7. Tra cứu giao dịch thanh toán theo Mã GD (p = 3.000 GD, 2.000 truy vấn): Mảng O(p) vs Hash Table O(1)."""
    payment_list = []
    table = HashTable()
    for i in range(1, n_payments + 1):
        pid = f"TT{i:05d}"
        record = (pid, f"BK{i:05d}", 1_000_000 + (i % 10) * 150_000)
        payment_list.append(record)
        table.put(pid, record)

    rng = random.Random(42)
    query_keys = [f"TT{rng.randint(1, n_payments):05d}" for _ in range(queries)]

    t0 = time.perf_counter()
    for key in query_keys:
        linear_search(payment_list, lambda x: x[0] == key)
    naive_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    for key in query_keys:
        res = table.get(key)
        assert res is not None
    opt_time = time.perf_counter() - t0

    return {
        "operation": f"7. Tra cứu giao dịch thanh toán ({n_payments} GD, {queries} truy vấn)",
        "naive_name": "Duyệt tuần tự O(p)",
        "opt_name": "Hash Table O(1) avg",
        "naive_ms": _ms(naive_time),
        "opt_ms": _ms(opt_time),
        "speedup": round(naive_time / max(opt_time, 1e-9), 1),
    }


def run_all_benchmarks():
    results = [
        benchmark_room_access(),
        benchmark_interval_conflict(),
        *benchmark_sorting(),
        benchmark_price_search(),
        benchmark_priority_queue(),
        benchmark_customer_lookup(),
        benchmark_payment_lookup(),
    ]
    return results


def format_benchmark_report(results=None):
    data = results if results is not None else run_all_benchmarks()
    headers = [
        "Bài toán & Quy mô kiểm thử (>= 2.000 bản ghi)",
        "Cấu trúc Ngây thơ",
        "Cấu trúc Tối ưu",
        "TG Ngây thơ (ms)",
        "TG Tối ưu (ms)",
        "Tăng tốc (lần)",
    ]
    rows = [
        [
            r["operation"],
            r["naive_name"],
            r["opt_name"],
            f"{r['naive_ms']:.3f}",
            f"{r['opt_ms']:.3f}",
            f"x{r['speedup']}",
        ]
        for r in data
    ]
    return render_table(headers, rows)


# ============================================================================
# MODULE: hotel/ui/cli.py
# ============================================================================
"""Giao diện dòng lệnh (CLI Menu) tương tác tiếng Việt cho Hệ thống Đặt phòng Khách sạn."""




def _prompt(text, default=None):
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"{text}{suffix}: ").strip()
    if not raw and default is not None:
        return str(default)
    return raw


def _prompt_date(text, default_date=None):
    default_str = format_date(default_date) if default_date is not None else None
    raw = _prompt(f"{text} (dd/mm/yyyy)", default_str)
    return parse_date(raw)


def _prompt_room_type(allow_all=True):
    options = "1=Đơn (SINGLE), 2=Đôi (DOUBLE), 3=Suite (SUITE)"
    if allow_all:
        options = "0=Tất cả, " + options
    choice = _prompt(f"Chọn loại phòng ({options})", "0" if allow_all else "1")
    mapping = {"1": RoomType.SINGLE, "2": RoomType.DOUBLE, "3": RoomType.SUITE}
    if allow_all and choice == "0":
        return None
    if choice not in mapping:
        raise HotelError("Lựa chọn loại phòng không hợp lệ")
    return mapping[choice]


class HotelCLI:
    def __init__(self, manager):
        self.manager = manager

    def run(self):
        while True:
            self._print_main_menu()
            choice = input("Chọn chức năng (0-10): ").strip()
            if choice == "0":
                self.manager.save()
                print("\nĐã lưu dữ liệu. Cảm ơn bạn đã sử dụng hệ thống!")
                break
            try:
                self._dispatch(choice)
            except HotelError as exc:
                print(f"\n[!] Lỗi nghiệp vụ: {exc}")
            except ValueError as exc:
                print(f"\n[!] Dữ liệu nhập chưa hợp lệ: {exc}")
            except (KeyboardInterrupt, EOFError):
                self.manager.save()
                print("\nĐã lưu dữ liệu và thoát chương trình.")
                break

    def _print_main_menu(self):
        print("\n" + "=" * 78)
        print("   HỆ THỐNG QUẢN LÝ ĐẶT PHÒNG KHÁCH SẠN (CẤU TRÚC DỮ LIỆU & GIẢI THUẬT - MI3060)")
        print("=" * 78)
        print("  1. Sơ đồ phòng theo tầng & Tra cứu phòng O(1)         [Mảng 2 chiều Matrix2D]")
        print("  2. Tìm phòng trống theo khoảng ngày                   [BST / AVL IntervalSchedule]")
        print("  3. Lọc & Sắp xếp phòng theo loại, giá, ngân sách      [Merge/Quick Sort + Binary Search]")
        print("  4. Đặt phòng / Nhận phòng (Check-in) / Trả phòng      [BST O(log n) + HashTable]")
        print("  5. Hủy đặt phòng & Hoàn tác (Undo)                    [Ngăn xếp Stack O(1)]")
        print("  6. Danh sách chờ khi hết phòng (Thường & VIP)         [Queue FIFO + Max-Heap VIP]")
        print("  7. Quản lý khách hàng & Lịch sử lưu trú               [Hash Table O(1) + Linked List]")
        print("  8. Yêu cầu dịch vụ nội bộ (Dọn phòng, Đồ ăn, Y tế)    [Priority Queue Max-Heap]")
        print("  9. Quản lý thanh toán (Tính phí, Xử lý, Lưu & Tra cứu)[Hash Table O(1) + Linked List]")
        print("  10. Thống kê doanh thu, tỷ lệ lấp đầy & Khởi tạo mẫu  [Báo cáo & JSON Persistence]")
        print("  0. Lưu và Thoát")
        print("-" * 78)

    def _dispatch(self, choice):
        handlers = {
            "1": self._menu_room_matrix,
            "2": self._menu_available_rooms,
            "3": self._menu_sort_and_search_rooms,
            "4": self._menu_booking_operations,
            "5": self._menu_cancel_and_undo,
            "6": self._menu_waiting_list,
            "7": self._menu_customers_and_history,
            "8": self._menu_service_requests,
            "9": self._menu_payments,
            "10": self._menu_reports_and_system,
        }
        handler = handlers.get(choice)
        if handler is None:
            print("\n[!] Vui lòng chọn số từ 0 đến 10.")
        else:
            handler()

    # -------------------- 1. Mảng 2 chiều Phòng ------------------------ #
    def _menu_room_matrix(self):
        print("\n--- [1] SƠ ĐỒ PHÒNG THEO TẦNG & TRA CỨU TRỰC TIẾP O(1) ---")
        print("  1. Hiển thị sơ đồ ma trận toàn khách sạn theo ngày")
        print("  2. Tra cứu trực tiếp phòng theo (Tầng, Số phòng) hoặc Mã phòng — O(1)")
        print("  3. Đặt / Gỡ trạng thái Bảo trì cho phòng")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            target = _prompt_date("Xem trạng thái tại ngày", date.today())
            print("\n" + render_floor_matrix(self.manager.floor_map(target), target))
        elif sub == "2":
            code = _prompt("Nhập mã phòng (vd P205) hoặc để trống để nhập tầng/số")
            if code:
                room = self.manager.get_room(code)
            else:
                floor = int(_prompt("Nhập tầng", "2"))
                room_number = int(_prompt("Nhập số phòng trong tầng", "5"))
                room = self.manager.get_room_by_coords(floor, room_number)
            status = self.manager.bookings.room_status_on(room.room_id, date.today())
            print("\n" + format_rooms_table([room], self.manager))
            print(f"-> Truy cập trực tiếp Matrix2D[{room.floor - 1}][{room.room_number - 1}] = {status.label}")
            bookings = self.manager.bookings.bookings_for_room(room.room_id)
            if bookings:
                print("\nLịch đặt của phòng trên cây BST (in-order theo ngày nhận):")
                print(format_bookings_table(bookings, self.manager.customers))
        elif sub == "3":
            code = _prompt("Nhập mã phòng cần đổi trạng thái bảo trì", "P104")
            flag = _prompt("Đặt bảo trì? (1=Bảo trì, 0=Hoạt động bình thường)", "0") == "1"
            room = self.manager.set_room_maintenance(code, flag)
            print(f"\nĐã cập nhật phòng {room.room_id}: under_maintenance = {room.under_maintenance}")

    # -------------------- 2. Tìm phòng trống trên BST ------------------ #
    def _menu_available_rooms(self):
        print("\n--- [2] TÌM PHÒNG TRỐNG THEO KHOẢNG NGÀY (BST O(log n)) ---")
        today = date.today()
        check_in = _prompt_date("Ngày nhận phòng", today + timedelta(days=1))
        check_out = _prompt_date("Ngày trả phòng", today + timedelta(days=3))
        rtype = _prompt_room_type(allow_all=True)
        rooms = self.manager.find_available_rooms(check_in, check_out, room_type=rtype)
        print(
            f"\nTìm thấy {len(rooms)} phòng trống từ {format_date(check_in)} đến {format_date(check_out)}:"
        )
        print(format_rooms_table(rooms, self.manager, check_in))

    # ------------- 3. Sắp xếp & Tìm kiếm nhị phân theo giá ------------- #
    def _menu_sort_and_search_rooms(self):
        print("\n--- [3] LỌC, SẮP XẾP (MERGE/QUICK SORT) & TÌM KIẾM NHỊ PHÂN ---")
        print("  1. Sắp xếp danh sách phòng theo giá (Merge Sort / Quick Sort — O(R log R))")
        print("  2. Tìm phòng theo khoảng giá [min, max] (Binary Search — O(log R + k))")
        print("  3. Gợi ý phòng có giá gần nhất với ngân sách (Binary Search — O(log R))")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            algo = "quick" if _prompt("Giải thuật (1=Merge Sort, 2=Quick Sort)", "1") == "2" else "merge"
            rev = _prompt("Thứ tự (1=Tăng dần, 2=Giảm dần)", "1") == "2"
            rooms = self.manager.sort_rooms(by="price", reverse=rev, algorithm=algo)
            print(f"\nDanh sách phòng sắp xếp bằng {algo.upper()} SORT:")
            print(format_rooms_table(rooms, self.manager))
        elif sub == "2":
            min_p = int(_prompt("Giá tối thiểu (VND)", "500000"))
            max_p = int(_prompt("Giá tối đa (VND)", "1000000"))
            rtype = _prompt_room_type(allow_all=True)
            rooms = self.manager.filter_rooms_by_price(min_p, max_p, room_type=rtype)
            print(f"\nKết quả Binary Search trong khoảng [{format_vnd(min_p)} .. {format_vnd(max_p)}]:")
            print(format_rooms_table(rooms, self.manager))
        elif sub == "3":
            budget = int(_prompt("Nhập ngân sách dự kiến / đêm (VND)", "850000"))
            rtype = _prompt_room_type(allow_all=True)
            room = self.manager.suggest_room_by_budget(budget, room_type=rtype)
            if room is None:
                print("\nKhông tìm thấy phòng phù hợp.")
            else:
                print(f"\nPhòng có giá gần ngân sách {format_vnd(budget)} nhất (O(log R)):")
                print(format_rooms_table([room], self.manager))

    # ---------------- 4. Đặt phòng / Nhận / Trả phòng ------------------ #
    def _resolve_or_register_customer(self, identifier):
        """Tìm khách hàng theo Mã/CCCD/SĐT; nếu chưa có thì cho phép đăng ký nhanh tại chỗ."""
        try:
            return self.manager.lookup_customer(identifier)
        except NotFoundError:
            print(f"\n[i] Khách hàng '{identifier}' chưa có trong hệ thống.")
            ans = _prompt("Bạn có muốn đăng ký mới khách hàng này ngay bây giờ không? (y/n)", "y").lower()
            if ans != "y":
                raise
            raw = (identifier or "").strip()
            default_phone = raw if raw.isdigit() and len(raw) <= 11 else ""
            default_cccd = raw if raw.isdigit() and len(raw) >= 12 else ""
            name = _prompt("  + Họ và tên khách hàng")
            cccd = _prompt("  + Số CCCD (8..15 chữ số)", default_cccd or None)
            phone = _prompt("  + Số điện thoại (8..15 chữ số)", default_phone or None)
            vip = int(_prompt("  + Cấp VIP (0=Thường, 1=Silver, 2=Gold, 3=Platinum)", "0"))
            customer = self.manager.register_customer(name, cccd, phone, VipLevel(vip))
            print(f"[OK] Đã tạo khách hàng mới: {customer.customer_id} - {customer.full_name} (SĐT: {customer.phone})")
            return customer

    def _menu_booking_operations(self):
        print("\n--- [4] ĐẶT PHÒNG / NHẬN PHÒNG (CHECK-IN) / TRẢ PHÒNG (CHECK-OUT) ---")
        print("  1. Đặt phòng cụ thể theo mã phòng (kiểm tra xung đột trên BST)")
        print("  2. Đặt phòng theo loại (tự động vào Hàng chờ nếu hết phòng)")
        print("  3. Nhận phòng (Check-in)")
        print("  4. Trả phòng (Check-out)")
        print("  5. Xem danh sách toàn bộ đơn đặt phòng")
        sub = _prompt("Chọn", "1")
        today = date.today()
        if sub == "1":
            cid = _prompt("Mã KH / CCCD / SĐT khách hàng", "KH001")
            customer = self._resolve_or_register_customer(cid)
            old_vip = customer.vip_level
            room_id = _prompt("Mã phòng muốn đặt (vd P205)", "P103")
            check_in = _prompt_date("Ngày nhận phòng", today + timedelta(days=1))
            check_out = _prompt_date("Ngày trả phòng", today + timedelta(days=3))
            booking = self.manager.book_room(customer.customer_id, room_id, check_in, check_out)
            print("\n[OK] Đặt phòng thành công:")
            print(format_bookings_table([booking], self.manager.customers))
            new_vip = self.manager.customers.get_customer(customer.customer_id).vip_level
            if new_vip > old_vip:
                total_paid = self.manager.customer_total_paid(customer.customer_id)
                print(
                    f"[★ VIP UPGRADE] Khách hàng {customer.full_name} ({customer.customer_id}) "
                    f"đạt tích lũy {format_vnd(total_paid)} -> Tự động nâng hạng VIP: {old_vip.label} -> {new_vip.label}!"
                )
        elif sub == "2":
            cid = _prompt("Mã KH / CCCD / SĐT khách hàng", "KH004")
            customer = self._resolve_or_register_customer(cid)
            old_vip = customer.vip_level
            rtype = _prompt_room_type(allow_all=False)
            check_in = _prompt_date("Ngày nhận phòng", today + timedelta(days=1))
            check_out = _prompt_date("Ngày trả phòng", today + timedelta(days=3))
            mode, record = self.manager.book_by_type_or_wait(
                customer.customer_id, rtype, check_in, check_out
            )
            if mode == "BOOKED":
                print("\n[OK] Còn phòng trống — Đã tạo đơn đặt phòng:")
                print(format_bookings_table([record], self.manager.customers))
                new_vip = self.manager.customers.get_customer(customer.customer_id).vip_level
                if new_vip > old_vip:
                    total_paid = self.manager.customer_total_paid(customer.customer_id)
                    print(
                        f"[★ VIP UPGRADE] Khách hàng {customer.full_name} ({customer.customer_id}) "
                        f"đạt tích lũy {format_vnd(total_paid)} -> Tự động nâng hạng VIP: {old_vip.label} -> {new_vip.label}!"
                    )
            else:
                print("\n[!] Hết phòng trống loại yêu cầu — Đã xếp khách vào danh sách chờ:")
                print(format_waiting_table([record], self.manager.customers))
        elif sub == "3":
            bid = _prompt("Nhập mã đơn đặt phòng cần Check-in", "BK00004")
            booking = self.manager.check_in(bid)
            print("\n[OK] Đã nhận phòng:")
            print(format_bookings_table([booking], self.manager.customers))
        elif sub == "4":
            bid = _prompt("Nhập mã đơn đặt phòng cần Check-out", "BK00003")
            bill = self.manager.calculate_booking_cost(bid)
            print("\n" + format_bill_detail(bill))
            if not bill["is_paid"]:
                pay_now = _prompt("Đơn này chưa thanh toán. Thanh toán ngay khi trả phòng? (y/n)", "y").lower()
                if pay_now == "y":
                    old_vip = bill["customer"].vip_level
                    method = self._prompt_payment_method()
                    extra = int(_prompt("Phụ phí phát sinh thêm (VND)", "0"))
                    note = _prompt("Ghi chú thanh toán", "Thanh toán khi trả phòng")
                    tx = self.manager.process_payment(bid, payment_method=method, extra_fee=extra, note=note)
                    print(f"\n[OK] Đã xử lý và lưu giao dịch thanh toán {tx.payment_id}:")
                    print(format_payments_table([tx], self.manager.customers))
                    new_vip = self.manager.customers.get_customer(tx.customer_id).vip_level
                    if new_vip > old_vip:
                        total_paid = self.manager.customer_total_paid(tx.customer_id)
                        print(
                            f"[★ VIP UPGRADE] Khách hàng {bill['customer'].full_name} ({tx.customer_id}) "
                            f"đạt tích lũy {format_vnd(total_paid)} -> Tự động nâng hạng VIP: {old_vip.label} -> {new_vip.label}!"
                        )
            booking = self.manager.check_out(bid)
            print("\n[OK] Đã trả phòng:")
            print(format_bookings_table([booking], self.manager.customers))
        elif sub == "5":
            bookings = merge_sort(self.manager.bookings.all_bookings(), key=lambda b: b.booking_id)
            print("\nDanh sách toàn bộ đơn đặt phòng:")
            print(format_bookings_table(bookings, self.manager.customers))

    # ---------------- 5. Hủy đặt phòng & Hoàn tác (Stack) -------------- #
    def _menu_cancel_and_undo(self):
        print("\n--- [5] HỦY ĐẶT PHÒNG & HOÀN TÁC (STACK LIFO — O(1)) ---")
        print("  1. Hủy một đơn đặt phòng (push vào Undo Stack)")
        print("  2. Hoàn tác thao tác hủy gần nhất (pop từ Undo Stack)")
        print("  3. Xem ngăn xếp các thao tác hủy hiện tại")
        sub = _prompt("Chọn", "3")
        if sub == "1":
            bid = _prompt("Nhập mã đơn đặt phòng cần hủy", "BK00004")
            by = _prompt("Người thực hiện hủy (STAFF / CUSTOMER)", "STAFF").upper()
            action, _ = self.manager.cancel_booking(bid, cancelled_by=by)
            print(f"\n[OK] Đã hủy đơn {action.booking_id} và đẩy vào đỉnh Undo Stack.")
        elif sub == "2":
            action, booking = self.manager.undo_last_cancellation()
            print(f"\n[OK] Đã hoàn tác lệnh hủy đơn {action.booking_id} — Khôi phục lịch trên BST:")
            print(format_bookings_table([booking], self.manager.customers))
        elif sub == "3":
            print("\nNgăn xếp hoàn tác (Stack — từ đỉnh xuống đáy):")
            print(format_undo_stack_table(self.manager.undo.history()))

    # ---------------- 6. Danh sách chờ (Queue + Max-Heap) -------------- #
    def _menu_waiting_list(self):
        print("\n--- [6] DANH SÁCH CHỜ KHI HẾT PHÒNG (QUEUE THƯỜNG + MAX-HEAP VIP) ---")
        print("  1. Xem danh sách chờ theo thứ tự ưu tiên phục vụ")
        print("  2. Thêm khách vào danh sách chờ")
        print("  3. Tự động phân phòng trống cho danh sách chờ (ưu tiên VIP trước)")
        print("  4. Lấy khách ưu tiên cao nhất ra khỏi hàng chờ (pop)")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            entries = self.manager.waiting.list_waiting_ordered()
            print(
                f"\nDanh sách chờ ({self.manager.waiting.vip_count()} VIP trong Max-Heap, "
                f"{self.manager.waiting.normal_count()} khách thường trong LinkedQueue):"
            )
            print(format_waiting_table(entries, self.manager.customers))
        elif sub == "2":
            cid = _prompt("Mã KH / CCCD / SĐT", "KH001")
            customer = self._resolve_or_register_customer(cid)
            rtype = _prompt_room_type(allow_all=False)
            today = date.today()
            check_in = _prompt_date("Ngày nhận mong muốn", today + timedelta(days=1))
            check_out = _prompt_date("Ngày trả mong muốn", today + timedelta(days=3))
            entry = self.manager.add_to_waiting_list(customer.customer_id, rtype, check_in, check_out)
            print("\n[OK] Đã thêm vào hàng chờ:")
            print(format_waiting_table([entry], self.manager.customers))
        elif sub == "3":
            fulfilled = self.manager.process_waiting_list()
            if not fulfilled:
                print("\nHiện chưa có phòng trống khớp với nhu cầu trong danh sách chờ.")
            else:
                print(f"\n[OK] Đã tự động xếp phòng cho {len(fulfilled)} khách trong danh sách chờ:")
                print(format_bookings_table([b for _, b in fulfilled], self.manager.customers))
        elif sub == "4":
            entry = self.manager.pop_next_waiting()
            print("\n[OK] Khách được lấy ra đầu tiên (ưu tiên cao nhất):")
            print(format_waiting_table([entry], self.manager.customers))

    # ---------------- 7. Khách hàng & Lịch sử lưu trú ------------------ #
    def _menu_customers_and_history(self):
        print("\n--- [7] QUẢN LÝ KHÁCH HÀNG (HASH TABLE) & LỊCH SỬ LƯU TRÚ (LINKED LIST) ---")
        print("  1. Danh sách toàn bộ khách hàng (kèm tích lũy đã TT & tiến độ nâng VIP)")
        print("  2. Tra cứu khách hàng theo Mã KH / CCCD / SĐT — O(1) trung bình")
        print("  3. Xem lịch sử lưu trú của khách (duyệt SinglyLinkedList)")
        print("  4. Đăng ký khách hàng mới")
        print("  5. Cập nhật hạng VIP cho khách hàng")
        print("  6. Xem chính sách mốc tích lũy & Quyền lợi tự động nâng hạng VIP")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            customers = merge_sort(self.manager.customers.all_customers(), key=lambda c: c.customer_id)
            print("\nDanh sách khách hàng:")
            print(format_customers_table(customers, self.manager.payments))
        elif sub == "2":
            ident = _prompt("Nhập Mã KH, CCCD hoặc Số điện thoại", "0901234567")
            customer = self.manager.lookup_customer(ident)
            print("\nKết quả tra cứu trên Bảng băm (Hash Table):")
            print(format_customers_table([customer], self.manager.payments))
        elif sub == "3":
            ident = _prompt("Nhập Mã KH, CCCD hoặc Số điện thoại", "KH004")
            customer = self.manager.lookup_customer(ident)
            history = self.manager.customer_stay_history(customer.customer_id)
            print(
                f"\nLịch sử lưu trú của {customer.full_name} ({customer.customer_id}) "
                f"— SinglyLinkedList (mới nhất ở đầu):"
            )
            print(format_bookings_table(history, self.manager.customers))
        elif sub == "4":
            name = _prompt("Họ và tên khách hàng")
            cccd = _prompt("Số CCCD (9..12 chữ số)")
            phone = _prompt("Số điện thoại (9..12 chữ số)")
            vip = int(_prompt("Cấp VIP (0=Thường, 1=Silver, 2=Gold, 3=Platinum)", "0"))
            customer = self.manager.register_customer(name, cccd, phone, VipLevel(vip))
            print("\n[OK] Đã đăng ký khách hàng mới:")
            print(format_customers_table([customer], self.manager.payments))
        elif sub == "5":
            ident = _prompt("Nhập Mã KH / CCCD / SĐT", "KH001")
            customer = self.manager.lookup_customer(ident)
            vip = int(_prompt("Cấp VIP mới (0=Thường, 1=Silver, 2=Gold, 3=Platinum)", "2"))
            updated = self.manager.set_customer_vip(customer.customer_id, VipLevel(vip))
            print("\n[OK] Đã cập nhật cấp VIP (đồng thời vun lại đống Max-Heap nếu đang chờ):")
            print(format_customers_table([updated], self.manager.payments))
        elif sub == "6":
            print("\nChính sách tự động nâng hạng VIP theo tổng tiền đã thanh toán tích lũy:")
            print(format_vip_policy_table())

    # ---------------- 8. Yêu cầu dịch vụ nội bộ ------------------------ #
    def _menu_service_requests(self):
        print("\n--- [8] YÊU CẦU DỊCH VỤ NỘI BỘ THEO ĐỘ KHẨN (MAX-HEAP — O(log s)) ---")
        print("  1. Xem hàng đợi yêu cầu dịch vụ đang chờ (theo độ ưu tiên giảm dần)")
        print("  2. Gửi yêu cầu dịch vụ mới (Dọn phòng / Đồ ăn / Y tế / Khác)")
        print("  3. Xử lý yêu cầu khẩn cấp nhất tiếp theo (pop từ Max-Heap)")
        print("  4. Xem lịch sử các yêu cầu dịch vụ đã hoàn thành")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            pending = self.manager.service_requests.pending_requests_ordered()
            print("\nHàng đợi ưu tiên yêu cầu dịch vụ (Max-Heap):")
            print(format_service_requests_table(pending))
        elif sub == "2":
            room_id = _prompt("Mã phòng gửi yêu cầu", "P101")
            t_choice = _prompt("Loại dịch vụ (1=Dọn phòng, 2=Đồ ăn, 3=Y tế, 4=Khác)", "2")
            t_map = {
                "1": ServiceType.CLEANING,
                "2": ServiceType.FOOD,
                "3": ServiceType.MEDICAL,
                "4": ServiceType.OTHER,
            }
            if t_choice not in t_map:
                raise HotelError("Loại dịch vụ không hợp lệ")
            u_choice = _prompt("Độ khẩn (1=Thấp, 2=Bình thường, 3=Khẩn cấp)", "2")
            u_map = {"1": UrgencyLevel.LOW, "2": UrgencyLevel.NORMAL, "3": UrgencyLevel.EMERGENCY}
            if u_choice not in u_map:
                raise HotelError("Độ khẩn không hợp lệ")
            note = _prompt("Ghi chú chi tiết", "Phục vụ tại phòng")
            req = self.manager.submit_service_request(
                room_id=room_id,
                service_type=t_map[t_choice],
                urgency=u_map[u_choice],
                note=note,
            )
            print("\n[OK] Đã thêm yêu cầu vào Max-Heap:")
            print(format_service_requests_table([req]))
        elif sub == "3":
            req = self.manager.process_next_service_request()
            print("\n[OK] Đã lấy và xử lý yêu cầu có độ ưu tiên cao nhất:")
            print(format_service_requests_table([req]))
        elif sub == "4":
            done = self.manager.service_requests.completed_requests()
            print("\nCác yêu cầu dịch vụ đã xử lý xong:")
            print(format_service_requests_table(done))

    # ---------------- 9. Quản lý thanh toán (HashTable + LL) ----------- #
    def _prompt_payment_method(self):
        choice = _prompt(
            "Chọn phương thức thanh toán (1=Tiền mặt, 2=Chuyển khoản, 3=Thẻ ngân hàng, 4=Ví điện tử)",
            "2",
        )
        mapping = {
            "1": PaymentMethod.CASH,
            "2": PaymentMethod.BANK_TRANSFER,
            "3": PaymentMethod.CARD,
            "4": PaymentMethod.E_WALLET,
        }
        if choice not in mapping:
            raise HotelError("Phương thức thanh toán không hợp lệ")
        return mapping[choice]

    def _menu_payments(self):
        print("\n--- [9] QUẢN LÝ THANH TOÁN: TÍNH TỔNG CHI PHÍ, XỬ LÝ, LƯU TRỮ & TRA CỨU ---")
        print("  1. Tính tổng chi phí & Xem bảng kê hóa đơn chi tiết của đơn đặt phòng")
        print("  2. Xử lý thanh toán cho đơn đặt phòng (lưu vào HashTable + SinglyLinkedList)")
        print("  3. Xem toàn bộ lịch sử giao dịch thanh toán đã lưu trữ")
        print("  4. Tra cứu thanh toán theo Mã GD / Mã đơn / Mã KH / CCCD / SĐT / Phòng — O(1)")
        print("  5. Hoàn tiền giao dịch thanh toán (Refund)")
        print("  6. Thống kê tổng hợp thanh toán & công nợ chưa thu")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            bid = _prompt("Nhập mã đơn đặt phòng cần tính chi phí", "BK00003")
            extra = int(_prompt("Phụ phí phát sinh khác (nếu có, VND)", "0"))
            bill = self.manager.calculate_booking_cost(bid, extra_fee=extra)
            print("\n" + format_bill_detail(bill))
        elif sub == "2":
            bid = _prompt("Nhập mã đơn đặt phòng cần thanh toán", "BK00003")
            extra = int(_prompt("Phụ phí phát sinh khác (VND)", "0"))
            bill = self.manager.calculate_booking_cost(bid, extra_fee=extra)
            print("\n" + format_bill_detail(bill))
            if bill["is_paid"]:
                print(f"\n[!] Đơn {bid} đã được thanh toán (Mã GD: {bill['active_payment'].payment_id}).")
                return
            old_vip = bill["customer"].vip_level
            method = self._prompt_payment_method()
            note = _prompt("Ghi chú giao dịch", "Thanh toán hóa đơn lưu trú")
            auto_co = False
            if bill["booking"].status == BookingStatus.CHECKED_IN:
                auto_co = _prompt("Khách đang ở — Tự động trả phòng (Check-out) luôn? (y/n)", "n").lower() == "y"
            tx = self.manager.process_payment(
                booking_id=bid,
                payment_method=method,
                extra_fee=extra,
                note=note,
                auto_check_out=auto_co,
            )
            print(f"\n[OK] Đã xử lý thanh toán thành công và lưu giao dịch {tx.payment_id}:")
            print(format_payments_table([tx], self.manager.customers))
            new_vip = self.manager.customers.get_customer(tx.customer_id).vip_level
            if new_vip > old_vip:
                total_paid = self.manager.customer_total_paid(tx.customer_id)
                print(
                    f"[★ VIP UPGRADE] Khách hàng {bill['customer'].full_name} ({tx.customer_id}) "
                    f"đạt tích lũy {format_vnd(total_paid)} -> Tự động nâng hạng VIP: {old_vip.label} -> {new_vip.label}!"
                )
        elif sub == "3":
            txs = self.manager.all_payments()
            print(f"\nDanh sách giao dịch thanh toán ({len(txs)} giao dịch — mới nhất ở đầu SinglyLinkedList):")
            print(format_payments_table(txs, self.manager.customers))
        elif sub == "4":
            q = _prompt("Nhập Mã GD (TT...), Mã đơn (BK...), Mã KH/CCCD/SĐT hoặc Mã phòng", "TT00001")
            found = self.manager.lookup_payments(q)
            print(f"\nKết quả tra cứu thanh toán cho '{q}' ({len(found)} giao dịch):")
            print(format_payments_table(found, self.manager.customers))
        elif sub == "5":
            ident = _prompt("Nhập Mã giao dịch (TT...) hoặc Mã đơn (BK...) cần hoàn tiền", "TT00002")
            reason = _prompt("Lý do hoàn tiền", "Khách thay đổi lịch trình")
            tx = self.manager.refund_payment(ident, reason=reason)
            print(f"\n[OK] Đã hoàn tiền giao dịch {tx.payment_id}:")
            print(format_payments_table([tx], self.manager.customers))
        elif sub == "6":
            summary = self.manager.payments.payment_summary()
            rows = [
                ["Tổng số giao dịch đã ghi nhận", summary["total_transactions"]],
                ["Số giao dịch Đã thanh toán / Đã hoàn tiền", f"{summary['paid_transactions']} / {summary['refunded_transactions']}"],
                ["Tổng số tiền đã thu thực tế", format_vnd(summary["total_collected"])],
                ["Tổng phí dịch vụ & phụ phí đã thu", format_vnd(summary["total_service_fee"])],
                ["Tổng chiết khấu VIP đã giảm cho khách", format_vnd(summary["total_discount"])],
                ["Tổng tiền đã hoàn trả (Refund)", format_vnd(summary["total_refunded"])],
                ["Số đơn hiệu lực chưa thanh toán", summary["unpaid_bookings_count"]],
                ["Tổng chi phí dự kiến cần thu thêm", format_vnd(summary["unpaid_estimated_total"])],
            ]
            print("\n=== THỐNG KÊ TỔNG HỢP QUẢN LÝ THANH TOÁN ===")
            print(render_table(["Chỉ tiêu thanh toán", "Giá trị"], rows))
            method_rows = [
                [
                    m.label,
                    summary["count_by_method"][m],
                    format_vnd(summary["revenue_by_method"][m]),
                ]
                for m in PaymentMethod
            ]
            print("\nDoanh thu đã thu theo phương thức thanh toán:")
            print(render_table(["Phương thức", "Số giao dịch", "Tổng tiền thu"], method_rows))

    # ---------------- 10. Báo cáo thống kê & Hệ thống ------------------ #
    def _menu_reports_and_system(self):
        print("\n--- [10] THỐNG KÊ DOANH THU, TỶ LỆ LẤP ĐẦY & DỮ LIỆU HỆ THỐNG ---")
        print("  1. Báo cáo doanh thu & tỷ lệ lấp đầy phòng")
        print("  2. Bảng xếp hạng Top khách hàng thân thiết (Merge Sort)")
        print("  3. Khởi tạo lại dữ liệu mẫu mặc định (Reset Sample Data)")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            rev = self.manager.reports.revenue_summary()
            occ = self.manager.reports.occupancy_on(date.today())
            pay_sum = self.manager.payments.payment_summary()
            print("\n=== TỔNG HỢP DOANH THU & CÔNG SUẤT PHÒNG ===")
            summary_rows = [
                ["Tổng doanh thu (các đơn hiệu lực)", format_vnd(rev["total_revenue"])],
                ["Doanh thu đã thực hiện (Đang ở / Đã trả)", format_vnd(rev["realized_revenue"])],
                ["Doanh thu đặt trước (Đã xác nhận)", format_vnd(rev["confirmed_revenue"])],
                [
                    "Tổng tiền đã thu qua giao dịch TT",
                    f"{format_vnd(pay_sum['total_collected'])} ({pay_sum['paid_transactions']} GD)",
                ],
                ["Tổng chiết khấu VIP đã giảm", format_vnd(pay_sum["total_discount"])],
                [
                    "Số đơn chưa thanh toán / Công nợ dự kiến",
                    f"{pay_sum['unpaid_bookings_count']} đơn ({format_vnd(pay_sum['unpaid_estimated_total'])})",
                ],
                ["Số đơn hiệu lực / Số đơn đã hủy", f"{rev['active_bookings']} / {rev['cancelled_bookings']}"],
                [
                    f"Công suất phòng hôm nay ({format_date(occ['date'])})",
                    f"{occ['booked_rooms']}/{occ['total_rooms']} phòng ({occ['occupancy_rate']}%)",
                ],
                ["Số phòng trống / Số phòng bảo trì", f"{occ['empty_rooms']} / {occ['maintenance_rooms']}"],
            ]
            print(render_table(["Chỉ tiêu thống kê", "Giá trị"], summary_rows))

            type_rows = [
                [
                    rtype.label,
                    rev["nights_by_type"][rtype],
                    format_vnd(rev["revenue_by_type"][rtype]),
                ]
                for rtype in RoomType
            ]
            print("\nDoanh thu theo loại phòng:")
            print(render_table(["Loại phòng", "Tổng số đêm", "Doanh thu"], type_rows))
        elif sub == "2":
            top = self.manager.reports.top_customers(limit=10)
            rows = [
                [
                    idx,
                    item["customer"].customer_id,
                    item["customer"].full_name,
                    item["customer"].vip_level.label,
                    item["booking_count"],
                    item["total_nights"],
                    format_vnd(item["total_spent"]),
                    format_vnd(item.get("total_paid", 0)),
                ]
                for idx, item in enumerate(top, start=1)
            ]
            print("\nTop khách hàng theo tổng chi tiêu:")
            print(
                render_table(
                    [
                        "Hạng",
                        "Mã KH",
                        "Họ và tên",
                        "VIP",
                        "Số đơn",
                        "Tổng đêm",
                        "Tổng đặt phòng",
                        "Tích lũy đã TT",
                    ],
                    rows,
                )
            )
        elif sub == "3":
            confirm = _prompt("Bạn có chắc chắn muốn nạp lại dữ liệu mẫu? (y/n)", "n").lower()
            if confirm == "y":
                self.manager.reset_with_sample_data()
                print("\n[OK] Đã khởi tạo lại toàn bộ dữ liệu mẫu và lưu ra file JSON.")


def run_demo_walkthrough(manager):
    """Chạy kịch bản minh họa tự động toàn bộ 8 chức năng cốt lõi trên console."""
    today = date.today()
    print("=" * 88)
    print("   MINH HỌA TỰ ĐỘNG CÁC LUỒNG NGHIỆP VỤ & CẤU TRÚC DỮ LIỆU CỐT LÕI")
    print("=" * 88)

    print("\n[1] MẢNG 2 CHIỀU (Matrix2D) — Sơ đồ ma trận phòng theo tầng:")
    print(render_floor_matrix(manager.floor_map(today), today))

    print("\n[2] CÂY NHỊ PHÂN TÌM KIẾM CÂN BẰNG (AVL / BST) — Tìm phòng Suite trống (ngày mai -> +3 ngày):")
    ci, co = today + timedelta(days=1), today + timedelta(days=3)
    avail = manager.find_available_rooms(ci, co, room_type=RoomType.SUITE)
    print(format_rooms_table(avail[:5], manager, ci))

    print("\n[3] MERGE SORT & BINARY SEARCH — Gợi ý phòng gần ngân sách 850.000 đ nhất:")
    suggested = manager.suggest_room_by_budget(850_000)
    print(format_rooms_table([suggested], manager, today))

    print("\n[4] HASH TABLE & LINKED LIST — Tra cứu khách hàng CCCD '001200045678' và lịch sử lưu trú:")
    cust = manager.lookup_customer("001200045678")
    print(format_customers_table([cust], manager.payments))
    print(format_bookings_table(manager.customer_stay_history(cust.customer_id), manager.customers))

    print("\n[5] STACK (NGĂN XẾP) — Xem thao tác hủy đang nằm ở đỉnh Stack và thực hiện Hoàn tác (Undo):")
    print(format_undo_stack_table(manager.undo.history()))
    action, restored = manager.undo_last_cancellation()
    print(f"-> Sau khi gọi undo_last_cancellation(): đơn {action.booking_id} trở lại trạng thái '{restored.status.label}'!")
    print(format_bookings_table([restored], manager.customers))
    # Hủy lại để giữ nguyên trạng thái mẫu
    manager.cancel_booking(restored.booking_id, cancelled_by="STAFF")

    print("\n[6] HÀNG ĐỢI ƯU TIÊN (Max-Heap VIP + LinkedQueue thường) — Thứ tự phục vụ danh sách chờ:")
    print(format_waiting_table(manager.waiting.list_waiting_ordered(), manager.customers))

    print("\n[7] YÊU CẦU DỊCH VỤ NỘI BỘ (Max-Heap theo độ khẩn) — Thứ tự xử lý:")
    print(format_service_requests_table(manager.service_requests.pending_requests_ordered()))

    print("\n[8] QUẢN LÝ THANH TOÁN (HashTable + SinglyLinkedList) — Tính tổng chi phí, thanh toán & tra cứu:")
    bill = manager.calculate_booking_cost("BK00003")
    print(format_bill_detail(bill))
    print("\nDanh sách các giao dịch thanh toán đang lưu trữ:")
    print(format_payments_table(manager.all_payments(), manager.customers))


# ============================================================================
# MODULE: hotel/ui/gui.py
# ============================================================================
"""Giao diện đồ họa Tkinter (GUI) cho Hệ thống Quản lý Đặt phòng Khách sạn."""




STATUS_COLORS = {
    RoomStatus.EMPTY: ("#d4efdf", "#196f3d"),
    RoomStatus.BOOKED: ("#fadbd8", "#922b21"),
    RoomStatus.MAINTENANCE: ("#e5e7e9", "#424949"),
}


class HotelGUI:
    def __init__(self, manager):
        self.manager = manager
        self.root = tk.Tk()
        self.root.title("Hệ thống Quản lý Đặt phòng Khách sạn — CTDL & GT (MI3060)")
        self.root.geometry("1180x740")
        self.selected_room_id = "P101"

        self._build_layout()
        self.refresh_all()

    def run(self):
        self.root.mainloop()

    def _build_layout(self):
        header = ttk.Frame(self.root, padding=(12, 8))
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="HỆ THỐNG QUẢN LÝ ĐẶT PHÒNG KHÁCH SẠN (MI3060)",
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Button(
            header,
            text="Khởi tạo lại dữ liệu mẫu",
            command=self._on_reset_sample,
        ).pack(side=tk.RIGHT, padx=4)
        ttk.Button(
            header,
            text="Làm mới toàn bộ",
            command=self.refresh_all,
        ).pack(side=tk.RIGHT, padx=4)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self.tab_matrix = ttk.Frame(self.notebook, padding=10)
        self.tab_bookings = ttk.Frame(self.notebook, padding=10)
        self.tab_search = ttk.Frame(self.notebook, padding=10)
        self.tab_customers = ttk.Frame(self.notebook, padding=10)
        self.tab_queues = ttk.Frame(self.notebook, padding=10)
        self.tab_payments = ttk.Frame(self.notebook, padding=10)
        self.tab_reports = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.tab_matrix, text="1. Sơ đồ phòng (Matrix 2D)")
        self.notebook.add(self.tab_bookings, text="2. Đặt/Hủy & Hoàn tác (BST + Stack)")
        self.notebook.add(self.tab_search, text="3. Lọc & Sắp xếp (Sort + Binary Search)")
        self.notebook.add(self.tab_customers, text="4. Khách hàng & Lịch sử (Hash + LinkedList)")
        self.notebook.add(self.tab_queues, text="5. Hàng chờ VIP & Dịch vụ (Max-Heap + Queue)")
        self.notebook.add(self.tab_payments, text="6. Quản lý thanh toán (Hash + LinkedList)")
        self.notebook.add(self.tab_reports, text="7. Thống kê & Báo cáo")

        self._build_matrix_tab()
        self._build_bookings_tab()
        self._build_search_tab()
        self._build_customers_tab()
        self._build_queues_tab()
        self._build_payments_tab()
        self._build_reports_tab()

    # -------------------- Tab 1: Sơ đồ ma trận phòng -------------------- #
    def _build_matrix_tab(self):
        top = ttk.Frame(self.tab_matrix)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top, text="Ngày kiểm tra (dd/mm/yyyy):").pack(side=tk.LEFT)
        self.var_map_date = tk.StringVar(value=format_date(date.today()))
        ttk.Entry(top, textvariable=self.var_map_date, width=14).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Xem sơ đồ", command=self.refresh_matrix_tab).pack(side=tk.LEFT)
        ttk.Label(
            top,
            text="   Chú thích:  [Xanh = TRỐNG]   [Đỏ = ĐÃ ĐẶT]   [Xám = BẢO TRÌ]",
            font=("Segoe UI", 9, "italic"),
        ).pack(side=tk.LEFT, padx=12)

        body = ttk.Frame(self.tab_matrix)
        body.pack(fill=tk.BOTH, expand=True)

        self.grid_frame = ttk.LabelFrame(body, text="Ma trận Tầng × Phòng (Truy cập O(1))", padding=8)
        self.grid_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = ttk.LabelFrame(body, text="Chi tiết phòng & Lịch BST", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.lbl_room_detail = ttk.Label(right, text="Chọn một ô phòng...", width=38, justify=tk.LEFT)
        self.lbl_room_detail.pack(anchor=tk.W, pady=(0, 8))
        ttk.Button(
            right,
            text="Đổi trạng thái Bảo trì phòng đang chọn",
            command=self._on_toggle_maintenance,
        ).pack(fill=tk.X, pady=4)

        ttk.Label(right, text="Lịch đặt trên cây BST của phòng:").pack(anchor=tk.W, pady=(10, 4))
        self.tree_room_schedule = ttk.Treeview(
            right,
            columns=("id", "checkin", "checkout", "status"),
            show="headings",
            height=10,
        )
        for col, text, w in (
            ("id", "Mã đơn", 75),
            ("checkin", "Nhận phòng", 85),
            ("checkout", "Trả phòng", 85),
            ("status", "Trạng thái", 90),
        ):
            self.tree_room_schedule.heading(col, text=text)
            self.tree_room_schedule.column(col, width=w, anchor=tk.CENTER)
        self.tree_room_schedule.pack(fill=tk.BOTH, expand=True)

    def refresh_matrix_tab(self):
        try:
            target = parse_date(self.var_map_date.get())
        except ValueError as exc:
            messagebox.showerror("Lỗi ngày", str(exc))
            return

        for child in self.grid_frame.winfo_children():
            child.destroy()

        grid = self.manager.floor_map(target)
        for r_idx, floor_row in enumerate(reversed(grid)):
            floor_no = len(grid) - r_idx
            ttk.Label(
                self.grid_frame,
                text=f"Tầng {floor_no}",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=r_idx, column=0, padx=4, pady=4, sticky="w")
            for c_idx, cell in enumerate(floor_row):
                room = cell["room"]
                status = cell["status"]
                bg, fg = STATUS_COLORS[status]
                btn = tk.Button(
                    self.grid_frame,
                    text=f"{room.room_id}\n{room.room_type.label}\n{status.label}",
                    bg=bg,
                    fg=fg,
                     relief=tk.GROOVE,
                    width=9,
                    height=3,
                    font=("Segoe UI", 8, "bold"),
                    command=lambda rid=room.room_id: self._select_room(rid),
                )
                btn.grid(row=r_idx, column=c_idx + 1, padx=3, pady=3, sticky="nsew")

        self._select_room(self.selected_room_id)

    def _select_room(self, room_id):
        self.selected_room_id = room_id
        room = self.manager.get_room(room_id)
        try:
            target = parse_date(self.var_map_date.get())
        except ValueError:
            target = date.today()
        status = self.manager.bookings.room_status_on(room_id, target)
        info = (
            f"Mã phòng   : {room.room_id} (Tầng {room.floor}, Phòng {room.room_number:02d})\n"
            f"Chỉ số 2D  : Matrix2D[{room.floor - 1}][{room.room_number - 1}]\n"
            f"Loại phòng : {room.room_type.label}\n"
            f"Giá / đêm  : {format_vnd(room.price_per_night)}\n"
            f"Trạng thái : {status.label}\n"
            f"Tiện nghi  : {room.description}"
        )
        self.lbl_room_detail.config(text=info)

        self.tree_room_schedule.delete(*self.tree_room_schedule.get_children())
        for b in self.manager.bookings.bookings_for_room(room_id):
            self.tree_room_schedule.insert(
                "",
                tk.END,
                values=(b.booking_id, format_date(b.check_in), format_date(b.check_out), b.status.label),
            )

    def _on_toggle_maintenance(self):
        try:
            room = self.manager.get_room(self.selected_room_id)
            self.manager.set_room_maintenance(room.room_id, not room.under_maintenance)
            self.refresh_all()
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    # ------------- Tab 2: Đặt phòng, Hủy & Hoàn tác (BST + Stack) ------- #
    def _build_bookings_tab(self):
        form = ttk.LabelFrame(self.tab_bookings, text="Tạo đơn đặt phòng mới", padding=8)
        form.pack(fill=tk.X, pady=(0, 8))

        today = date.today()
        self.var_bk_cust = tk.StringVar(value="KH001")
        self.var_bk_room = tk.StringVar(value="P103")
        self.var_bk_in = tk.StringVar(value=format_date(today + timedelta(days=1)))
        self.var_bk_out = tk.StringVar(value=format_date(today + timedelta(days=3)))

        ttk.Label(form, text="Mã KH/CCCD/SĐT:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.var_bk_cust, width=15).grid(row=0, column=1, padx=4, pady=4)
        ttk.Label(form, text="Mã phòng:").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.var_bk_room, width=10).grid(row=0, column=3, padx=4, pady=4)
        ttk.Label(form, text="Nhận phòng:").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.var_bk_in, width=12).grid(row=0, column=5, padx=4, pady=4)
        ttk.Label(form, text="Trả phòng:").grid(row=0, column=6, padx=4, pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.var_bk_out, width=12).grid(row=0, column=7, padx=4, pady=4)
        ttk.Button(form, text="Đặt phòng (BST O(log n))", command=self._on_create_booking).grid(
            row=0, column=8, padx=8, pady=4
        )

        actions = ttk.Frame(self.tab_bookings)
        actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(actions, text="Nhận phòng (Check-in)", command=self._on_checkin).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Trả phòng (Check-out)", command=self._on_checkout).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Hủy đơn đã chọn (Push Stack)", command=self._on_cancel_booking).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(actions, text="Hoàn tác lệnh hủy gần nhất (Pop Stack O(1))", command=self._on_undo_cancel).pack(
            side=tk.LEFT, padx=12
        )
        self.lbl_undo_top = ttk.Label(actions, text="", font=("Segoe UI", 9, "bold"))
        self.lbl_undo_top.pack(side=tk.RIGHT, padx=6)

        cols = ("id", "cust", "name", "room", "in", "out", "nights", "total", "status")
        self.tree_bookings = ttk.Treeview(self.tab_bookings, columns=cols, show="headings", height=16)
        headings = [
            ("id", "Mã đơn", 85),
            ("cust", "Mã KH", 70),
            ("name", "Tên khách hàng", 160),
            ("room", "Phòng", 65),
            ("in", "Nhận phòng", 95),
            ("out", "Trả phòng", 95),
            ("nights", "Số đêm", 65),
            ("total", "Tổng tiền", 115),
            ("status", "Trạng thái", 110),
        ]
        for col, text, w in headings:
            self.tree_bookings.heading(col, text=text)
            self.tree_bookings.column(col, width=w, anchor=tk.CENTER)
        self.tree_bookings.pack(fill=tk.BOTH, expand=True)

    def refresh_bookings_tab(self):
        self.tree_bookings.delete(*self.tree_bookings.get_children())
        bookings = merge_sort(self.manager.bookings.all_bookings(), key=lambda b: b.booking_id)
        for b in bookings:
            try:
                cname = self.manager.customers.get_customer(b.customer_id).full_name
            except Exception:
                cname = "-"
            self.tree_bookings.insert(
                "",
                tk.END,
                iid=b.booking_id,
                values=(
                    b.booking_id,
                    b.customer_id,
                    cname,
                    b.room_id,
                    format_date(b.check_in),
                    format_date(b.check_out),
                    b.num_nights,
                    format_vnd(b.total_price),
                    b.status.label,
                ),
            )
        top_undo = self.manager.undo.peek_last_cancellation()
        if top_undo is None:
            self.lbl_undo_top.config(text="Đỉnh Undo Stack: (Trống)")
        else:
            self.lbl_undo_top.config(
                text=f"Đỉnh Undo Stack: {top_undo.booking_id} (Phòng {top_undo.room_id}) — Sẵn sàng hoàn tác"
            )

    def _selected_booking_id(self):
        sel = self.tree_bookings.selection()
        if not sel:
            raise HotelError("Vui lòng chọn một đơn đặt phòng trong bảng")
        return sel[0]

    def _on_create_booking(self):
        try:
            cust = self.manager.lookup_customer(self.var_bk_cust.get())
            old_vip = cust.vip_level
            ci = parse_date(self.var_bk_in.get())
            co = parse_date(self.var_bk_out.get())
            booking = self.manager.book_room(cust.customer_id, self.var_bk_room.get(), ci, co)
            new_vip = self.manager.customers.get_customer(cust.customer_id).vip_level
            self.refresh_all()
            upgrade_msg = ""
            if new_vip > old_vip:
                total_paid = self.manager.customer_total_paid(cust.customer_id)
                upgrade_msg = (
                    f"\n\n★ Khách hàng {cust.full_name} đạt tích lũy {format_vnd(total_paid)} "
                    f"và được TỰ ĐỘNG NÂNG HẠNG VIP: {old_vip.label} -> {new_vip.label}!"
                )
            messagebox.showinfo(
                "Thành công",
                f"Đã tạo đơn {booking.booking_id} cho phòng {booking.room_id}{upgrade_msg}",
            )
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Không thể đặt phòng", str(exc))

    def _on_checkin(self):
        try:
            bid = self._selected_booking_id()
            self.manager.check_in(bid)
            self.refresh_all()
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_checkout(self):
        try:
            bid = self._selected_booking_id()
            self.manager.check_out(bid)
            self.refresh_all()
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_cancel_booking(self):
        try:
            bid = self._selected_booking_id()
            action, _ = self.manager.cancel_booking(bid, cancelled_by="STAFF")
            self.refresh_all()
            messagebox.showinfo(
                "Đã hủy đơn",
                f"Đã hủy đơn {action.booking_id} và đẩy vào đỉnh ngăn xếp Undo Stack.",
            )
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_undo_cancel(self):
        try:
            action, booking = self.manager.undo_last_cancellation()
            self.refresh_all()
            messagebox.showinfo(
                "Hoàn tác thành công",
                f"Đã khôi phục đơn {action.booking_id} (Phòng {booking.room_id}) về trạng thái '{booking.status.label}'.",
            )
        except HotelError as exc:
            messagebox.showerror("Không thể hoàn tác", str(exc))

    # -------- Tab 3: Lọc, Sắp xếp & Tìm kiếm nhị phân theo giá ---------- #
    def _build_search_tab(self):
        ctrl = ttk.LabelFrame(
            self.tab_search,
            text="Bộ lọc khoảng ngày (BST), Khoảng giá (Binary Search) & Sắp xếp (Merge/Quick Sort)",
            padding=8,
        )
        ctrl.pack(fill=tk.X, pady=(0, 8))

        today = date.today()
        self.var_s_in = tk.StringVar(value=format_date(today + timedelta(days=1)))
        self.var_s_out = tk.StringVar(value=format_date(today + timedelta(days=3)))
        self.var_s_type = tk.StringVar(value="ALL")
        self.var_s_min = tk.StringVar(value="0")
        self.var_s_max = tk.StringVar(value="3000000")
        self.var_s_algo = tk.StringVar(value="merge")
        self.var_s_budget = tk.StringVar(value="850000")

        ttk.Label(ctrl, text="Nhận:").grid(row=0, column=0, padx=3, pady=3)
        ttk.Entry(ctrl, textvariable=self.var_s_in, width=11).grid(row=0, column=1, padx=3, pady=3)
        ttk.Label(ctrl, text="Trả:").grid(row=0, column=2, padx=3, pady=3)
        ttk.Entry(ctrl, textvariable=self.var_s_out, width=11).grid(row=0, column=3, padx=3, pady=3)
        ttk.Label(ctrl, text="Loại:").grid(row=0, column=4, padx=3, pady=3)
        ttk.Combobox(
            ctrl,
            textvariable=self.var_s_type,
            values=("ALL", "SINGLE", "DOUBLE", "SUITE"),
            width=9,
            state="readonly",
        ).grid(row=0, column=5, padx=3, pady=3)
        ttk.Label(ctrl, text="Giá từ:").grid(row=0, column=6, padx=3, pady=3)
        ttk.Entry(ctrl, textvariable=self.var_s_min, width=9).grid(row=0, column=7, padx=3, pady=3)
        ttk.Label(ctrl, text="đến:").grid(row=0, column=8, padx=3, pady=3)
        ttk.Entry(ctrl, textvariable=self.var_s_max, width=9).grid(row=0, column=9, padx=3, pady=3)
        ttk.Combobox(
            ctrl,
            textvariable=self.var_s_algo,
            values=("merge", "quick"),
            width=7,
            state="readonly",
        ).grid(row=0, column=10, padx=3, pady=3)
        ttk.Button(ctrl, text="Tìm phòng trống", command=self._on_search_available).grid(
            row=0, column=11, padx=6, pady=3
        )

        budget_row = ttk.Frame(self.tab_search)
        budget_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(budget_row, text="Ngân sách dự kiến (VND/đêm):").pack(side=tk.LEFT)
        ttk.Entry(budget_row, textvariable=self.var_s_budget, width=12).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            budget_row,
            text="Tìm 1 phòng có giá gần ngân sách nhất (Binary Search O(log R))",
            command=self._on_suggest_budget,
        ).pack(side=tk.LEFT)

        cols = ("id", "floor", "num", "type", "price", "desc")
        self.tree_search = ttk.Treeview(self.tab_search, columns=cols, show="headings", height=16)
        for col, text, w in (
            ("id", "Mã phòng", 80),
            ("floor", "Tầng", 60),
            ("num", "Số phòng", 70),
            ("type", "Loại phòng", 90),
            ("price", "Giá / đêm", 120),
            ("desc", "Mô tả tiện nghi", 380),
        ):
            self.tree_search.heading(col, text=text)
            self.tree_search.column(col, width=w, anchor=tk.CENTER if col != "desc" else tk.W)
        self.tree_search.pack(fill=tk.BOTH, expand=True)

    def _on_search_available(self):
        try:
            ci = parse_date(self.var_s_in.get())
            co = parse_date(self.var_s_out.get())
            t_val = self.var_s_type.get()
            rtype = None if t_val == "ALL" else RoomType(t_val)
            min_p = int(self.var_s_min.get() or 0)
            max_p = int(self.var_s_max.get() or 10_000_000)
            rooms = self.manager.find_available_rooms(
                ci, co, room_type=rtype, min_price=min_p, max_price=max_p, algorithm=self.var_s_algo.get()
            )
            self._populate_search_tree(rooms)
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi tìm kiếm", str(exc))

    def _on_suggest_budget(self):
        try:
            budget = int(self.var_s_budget.get())
            t_val = self.var_s_type.get()
            rtype = None if t_val == "ALL" else RoomType(t_val)
            room = self.manager.suggest_room_by_budget(budget, room_type=rtype)
            self._populate_search_tree([room] if room else [])
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _populate_search_tree(self, rooms):
        self.tree_search.delete(*self.tree_search.get_children())
        for r in rooms:
            self.tree_search.insert(
                "",
                tk.END,
                values=(
                    r.room_id,
                    r.floor,
                    f"{r.room_number:02d}",
                    r.room_type.label,
                    format_vnd(r.price_per_night),
                    r.description,
                ),
            )

    # --------- Tab 4: Khách hàng & Lịch sử (HashTable + LinkedList) ----- #
    def _build_customers_tab(self):
        top = ttk.LabelFrame(self.tab_customers, text="Đăng ký & Tra cứu Bảng băm O(1)", padding=8)
        top.pack(fill=tk.X, pady=(0, 8))

        self.var_c_name = tk.StringVar()
        self.var_c_cccd = tk.StringVar()
        self.var_c_phone = tk.StringVar()
        self.var_c_vip = tk.StringVar(value="0")
        self.var_c_lookup = tk.StringVar()

        ttk.Label(top, text="Họ tên:").grid(row=0, column=0, padx=3, pady=3)
        ttk.Entry(top, textvariable=self.var_c_name, width=18).grid(row=0, column=1, padx=3, pady=3)
        ttk.Label(top, text="CCCD:").grid(row=0, column=2, padx=3, pady=3)
        ttk.Entry(top, textvariable=self.var_c_cccd, width=14).grid(row=0, column=3, padx=3, pady=3)
        ttk.Label(top, text="SĐT:").grid(row=0, column=4, padx=3, pady=3)
        ttk.Entry(top, textvariable=self.var_c_phone, width=13).grid(row=0, column=5, padx=3, pady=3)
        ttk.Label(top, text="VIP (0..3):").grid(row=0, column=6, padx=3, pady=3)
        ttk.Combobox(top, textvariable=self.var_c_vip, values=("0", "1", "2", "3"), width=4, state="readonly").grid(
            row=0, column=7, padx=3, pady=3
        )
        ttk.Button(top, text="Đăng ký KH", command=self._on_register_customer).grid(row=0, column=8, padx=6, pady=3)

        ttk.Label(top, text="Tra cứu O(1) (Mã/CCCD/SĐT):").grid(row=1, column=0, columnspan=2, padx=3, pady=4, sticky="w")
        ttk.Entry(top, textvariable=self.var_c_lookup, width=20).grid(row=1, column=2, columnspan=2, padx=3, pady=4, sticky="w")
        ttk.Button(top, text="Tra cứu Hash Table", command=self._on_lookup_customer).grid(row=1, column=4, padx=4, pady=4, sticky="w")
        ttk.Button(top, text="Đặt VIP KH chọn", command=self._on_update_customer_vip).grid(row=1, column=5, padx=4, pady=4, sticky="w")
        ttk.Label(
            top,
            text="Tự động lên VIP theo tổng tiền đã TT: >= 3tr Silver (-3%) | >= 8tr Gold (-5%) | >= 15tr Platinum (-10%)",
            font=("Segoe UI", 8, "italic"),
        ).grid(row=1, column=6, columnspan=3, padx=6, pady=4, sticky="w")

        panes = ttk.Frame(self.tab_customers)
        panes.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(panes, text="Danh sách khách hàng (Chọn 1 khách để xem DSLK lịch sử)", padding=6)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_customers = ttk.Treeview(
            left,
            columns=("id", "name", "cccd", "phone", "vip", "paid", "next_vip", "count"),
            show="headings",
            height=14,
        )
        for col, text, w in (
            ("id", "Mã KH", 60),
            ("name", "Họ và tên", 135),
            ("cccd", "Số CCCD", 95),
            ("phone", "Điện thoại", 90),
            ("vip", "Hạng VIP", 80),
            ("paid", "Tích lũy đã TT", 95),
            ("next_vip", "Tiến độ nâng VIP", 145),
            ("count", "Đơn", 45),
        ):
            self.tree_customers.heading(col, text=text)
            self.tree_customers.column(col, width=w, anchor=tk.CENTER)
        self.tree_customers.pack(fill=tk.BOTH, expand=True)
        self.tree_customers.bind("<<TreeviewSelect>>", self._on_customer_selected)

        right = ttk.LabelFrame(panes, text="Lịch sử lưu trú (SinglyLinkedList — Mới nhất ở đầu)", padding=6)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self.tree_history = ttk.Treeview(
            right,
            columns=("id", "room", "in", "out", "total", "status"),
            show="headings",
            height=14,
        )
        for col, text, w in (
            ("id", "Mã đơn", 80),
            ("room", "Phòng", 60),
            ("in", "Nhận phòng", 85),
            ("out", "Trả phòng", 85),
            ("total", "Tổng tiền", 100),
            ("status", "Trạng thái", 95),
        ):
            self.tree_history.heading(col, text=text)
            self.tree_history.column(col, width=w, anchor=tk.CENTER)
        self.tree_history.pack(fill=tk.BOTH, expand=True)

    def refresh_customers_tab(self):
        self.tree_customers.delete(*self.tree_customers.get_children())
        for c in merge_sort(self.manager.customers.all_customers(), key=lambda x: x.customer_id):
            prog = self.manager.customer_vip_progress(c.customer_id)
            if prog["next_vip"] is not None:
                next_txt = f"Còn {format_vnd(prog['amount_to_next_vip'])} -> {prog['next_vip'].label}"
            else:
                next_txt = "Đạt đỉnh (Platinum)"
            self.tree_customers.insert(
                "",
                tk.END,
                iid=c.customer_id,
                values=(
                    c.customer_id,
                    c.full_name,
                    c.cccd,
                    c.phone,
                    f"{c.vip_level.label} ({int(c.vip_level)})",
                    format_vnd(prog["total_paid"]),
                    next_txt,
                    len(c.history),
                ),
            )

    def _on_customer_selected(self, _event=None):
        sel = self.tree_customers.selection()
        if not sel:
            return
        cid = sel[0]
        self.tree_history.delete(*self.tree_history.get_children())
        for b in self.manager.customer_stay_history(cid):
            self.tree_history.insert(
                "",
                tk.END,
                values=(
                    b.booking_id,
                    b.room_id,
                    format_date(b.check_in),
                    format_date(b.check_out),
                    format_vnd(b.total_price),
                    b.status.label,
                ),
            )

    def _on_register_customer(self):
        try:
            cust = self.manager.register_customer(
                self.var_c_name.get(),
                self.var_c_cccd.get(),
                self.var_c_phone.get(),
                VipLevel(int(self.var_c_vip.get())),
            )
            self.refresh_all()
            messagebox.showinfo("Thành công", f"Đã đăng ký khách hàng {cust.customer_id} ({cust.full_name})")
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_lookup_customer(self):
        try:
            cust = self.manager.lookup_customer(self.var_c_lookup.get())
            self.tree_customers.selection_set(cust.customer_id)
            self.tree_customers.see(cust.customer_id)
            self._on_customer_selected()
        except HotelError as exc:
            messagebox.showerror("Không tìm thấy", str(exc))

    def _on_update_customer_vip(self):
        sel = self.tree_customers.selection()
        ident = sel[0] if sel else self.var_c_lookup.get().strip()
        if not ident:
            messagebox.showerror("Lỗi", "Vui lòng chọn một khách hàng trong bảng hoặc nhập Mã KH/CCCD/SĐT")
            return
        try:
            cust = self.manager.lookup_customer(ident)
            new_vip = VipLevel(int(self.var_c_vip.get()))
            self.manager.set_customer_vip(cust.customer_id, new_vip)
            self.refresh_all()
            messagebox.showinfo(
                "Đã cập nhật VIP",
                f"Khách hàng {cust.customer_id} ({cust.full_name}) đã được cập nhật lên hạng VIP: {new_vip.label} ({int(new_vip)})",
            )
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi", str(exc))

    # --------- Tab 5: Hàng chờ VIP & Yêu cầu dịch vụ (Max-Heap) --------- #
    def _build_queues_tab(self):
        panes = ttk.Frame(self.tab_queues)
        panes.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(panes, text="Danh sách chờ khi hết phòng (Max-Heap VIP + Queue Thường)", padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        w_btns = ttk.Frame(left)
        w_btns.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(
            w_btns,
            text="Tự động phân phòng cho DS chờ",
            command=self._on_process_waiting,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            w_btns,
            text="Lấy khách ưu tiên cao nhất (Pop)",
            command=self._on_pop_waiting,
        ).pack(side=tk.LEFT, padx=3)

        self.tree_waiting = ttk.Treeview(
            left,
            columns=("id", "cust", "vip", "type", "in", "out", "ds"),
            show="headings",
            height=15,
        )
        for col, text, w in (
            ("id", "Mã chờ", 65),
            ("cust", "Khách hàng", 130),
            ("vip", "Ưu tiên", 80),
            ("type", "Loại", 60),
            ("in", "Nhận", 80),
            ("out", "Trả", 80),
            ("ds", "Cấu trúc", 105),
        ):
            self.tree_waiting.heading(col, text=text)
            self.tree_waiting.column(col, width=w, anchor=tk.CENTER)
        self.tree_waiting.pack(fill=tk.BOTH, expand=True)

        right = ttk.LabelFrame(panes, text="Yêu cầu dịch vụ nội bộ (Max-Heap theo độ khẩn)", padding=8)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        sr_form = ttk.Frame(right)
        sr_form.pack(fill=tk.X, pady=(0, 6))
        self.var_sr_room = tk.StringVar(value="P101")
        self.var_sr_type = tk.StringVar(value="FOOD")
        self.var_sr_urg = tk.StringVar(value="2")
        self.var_sr_note = tk.StringVar(value="Phục vụ tại phòng")

        ttk.Label(sr_form, text="Phòng:").pack(side=tk.LEFT)
        ttk.Entry(sr_form, textvariable=self.var_sr_room, width=6).pack(side=tk.LEFT, padx=3)
        ttk.Combobox(
            sr_form,
            textvariable=self.var_sr_type,
            values=("CLEANING", "FOOD", "MEDICAL", "OTHER"),
            width=9,
            state="readonly",
        ).pack(side=tk.LEFT, padx=3)
        ttk.Combobox(
            sr_form,
            textvariable=self.var_sr_urg,
            values=("1", "2", "3"),
            width=3,
            state="readonly",
        ).pack(side=tk.LEFT, padx=3)
        ttk.Entry(sr_form, textvariable=self.var_sr_note, width=16).pack(side=tk.LEFT, padx=3)
        ttk.Button(sr_form, text="Gửi YC", command=self._on_submit_sr).pack(side=tk.LEFT, padx=3)
        ttk.Button(sr_form, text="Xử lý khẩn nhất", command=self._on_process_sr).pack(side=tk.LEFT, padx=3)

        self.tree_sr = ttk.Treeview(
            right,
            columns=("id", "room", "type", "urgency", "note"),
            show="headings",
            height=15,
        )
        for col, text, w in (
            ("id", "Mã YC", 65),
            ("room", "Phòng", 60),
            ("type", "Dịch vụ", 85),
            ("urgency", "Độ khẩn", 95),
            ("note", "Ghi chú", 190),
        ):
            self.tree_sr.heading(col, text=text)
            self.tree_sr.column(col, width=w, anchor=tk.CENTER if col != "note" else tk.W)
        self.tree_sr.pack(fill=tk.BOTH, expand=True)

    def refresh_queues_tab(self):
        self.tree_waiting.delete(*self.tree_waiting.get_children())
        for e in self.manager.waiting.list_waiting_ordered():
            try:
                cust = self.manager.customers.get_customer(e.customer_id)
                cname = f"{cust.customer_id} - {cust.full_name}"
                vip_txt = f"{cust.vip_level.label} ({e.priority})"
            except Exception:
                cname = e.customer_id
                vip_txt = str(e.priority)
            ds = "Max-Heap (VIP)" if e.priority > 0 else "LinkedQueue"
            self.tree_waiting.insert(
                "",
                tk.END,
                values=(
                    e.entry_id,
                    cname,
                    vip_txt,
                    e.room_type.label,
                    format_date(e.check_in),
                    format_date(e.check_out),
                    ds,
                ),
            )

        self.tree_sr.delete(*self.tree_sr.get_children())
        for req in self.manager.service_requests.pending_requests_ordered():
            self.tree_sr.insert(
                "",
                tk.END,
                values=(
                    req.request_id,
                    req.room_id,
                    req.service_type.label,
                    f"{req.urgency.label} ({int(req.urgency)})",
                    req.note,
                ),
            )

    def _on_process_waiting(self):
        fulfilled = self.manager.process_waiting_list()
        self.refresh_all()
        if not fulfilled:
            messagebox.showinfo("Danh sách chờ", "Chưa có phòng trống phù hợp với nhu cầu đang chờ.")
        else:
            msg = "\n".join(f"- {e.entry_id} ({e.customer_id}) -> Đơn {b.booking_id} (Phòng {b.room_id})" for e, b in fulfilled)
            messagebox.showinfo("Đã phân phòng", f"Đã tự động xếp phòng:\n{msg}")

    def _on_pop_waiting(self):
        try:
            entry = self.manager.pop_next_waiting()
            self.refresh_all()
            messagebox.showinfo("Pop hàng chờ", f"Đã lấy mục {entry.entry_id} (Khách {entry.customer_id}, ưu tiên {entry.priority})")
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_submit_sr(self):
        try:
            self.manager.submit_service_request(
                room_id=self.var_sr_room.get(),
                service_type=ServiceType(self.var_sr_type.get()),
                urgency=UrgencyLevel(int(self.var_sr_urg.get())),
                note=self.var_sr_note.get(),
            )
            self.refresh_queues_tab()
            self.refresh_payments_tab()
            self.refresh_reports_tab()
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_process_sr(self):
        try:
            req = self.manager.process_next_service_request()
            self.refresh_queues_tab()
            self.refresh_payments_tab()
            self.refresh_reports_tab()
            messagebox.showinfo(
                "Đã xử lý dịch vụ",
                f"Đã xử lý yêu cầu {req.request_id} tại phòng {req.room_id} ({req.service_type.label} - {req.urgency.label})",
            )
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    # -------- Tab 6: Quản lý thanh toán (HashTable + SinglyLinkedList) --- #
    def _build_payments_tab(self):
        top = ttk.Frame(self.tab_payments)
        top.pack(fill=tk.X, pady=(0, 8))

        left_ctrl = ttk.LabelFrame(
            top,
            text="1. Tính tổng chi phí & Xử lý thanh toán",
            padding=8,
        )
        left_ctrl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.var_pay_booking = tk.StringVar(value="BK00003")
        self.var_pay_extra = tk.StringVar(value="0")
        self.var_pay_method = tk.StringVar(value="BANK_TRANSFER")
        self.var_pay_note = tk.StringVar(value="Thanh toán hóa đơn lưu trú")
        self.var_pay_auto_checkout = tk.BooleanVar(value=False)
        self.var_pay_lookup = tk.StringVar()

        ttk.Label(left_ctrl, text="Mã đơn đặt phòng:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        self.cmb_pay_booking = ttk.Combobox(left_ctrl, textvariable=self.var_pay_booking, width=13)
        self.cmb_pay_booking.grid(row=0, column=1, padx=4, pady=4, sticky="w")
        self.cmb_pay_booking.bind("<<ComboboxSelected>>", lambda _e: self._on_calculate_bill())

        ttk.Label(left_ctrl, text="Phụ phí (VND):").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        ttk.Entry(left_ctrl, textvariable=self.var_pay_extra, width=11).grid(row=0, column=3, padx=4, pady=4, sticky="w")

        ttk.Label(left_ctrl, text="Phương thức:").grid(row=1, column=0, padx=4, pady=4, sticky="w")
        ttk.Combobox(
            left_ctrl,
            textvariable=self.var_pay_method,
            values=("CASH", "BANK_TRANSFER", "CARD", "E_WALLET"),
            width=15,
            state="readonly",
        ).grid(row=1, column=1, padx=4, pady=4, sticky="w")

        ttk.Label(left_ctrl, text="Ghi chú:").grid(row=1, column=2, padx=4, pady=4, sticky="w")
        ttk.Entry(left_ctrl, textvariable=self.var_pay_note, width=24).grid(row=1, column=3, padx=4, pady=4, sticky="w")

        btn_row = ttk.Frame(left_ctrl)
        btn_row.grid(row=2, column=0, columnspan=4, pady=(6, 2), sticky="w")
        ttk.Button(
            btn_row,
            text="Tính tổng chi phí (Xem hóa đơn)",
            command=self._on_calculate_bill,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            btn_row,
            text="Xử lý thanh toán & Lưu giao dịch",
            command=self._on_process_payment,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            btn_row,
            text="Hoàn tiền (Refund) GD đã chọn",
            command=self._on_refund_payment,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Checkbutton(
            btn_row,
            text="Tự động Check-out",
            variable=self.var_pay_auto_checkout,
        ).pack(side=tk.LEFT, padx=6)

        search_row = ttk.Frame(left_ctrl)
        search_row.grid(row=3, column=0, columnspan=4, pady=(6, 2), sticky="w")
        ttk.Label(search_row, text="Tra cứu O(1) (Mã GD/Đơn/KH/SĐT/Phòng):").pack(side=tk.LEFT, padx=2)
        ttk.Entry(search_row, textvariable=self.var_pay_lookup, width=18).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            search_row,
            text="Tra cứu thanh toán",
            command=self._on_lookup_payments,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            search_row,
            text="Hiện tất cả GD",
            command=self.refresh_payments_tab,
        ).pack(side=tk.LEFT, padx=3)

        right_bill = ttk.LabelFrame(
            top,
            text="Bảng kê chi tiết tổng chi phí (Hóa đơn)",
            padding=8,
        )
        right_bill.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self.txt_bill_detail = tk.Text(right_bill, font=("Consolas", 9), height=10, width=58)
        self.txt_bill_detail.pack(fill=tk.BOTH, expand=True)

        bottom = ttk.LabelFrame(
            self.tab_payments,
            text="Danh sách giao dịch thanh toán đã lưu trữ (HashTable + SinglyLinkedList)",
            padding=6,
        )
        bottom.pack(fill=tk.BOTH, expand=True)
        cols = (
            "pid",
            "bid",
            "cust",
            "room",
            "room_cost",
            "srv_cost",
            "discount",
            "total",
            "method",
            "date",
            "status",
            "note",
        )
        self.tree_payments = ttk.Treeview(bottom, columns=cols, show="headings", height=12)
        for col, text, w in (
            ("pid", "Mã GD", 75),
            ("bid", "Mã đơn", 75),
            ("cust", "Khách hàng", 145),
            ("room", "Phòng", 55),
            ("room_cost", "Tiền phòng", 95),
            ("srv_cost", "Phí DV+Phụ phí", 95),
            ("discount", "Giảm VIP", 85),
            ("total", "Tổng thanh toán", 105),
            ("method", "Phương thức", 100),
            ("date", "Ngày TT", 80),
            ("status", "Trạng thái", 95),
            ("note", "Ghi chú", 170),
        ):
            self.tree_payments.heading(col, text=text)
            self.tree_payments.column(col, width=w, anchor=tk.CENTER if col != "note" else tk.W)
        self.tree_payments.pack(fill=tk.BOTH, expand=True)
        self.tree_payments.bind("<<TreeviewSelect>>", self._on_payment_selected)

    def _populate_payments_tree(self, payments):
        self.tree_payments.delete(*self.tree_payments.get_children())
        for tx in payments:
            try:
                cust = self.manager.customers.get_customer(tx.customer_id)
                cname = f"{cust.customer_id} - {cust.full_name}"
            except Exception:
                cname = tx.customer_id
            self.tree_payments.insert(
                "",
                tk.END,
                iid=tx.payment_id,
                values=(
                    tx.payment_id,
                    tx.booking_id,
                    cname,
                    tx.room_id,
                    format_vnd(tx.room_cost),
                    format_vnd(tx.service_cost + tx.extra_fee),
                    format_vnd(tx.discount_amount),
                    format_vnd(tx.total_amount),
                    tx.payment_method.label,
                    format_date(tx.paid_at),
                    tx.status.label,
                    tx.note,
                ),
            )

    def refresh_payments_tab(self):
        all_bks = merge_sort(self.manager.bookings.all_bookings(), key=lambda b: b.booking_id)
        self.cmb_pay_booking["values"] = [b.booking_id for b in all_bks]
        self._populate_payments_tree(self.manager.all_payments())
        try:
            bid = self.var_pay_booking.get().strip()
            if bid:
                bill = self.manager.calculate_booking_cost(bid, extra_fee=int(self.var_pay_extra.get() or 0))
                self.txt_bill_detail.delete("1.0", tk.END)
                self.txt_bill_detail.insert(tk.END, format_bill_detail(bill))
        except Exception:
            pass

    def _on_payment_selected(self, _event=None):
        sel = self.tree_payments.selection()
        if not sel:
            return
        try:
            tx = self.manager.get_payment(sel[0])
            self.var_pay_booking.set(tx.booking_id)
            self.var_pay_extra.set(str(tx.extra_fee))
            self._on_calculate_bill()
        except Exception:
            pass

    def _on_calculate_bill(self):
        try:
            bid = self.var_pay_booking.get().strip()
            extra = int(self.var_pay_extra.get() or 0)
            bill = self.manager.calculate_booking_cost(bid, extra_fee=extra)
            self.txt_bill_detail.delete("1.0", tk.END)
            self.txt_bill_detail.insert(tk.END, format_bill_detail(bill))
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi tính chi phí", str(exc))

    def _on_process_payment(self):
        try:
            bid = self.var_pay_booking.get().strip()
            extra = int(self.var_pay_extra.get() or 0)
            method = PaymentMethod(self.var_pay_method.get())
            note = self.var_pay_note.get()
            booking_before = self.manager.bookings.get_booking(bid)
            cust_before = self.manager.customers.get_customer(booking_before.customer_id)
            old_vip = cust_before.vip_level
            tx = self.manager.process_payment(
                booking_id=bid,
                payment_method=method,
                extra_fee=extra,
                note=note,
                auto_check_out=self.var_pay_auto_checkout.get(),
            )
            new_vip = self.manager.customers.get_customer(tx.customer_id).vip_level
            total_paid = self.manager.customer_total_paid(tx.customer_id)
            self.refresh_all()
            upgrade_msg = ""
            if new_vip > old_vip:
                upgrade_msg = (
                    f"\n\n★ Chúc mừng! Khách hàng {cust_before.full_name} đạt tích lũy "
                    f"{format_vnd(total_paid)} và được TỰ ĐỘNG NÂNG HẠNG VIP: {old_vip.label} -> {new_vip.label}!"
                )
            messagebox.showinfo(
                "Thanh toán thành công",
                f"Đã xử lý và lưu giao dịch {tx.payment_id} cho đơn {tx.booking_id}\n"
                f"Tổng thanh toán: {format_vnd(tx.total_amount)} ({tx.payment_method.label})"
                f"{upgrade_msg}",
            )
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Không thể thanh toán", str(exc))

    def _on_refund_payment(self):
        sel = self.tree_payments.selection()
        target = sel[0] if sel else self.var_pay_booking.get().strip()
        if not target:
            messagebox.showerror("Lỗi", "Vui lòng chọn một giao dịch trong bảng để hoàn tiền")
            return
        try:
            tx = self.manager.refund_payment(target, reason="Hoàn tiền qua GUI")
            self.refresh_all()
            messagebox.showinfo("Đã hoàn tiền", f"Giao dịch {tx.payment_id} đã chuyển sang trạng thái '{tx.status.label}'.")
        except HotelError as exc:
            messagebox.showerror("Lỗi hoàn tiền", str(exc))

    def _on_lookup_payments(self):
        try:
            q = self.var_pay_lookup.get().strip()
            found = self.manager.lookup_payments(q)
            self._populate_payments_tree(found)
        except HotelError as exc:
            messagebox.showerror("Không tìm thấy", str(exc))

    # -------------------- Tab 7: Thống kê & Báo cáo --------------------- #
    def _build_reports_tab(self):
        self.txt_report = tk.Text(self.tab_reports, font=("Consolas", 10), height=28)
        self.txt_report.pack(fill=tk.BOTH, expand=True)

    def refresh_reports_tab(self):
        rev = self.manager.reports.revenue_summary()
        occ = self.manager.reports.occupancy_on(date.today())
        top = self.manager.reports.top_customers(limit=10)
        pay_sum = self.manager.payments.payment_summary()

        lines = [
            "=== BÁO CÁO THỐNG KÊ DOANH THU, THANH TOÁN & TỶ LỆ LẤP ĐẦY PHÒNG ===",
            "",
            f"- Tổng doanh thu (các đơn hiệu lực)       : {format_vnd(rev['total_revenue'])}",
            f"- Doanh thu đã thực hiện (Đang ở/Đã trả)  : {format_vnd(rev['realized_revenue'])}",
            f"- Doanh thu đặt trước (Đã xác nhận)       : {format_vnd(rev['confirmed_revenue'])}",
            f"- Tổng tiền đã thu qua giao dịch TT       : {format_vnd(pay_sum['total_collected'])} ({pay_sum['paid_transactions']} GD)",
            f"- Tổng chiết khấu VIP đã giảm             : {format_vnd(pay_sum['total_discount'])}",
            f"- Số đơn chưa thanh toán / Công nợ dự kiến: {pay_sum['unpaid_bookings_count']} đơn ({format_vnd(pay_sum['unpaid_estimated_total'])})",
            f"- Số đơn hiệu lực / Số đơn đã hủy         : {rev['active_bookings']} / {rev['cancelled_bookings']}",
            f"- Tỷ lệ lấp đầy hôm nay ({format_date(occ['date'])})   : {occ['booked_rooms']}/{occ['total_rooms']} phòng ({occ['occupancy_rate']}%)",
            f"- Số phòng trống / bảo trì                : {occ['empty_rooms']} trống / {occ['maintenance_rooms']} bảo trì",
            "",
            "--- Doanh thu theo loại phòng ---",
        ]
        for rtype in RoomType:
            lines.append(
                f"  + Phòng {rtype.label:<6}: {rev['nights_by_type'][rtype]:>3} đêm  |  {format_vnd(rev['revenue_by_type'][rtype])}"
            )
        lines.append("")
        lines.append("--- Top khách hàng chi tiêu cao nhất (Sắp xếp bằng Merge Sort) ---")
        for idx, item in enumerate(top, start=1):
            c = item["customer"]
            lines.append(
                f"  #{idx:02d}  {c.customer_id} - {c.full_name:<20} | VIP: {c.vip_level.label:<8} | "
                f"{item['booking_count']} đơn ({item['total_nights']} đêm) | "
                f"Đặt: {format_vnd(item['total_spent'])} | Đã TT: {format_vnd(item.get('total_paid', 0))}"
            )

        self.txt_report.delete("1.0", tk.END)
        self.txt_report.insert(tk.END, "\n".join(lines))

    def _on_reset_sample(self):
        if messagebox.askyesno("Xác nhận", "Khởi tạo lại toàn bộ dữ liệu mẫu mặc định?"):
            self.manager.reset_with_sample_data()
            self.refresh_all()

    def refresh_all(self):
        self.refresh_matrix_tab()
        self.refresh_bookings_tab()
        self._on_search_available()
        self.refresh_customers_tab()
        self.refresh_queues_tab()
        self.refresh_payments_tab()
        self.refresh_reports_tab()


# ============================================================================
# MODULE: main.py
# ============================================================================
"""Điểm vào chính của Hệ thống Quản lý Đặt phòng Khách sạn (MI3060).

Cách chạy:
    python main.py              # Chạy giao diện dòng lệnh (CLI Menu tương tác)
    python main.py --gui        # Chạy giao diện đồ họa Tkinter (GUI)
    python main.py --demo       # Chạy kịch bản minh họa tự động 8 chức năng cốt lõi
    python main.py --benchmark  # Chạy đánh giá hiệu năng trên tập dữ liệu >= 2.000 bản ghi
    python main.py --reset      # Khởi tạo lại dữ liệu mẫu chuẩn vào data/hotel_data.json
"""




def _configure_utf8_console():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Hệ thống Quản lý Đặt phòng Khách sạn — Cấu trúc Dữ liệu & Giải thuật (MI3060)"
    )
    parser.add_argument("--gui", action="store_true", help="Khởi chạy giao diện đồ họa Tkinter (GUI)")
    parser.add_argument("--demo", action="store_true", help="Chạy kịch bản minh họa tự động trên console")
    parser.add_argument("--benchmark", action="store_true", help="Chạy đo hiệu năng thực nghiệm (>= 2.000 bản ghi)")
    parser.add_argument("--reset", action="store_true", help="Khởi tạo lại dữ liệu mẫu trước khi chạy")
    return parser.parse_args(argv)


def main(argv=None):
    _configure_utf8_console()
    args = parse_args(argv)

    if args.benchmark:
        print("=== KẾT QUẢ ĐÁNH GIÁ HIỆU NĂNG THỰC NGHIỆM (CHƯƠNG 4 — >= 2.000 BẢN GHI) ===")
        print(format_benchmark_report())
        return

    if args.reset:
        manager = HotelManager(seed_if_empty=False, load_existing=False)
        manager.reset_with_sample_data()
        print("[OK] Đã khởi tạo lại dữ liệu mẫu tại data/hotel_data.json.")
    else:
        manager = HotelManager(seed_if_empty=True)

    if args.demo:
        run_demo_walkthrough(manager)
        return

    if args.gui:

        app = HotelGUI(manager)
        app.run()
        return

    cli = HotelCLI(manager)
    cli.run()


if __name__ == "__main__":
    main()
