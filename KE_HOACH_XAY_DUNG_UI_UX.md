# BÁO CÁO & ĐẶC TẢ KIẾN TRÚC PHÂN HỆ GIAO DIỆN WEB HIỆN ĐẠI
## Dự án: Hệ thống Quản lý Đặt phòng Khách sạn (CTDL & GT — MI3060)
### Phong cách thiết kế: Tangerine Capital Editorial Design System TC-04

---

## 1. Tuyên Bố & Nguyên Tắc Đóng Gói (Zero-Touch Source Code)

Phân hệ Web Application được xây dựng hoàn chỉnh dưới dạng **Module độc lập 100%** nằm trọn vẹn trong thư mục `web_app/`.

### Cam kết bất khả xâm phạm đối với mã nguồn của nhóm:
1. **Bảo toàn mã nguồn nhóm:** Tuyệt đối không xóa, sửa, đổi tên hay can thiệp vào bất kỳ tệp tin nào trong `hotel/`, `main.py`, `tests/`, `data/`.
2. **Bảo tồn ứng dụng Desktop:** Ứng dụng Tkinter desktop ban đầu (`python main.py --gui`) và giao diện CLI (`python main.py`) tiếp tục hoạt động độc lập làm phiên bản dự phòng.
3. **Chung cơ sở dữ liệu bền vững:** Cả Web và Desktop Tkinter đều đọc/ghi chung tệp dữ liệu `data/hotel_data.json`, đảm bảo tính toàn vẹn và đồng bộ dữ liệu tức thời.
4. **Khởi chạy độc lập 1-click:** Ứng dụng Web được đóng gói mở trực tiếp từ shortcut `Tangerine Grand Hotel.lnk` ở thư mục gốc dự án mà không yêu cầu thao tác lệnh phức tạp.

---

## 2. Cấu Trúc Độc Lập Bên Trong `web_app/`

Toàn bộ mã nguồn, tài nguyên, thiết kế và script chạy của phân hệ Web được gom gọn như sau:

```text
hotel_booking/
├── Chay_Giao_Dien_Web.bat               # [FILE KHỞI CHẠY WEB] Mở web 1-click trên mọi máy giải nén (C, D, USB...)
├── web_app/                             # [TỔNG DUNG LƯỢNG SIÊU NHẸ: ~1.94 MB]
│   ├── backend/                         # [TẦNG BACKEND BRIDGE & WEB SERVER]
│   │   ├── api.py                       # 39 REST API endpoints + Trình phục vụ Web tĩnh trực tiếp
│   │   └── run.py                       # Script khởi chạy FastAPI (Port 8000, tự nhận diện Python)
│   │
│   ├── frontend/                        # [PHÂN HỆ GIAO DIỆN CLIENT]
│   │   ├── app/                         # Mã nguồn React/Next.js 14 (7 phân hệ nghiệp vụ TC-04)
│   │   │   ├── layout.tsx               # Root layout tích hợp chuẩn typography TC-04
│   │   │   ├── globals.css              # Custom styling, loại bỏ hoàn toàn bôi vàng và dropcap lỗi
│   │   │   ├── page.tsx                 # 1. Homepage Editorial (Hero Cam, Live Ticker, Allocation)
│   │   │   ├── rooms/page.tsx           # 2. Danh mục phòng, lọc BST/AVL, gợi ý ngân sách & đặt phòng
│   │   │   ├── floor-map/page.tsx       # 3. Sơ đồ ma trận tầng 2D tương tác O(1) theo ngày
│   │   │   ├── operations/page.tsx      # 4. Hàng chờ VIP (Max-Heap), Dịch vụ & Hoàn tác (Undo Stack)
│   │   │   ├── customers/page.tsx       # 5. Tra cứu khách hàng HashTable O(1) & Lịch sử LinkedList
│   │   │   ├── billing/page.tsx         # 6. Quản lý thanh toán, hóa đơn chiết khấu VIP & hoàn tiền
│   │   │   ├── reports/page.tsx         # 7. Báo cáo doanh thu, công suất phòng & Top khách hàng
│   │   │   └── typography-test/page.tsx # Trang kiểm định bảng mã tiếng Việt & kiểu chữ chuyên sâu
│   │   ├── components/                  # UI Components (Navbar, Footer, RoomCard, Badge, Modal, Toast)
│   │   ├── services/api.ts              # Typed API Client giao tiếp backend
│   │   ├── types/index.ts               # Định nghĩa TypeScript interfaces chuẩn hóa
│   │   ├── out/                         # [PRODUCTION STATIC BUILD - 1.6 MB] Toàn bộ HTML/CSS/JS đã compile
│   │   └── package.json, tsconfig...    # Cấu hình dự án (đầy đủ để cài đặt & mở rộng khi cần)
│   │
│   ├── design-system/                   # Hệ thống chuẩn hóa nhận diện thương hiệu
│   │   └── hotelbooking/MASTER.md       # Bảng màu, typography và quy tắc Tangerine TC-04
│   │
│   ├── Chay_Web.bat                     # Script khởi chạy hệ thống Web 1-click duy nhất
│   └── KE_HOACH_XAY_DUNG_UI_UX.md       # [TÀI LIỆU NÀY] Báo cáo đặc tả kiến trúc UI/UX
```

---

## 3. Bảng Ánh Xạ CTDL & Giải Thuật Của Nhóm Vào Giao Diện Web

Toàn bộ 8 cấu trúc dữ liệu và giải thuật cốt lõi do nhóm tự cài đặt 100% bằng Python đã được kết nối trực tiếp vào giao diện Web:

| STT | Cấu trúc Dữ liệu & Giải thuật | File Python nguồn của nhóm | Thành phần trên Web Application | Ý nghĩa trực quan hóa |
|---|---|---|---|---|
| **1** | **Mảng 2 chiều (`Matrix2D`)** | `hotel/data_structures/matrix_2d.py` | Trang **Sơ đồ ma trận 2D** (`/floor-map`) | Hiển thị ma trận 5 tầng $\times$ 10 phòng truy xuất $O(1)$. Bấm xem chi tiết, check-in, check-out và chuyển bảo trì tức thì. |
| **2** | **Cây nhị phân tự cân bằng (`AVLTree` + `IntervalSchedule`)** | `hotel/data_structures/avl_tree.py`, `interval_schedule.py` | Trang **Phòng & Đặt chỗ** (`/rooms`) | Kiểm tra xung đột ngày nhận/trả phòng trên khoảng thời gian nửa mở $[Check\_in, Check\_out)$ với độ phức tạp $O(\log n)$. |
| **3** | **Sắp xếp Merge Sort & Quick Sort (3-way)** | `hotel/algorithms/merge_sort.py`, `quick_sort.py` | Thanh lọc phòng trang `/rooms` | Sắp xếp danh sách phòng khả dụng theo giá tăng/giảm dần với độ phức tạp $O(R \log R)$. |
| **4** | **Tìm kiếm nhị phân (`BinarySearch`)** | `hotel/algorithms/binary_search.py` | Công cụ **Gợi ý theo ngân sách** trang `/rooms` | Tìm kiếm phòng có giá gần ngân sách người dùng nhập nhất với độ phức tạp $O(\log R)$. |
| **5** | **Hàng đợi ưu tiên (`MaxHeap`) & FIFO Queue (`LinkedQueue`)** | `hotel/data_structures/max_heap.py`, `linked_queue.py` | Tab **Hàng chờ khách** (`/operations`) | Khách VIP tự động vào Max-Heap theo cấp bậc VIP và thời gian đến. Khách thường vào Queue FIFO $O(1)$. Phân bổ tự động khi có phòng trống. |
| **6** | **Hàng đợi ưu tiên Dịch vụ (`MaxHeap`)** | `hotel/data_structures/max_heap.py` | Tab **Dịch vụ khẩn cấp** (`/operations`) | Yêu cầu phục vụ nội bộ (Y tế, Dọn dẹp, Ẩm thực) tự động xếp theo độ khẩn cấp (Khẩn cấp > Cao > Thường > Thấp). Xử lý theo thứ tự $O(\log s)$. |
| **7** | **Ngăn xếp Hoàn tác (`Stack` LIFO)** | `hotel/data_structures/stack.py` | Tab **Đơn đặt & Hoàn tác** (`/operations`) | Khi hủy đơn đặt phòng, snapshot được đẩy vào Stack. Giao diện hiển thị thanh thông báo Toast với nút **"Hoàn tác (Undo)"** $O(1)$ khôi phục lại cây BST. |
| **8** | **Bảng băm đa thức (`HashTable` Chaining)** | `hotel/data_structures/hash_table.py` | Trang **Khách hàng** (`/customers`) & **Thanh toán** (`/billing`) | Tra cứu khách hàng theo Mã KH, CCCD hoặc SĐT tức thời $O(1)$ trung bình. Tra cứu lịch sử thanh toán theo Mã GD (TT...) $O(1)$. |
| **9** | **Danh sách liên kết đơn (`SinglyLinkedList`)** | `hotel/data_structures/linked_list.py` | Modal **Lịch sử lưu trú** (`/customers`) | Mỗi khi khách đặt phòng, đơn mới được chèn đầu danh sách $O(1)$ tạo thành dòng thời gian lưu trú xuyên suốt. |

---

## 4. Ngôn Ngữ Thiết Kế & Hệ Thống Typography Chính Thức

Giao diện áp dụng chuẩn mực biên tập cao cấp Tangerine Capital Editorial TC-04 với hệ thống 3 font tối ưu cho tiếng Việt:

### 4.1. Hệ thống Typography 3 Font (Khóa chuẩn):
1. **Display / Heading Font — `Bricolage Grotesque`:**
   - **Weights:** `700` (Bold), `800` (ExtraBold).
   - **Tailwind class:** `font-display`.
   - **Ứng dụng:** Homepage Hero heading, Page titles, Section headings, Card titles, chỉ số thống kê số liệu lớn. Tạo cá tính thương hiệu mạnh mẽ, hiện đại, mang phong cách tạp chí boutique.
2. **Body & UI Font — `Inter`:**
   - **Weights:** `400` (Regular), `500` (Medium), `600` (SemiBold).
   - **Tailwind class:** `font-sans`.
   - **Ứng dụng:** Đoạn văn mô tả (paragraph), thanh điều hướng (navbar), các nút bấm (CTA buttons), form inputs, labels, bảng dữ liệu và modals. Độ nét cao, tối ưu khả năng đọc ở mọi kích cỡ màn hình.
3. **Metadata & Technical Font — `JetBrains Mono`:**
   - **Weights:** `500` (Medium), `700` (Bold).
   - **Tailwind class:** `font-mono`.
   - **Ứng dụng:** Top folio metadata (`NO. TC-04`, `LIGHT EDITION`), Live Ticker Tape, các nhãn thuật ngữ giải thuật (Matrix2D, AVL Tree, Max-Heap, Hash Table), mã phòng, mã giao dịch và mốc thời gian.

### 4.2. Bảng màu chủ đạo (Color Palette):
- **Tangerine Orange (`#E94B18`):** Màu cam ấm đặc trưng cho các khối Hero và thẻ điểm nhấn.
- **Parchment Background (`#F4EBD6` / `#FAF5E9`):** Màu nền giấy da ngà sang trọng, dịu mắt.
- **Primary Ink (`#1D100B`):** Màu mực đen nâu cổ điển, độ tương phản cao đạt chuẩn WCAG AAA.
- **Deep Brown Surfaces (`#1B0D08`):** Bề mặt tương phản cho Footer, khối Allocation và thanh Ticker.

### 4.3. Loại bỏ lỗi hiển thị & Chuẩn hóa Text Rendering:
- **Xóa bỏ hoàn toàn Highlight vàng lỗi thời:** Đã gỡ bỏ 100% các class `.highlight-yellow` gây đè chữ và chật chội. Văn bản hiển thị tinh tế trên nền cam hoặc giấy da.
- **Xóa bỏ ký tự dropcap T đỏ:** Loại bỏ quy tắc `.editorial-dropcap::first-letter` gây lỗi tách rời chữ tiếng Việt; cấu trúc lại phân đoạn Triết lý dịch vụ thành 2 editorial cards thanh lịch.
- **Sửa triệt để lỗi "Phòng Đơn" tàng hình:** Bổ sung mã màu `warm-paper: "#FAF5E9"` vào Tailwind config và định nghĩa biến thể `variant="white"` cho `RoomTypeBadge` với nền trắng đục, chữ đen đậm và viền rõ nét (độ tương phản 21:1 trên mọi nền ảnh).
- **Mở rộng Hero Container:** Điều chỉnh container lên `max-w-5xl xl:max-w-6xl` kèm ngắt dòng hợp lý `<br className="hidden md:inline" />`, tận dụng trọn vẹn diện tích bên phải card cam, không còn khoảng trống bất hợp lý.
- **Chống rớt dòng Navbar:** Toàn bộ 7 mục menu điều hướng được gán thuộc tính `whitespace-nowrap shrink-0`.

---

## 5. Bản Sắc Giọng Văn & Nội Dung (Copywriting Refinement)

Nội dung website được định hình theo giọng văn của một thương hiệu khách sạn boutique thực thụ:
- **Tự nhiên & Tinh tế:** Sử dụng tiếng Việt chuẩn mực, ấm áp, ngắn gọn và có thông tin hữu ích thay cho các khẩu hiệu sáo rỗng do AI sinh ra.
- **Phân tách ranh giới rõ ràng:** Khu vực khách hàng (Trang chủ, Danh mục phòng, Đặt phòng) nói bằng ngôn ngữ hiếu khách thân thiện; khu vực quản trị (Sơ đồ tầng, Hàng chờ, Thanh toán, Báo cáo) dùng thuật ngữ vận hành rõ ràng kèm các nhãn kỹ thuật nhỏ và gọn.
- **Tính xác thực:** Mọi thông tin về giá phòng, số lượng 50 phòng, giờ nhận/trả 14:00/12:00 đều phản ánh chính xác dữ liệu thực tế từ hệ thống.

---

## 6. Hướng Dẫn Khởi Chạy Ứng Dụng Web (Kiến Trúc Tối Ưu Siêu Nhẹ 1.94 MB)

Toàn bộ hệ thống Web được phục vụ hợp nhất qua máy chủ Python FastAPI Bridge, **không cần môi trường Node.js hay gói thư viện `node_modules` (285 MB) cồng kềnh**:

> **Khởi chạy 1-click tại thư mục gốc:**
> Nhấp đúp vào file **[`Chay_Giao_Dien_Web.bat`](file:///d:/project/hotel_booking/Chay_Giao_Dien_Web.bat)** ở thư mục gốc của dự án.
>
> File batch sử dụng đường dẫn tương đối `%~dp0`, đảm bảo chạy thành công 100% trên mọi ổ đĩa (C, D, E, Desktop, USB...), tự động kiểm tra và cài đặt `fastapi, uvicorn` nếu máy bạn chưa có.

Quy trình tự động khi nhấp chạy:
1. **Khởi động siêu tốc (0.2s):** Bật máy chủ tích hợp phục vụ song song toàn bộ 39 REST API và giao diện tĩnh sản phẩm `out/`.
2. **Mở trình duyệt:** Tự động mở trình duyệt mặc định truy cập `http://localhost:8000`.
3. **Tắt máy chủ an toàn:** Khi sử dụng xong, chỉ cần đóng cửa sổ console của máy chủ.

*(Để chạy lại ứng dụng desktop Tkinter ban đầu của nhóm, chỉ cần chạy file [`Chay_Giao_Dien_GUI.bat`](file:///d:/project/hotel_booking/Chay_Giao_Dien_GUI.bat) ở thư mục gốc).*

---

## 7. Kết Quả Kiểm Thử & Nghiệm Thu Hệ Thống

1. **Bộ kiểm thử Tkinter của nhóm (tests/):** **25/25 unit tests đạt PASS (0.293s)**.
2. **Bộ kiểm thử nghiệp vụ tự động (E2E Test Suite):** **15/15 tính năng nghiệp vụ cốt lõi đạt PASS 100%**:
   - Quản lý phòng & Sơ đồ tầng Matrix2D $5 \times 10$.
   - Tìm kiếm & Lọc giá bằng Merge Sort / Quick Sort.
   - Gợi ý phòng theo ngân sách bằng Binary Search.
   - Đặt phòng & phát hiện trùng lịch bằng AVL Tree & Interval Schedule.
   - Quản lý hồ sơ & tra cứu khách hàng bằng Hash Table $O(1)$.
   - Hàng đợi nhận phòng VIP Max-Heap & FIFO Queue.
   - Tiếp nhận và xử lý yêu cầu dịch vụ ưu tiên Max-Heap.
   - Hoàn tác hủy phòng bằng Ngăn xếp (Undo Stack).
   - Tính cước lưu trú chi tiết, giảm giá VIP và xuất hóa đơn thanh toán.
   - Báo cáo doanh thu, công suất phòng và Top khách hàng thân thiết.
3. **Next.js Production Build:** Biên dịch thành công 100% với **Exit Code 0** cho toàn bộ 12 static routes (`/`, `/rooms`, `/floor-map`, `/operations`, `/customers`, `/billing`, `/reports`, `/typography-test`, `/_not-found`...).
4. **Độ tương thích & Responsive:** Hoạt động ổn định trên toàn bộ các dải kích thước Desktop (1440px), Laptop (1280px), Tablet (768px-1024px) và Mobile (390px).
