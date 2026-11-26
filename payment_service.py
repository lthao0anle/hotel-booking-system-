"""Chức năng 8: Quản lý thanh toán — Tính tổng chi phí, xử lý thanh toán, lưu trữ & tra cứu giao dịch.

Cấu trúc dữ liệu & Giải thuật sử dụng:
- Bảng băm (`HashTable` chaining):
    + `_by_payment_id`  : Tra cứu giao dịch theo mã thanh toán (TT00001) — O(1) trung bình.
    + `_by_booking_id`  : Tra cứu danh sách giao dịch của một đơn đặt phòng (BK00001) — O(1) trung bình.
    + `_by_customer_id` : Tra cứu lịch sử giao dịch theo mã khách hàng (KH001) — O(1) trung bình.
- Danh sách liên kết đơn (`SinglyLinkedList`):
    + `_transactions`   : Lưu trữ chuỗi giao dịch theo thời gian (mới nhất ở đầu `push_front` — O(1)).
- Sắp xếp (`merge_sort`):
    + Sắp xếp danh sách giao dịch theo tổng tiền, ngày thanh toán hoặc mã giao dịch — O(p log p).
"""

from datetime import date

from hotel.algorithms.merge_sort import merge_sort
from hotel.config import (
    SERVICE_PRICE_BY_TYPE,
    VIP_DISCOUNT_RATES,
    VIP_SPENDING_THRESHOLDS,
    evaluate_vip_level_by_spending,
    get_vip_tier_progress,
)
from hotel.data_structures.hash_table import HashTable
from hotel.data_structures.linked_list import SinglyLinkedList
from hotel.models.enums import BookingStatus, PaymentMethod, PaymentStatus, VipLevel
from hotel.models.payment import PaymentTransaction
from hotel.services.errors import HotelError, NotFoundError
from hotel.services.id_generator import SequenceGenerator


def _parse_payment_method(method):
    if isinstance(method, PaymentMethod):
        return method
    raw = (str(method) if method is not None else "").strip().upper()
    aliases = {
        "1": PaymentMethod.CASH,
        "CASH": PaymentMethod.CASH,
        "TIEN_MAT": PaymentMethod.CASH,
        "TIỀN MẶT": PaymentMethod.CASH,
        "2": PaymentMethod.BANK_TRANSFER,
        "BANK_TRANSFER": PaymentMethod.BANK_TRANSFER,
        "TRANSFER": PaymentMethod.BANK_TRANSFER,
        "CHUYEN_KHOAN": PaymentMethod.BANK_TRANSFER,
        "CHUYỂN KHOẢN": PaymentMethod.BANK_TRANSFER,
        "3": PaymentMethod.CARD,
        "CARD": PaymentMethod.CARD,
        "CREDIT_CARD": PaymentMethod.CARD,
        "THE": PaymentMethod.CARD,
        "THẺ": PaymentMethod.CARD,
        "THẺ NGÂN HÀNG": PaymentMethod.CARD,
        "THE_NGAN_HANG": PaymentMethod.CARD,
        "4": PaymentMethod.E_WALLET,
        "E_WALLET": PaymentMethod.E_WALLET,
        "WALLET": PaymentMethod.E_WALLET,
        "VI_DIEN_TU": PaymentMethod.E_WALLET,
        "VÍ ĐIỆN TỬ": PaymentMethod.E_WALLET,
    }
    if raw in aliases:
        return aliases[raw]
    raise HotelError(
        f"Phương thức thanh toán '{method}' không hợp lệ "
        f"(chọn CASH, BANK_TRANSFER, CARD hoặc E_WALLET)"
    )


def _parse_payment_status(status):
    if isinstance(status, PaymentStatus):
        return status
    raw = (str(status) if status is not None else "").strip().upper()
    try:
        return PaymentStatus(raw)
    except ValueError as exc:
        raise HotelError(
            f"Trạng thái thanh toán '{status}' không hợp lệ (chọn UNPAID, PAID hoặc REFUNDED)"
        ) from exc


class PaymentService:
    def __init__(
        self,
        room_service,
        customer_service,
        booking_service,
        service_request_service=None,
        waiting_service=None,
    ):
        self._room_service = room_service
        self._customer_service = customer_service
        self._booking_service = booking_service
        self._service_request_service = service_request_service
        self._waiting_service = waiting_service

        self._by_payment_id = HashTable()   # payment_id -> PaymentTransaction
        self._by_booking_id = HashTable()   # booking_id -> SinglyLinkedList[PaymentTransaction]
        self._by_customer_id = HashTable()  # customer_id -> SinglyLinkedList[PaymentTransaction]
        self._transactions = SinglyLinkedList()
        self._id_gen = SequenceGenerator("TT", 5)

        if self._booking_service is not None and hasattr(self._booking_service, "set_vip_sync_callback"):
            self._booking_service.set_vip_sync_callback(self.sync_customer_vip)

    @property
    def id_generator(self):
        return self._id_gen

    # -------------------- 1. Tính tổng chi phí hóa đơn -------------------- #
    def _match_booking_for_request(self, req, room_bookings):
        """Xác định duy nhất một đơn đặt phòng chịu phí cho yêu cầu dịch vụ `req`."""
        if req.customer_id:
            candidates = [b for b in room_bookings if b.customer_id == req.customer_id]
        else:
            candidates = list(room_bookings)

        if not candidates:
            return None

        status_rank = {
            BookingStatus.CHECKED_IN: 3,
            BookingStatus.CONFIRMED: 2,
            BookingStatus.CHECKED_OUT: 1,
        }

        covering = [b for b in candidates if b.check_in <= req.requested_at <= b.check_out]
        if covering:
            # Ưu tiên:
            # 1. Đơn đang ở (CHECKED_IN) tại phòng
            # 2. Ngày yêu cầu nằm trọn trong nửa mở [check_in, check_out) (tránh tính trùng ngày trả phòng
            #    khi khách cũ trả phòng và khách mới nhận phòng trong cùng một ngày)
            # 3. Trạng thái ưu tiên cao hơn (CHECKED_IN > CONFIRMED > CHECKED_OUT)
            # 4. Ngày check_in mới nhất
            return max(
                covering,
                key=lambda b: (
                    1 if b.status == BookingStatus.CHECKED_IN else 0,
                    1 if b.check_in <= req.requested_at < b.check_out else 0,
                    status_rank.get(b.status, 0),
                    b.check_in,
                    b.booking_id,
                ),
            )

        def _distance_days(b):
            if req.requested_at < b.check_in:
                return (b.check_in - req.requested_at).days
            return (req.requested_at - b.check_out).days

        return max(
            candidates,
            key=lambda b: (
                status_rank.get(b.status, 0),
                -_distance_days(b),
                b.check_in,
                b.booking_id,
            ),
        )

    def _service_requests_for_booking(self, booking):
        """Lấy các yêu cầu dịch vụ nội bộ phát sinh thuộc về đơn đặt phòng `booking`."""
        if self._service_request_service is None or booking.status == BookingStatus.CANCELLED:
            return []

        all_reqs = self._service_request_service.all_requests()
        room_bookings = [
            b
            for b in self._booking_service.all_bookings()
            if b.room_id == booking.room_id and b.status != BookingStatus.CANCELLED
        ]

        matched = []
        for req in all_reqs:
            if req.room_id != booking.room_id:
                continue
            owner = self._match_booking_for_request(req, room_bookings)
            if owner is not None and owner.booking_id == booking.booking_id:
                matched.append(req)

        return merge_sort(matched, key=lambda r: r.sequence)

    def calculate_total_cost(self, booking_id, extra_fee=0):
        """Tính tổng chi phí chi tiết cho một đơn đặt phòng.

        Bao gồm:
        - Tiền phòng (`room_cost` = số đêm × đơn giá phòng / đêm)
        - Phí dịch vụ nội bộ (`service_cost` = tổng phí các yêu cầu Dọn phòng, Đồ ăn, Y tế, Khác)
        - Phụ phí phát sinh khác (`extra_fee`)
        - Chiết khấu theo hạng VIP của khách hàng (`discount_amount`)
        - Tổng chi phí thực thu (`total_amount`)
        """
        if isinstance(extra_fee, bool):
            raise HotelError("Phụ phí phát sinh phải là số nguyên không âm")
        try:
            extra_fee_val = int(extra_fee or 0)
        except (ValueError, TypeError) as exc:
            raise HotelError("Phụ phí phát sinh phải là số nguyên không âm") from exc
        if extra_fee_val < 0:
            raise HotelError("Phụ phí phát sinh không được nhỏ hơn 0")

        booking = self._booking_service.get_booking(booking_id)
        customer = self._customer_service.get_customer(booking.customer_id)
        room = self._room_service.get_room(booking.room_id)

        room_cost = booking.total_price
        reqs = self._service_requests_for_booking(booking)
        service_items = []
        for req in reqs:
            fee = SERVICE_PRICE_BY_TYPE.get(req.service_type, 0)
            service_items.append(
                {
                    "request_id": req.request_id,
                    "service_type": req.service_type,
                    "urgency": req.urgency,
                    "status": req.status,
                    "fee": fee,
                    "note": req.note,
                }
            )
        service_cost = sum(item["fee"] for item in service_items)

        existing_payments = self.get_payments_by_booking(booking.booking_id)
        paid_txs = [tx for tx in existing_payments if tx.status == PaymentStatus.PAID]
        paid_extra_fee = sum(tx.extra_fee for tx in paid_txs)
        effective_extra_fee = max(extra_fee_val, paid_extra_fee)

        gross_amount = room_cost + service_cost + effective_extra_fee
        base_vip_val = (
            int(booking.vip_level_at_booking)
            if getattr(booking, "vip_level_at_booking", None) is not None
            else int(customer.vip_level)
        )
        if getattr(customer, "manual_vip_level", None) is not None:
            base_vip_val = max(base_vip_val, int(customer.manual_vip_level))
        booking_vip_level = VipLevel(base_vip_val)
        discount_rate = VIP_DISCOUNT_RATES.get(booking_vip_level, 0.0)

        if not paid_txs:
            discount_amount = int(round(gross_amount * discount_rate))
            total_amount = max(0, gross_amount - discount_amount)
            paid_amount = 0
            remaining_amount = total_amount
        else:
            paid_gross = sum(tx.gross_amount for tx in paid_txs)
            paid_discount = sum(tx.discount_amount for tx in paid_txs)
            paid_amount = sum(tx.total_amount for tx in paid_txs)
            delta_gross = max(0, gross_amount - paid_gross)
            delta_discount = int(round(delta_gross * discount_rate))
            discount_amount = paid_discount + delta_discount
            remaining_amount = max(0, delta_gross - delta_discount)
            total_amount = paid_amount + remaining_amount

        active_tx = paid_txs[0] if paid_txs else None
        is_fully_paid = active_tx is not None and remaining_amount == 0

        if is_fully_paid:
            payment_status = PaymentStatus.PAID
        elif any(tx.status == PaymentStatus.REFUNDED for tx in existing_payments) and active_tx is None:
            payment_status = PaymentStatus.REFUNDED
        else:
            payment_status = PaymentStatus.UNPAID

        prior_spending = (
            self.get_customer_effective_spending(
                customer.customer_id, exclude_unpaid_booking_id=booking.booking_id
            )
            if not is_fully_paid
            else self.get_customer_effective_spending(customer.customer_id)
        )
        customer_total_paid = prior_spending
        projected_total_paid = prior_spending + remaining_amount
        qualifying_after = max(
            projected_total_paid,
            self.get_customer_qualifying_spending(customer.customer_id),
        )
        earned_after = evaluate_vip_level_by_spending(qualifying_after)
        projected_vip = VipLevel(max(int(customer.vip_level), int(earned_after)))
        applied_discount_rate = (
            round(discount_amount / gross_amount, 4)
            if (is_fully_paid and gross_amount > 0)
            else discount_rate
        )

        return {
            "booking": booking,
            "customer": customer,
            "room": room,
            "num_nights": booking.num_nights,
            "price_per_night": booking.price_per_night,
            "room_cost": room_cost,
            "service_items": service_items,
            "service_cost": service_cost,
            "extra_fee": effective_extra_fee,
            "gross_amount": gross_amount,
            "vip_level": booking_vip_level,
            "discount_rate": discount_rate,
            "applied_discount_rate": applied_discount_rate,
            "discount_amount": discount_amount,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount,
            "is_paid": is_fully_paid,
            "payment_status": payment_status,
            "active_payment": active_tx,
            "customer_total_paid": customer_total_paid,
            "projected_total_paid": projected_total_paid,
            "projected_vip_level": projected_vip,
            "will_upgrade_vip": projected_vip > booking_vip_level,
        }

    # -------------------- 2. Xử lý & Lưu trữ giao dịch -------------------- #
    def process_payment(
        self,
        booking_id,
        payment_method=PaymentMethod.CASH,
        extra_fee=0,
        note="",
        paid_at=None,
    ):
        """Xử lý thanh toán cho đơn đặt phòng, lưu giao dịch và tự động xét nâng hạng VIP tích lũy."""
        booking = self._booking_service.get_booking(booking_id)
        if booking.status == BookingStatus.CANCELLED:
            raise HotelError(
                f"Không thể thanh toán cho đơn đặt phòng {booking.booking_id} vì đơn đã bị hủy"
            )

        method = _parse_payment_method(payment_method)
        paid_txs = self.get_active_payments_for_booking(booking.booking_id)
        bill = self.calculate_total_cost(booking.booking_id, extra_fee=extra_fee)

        if paid_txs and bill["remaining_amount"] <= 0:
            raise HotelError(
                f"Đơn đặt phòng {booking.booking_id} đã được thanh toán "
                f"(Mã giao dịch: {paid_txs[0].payment_id})"
            )

        paid_room_cost = sum(t.room_cost for t in paid_txs)
        paid_service_cost = sum(t.service_cost for t in paid_txs)
        paid_extra_fee = sum(t.extra_fee for t in paid_txs)
        paid_discount = sum(t.discount_amount for t in paid_txs)

        tx = PaymentTransaction(
            payment_id=self._id_gen.next_id(),
            booking_id=booking.booking_id,
            customer_id=booking.customer_id,
            room_id=booking.room_id,
            room_cost=max(0, bill["room_cost"] - paid_room_cost),
            service_cost=max(0, bill["service_cost"] - paid_service_cost),
            extra_fee=max(0, bill["extra_fee"] - paid_extra_fee),
            discount_amount=max(0, bill["discount_amount"] - paid_discount),
            total_amount=bill["remaining_amount"],
            payment_method=method,
            paid_at=paid_at or date.today(),
            status=PaymentStatus.PAID,
            note=(note or "").strip(),
        )
        self._store_transaction(tx)
        self.sync_customer_vip(booking.customer_id)
        return tx

    def _store_transaction(self, tx):
        """Lưu giao dịch vào 3 bảng băm chỉ mục O(1) và đầu danh sách liên kết đơn O(1)."""
        self._by_payment_id.put(tx.payment_id, tx)

        booking_list = self._by_booking_id.get(tx.booking_id)
        if booking_list is None:
            booking_list = SinglyLinkedList()
            self._by_booking_id.put(tx.booking_id, booking_list)
        booking_list.push_front(tx)

        customer_list = self._by_customer_id.get(tx.customer_id)
        if customer_list is None:
            customer_list = SinglyLinkedList()
            self._by_customer_id.put(tx.customer_id, customer_list)
        customer_list.push_front(tx)

        self._transactions.push_front(tx)

    def refund_payment(self, identifier, reason=""):
        """Hoàn tiền cho một giao dịch thanh toán (theo mã TT... hoặc mã đơn BK...)."""
        key = (identifier or "").strip().upper()
        if not key:
            raise HotelError("Vui lòng nhập mã giao dịch hoặc mã đơn đặt phòng cần hoàn tiền")

        tx = self._by_payment_id.get(key)
        if tx is None:
            tx = self.get_active_payment_for_booking(key)
        if tx is None:
            raise NotFoundError(
                f"Không tìm thấy giao dịch thanh toán đang hiệu lực cho '{identifier}'"
            )
        if tx.status == PaymentStatus.REFUNDED:
            raise HotelError(f"Giao dịch {tx.payment_id} đã ở trạng thái Đã hoàn tiền")

        tx.status = PaymentStatus.REFUNDED
        clean_reason = (reason or "").strip()
        if clean_reason:
            tx.note = f"{tx.note} | Hoàn tiền: {clean_reason}" if tx.note else f"Hoàn tiền: {clean_reason}"
        try:
            self.sync_customer_vip(tx.customer_id, allow_downgrade=False)
        except NotFoundError:
            pass
        return tx

    # -------------------- 3. Tra cứu giao dịch thanh toán ---------------- #
    def get_payment(self, payment_id):
        """Tra cứu trực tiếp giao dịch theo mã `payment_id` (vd TT00001) — O(1) trung bình."""
        key = (payment_id or "").strip().upper()
        tx = self._by_payment_id.get(key)
        if tx is None:
            raise NotFoundError(f"Không tìm thấy giao dịch thanh toán '{payment_id}'")
        return tx

    def get_payments_by_booking(self, booking_id):
        """Lấy danh sách các giao dịch của một đơn đặt phòng — O(1) trung bình."""
        key = (booking_id or "").strip().upper()
        ll = self._by_booking_id.get(key)
        return ll.to_list() if ll is not None else []

    def get_active_payments_for_booking(self, booking_id):
        """Trả về danh sách các giao dịch PAID đang hiệu lực của đơn đặt phòng — O(1) trung bình."""
        return [
            tx
            for tx in self.get_payments_by_booking(booking_id)
            if tx.status == PaymentStatus.PAID
        ]

    def get_active_payment_for_booking(self, booking_id):
        """Trả về giao dịch PAID hiện hành mới nhất của đơn đặt phòng (hoặc None) — O(1) trung bình."""
        active = self.get_active_payments_for_booking(booking_id)
        return active[0] if active else None

    def is_booking_paid(self, booking_id):
        """Kiểm tra đơn đặt phòng đã được thanh toán đầy đủ hay chưa."""
        active = self.get_active_payments_for_booking(booking_id)
        if not active:
            return False
        bill = self.calculate_total_cost(booking_id)
        return bill["is_paid"]

    def get_payments_by_customer(self, customer_identifier):
        """Tra cứu lịch sử giao dịch thanh toán của khách hàng (theo Mã KH / CCCD / SĐT) — O(1) TB."""
        customer = self._customer_service.lookup(customer_identifier)
        ll = self._by_customer_id.get(customer.customer_id)
        return ll.to_list() if ll is not None else []

    def get_customer_paid_transactions_total(self, customer_identifier):
        """Tính tổng số tiền từ các giao dịch thanh toán PAID của một khách hàng."""
        customer = self._customer_service.lookup(customer_identifier)
        ll = self._by_customer_id.get(customer.customer_id)
        if ll is None:
            return 0
        return sum(tx.total_amount for tx in ll if tx.status == PaymentStatus.PAID)

    def get_customer_booking_spending(self, customer_identifier, exclude_booking_id=None):
        """Tính tổng giá trị các đơn đặt phòng đang hiệu lực (không bị hủy / hoàn tiền) của khách."""
        customer = self._customer_service.lookup(customer_identifier)
        total = 0
        for b in customer.history:
            if b.status == BookingStatus.CANCELLED:
                continue
            if exclude_booking_id is not None and b.booking_id == exclude_booking_id:
                continue
            txs = self.get_payments_by_booking(b.booking_id)
            has_paid = any(tx.status == PaymentStatus.PAID for tx in txs)
            has_refunded = any(tx.status == PaymentStatus.REFUNDED for tx in txs)
            if has_refunded and not has_paid:
                continue
            total += b.total_price
        return total

    def get_customer_effective_spending(self, customer_identifier, exclude_unpaid_booking_id=None):
        """Tính tổng chi tiêu lũy kế thực tế (đơn đã TT tính theo số tiền TT, đơn chưa TT tính theo giá đặt)."""
        customer = self._customer_service.lookup(customer_identifier)
        total = 0
        counted_booking_ids = set()
        for b in customer.history:
            if b.status == BookingStatus.CANCELLED:
                continue
            counted_booking_ids.add(b.booking_id)
            txs = self.get_payments_by_booking(b.booking_id)
            paid_amt = sum(tx.total_amount for tx in txs if tx.status == PaymentStatus.PAID)
            has_refunded = any(tx.status == PaymentStatus.REFUNDED for tx in txs)
            if paid_amt > 0:
                total += paid_amt
            elif has_refunded:
                continue
            else:
                if exclude_unpaid_booking_id is not None and b.booking_id == exclude_unpaid_booking_id:
                    continue
                total += b.total_price

        ll = self._by_customer_id.get(customer.customer_id)
        if ll is not None:
            for tx in ll:
                if tx.status == PaymentStatus.PAID and tx.booking_id not in counted_booking_ids:
                    total += tx.total_amount
        return total

    def get_customer_qualifying_spending(self, customer_identifier):
        """Tổng chi tiêu dùng để xét nâng hạng VIP tự động = max(đã thanh toán, tổng đặt phòng hiệu lực)."""
        paid_tx_total = self.get_customer_paid_transactions_total(customer_identifier)
        booking_total = self.get_customer_booking_spending(customer_identifier)
        effective_total = self.get_customer_effective_spending(customer_identifier)
        return max(paid_tx_total, booking_total, effective_total)

    def get_customer_total_paid(self, customer_identifier):
        """Tính tổng chi tiêu lũy kế của khách hàng (bao gồm giao dịch PAID và đơn đặt phòng hiệu lực)."""
        return self.get_customer_effective_spending(customer_identifier)

    def get_customer_vip_progress(self, customer_identifier):
        """Lấy thông tin chi tiêu tích lũy và tiến độ lên hạng VIP tiếp theo của khách."""
        customer = self._customer_service.lookup(customer_identifier)
        ll = self._by_customer_id.get(customer.customer_id)
        paid_txs = [tx for tx in ll if tx.status == PaymentStatus.PAID] if ll is not None else []
        effective_paid = self.get_customer_effective_spending(customer.customer_id)
        qualifying_spending = self.get_customer_qualifying_spending(customer.customer_id)
        progress = get_vip_tier_progress(customer.vip_level, qualifying_spending)
        progress["total_paid"] = effective_paid
        progress["qualifying_spending"] = qualifying_spending
        return {
            "customer": customer,
            "customer_id": customer.customer_id,
            "paid_transaction_count": len(paid_txs),
            **progress,
        }

    def sync_customer_vip(self, customer_identifier, allow_downgrade=False):
        """Tự động xét và nâng hạng VIP cho khách hàng khi tổng chi tiêu đặt phòng / thanh toán đạt mốc.

        Đồng bộ ngay mức độ ưu tiên trong `WaitingService` (chuyển từ LinkedQueue sang MaxHeap
        hoặc vun lại đống MaxHeap nếu khách đang nằm trong danh sách chờ).
        """
        customer = self._customer_service.lookup(customer_identifier)
        qualifying_spending = self.get_customer_qualifying_spending(customer.customer_id)
        res = self._customer_service.evaluate_and_update_vip(
            customer.customer_id,
            qualifying_spending,
            allow_downgrade=allow_downgrade,
        )
        res["total_paid"] = self.get_customer_effective_spending(customer.customer_id)
        res["qualifying_spending"] = qualifying_spending
        if res["changed"] and self._waiting_service is not None:
            self._waiting_service.update_customer_priority(
                customer.customer_id, int(res["new_vip"])
            )
        return res

    def lookup_payments(self, query):
        """Tra cứu thanh toán đa năng theo Mã GD (TT...), Mã đơn (BK...), Mã KH/CCCD/SĐT hoặc Mã phòng."""
        raw = (query or "").strip()
        if not raw:
            raise NotFoundError("Từ khóa tra cứu thanh toán không được để trống")
        upper = raw.upper()

        # 1. Tra cứu O(1) theo mã giao dịch TT...
        tx = self._by_payment_id.get(upper)
        if tx is not None:
            return [tx]

        # 2. Tra cứu O(1) theo mã đơn đặt phòng BK...
        by_booking = self.get_payments_by_booking(upper)
        if by_booking:
            return by_booking

        # 3. Tra cứu O(1) theo khách hàng (Mã KH / CCCD / SĐT)
        try:
            customer = self._customer_service.lookup(raw)
            by_cust = self._by_customer_id.get(customer.customer_id)
            if by_cust is not None and len(by_cust) > 0:
                return by_cust.to_list()
        except NotFoundError:
            pass

        # 4. Tra cứu theo mã phòng hoặc tên khách hàng
        matched = []
        raw_lower = raw.lower()
        for item in self._transactions:
            if item.room_id.upper() == upper:
                matched.append(item)
                continue
            try:
                cust_name = self._customer_service.get_customer(item.customer_id).full_name.lower()
                if raw_lower in cust_name:
                    matched.append(item)
            except NotFoundError:
                pass

        if not matched:
            raise NotFoundError(f"Không tìm thấy giao dịch thanh toán nào khớp với '{query}'")
        return matched

    def filter_transactions(
        self,
        payment_method=None,
        status=None,
        start_date=None,
        end_date=None,
    ):
        """Lọc danh sách giao dịch theo phương thức, trạng thái và khoảng ngày thanh toán."""
        if start_date is not None and end_date is not None and start_date > end_date:
            raise HotelError("Ngày bắt đầu lọc không được lớn hơn ngày kết thúc")
        method_filter = _parse_payment_method(payment_method) if payment_method is not None else None
        status_filter = _parse_payment_status(status) if status is not None else None
        result = []
        for tx in self._transactions:
            if method_filter is not None and tx.payment_method != method_filter:
                continue
            if status_filter is not None and tx.status != status_filter:
                continue
            if start_date is not None and tx.paid_at < start_date:
                continue
            if end_date is not None and tx.paid_at > end_date:
                continue
            result.append(tx)
        return result

    def sort_transactions(self, transactions=None, by="paid_at", reverse=False):
        """Sắp xếp danh sách giao dịch bằng Merge Sort O(p log p)."""
        items = list(transactions) if transactions is not None else self.all_transactions()
        field_key = (by or "paid_at").strip().lower()
        key_map = {
            "paid_at": lambda tx: (tx.paid_at, tx.payment_id),
            "date": lambda tx: (tx.paid_at, tx.payment_id),
            "total_amount": lambda tx: (tx.total_amount, tx.payment_id),
            "amount": lambda tx: (tx.total_amount, tx.payment_id),
            "payment_id": lambda tx: tx.payment_id,
            "id": lambda tx: tx.payment_id,
            "booking_id": lambda tx: (tx.booking_id, tx.payment_id),
        }
        if field_key not in key_map:
            raise HotelError(
                f"Tiêu chí sắp xếp giao dịch '{by}' không hợp lệ "
                f"(chọn paid_at, total_amount, payment_id hoặc booking_id)"
            )
        return merge_sort(items, key=key_map[field_key], reverse=reverse)

    def all_transactions(self):
        """Toàn bộ giao dịch lưu trong SinglyLinkedList (mới nhất -> cũ nhất)."""
        return self._transactions.to_list()

    def payment_summary(self):
        """Thống kê tổng hợp tình hình thanh toán và công nợ."""
        by_method = {m: 0 for m in PaymentMethod}
        count_by_method = {m: 0 for m in PaymentMethod}
        total_collected = 0
        total_refunded = 0
        total_discount = 0
        total_service_fee = 0
        paid_count = 0
        refunded_count = 0

        for tx in self._transactions:
            if tx.status == PaymentStatus.PAID:
                paid_count += 1
                total_collected += tx.total_amount
                total_discount += tx.discount_amount
                total_service_fee += tx.service_cost + tx.extra_fee
                by_method[tx.payment_method] += tx.total_amount
                count_by_method[tx.payment_method] += 1
            elif tx.status == PaymentStatus.REFUNDED:
                refunded_count += 1
                total_refunded += tx.total_amount

        unpaid_bookings = []
        unpaid_estimated_total = 0
        for booking in self._booking_service.all_bookings():
            if booking.status == BookingStatus.CANCELLED:
                continue
            bill = self.calculate_total_cost(booking.booking_id)
            if bill["remaining_amount"] > 0:
                unpaid_bookings.append(booking)
                unpaid_estimated_total += bill["remaining_amount"]

        return {
            "total_transactions": len(self._transactions),
            "paid_transactions": paid_count,
            "refunded_transactions": refunded_count,
            "total_collected": total_collected,
            "total_refunded": total_refunded,
            "total_discount": total_discount,
            "total_service_fee": total_service_fee,
            "revenue_by_method": by_method,
            "count_by_method": count_by_method,
            "unpaid_bookings_count": len(unpaid_bookings),
            "unpaid_estimated_total": unpaid_estimated_total,
        }

    # -------------------- 4. Khôi phục từ JSON Persistence --------------- #
    def load_payments(self, payment_dicts, sequence_value):
        """Khôi phục các bảng băm và danh sách liên kết giao dịch khi đọc file JSON."""
        self._by_payment_id = HashTable()
        self._by_booking_id = HashTable()
        self._by_customer_id = HashTable()
        self._transactions = SinglyLinkedList()
        self._id_gen.restore(sequence_value)

        # payment_dicts được lưu từ mới nhất -> cũ nhất; nạp ngược để giữ đúng thứ tự push_front
        touched_customers = set()
        for item in reversed(payment_dicts):
            tx = PaymentTransaction.from_dict(item)
            self._store_transaction(tx)
            touched_customers.add(tx.customer_id)
            if tx.payment_id.startswith("TT") and tx.payment_id[2:].isdigit():
                self._id_gen.restore(int(tx.payment_id[2:]))

        for cust in self._customer_service.all_customers():
            try:
                self.sync_customer_vip(cust.customer_id, allow_downgrade=False)
            except NotFoundError:
                pass
        for cid in touched_customers:
            try:
                self.sync_customer_vip(cid, allow_downgrade=False)
            except NotFoundError:
                pass

    def __len__(self):
        return len(self._transactions)
