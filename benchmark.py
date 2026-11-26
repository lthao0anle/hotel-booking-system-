"""Đánh giá hiệu năng thực nghiệm (Chương 4 — Mục 4.3).

So sánh thời gian thực thi giữa cách tiếp cận ngây thơ (Naive) và cấu trúc dữ liệu
tối ưu tự cài đặt trên tập dữ liệu >= 1.000 bản ghi.
"""

from datetime import date, timedelta
import random
import time

from hotel.algorithms.binary_search import binary_search, find_closest
from hotel.algorithms.merge_sort import merge_sort
from hotel.algorithms.naive import (
    linear_extract_max,
    linear_find_conflict,
    linear_search,
    selection_sort,
)
from hotel.algorithms.quick_sort import quick_sort
from hotel.data_structures.hash_table import HashTable
from hotel.data_structures.interval_schedule import IntervalSchedule
from hotel.data_structures.matrix_2d import Matrix2D
from hotel.data_structures.max_heap import MaxHeap
from hotel.ui.formatter import render_table


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


if __name__ == "__main__":
    print("=== KẾT QUẢ ĐÁNH GIÁ HIỆU NĂNG THỰC NGHIỆM (CHƯƠNG 4) ===")
    print(format_benchmark_report())
