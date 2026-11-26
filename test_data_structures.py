"""Kiểm thử chuyên sâu các Cấu trúc Dữ liệu tự cài đặt (kèm trường hợp biên)."""

from datetime import date, timedelta
import unittest

from hotel.data_structures.avl_tree import AVLTree
from hotel.data_structures.hash_table import HashTable
from hotel.data_structures.interval_schedule import IntervalSchedule
from hotel.data_structures.linked_list import SinglyLinkedList
from hotel.data_structures.linked_queue import LinkedQueue
from hotel.data_structures.matrix_2d import Matrix2D
from hotel.data_structures.max_heap import MaxHeap
from hotel.data_structures.stack import Stack


class TestMatrix2D(unittest.TestCase):
    def test_dimensions_and_access(self):
        m = Matrix2D(3, 4, fill=0)
        self.assertEqual(m.rows, 3)
        self.assertEqual(m.cols, 4)
        self.assertEqual(len(m), 12)
        m.set(2, 3, "P304")
        self.assertEqual(m.get(2, 3), "P304")
        self.assertEqual(m.row(2), [0, 0, 0, "P304"])

    def test_invalid_dimensions_and_bounds(self):
        with self.assertRaises(ValueError):
            Matrix2D(0, 5)
        with self.assertRaises(ValueError):
            Matrix2D(5, -1)
        m = Matrix2D(2, 2)
        with self.assertRaises(IndexError):
            m.get(-1, 0)
        with self.assertRaises(IndexError):
            m.set(2, 0, 1)


class TestAVLTreeAndIntervalSchedule(unittest.TestCase):
    def test_avl_rotations_and_balance_on_sorted_insert(self):
        tree = AVLTree()
        # Chèn 500 khóa tăng dần (trường hợp suy biến O(n) với BST thường)
        for k in range(500):
            tree.insert(k, f"val-{k}")
        self.assertEqual(len(tree), 500)
        # Chiều cao cây AVL với 500 nút phải <= 1.44 * log2(502) ~ 12
        self.assertLessEqual(tree.height, 12)
        self.assertEqual([k for k, _ in tree.items()], list(range(500)))

        # Xóa các nút có 0, 1, 2 con
        for k in range(0, 500, 2):
            removed = tree.remove(k)
            self.assertEqual(removed, f"val-{k}")
        self.assertEqual(len(tree), 250)
        self.assertEqual([k for k, _ in tree.items()], list(range(1, 500, 2)))

    def test_avl_duplicate_and_missing_key(self):
        tree = AVLTree()
        tree.insert(10, "a")
        with self.assertRaises(KeyError):
            tree.insert(10, "b")
        with self.assertRaises(KeyError):
            tree.remove(99)

    def test_avl_lower_floor_and_range(self):
        tree = AVLTree()
        for k in [10, 20, 30, 40]:
            tree.insert(k, k * 10)
        self.assertIsNone(tree.lower_entry(10))
        self.assertEqual(tree.lower_entry(25), (20, 200))
        self.assertEqual(tree.floor_entry(20), (20, 200))
        self.assertEqual(tree.range_items(15, 35), [(20, 200), (30, 300)])

    def test_interval_schedule_overlap_and_adjacent_boundaries(self):
        sched = IntervalSchedule(lambda x: x[0], lambda x: x[1])
        d = lambda day: date(2026, 11, day)
        iv1 = (d(10), d(15), "BK1")
        iv2 = (d(15), d(20), "BK2")  # Tiếp giáp tại ngày 15 -> KHÔNG xung đột
        sched.add(iv1)
        sched.add(iv2)
        self.assertEqual(len(sched), 2)

        # Giao một phần đầu, giữa, cuối hoặc bao trùm đều phải phát hiện xung đột
        self.assertEqual(sched.find_conflict(d(8), d(11)), iv1)
        self.assertEqual(sched.find_conflict(d(12), d(14)), iv1)
        self.assertEqual(sched.find_conflict(d(14), d(16)), iv2)
        self.assertEqual(sched.find_conflict(d(5), d(25)), iv2)
        self.assertIsNone(sched.find_conflict(d(1), d(10)))
        self.assertIsNone(sched.find_conflict(d(20), d(25)))

        with self.assertRaises(ValueError):
            sched.find_conflict(d(10), d(10))


class TestHashTable(unittest.TestCase):
    def test_put_get_update_remove_and_resize(self):
        ht = HashTable(capacity=4)
        for i in range(200):
            ht.put(f"key-{i}", i)
        self.assertEqual(len(ht), 200)
        for i in range(200):
            self.assertEqual(ht.get(f"key-{i}"), i)

        # Ghi đè khóa cũ không làm tăng kích thước
        ht.put("key-0", 9999)
        self.assertEqual(len(ht), 200)
        self.assertEqual(ht.get("key-0"), 9999)

        self.assertTrue(ht.remove("key-0"))
        self.assertFalse(ht.remove("key-0"))
        self.assertIsNone(ht.get("key-0"))
        self.assertEqual(len(ht), 199)


class TestLinkedListQueueStackHeap(unittest.TestCase):
    def test_singly_linked_list(self):
        ll = SinglyLinkedList()
        self.assertTrue(ll.is_empty())
        ll.push_front("B")
        ll.push_front("A")
        ll.push_back("C")
        self.assertEqual(ll.to_list(), ["A", "B", "C"])
        self.assertEqual(ll.find(lambda x: x == "B"), "B")
        self.assertTrue(ll.remove_first(lambda x: x == "B"))
        self.assertEqual(ll.to_list(), ["A", "C"])

    def test_linked_queue_fifo(self):
        q = LinkedQueue()
        for x in [1, 2, 3]:
            q.enqueue(x)
        self.assertEqual(q.peek(), 1)
        self.assertEqual(q.remove_first(lambda v: v == 2), 2)
        self.assertEqual([q.dequeue(), q.dequeue()], [1, 3])
        self.assertTrue(q.is_empty())
        with self.assertRaises(IndexError):
            q.dequeue()

    def test_stack_lifo(self):
        s = Stack()
        s.push("first")
        s.push("second")
        self.assertEqual(s.peek(), "second")
        self.assertEqual(s.pop(), "second")
        self.assertEqual(s.pop(), "first")
        self.assertTrue(s.is_empty())
        with self.assertRaises(IndexError):
            s.pop()

    def test_max_heap_priority_and_tiebreak(self):
        heap = MaxHeap(lambda item: (item["vip"], -item["seq"]))
        heap.push({"id": "A", "vip": 1, "seq": 1})
        heap.push({"id": "B", "vip": 3, "seq": 2})
        heap.push({"id": "C", "vip": 2, "seq": 3})
        heap.push({"id": "D", "vip": 3, "seq": 1})  # Cùng VIP=3 nhưng đến sớm hơn B

        order = [heap.pop()["id"] for _ in range(4)]
        self.assertEqual(order, ["D", "B", "C", "A"])


if __name__ == "__main__":
    unittest.main()
