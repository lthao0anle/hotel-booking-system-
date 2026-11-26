"""Định dạng bảng biểu, tiền tệ VND và sơ đồ ma trận phòng trực quan."""

from datetime import date

from hotel.config import VIP_DISCOUNT_RATES, VIP_SPENDING_THRESHOLDS
from hotel.models.date_utils import format_date
from hotel.models.enums import RoomStatus, VipLevel


def format_vnd(amount):
    """Định dạng số tiền sang chuỗi VND, ví dụ 1500000 -> '1.500.000 đ'."""
    return f"{int(amount):,}".replace(",", ".") + " đ"


def render_table(headers, rows):
    """Vẽ bảng ASCII căn lề tự động từ danh sách tiêu đề và các dòng."""
    str_headers = [str(h) for h in headers]
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(h) for h in str_headers]
    for row in str_rows:
        for idx, cell in enumerate(row):
            if idx < len(widths):
                widths[idx] = max(widths[idx], len(cell))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(str_headers)) + " |"
    lines = [sep, header_line, sep]
    if not str_rows:
        empty_msg = "(Không có dữ liệu)"
        total_inner = sum(widths) + 3 * (len(widths) - 1)
        lines.append("| " + empty_msg.center(total_inner) + " |")
    else:
        for row in str_rows:
            lines.append(
                "| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(widths))) + " |"
            )
    lines.append(sep)
    return "\n".join(lines)


def render_floor_matrix(floor_grid, on_date=None):
    """Vẽ sơ đồ ma trận phòng theo tầng (tầng cao ở trên hoặc tầng 1..N rõ ràng).

    Ký hiệu trạng thái:
        [ ] TRỐNG       [X] ĐÃ ĐẶT       [!] BẢO TRÌ
    Ký hiệu loại phòng:
        S = Đơn (Single), D = Đôi (Double), U = Suite
    """
    target = on_date or date.today()
    type_code = {"SINGLE": "Đơn", "DOUBLE": "Đôi", "SUITE": "Suite"}
    status_mark = {
        RoomStatus.EMPTY: "TRỐNG ",
        RoomStatus.BOOKED: "ĐÃ ĐẶT",
        RoomStatus.MAINTENANCE: "BẢO TRÌ",
    }

    lines = [
        f"=== SƠ ĐỒ MA TRẬN PHÒNG KHÁCH SẠN (Ngày kiểm tra: {format_date(target)}) ===",
        "Chú thích: [Mã phòng | Loại | Trạng thái]",
        "-" * 88,
    ]
    for floor_index in range(len(floor_grid) - 1, -1, -1):
        row = floor_grid[floor_index]
        floor_no = floor_index + 1
        cells = []
        for cell in row:
            room = cell["room"]
            status = cell["status"]
            t_short = type_code[room.room_type.value]
            s_short = status_mark[status]
            cells.append(f"[{room.room_id}:{t_short}:{s_short}]")
        # Chia 5 phòng mỗi dòng để vừa khung màn hình console
        mid = len(cells) // 2 if len(cells) > 5 else len(cells)
        lines.append(f"Tầng {floor_no:02d} (01..{mid:02d}): " + " ".join(cells[:mid]))
        if mid < len(cells):
            lines.append(f"        ({mid + 1:02d}..{len(cells):02d}): " + " ".join(cells[mid:]))
        lines.append("-" * 88)
    return "\n".join(lines)


def format_rooms_table(rooms, manager=None, on_date=None):
    target = on_date or date.today()
    headers = ["Mã phòng", "Tầng", "Số", "Loại phòng", "Giá / đêm", "Trạng thái", "Mô tả tiện nghi"]
    rows = []
    for room in rooms:
        if manager is not None:
            status_label = manager.bookings.room_status_on(room.room_id, target).label
        else:
            status_label = "BẢO TRÌ" if room.under_maintenance else "TRỐNG"
        rows.append(
            [
                room.room_id,
                room.floor,
                f"{room.room_number:02d}",
                room.room_type.label,
                format_vnd(room.price_per_night),
                status_label,
                room.description,
            ]
        )
    return render_table(headers, rows)


def format_bookings_table(bookings, customer_service=None):
    headers = [
        "Mã đơn",
        "Mã KH",
        "Tên khách hàng",
        "Phòng",
        "Nhận phòng",
        "Trả phòng",
        "Số đêm",
        "Tổng tiền",
        "Trạng thái",
    ]
    rows = []
    for b in bookings:
        cname = ""
        if customer_service is not None:
            try:
                cname = customer_service.get_customer(b.customer_id).full_name
            except Exception:
                cname = "-"
        rows.append(
            [
                b.booking_id,
                b.customer_id,
                cname,
                b.room_id,
                format_date(b.check_in),
                format_date(b.check_out),
                b.num_nights,
                format_vnd(b.total_price),
                b.status.label,
            ]
        )
    return render_table(headers, rows)


def format_customers_table(customers, payment_service=None):
    if payment_service is None:
        headers = ["Mã KH", "Họ và tên", "Số CCCD", "Số điện thoại", "Hạng VIP", "Số lượt đặt"]
    else:
        headers = [
            "Mã KH",
            "Họ và tên",
            "Số CCCD",
            "Số điện thoại",
            "Hạng VIP",
            "Số đơn",
            "Tích lũy đã TT",
            "Tiến độ nâng VIP",
        ]
    rows = []
    for c in customers:
        base_row = [
            c.customer_id,
            c.full_name,
            c.cccd,
            c.phone,
            f"{c.vip_level.label} ({int(c.vip_level)})",
            len(c.history),
        ]
        if payment_service is not None:
            prog = payment_service.get_customer_vip_progress(c.customer_id)
            if prog["next_vip"] is not None:
                next_info = f"Còn {format_vnd(prog['amount_to_next_vip'])} -> {prog['next_vip'].label}"
            else:
                next_info = "Đạt đỉnh (Platinum)"
            base_row.extend([format_vnd(prog["total_paid"]), next_info])
        rows.append(base_row)
    return render_table(headers, rows)


def format_vip_policy_table():
    """Bảng quy định mốc tích lũy tự động nâng hạng VIP và quyền lợi chiết khấu."""
    headers = ["Hạng thành viên", "Mức ưu tiên", "Mốc tích lũy đã thanh toán", "Chiết khấu hóa đơn", "Quyền lợi hàng chờ"]
    rows = []
    for level in VipLevel:
        threshold = VIP_SPENDING_THRESHOLDS.get(level, 0)
        rate_pct = int(round(VIP_DISCOUNT_RATES.get(level, 0.0) * 100))
        thresh_str = "Mặc định (< 3.000.000 đ)" if level == VipLevel.NORMAL else f">= {format_vnd(threshold)}"
        queue_benefit = (
            "LinkedQueue (FIFO thường)"
            if level == VipLevel.NORMAL
            else f"Max-Heap VIP (Ưu tiên mức {int(level)})"
        )
        rows.append([level.label, int(level), thresh_str, f"Giảm {rate_pct}%", queue_benefit])
    return render_table(headers, rows)


def format_waiting_table(entries, customer_service=None):
    headers = [
        "Thứ tự",
        "Mã chờ",
        "Mã KH",
        "Tên khách",
        "Hạng ưu tiên",
        "Loại phòng",
        "Nhận phòng",
        "Trả phòng",
        "Cấu trúc lưu",
    ]
    rows = []
    for idx, e in enumerate(entries, start=1):
        cname = ""
        vip_label = f"Mức {e.priority}"
        if customer_service is not None:
            try:
                cust = customer_service.get_customer(e.customer_id)
                cname = cust.full_name
                vip_label = f"{cust.vip_level.label} ({e.priority})"
            except Exception:
                cname = "-"
        ds_name = "Max-Heap (VIP)" if e.priority > 0 else "LinkedQueue (FIFO)"
        rows.append(
            [
                idx,
                e.entry_id,
                e.customer_id,
                cname,
                vip_label,
                e.room_type.label,
                format_date(e.check_in),
                format_date(e.check_out),
                ds_name,
            ]
        )
    return render_table(headers, rows)


def format_service_requests_table(requests):
    headers = [
        "Mã YC",
        "Phòng",
        "Mã KH",
        "Loại dịch vụ",
        "Độ khẩn",
        "Trạng thái",
        "Ghi chú",
    ]
    rows = []
    for req in requests:
        rows.append(
            [
                req.request_id,
                req.room_id,
                req.customer_id or "-",
                req.service_type.label,
                f"{req.urgency.label} ({int(req.urgency)})",
                req.status.label,
                req.note,
            ]
        )
    return render_table(headers, rows)


def format_undo_stack_table(actions):
    headers = ["Vị trí Stack", "Mã đơn bị hủy", "Phòng", "Người hủy", "Ngày hủy", "Trạng thái trước hủy"]
    rows = []
    for idx, act in enumerate(actions):
        pos = "ĐỈNH (Top)" if idx == 0 else f"Đáy -{idx}"
        rows.append(
            [
                pos,
                act.booking_id,
                act.room_id,
                act.cancelled_by,
                format_date(act.cancelled_at),
                act.booking_snapshot.get("status", ""),
            ]
        )
    return render_table(headers, rows)


def format_bill_detail(bill):
    """Hiển thị bảng kê chi tiết tổng chi phí (hóa đơn thanh toán) của một đơn đặt phòng."""
    booking = bill["booking"]
    customer = bill["customer"]
    room = bill["room"]
    pct = int(round(bill["discount_rate"] * 100))
    applied_pct = int(round(bill.get("applied_discount_rate", bill["discount_rate"]) * 100))
    discount_label = (
        f"4. Giảm giá VIP ({applied_pct}% lúc TT)"
        if bill["is_paid"] and applied_pct != pct
        else f"4. Giảm giá VIP ({applied_pct}%)"
    )

    lines = [
        f"=== BẢNG KÊ TỔNG CHI PHÍ / HÓA ĐƠN ĐẶT PHÒNG ({booking.booking_id}) ===",
    ]
    info_rows = [
        ["Mã đơn đặt phòng", f"{booking.booking_id} ({booking.status.label})"],
        ["Khách hàng", f"{customer.customer_id} - {customer.full_name} (SĐT: {customer.phone})"],
        ["Hạng thành viên VIP", f"{customer.vip_level.label} (Chiết khấu {pct}%)"],
        ["Tích lũy đã thanh toán", format_vnd(bill.get("customer_total_paid", 0))],
        ["Phòng lưu trú", f"{room.room_id} - Loại {room.room_type.label} (Tầng {room.floor})"],
        ["Thời gian lưu trú", f"{format_date(booking.check_in)} -> {format_date(booking.check_out)} ({bill['num_nights']} đêm)"],
        [
            "1. Tiền phòng",
            f"{bill['num_nights']} đêm × {format_vnd(bill['price_per_night'])} = {format_vnd(bill['room_cost'])}",
        ],
    ]
    if bill["service_items"]:
        srv_desc = ", ".join(
            f"{item['request_id']}:{item['service_type'].label}({format_vnd(item['fee'])})"
            for item in bill["service_items"]
        )
        info_rows.append(["2. Phí dịch vụ nội bộ", f"{format_vnd(bill['service_cost'])} [{srv_desc}]"])
    else:
        info_rows.append(["2. Phí dịch vụ nội bộ", "0 đ (Không phát sinh)"])

    info_rows.extend(
        [
            ["3. Phụ phí phát sinh khác", format_vnd(bill["extra_fee"])],
            ["Tổng tạm tính (1 + 2 + 3)", format_vnd(bill["gross_amount"])],
            [discount_label, f"- {format_vnd(bill['discount_amount'])}"],
            ["TỔNG CHI PHÍ PHẢI THANH TOÁN", format_vnd(bill["total_amount"])],
            [
                "Trạng thái thanh toán",
                f"{bill['payment_status'].label}"
                + (
                    f" (Mã GD: {bill['active_payment'].payment_id} - {bill['active_payment'].payment_method.label})"
                    if bill["active_payment"] is not None and bill["remaining_amount"] == 0
                    else (
                        f" (Đã thu {format_vnd(bill['paid_amount'])}, còn phải thu: {format_vnd(bill['remaining_amount'])})"
                        if bill["paid_amount"] > 0
                        else f" (Còn phải thu: {format_vnd(bill['remaining_amount'])})"
                    )
                ),
            ],
        ]
    )
    if bill.get("will_upgrade_vip") and not bill["is_paid"]:
        info_rows.append(
            [
                "Xét nâng hạng VIP tự động",
                f"Sau thanh toán đạt {format_vnd(bill['projected_total_paid'])} -> Tự động lên VIP {bill['projected_vip_level'].label}",
            ]
        )
    lines.append(render_table(["Khoản mục chi phí", "Chi tiết / Số tiền"], info_rows))
    return "\n".join(lines)


def format_payments_table(payments, customer_service=None):
    """Hiển thị bảng danh sách các giao dịch thanh toán đã lưu."""
    headers = [
        "Mã GD",
        "Mã đơn",
        "Mã KH",
        "Tên khách hàng",
        "Phòng",
        "Tiền phòng",
        "Phí DV+Phụ phí",
        "Giảm VIP",
        "Tổng thanh toán",
        "Phương thức",
        "Ngày TT",
        "Trạng thái",
    ]
    rows = []
    for tx in payments:
        cname = ""
        if customer_service is not None:
            try:
                cname = customer_service.get_customer(tx.customer_id).full_name
            except Exception:
                cname = "-"
        rows.append(
            [
                tx.payment_id,
                tx.booking_id,
                tx.customer_id,
                cname,
                tx.room_id,
                format_vnd(tx.room_cost),
                format_vnd(tx.service_cost + tx.extra_fee),
                format_vnd(tx.discount_amount),
                format_vnd(tx.total_amount),
                tx.payment_method.label,
                format_date(tx.paid_at),
                tx.status.label,
            ]
        )
    return render_table(headers, rows)
