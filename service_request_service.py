"""Chức năng 7: Quản lý yêu cầu dịch vụ nội bộ (Dọn phòng, Đồ ăn, Y tế...) bằng Priority Queue.

Độ phức tạp mục tiêu (s = số yêu cầu đang chờ xử lý):
- Thêm yêu cầu dịch vụ mới (push vào Max-Heap) : O(log s)
- Lấy yêu cầu khẩn nhất để xử lý (pop)         : O(log s)
- Xem yêu cầu khẩn nhất (peek)                 : O(1)

Thứ tự ưu tiên: EMERGENCY (3) > NORMAL (2) > LOW (1).
Cùng độ khẩn: yêu cầu gửi sớm hơn (sequence nhỏ hơn) được phục vụ trước.
"""

from datetime import date

from hotel.data_structures.linked_list import SinglyLinkedList
from hotel.data_structures.max_heap import MaxHeap
from hotel.models.enums import ServiceStatus, ServiceType, UrgencyLevel
from hotel.models.service_request import ServiceRequest
from hotel.services.errors import HotelError
from hotel.services.id_generator import SequenceGenerator


def _request_priority_key(req):
    return req.priority_key()


DEFAULT_URGENCY_BY_SERVICE = {
    ServiceType.MEDICAL: UrgencyLevel.EMERGENCY,
    ServiceType.FOOD: UrgencyLevel.NORMAL,
    ServiceType.CLEANING: UrgencyLevel.LOW,
    ServiceType.OTHER: UrgencyLevel.NORMAL,
}


class ServiceRequestService:
    def __init__(self, room_service, customer_service):
        self._room_service = room_service
        self._customer_service = customer_service
        self._pending_heap = MaxHeap(_request_priority_key)
        self._completed_list = SinglyLinkedList()
        self._id_gen = SequenceGenerator("SR", 4)
        self._seq_gen = SequenceGenerator("SRSEQ", 1)

    @property
    def id_generator(self):
        return self._id_gen

    @property
    def sequence_generator(self):
        return self._seq_gen

    def submit_request(
        self,
        room_id,
        service_type,
        urgency=None,
        note="",
        customer_id="",
        requested_at=None,
    ):
        """Gửi một yêu cầu dịch vụ mới vào Max-Heap — O(log s)."""
        room = self._room_service.get_room(room_id)
        stype = service_type if isinstance(service_type, ServiceType) else ServiceType(service_type)
        if urgency is None:
            ulevel = DEFAULT_URGENCY_BY_SERVICE[stype]
        else:
            ulevel = urgency if isinstance(urgency, UrgencyLevel) else UrgencyLevel(int(urgency))

        cid = ""
        if customer_id and customer_id.strip():
            cid = self._customer_service.get_customer(customer_id).customer_id

        request = ServiceRequest(
            request_id=self._id_gen.next_id(),
            room_id=room.room_id,
            customer_id=cid,
            service_type=stype,
            urgency=ulevel,
            note=(note or "").strip(),
            sequence=self._seq_gen.next_number(),
            requested_at=requested_at or date.today(),
            status=ServiceStatus.WAITING,
        )
        self._pending_heap.push(request)
        return request

    def peek_next(self):
        """Xem yêu cầu dịch vụ có độ khẩn cao nhất — O(1)."""
        if self._pending_heap.is_empty():
            return None
        return self._pending_heap.peek()

    def process_next(self):
        """Xử lý yêu cầu dịch vụ khẩn nhất (pop khỏi Max-Heap) — O(log s)."""
        if self._pending_heap.is_empty():
            raise HotelError("Hiện không có yêu cầu dịch vụ nào đang chờ xử lý")
        request = self._pending_heap.pop()
        request.status = ServiceStatus.DONE
        self._completed_list.push_front(request)
        return request

    def pending_requests_ordered(self):
        """Danh sách yêu cầu đang chờ theo thứ tự ưu tiên giảm dần — O(s log s)."""
        return self._pending_heap.to_sorted_list()

    def completed_requests(self):
        """Danh sách các yêu cầu đã hoàn thành (mới nhất trước)."""
        return self._completed_list.to_list()

    def all_requests(self):
        """Danh sách toàn bộ yêu cầu dịch vụ (cả đang chờ và đã hoàn thành)."""
        return list(self._pending_heap) + self._completed_list.to_list()

    def pending_count(self):
        return len(self._pending_heap)

    def completed_count(self):
        return len(self._completed_list)

    def load_requests(self, pending_dicts, completed_dicts, id_seq, order_seq):
        self._pending_heap = MaxHeap(_request_priority_key)
        self._completed_list = SinglyLinkedList()
        self._id_gen.restore(id_seq)
        self._seq_gen.restore(order_seq)

        for item in pending_dicts:
            req = ServiceRequest.from_dict(item)
            self._pending_heap.push(req)
            self._seq_gen.restore(req.sequence)
            if req.request_id.startswith("SR") and req.request_id[2:].isdigit():
                self._id_gen.restore(int(req.request_id[2:]))

        # completed_dicts lưu từ mới -> cũ, nạp ngược lại bằng push_front
        for item in reversed(completed_dicts):
            req = ServiceRequest.from_dict(item)
            self._completed_list.push_front(req)
            self._seq_gen.restore(req.sequence)
            if req.request_id.startswith("SR") and req.request_id[2:].isdigit():
                self._id_gen.restore(int(req.request_id[2:]))
