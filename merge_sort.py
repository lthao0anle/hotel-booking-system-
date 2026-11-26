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
