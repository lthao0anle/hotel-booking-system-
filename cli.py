"""Giao diện dòng lệnh (CLI Menu) tương tác tiếng Việt cho Hệ thống Đặt phòng Khách sạn."""

from datetime import date, timedelta

from hotel.algorithms.merge_sort import merge_sort
from hotel.models.date_utils import format_date, parse_date
from hotel.models.enums import (
    BookingStatus,
    PaymentMethod,
    RoomType,
    ServiceType,
    UrgencyLevel,
    VipLevel,
)
from hotel.services.errors import HotelError, NotFoundError
from hotel.ui.formatter import (
    format_bill_detail,
    format_bookings_table,
    format_customers_table,
    format_payments_table,
    format_rooms_table,
    format_service_requests_table,
    format_undo_stack_table,
    format_vip_policy_table,
    format_vnd,
    format_waiting_table,
    render_floor_matrix,
    render_table,
)


def _prompt(text, default=None):
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"{text}{suffix}: ").strip()
    if not raw and default is not None:
        return str(default)
    return raw


def _prompt_date(text, default_date=None):
    default_str = format_date(default_date) if default_date is not None else None
    raw = _prompt(f"{text} (dd/mm/yyyy)", default_str)
    return parse_date(raw)


def _prompt_room_type(allow_all=True):
    options = "1=Đơn (SINGLE), 2=Đôi (DOUBLE), 3=Suite (SUITE)"
    if allow_all:
        options = "0=Tất cả, " + options
    choice = _prompt(f"Chọn loại phòng ({options})", "0" if allow_all else "1")
    mapping = {"1": RoomType.SINGLE, "2": RoomType.DOUBLE, "3": RoomType.SUITE}
    if allow_all and choice == "0":
        return None
    if choice not in mapping:
        raise HotelError("Lựa chọn loại phòng không hợp lệ")
    return mapping[choice]


class HotelCLI:
    def __init__(self, manager):
        self.manager = manager

    def run(self):
        while True:
            self._print_main_menu()
            choice = input("Chọn chức năng (0-10): ").strip()
            if choice == "0":
                self.manager.save()
                print("\nĐã lưu dữ liệu. Cảm ơn bạn đã sử dụng hệ thống!")
                break
            try:
                self._dispatch(choice)
            except HotelError as exc:
                print(f"\n[!] Lỗi nghiệp vụ: {exc}")
            except ValueError as exc:
                print(f"\n[!] Dữ liệu nhập chưa hợp lệ: {exc}")
            except (KeyboardInterrupt, EOFError):
                self.manager.save()
                print("\nĐã lưu dữ liệu và thoát chương trình.")
                break

    def _print_main_menu(self):
        print("\n" + "=" * 78)
        print("   HỆ THỐNG QUẢN LÝ ĐẶT PHÒNG KHÁCH SẠN (CẤU TRÚC DỮ LIỆU & GIẢI THUẬT - MI3060)")
        print("=" * 78)
        print("  1. Sơ đồ phòng theo tầng & Tra cứu phòng O(1)         [Mảng 2 chiều Matrix2D]")
        print("  2. Tìm phòng trống theo khoảng ngày                   [BST / AVL IntervalSchedule]")
        print("  3. Lọc & Sắp xếp phòng theo loại, giá, ngân sách      [Merge/Quick Sort + Binary Search]")
        print("  4. Đặt phòng / Nhận phòng (Check-in) / Trả phòng      [BST O(log n) + HashTable]")
        print("  5. Hủy đặt phòng & Hoàn tác (Undo)                    [Ngăn xếp Stack O(1)]")
        print("  6. Danh sách chờ khi hết phòng (Thường & VIP)         [Queue FIFO + Max-Heap VIP]")
        print("  7. Quản lý khách hàng & Lịch sử lưu trú               [Hash Table O(1) + Linked List]")
        print("  8. Yêu cầu dịch vụ nội bộ (Dọn phòng, Đồ ăn, Y tế)    [Priority Queue Max-Heap]")
        print("  9. Quản lý thanh toán (Tính phí, Xử lý, Lưu & Tra cứu)[Hash Table O(1) + Linked List]")
        print("  10. Thống kê doanh thu, tỷ lệ lấp đầy & Khởi tạo mẫu  [Báo cáo & JSON Persistence]")
        print("  0. Lưu và Thoát")
        print("-" * 78)

    def _dispatch(self, choice):
        handlers = {
            "1": self._menu_room_matrix,
            "2": self._menu_available_rooms,
            "3": self._menu_sort_and_search_rooms,
            "4": self._menu_booking_operations,
            "5": self._menu_cancel_and_undo,
            "6": self._menu_waiting_list,
            "7": self._menu_customers_and_history,
            "8": self._menu_service_requests,
            "9": self._menu_payments,
            "10": self._menu_reports_and_system,
        }
        handler = handlers.get(choice)
        if handler is None:
            print("\n[!] Vui lòng chọn số từ 0 đến 10.")
        else:
            handler()

    # -------------------- 1. Mảng 2 chiều Phòng ------------------------ #
    def _menu_room_matrix(self):
        print("\n--- [1] SƠ ĐỒ PHÒNG THEO TẦNG & TRA CỨU TRỰC TIẾP O(1) ---")
        print("  1. Hiển thị sơ đồ ma trận toàn khách sạn theo ngày")
        print("  2. Tra cứu trực tiếp phòng theo (Tầng, Số phòng) hoặc Mã phòng — O(1)")
        print("  3. Đặt / Gỡ trạng thái Bảo trì cho phòng")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            target = _prompt_date("Xem trạng thái tại ngày", date.today())
            print("\n" + render_floor_matrix(self.manager.floor_map(target), target))
        elif sub == "2":
            code = _prompt("Nhập mã phòng (vd P205) hoặc để trống để nhập tầng/số")
            if code:
                room = self.manager.get_room(code)
            else:
                floor = int(_prompt("Nhập tầng", "2"))
                room_number = int(_prompt("Nhập số phòng trong tầng", "5"))
                room = self.manager.get_room_by_coords(floor, room_number)
            status = self.manager.bookings.room_status_on(room.room_id, date.today())
            print("\n" + format_rooms_table([room], self.manager))
            print(f"-> Truy cập trực tiếp Matrix2D[{room.floor - 1}][{room.room_number - 1}] = {status.label}")
            bookings = self.manager.bookings.bookings_for_room(room.room_id)
            if bookings:
                print("\nLịch đặt của phòng trên cây BST (in-order theo ngày nhận):")
                print(format_bookings_table(bookings, self.manager.customers))
        elif sub == "3":
            code = _prompt("Nhập mã phòng cần đổi trạng thái bảo trì", "P104")
            flag = _prompt("Đặt bảo trì? (1=Bảo trì, 0=Hoạt động bình thường)", "0") == "1"
            room = self.manager.set_room_maintenance(code, flag)
            print(f"\nĐã cập nhật phòng {room.room_id}: under_maintenance = {room.under_maintenance}")

    # -------------------- 2. Tìm phòng trống trên BST ------------------ #
    def _menu_available_rooms(self):
        print("\n--- [2] TÌM PHÒNG TRỐNG THEO KHOẢNG NGÀY (BST O(log n)) ---")
        today = date.today()
        check_in = _prompt_date("Ngày nhận phòng", today + timedelta(days=1))
        check_out = _prompt_date("Ngày trả phòng", today + timedelta(days=3))
        rtype = _prompt_room_type(allow_all=True)
        rooms = self.manager.find_available_rooms(check_in, check_out, room_type=rtype)
        print(
            f"\nTìm thấy {len(rooms)} phòng trống từ {format_date(check_in)} đến {format_date(check_out)}:"
        )
        print(format_rooms_table(rooms, self.manager, check_in))

    # ------------- 3. Sắp xếp & Tìm kiếm nhị phân theo giá ------------- #
    def _menu_sort_and_search_rooms(self):
        print("\n--- [3] LỌC, SẮP XẾP (MERGE/QUICK SORT) & TÌM KIẾM NHỊ PHÂN ---")
        print("  1. Sắp xếp danh sách phòng theo giá (Merge Sort / Quick Sort — O(R log R))")
        print("  2. Tìm phòng theo khoảng giá [min, max] (Binary Search — O(log R + k))")
        print("  3. Gợi ý phòng có giá gần nhất với ngân sách (Binary Search — O(log R))")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            algo = "quick" if _prompt("Giải thuật (1=Merge Sort, 2=Quick Sort)", "1") == "2" else "merge"
            rev = _prompt("Thứ tự (1=Tăng dần, 2=Giảm dần)", "1") == "2"
            rooms = self.manager.sort_rooms(by="price", reverse=rev, algorithm=algo)
            print(f"\nDanh sách phòng sắp xếp bằng {algo.upper()} SORT:")
            print(format_rooms_table(rooms, self.manager))
        elif sub == "2":
            min_p = int(_prompt("Giá tối thiểu (VND)", "500000"))
            max_p = int(_prompt("Giá tối đa (VND)", "1000000"))
            rtype = _prompt_room_type(allow_all=True)
            rooms = self.manager.filter_rooms_by_price(min_p, max_p, room_type=rtype)
            print(f"\nKết quả Binary Search trong khoảng [{format_vnd(min_p)} .. {format_vnd(max_p)}]:")
            print(format_rooms_table(rooms, self.manager))
        elif sub == "3":
            budget = int(_prompt("Nhập ngân sách dự kiến / đêm (VND)", "850000"))
            rtype = _prompt_room_type(allow_all=True)
            room = self.manager.suggest_room_by_budget(budget, room_type=rtype)
            if room is None:
                print("\nKhông tìm thấy phòng phù hợp.")
            else:
                print(f"\nPhòng có giá gần ngân sách {format_vnd(budget)} nhất (O(log R)):")
                print(format_rooms_table([room], self.manager))

    # ---------------- 4. Đặt phòng / Nhận / Trả phòng ------------------ #
    def _resolve_or_register_customer(self, identifier):
        """Tìm khách hàng theo Mã/CCCD/SĐT; nếu chưa có thì cho phép đăng ký nhanh tại chỗ."""
        try:
            return self.manager.lookup_customer(identifier)
        except NotFoundError:
            print(f"\n[i] Khách hàng '{identifier}' chưa có trong hệ thống.")
            ans = _prompt("Bạn có muốn đăng ký mới khách hàng này ngay bây giờ không? (y/n)", "y").lower()
            if ans != "y":
                raise
            raw = (identifier or "").strip()
            default_phone = raw if raw.isdigit() and len(raw) <= 11 else ""
            default_cccd = raw if raw.isdigit() and len(raw) >= 12 else ""
            name = _prompt("  + Họ và tên khách hàng")
            cccd = _prompt("  + Số CCCD (8..15 chữ số)", default_cccd or None)
            phone = _prompt("  + Số điện thoại (8..15 chữ số)", default_phone or None)
            vip = int(_prompt("  + Cấp VIP (0=Thường, 1=Silver, 2=Gold, 3=Platinum)", "0"))
            customer = self.manager.register_customer(name, cccd, phone, VipLevel(vip))
            print(f"[OK] Đã tạo khách hàng mới: {customer.customer_id} - {customer.full_name} (SĐT: {customer.phone})")
            return customer

    def _menu_booking_operations(self):
        print("\n--- [4] ĐẶT PHÒNG / NHẬN PHÒNG (CHECK-IN) / TRẢ PHÒNG (CHECK-OUT) ---")
        print("  1. Đặt phòng cụ thể theo mã phòng (kiểm tra xung đột trên BST)")
        print("  2. Đặt phòng theo loại (tự động vào Hàng chờ nếu hết phòng)")
        print("  3. Nhận phòng (Check-in)")
        print("  4. Trả phòng (Check-out)")
        print("  5. Xem danh sách toàn bộ đơn đặt phòng")
        sub = _prompt("Chọn", "1")
        today = date.today()
        if sub == "1":
            cid = _prompt("Mã KH / CCCD / SĐT khách hàng", "KH001")
            customer = self._resolve_or_register_customer(cid)
            old_vip = customer.vip_level
            room_id = _prompt("Mã phòng muốn đặt (vd P205)", "P103")
            check_in = _prompt_date("Ngày nhận phòng", today + timedelta(days=1))
            check_out = _prompt_date("Ngày trả phòng", today + timedelta(days=3))
            booking = self.manager.book_room(customer.customer_id, room_id, check_in, check_out)
            print("\n[OK] Đặt phòng thành công:")
            print(format_bookings_table([booking], self.manager.customers))
            new_vip = self.manager.customers.get_customer(customer.customer_id).vip_level
            if new_vip > old_vip:
                total_paid = self.manager.customer_total_paid(customer.customer_id)
                print(
                    f"[★ VIP UPGRADE] Khách hàng {customer.full_name} ({customer.customer_id}) "
                    f"đạt tích lũy {format_vnd(total_paid)} -> Tự động nâng hạng VIP: {old_vip.label} -> {new_vip.label}!"
                )
        elif sub == "2":
            cid = _prompt("Mã KH / CCCD / SĐT khách hàng", "KH004")
            customer = self._resolve_or_register_customer(cid)
            old_vip = customer.vip_level
            rtype = _prompt_room_type(allow_all=False)
            check_in = _prompt_date("Ngày nhận phòng", today + timedelta(days=1))
            check_out = _prompt_date("Ngày trả phòng", today + timedelta(days=3))
            mode, record = self.manager.book_by_type_or_wait(
                customer.customer_id, rtype, check_in, check_out
            )
            if mode == "BOOKED":
                print("\n[OK] Còn phòng trống — Đã tạo đơn đặt phòng:")
                print(format_bookings_table([record], self.manager.customers))
                new_vip = self.manager.customers.get_customer(customer.customer_id).vip_level
                if new_vip > old_vip:
                    total_paid = self.manager.customer_total_paid(customer.customer_id)
                    print(
                        f"[★ VIP UPGRADE] Khách hàng {customer.full_name} ({customer.customer_id}) "
                        f"đạt tích lũy {format_vnd(total_paid)} -> Tự động nâng hạng VIP: {old_vip.label} -> {new_vip.label}!"
                    )
            else:
                print("\n[!] Hết phòng trống loại yêu cầu — Đã xếp khách vào danh sách chờ:")
                print(format_waiting_table([record], self.manager.customers))
        elif sub == "3":
            bid = _prompt("Nhập mã đơn đặt phòng cần Check-in", "BK00004")
            booking = self.manager.check_in(bid)
            print("\n[OK] Đã nhận phòng:")
            print(format_bookings_table([booking], self.manager.customers))
        elif sub == "4":
            bid = _prompt("Nhập mã đơn đặt phòng cần Check-out", "BK00003")
            bill = self.manager.calculate_booking_cost(bid)
            print("\n" + format_bill_detail(bill))
            if not bill["is_paid"]:
                pay_now = _prompt("Đơn này chưa thanh toán. Thanh toán ngay khi trả phòng? (y/n)", "y").lower()
                if pay_now == "y":
                    old_vip = bill["customer"].vip_level
                    method = self._prompt_payment_method()
                    extra = int(_prompt("Phụ phí phát sinh thêm (VND)", "0"))
                    note = _prompt("Ghi chú thanh toán", "Thanh toán khi trả phòng")
                    tx = self.manager.process_payment(bid, payment_method=method, extra_fee=extra, note=note)
                    print(f"\n[OK] Đã xử lý và lưu giao dịch thanh toán {tx.payment_id}:")
                    print(format_payments_table([tx], self.manager.customers))
                    new_vip = self.manager.customers.get_customer(tx.customer_id).vip_level
                    if new_vip > old_vip:
                        total_paid = self.manager.customer_total_paid(tx.customer_id)
                        print(
                            f"[★ VIP UPGRADE] Khách hàng {bill['customer'].full_name} ({tx.customer_id}) "
                            f"đạt tích lũy {format_vnd(total_paid)} -> Tự động nâng hạng VIP: {old_vip.label} -> {new_vip.label}!"
                        )
            booking = self.manager.check_out(bid)
            print("\n[OK] Đã trả phòng:")
            print(format_bookings_table([booking], self.manager.customers))
        elif sub == "5":
            bookings = merge_sort(self.manager.bookings.all_bookings(), key=lambda b: b.booking_id)
            print("\nDanh sách toàn bộ đơn đặt phòng:")
            print(format_bookings_table(bookings, self.manager.customers))

    # ---------------- 5. Hủy đặt phòng & Hoàn tác (Stack) -------------- #
    def _menu_cancel_and_undo(self):
        print("\n--- [5] HỦY ĐẶT PHÒNG & HOÀN TÁC (STACK LIFO — O(1)) ---")
        print("  1. Hủy một đơn đặt phòng (push vào Undo Stack)")
        print("  2. Hoàn tác thao tác hủy gần nhất (pop từ Undo Stack)")
        print("  3. Xem ngăn xếp các thao tác hủy hiện tại")
        sub = _prompt("Chọn", "3")
        if sub == "1":
            bid = _prompt("Nhập mã đơn đặt phòng cần hủy", "BK00004")
            by = _prompt("Người thực hiện hủy (STAFF / CUSTOMER)", "STAFF").upper()
            action, _ = self.manager.cancel_booking(bid, cancelled_by=by)
            print(f"\n[OK] Đã hủy đơn {action.booking_id} và đẩy vào đỉnh Undo Stack.")
        elif sub == "2":
            action, booking = self.manager.undo_last_cancellation()
            print(f"\n[OK] Đã hoàn tác lệnh hủy đơn {action.booking_id} — Khôi phục lịch trên BST:")
            print(format_bookings_table([booking], self.manager.customers))
        elif sub == "3":
            print("\nNgăn xếp hoàn tác (Stack — từ đỉnh xuống đáy):")
            print(format_undo_stack_table(self.manager.undo.history()))

    # ---------------- 6. Danh sách chờ (Queue + Max-Heap) -------------- #
    def _menu_waiting_list(self):
        print("\n--- [6] DANH SÁCH CHỜ KHI HẾT PHÒNG (QUEUE THƯỜNG + MAX-HEAP VIP) ---")
        print("  1. Xem danh sách chờ theo thứ tự ưu tiên phục vụ")
        print("  2. Thêm khách vào danh sách chờ")
        print("  3. Tự động phân phòng trống cho danh sách chờ (ưu tiên VIP trước)")
        print("  4. Lấy khách ưu tiên cao nhất ra khỏi hàng chờ (pop)")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            entries = self.manager.waiting.list_waiting_ordered()
            print(
                f"\nDanh sách chờ ({self.manager.waiting.vip_count()} VIP trong Max-Heap, "
                f"{self.manager.waiting.normal_count()} khách thường trong LinkedQueue):"
            )
            print(format_waiting_table(entries, self.manager.customers))
        elif sub == "2":
            cid = _prompt("Mã KH / CCCD / SĐT", "KH001")
            customer = self._resolve_or_register_customer(cid)
            rtype = _prompt_room_type(allow_all=False)
            today = date.today()
            check_in = _prompt_date("Ngày nhận mong muốn", today + timedelta(days=1))
            check_out = _prompt_date("Ngày trả mong muốn", today + timedelta(days=3))
            entry = self.manager.add_to_waiting_list(customer.customer_id, rtype, check_in, check_out)
            print("\n[OK] Đã thêm vào hàng chờ:")
            print(format_waiting_table([entry], self.manager.customers))
        elif sub == "3":
            fulfilled = self.manager.process_waiting_list()
            if not fulfilled:
                print("\nHiện chưa có phòng trống khớp với nhu cầu trong danh sách chờ.")
            else:
                print(f"\n[OK] Đã tự động xếp phòng cho {len(fulfilled)} khách trong danh sách chờ:")
                print(format_bookings_table([b for _, b in fulfilled], self.manager.customers))
        elif sub == "4":
            entry = self.manager.pop_next_waiting()
            print("\n[OK] Khách được lấy ra đầu tiên (ưu tiên cao nhất):")
            print(format_waiting_table([entry], self.manager.customers))

    # ---------------- 7. Khách hàng & Lịch sử lưu trú ------------------ #
    def _menu_customers_and_history(self):
        print("\n--- [7] QUẢN LÝ KHÁCH HÀNG (HASH TABLE) & LỊCH SỬ LƯU TRÚ (LINKED LIST) ---")
        print("  1. Danh sách toàn bộ khách hàng (kèm tích lũy đã TT & tiến độ nâng VIP)")
        print("  2. Tra cứu khách hàng theo Mã KH / CCCD / SĐT — O(1) trung bình")
        print("  3. Xem lịch sử lưu trú của khách (duyệt SinglyLinkedList)")
        print("  4. Đăng ký khách hàng mới")
        print("  5. Cập nhật hạng VIP cho khách hàng")
        print("  6. Xem chính sách mốc tích lũy & Quyền lợi tự động nâng hạng VIP")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            customers = merge_sort(self.manager.customers.all_customers(), key=lambda c: c.customer_id)
            print("\nDanh sách khách hàng:")
            print(format_customers_table(customers, self.manager.payments))
        elif sub == "2":
            ident = _prompt("Nhập Mã KH, CCCD hoặc Số điện thoại", "0901234567")
            customer = self.manager.lookup_customer(ident)
            print("\nKết quả tra cứu trên Bảng băm (Hash Table):")
            print(format_customers_table([customer], self.manager.payments))
        elif sub == "3":
            ident = _prompt("Nhập Mã KH, CCCD hoặc Số điện thoại", "KH004")
            customer = self.manager.lookup_customer(ident)
            history = self.manager.customer_stay_history(customer.customer_id)
            print(
                f"\nLịch sử lưu trú của {customer.full_name} ({customer.customer_id}) "
                f"— SinglyLinkedList (mới nhất ở đầu):"
            )
            print(format_bookings_table(history, self.manager.customers))
        elif sub == "4":
            name = _prompt("Họ và tên khách hàng")
            cccd = _prompt("Số CCCD (9..12 chữ số)")
            phone = _prompt("Số điện thoại (9..12 chữ số)")
            vip = int(_prompt("Cấp VIP (0=Thường, 1=Silver, 2=Gold, 3=Platinum)", "0"))
            customer = self.manager.register_customer(name, cccd, phone, VipLevel(vip))
            print("\n[OK] Đã đăng ký khách hàng mới:")
            print(format_customers_table([customer], self.manager.payments))
        elif sub == "5":
            ident = _prompt("Nhập Mã KH / CCCD / SĐT", "KH001")
            customer = self.manager.lookup_customer(ident)
            vip = int(_prompt("Cấp VIP mới (0=Thường, 1=Silver, 2=Gold, 3=Platinum)", "2"))
            updated = self.manager.set_customer_vip(customer.customer_id, VipLevel(vip))
            print("\n[OK] Đã cập nhật cấp VIP (đồng thời vun lại đống Max-Heap nếu đang chờ):")
            print(format_customers_table([updated], self.manager.payments))
        elif sub == "6":
            print("\nChính sách tự động nâng hạng VIP theo tổng tiền đã thanh toán tích lũy:")
            print(format_vip_policy_table())

    # ---------------- 8. Yêu cầu dịch vụ nội bộ ------------------------ #
    def _menu_service_requests(self):
        print("\n--- [8] YÊU CẦU DỊCH VỤ NỘI BỘ THEO ĐỘ KHẨN (MAX-HEAP — O(log s)) ---")
        print("  1. Xem hàng đợi yêu cầu dịch vụ đang chờ (theo độ ưu tiên giảm dần)")
        print("  2. Gửi yêu cầu dịch vụ mới (Dọn phòng / Đồ ăn / Y tế / Khác)")
        print("  3. Xử lý yêu cầu khẩn cấp nhất tiếp theo (pop từ Max-Heap)")
        print("  4. Xem lịch sử các yêu cầu dịch vụ đã hoàn thành")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            pending = self.manager.service_requests.pending_requests_ordered()
            print("\nHàng đợi ưu tiên yêu cầu dịch vụ (Max-Heap):")
            print(format_service_requests_table(pending))
        elif sub == "2":
            room_id = _prompt("Mã phòng gửi yêu cầu", "P101")
            t_choice = _prompt("Loại dịch vụ (1=Dọn phòng, 2=Đồ ăn, 3=Y tế, 4=Khác)", "2")
            t_map = {
                "1": ServiceType.CLEANING,
                "2": ServiceType.FOOD,
                "3": ServiceType.MEDICAL,
                "4": ServiceType.OTHER,
            }
            if t_choice not in t_map:
                raise HotelError("Loại dịch vụ không hợp lệ")
            u_choice = _prompt("Độ khẩn (1=Thấp, 2=Bình thường, 3=Khẩn cấp)", "2")
            u_map = {"1": UrgencyLevel.LOW, "2": UrgencyLevel.NORMAL, "3": UrgencyLevel.EMERGENCY}
            if u_choice not in u_map:
                raise HotelError("Độ khẩn không hợp lệ")
            note = _prompt("Ghi chú chi tiết", "Phục vụ tại phòng")
            req = self.manager.submit_service_request(
                room_id=room_id,
                service_type=t_map[t_choice],
                urgency=u_map[u_choice],
                note=note,
            )
            print("\n[OK] Đã thêm yêu cầu vào Max-Heap:")
            print(format_service_requests_table([req]))
        elif sub == "3":
            req = self.manager.process_next_service_request()
            print("\n[OK] Đã lấy và xử lý yêu cầu có độ ưu tiên cao nhất:")
            print(format_service_requests_table([req]))
        elif sub == "4":
            done = self.manager.service_requests.completed_requests()
            print("\nCác yêu cầu dịch vụ đã xử lý xong:")
            print(format_service_requests_table(done))

    # ---------------- 9. Quản lý thanh toán (HashTable + LL) ----------- #
    def _prompt_payment_method(self):
        choice = _prompt(
            "Chọn phương thức thanh toán (1=Tiền mặt, 2=Chuyển khoản, 3=Thẻ ngân hàng, 4=Ví điện tử)",
            "2",
        )
        mapping = {
            "1": PaymentMethod.CASH,
            "2": PaymentMethod.BANK_TRANSFER,
            "3": PaymentMethod.CARD,
            "4": PaymentMethod.E_WALLET,
        }
        if choice not in mapping:
            raise HotelError("Phương thức thanh toán không hợp lệ")
        return mapping[choice]

    def _menu_payments(self):
        print("\n--- [9] QUẢN LÝ THANH TOÁN: TÍNH TỔNG CHI PHÍ, XỬ LÝ, LƯU TRỮ & TRA CỨU ---")
        print("  1. Tính tổng chi phí & Xem bảng kê hóa đơn chi tiết của đơn đặt phòng")
        print("  2. Xử lý thanh toán cho đơn đặt phòng (lưu vào HashTable + SinglyLinkedList)")
        print("  3. Xem toàn bộ lịch sử giao dịch thanh toán đã lưu trữ")
        print("  4. Tra cứu thanh toán theo Mã GD / Mã đơn / Mã KH / CCCD / SĐT / Phòng — O(1)")
        print("  5. Hoàn tiền giao dịch thanh toán (Refund)")
        print("  6. Thống kê tổng hợp thanh toán & công nợ chưa thu")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            bid = _prompt("Nhập mã đơn đặt phòng cần tính chi phí", "BK00003")
            extra = int(_prompt("Phụ phí phát sinh khác (nếu có, VND)", "0"))
            bill = self.manager.calculate_booking_cost(bid, extra_fee=extra)
            print("\n" + format_bill_detail(bill))
        elif sub == "2":
            bid = _prompt("Nhập mã đơn đặt phòng cần thanh toán", "BK00003")
            extra = int(_prompt("Phụ phí phát sinh khác (VND)", "0"))
            bill = self.manager.calculate_booking_cost(bid, extra_fee=extra)
            print("\n" + format_bill_detail(bill))
            if bill["is_paid"]:
                print(f"\n[!] Đơn {bid} đã được thanh toán (Mã GD: {bill['active_payment'].payment_id}).")
                return
            old_vip = bill["customer"].vip_level
            method = self._prompt_payment_method()
            note = _prompt("Ghi chú giao dịch", "Thanh toán hóa đơn lưu trú")
            auto_co = False
            if bill["booking"].status == BookingStatus.CHECKED_IN:
                auto_co = _prompt("Khách đang ở — Tự động trả phòng (Check-out) luôn? (y/n)", "n").lower() == "y"
            tx = self.manager.process_payment(
                booking_id=bid,
                payment_method=method,
                extra_fee=extra,
                note=note,
                auto_check_out=auto_co,
            )
            print(f"\n[OK] Đã xử lý thanh toán thành công và lưu giao dịch {tx.payment_id}:")
            print(format_payments_table([tx], self.manager.customers))
            new_vip = self.manager.customers.get_customer(tx.customer_id).vip_level
            if new_vip > old_vip:
                total_paid = self.manager.customer_total_paid(tx.customer_id)
                print(
                    f"[★ VIP UPGRADE] Khách hàng {bill['customer'].full_name} ({tx.customer_id}) "
                    f"đạt tích lũy {format_vnd(total_paid)} -> Tự động nâng hạng VIP: {old_vip.label} -> {new_vip.label}!"
                )
        elif sub == "3":
            txs = self.manager.all_payments()
            print(f"\nDanh sách giao dịch thanh toán ({len(txs)} giao dịch — mới nhất ở đầu SinglyLinkedList):")
            print(format_payments_table(txs, self.manager.customers))
        elif sub == "4":
            q = _prompt("Nhập Mã GD (TT...), Mã đơn (BK...), Mã KH/CCCD/SĐT hoặc Mã phòng", "TT00001")
            found = self.manager.lookup_payments(q)
            print(f"\nKết quả tra cứu thanh toán cho '{q}' ({len(found)} giao dịch):")
            print(format_payments_table(found, self.manager.customers))
        elif sub == "5":
            ident = _prompt("Nhập Mã giao dịch (TT...) hoặc Mã đơn (BK...) cần hoàn tiền", "TT00002")
            reason = _prompt("Lý do hoàn tiền", "Khách thay đổi lịch trình")
            tx = self.manager.refund_payment(ident, reason=reason)
            print(f"\n[OK] Đã hoàn tiền giao dịch {tx.payment_id}:")
            print(format_payments_table([tx], self.manager.customers))
        elif sub == "6":
            summary = self.manager.payments.payment_summary()
            rows = [
                ["Tổng số giao dịch đã ghi nhận", summary["total_transactions"]],
                ["Số giao dịch Đã thanh toán / Đã hoàn tiền", f"{summary['paid_transactions']} / {summary['refunded_transactions']}"],
                ["Tổng số tiền đã thu thực tế", format_vnd(summary["total_collected"])],
                ["Tổng phí dịch vụ & phụ phí đã thu", format_vnd(summary["total_service_fee"])],
                ["Tổng chiết khấu VIP đã giảm cho khách", format_vnd(summary["total_discount"])],
                ["Tổng tiền đã hoàn trả (Refund)", format_vnd(summary["total_refunded"])],
                ["Số đơn hiệu lực chưa thanh toán", summary["unpaid_bookings_count"]],
                ["Tổng chi phí dự kiến cần thu thêm", format_vnd(summary["unpaid_estimated_total"])],
            ]
            print("\n=== THỐNG KÊ TỔNG HỢP QUẢN LÝ THANH TOÁN ===")
            print(render_table(["Chỉ tiêu thanh toán", "Giá trị"], rows))
            method_rows = [
                [
                    m.label,
                    summary["count_by_method"][m],
                    format_vnd(summary["revenue_by_method"][m]),
                ]
                for m in PaymentMethod
            ]
            print("\nDoanh thu đã thu theo phương thức thanh toán:")
            print(render_table(["Phương thức", "Số giao dịch", "Tổng tiền thu"], method_rows))

    # ---------------- 10. Báo cáo thống kê & Hệ thống ------------------ #
    def _menu_reports_and_system(self):
        print("\n--- [10] THỐNG KÊ DOANH THU, TỶ LỆ LẤP ĐẦY & DỮ LIỆU HỆ THỐNG ---")
        print("  1. Báo cáo doanh thu & tỷ lệ lấp đầy phòng")
        print("  2. Bảng xếp hạng Top khách hàng thân thiết (Merge Sort)")
        print("  3. Khởi tạo lại dữ liệu mẫu mặc định (Reset Sample Data)")
        sub = _prompt("Chọn", "1")
        if sub == "1":
            rev = self.manager.reports.revenue_summary()
            occ = self.manager.reports.occupancy_on(date.today())
            pay_sum = self.manager.payments.payment_summary()
            print("\n=== TỔNG HỢP DOANH THU & CÔNG SUẤT PHÒNG ===")
            summary_rows = [
                ["Tổng doanh thu (các đơn hiệu lực)", format_vnd(rev["total_revenue"])],
                ["Doanh thu đã thực hiện (Đang ở / Đã trả)", format_vnd(rev["realized_revenue"])],
                ["Doanh thu đặt trước (Đã xác nhận)", format_vnd(rev["confirmed_revenue"])],
                [
                    "Tổng tiền đã thu qua giao dịch TT",
                    f"{format_vnd(pay_sum['total_collected'])} ({pay_sum['paid_transactions']} GD)",
                ],
                ["Tổng chiết khấu VIP đã giảm", format_vnd(pay_sum["total_discount"])],
                [
                    "Số đơn chưa thanh toán / Công nợ dự kiến",
                    f"{pay_sum['unpaid_bookings_count']} đơn ({format_vnd(pay_sum['unpaid_estimated_total'])})",
                ],
                ["Số đơn hiệu lực / Số đơn đã hủy", f"{rev['active_bookings']} / {rev['cancelled_bookings']}"],
                [
                    f"Công suất phòng hôm nay ({format_date(occ['date'])})",
                    f"{occ['booked_rooms']}/{occ['total_rooms']} phòng ({occ['occupancy_rate']}%)",
                ],
                ["Số phòng trống / Số phòng bảo trì", f"{occ['empty_rooms']} / {occ['maintenance_rooms']}"],
            ]
            print(render_table(["Chỉ tiêu thống kê", "Giá trị"], summary_rows))

            type_rows = [
                [
                    rtype.label,
                    rev["nights_by_type"][rtype],
                    format_vnd(rev["revenue_by_type"][rtype]),
                ]
                for rtype in RoomType
            ]
            print("\nDoanh thu theo loại phòng:")
            print(render_table(["Loại phòng", "Tổng số đêm", "Doanh thu"], type_rows))
        elif sub == "2":
            top = self.manager.reports.top_customers(limit=10)
            rows = [
                [
                    idx,
                    item["customer"].customer_id,
                    item["customer"].full_name,
                    item["customer"].vip_level.label,
                    item["booking_count"],
                    item["total_nights"],
                    format_vnd(item["total_spent"]),
                    format_vnd(item.get("total_paid", 0)),
                ]
                for idx, item in enumerate(top, start=1)
            ]
            print("\nTop khách hàng theo tổng chi tiêu:")
            print(
                render_table(
                    [
                        "Hạng",
                        "Mã KH",
                        "Họ và tên",
                        "VIP",
                        "Số đơn",
                        "Tổng đêm",
                        "Tổng đặt phòng",
                        "Tích lũy đã TT",
                    ],
                    rows,
                )
            )
        elif sub == "3":
            confirm = _prompt("Bạn có chắc chắn muốn nạp lại dữ liệu mẫu? (y/n)", "n").lower()
            if confirm == "y":
                self.manager.reset_with_sample_data()
                print("\n[OK] Đã khởi tạo lại toàn bộ dữ liệu mẫu và lưu ra file JSON.")


def run_demo_walkthrough(manager):
    """Chạy kịch bản minh họa tự động toàn bộ 8 chức năng cốt lõi trên console."""
    today = date.today()
    print("=" * 88)
    print("   MINH HỌA TỰ ĐỘNG CÁC LUỒNG NGHIỆP VỤ & CẤU TRÚC DỮ LIỆU CỐT LÕI")
    print("=" * 88)

    print("\n[1] MẢNG 2 CHIỀU (Matrix2D) — Sơ đồ ma trận phòng theo tầng:")
    print(render_floor_matrix(manager.floor_map(today), today))

    print("\n[2] CÂY NHỊ PHÂN TÌM KIẾM CÂN BẰNG (AVL / BST) — Tìm phòng Suite trống (ngày mai -> +3 ngày):")
    ci, co = today + timedelta(days=1), today + timedelta(days=3)
    avail = manager.find_available_rooms(ci, co, room_type=RoomType.SUITE)
    print(format_rooms_table(avail[:5], manager, ci))

    print("\n[3] MERGE SORT & BINARY SEARCH — Gợi ý phòng gần ngân sách 850.000 đ nhất:")
    suggested = manager.suggest_room_by_budget(850_000)
    print(format_rooms_table([suggested], manager, today))

    print("\n[4] HASH TABLE & LINKED LIST — Tra cứu khách hàng CCCD '001200045678' và lịch sử lưu trú:")
    cust = manager.lookup_customer("001200045678")
    print(format_customers_table([cust], manager.payments))
    print(format_bookings_table(manager.customer_stay_history(cust.customer_id), manager.customers))

    print("\n[5] STACK (NGĂN XẾP) — Xem thao tác hủy đang nằm ở đỉnh Stack và thực hiện Hoàn tác (Undo):")
    print(format_undo_stack_table(manager.undo.history()))
    action, restored = manager.undo_last_cancellation()
    print(f"-> Sau khi gọi undo_last_cancellation(): đơn {action.booking_id} trở lại trạng thái '{restored.status.label}'!")
    print(format_bookings_table([restored], manager.customers))
    # Hủy lại để giữ nguyên trạng thái mẫu
    manager.cancel_booking(restored.booking_id, cancelled_by="STAFF")

    print("\n[6] HÀNG ĐỢI ƯU TIÊN (Max-Heap VIP + LinkedQueue thường) — Thứ tự phục vụ danh sách chờ:")
    print(format_waiting_table(manager.waiting.list_waiting_ordered(), manager.customers))

    print("\n[7] YÊU CẦU DỊCH VỤ NỘI BỘ (Max-Heap theo độ khẩn) — Thứ tự xử lý:")
    print(format_service_requests_table(manager.service_requests.pending_requests_ordered()))

    print("\n[8] QUẢN LÝ THANH TOÁN (HashTable + SinglyLinkedList) — Tính tổng chi phí, thanh toán & tra cứu:")
    bill = manager.calculate_booking_cost("BK00003")
    print(format_bill_detail(bill))
    print("\nDanh sách các giao dịch thanh toán đang lưu trữ:")
    print(format_payments_table(manager.all_payments(), manager.customers))
