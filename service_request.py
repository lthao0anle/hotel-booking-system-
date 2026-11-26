"""Thực thể Yêu cầu dịch vụ nội bộ (ServiceRequest)."""

from dataclasses import dataclass
from datetime import date

from hotel.models.date_utils import from_iso, to_iso
from hotel.models.enums import ServiceStatus, ServiceType, UrgencyLevel


@dataclass
class ServiceRequest:
    request_id: str
    room_id: str
    customer_id: str        # có thể rỗng nếu do nhân viên tạo
    service_type: ServiceType
    urgency: UrgencyLevel
    note: str
    sequence: int           # thứ tự gửi, dùng phá hòa khi cùng độ khẩn
    requested_at: date
    status: ServiceStatus = ServiceStatus.WAITING

    def priority_key(self):
        """Khóa cho Max-Heap: khẩn hơn trước; cùng độ khẩn thì gửi trước xử lý trước."""
        return (int(self.urgency), -self.sequence)

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "room_id": self.room_id,
            "customer_id": self.customer_id,
            "service_type": self.service_type.value,
            "urgency": int(self.urgency),
            "note": self.note,
            "sequence": self.sequence,
            "requested_at": to_iso(self.requested_at),
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            request_id=data["request_id"],
            room_id=data["room_id"],
            customer_id=data.get("customer_id", ""),
            service_type=ServiceType(data["service_type"]),
            urgency=UrgencyLevel(data["urgency"]),
            note=data.get("note", ""),
            sequence=data["sequence"],
            requested_at=from_iso(data["requested_at"]),
            status=ServiceStatus(data.get("status", "WAITING")),
        )
