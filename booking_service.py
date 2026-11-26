"""Chức năng 2: Quản lý đặt phòng và kiểm tra xung đột ngày bằng BST (AVL Tree).

Độ phức tạp mục tiêu (n = số đơn đặt đang hiệu lực của một phòng):
- Kiểm tra xung đột khoảng ngày [check_in, check_out) trên 1 phòng : O(log n)
- Chèn đơn đặt phòng mới vào lịch phòng (BST theo check_in)        : O(log n)
- Xóa đơn đặt phòng khỏi lịch phòng (khi hủy)                      : O(log n)
- Tra cứu đơn đặt phòng theo mã booking_id                         : O(1) trung bình (HashTable)
"""

from datetime import date

from hotel.config import MAX_STAY_NIGHTS
from hotel.data_structures.hash_table import HashTable
from hotel.data_structures.interval_schedule import IntervalSchedule
from hotel.models.booking import Booking
from hotel.models.enums import BookingStatus, RoomStatus
from hotel.models.date_utils import format_date
from hotel.services.errors import HotelError, NotFoundError, RoomUnavailableError
from hotel.services.id_generator import SequenceGenerator


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
