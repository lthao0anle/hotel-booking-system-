"""Thực thể Khách hàng (Customer).

Lịch sử lưu trú được lưu bằng danh sách liên kết đơn: lượt đặt mới nhất ở đầu.
"""

from dataclasses import dataclass, field

from hotel.data_structures.linked_list import SinglyLinkedList
from hotel.models.enums import VipLevel


@dataclass
class Customer:
    customer_id: str
    full_name: str
    cccd: str
    phone: str
    vip_level: VipLevel = VipLevel.NORMAL
    manual_vip_level: VipLevel | None = None
    history: SinglyLinkedList = field(default_factory=SinglyLinkedList, repr=False, compare=False)

    def __post_init__(self):
        self.vip_level = VipLevel(int(self.vip_level))
        if self.manual_vip_level is None:
            self.manual_vip_level = self.vip_level
        else:
            self.manual_vip_level = VipLevel(int(self.manual_vip_level))

    @property
    def is_vip(self):
        return self.vip_level > VipLevel.NORMAL

    def add_booking_to_history(self, booking):
        """Chèn lượt đặt mới vào ĐẦU lịch sử — O(1)."""
        self.history.push_front(booking)

    def to_dict(self):
        return {
            "customer_id": self.customer_id,
            "full_name": self.full_name,
            "cccd": self.cccd,
            "phone": self.phone,
            "vip_level": int(self.vip_level),
            "manual_vip_level": int(self.manual_vip_level),
            # Lưu theo thứ tự cũ -> mới để khi nạp lại chỉ cần push_front lần lượt.
            "history": [booking.booking_id for booking in reversed(self.history.to_list())],
        }

    @classmethod
    def from_dict(cls, data):
        vip = VipLevel(data.get("vip_level", 0))
        manual_vip = VipLevel(data.get("manual_vip_level", int(vip)))
        return cls(
            customer_id=data["customer_id"],
            full_name=data["full_name"],
            cccd=data["cccd"],
            phone=data["phone"],
            vip_level=vip,
            manual_vip_level=manual_vip,
        )
