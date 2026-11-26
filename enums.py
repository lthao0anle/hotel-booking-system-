"""Các kiểu liệt kê (enum) dùng chung cho các thực thể."""

from enum import Enum, IntEnum


class RoomType(Enum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    SUITE = "SUITE"

    @property
    def label(self):
        return {"SINGLE": "Đơn", "DOUBLE": "Đôi", "SUITE": "Suite"}[self.value]

    @property
    def order(self):
        """Thứ tự dùng khi sắp xếp/nhóm theo loại phòng."""
        return {"SINGLE": 0, "DOUBLE": 1, "SUITE": 2}[self.value]


class RoomStatus(Enum):
    """Trạng thái hiển thị của phòng TẠI MỘT NGÀY cụ thể."""
    EMPTY = "EMPTY"
    BOOKED = "BOOKED"
    MAINTENANCE = "MAINTENANCE"

    @property
    def label(self):
        return {"EMPTY": "TRỐNG", "BOOKED": "ĐÃ ĐẶT", "MAINTENANCE": "BẢO TRÌ"}[self.value]


class BookingStatus(Enum):
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"

    @property
    def label(self):
        return {
            "CONFIRMED": "Đã xác nhận",
            "CHECKED_IN": "Đang ở",
            "CHECKED_OUT": "Đã trả phòng",
            "CANCELLED": "Đã hủy",
        }[self.value]


class VipLevel(IntEnum):
    NORMAL = 0
    SILVER = 1
    GOLD = 2
    PLATINUM = 3

    @property
    def label(self):
        return {0: "Thường", 1: "Silver", 2: "Gold", 3: "Platinum"}[int(self)]


class ServiceType(Enum):
    CLEANING = "CLEANING"
    FOOD = "FOOD"
    MEDICAL = "MEDICAL"
    OTHER = "OTHER"

    @property
    def label(self):
        return {"CLEANING": "Dọn phòng", "FOOD": "Đồ ăn", "MEDICAL": "Y tế", "OTHER": "Khác"}[self.value]


class UrgencyLevel(IntEnum):
    LOW = 1
    NORMAL = 2
    EMERGENCY = 3

    @property
    def label(self):
        return {1: "Thấp", 2: "Bình thường", 3: "Khẩn cấp"}[int(self)]


class ServiceStatus(Enum):
    WAITING = "WAITING"
    DONE = "DONE"

    @property
    def label(self):
        return {"WAITING": "Đang chờ", "DONE": "Đã xử lý"}[self.value]


class PaymentMethod(Enum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    CARD = "CARD"
    E_WALLET = "E_WALLET"

    @property
    def label(self):
        return {
            "CASH": "Tiền mặt",
            "BANK_TRANSFER": "Chuyển khoản",
            "CARD": "Thẻ ngân hàng",
            "E_WALLET": "Ví điện tử",
        }[self.value]


class PaymentStatus(Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"

    @property
    def label(self):
        return {
            "UNPAID": "Chưa thanh toán",
            "PAID": "Đã thanh toán",
            "REFUNDED": "Đã hoàn tiền",
        }[self.value]
