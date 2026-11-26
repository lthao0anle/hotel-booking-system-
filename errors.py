"""Ngoại lệ nghiệp vụ. Lớp giao diện bắt `HotelError` để hiển thị thông báo thân thiện."""


class HotelError(Exception):
    """Lỗi nghiệp vụ chung (dữ liệu nhập sai, thao tác không hợp lệ...)."""


class NotFoundError(HotelError):
    """Không tìm thấy đối tượng (phòng, khách, booking...)."""


class RoomUnavailableError(HotelError):
    """Phòng không thể đặt trong khoảng ngày yêu cầu."""

    def __init__(self, message, conflicting_booking=None):
        super().__init__(message)
        self.conflicting_booking = conflicting_booking
