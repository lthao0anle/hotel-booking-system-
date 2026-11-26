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

from datetime import date

from hotel.config import DEFAULT_DATA_FILE, DEFAULT_FLOORS, DEFAULT_ROOMS_PER_FLOOR
from hotel.models.enums import BookingStatus, PaymentMethod, PaymentStatus
from hotel.services.booking_service import BookingService
from hotel.services.customer_service import CustomerService
from hotel.services.payment_service import PaymentService
from hotel.services.report_service import ReportService
from hotel.services.room_service import RoomService
from hotel.services.seed_service import seed_sample_data
from hotel.services.service_request_service import ServiceRequestService
from hotel.services.storage_service import StorageService
from hotel.services.undo_service import UndoService
from hotel.services.waiting_service import WaitingService


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
