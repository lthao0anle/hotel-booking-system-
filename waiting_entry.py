"""Thực thể Mục chờ (WaitingEntry) — khách chờ phòng khi hết phòng."""

from dataclasses import dataclass
from datetime import date

from hotel.models.date_utils import from_iso, to_iso
from hotel.models.enums import RoomType


@dataclass
class WaitingEntry:
    entry_id: str
    customer_id: str
    room_type: RoomType
    check_in: date
    check_out: date
    priority: int          # = cấp VIP của khách tại thời điểm vào hàng chờ (0..3)
    sequence: int          # số thứ tự vào hàng, dùng để phá hòa (ai đến trước phục vụ trước)
    requested_at: date

    def priority_key(self):
        """Khóa cho Max-Heap: VIP cao hơn trước; cùng cấp thì sequence nhỏ (đến sớm) trước."""
        return (self.priority, -self.sequence)

    def to_dict(self):
        return {
            "entry_id": self.entry_id,
            "customer_id": self.customer_id,
            "room_type": self.room_type.value,
            "check_in": to_iso(self.check_in),
            "check_out": to_iso(self.check_out),
            "priority": self.priority,
            "sequence": self.sequence,
            "requested_at": to_iso(self.requested_at),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            entry_id=data["entry_id"],
            customer_id=data["customer_id"],
            room_type=RoomType(data["room_type"]),
            check_in=from_iso(data["check_in"]),
            check_out=from_iso(data["check_out"]),
            priority=data["priority"],
            sequence=data["sequence"],
            requested_at=from_iso(data["requested_at"]),
        )
