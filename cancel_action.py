"""Thực thể Thao tác hủy (CancelAction) — phần tử của ngăn xếp hoàn tác."""

from dataclasses import dataclass
from datetime import date

from hotel.models.date_utils import from_iso, to_iso


@dataclass
class CancelAction:
    booking_id: str
    room_id: str
    booking_snapshot: dict   # bản sao Booking.to_dict() NGAY TRƯỚC khi hủy
    cancelled_by: str        # "STAFF" hoặc "CUSTOMER"
    cancelled_at: date

    def to_dict(self):
        return {
            "booking_id": self.booking_id,
            "room_id": self.room_id,
            "booking_snapshot": dict(self.booking_snapshot),
            "cancelled_by": self.cancelled_by,
            "cancelled_at": to_iso(self.cancelled_at),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            booking_id=data["booking_id"],
            room_id=data["room_id"],
            booking_snapshot=dict(data["booking_snapshot"]),
            cancelled_by=data.get("cancelled_by", "STAFF"),
            cancelled_at=from_iso(data["cancelled_at"]),
        )
