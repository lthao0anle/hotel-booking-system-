"""Khởi tạo bộ dữ liệu mẫu tiếng Việt phong phú để minh họa ngay các cấu trúc dữ liệu."""

from datetime import date, timedelta

from hotel.models.enums import PaymentMethod, RoomType, ServiceType, UrgencyLevel, VipLevel


def seed_sample_data(manager, reference_date=None):
    """Tạo dữ liệu mẫu cho khách sạn (khách hàng, đặt phòng, hàng chờ, undo, dịch vụ)."""
    today = reference_date or date.today()

    # 1. Đặt 1 phòng ở trạng thái bảo trì để minh họa sơ đồ tầng
    manager.set_room_maintenance("P104", True)

    # 2. Đăng ký khách hàng mẫu (từ Thường đến Platinum VIP)
    c1 = manager.register_customer("Nguyễn Văn An", "001200012345", "0901234567", VipLevel.NORMAL)
    c2 = manager.register_customer("Trần Thị Bích", "001200023456", "0912345678", VipLevel.SILVER)
    c3 = manager.register_customer("Lê Hoàng Nam", "001200034567", "0923456789", VipLevel.GOLD)
    c4 = manager.register_customer("Phạm Minh Châu", "001200045678", "0934567890", VipLevel.PLATINUM)
    c5 = manager.register_customer("Hoàng Đức Thịnh", "001200056789", "0945678901", VipLevel.NORMAL)
    c6 = manager.register_customer("Vũ Ngọc Mai", "001200067890", "0956789012", VipLevel.GOLD)

    # 3. Tạo các đơn đặt phòng (bao gồm đã trả, đang ở, sắp nhận)
    b_past = manager.book_room(
        c4.customer_id,
        "P509",
        today - timedelta(days=5),
        today - timedelta(days=2),
    )
    manager.check_in(b_past.booking_id)
    manager.check_out(b_past.booking_id)

    b_stay1 = manager.book_room(
        c1.customer_id,
        "P101",
        today - timedelta(days=1),
        today + timedelta(days=2),
    )
    manager.check_in(b_stay1.booking_id)

    b_stay2 = manager.book_room(
        c3.customer_id,
        "P205",
        today,
        today + timedelta(days=3),
    )
    manager.check_in(b_stay2.booking_id)

    manager.book_room(
        c2.customer_id,
        "P306",
        today + timedelta(days=1),
        today + timedelta(days=4),
    )
    manager.book_room(
        c4.customer_id,
        "P410",
        today,
        today + timedelta(days=4),
    )

    # Tạo 1 đơn rồi hủy để có sẵn phần tử trong Undo Stack minh họa hoàn tác
    b_cancel = manager.book_room(
        c5.customer_id,
        "P102",
        today + timedelta(days=2),
        today + timedelta(days=5),
    )
    manager.cancel_booking(b_cancel.booking_id, cancelled_by="STAFF", auto_fulfill=False)

    # 4. Thêm khách vào danh sách chờ (khách thường + khách VIP để minh họa Max-Heap vs Queue)
    manager.add_to_waiting_list(
        c5.customer_id,
        RoomType.SUITE,
        today + timedelta(days=1),
        today + timedelta(days=3),
    )
    manager.add_to_waiting_list(
        c2.customer_id,
        RoomType.SUITE,
        today + timedelta(days=1),
        today + timedelta(days=3),
    )
    manager.add_to_waiting_list(
        c6.customer_id,
        RoomType.SUITE,
        today + timedelta(days=1),
        today + timedelta(days=3),
    )

    # 5. Gửi các yêu cầu dịch vụ nội bộ với độ khẩn khác nhau (LOW, NORMAL, EMERGENCY)
    manager.submit_service_request(
        room_id="P101",
        service_type=ServiceType.CLEANING,
        urgency=UrgencyLevel.LOW,
        note="Thay khăn tắm và dọn phòng buổi sáng",
        customer_id=c1.customer_id,
    )
    manager.submit_service_request(
        room_id="P205",
        service_type=ServiceType.FOOD,
        urgency=UrgencyLevel.NORMAL,
        note="2 suất phở bò + 2 nước cam lên phòng",
        customer_id=c3.customer_id,
    )
    manager.submit_service_request(
        room_id="P410",
        service_type=ServiceType.MEDICAL,
        urgency=UrgencyLevel.EMERGENCY,
        note="Khách bị sốt cao, cần hỗ trợ y tế ngay",
        customer_id=c4.customer_id,
    )

    # 6. Tạo các giao dịch thanh toán mẫu (minh họa Quản lý thanh toán: HashTable + SinglyLinkedList)
    manager.process_payment(
        booking_id=b_past.booking_id,
        payment_method=PaymentMethod.CARD,
        extra_fee=0,
        note="Thanh toán khi trả phòng P509 (giảm 10% hạng Platinum)",
        paid_at=today - timedelta(days=2),
    )
    manager.process_payment(
        booking_id=b_stay1.booking_id,
        payment_method=PaymentMethod.BANK_TRANSFER,
        extra_fee=0,
        note="Thanh toán trước tiền phòng P101 và phí dọn phòng",
        paid_at=today,
    )
