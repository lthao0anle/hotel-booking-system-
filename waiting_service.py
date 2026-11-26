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

from datetime import date

from hotel.algorithms.merge_sort import merge_sort
from hotel.data_structures.linked_queue import LinkedQueue
from hotel.data_structures.max_heap import MaxHeap
from hotel.models.enums import RoomType
from hotel.models.waiting_entry import WaitingEntry
from hotel.services.booking_service import validate_date_range
from hotel.services.errors import HotelError, NotFoundError
from hotel.services.id_generator import SequenceGenerator


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
