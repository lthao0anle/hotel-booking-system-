# Hệ thống Quản lý Đặt phòng Khách sạn (CTDL & GT — MI3060)

Dự án mẫu môn **Cấu trúc Dữ liệu và Giải thuật (MI3060)** — Đề tài **6. Đặt phòng khách sạn**.
Toàn bộ các cấu trúc dữ liệu và giải thuật cốt lõi đều được **tự cài đặt từ đầu (không dùng thư viện sẵn có)**, tách biệt rõ ràng theo kiến trúc 3 tầng (**Giao diện** $\rightarrow$ **Điều phối Nghiệp vụ** $\rightarrow$ **Mô hình & Cấu trúc Dữ liệu**), mỗi chức năng và mỗi CTDL nằm trong một file riêng biệt.

---

## 1. Cấu trúc thư mục mã nguồn

```text
hotel_booking/
├── main.py                              # Điểm vào chương trình (--gui, --demo, --benchmark, --reset)
├── README.md                            # Tài liệu hướng dẫn và bảng ánh xạ CTDL
├── data/
│   └── hotel_data.json                  # Dữ liệu lưu trữ bền vững (JSON Persistence)
├── hotel/
│   ├── config.py                        # Cấu hình mặc định (8 tầng × 10 phòng, bảng giá...)
│   ├── benchmark.py                     # Đo hiệu năng thực nghiệm (>= 2.000 bản ghi, Chương 4)
│   ├── models/                          # [Tầng 1a] Các thực thể dữ liệu cốt lõi
│   │   ├── enums.py                     # RoomType, RoomStatus, BookingStatus, VipLevel, UrgencyLevel...
│   │   ├── date_utils.py                # Xử lý và định dạng ngày tháng (dd/mm/yyyy <-> ISO)
│   │   ├── room.py                      # Thực thể Room & ánh xạ mã phòng P205 <-> (tầng 2, phòng 05)
│   │   ├── customer.py                  # Thực thể Customer (gắn SinglyLinkedList lịch sử)
│   │   ├── booking.py                   # Thực thể Booking (khoảng nửa mở [check_in, check_out))
│   │   ├── waiting_entry.py             # Thực thể WaitingEntry (khóa ưu tiên VIP & thứ tự đến)
│   │   ├── service_request.py           # Thực thể ServiceRequest (khóa độ khẩn & thứ tự gửi)
│   │   ├── cancel_action.py             # Thực thể CancelAction (snapshot cho Undo Stack)
│   │   └── payment.py                   # Thực thể PaymentTransaction (giao dịch thanh toán)
│   ├── data_structures/                 # [Tầng 1b] CTDL nền tảng tự cài đặt 100%
│   │   ├── matrix_2d.py                 # Mảng 2 chiều (Matrix2D) — Quản lý phòng theo tầng O(1)
│   │   ├── avl_tree.py                  # Cây nhị phân tìm kiếm tự cân bằng (AVL / BST) — O(log n)
│   │   ├── interval_schedule.py         # Lịch đặt phòng trên BST — Kiểm tra xung đột ngày O(log n)
│   │   ├── linked_list.py               # Danh sách liên kết đơn (SinglyLinkedList) — Chèn đầu O(1)
│   │   ├── hash_table.py                # Bảng băm đa thức + Chaining (HashTable) — Tra cứu O(1) avg
│   │   ├── linked_queue.py              # Hàng đợi FIFO (LinkedQueue) — Hàng chờ khách thường O(1)
│   │   ├── max_heap.py                  # Hàng đợi ưu tiên (MaxHeap) — Hàng chờ VIP & Dịch vụ O(log k)
│   │   └── stack.py                     # Ngăn xếp LIFO (Stack) — Hủy phòng & Hoàn tác O(1)
│   ├── algorithms/                      # [Tầng 1c] Giải thuật sắp xếp & tìm kiếm tự cài đặt
│   │   ├── merge_sort.py                # Merge Sort (ổn định) — O(n log n)
│   │   ├── quick_sort.py                # Quick Sort phân hoạch 3 phần (3-way) — O(n log n)
│   │   ├── binary_search.py             # Binary Search, lower/upper_bound, range_search, find_closest — O(log n)
│   │   └── naive.py                     # Các giải thuật ngây thơ dùng đối chiếu hiệu năng ở Chương 4
│   ├── services/                        # [Tầng 2] Điều phối nghiệp vụ (mỗi chức năng 1 file riêng)
│   │   ├── room_service.py              # Chức năng 1 & 3: Sơ đồ phòng 2D, lọc/sắp xếp & tìm theo giá
│   │   ├── booking_service.py           # Chức năng 2: Tìm phòng trống, đặt/nhận/trả phòng trên BST
│   │   ├── waiting_service.py           # Chức năng 4: Hàng chờ khi hết phòng (Queue + Max-Heap VIP)
│   │   ├── customer_service.py          # Chức năng 5: Tra cứu khách (HashTable) & lịch sử (LinkedList)
│   │   ├── undo_service.py              # Chức năng 6: Hủy đặt phòng & hoàn tác (Stack)
│   │   ├── service_request_service.py   # Chức năng 7: Yêu cầu dịch vụ nội bộ (Max-Heap)
│   │   ├── payment_service.py           # Chức năng 8: Quản lý thanh toán (HashTable + SinglyLinkedList)
│   │   ├── report_service.py            # Mở rộng: Thống kê doanh thu, tỷ lệ lấp đầy, Top khách hàng
│   │   ├── storage_service.py           # Đọc/ghi trạng thái toàn hệ thống ra file JSON
│   │   ├── seed_service.py              # Khởi tạo dữ liệu mẫu tiếng Việt
│   │   └── hotel_manager.py             # Lớp Facade kết nối toàn bộ các service
│   └── ui/                              # [Tầng 3] Giao diện người dùng
│       ├── formatter.py                 # Vẽ bảng ASCII và sơ đồ ma trận tầng trực quan
│       ├── cli.py                       # Giao diện dòng lệnh (CLI Menu tương tác)
│       └── gui.py                       # Giao diện đồ họa Tkinter (GUI 7 tab trực quan)
└── tests/                               # Bộ kiểm thử đơn vị & kiểm thử luồng nghiệp vụ
    ├── test_data_structures.py
    ├── test_algorithms.py
    └── test_services_and_flows.py
```

---

## 2. Bảng ánh xạ Chức năng — CTDL & Độ phức tạp mục tiêu

| # | Chức năng nghiệp vụ | File nghiệp vụ | CTDL / Giải thuật tự cài đặt | Độ phức tạp đạt được |
|---|---|---|---|---|
| 1 | Danh sách phòng theo tầng | `services/room_service.py` | `Matrix2D` (`data_structures/matrix_2d.py`) | Truy cập theo `(tầng, phòng)` hoặc mã `P205`: **O(1)** |
| 2 | Tìm phòng trống & Kiểm tra xung đột ngày | `services/booking_service.py` | `AVLTree` + `IntervalSchedule` (`avl_tree.py`, `interval_schedule.py`) | Kiểm tra xung đột / Chèn / Xóa lịch đặt: **O(log n)** |
| 3 | Lọc & Sắp xếp phòng theo loại, giá, ngân sách | `services/room_service.py` | `merge_sort`, `quick_sort`, `binary_search`, `find_closest` | Sắp xếp: **O(R log R)**; Tìm theo ngưỡng/budget: **O(log R)** |
| 4 | Danh sách chờ khi hết phòng (Thường & VIP) | `services/waiting_service.py` | `LinkedQueue` (thường) + `MaxHeap` (VIP) | Thêm/Lấy VIP: **O(log k)**, Xem đầu hàng: **O(1)**; Thường: **O(1)** |
| 5 | Tra cứu khách hàng & Lịch sử lưu trú | `services/customer_service.py` | `HashTable` (chaining) + `SinglyLinkedList` | Tra cứu Mã/CCCD/SĐT: **O(1)** TB; Chèn đầu lịch sử: **O(1)** |
| 6 | Hủy đặt phòng & Hoàn tác (Undo) | `services/undo_service.py` | `Stack` (`data_structures/stack.py`) | Push / Pop / Peek thao tác hủy: **O(1)** (+ cập nhật BST **O(log n)**) |
| 7 | Yêu cầu dịch vụ nội bộ (Dọn phòng, Đồ ăn, Y tế) | `services/service_request_service.py` | `MaxHeap` (`data_structures/max_heap.py`) | Thêm yêu cầu / Lấy yêu cầu khẩn nhất: **O(log s)**, Peek: **O(1)** |
| 8 | Quản lý thanh toán (Tính phí, Xử lý, Lưu trữ & Tra cứu) | `services/payment_service.py` | `HashTable` (chaining) + `SinglyLinkedList` | Lưu giao dịch: **O(1)**; Tra cứu theo Mã GD / Mã đơn / KH: **O(1)** TB |

### Chính sách tự động xét & nâng hạng VIP theo tích lũy đã thanh toán

| Hạng thành viên | Mã mức (`VipLevel`) | Mốc tổng tiền đã thanh toán tích lũy | Chiết khấu hóa đơn | Quyền lợi hàng chờ |
|---|---|---|---|---|
| **Thường (Normal)** | `0` | `< 3.000.000 đ` | `0%` | Hàng đợi `LinkedQueue` (FIFO) |
| **VIP Bạc (Silver)** | `1` | `>= 3.000.000 đ` | `3%` | Hàng đợi ưu tiên `MaxHeap` (Mức `1`) |
| **VIP Vàng (Gold)** | `2` | `>= 8.000.000 đ` | `5%` | Hàng đợi ưu tiên `MaxHeap` (Mức `2`) |
| **VIP Platinum** | `3` | `>= 15.000.000 đ` | `10%` | Hàng đợi ưu tiên `MaxHeap` (Mức `3` — cao nhất) |

---

## 3. Hướng dẫn chạy chương trình

Yêu cầu: **Python 3.10+** (không cần cài thêm bất kỳ thư viện bên ngoài nào).

```bash
# 1. Chạy giao diện dòng lệnh (CLI Menu tương tác)
python main.py

# 2. Chạy giao diện đồ họa Tkinter (GUI)
python main.py --gui

# 3. Chạy kịch bản minh họa tự động 8 chức năng cốt lõi
python main.py --demo

# 4. Chạy đo hiệu năng thực nghiệm trên tập dữ liệu >= 2.000 bản ghi (Chương 4)
python main.py --benchmark

# 5. Chạy toàn bộ bộ kiểm thử tự động (Unit Tests & Functional Tests)
python -m unittest discover -s tests -v
```
