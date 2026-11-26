"""Giao diện đồ họa Tkinter (GUI) cho Hệ thống Quản lý Đặt phòng Khách sạn."""

from datetime import date, timedelta
import tkinter as tk
from tkinter import messagebox, ttk

from hotel.algorithms.merge_sort import merge_sort
from hotel.models.date_utils import format_date, parse_date
from hotel.models.enums import (
    PaymentMethod,
    RoomStatus,
    RoomType,
    ServiceType,
    UrgencyLevel,
    VipLevel,
)
from hotel.services.errors import HotelError
from hotel.ui.formatter import format_bill_detail, format_vnd


STATUS_COLORS = {
    RoomStatus.EMPTY: ("#d4efdf", "#196f3d"),
    RoomStatus.BOOKED: ("#fadbd8", "#922b21"),
    RoomStatus.MAINTENANCE: ("#e5e7e9", "#424949"),
}


class HotelGUI:
    def __init__(self, manager):
        self.manager = manager
        self.root = tk.Tk()
        self.root.title("Hệ thống Quản lý Đặt phòng Khách sạn — CTDL & GT (MI3060)")
        self.root.geometry("1180x740")
        self.selected_room_id = "P101"

        self._build_layout()
        self.refresh_all()

    def run(self):
        self.root.mainloop()

    def _build_layout(self):
        header = ttk.Frame(self.root, padding=(12, 8))
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="HỆ THỐNG QUẢN LÝ ĐẶT PHÒNG KHÁCH SẠN (MI3060)",
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Button(
            header,
            text="Khởi tạo lại dữ liệu mẫu",
            command=self._on_reset_sample,
        ).pack(side=tk.RIGHT, padx=4)
        ttk.Button(
            header,
            text="Làm mới toàn bộ",
            command=self.refresh_all,
        ).pack(side=tk.RIGHT, padx=4)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self.tab_matrix = ttk.Frame(self.notebook, padding=10)
        self.tab_bookings = ttk.Frame(self.notebook, padding=10)
        self.tab_search = ttk.Frame(self.notebook, padding=10)
        self.tab_customers = ttk.Frame(self.notebook, padding=10)
        self.tab_queues = ttk.Frame(self.notebook, padding=10)
        self.tab_payments = ttk.Frame(self.notebook, padding=10)
        self.tab_reports = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.tab_matrix, text="1. Sơ đồ phòng (Matrix 2D)")
        self.notebook.add(self.tab_bookings, text="2. Đặt/Hủy & Hoàn tác (BST + Stack)")
        self.notebook.add(self.tab_search, text="3. Lọc & Sắp xếp (Sort + Binary Search)")
        self.notebook.add(self.tab_customers, text="4. Khách hàng & Lịch sử (Hash + LinkedList)")
        self.notebook.add(self.tab_queues, text="5. Hàng chờ VIP & Dịch vụ (Max-Heap + Queue)")
        self.notebook.add(self.tab_payments, text="6. Quản lý thanh toán (Hash + LinkedList)")
        self.notebook.add(self.tab_reports, text="7. Thống kê & Báo cáo")

        self._build_matrix_tab()
        self._build_bookings_tab()
        self._build_search_tab()
        self._build_customers_tab()
        self._build_queues_tab()
        self._build_payments_tab()
        self._build_reports_tab()

    # -------------------- Tab 1: Sơ đồ ma trận phòng -------------------- #
    def _build_matrix_tab(self):
        top = ttk.Frame(self.tab_matrix)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top, text="Ngày kiểm tra (dd/mm/yyyy):").pack(side=tk.LEFT)
        self.var_map_date = tk.StringVar(value=format_date(date.today()))
        ttk.Entry(top, textvariable=self.var_map_date, width=14).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Xem sơ đồ", command=self.refresh_matrix_tab).pack(side=tk.LEFT)
        ttk.Label(
            top,
            text="   Chú thích:  [Xanh = TRỐNG]   [Đỏ = ĐÃ ĐẶT]   [Xám = BẢO TRÌ]",
            font=("Segoe UI", 9, "italic"),
        ).pack(side=tk.LEFT, padx=12)

        body = ttk.Frame(self.tab_matrix)
        body.pack(fill=tk.BOTH, expand=True)

        self.grid_frame = ttk.LabelFrame(body, text="Ma trận Tầng × Phòng (Truy cập O(1))", padding=8)
        self.grid_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = ttk.LabelFrame(body, text="Chi tiết phòng & Lịch BST", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.lbl_room_detail = ttk.Label(right, text="Chọn một ô phòng...", width=38, justify=tk.LEFT)
        self.lbl_room_detail.pack(anchor=tk.W, pady=(0, 8))
        ttk.Button(
            right,
            text="Đổi trạng thái Bảo trì phòng đang chọn",
            command=self._on_toggle_maintenance,
        ).pack(fill=tk.X, pady=4)

        ttk.Label(right, text="Lịch đặt trên cây BST của phòng:").pack(anchor=tk.W, pady=(10, 4))
        self.tree_room_schedule = ttk.Treeview(
            right,
            columns=("id", "checkin", "checkout", "status"),
            show="headings",
            height=10,
        )
        for col, text, w in (
            ("id", "Mã đơn", 75),
            ("checkin", "Nhận phòng", 85),
            ("checkout", "Trả phòng", 85),
            ("status", "Trạng thái", 90),
        ):
            self.tree_room_schedule.heading(col, text=text)
            self.tree_room_schedule.column(col, width=w, anchor=tk.CENTER)
        self.tree_room_schedule.pack(fill=tk.BOTH, expand=True)

    def refresh_matrix_tab(self):
        try:
            target = parse_date(self.var_map_date.get())
        except ValueError as exc:
            messagebox.showerror("Lỗi ngày", str(exc))
            return

        for child in self.grid_frame.winfo_children():
            child.destroy()

        grid = self.manager.floor_map(target)
        for r_idx, floor_row in enumerate(reversed(grid)):
            floor_no = len(grid) - r_idx
            ttk.Label(
                self.grid_frame,
                text=f"Tầng {floor_no}",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=r_idx, column=0, padx=4, pady=4, sticky="w")
            for c_idx, cell in enumerate(floor_row):
                room = cell["room"]
                status = cell["status"]
                bg, fg = STATUS_COLORS[status]
                btn = tk.Button(
                    self.grid_frame,
                    text=f"{room.room_id}\n{room.room_type.label}\n{status.label}",
                    bg=bg,
                    fg=fg,
                     relief=tk.GROOVE,
                    width=9,
                    height=3,
                    font=("Segoe UI", 8, "bold"),
                    command=lambda rid=room.room_id: self._select_room(rid),
                )
                btn.grid(row=r_idx, column=c_idx + 1, padx=3, pady=3, sticky="nsew")

        self._select_room(self.selected_room_id)

    def _select_room(self, room_id):
        self.selected_room_id = room_id
        room = self.manager.get_room(room_id)
        try:
            target = parse_date(self.var_map_date.get())
        except ValueError:
            target = date.today()
        status = self.manager.bookings.room_status_on(room_id, target)
        info = (
            f"Mã phòng   : {room.room_id} (Tầng {room.floor}, Phòng {room.room_number:02d})\n"
            f"Chỉ số 2D  : Matrix2D[{room.floor - 1}][{room.room_number - 1}]\n"
            f"Loại phòng : {room.room_type.label}\n"
            f"Giá / đêm  : {format_vnd(room.price_per_night)}\n"
            f"Trạng thái : {status.label}\n"
            f"Tiện nghi  : {room.description}"
        )
        self.lbl_room_detail.config(text=info)

        self.tree_room_schedule.delete(*self.tree_room_schedule.get_children())
        for b in self.manager.bookings.bookings_for_room(room_id):
            self.tree_room_schedule.insert(
                "",
                tk.END,
                values=(b.booking_id, format_date(b.check_in), format_date(b.check_out), b.status.label),
            )

    def _on_toggle_maintenance(self):
        try:
            room = self.manager.get_room(self.selected_room_id)
            self.manager.set_room_maintenance(room.room_id, not room.under_maintenance)
            self.refresh_all()
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    # ------------- Tab 2: Đặt phòng, Hủy & Hoàn tác (BST + Stack) ------- #
    def _build_bookings_tab(self):
        form = ttk.LabelFrame(self.tab_bookings, text="Tạo đơn đặt phòng mới", padding=8)
        form.pack(fill=tk.X, pady=(0, 8))

        today = date.today()
        self.var_bk_cust = tk.StringVar(value="KH001")
        self.var_bk_room = tk.StringVar(value="P103")
        self.var_bk_in = tk.StringVar(value=format_date(today + timedelta(days=1)))
        self.var_bk_out = tk.StringVar(value=format_date(today + timedelta(days=3)))

        ttk.Label(form, text="Mã KH/CCCD/SĐT:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.var_bk_cust, width=15).grid(row=0, column=1, padx=4, pady=4)
        ttk.Label(form, text="Mã phòng:").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.var_bk_room, width=10).grid(row=0, column=3, padx=4, pady=4)
        ttk.Label(form, text="Nhận phòng:").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.var_bk_in, width=12).grid(row=0, column=5, padx=4, pady=4)
        ttk.Label(form, text="Trả phòng:").grid(row=0, column=6, padx=4, pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.var_bk_out, width=12).grid(row=0, column=7, padx=4, pady=4)
        ttk.Button(form, text="Đặt phòng (BST O(log n))", command=self._on_create_booking).grid(
            row=0, column=8, padx=8, pady=4
        )

        actions = ttk.Frame(self.tab_bookings)
        actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(actions, text="Nhận phòng (Check-in)", command=self._on_checkin).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Trả phòng (Check-out)", command=self._on_checkout).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Hủy đơn đã chọn (Push Stack)", command=self._on_cancel_booking).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(actions, text="Hoàn tác lệnh hủy gần nhất (Pop Stack O(1))", command=self._on_undo_cancel).pack(
            side=tk.LEFT, padx=12
        )
        self.lbl_undo_top = ttk.Label(actions, text="", font=("Segoe UI", 9, "bold"))
        self.lbl_undo_top.pack(side=tk.RIGHT, padx=6)

        cols = ("id", "cust", "name", "room", "in", "out", "nights", "total", "status")
        self.tree_bookings = ttk.Treeview(self.tab_bookings, columns=cols, show="headings", height=16)
        headings = [
            ("id", "Mã đơn", 85),
            ("cust", "Mã KH", 70),
            ("name", "Tên khách hàng", 160),
            ("room", "Phòng", 65),
            ("in", "Nhận phòng", 95),
            ("out", "Trả phòng", 95),
            ("nights", "Số đêm", 65),
            ("total", "Tổng tiền", 115),
            ("status", "Trạng thái", 110),
        ]
        for col, text, w in headings:
            self.tree_bookings.heading(col, text=text)
            self.tree_bookings.column(col, width=w, anchor=tk.CENTER)
        self.tree_bookings.pack(fill=tk.BOTH, expand=True)

    def refresh_bookings_tab(self):
        self.tree_bookings.delete(*self.tree_bookings.get_children())
        bookings = merge_sort(self.manager.bookings.all_bookings(), key=lambda b: b.booking_id)
        for b in bookings:
            try:
                cname = self.manager.customers.get_customer(b.customer_id).full_name
            except Exception:
                cname = "-"
            self.tree_bookings.insert(
                "",
                tk.END,
                iid=b.booking_id,
                values=(
                    b.booking_id,
                    b.customer_id,
                    cname,
                    b.room_id,
                    format_date(b.check_in),
                    format_date(b.check_out),
                    b.num_nights,
                    format_vnd(b.total_price),
                    b.status.label,
                ),
            )
        top_undo = self.manager.undo.peek_last_cancellation()
        if top_undo is None:
            self.lbl_undo_top.config(text="Đỉnh Undo Stack: (Trống)")
        else:
            self.lbl_undo_top.config(
                text=f"Đỉnh Undo Stack: {top_undo.booking_id} (Phòng {top_undo.room_id}) — Sẵn sàng hoàn tác"
            )

    def _selected_booking_id(self):
        sel = self.tree_bookings.selection()
        if not sel:
            raise HotelError("Vui lòng chọn một đơn đặt phòng trong bảng")
        return sel[0]

    def _on_create_booking(self):
        try:
            cust = self.manager.lookup_customer(self.var_bk_cust.get())
            old_vip = cust.vip_level
            ci = parse_date(self.var_bk_in.get())
            co = parse_date(self.var_bk_out.get())
            booking = self.manager.book_room(cust.customer_id, self.var_bk_room.get(), ci, co)
            new_vip = self.manager.customers.get_customer(cust.customer_id).vip_level
            self.refresh_all()
            upgrade_msg = ""
            if new_vip > old_vip:
                total_paid = self.manager.customer_total_paid(cust.customer_id)
                upgrade_msg = (
                    f"\n\n★ Khách hàng {cust.full_name} đạt tích lũy {format_vnd(total_paid)} "
                    f"và được TỰ ĐỘNG NÂNG HẠNG VIP: {old_vip.label} -> {new_vip.label}!"
                )
            messagebox.showinfo(
                "Thành công",
                f"Đã tạo đơn {booking.booking_id} cho phòng {booking.room_id}{upgrade_msg}",
            )
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Không thể đặt phòng", str(exc))

    def _on_checkin(self):
        try:
            bid = self._selected_booking_id()
            self.manager.check_in(bid)
            self.refresh_all()
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_checkout(self):
        try:
            bid = self._selected_booking_id()
            self.manager.check_out(bid)
            self.refresh_all()
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_cancel_booking(self):
        try:
            bid = self._selected_booking_id()
            action, _ = self.manager.cancel_booking(bid, cancelled_by="STAFF")
            self.refresh_all()
            messagebox.showinfo(
                "Đã hủy đơn",
                f"Đã hủy đơn {action.booking_id} và đẩy vào đỉnh ngăn xếp Undo Stack.",
            )
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_undo_cancel(self):
        try:
            action, booking = self.manager.undo_last_cancellation()
            self.refresh_all()
            messagebox.showinfo(
                "Hoàn tác thành công",
                f"Đã khôi phục đơn {action.booking_id} (Phòng {booking.room_id}) về trạng thái '{booking.status.label}'.",
            )
        except HotelError as exc:
            messagebox.showerror("Không thể hoàn tác", str(exc))

    # -------- Tab 3: Lọc, Sắp xếp & Tìm kiếm nhị phân theo giá ---------- #
    def _build_search_tab(self):
        ctrl = ttk.LabelFrame(
            self.tab_search,
            text="Bộ lọc khoảng ngày (BST), Khoảng giá (Binary Search) & Sắp xếp (Merge/Quick Sort)",
            padding=8,
        )
        ctrl.pack(fill=tk.X, pady=(0, 8))

        today = date.today()
        self.var_s_in = tk.StringVar(value=format_date(today + timedelta(days=1)))
        self.var_s_out = tk.StringVar(value=format_date(today + timedelta(days=3)))
        self.var_s_type = tk.StringVar(value="ALL")
        self.var_s_min = tk.StringVar(value="0")
        self.var_s_max = tk.StringVar(value="3000000")
        self.var_s_algo = tk.StringVar(value="merge")
        self.var_s_budget = tk.StringVar(value="850000")

        ttk.Label(ctrl, text="Nhận:").grid(row=0, column=0, padx=3, pady=3)
        ttk.Entry(ctrl, textvariable=self.var_s_in, width=11).grid(row=0, column=1, padx=3, pady=3)
        ttk.Label(ctrl, text="Trả:").grid(row=0, column=2, padx=3, pady=3)
        ttk.Entry(ctrl, textvariable=self.var_s_out, width=11).grid(row=0, column=3, padx=3, pady=3)
        ttk.Label(ctrl, text="Loại:").grid(row=0, column=4, padx=3, pady=3)
        ttk.Combobox(
            ctrl,
            textvariable=self.var_s_type,
            values=("ALL", "SINGLE", "DOUBLE", "SUITE"),
            width=9,
            state="readonly",
        ).grid(row=0, column=5, padx=3, pady=3)
        ttk.Label(ctrl, text="Giá từ:").grid(row=0, column=6, padx=3, pady=3)
        ttk.Entry(ctrl, textvariable=self.var_s_min, width=9).grid(row=0, column=7, padx=3, pady=3)
        ttk.Label(ctrl, text="đến:").grid(row=0, column=8, padx=3, pady=3)
        ttk.Entry(ctrl, textvariable=self.var_s_max, width=9).grid(row=0, column=9, padx=3, pady=3)
        ttk.Combobox(
            ctrl,
            textvariable=self.var_s_algo,
            values=("merge", "quick"),
            width=7,
            state="readonly",
        ).grid(row=0, column=10, padx=3, pady=3)
        ttk.Button(ctrl, text="Tìm phòng trống", command=self._on_search_available).grid(
            row=0, column=11, padx=6, pady=3
        )

        budget_row = ttk.Frame(self.tab_search)
        budget_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(budget_row, text="Ngân sách dự kiến (VND/đêm):").pack(side=tk.LEFT)
        ttk.Entry(budget_row, textvariable=self.var_s_budget, width=12).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            budget_row,
            text="Tìm 1 phòng có giá gần ngân sách nhất (Binary Search O(log R))",
            command=self._on_suggest_budget,
        ).pack(side=tk.LEFT)

        cols = ("id", "floor", "num", "type", "price", "desc")
        self.tree_search = ttk.Treeview(self.tab_search, columns=cols, show="headings", height=16)
        for col, text, w in (
            ("id", "Mã phòng", 80),
            ("floor", "Tầng", 60),
            ("num", "Số phòng", 70),
            ("type", "Loại phòng", 90),
            ("price", "Giá / đêm", 120),
            ("desc", "Mô tả tiện nghi", 380),
        ):
            self.tree_search.heading(col, text=text)
            self.tree_search.column(col, width=w, anchor=tk.CENTER if col != "desc" else tk.W)
        self.tree_search.pack(fill=tk.BOTH, expand=True)

    def _on_search_available(self):
        try:
            ci = parse_date(self.var_s_in.get())
            co = parse_date(self.var_s_out.get())
            t_val = self.var_s_type.get()
            rtype = None if t_val == "ALL" else RoomType(t_val)
            min_p = int(self.var_s_min.get() or 0)
            max_p = int(self.var_s_max.get() or 10_000_000)
            rooms = self.manager.find_available_rooms(
                ci, co, room_type=rtype, min_price=min_p, max_price=max_p, algorithm=self.var_s_algo.get()
            )
            self._populate_search_tree(rooms)
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi tìm kiếm", str(exc))

    def _on_suggest_budget(self):
        try:
            budget = int(self.var_s_budget.get())
            t_val = self.var_s_type.get()
            rtype = None if t_val == "ALL" else RoomType(t_val)
            room = self.manager.suggest_room_by_budget(budget, room_type=rtype)
            self._populate_search_tree([room] if room else [])
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _populate_search_tree(self, rooms):
        self.tree_search.delete(*self.tree_search.get_children())
        for r in rooms:
            self.tree_search.insert(
                "",
                tk.END,
                values=(
                    r.room_id,
                    r.floor,
                    f"{r.room_number:02d}",
                    r.room_type.label,
                    format_vnd(r.price_per_night),
                    r.description,
                ),
            )

    # --------- Tab 4: Khách hàng & Lịch sử (HashTable + LinkedList) ----- #
    def _build_customers_tab(self):
        top = ttk.LabelFrame(self.tab_customers, text="Đăng ký & Tra cứu Bảng băm O(1)", padding=8)
        top.pack(fill=tk.X, pady=(0, 8))

        self.var_c_name = tk.StringVar()
        self.var_c_cccd = tk.StringVar()
        self.var_c_phone = tk.StringVar()
        self.var_c_vip = tk.StringVar(value="0")
        self.var_c_lookup = tk.StringVar()

        ttk.Label(top, text="Họ tên:").grid(row=0, column=0, padx=3, pady=3)
        ttk.Entry(top, textvariable=self.var_c_name, width=18).grid(row=0, column=1, padx=3, pady=3)
        ttk.Label(top, text="CCCD:").grid(row=0, column=2, padx=3, pady=3)
        ttk.Entry(top, textvariable=self.var_c_cccd, width=14).grid(row=0, column=3, padx=3, pady=3)
        ttk.Label(top, text="SĐT:").grid(row=0, column=4, padx=3, pady=3)
        ttk.Entry(top, textvariable=self.var_c_phone, width=13).grid(row=0, column=5, padx=3, pady=3)
        ttk.Label(top, text="VIP (0..3):").grid(row=0, column=6, padx=3, pady=3)
        ttk.Combobox(top, textvariable=self.var_c_vip, values=("0", "1", "2", "3"), width=4, state="readonly").grid(
            row=0, column=7, padx=3, pady=3
        )
        ttk.Button(top, text="Đăng ký KH", command=self._on_register_customer).grid(row=0, column=8, padx=6, pady=3)

        ttk.Label(top, text="Tra cứu O(1) (Mã/CCCD/SĐT):").grid(row=1, column=0, columnspan=2, padx=3, pady=4, sticky="w")
        ttk.Entry(top, textvariable=self.var_c_lookup, width=20).grid(row=1, column=2, columnspan=2, padx=3, pady=4, sticky="w")
        ttk.Button(top, text="Tra cứu Hash Table", command=self._on_lookup_customer).grid(row=1, column=4, padx=4, pady=4, sticky="w")
        ttk.Button(top, text="Đặt VIP KH chọn", command=self._on_update_customer_vip).grid(row=1, column=5, padx=4, pady=4, sticky="w")
        ttk.Label(
            top,
            text="Tự động lên VIP theo tổng tiền đã TT: >= 3tr Silver (-3%) | >= 8tr Gold (-5%) | >= 15tr Platinum (-10%)",
            font=("Segoe UI", 8, "italic"),
        ).grid(row=1, column=6, columnspan=3, padx=6, pady=4, sticky="w")

        panes = ttk.Frame(self.tab_customers)
        panes.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(panes, text="Danh sách khách hàng (Chọn 1 khách để xem DSLK lịch sử)", padding=6)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_customers = ttk.Treeview(
            left,
            columns=("id", "name", "cccd", "phone", "vip", "paid", "next_vip", "count"),
            show="headings",
            height=14,
        )
        for col, text, w in (
            ("id", "Mã KH", 60),
            ("name", "Họ và tên", 135),
            ("cccd", "Số CCCD", 95),
            ("phone", "Điện thoại", 90),
            ("vip", "Hạng VIP", 80),
            ("paid", "Tích lũy đã TT", 95),
            ("next_vip", "Tiến độ nâng VIP", 145),
            ("count", "Đơn", 45),
        ):
            self.tree_customers.heading(col, text=text)
            self.tree_customers.column(col, width=w, anchor=tk.CENTER)
        self.tree_customers.pack(fill=tk.BOTH, expand=True)
        self.tree_customers.bind("<<TreeviewSelect>>", self._on_customer_selected)

        right = ttk.LabelFrame(panes, text="Lịch sử lưu trú (SinglyLinkedList — Mới nhất ở đầu)", padding=6)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self.tree_history = ttk.Treeview(
            right,
            columns=("id", "room", "in", "out", "total", "status"),
            show="headings",
            height=14,
        )
        for col, text, w in (
            ("id", "Mã đơn", 80),
            ("room", "Phòng", 60),
            ("in", "Nhận phòng", 85),
            ("out", "Trả phòng", 85),
            ("total", "Tổng tiền", 100),
            ("status", "Trạng thái", 95),
        ):
            self.tree_history.heading(col, text=text)
            self.tree_history.column(col, width=w, anchor=tk.CENTER)
        self.tree_history.pack(fill=tk.BOTH, expand=True)

    def refresh_customers_tab(self):
        self.tree_customers.delete(*self.tree_customers.get_children())
        for c in merge_sort(self.manager.customers.all_customers(), key=lambda x: x.customer_id):
            prog = self.manager.customer_vip_progress(c.customer_id)
            if prog["next_vip"] is not None:
                next_txt = f"Còn {format_vnd(prog['amount_to_next_vip'])} -> {prog['next_vip'].label}"
            else:
                next_txt = "Đạt đỉnh (Platinum)"
            self.tree_customers.insert(
                "",
                tk.END,
                iid=c.customer_id,
                values=(
                    c.customer_id,
                    c.full_name,
                    c.cccd,
                    c.phone,
                    f"{c.vip_level.label} ({int(c.vip_level)})",
                    format_vnd(prog["total_paid"]),
                    next_txt,
                    len(c.history),
                ),
            )

    def _on_customer_selected(self, _event=None):
        sel = self.tree_customers.selection()
        if not sel:
            return
        cid = sel[0]
        self.tree_history.delete(*self.tree_history.get_children())
        for b in self.manager.customer_stay_history(cid):
            self.tree_history.insert(
                "",
                tk.END,
                values=(
                    b.booking_id,
                    b.room_id,
                    format_date(b.check_in),
                    format_date(b.check_out),
                    format_vnd(b.total_price),
                    b.status.label,
                ),
            )

    def _on_register_customer(self):
        try:
            cust = self.manager.register_customer(
                self.var_c_name.get(),
                self.var_c_cccd.get(),
                self.var_c_phone.get(),
                VipLevel(int(self.var_c_vip.get())),
            )
            self.refresh_all()
            messagebox.showinfo("Thành công", f"Đã đăng ký khách hàng {cust.customer_id} ({cust.full_name})")
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_lookup_customer(self):
        try:
            cust = self.manager.lookup_customer(self.var_c_lookup.get())
            self.tree_customers.selection_set(cust.customer_id)
            self.tree_customers.see(cust.customer_id)
            self._on_customer_selected()
        except HotelError as exc:
            messagebox.showerror("Không tìm thấy", str(exc))

    def _on_update_customer_vip(self):
        sel = self.tree_customers.selection()
        ident = sel[0] if sel else self.var_c_lookup.get().strip()
        if not ident:
            messagebox.showerror("Lỗi", "Vui lòng chọn một khách hàng trong bảng hoặc nhập Mã KH/CCCD/SĐT")
            return
        try:
            cust = self.manager.lookup_customer(ident)
            new_vip = VipLevel(int(self.var_c_vip.get()))
            self.manager.set_customer_vip(cust.customer_id, new_vip)
            self.refresh_all()
            messagebox.showinfo(
                "Đã cập nhật VIP",
                f"Khách hàng {cust.customer_id} ({cust.full_name}) đã được cập nhật lên hạng VIP: {new_vip.label} ({int(new_vip)})",
            )
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi", str(exc))

    # --------- Tab 5: Hàng chờ VIP & Yêu cầu dịch vụ (Max-Heap) --------- #
    def _build_queues_tab(self):
        panes = ttk.Frame(self.tab_queues)
        panes.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(panes, text="Danh sách chờ khi hết phòng (Max-Heap VIP + Queue Thường)", padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        w_btns = ttk.Frame(left)
        w_btns.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(
            w_btns,
            text="Tự động phân phòng cho DS chờ",
            command=self._on_process_waiting,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            w_btns,
            text="Lấy khách ưu tiên cao nhất (Pop)",
            command=self._on_pop_waiting,
        ).pack(side=tk.LEFT, padx=3)

        self.tree_waiting = ttk.Treeview(
            left,
            columns=("id", "cust", "vip", "type", "in", "out", "ds"),
            show="headings",
            height=15,
        )
        for col, text, w in (
            ("id", "Mã chờ", 65),
            ("cust", "Khách hàng", 130),
            ("vip", "Ưu tiên", 80),
            ("type", "Loại", 60),
            ("in", "Nhận", 80),
            ("out", "Trả", 80),
            ("ds", "Cấu trúc", 105),
        ):
            self.tree_waiting.heading(col, text=text)
            self.tree_waiting.column(col, width=w, anchor=tk.CENTER)
        self.tree_waiting.pack(fill=tk.BOTH, expand=True)

        right = ttk.LabelFrame(panes, text="Yêu cầu dịch vụ nội bộ (Max-Heap theo độ khẩn)", padding=8)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        sr_form = ttk.Frame(right)
        sr_form.pack(fill=tk.X, pady=(0, 6))
        self.var_sr_room = tk.StringVar(value="P101")
        self.var_sr_type = tk.StringVar(value="FOOD")
        self.var_sr_urg = tk.StringVar(value="2")
        self.var_sr_note = tk.StringVar(value="Phục vụ tại phòng")

        ttk.Label(sr_form, text="Phòng:").pack(side=tk.LEFT)
        ttk.Entry(sr_form, textvariable=self.var_sr_room, width=6).pack(side=tk.LEFT, padx=3)
        ttk.Combobox(
            sr_form,
            textvariable=self.var_sr_type,
            values=("CLEANING", "FOOD", "MEDICAL", "OTHER"),
            width=9,
            state="readonly",
        ).pack(side=tk.LEFT, padx=3)
        ttk.Combobox(
            sr_form,
            textvariable=self.var_sr_urg,
            values=("1", "2", "3"),
            width=3,
            state="readonly",
        ).pack(side=tk.LEFT, padx=3)
        ttk.Entry(sr_form, textvariable=self.var_sr_note, width=16).pack(side=tk.LEFT, padx=3)
        ttk.Button(sr_form, text="Gửi YC", command=self._on_submit_sr).pack(side=tk.LEFT, padx=3)
        ttk.Button(sr_form, text="Xử lý khẩn nhất", command=self._on_process_sr).pack(side=tk.LEFT, padx=3)

        self.tree_sr = ttk.Treeview(
            right,
            columns=("id", "room", "type", "urgency", "note"),
            show="headings",
            height=15,
        )
        for col, text, w in (
            ("id", "Mã YC", 65),
            ("room", "Phòng", 60),
            ("type", "Dịch vụ", 85),
            ("urgency", "Độ khẩn", 95),
            ("note", "Ghi chú", 190),
        ):
            self.tree_sr.heading(col, text=text)
            self.tree_sr.column(col, width=w, anchor=tk.CENTER if col != "note" else tk.W)
        self.tree_sr.pack(fill=tk.BOTH, expand=True)

    def refresh_queues_tab(self):
        self.tree_waiting.delete(*self.tree_waiting.get_children())
        for e in self.manager.waiting.list_waiting_ordered():
            try:
                cust = self.manager.customers.get_customer(e.customer_id)
                cname = f"{cust.customer_id} - {cust.full_name}"
                vip_txt = f"{cust.vip_level.label} ({e.priority})"
            except Exception:
                cname = e.customer_id
                vip_txt = str(e.priority)
            ds = "Max-Heap (VIP)" if e.priority > 0 else "LinkedQueue"
            self.tree_waiting.insert(
                "",
                tk.END,
                values=(
                    e.entry_id,
                    cname,
                    vip_txt,
                    e.room_type.label,
                    format_date(e.check_in),
                    format_date(e.check_out),
                    ds,
                ),
            )

        self.tree_sr.delete(*self.tree_sr.get_children())
        for req in self.manager.service_requests.pending_requests_ordered():
            self.tree_sr.insert(
                "",
                tk.END,
                values=(
                    req.request_id,
                    req.room_id,
                    req.service_type.label,
                    f"{req.urgency.label} ({int(req.urgency)})",
                    req.note,
                ),
            )

    def _on_process_waiting(self):
        fulfilled = self.manager.process_waiting_list()
        self.refresh_all()
        if not fulfilled:
            messagebox.showinfo("Danh sách chờ", "Chưa có phòng trống phù hợp với nhu cầu đang chờ.")
        else:
            msg = "\n".join(f"- {e.entry_id} ({e.customer_id}) -> Đơn {b.booking_id} (Phòng {b.room_id})" for e, b in fulfilled)
            messagebox.showinfo("Đã phân phòng", f"Đã tự động xếp phòng:\n{msg}")

    def _on_pop_waiting(self):
        try:
            entry = self.manager.pop_next_waiting()
            self.refresh_all()
            messagebox.showinfo("Pop hàng chờ", f"Đã lấy mục {entry.entry_id} (Khách {entry.customer_id}, ưu tiên {entry.priority})")
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_submit_sr(self):
        try:
            self.manager.submit_service_request(
                room_id=self.var_sr_room.get(),
                service_type=ServiceType(self.var_sr_type.get()),
                urgency=UrgencyLevel(int(self.var_sr_urg.get())),
                note=self.var_sr_note.get(),
            )
            self.refresh_queues_tab()
            self.refresh_payments_tab()
            self.refresh_reports_tab()
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi", str(exc))

    def _on_process_sr(self):
        try:
            req = self.manager.process_next_service_request()
            self.refresh_queues_tab()
            self.refresh_payments_tab()
            self.refresh_reports_tab()
            messagebox.showinfo(
                "Đã xử lý dịch vụ",
                f"Đã xử lý yêu cầu {req.request_id} tại phòng {req.room_id} ({req.service_type.label} - {req.urgency.label})",
            )
        except HotelError as exc:
            messagebox.showerror("Lỗi", str(exc))

    # -------- Tab 6: Quản lý thanh toán (HashTable + SinglyLinkedList) --- #
    def _build_payments_tab(self):
        top = ttk.Frame(self.tab_payments)
        top.pack(fill=tk.X, pady=(0, 8))

        left_ctrl = ttk.LabelFrame(
            top,
            text="1. Tính tổng chi phí & Xử lý thanh toán",
            padding=8,
        )
        left_ctrl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.var_pay_booking = tk.StringVar(value="BK00003")
        self.var_pay_extra = tk.StringVar(value="0")
        self.var_pay_method = tk.StringVar(value="BANK_TRANSFER")
        self.var_pay_note = tk.StringVar(value="Thanh toán hóa đơn lưu trú")
        self.var_pay_auto_checkout = tk.BooleanVar(value=False)
        self.var_pay_lookup = tk.StringVar()

        ttk.Label(left_ctrl, text="Mã đơn đặt phòng:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        self.cmb_pay_booking = ttk.Combobox(left_ctrl, textvariable=self.var_pay_booking, width=13)
        self.cmb_pay_booking.grid(row=0, column=1, padx=4, pady=4, sticky="w")
        self.cmb_pay_booking.bind("<<ComboboxSelected>>", lambda _e: self._on_calculate_bill())

        ttk.Label(left_ctrl, text="Phụ phí (VND):").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        ttk.Entry(left_ctrl, textvariable=self.var_pay_extra, width=11).grid(row=0, column=3, padx=4, pady=4, sticky="w")

        ttk.Label(left_ctrl, text="Phương thức:").grid(row=1, column=0, padx=4, pady=4, sticky="w")
        ttk.Combobox(
            left_ctrl,
            textvariable=self.var_pay_method,
            values=("CASH", "BANK_TRANSFER", "CARD", "E_WALLET"),
            width=15,
            state="readonly",
        ).grid(row=1, column=1, padx=4, pady=4, sticky="w")

        ttk.Label(left_ctrl, text="Ghi chú:").grid(row=1, column=2, padx=4, pady=4, sticky="w")
        ttk.Entry(left_ctrl, textvariable=self.var_pay_note, width=24).grid(row=1, column=3, padx=4, pady=4, sticky="w")

        btn_row = ttk.Frame(left_ctrl)
        btn_row.grid(row=2, column=0, columnspan=4, pady=(6, 2), sticky="w")
        ttk.Button(
            btn_row,
            text="Tính tổng chi phí (Xem hóa đơn)",
            command=self._on_calculate_bill,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            btn_row,
            text="Xử lý thanh toán & Lưu giao dịch",
            command=self._on_process_payment,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            btn_row,
            text="Hoàn tiền (Refund) GD đã chọn",
            command=self._on_refund_payment,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Checkbutton(
            btn_row,
            text="Tự động Check-out",
            variable=self.var_pay_auto_checkout,
        ).pack(side=tk.LEFT, padx=6)

        search_row = ttk.Frame(left_ctrl)
        search_row.grid(row=3, column=0, columnspan=4, pady=(6, 2), sticky="w")
        ttk.Label(search_row, text="Tra cứu O(1) (Mã GD/Đơn/KH/SĐT/Phòng):").pack(side=tk.LEFT, padx=2)
        ttk.Entry(search_row, textvariable=self.var_pay_lookup, width=18).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            search_row,
            text="Tra cứu thanh toán",
            command=self._on_lookup_payments,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            search_row,
            text="Hiện tất cả GD",
            command=self.refresh_payments_tab,
        ).pack(side=tk.LEFT, padx=3)

        right_bill = ttk.LabelFrame(
            top,
            text="Bảng kê chi tiết tổng chi phí (Hóa đơn)",
            padding=8,
        )
        right_bill.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self.txt_bill_detail = tk.Text(right_bill, font=("Consolas", 9), height=10, width=58)
        self.txt_bill_detail.pack(fill=tk.BOTH, expand=True)

        bottom = ttk.LabelFrame(
            self.tab_payments,
            text="Danh sách giao dịch thanh toán đã lưu trữ (HashTable + SinglyLinkedList)",
            padding=6,
        )
        bottom.pack(fill=tk.BOTH, expand=True)
        cols = (
            "pid",
            "bid",
            "cust",
            "room",
            "room_cost",
            "srv_cost",
            "discount",
            "total",
            "method",
            "date",
            "status",
            "note",
        )
        self.tree_payments = ttk.Treeview(bottom, columns=cols, show="headings", height=12)
        for col, text, w in (
            ("pid", "Mã GD", 75),
            ("bid", "Mã đơn", 75),
            ("cust", "Khách hàng", 145),
            ("room", "Phòng", 55),
            ("room_cost", "Tiền phòng", 95),
            ("srv_cost", "Phí DV+Phụ phí", 95),
            ("discount", "Giảm VIP", 85),
            ("total", "Tổng thanh toán", 105),
            ("method", "Phương thức", 100),
            ("date", "Ngày TT", 80),
            ("status", "Trạng thái", 95),
            ("note", "Ghi chú", 170),
        ):
            self.tree_payments.heading(col, text=text)
            self.tree_payments.column(col, width=w, anchor=tk.CENTER if col != "note" else tk.W)
        self.tree_payments.pack(fill=tk.BOTH, expand=True)
        self.tree_payments.bind("<<TreeviewSelect>>", self._on_payment_selected)

    def _populate_payments_tree(self, payments):
        self.tree_payments.delete(*self.tree_payments.get_children())
        for tx in payments:
            try:
                cust = self.manager.customers.get_customer(tx.customer_id)
                cname = f"{cust.customer_id} - {cust.full_name}"
            except Exception:
                cname = tx.customer_id
            self.tree_payments.insert(
                "",
                tk.END,
                iid=tx.payment_id,
                values=(
                    tx.payment_id,
                    tx.booking_id,
                    cname,
                    tx.room_id,
                    format_vnd(tx.room_cost),
                    format_vnd(tx.service_cost + tx.extra_fee),
                    format_vnd(tx.discount_amount),
                    format_vnd(tx.total_amount),
                    tx.payment_method.label,
                    format_date(tx.paid_at),
                    tx.status.label,
                    tx.note,
                ),
            )

    def refresh_payments_tab(self):
        all_bks = merge_sort(self.manager.bookings.all_bookings(), key=lambda b: b.booking_id)
        self.cmb_pay_booking["values"] = [b.booking_id for b in all_bks]
        self._populate_payments_tree(self.manager.all_payments())
        try:
            bid = self.var_pay_booking.get().strip()
            if bid:
                bill = self.manager.calculate_booking_cost(bid, extra_fee=int(self.var_pay_extra.get() or 0))
                self.txt_bill_detail.delete("1.0", tk.END)
                self.txt_bill_detail.insert(tk.END, format_bill_detail(bill))
        except Exception:
            pass

    def _on_payment_selected(self, _event=None):
        sel = self.tree_payments.selection()
        if not sel:
            return
        try:
            tx = self.manager.get_payment(sel[0])
            self.var_pay_booking.set(tx.booking_id)
            self.var_pay_extra.set(str(tx.extra_fee))
            self._on_calculate_bill()
        except Exception:
            pass

    def _on_calculate_bill(self):
        try:
            bid = self.var_pay_booking.get().strip()
            extra = int(self.var_pay_extra.get() or 0)
            bill = self.manager.calculate_booking_cost(bid, extra_fee=extra)
            self.txt_bill_detail.delete("1.0", tk.END)
            self.txt_bill_detail.insert(tk.END, format_bill_detail(bill))
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Lỗi tính chi phí", str(exc))

    def _on_process_payment(self):
        try:
            bid = self.var_pay_booking.get().strip()
            extra = int(self.var_pay_extra.get() or 0)
            method = PaymentMethod(self.var_pay_method.get())
            note = self.var_pay_note.get()
            booking_before = self.manager.bookings.get_booking(bid)
            cust_before = self.manager.customers.get_customer(booking_before.customer_id)
            old_vip = cust_before.vip_level
            tx = self.manager.process_payment(
                booking_id=bid,
                payment_method=method,
                extra_fee=extra,
                note=note,
                auto_check_out=self.var_pay_auto_checkout.get(),
            )
            new_vip = self.manager.customers.get_customer(tx.customer_id).vip_level
            total_paid = self.manager.customer_total_paid(tx.customer_id)
            self.refresh_all()
            upgrade_msg = ""
            if new_vip > old_vip:
                upgrade_msg = (
                    f"\n\n★ Chúc mừng! Khách hàng {cust_before.full_name} đạt tích lũy "
                    f"{format_vnd(total_paid)} và được TỰ ĐỘNG NÂNG HẠNG VIP: {old_vip.label} -> {new_vip.label}!"
                )
            messagebox.showinfo(
                "Thanh toán thành công",
                f"Đã xử lý và lưu giao dịch {tx.payment_id} cho đơn {tx.booking_id}\n"
                f"Tổng thanh toán: {format_vnd(tx.total_amount)} ({tx.payment_method.label})"
                f"{upgrade_msg}",
            )
        except (HotelError, ValueError) as exc:
            messagebox.showerror("Không thể thanh toán", str(exc))

    def _on_refund_payment(self):
        sel = self.tree_payments.selection()
        target = sel[0] if sel else self.var_pay_booking.get().strip()
        if not target:
            messagebox.showerror("Lỗi", "Vui lòng chọn một giao dịch trong bảng để hoàn tiền")
            return
        try:
            tx = self.manager.refund_payment(target, reason="Hoàn tiền qua GUI")
            self.refresh_all()
            messagebox.showinfo("Đã hoàn tiền", f"Giao dịch {tx.payment_id} đã chuyển sang trạng thái '{tx.status.label}'.")
        except HotelError as exc:
            messagebox.showerror("Lỗi hoàn tiền", str(exc))

    def _on_lookup_payments(self):
        try:
            q = self.var_pay_lookup.get().strip()
            found = self.manager.lookup_payments(q)
            self._populate_payments_tree(found)
        except HotelError as exc:
            messagebox.showerror("Không tìm thấy", str(exc))

    # -------------------- Tab 7: Thống kê & Báo cáo --------------------- #
    def _build_reports_tab(self):
        self.txt_report = tk.Text(self.tab_reports, font=("Consolas", 10), height=28)
        self.txt_report.pack(fill=tk.BOTH, expand=True)

    def refresh_reports_tab(self):
        rev = self.manager.reports.revenue_summary()
        occ = self.manager.reports.occupancy_on(date.today())
        top = self.manager.reports.top_customers(limit=10)
        pay_sum = self.manager.payments.payment_summary()

        lines = [
            "=== BÁO CÁO THỐNG KÊ DOANH THU, THANH TOÁN & TỶ LỆ LẤP ĐẦY PHÒNG ===",
            "",
            f"- Tổng doanh thu (các đơn hiệu lực)       : {format_vnd(rev['total_revenue'])}",
            f"- Doanh thu đã thực hiện (Đang ở/Đã trả)  : {format_vnd(rev['realized_revenue'])}",
            f"- Doanh thu đặt trước (Đã xác nhận)       : {format_vnd(rev['confirmed_revenue'])}",
            f"- Tổng tiền đã thu qua giao dịch TT       : {format_vnd(pay_sum['total_collected'])} ({pay_sum['paid_transactions']} GD)",
            f"- Tổng chiết khấu VIP đã giảm             : {format_vnd(pay_sum['total_discount'])}",
            f"- Số đơn chưa thanh toán / Công nợ dự kiến: {pay_sum['unpaid_bookings_count']} đơn ({format_vnd(pay_sum['unpaid_estimated_total'])})",
            f"- Số đơn hiệu lực / Số đơn đã hủy         : {rev['active_bookings']} / {rev['cancelled_bookings']}",
            f"- Tỷ lệ lấp đầy hôm nay ({format_date(occ['date'])})   : {occ['booked_rooms']}/{occ['total_rooms']} phòng ({occ['occupancy_rate']}%)",
            f"- Số phòng trống / bảo trì                : {occ['empty_rooms']} trống / {occ['maintenance_rooms']} bảo trì",
            "",
            "--- Doanh thu theo loại phòng ---",
        ]
        for rtype in RoomType:
            lines.append(
                f"  + Phòng {rtype.label:<6}: {rev['nights_by_type'][rtype]:>3} đêm  |  {format_vnd(rev['revenue_by_type'][rtype])}"
            )
        lines.append("")
        lines.append("--- Top khách hàng chi tiêu cao nhất (Sắp xếp bằng Merge Sort) ---")
        for idx, item in enumerate(top, start=1):
            c = item["customer"]
            lines.append(
                f"  #{idx:02d}  {c.customer_id} - {c.full_name:<20} | VIP: {c.vip_level.label:<8} | "
                f"{item['booking_count']} đơn ({item['total_nights']} đêm) | "
                f"Đặt: {format_vnd(item['total_spent'])} | Đã TT: {format_vnd(item.get('total_paid', 0))}"
            )

        self.txt_report.delete("1.0", tk.END)
        self.txt_report.insert(tk.END, "\n".join(lines))

    def _on_reset_sample(self):
        if messagebox.askyesno("Xác nhận", "Khởi tạo lại toàn bộ dữ liệu mẫu mặc định?"):
            self.manager.reset_with_sample_data()
            self.refresh_all()

    def refresh_all(self):
        self.refresh_matrix_tab()
        self.refresh_bookings_tab()
        self._on_search_available()
        self.refresh_customers_tab()
        self.refresh_queues_tab()
        self.refresh_payments_tab()
        self.refresh_reports_tab()
