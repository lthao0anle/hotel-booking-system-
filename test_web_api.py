"""Kiểm thử tích hợp cho Web API Bridge (web_app/backend/api.py) và tự động nâng hạng VIP."""

from datetime import date, timedelta
import os
import tempfile
import unittest

from hotel.models.enums import RoomType, VipLevel
from hotel.services.hotel_manager import HotelManager
import web_app.backend.api as web_api


class TestWebApiVipUpgrade(unittest.TestCase):
    def setUp(self):
        self._orig_manager = web_api.manager
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmp.close()
        os.unlink(self._tmp.name)
        web_api.manager = HotelManager(
            data_file=self._tmp.name,
            auto_save=True,
            seed_if_empty=False,
            load_existing=False,
        )

    def tearDown(self):
        web_api.manager = self._orig_manager
        if os.path.exists(self._tmp.name):
            try:
                os.unlink(self._tmp.name)
            except OSError:
                pass

    def test_register_customer_and_vip_progress_endpoint(self):
        res = web_api.register_customer(
            web_api.RegisterCustomerRequest(
                full_name="Nguyễn Văn Web",
                cccd="001200009999",
                phone="0912349999",
                vip_level=0,
            )
        )
        cid = res["customer_id"]
        self.assertEqual(res["vip_level"], 0)
        self.assertEqual(res["total_paid"], 0)
        self.assertEqual(res["next_vip"], 1)
        self.assertEqual(res["next_threshold"], 3_000_000)
        self.assertEqual(res["amount_to_next_vip"], 3_000_000)

        prog = web_api.get_customer_vip_progress(cid)
        self.assertEqual(prog["current_vip"], 0)
        self.assertEqual(prog["next_vip"], 1)
        self.assertEqual(prog["thresholds"][1], 3_000_000)
        self.assertEqual(prog["thresholds"][2], 8_000_000)
        self.assertEqual(prog["thresholds"][3], 15_000_000)
        self.assertAlmostEqual(prog["discount_rates"][1], 0.03)
        self.assertAlmostEqual(prog["discount_rates"][2], 0.05)
        self.assertAlmostEqual(prog["discount_rates"][3], 0.10)

    def test_web_api_payment_auto_upgrades_vip_and_updates_waiting_list(self):
        c = web_api.register_customer(
            web_api.RegisterCustomerRequest(
                full_name="Trần Thị Web VIP",
                cccd="001200008888",
                phone="0912348888",
                vip_level=0,
            )
        )
        cid = c["customer_id"]
        today = date.today()

        # Thêm khách (đang là khách thường VIP 0) vào danh sách chờ trước khi đặt phòng
        web_api.add_waiting_entry(
            web_api.AddWaitingRequest(
                customer_id=cid,
                room_type=RoomType.SINGLE.value,
                check_in=(today + timedelta(days=10)).isoformat(),
                check_out=(today + timedelta(days=12)).isoformat(),
            )
        )
        w_before = web_api.get_waiting_list()
        self.assertEqual(w_before["total_regular"], 1)
        self.assertEqual(w_before["total_vip"], 0)

        # Đặt phòng P509 (Suite tầng 5: 1,700,000/đêm) x 2 đêm = 3,400,000 VND (>= 3,000,000)
        # Ngay khi đặt phòng đạt mốc >= 3tr, khách tự động lên VIP 1 và chuyển sang Max-Heap VIP
        b = web_api.create_booking(
            web_api.CreateBookingRequest(
                customer_id=cid,
                room_id="P509",
                check_in=today.isoformat(),
                check_out=(today + timedelta(days=2)).isoformat(),
            )
        )
        bid = b["booking_id"]
        self.assertTrue(b["vip_upgraded"])
        self.assertEqual(b["new_vip_level"], 1)

        # Kiểm tra dự tính hóa đơn trước khi thanh toán
        calc = web_api.calculate_cost(bid, extra_fee=0)
        self.assertEqual(calc["total_amount"], 3_400_000)
        self.assertEqual(calc["vip_level"], 0)
        self.assertEqual(calc["projected_total_paid"], 3_400_000)
        self.assertEqual(calc["projected_vip_level"], int(VipLevel.SILVER))
        self.assertTrue(calc["will_upgrade_vip"])

        # Thanh toán qua API -> Tự động lên VIP 1 (Silver) & chuyển sang hàng chờ VIP Max-Heap
        tx = web_api.process_payment(
            web_api.ProcessPaymentRequest(
                booking_id=bid,
                payment_method="BANK_TRANSFER",
                extra_fee=0,
                note="Thanh toán qua Web API",
                auto_check_out=False,
            )
        )
        self.assertEqual(tx["amount"], 3_400_000)
        self.assertEqual(tx["previous_vip_level"], 0)
        self.assertEqual(tx["new_vip_level"], 1)
        self.assertTrue(tx["vip_upgraded"])
        self.assertEqual(tx["customer_total_paid"], 3_400_000)

        # Kiểm tra khách hàng đã lên VIP 1 và hưởng chiết khấu 3%
        c_after = web_api.lookup_customer(cid)
        self.assertEqual(c_after["vip_level"], 1)
        self.assertAlmostEqual(c_after["discount_rate"], 0.03)
        self.assertEqual(c_after["total_paid"], 3_400_000)
        self.assertEqual(c_after["next_vip"], 2)
        self.assertEqual(c_after["amount_to_next_vip"], 8_000_000 - 3_400_000)

        # Kiểm tra hàng chờ đã tự động đôn khách từ FIFO thường sang Max-Heap VIP
        w_after = web_api.get_waiting_list()
        self.assertEqual(w_after["total_regular"], 0)
        self.assertEqual(w_after["total_vip"], 1)
        self.assertEqual(w_after["vip"][0]["customer_id"], cid)
        self.assertEqual(w_after["vip"][0]["vip_level"], 1)

        # Phân bổ phòng tự động cho hàng chờ qua API (kiểm tra serialize tuple (entry, booking))
        fulfilled_res = web_api.process_waiting(room_type=RoomType.SINGLE.value)
        self.assertEqual(fulfilled_res["fulfilled_count"], 1)
        self.assertEqual(fulfilled_res["fulfilled"][0]["customer_id"], cid)

    def test_web_api_multi_tier_upgrade_refund_cancel_undo_and_reports(self):
        c = web_api.register_customer(
            web_api.RegisterCustomerRequest(
                full_name="Phạm Lũy Kế",
                cccd="001200007777",
                phone="0912347777",
                vip_level=0,
            )
        )
        cid = c["customer_id"]
        today = date.today()

        # 1. Đợt 1: P509 (1,700,000/đêm) x 2 đêm = 3,400,000 VND -> Lên VIP 1 (Silver - 3%)
        b1 = web_api.create_booking(
            web_api.CreateBookingRequest(
                customer_id=cid,
                room_id="P509",
                check_in=today.isoformat(),
                check_out=(today + timedelta(days=2)).isoformat(),
            )
        )
        tx1 = web_api.process_payment(
            web_api.ProcessPaymentRequest(
                booking_id=b1["booking_id"],
                payment_method="CREDIT_CARD",
                extra_fee=0,
                note="Đợt 1 dùng CREDIT_CARD",
            )
        )
        self.assertEqual(tx1["new_vip_level"], 1)
        self.assertTrue(tx1["vip_upgraded"])

        # 2. Hủy đơn b1 -> tự động hoàn tiền -> tích lũy về 0 -> hạ về VIP 0; sau đó Undo -> khôi phục VIP 1
        cancel_res = web_api.cancel_booking(
            b1["booking_id"], web_api.CancelBookingRequest(cancelled_by="STAFF", auto_fulfill=True)
        )
        self.assertTrue(cancel_res["can_undo"])
        self.assertEqual(web_api.lookup_customer(cid)["vip_level"], 0)
        self.assertEqual(web_api.lookup_customer(cid)["total_paid"], 0)

        undo_res = web_api.undo_last_cancel()
        self.assertEqual(undo_res["booking"]["booking_id"], b1["booking_id"])
        self.assertEqual(web_api.lookup_customer(cid)["vip_level"], 1)
        self.assertEqual(web_api.lookup_customer(cid)["total_paid"], 3_400_000)

        # 3. Đợt 2: P510 (1,700,000/đêm) x 3 đêm = 5,100,000 VND, giảm 3% (153,000) = 4,947,000 VND
        # Lũy kế = 3,400,000 + 4,947,000 = 8,347,000 VND (>= 8,000,000) -> Lên VIP 2 (Gold - 5%)
        b2 = web_api.create_booking(
            web_api.CreateBookingRequest(
                customer_id=cid,
                room_id="P510",
                check_in=(today + timedelta(days=2)).isoformat(),
                check_out=(today + timedelta(days=5)).isoformat(),
            )
        )
        tx2 = web_api.process_payment(
            web_api.ProcessPaymentRequest(
                booking_id=b2["booking_id"],
                payment_method="BANK_TRANSFER",
                extra_fee=0,
            )
        )
        self.assertEqual(tx2["amount"], 4_947_000)
        self.assertEqual(tx2["previous_vip_level"], 1)
        self.assertEqual(tx2["new_vip_level"], 2)
        self.assertTrue(tx2["vip_upgraded"])
        self.assertEqual(tx2["customer_total_paid"], 8_347_000)

        # 4. Đợt 3: P510 (1,700,000/đêm) x 5 đêm = 8,500,000 VND, giảm 5% (425,000) = 8,075,000 VND
        # Lũy kế = 8,347,000 + 8,075,000 = 16,422,000 VND (>= 15,000,000) -> Lên VIP 3 (Platinum - 10%)
        b3 = web_api.create_booking(
            web_api.CreateBookingRequest(
                customer_id=cid,
                room_id="P510",
                check_in=(today + timedelta(days=5)).isoformat(),
                check_out=(today + timedelta(days=10)).isoformat(),
            )
        )
        tx3 = web_api.process_payment(
            web_api.ProcessPaymentRequest(
                booking_id=b3["booking_id"],
                payment_method="CASH",
                extra_fee=0,
            )
        )
        self.assertEqual(tx3["amount"], 8_075_000)
        self.assertEqual(tx3["previous_vip_level"], 2)
        self.assertEqual(tx3["new_vip_level"], 3)
        self.assertTrue(tx3["vip_upgraded"])
        self.assertEqual(tx3["customer_total_paid"], 16_422_000)

        # Kiểm tra báo cáo top customers có trả về total_paid và vip_level = 3
        top = web_api.get_top_customers(k=5)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]["customer"]["customer_id"], cid)
        self.assertEqual(top[0]["customer"]["vip_level"], 3)
        self.assertEqual(top[0]["total_paid"], 16_422_000)

        # Kiểm tra mã lỗi 404 khi tra cứu không tồn tại
        with self.assertRaises(web_api.HTTPException) as ctx_room:
            web_api.get_room_detail("P999")
        self.assertEqual(ctx_room.exception.status_code, 404)

        with self.assertRaises(web_api.HTTPException) as ctx_cust:
            web_api.lookup_customer("KH999")
        self.assertEqual(ctx_cust.exception.status_code, 404)

        with self.assertRaises(web_api.HTTPException) as ctx_pay:
            web_api.lookup_payments("KHONG_TON_TAI")
        self.assertEqual(ctx_pay.exception.status_code, 404)

    def test_booking_23_8m_immediately_upgrades_to_vip3_in_reports_and_load_sync(self):
        """Kiểm thử kịch bản thực tế: Khách Lê Ngọc Huy đặt 2 lượt lưu trú tổng 23.800.000 đ
        phải được nâng ngay lên VIP 3 (Platinum) trên bảng xếp hạng Báo cáo mà không cần chờ thanh toán.
        """
        c = web_api.register_customer(
            web_api.RegisterCustomerRequest(
                full_name="Lê Ngọc Huy",
                cccd="001200006666",
                phone="0912346666",
                vip_level=0,
            )
        )
        cid = c["customer_id"]
        today = date.today()

        # Lượt 1: P509 (1.700.000đ/đêm) x 7 đêm = 11.900.000 đ -> Lên ngay VIP 2 (Gold >= 8tr)
        b1 = web_api.create_booking(
            web_api.CreateBookingRequest(
                customer_id=cid,
                room_id="P509",
                check_in=today.isoformat(),
                check_out=(today + timedelta(days=7)).isoformat(),
            )
        )
        self.assertTrue(b1["vip_upgraded"])
        self.assertEqual(b1["new_vip_level"], int(VipLevel.GOLD))
        self.assertEqual(web_api.lookup_customer(cid)["vip_level"], int(VipLevel.GOLD))

        # Lượt 2: P510 (1.700.000đ/đêm) x 7 đêm = 11.900.000 đ -> Tổng = 23.800.000 đ -> Lên ngay VIP 3 (Platinum >= 15tr)
        b2 = web_api.create_booking(
            web_api.CreateBookingRequest(
                customer_id=cid,
                room_id="P510",
                check_in=(today + timedelta(days=7)).isoformat(),
                check_out=(today + timedelta(days=14)).isoformat(),
            )
        )
        self.assertTrue(b2["vip_upgraded"])
        self.assertEqual(b2["new_vip_level"], int(VipLevel.PLATINUM))

        # Kiểm tra trên /api/reports/top-customers: Lê Ngọc Huy đạt 23.800.000 đ và Hạng VIP 3
        top = web_api.get_top_customers(k=5)
        self.assertEqual(top[0]["customer"]["full_name"], "Lê Ngọc Huy")
        self.assertEqual(top[0]["booking_count"], 2)
        self.assertEqual(top[0]["total_spent"], 23_800_000)
        self.assertEqual(top[0]["customer"]["vip_level"], 3)

        # Hủy lượt 2 (chưa thanh toán) -> còn 11.900.000 đ -> tự động hạ về VIP 2 (Gold)
        web_api.cancel_booking(
            b2["booking_id"], web_api.CancelBookingRequest(cancelled_by="STAFF", auto_fulfill=False)
        )
        self.assertEqual(web_api.lookup_customer(cid)["vip_level"], 2)

        # Hoàn tác hủy lượt 2 -> trở lại 23.800.000 đ -> tự động khôi phục VIP 3 (Platinum)
        web_api.undo_last_cancel()
        self.assertEqual(web_api.lookup_customer(cid)["vip_level"], 3)

        # Giả lập dữ liệu cũ trong JSON bị lưu vip_level=0 dù có 23.800.000 đ đặt phòng -> Khi load() phải tự động lên VIP 3
        cust_obj = web_api.manager.customers.get_customer(cid)
        cust_obj.vip_level = VipLevel.NORMAL
        cust_obj.manual_vip_level = VipLevel.NORMAL
        web_api.manager.save()

        reloaded_manager = HotelManager(
            data_file=self._tmp.name,
            auto_save=True,
            seed_if_empty=False,
            load_existing=True,
        )
        self.assertEqual(
            reloaded_manager.customers.get_customer(cid).vip_level,
            VipLevel.PLATINUM,
        )


if __name__ == "__main__":
    unittest.main()
