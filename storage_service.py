"""Chức năng lưu trữ bền vững: Đọc/ghi toàn bộ trạng thái hệ thống ra file JSON.

Khi nạp lại từ file JSON, các cấu trúc dữ liệu nền tảng (Matrix2D, AVLTree/BST,
HashTable, SinglyLinkedList, MaxHeap, LinkedQueue, Stack) đều được tái lập đầy đủ.
"""

import json
from pathlib import Path

from hotel.models.room import Room
from hotel.services.errors import HotelError


class StorageService:
    def __init__(self, data_file):
        self._data_file = Path(data_file)

    @property
    def data_file(self):
        return self._data_file

    def exists(self):
        return self._data_file.is_file()

    def save(
        self,
        room_service,
        customer_service,
        booking_service,
        waiting_service,
        undo_service,
        service_request_service,
        payment_service=None,
    ):
        """Lưu toàn bộ trạng thái hiện tại ra file JSON."""
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "floors": room_service.floors,
                "rooms_per_floor": room_service.rooms_per_floor,
                "customer_seq": customer_service.id_generator.current,
                "booking_seq": booking_service.id_generator.current,
                "waiting_id_seq": waiting_service.id_generator.current,
                "waiting_order_seq": waiting_service.sequence_generator.current,
                "service_id_seq": service_request_service.id_generator.current,
                "service_order_seq": service_request_service.sequence_generator.current,
                "payment_seq": payment_service.id_generator.current if payment_service is not None else 0,
            },
            "rooms": [room.to_dict() for room in room_service.all_rooms()],
            "bookings": [booking.to_dict() for booking in booking_service.all_bookings()],
            "customers": [customer.to_dict() for customer in customer_service.all_customers()],
            "waiting_entries": [entry.to_dict() for entry in waiting_service.list_waiting_ordered()],
            "undo_stack": [action.to_dict() for action in undo_service.history()],
            "service_requests": {
                "pending": [req.to_dict() for req in service_request_service.pending_requests_ordered()],
                "completed": [req.to_dict() for req in service_request_service.completed_requests()],
            },
            "payments": (
                [tx.to_dict() for tx in payment_service.all_transactions()]
                if payment_service is not None
                else []
            ),
        }
        temp_file = self._data_file.with_suffix(".tmp")
        temp_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_file.replace(self._data_file)

    def load(
        self,
        room_service,
        customer_service,
        booking_service,
        waiting_service,
        undo_service,
        service_request_service,
        payment_service=None,
    ):
        """Nạp dữ liệu từ file JSON và khôi phục toàn bộ các cấu trúc dữ liệu."""
        if not self.exists():
            return False

        try:
            raw = json.loads(self._data_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Nội dung JSON gốc phải là một đối tượng (dict)")
            meta = raw.get("meta", {})
            if not isinstance(meta, dict):
                raise ValueError("Trường 'meta' trong file JSON không hợp lệ")

            floors = int(meta.get("floors", room_service.floors))
            rooms_per_floor = int(meta.get("rooms_per_floor", room_service.rooms_per_floor))
            rooms = [Room.from_dict(item) for item in raw.get("rooms", [])]
            room_service.load_rooms(floors, rooms_per_floor, rooms)

            booking_service.load_bookings(
                raw.get("bookings", []),
                meta.get("booking_seq", 0),
            )

            customer_service.load_customers(
                raw.get("customers", []),
                meta.get("customer_seq", 0),
                booking_service.bookings_by_id_map(),
            )

            waiting_service.load_waiting_entries(
                raw.get("waiting_entries", []),
                meta.get("waiting_id_seq", 0),
                meta.get("waiting_order_seq", 0),
            )

            undo_service.load_actions(raw.get("undo_stack", []))

            sr_data = raw.get("service_requests", {})
            if not isinstance(sr_data, dict):
                raise ValueError("Trường 'service_requests' trong file JSON không hợp lệ")
            service_request_service.load_requests(
                sr_data.get("pending", []),
                sr_data.get("completed", []),
                meta.get("service_id_seq", 0),
                meta.get("service_order_seq", 0),
            )

            if payment_service is not None:
                payments_data = raw.get("payments", [])
                if not isinstance(payments_data, list):
                    raise ValueError("Trường 'payments' trong file JSON không hợp lệ")
                payment_service.load_payments(
                    payments_data,
                    meta.get("payment_seq", 0),
                )
        except HotelError:
            raise
        except (json.JSONDecodeError, KeyError, ValueError, TypeError, OSError) as exc:
            raise HotelError(
                f"Không thể nạp file dữ liệu '{self._data_file}': dữ liệu bị hỏng hoặc sai định dạng ({exc})"
            ) from exc
        return True
