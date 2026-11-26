"""Kiểm thử các giải thuật Sắp xếp (Merge Sort, Quick Sort) và Tìm kiếm nhị phân."""

import random
import unittest

from hotel.algorithms.binary_search import (
    binary_search,
    find_closest,
    lower_bound,
    range_search,
    upper_bound,
)
from hotel.algorithms.merge_sort import merge_sort
from hotel.algorithms.quick_sort import quick_sort


class TestSortingAlgorithms(unittest.TestCase):
    def test_merge_sort_stability(self):
        items = [
            ("P102", 500),
            ("P101", 800),
            ("P103", 500),
            ("P104", 500),
            ("P105", 800),
        ]
        sorted_items = merge_sort(items, key=lambda x: x[1])
        self.assertEqual(
            sorted_items,
            [
                ("P102", 500),
                ("P103", 500),
                ("P104", 500),
                ("P101", 800),
                ("P105", 800),
            ],
        )

    def test_quick_sort_and_merge_sort_edge_cases(self):
        for sorter in (merge_sort, quick_sort):
            self.assertEqual(sorter([]), [])
            self.assertEqual(sorter([42]), [42])
            self.assertEqual(sorter([5, 5, 5, 5]), [5, 5, 5, 5])
            rng = random.Random(123)
            arr = [rng.randint(-100, 100) for _ in range(300)]
            self.assertEqual(sorter(arr), sorted(arr))
            self.assertEqual(sorter(arr, reverse=True), sorted(arr, reverse=True))


class TestBinarySearch(unittest.TestCase):
    def test_bounds_and_range_search(self):
        arr = [500, 500, 650, 800, 800, 1500]
        self.assertEqual(lower_bound(arr, 500), 0)
        self.assertEqual(upper_bound(arr, 500), 2)
        self.assertEqual(binary_search(arr, 650), 2)
        self.assertEqual(binary_search(arr, 999), -1)
        self.assertEqual(range_search(arr, 550, 800), [650, 800, 800])

    def test_find_closest_budget(self):
        prices = [500_000, 800_000, 1_500_000]
        self.assertIsNone(find_closest([], 800_000))
        self.assertEqual(find_closest(prices, 200_000), 500_000)
        self.assertEqual(find_closest(prices, 5_000_000), 1_500_000)
        # Khi cách đều 500k và 800k (tức 650k), ưu tiên phòng rẻ hơn (500k)
        self.assertEqual(find_closest(prices, 650_000), 500_000)
        self.assertEqual(find_closest(prices, 700_000), 800_000)


if __name__ == "__main__":
    unittest.main()
