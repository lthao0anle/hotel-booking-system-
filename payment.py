"""Thực thể Giao dịch Thanh toán (PaymentTransaction)."""

from dataclasses import dataclass
from datetime import date

from hotel.models.date_utils import from_iso, to_iso
from hotel.models.enums import PaymentMethod, PaymentStatus


@dataclass
class PaymentTransaction:
    payment_id: str
    booking_id: str
    customer_id: str
    room_id: str
    room_cost: int
    service_cost: int
    extra_fee: int
    discount_amount: int
    total_amount: int
    payment_method: PaymentMethod
    paid_at: date
    status: PaymentStatus = PaymentStatus.PAID
    note: str = ""

    @property
    def gross_amount(self):
        """Tổng chi phí trước khi trừ chiết khấu VIP."""
        return self.room_cost + self.service_cost + self.extra_fee

    def to_dict(self):
        return {
            "payment_id": self.payment_id,
            "booking_id": self.booking_id,
            "customer_id": self.customer_id,
            "room_id": self.room_id,
            "room_cost": self.room_cost,
            "service_cost": self.service_cost,
            "extra_fee": self.extra_fee,
            "discount_amount": self.discount_amount,
            "total_amount": self.total_amount,
            "payment_method": self.payment_method.value,
            "paid_at": to_iso(self.paid_at),
            "status": self.status.value,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            payment_id=data["payment_id"],
            booking_id=data["booking_id"],
            customer_id=data["customer_id"],
            room_id=data["room_id"],
            room_cost=int(data.get("room_cost", 0)),
            service_cost=int(data.get("service_cost", 0)),
            extra_fee=int(data.get("extra_fee", 0)),
            discount_amount=int(data.get("discount_amount", 0)),
            total_amount=int(data.get("total_amount", 0)),
            payment_method=PaymentMethod(data.get("payment_method", "CASH")),
            paid_at=from_iso(data["paid_at"]),
            status=PaymentStatus(data.get("status", "PAID")),
            note=data.get("note", ""),
        )
