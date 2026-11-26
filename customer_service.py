"""Chức năng 5: Quản lý khách hàng (Hash Table) và Lịch sử lưu trú (Linked List).

Độ phức tạp mục tiêu:
- Tra cứu khách hàng theo Mã KH / CCCD / SĐT : O(1) trung bình (HashTable chaining)
- Đăng ký khách hàng mới                     : O(1) trung bình
- Thêm lượt đặt vào đầu lịch sử lưu trú      : O(1) (SinglyLinkedList.push_front)
- Duyệt lịch sử lưu trú của một khách        : O(m) với m là số lượt đặt của khách đó
"""

from hotel.config import evaluate_vip_level_by_spending, get_vip_tier_progress
from hotel.data_structures.hash_table import HashTable
from hotel.models.customer import Customer
from hotel.models.enums import VipLevel
from hotel.services.errors import HotelError, NotFoundError
from hotel.services.id_generator import SequenceGenerator


def _clean_text(value, field_name):
    cleaned = (value or "").strip()
    if not cleaned:
        raise HotelError(f"{field_name} không được để trống")
    return cleaned


def _normalize_digits(raw_value, is_phone=False):
    """Chuẩn hóa chuỗi số (bỏ khoảng trắng, dấu gạch ngang, dấu chấm, ngoặc và đổi +84 -> 0)."""
    text = (raw_value or "").strip()
    for ch in (" ", "-", ".", "(", ")"):
        text = text.replace(ch, "")
    if is_phone and text.startswith("+84"):
        text = "0" + text[3:]
    return text


def _clean_digits(value, field_name, min_len=8, max_len=15, is_phone=False):
    cleaned = _normalize_digits(value, is_phone=is_phone)
    if not cleaned.isdigit() or not (min_len <= len(cleaned) <= max_len):
        raise HotelError(
            f"{field_name} phải gồm từ {min_len} đến {max_len} chữ số "
            f"(ví dụ: 0901234567 hoặc +84 901 234 567; nhận: '{value}')"
        )
    return cleaned


class CustomerService:
    def __init__(self):
        self._by_id = HashTable()
        self._by_cccd = HashTable()
        self._by_phone = HashTable()
        self._id_gen = SequenceGenerator("KH", 3)

    @property
    def id_generator(self):
        return self._id_gen

    # ---------------------- Đăng ký & Cập nhật -------------------------- #
    def register_customer(self, full_name, cccd, phone, vip_level=VipLevel.NORMAL):
        """Đăng ký khách hàng mới — O(1) trung bình."""
        name = _clean_text(full_name, "Họ tên")
        cccd_norm = _clean_digits(cccd, "Số CCCD", min_len=8, max_len=15, is_phone=False)
        phone_norm = _clean_digits(phone, "Số điện thoại", min_len=8, max_len=15, is_phone=True)
        vip = VipLevel(int(vip_level))

        if self._by_cccd.contains(cccd_norm):
            existing = self._by_cccd.get(cccd_norm)
            raise HotelError(f"CCCD {cccd_norm} đã được đăng ký cho khách {existing.customer_id} ({existing.full_name})")
        if self._by_phone.contains(phone_norm):
            existing = self._by_phone.get(phone_norm)
            raise HotelError(f"SĐT {phone_norm} đã được đăng ký cho khách {existing.customer_id} ({existing.full_name})")

        customer = Customer(
            customer_id=self._id_gen.next_id(),
            full_name=name,
            cccd=cccd_norm,
            phone=phone_norm,
            vip_level=vip,
        )
        self._index_customer(customer)
        return customer

    def _index_customer(self, customer):
        self._by_id.put(customer.customer_id, customer)
        self._by_cccd.put(customer.cccd, customer)
        self._by_phone.put(customer.phone, customer)

    def set_vip_level(self, customer_id, vip_level, is_manual=True):
        """Cập nhật cấp VIP của khách hàng — O(1) trung bình."""
        customer = self.get_customer(customer_id)
        new_vip = VipLevel(int(vip_level))
        customer.vip_level = new_vip
        if is_manual:
            customer.manual_vip_level = new_vip
            for booking in customer.history:
                if getattr(booking, "status", None) is not None and str(booking.status) != "BookingStatus.CANCELLED":
                    booking.vip_level_at_booking = int(new_vip)
        return customer

    def evaluate_and_update_vip(self, customer_identifier, total_paid, allow_downgrade=False):
        """Đánh giá tổng chi tiêu đã thanh toán và tự động cập nhật hạng VIP cho khách hàng."""
        customer = self.lookup(customer_identifier)
        earned_vip = evaluate_vip_level_by_spending(total_paid)
        old_vip = customer.vip_level
        if allow_downgrade:
            target_vip = earned_vip
        else:
            floor_vip = getattr(customer, "manual_vip_level", old_vip)
            target_vip = VipLevel(max(int(floor_vip), int(earned_vip)))

        changed = target_vip != old_vip
        upgraded = target_vip > old_vip
        if changed:
            customer.vip_level = target_vip

        return {
            "customer": customer,
            "old_vip": old_vip,
            "new_vip": customer.vip_level,
            "earned_vip": earned_vip,
            "total_paid": max(0, int(total_paid or 0)),
            "upgraded": upgraded,
            "changed": changed,
        }

    def get_vip_progress(self, customer_identifier, total_paid=0):
        """Tính tiến độ tích lũy và số tiền còn thiếu để lên hạng VIP tiếp theo."""
        customer = self.lookup(customer_identifier)
        progress = get_vip_tier_progress(customer.vip_level, total_paid)
        return {
            "customer": customer,
            "customer_id": customer.customer_id,
            **progress,
        }

    def update_phone(self, customer_id, new_phone):
        """Đổi số điện thoại và cập nhật bảng băm — O(1) trung bình."""
        customer = self.get_customer(customer_id)
        phone_norm = _clean_digits(new_phone, "Số điện thoại", min_len=8, max_len=15, is_phone=True)
        existing = self._by_phone.get(phone_norm)
        if existing is not None and existing.customer_id != customer.customer_id:
            raise HotelError(f"SĐT {phone_norm} đã thuộc về khách {existing.customer_id}")
        self._by_phone.remove(customer.phone)
        customer.phone = phone_norm
        self._by_phone.put(phone_norm, customer)
        return customer

    # ---------------------- Tra cứu O(1) trung bình --------------------- #
    def get_customer(self, customer_id):
        """Tra cứu theo mã khách hàng (vd 'KH001'), hoặc dự phòng theo CCCD/SĐT — O(1) trung bình."""
        key = (customer_id or "").strip()
        customer = self._by_id.get(key.upper())
        if customer is None:
            norm_phone = _normalize_digits(key, is_phone=True)
            norm_digits = _normalize_digits(key, is_phone=False)
            customer = (
                self._by_cccd.get(key)
                or self._by_phone.get(key)
                or self._by_cccd.get(norm_digits)
                or self._by_phone.get(norm_phone)
            )
        if customer is None:
            raise NotFoundError(f"Không tìm thấy khách hàng có mã/CCCD/SĐT '{customer_id}'")
        return customer

    def find_by_cccd(self, cccd):
        """Tra cứu theo CCCD — O(1) trung bình. Trả về Customer hoặc None."""
        raw = (cccd or "").strip()
        return self._by_cccd.get(raw) or self._by_cccd.get(_normalize_digits(raw, is_phone=False))

    def find_by_phone(self, phone):
        """Tra cứu theo SĐT — O(1) trung bình. Trả về Customer hoặc None."""
        raw = (phone or "").strip()
        return self._by_phone.get(raw) or self._by_phone.get(_normalize_digits(raw, is_phone=True))

    def lookup(self, identifier):
        """Tra cứu linh hoạt theo Mã KH, CCCD hoặc SĐT — O(1) trung bình."""
        key = (identifier or "").strip()
        if not key:
            raise NotFoundError("Thông tin tra cứu khách hàng đang để trống")
        norm_phone = _normalize_digits(key, is_phone=True)
        norm_digits = _normalize_digits(key, is_phone=False)
        customer = (
            self._by_id.get(key.upper())
            or self._by_cccd.get(key)
            or self._by_phone.get(key)
            or self._by_cccd.get(norm_digits)
            or self._by_phone.get(norm_phone)
        )
        if customer is None:
            raise NotFoundError(f"Không tìm thấy khách hàng với mã/CCCD/SĐT '{identifier}'")
        return customer

    # --------------- Lịch sử lưu trú (SinglyLinkedList) ----------------- #
    def record_booking(self, customer_id, booking):
        """Chèn đơn đặt phòng vào ĐẦU danh sách liên kết lịch sử — O(1)."""
        customer = self.get_customer(customer_id)
        # Tránh nhân bản nút trong lịch sử khi hoàn tác (undo) một đơn đã từng lưu
        if customer.history.find(lambda b: b.booking_id == booking.booking_id) is None:
            customer.add_booking_to_history(booking)
        return customer

    def get_stay_history(self, customer_id):
        """Duyệt danh sách liên kết lịch sử của khách (mới nhất -> cũ nhất) — O(m)."""
        customer = self.get_customer(customer_id)
        return customer.history.to_list()

    def all_customers(self):
        return self._by_id.values()

    def load_customers(self, customers, sequence_value, bookings_by_id):
        """Khôi phục các bảng băm và danh sách liên kết lịch sử khi nạp file JSON."""
        self._by_id = HashTable()
        self._by_cccd = HashTable()
        self._by_phone = HashTable()
        self._id_gen.restore(sequence_value)
        for item in customers:
            customer = Customer.from_dict(item)
            for booking_id in item.get("history", []):
                booking = bookings_by_id.get(booking_id)
                if booking is not None:
                    customer.add_booking_to_history(booking)
            self._index_customer(customer)
            if customer.customer_id.startswith("KH") and customer.customer_id[2:].isdigit():
                self._id_gen.restore(int(customer.customer_id[2:]))

    def __len__(self):
        return len(self._by_id)
