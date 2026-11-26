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

