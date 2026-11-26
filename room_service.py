"""Chức năng 1 & 3: Quản lý phòng theo tầng (Mảng 2D) và Lọc/Sắp xếp/Tìm kiếm phòng.

Độ phức tạp mục tiêu:
- Truy cập phòng theo (tầng, số phòng) hoặc mã phòng (vd 'P205') : O(1) qua Matrix2D
- Sắp xếp danh sách phòng theo giá (Merge Sort / Quick Sort)     : O(R log R)
- Tìm phòng theo khoảng giá [min, max] trên mảng đã sắp          : O(log R + k) qua Binary Search
- Tìm phòng có giá gần nhất với ngân sách (budget)               : O(log R) qua Binary Search
- Lọc theo loại phòng + tìm theo ngưỡng giá                      : O(log R_t + k) nhờ nhóm theo loại
"""

from hotel.algorithms.binary_search import (
    binary_search,
    find_closest,
    range_search,
)
from hotel.algorithms.merge_sort import merge_sort
from hotel.algorithms.quick_sort import quick_sort
from hotel.config import (
    BASE_PRICE_BY_TYPE,
    DEFAULT_FLOORS,
    DEFAULT_ROOMS_PER_FLOOR,
    FLOOR_SURCHARGE,
    ROOM_DESCRIPTION_BY_TYPE,
)
from hotel.data_structures.matrix_2d import Matrix2D
from hotel.models.enums import RoomType
from hotel.models.room import Room, parse_room_id
from hotel.services.errors import HotelError, NotFoundError


def _price_key(room):
    return room.price_per_night


def _default_room_type(room_number, rooms_per_floor):
    """Phân bổ loại phòng mặc định trong mỗi tầng:
    40% đầu là SINGLE, 40% tiếp theo là DOUBLE, 20% cuối là SUITE.
    """
    single_limit = max(1, (rooms_per_floor * 4) // 10)
    double_limit = max(single_limit + 1, (rooms_per_floor * 8) // 10)
    if room_number <= single_limit:
        return RoomType.SINGLE
    if room_number <= double_limit:
        return RoomType.DOUBLE
    return RoomType.SUITE


class RoomService:
    def __init__(self, floors=DEFAULT_FLOORS, rooms_per_floor=DEFAULT_ROOMS_PER_FLOOR):
        self._matrix = Matrix2D(floors, rooms_per_floor)
        self._sorted_by_price = []
        self._sorted_by_type = {room_type: [] for room_type in RoomType}
        self._initialize_default_rooms()

    @property
    def floors(self):
        return self._matrix.rows

    @property
    def rooms_per_floor(self):
        return self._matrix.cols

    @property
    def matrix(self):
        return self._matrix

    # ------------------- Khởi tạo & nạp sơ đồ ma trận ------------------- #
    def _initialize_default_rooms(self):
        for floor in range(1, self.floors + 1):
            for number in range(1, self.rooms_per_floor + 1):
                rtype = _default_room_type(number, self.rooms_per_floor)
                price = BASE_PRICE_BY_TYPE[rtype] + (floor - 1) * FLOOR_SURCHARGE
                room = Room(
                    floor=floor,
                    room_number=number,
                    room_type=rtype,
                    price_per_night=price,
                    description=ROOM_DESCRIPTION_BY_TYPE[rtype],
                )
                self._matrix.set(floor - 1, number - 1, room)
        self._rebuild_sorted_index()

    def load_rooms(self, floors, rooms_per_floor, room_list):
        """Khôi phục ma trận phòng từ dữ liệu lưu trữ."""
        self._matrix = Matrix2D(floors, rooms_per_floor)
        self._initialize_default_rooms()
        for room in room_list:
            if not self._matrix.in_bounds(room.floor - 1, room.room_number - 1):
                raise HotelError(f"Vị trí phòng {room.room_id} nằm ngoài sơ đồ khách sạn")
            self._matrix.set(room.floor - 1, room.room_number - 1, room)
        self._rebuild_sorted_index()

    def _rebuild_sorted_index(self):
        """Cập nhật chỉ mục đã sắp theo giá bằng Merge Sort — O(R log R)."""
        all_rooms = list(self._matrix)
        self._sorted_by_price = merge_sort(all_rooms, key=_price_key)
        self._sorted_by_type = {
            rtype: [r for r in self._sorted_by_price if r.room_type == rtype]
            for rtype in RoomType
        }

    # -------------------- Truy cập O(1) trên Mảng 2D -------------------- #
    def get_room_by_coords(self, floor, room_number):
        """Truy cập trực tiếp phòng theo (tầng, số phòng) — O(1)."""
        row, col = floor - 1, room_number - 1
        if not self._matrix.in_bounds(row, col):
            raise NotFoundError(
                f"Không tồn tại phòng ở tầng {floor}, số {room_number} "
                f"(khách sạn có {self.floors} tầng × {self.rooms_per_floor} phòng)"
            )
        return self._matrix.get(row, col)

    def get_room(self, room_id):
        """Truy cập trực tiếp phòng theo mã phòng (vd 'P205') — O(1) nhờ ánh xạ tọa độ."""
        try:
            floor, room_number = parse_room_id(room_id)
        except ValueError as exc:
            raise NotFoundError(str(exc)) from exc
        return self.get_room_by_coords(floor, room_number)

    def floor_rooms(self, floor):
        """Danh sách phòng của một tầng (1..floors) — O(rooms_per_floor)."""
        if not 1 <= floor <= self.floors:
            raise NotFoundError(f"Tầng {floor} không hợp lệ (1..{self.floors})")
        return self._matrix.row(floor - 1)

    def all_rooms(self):
        """Danh sách toàn bộ phòng theo thứ tự tầng -> số phòng."""
        return list(self._matrix)

    # ------------------------- Cập nhật phòng --------------------------- #
    def set_maintenance(self, room_id, under_maintenance):
        """Đặt hoặc gỡ trạng thái bảo trì cho phòng — O(1)."""
        room = self.get_room(room_id)
        room.under_maintenance = bool(under_maintenance)
        return room

    def update_room_price(self, room_id, new_price):
        """Cập nhật giá phòng và tái lập chỉ mục sắp xếp — O(R log R)."""
        if new_price <= 0:
            raise HotelError("Giá phòng phải lớn hơn 0")
        room = self.get_room(room_id)
        room.price_per_night = int(new_price)
        self._rebuild_sorted_index()
        return room

    # ---------- Sắp xếp O(R log R) & Tìm kiếm nhị phân O(log R) --------- #
    def sort_rooms(self, rooms=None, by="price", reverse=False, algorithm="merge"):
        """Sắp xếp danh sách phòng bằng Merge Sort (ổn định) hoặc Quick Sort — O(R log R).

        Tham số `by`:
            - "price": sắp theo giá/đêm
            - "type_price": sắp theo loại phòng rồi theo giá
            - "room_id": sắp theo tầng và số phòng
        """
        target = self.all_rooms() if rooms is None else list(rooms)
        if by == "price":
            key_fn = _price_key
        elif by == "type_price":
            key_fn = lambda r: (r.room_type.order, r.price_per_night, r.floor, r.room_number)
        elif by == "room_id":
            key_fn = lambda r: (r.floor, r.room_number)
        else:
            raise HotelError(f"Tiêu chí sắp xếp không hợp lệ: {by}")

        sorter = quick_sort if algorithm == "quick" else merge_sort
        return sorter(target, key=key_fn, reverse=reverse)

    def filter_by_price_range(self, min_price=0, max_price=float("inf"), room_type=None):
        """Tìm phòng trong khoảng giá [min_price, max_price] bằng Binary Search — O(log R + k).

        Nếu truyền `room_type`, tìm trực tiếp trên mảng con đã phân nhóm theo loại phòng.
        """
        if min_price > max_price:
            raise HotelError("Giá tối thiểu không được lớn hơn giá tối đa")
        sorted_pool = (
            self._sorted_by_type[room_type]
            if room_type is not None
            else self._sorted_by_price
        )
        return range_search(sorted_pool, min_price, max_price, key=_price_key)

    def find_closest_to_budget(self, budget, room_type=None, candidates=None):
        """Tìm phòng có giá gần nhất với `budget` bằng Binary Search — O(log R).

        - Nếu `candidates` là None: tìm trực tiếp trên mảng đã sort sẵn trong O(log R).
        - Nếu truyền `candidates` (ví dụ tập phòng trống): sắp bằng Merge Sort rồi Binary Search.
        """
        if budget <= 0:
            raise HotelError("Ngân sách phải lớn hơn 0")
        if candidates is not None:
            pool = [
                r for r in candidates
                if room_type is None or r.room_type == room_type
            ]
            sorted_pool = merge_sort(pool, key=_price_key)
        else:
            sorted_pool = (
                self._sorted_by_type[room_type]
                if room_type is not None
                else self._sorted_by_price
            )
        return find_closest(sorted_pool, budget, key=_price_key)

    def find_exact_price(self, price, room_type=None):
        """Kiểm tra và trả về một phòng có giá đúng bằng `price` bằng Binary Search — O(log R)."""
        sorted_pool = (
            self._sorted_by_type[room_type]
            if room_type is not None
            else self._sorted_by_price
        )
        idx = binary_search(sorted_pool, price, key=_price_key)
        return None if idx == -1 else sorted_pool[idx]
