"""Chức năng 6: Hủy đặt phòng và Hoàn tác (Undo) bằng Ngăn xếp (Stack).

Độ phức tạp mục tiêu:
- Lưu thao tác hủy vào Stack (push)          : O(1)
- Lấy thao tác hủy gần nhất từ Stack (pop)   : O(1)
- Xem thao tác hủy sắp hoàn tác (peek)       : O(1)
- Cập nhật lịch phòng trên BST khi hủy/undo  : O(log n)
"""

from datetime import date

from hotel.data_structures.stack import Stack
from hotel.models.cancel_action import CancelAction
from hotel.models.enums import BookingStatus
from hotel.services.errors import HotelError


class UndoService:
    def __init__(self, booking_service):
        self._booking_service = booking_service
        self._undo_stack = Stack()

    def cancel_booking(self, booking_id, cancelled_by="STAFF", cancelled_at=None):
        """Hủy một đơn đặt phòng và đẩy bản chụp trạng thái vào Stack — O(1) stack + O(log n) BST."""
        booking = self._booking_service.get_booking(booking_id)
        if booking.status == BookingStatus.CANCELLED:
            raise HotelError(f"Đơn đặt phòng {booking.booking_id} đã ở trạng thái ĐÃ HỦY")
        if booking.status == BookingStatus.CHECKED_OUT:
            raise HotelError(
                f"Không thể hủy đơn {booking.booking_id} vì khách đã trả phòng (CHECKED_OUT)"
            )

        snapshot = booking.to_dict()
        self._booking_service.detach_booking_from_schedule(booking)
        booking.status = BookingStatus.CANCELLED

        action = CancelAction(
            booking_id=booking.booking_id,
            room_id=booking.room_id,
            booking_snapshot=snapshot,
            cancelled_by=cancelled_by,
            cancelled_at=cancelled_at or date.today(),
        )
        self._undo_stack.push(action)
        return action

    def peek_last_cancellation(self):
        """Xem thao tác hủy gần nhất trên đỉnh Stack mà không xóa — O(1)."""
        if self._undo_stack.is_empty():
            return None
        return self._undo_stack.peek()

    def undo_last_cancellation(self):
        """Hoàn tác thao tác hủy gần nhất: pop Stack O(1) + chèn lại vào BST O(log n)."""
        if self._undo_stack.is_empty():
            raise HotelError("Ngăn xếp hoàn tác đang trống — không có thao tác hủy nào để hoàn tác")

        action = self._undo_stack.pop()
        booking = self._booking_service.get_booking(action.booking_id)
        previous_status = BookingStatus(action.booking_snapshot["status"])

        try:
            self._booking_service.attach_booking_to_schedule(booking)
        except Exception:
            # Nếu không thể khôi phục (do phòng đã bị người khác đặt chồng), trả lại vào Stack
            self._undo_stack.push(action)
            raise

        booking.status = previous_status
        return action, booking

    def history(self):
        """Danh sách các thao tác hủy đang lưu trong Stack (từ mới nhất xuống cũ nhất)."""
        return list(self._undo_stack)

    def __len__(self):
        return len(self._undo_stack)

    def load_actions(self, action_dicts):
        """Khôi phục ngăn xếp hoàn tác từ dữ liệu JSON (action_dicts lưu từ đỉnh xuống đáy)."""
        self._undo_stack = Stack()
        for item in reversed(action_dicts):
            self._undo_stack.push(CancelAction.from_dict(item))
