"""Thực thể Phòng (Room)."""

from dataclasses import dataclass

from hotel.models.enums import RoomType


def make_room_id(floor, room_number):
    """Mã phòng: 'P' + tầng + số phòng 2 chữ số, ví dụ tầng 2 phòng 5 -> 'P205'."""
    return f"P{floor}{room_number:02d}"


def parse_room_id(room_id):
    """Tách mã phòng thành (tầng, số phòng). Chấp nhận 'P205', 'p205' hoặc '205'."""
    text = (room_id or "").strip().upper()
    if text.startswith("P"):
        text = text[1:]
    if len(text) < 3 or not text.isdigit():
        raise ValueError(f"Mã phòng không hợp lệ: '{room_id}'")
    return int(text[:-2]), int(text[-2:])


@dataclass
class Room:
    floor: int
    room_number: int
    room_type: RoomType
    price_per_night: int
    description: str = ""
    under_maintenance: bool = False

    @property
    def room_id(self):
        return make_room_id(self.floor, self.room_number)

    def to_dict(self):
        return {
            "floor": self.floor,
            "room_number": self.room_number,
            "room_type": self.room_type.value,
            "price_per_night": self.price_per_night,
            "description": self.description,
            "under_maintenance": self.under_maintenance,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            floor=data["floor"],
            room_number=data["room_number"],
            room_type=RoomType(data["room_type"]),
            price_per_night=data["price_per_night"],
            description=data.get("description", ""),
            under_maintenance=data.get("under_maintenance", False),
        )
