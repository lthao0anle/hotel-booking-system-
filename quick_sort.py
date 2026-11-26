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
