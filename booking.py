"""Thực thể Đơn đặt phòng (Booking). Khoảng lưu trú là nửa mở [check_in, check_out)."""

from dataclasses import dataclass
from datetime import date

from hotel.models.date_utils import from_iso, to_iso
from hotel.models.enums import BookingStatus


@dataclass
class Booking:
    booking_id: str
    customer_id: str
    room_id: str
    check_in: date
    check_out: date
    price_per_night: int
    created_at: date
    status: BookingStatus = BookingStatus.CONFIRMED
    vip_level_at_booking: int | None = None

    @property
    def num_nights(self):
        return (self.check_out - self.check_in).days

    @property
    def total_price(self):
        return self.num_nights * self.price_per_night

    @property
    def is_active(self):
        """Booking còn đang giữ lịch phòng (CONFIRMED hoặc CHECKED_IN)."""
        return self.status in (BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN)

    def overlaps(self, check_in, check_out):
        """Hai khoảng [A, B) và [C, D) giao nhau  <=>  A < D và C < B."""
        return self.check_in < check_out and check_in < self.check_out

    def to_dict(self):
        data = {
            "booking_id": self.booking_id,
            "customer_id": self.customer_id,
            "room_id": self.room_id,
            "check_in": to_iso(self.check_in),
            "check_out": to_iso(self.check_out),
            "price_per_night": self.price_per_night,
            "created_at": to_iso(self.created_at),
            "status": self.status.value,
        }
        if self.vip_level_at_booking is not None:
            data["vip_level_at_booking"] = int(self.vip_level_at_booking)
        return data

    @classmethod
    def from_dict(cls, data):
        vip_at_bk = data.get("vip_level_at_booking")
        return cls(
            booking_id=data["booking_id"],
            customer_id=data["customer_id"],
            room_id=data["room_id"],
            check_in=from_iso(data["check_in"]),
            check_out=from_iso(data["check_out"]),
            price_per_night=data["price_per_night"],
            created_at=from_iso(data["created_at"]),
            status=BookingStatus(data["status"]),
            vip_level_at_booking=int(vip_at_bk) if vip_at_bk is not None else None,
        )
