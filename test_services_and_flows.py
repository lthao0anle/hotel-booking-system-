"""Kiểm thử toàn diện các luồng nghiệp vụ khách sạn, lưu trữ JSON và trường hợp biên."""

from datetime import date, timedelta
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hotel.models.enums import (
    BookingStatus,
    PaymentMethod,
    PaymentStatus,
    RoomStatus,
    RoomType,
    ServiceType,
    UrgencyLevel,
    VipLevel,
)
from hotel.services.errors import HotelError, NotFoundError, RoomUnavailableError
from hotel.services.hotel_manager import HotelManager


class TestHotelBusinessFlows(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 11, 10)
        self.manager = HotelManager(
            floors=3,
            rooms_per_floor=5,
            data_file=None,
            auto_save=False,
        )

    def test_room_matrix_and_price_filtering(self):
        room = self.manager.get_room("P203")
        self.assertEqual((room.floor, room.room_number), (2, 3))
        self.assertEqual(self.manager.get_room_by_coords(2, 3).room_id, "P203")

        with self.assertRaises(NotFoundError):
            self.manager.get_room("P999")

        filtered = self.manager.filter_rooms_by_price(500_000, 900_000, room_type=RoomType.DOUBLE)
        self.assertTrue(all(r.room_type == RoomType.DOUBLE for r in filtered))
        self.assertTrue(all(500_000 <= r.price_per_night <= 900_000 for r in filtered))

        closest = self.manager.suggest_room_by_budget(820_000)
        self.assertIsNotNone(closest)

    def test_booking_conflict_and_checkin_checkout(self):
        c1 = self.manager.register_customer("Nguyễn An", "001200000001", "0900000001", VipLevel.NORMAL)
        c2 = self.manager.register_customer("Trần Bình", "001200000002", "0900000002", VipLevel.GOLD)

        d1 = self.today
        d2 = self.today + timedelta(days=3)
        d3 = self.today + timedelta(days=5)

        b1 = self.manager.book_room(c1.customer_id, "P101", d1, d2)
        self.assertEqual(b1.status, BookingStatus.CONFIRMED)
        self.assertEqual(self.manager.bookings.room_status_on("P101", d1), RoomStatus.BOOKED)

        # Đặt trùng khoảng ngày trên cùng phòng phải bị chặn bởi BST IntervalSchedule
        with self.assertRaises(RoomUnavailableError):
            self.manager.book_room(c2.customer_id, "P101", d1 + timedelta(days=1), d3)

        # Đặt nối tiếp ngày trả phòng (check_in mới == check_out cũ) phải thành công
        b2 = self.manager.book_room(c2.customer_id, "P101", d2, d3)
        self.assertEqual(b2.room_id, "P101")

        # Luồng Check-in -> Check-out: sau khi trả phòng, phòng phải trở lại TRỐNG và cho phép đặt mới
        self.manager.check_in(b1.booking_id)
        self.assertEqual(b1.status, BookingStatus.CHECKED_IN)
        self.manager.check_out(b1.booking_id)
        self.assertEqual(b1.status, BookingStatus.CHECKED_OUT)
        self.assertEqual(self.manager.bookings.room_status_on("P101", d1), RoomStatus.EMPTY)
        self.assertTrue(self.manager.bookings.is_room_available("P101", d1, d2))

    def test_cancel_and_undo_stack_with_conflict_guard(self):
        c1 = self.manager.register_customer("Lê C", "001200000003", "0900000003")
        c2 = self.manager.register_customer("Phạm D", "001200000004", "0900000004")
        ci, co = self.today + timedelta(days=1), self.today + timedelta(days=4)

        b1 = self.manager.book_room(c1.customer_id, "P102", ci, co)
        action, _ = self.manager.cancel_booking(b1.booking_id)
        self.assertEqual(action.booking_id, b1.booking_id)
        self.assertEqual(b1.status, BookingStatus.CANCELLED)
        self.assertTrue(self.manager.bookings.is_room_available("P102", ci, co))

        # Hoàn tác thành công khi phòng vẫn trống
        _, restored = self.manager.undo_last_cancellation()
        self.assertEqual(restored.status, BookingStatus.CONFIRMED)
        self.assertFalse(self.manager.bookings.is_room_available("P102", ci, co))

        # Hủy lần nữa, rồi cho khách khác đặt đè vào phòng P102 -> Undo phải báo lỗi và giữ nguyên Stack
        self.manager.cancel_booking(b1.booking_id)
        self.manager.book_room(c2.customer_id, "P102", ci, co)
        with self.assertRaises(RoomUnavailableError):
            self.manager.undo_last_cancellation()
        self.assertEqual(len(self.manager.undo), 1)

    def test_vip_waiting_queue_and_priority_upgrade(self):
        c_norm = self.manager.register_customer("Khách Thường", "001200000010", "0900000010", VipLevel.NORMAL)
        c_silv = self.manager.register_customer("Khách Silver", "001200000011", "0900000011", VipLevel.SILVER)
        c_plat = self.manager.register_customer("Khách Platinum", "001200000012", "0900000012", VipLevel.PLATINUM)

        ci, co = self.today + timedelta(days=2), self.today + timedelta(days=4)
        self.manager.add_to_waiting_list(c_norm.customer_id, RoomType.SUITE, ci, co)
        self.manager.add_to_waiting_list(c_silv.customer_id, RoomType.SUITE, ci, co)
        self.manager.add_to_waiting_list(c_plat.customer_id, RoomType.SUITE, ci, co)

        ordered = self.manager.waiting.list_waiting_ordered()
        self.assertEqual(
            [e.customer_id for e in ordered],
            [c_plat.customer_id, c_silv.customer_id, c_norm.customer_id],
        )

        # Nâng cấp khách thường lên GOLD -> tự động chuyển từ Queue thường sang VIP Max-Heap
        self.manager.set_customer_vip(c_norm.customer_id, VipLevel.GOLD)
        ordered_after = self.manager.waiting.list_waiting_ordered()
        self.assertEqual(
            [e.customer_id for e in ordered_after],
            [c_plat.customer_id, c_norm.customer_id, c_silv.customer_id],
        )

        # Thêm mục chờ thứ 2 cho c_plat rồi hạ cấp c_plat xuống SILVER -> không làm hỏng tính chất Max-Heap
        self.manager.add_to_waiting_list(c_plat.customer_id, RoomType.SINGLE, ci, co)
        self.manager.set_customer_vip(c_plat.customer_id, VipLevel.SILVER)
        self.assertEqual(self.manager.waiting.peek_next().customer_id, c_norm.customer_id)

        # Hạ cấp khách VIP về NORMAL (0) -> phải chuyển khỏi Max-Heap sang LinkedQueue theo đúng sequence
        self.manager.set_customer_vip(c_silv.customer_id, VipLevel.NORMAL)
        self.assertTrue(
            all(e.priority > 0 for e in self.manager.waiting._vip_heap)
        )
        self.assertEqual(self.manager.waiting.normal_count(), 1)

    def test_service_request_priority_queue(self):
        self.manager.submit_service_request("P101", ServiceType.CLEANING, UrgencyLevel.LOW, "Dọn phòng")
        self.manager.submit_service_request("P102", ServiceType.FOOD, UrgencyLevel.NORMAL, "Đồ ăn")
        self.manager.submit_service_request("P103", ServiceType.MEDICAL, UrgencyLevel.EMERGENCY, "Cấp cứu")

        first = self.manager.process_next_service_request()
        second = self.manager.process_next_service_request()
        third = self.manager.process_next_service_request()
        self.assertEqual([first.room_id, second.room_id, third.room_id], ["P103", "P102", "P101"])

    def test_payment_calculation_processing_storage_and_lookup(self):
        c_gold = self.manager.register_customer(
            "Lê Hoàng Nam", "001200033333", "+84 912 345 678", VipLevel.GOLD
        )
        c_norm = self.manager.register_customer(
            "Nguyễn Văn Bình", "001200044444", "0987654321", VipLevel.NORMAL
        )
        ci = self.today
        co = self.today + timedelta(days=2)  # 2 đêm

        # Phòng P101 (tầng 1, SINGLE, 500.000đ/đêm) -> 2 đêm = 1.000.000đ
        b1 = self.manager.book_room(c_gold.customer_id, "P101", ci, co)
        self.manager.check_in(b1.booking_id)

        # Thêm 2 yêu cầu dịch vụ cho P101: FOOD (150.000đ) + CLEANING (50.000đ) = 200.000đ
        self.manager.submit_service_request(
            "P101", ServiceType.FOOD, UrgencyLevel.NORMAL, "Đồ ăn tối", customer_id=c_gold.customer_id
        )
        self.manager.submit_service_request(
            "P101", ServiceType.CLEANING, UrgencyLevel.LOW, "Dọn phòng", customer_id=c_gold.customer_id
        )

        # 1. Tính tổng chi phí (có phụ phí 100.000đ, giảm 5% hạng GOLD)
        bill = self.manager.calculate_booking_cost(b1.booking_id, extra_fee=100_000)
        self.assertEqual(bill["room_cost"], 1_000_000)
        self.assertEqual(bill["service_cost"], 200_000)
        self.assertEqual(bill["extra_fee"], 100_000)
        self.assertEqual(bill["gross_amount"], 1_300_000)
        self.assertEqual(bill["discount_amount"], 65_000)
        self.assertEqual(bill["total_amount"], 1_235_000)
        self.assertFalse(bill["is_paid"])
        self.assertEqual(bill["payment_status"], PaymentStatus.UNPAID)

        # Kiểm tra chặn phụ phí âm
        with self.assertRaises(HotelError):
            self.manager.calculate_booking_cost(b1.booking_id, extra_fee=-10_000)

        # 2. Xử lý thanh toán và tự động trả phòng
        tx1 = self.manager.process_payment(
            b1.booking_id,
            payment_method=PaymentMethod.BANK_TRANSFER,
            extra_fee=100_000,
            note="Thanh toán chuyển khoản khi trả phòng",
            paid_at=self.today,
            auto_check_out=True,
        )
        self.assertEqual(tx1.payment_id, "TT00001")
        self.assertEqual(tx1.total_amount, 1_235_000)
        self.assertEqual(tx1.status, PaymentStatus.PAID)
        self.assertEqual(self.manager.bookings.get_booking(b1.booking_id).status, BookingStatus.CHECKED_OUT)

        # Chặn thanh toán trùng lặp trên cùng một đơn đã thanh toán
        with self.assertRaises(HotelError):
            self.manager.process_payment(b1.booking_id, payment_method=PaymentMethod.CASH)

        # Chặn thanh toán cho đơn đã bị hủy
        b_cancel = self.manager.book_room(c_norm.customer_id, "P102", ci, co)
        self.manager.cancel_booking(b_cancel.booking_id)
        with self.assertRaises(HotelError):
            self.manager.process_payment(b_cancel.booking_id, payment_method=PaymentMethod.CASH)

        # 3. Tra cứu thanh toán theo Mã GD, Mã đơn, Mã KH, CCCD, SĐT (+84), Mã phòng, Tên khách
        self.assertEqual(self.manager.get_payment("TT00001").booking_id, b1.booking_id)
        self.assertEqual(len(self.manager.lookup_payments("TT00001")), 1)
        self.assertEqual(len(self.manager.lookup_payments(b1.booking_id)), 1)
        self.assertEqual(len(self.manager.lookup_payments(c_gold.customer_id)), 1)
        self.assertEqual(len(self.manager.lookup_payments("001200033333")), 1)
        self.assertEqual(len(self.manager.lookup_payments("0912-345-678")), 1)
        self.assertEqual(len(self.manager.lookup_payments("P101")), 1)
        self.assertEqual(len(self.manager.lookup_payments("Hoàng Nam")), 1)

        with self.assertRaises(NotFoundError):
            self.manager.lookup_payments("KHONG_TON_TAI")
        with self.assertRaises(NotFoundError):
            self.manager.lookup_payments("   ")

        # 4. Hoàn tiền (Refund) và thanh toán lại
        refunded = self.manager.refund_payment("TT00001", reason="Nhập sai phụ phí")
        self.assertEqual(refunded.status, PaymentStatus.REFUNDED)
        self.assertFalse(self.manager.payments.is_booking_paid(b1.booking_id))
        with self.assertRaises(HotelError):
            self.manager.refund_payment("TT00001")

        tx2 = self.manager.process_payment(
            b1.booking_id,
            payment_method=PaymentMethod.CARD,
            extra_fee=0,
            note="Thanh toán lại đúng số tiền",
            paid_at=self.today,
        )
        self.assertEqual(tx2.payment_id, "TT00002")
        self.assertEqual(tx2.total_amount, 1_140_000)
        self.assertEqual(len(self.manager.payments_for_booking(b1.booking_id)), 2)

        summary = self.manager.payments.payment_summary()
        self.assertEqual(summary["total_transactions"], 2)
        self.assertEqual(summary["paid_transactions"], 1)
        self.assertEqual(summary["refunded_transactions"], 1)
        self.assertEqual(summary["total_collected"], 1_140_000)

    def test_payment_boundary_dates_supplementary_and_cancel_undo(self):
        c1 = self.manager.register_customer("Khách A", "001200055551", "0911111111", VipLevel.NORMAL)
        c2 = self.manager.register_customer("Khách B", "001200055552", "0922222222", VipLevel.SILVER)

        d1 = self.today
        d2 = self.today + timedelta(days=2)
        d3 = self.today + timedelta(days=4)

        # Hai đơn nối tiếp nhau tại cùng phòng P101: b1 [d1, d2) và b2 [d2, d3)
        b1 = self.manager.book_room(c1.customer_id, "P101", d1, d2)
        b2 = self.manager.book_room(c2.customer_id, "P101", d2, d3)
        self.manager.check_in(b1.booking_id)

        # Yêu cầu dịch vụ tạo vào ngày biên d2 khi b1 đang CHECKED_IN và không truyền customer_id
        self.manager.submit_service_request(
            "P101", ServiceType.CLEANING, UrgencyLevel.LOW, "Dọn phòng sáng trả phòng", requested_at=d2
        )
        self.manager.check_out(b1.booking_id)
        self.manager.check_in(b2.booking_id)

        # Yêu cầu dịch vụ thứ 2 tạo vào ngày biên d2 sau khi b2 đã CHECKED_IN (gọi trực tiếp không có customer_id)
        self.manager.service_requests.submit_request(
            "P101", ServiceType.FOOD, UrgencyLevel.NORMAL, "Bữa trưa nhận phòng", customer_id="", requested_at=d2
        )

        # Kiểm tra không bị tính trùng (double-billing) giữa b1 và b2 ở ngày biên d2
        bill_b1 = self.manager.calculate_booking_cost(b1.booking_id)
        bill_b2 = self.manager.calculate_booking_cost(b2.booking_id)
        self.assertEqual(bill_b1["service_cost"], 50_000)
        self.assertEqual(bill_b2["service_cost"], 150_000)

        # Kiểm tra bảo toàn extra_fee sau khi đã thanh toán và thanh toán bổ sung khi phát sinh thêm dịch vụ
        tx_b2_first = self.manager.process_payment(
            b2.booking_id, payment_method="CHUYỂN KHOẢN", extra_fee=100_000, paid_at=d2
        )
        self.assertEqual(tx_b2_first.extra_fee, 100_000)
        bill_after_first = self.manager.calculate_booking_cost(b2.booking_id)
        self.assertEqual(bill_after_first["extra_fee"], 100_000)
        self.assertTrue(bill_after_first["is_paid"])
        self.assertEqual(bill_after_first["remaining_amount"], 0)

        # Phát sinh thêm yêu cầu Y tế (200.000đ) cho b2 sau khi đã thanh toán lần 1
        self.manager.submit_service_request(
            "P101", ServiceType.MEDICAL, UrgencyLevel.EMERGENCY, "Thuốc cảm", customer_id=c2.customer_id, requested_at=d2
        )
        bill_supplementary = self.manager.calculate_booking_cost(b2.booking_id)
        self.assertFalse(bill_supplementary["is_paid"])
        # 200.000đ giảm 3% hạng SILVER = 194.000đ còn phải thu thêm
        self.assertEqual(bill_supplementary["remaining_amount"], 194_000)

        tx_b2_second = self.manager.process_payment(
            b2.booking_id, payment_method="TIỀN MẶT", paid_at=d2
        )
        self.assertEqual(tx_b2_second.total_amount, 194_000)
        self.assertTrue(self.manager.payments.is_booking_paid(b2.booking_id))

        # Kiểm tra hủy đơn đã thanh toán tự động hoàn tiền và Undo khôi phục lại trạng thái PAID
        b3 = self.manager.book_room(c1.customer_id, "P102", d2, d3)
        tx_b3 = self.manager.process_payment(b3.booking_id, payment_method=PaymentMethod.E_WALLET, paid_at=d1)
        self.assertEqual(tx_b3.status, PaymentStatus.PAID)
        self.manager.cancel_booking(b3.booking_id)
        self.assertEqual(tx_b3.status, PaymentStatus.REFUNDED)
        self.manager.undo_last_cancellation()
        self.assertEqual(tx_b3.status, PaymentStatus.PAID)

        # Kiểm tra lọc & sắp xếp giao dịch bằng Merge Sort và chặn tham số không hợp lệ
        sorted_by_amount = self.manager.sort_payments(by="total_amount", reverse=True)
        self.assertEqual(
            [t.total_amount for t in sorted_by_amount],
            sorted([t.total_amount for t in sorted_by_amount], reverse=True),
        )
        paid_only = self.manager.filter_payments(status="PAID")
        self.assertTrue(all(t.status == PaymentStatus.PAID for t in paid_only))
        with self.assertRaises(HotelError):
            self.manager.calculate_booking_cost(b1.booking_id, extra_fee=True)
        with self.assertRaises(HotelError):
            self.manager.filter_payments(start_date=d3, end_date=d1)
        with self.assertRaises(HotelError):
            self.manager.sort_payments(by="invalid_field")

    def test_automatic_vip_upgrade_by_cumulative_paid_spending_and_waiting_sync(self):
        c_prog = self.manager.register_customer(
            "Trần Tích Lũy", "001200099991", "0999999901", VipLevel.NORMAL
        )
        c_other_norm = self.manager.register_customer(
            "Khách Thường Chờ Trước", "001200099992", "0999999902", VipLevel.NORMAL
        )
        c_manual_gold = self.manager.register_customer(
            "Khách Gold Đặc Cách", "001200099993", "0999999903", VipLevel.GOLD
        )

        # Xếp c_other_norm vào hàng chờ trước, sau đó đến c_prog (cả hai đang ở LinkedQueue thường)
        wait_in = self.today + timedelta(days=20)
        wait_out = self.today + timedelta(days=22)
        self.manager.add_to_waiting_list(c_other_norm.customer_id, RoomType.SUITE, wait_in, wait_out)
        self.manager.add_to_waiting_list(c_prog.customer_id, RoomType.SUITE, wait_in, wait_out)
        self.assertEqual(self.manager.waiting.vip_count(), 0)
        self.assertEqual(self.manager.waiting.normal_count(), 2)
        self.assertEqual(self.manager.waiting.peek_next().customer_id, c_other_norm.customer_id)

        # 1. Đợt 1: c_prog ở 5 đêm phòng P101 (500.000đ/đêm = 2.500.000đ < 3.000.000đ) -> Vẫn NORMAL (0)
        b1 = self.manager.book_room(
            c_prog.customer_id, "P101", self.today, self.today + timedelta(days=5)
        )
        bill1 = self.manager.calculate_booking_cost(b1.booking_id)
        self.assertFalse(bill1["will_upgrade_vip"])
        self.assertEqual(bill1["projected_vip_level"], VipLevel.NORMAL)
        self.manager.process_payment(b1.booking_id, payment_method=PaymentMethod.CASH)
        self.assertEqual(self.manager.customer_total_paid(c_prog.customer_id), 2_500_000)
        self.assertEqual(c_prog.vip_level, VipLevel.NORMAL)
        prog1 = self.manager.customer_vip_progress(c_prog.customer_id)
        self.assertEqual(prog1["next_vip"], VipLevel.SILVER)
        self.assertEqual(prog1["amount_to_next_vip"], 500_000)

        # 2. Đợt 2: c_prog ở thêm 1 đêm P101 (500.000đ) -> Tích lũy đúng 3.000.000đ -> Tự động lên SILVER (1)
        # Đồng thời mục chờ của c_prog tự động chuyển từ LinkedQueue sang Max-Heap VIP và vượt lên đầu hàng chờ!
        b2 = self.manager.book_room(
            c_prog.customer_id,
            "P101",
            self.today + timedelta(days=5),
            self.today + timedelta(days=6),
        )
        bill2 = self.manager.calculate_booking_cost(b2.booking_id)
        self.assertTrue(bill2["will_upgrade_vip"])
        self.assertEqual(bill2["projected_vip_level"], VipLevel.SILVER)
        self.manager.process_payment(b2.booking_id, payment_method=PaymentMethod.BANK_TRANSFER)
        self.assertEqual(self.manager.customer_total_paid(c_prog.customer_id), 3_000_000)
        self.assertEqual(c_prog.vip_level, VipLevel.SILVER)
        self.assertEqual(self.manager.waiting.vip_count(), 1)
        self.assertEqual(self.manager.waiting.normal_count(), 1)
        self.assertEqual(self.manager.waiting.peek_next().customer_id, c_prog.customer_id)

        # 3. Đợt 3: Đang là SILVER (giảm 3%), đặt phòng P305 (Suite tầng 3: 1.600.000đ/đêm × 4 đêm = 6.400.000đ)
        # Sau giảm 3% (192.000đ) còn 6.208.000đ -> Tích lũy = 3.000.000 + 6.208.000 = 9.208.000đ (>= 8tr) -> Tự động lên GOLD (2)
        b3 = self.manager.book_room(
            c_prog.customer_id,
            "P305",
            self.today + timedelta(days=6),
            self.today + timedelta(days=10),
        )
        bill3 = self.manager.calculate_booking_cost(b3.booking_id)
        self.assertEqual(bill3["discount_rate"], 0.03)
        self.assertEqual(bill3["total_amount"], 6_208_000)
        self.assertTrue(bill3["will_upgrade_vip"])
        self.assertEqual(bill3["projected_vip_level"], VipLevel.GOLD)
        self.manager.process_payment(b3.booking_id, payment_method=PaymentMethod.CARD)
        self.assertEqual(self.manager.customer_total_paid(c_prog.customer_id), 9_208_000)
        self.assertEqual(c_prog.vip_level, VipLevel.GOLD)
        self.assertEqual(self.manager.waiting.peek_next().priority, int(VipLevel.GOLD))

        # 4. Đợt 4: Đang là GOLD (giảm 5%), đặt phòng P305 4 đêm (6.400.000đ, giảm 5% còn 6.080.000đ)
        # Tích lũy = 9.208.000 + 6.080.000 = 15.288.000đ (>= 15tr) -> Tự động lên PLATINUM (3)
        b4 = self.manager.book_room(
            c_prog.customer_id,
            "P305",
            self.today + timedelta(days=10),
            self.today + timedelta(days=14),
        )
        bill4 = self.manager.calculate_booking_cost(b4.booking_id)
        self.assertEqual(bill4["discount_rate"], 0.05)
        self.assertEqual(bill4["total_amount"], 6_080_000)
        self.assertTrue(bill4["will_upgrade_vip"])
        self.assertEqual(bill4["projected_vip_level"], VipLevel.PLATINUM)
        self.manager.process_payment(b4.booking_id, payment_method=PaymentMethod.E_WALLET)
        self.assertEqual(self.manager.customer_total_paid(c_prog.customer_id), 15_288_000)
        self.assertEqual(c_prog.vip_level, VipLevel.PLATINUM)
        self.assertEqual(self.manager.waiting.peek_next().priority, int(VipLevel.PLATINUM))
        prog_final = self.manager.customer_vip_progress(c_prog.customer_id)
        self.assertIsNone(prog_final["next_vip"])
        self.assertEqual(prog_final["amount_to_next_vip"], 0)
        self.assertEqual(prog_final["discount_rate"], 0.10)

        # 5. Khách được cấp GOLD thủ công khi mới thanh toán < 3.000.000đ không bị hạ cấp
        b_gold = self.manager.book_room(
            c_manual_gold.customer_id, "P102", self.today, self.today + timedelta(days=1)
        )
        tx_gold = self.manager.process_payment(b_gold.booking_id, payment_method=PaymentMethod.CASH)
        self.assertEqual(c_manual_gold.vip_level, VipLevel.GOLD)

        # Hoàn tiền giao dịch của c_manual_gold vẫn giữ nguyên hạng GOLD được cấp thủ công
        self.manager.refund_payment(tx_gold.payment_id, reason="Test giữ hạng thủ công")
        self.assertEqual(c_manual_gold.vip_level, VipLevel.GOLD)

        # 6. Khách thường (NORMAL) tự động lên SILVER nhờ thanh toán, nếu hoàn tiền / hủy đơn và tổng tiền
        # đã TT quay về < 3tr thì phải thu hồi hạng VIP tự động (và hạ mức ưu tiên trong hàng chờ về LinkedQueue)
        c_refund = self.manager.register_customer(
            "Khách Hoàn Tiền", "001200099994", "0999999904", VipLevel.NORMAL
        )
        self.manager.add_to_waiting_list(c_refund.customer_id, RoomType.SINGLE, wait_in, wait_out)
        b_ref = self.manager.book_room(
            c_refund.customer_id, "P103", self.today, self.today + timedelta(days=6)
        )  # 6 đêm × 500k = 3.000.000đ -> Tự động lên SILVER (1)
        self.manager.process_payment(b_ref.booking_id, payment_method=PaymentMethod.CASH)
        self.assertEqual(c_refund.vip_level, VipLevel.SILVER)
        self.assertEqual(self.manager.waiting.vip_count(), 2)  # c_prog (PLATINUM) + c_refund (SILVER)

        # Hủy đơn b_ref -> tự động hoàn tiền -> tích lũy về 0đ -> hạ về NORMAL (0) và chuyển về LinkedQueue
        self.manager.cancel_booking(b_ref.booking_id)
        self.assertEqual(self.manager.customer_total_paid(c_refund.customer_id), 0)
        self.assertEqual(c_refund.vip_level, VipLevel.NORMAL)
        self.assertEqual(self.manager.waiting.vip_count(), 1)
        self.assertEqual(self.manager.waiting.normal_count(), 2)

        # Hoàn tác lệnh hủy đơn b_ref -> giao dịch về lại PAID -> tự động khôi phục SILVER (1) và đưa lại vào MaxHeap
        self.manager.undo_last_cancellation()
        self.assertEqual(self.manager.customer_total_paid(c_refund.customer_id), 4_800_000)
        self.assertEqual(c_refund.vip_level, VipLevel.SILVER)
        self.assertEqual(self.manager.waiting.vip_count(), 2)

    def test_cli_payment_menus_interactive(self):
        from hotel.ui.cli import HotelCLI

        m = HotelManager(data_file=None, auto_save=False, seed_if_empty=True)
        cli = HotelCLI(m)
        inputs = [
            "9", "1", "BK00003", "50000",
            "9", "2", "BK00003", "50000", "2", "Thanh toán CLI", "y",
            "9", "3",
            "9", "4", "BK00003",
            "9", "6",
            "0",
        ]
        with patch("builtins.input", side_effect=inputs), patch("sys.stdout", new_callable=io.StringIO) as out:
            cli.run()
            output_text = out.getvalue()
        self.assertIn("TT00003", output_text)
        self.assertEqual(m.bookings.get_booking("BK00003").status, BookingStatus.CHECKED_OUT)

    def test_json_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "hotel_test.json"
            m1 = HotelManager(data_file=json_path, auto_save=True, seed_if_empty=True)
            expected_customers = len(m1.customers)
            expected_bookings = len(m1.bookings.all_bookings())
            expected_waiting = len(m1.waiting)
            expected_undo = len(m1.undo)
            expected_sr = m1.service_requests.pending_count()
            expected_payments = len(m1.payments)

            # Nạp lại từ file JSON vào một instance hoàn toàn mới
            m2 = HotelManager(data_file=json_path, auto_save=False, seed_if_empty=False)
            self.assertEqual(len(m2.customers), expected_customers)
            self.assertEqual(len(m2.bookings.all_bookings()), expected_bookings)
            self.assertEqual(len(m2.waiting), expected_waiting)
            self.assertEqual(len(m2.undo), expected_undo)
            self.assertEqual(m2.service_requests.pending_count(), expected_sr)
            self.assertEqual(len(m2.payments), expected_payments)
            self.assertEqual(m2.get_payment("TT00001").booking_id, "BK00001")

            # Kiểm tra lịch sử lưu trú (SinglyLinkedList) và Undo Stack vẫn hoạt động đúng sau khi nạp
            _, restored = m2.undo_last_cancellation()
            self.assertEqual(restored.status, BookingStatus.CONFIRMED)

            # Kiểm tra khả năng chịu lỗi khi file JSON bị hỏng
            json_path.write_text("{corrupted json", encoding="utf-8")
            with self.assertRaises(HotelError):
                HotelManager(data_file=json_path, auto_save=False, seed_if_empty=False)

    def test_gui_instantiation_and_tabs(self):
        from hotel.ui.gui import HotelGUI

        m = HotelManager(data_file=None, auto_save=False, seed_if_empty=True)
        app = HotelGUI(m)
        try:
            app.root.update_idletasks()
            app._select_room("P205")
            app._on_suggest_budget()
            self.assertGreater(len(app.tree_bookings.get_children()), 0)
            self.assertGreater(len(app.tree_customers.get_children()), 0)
            self.assertGreater(len(app.tree_waiting.get_children()), 0)
            self.assertGreater(len(app.tree_sr.get_children()), 0)
            self.assertGreater(len(app.tree_payments.get_children()), 0)
            app._on_calculate_bill()
            self.assertIn("BK00003", app.txt_bill_detail.get("1.0", "end"))
        finally:
            app.root.destroy()


if __name__ == "__main__":
    unittest.main()
