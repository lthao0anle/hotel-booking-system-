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
