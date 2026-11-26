"""Mảng hai chiều kích thước cố định (rows × cols).

Lưu trên một mảng một chiều liên tục: phần tử (r, c) nằm ở chỉ số r * cols + c,
giống cách bố trí "row-major" của mảng 2 chiều trong C.

Dùng để lưu danh sách phòng theo tầng: rooms[tầng][số phòng].

Độ phức tạp: get / set O(1), duyệt toàn bộ O(rows × cols).
"""


class Matrix2D:
    def __init__(self, rows, cols, fill=None):
        if rows <= 0 or cols <= 0:
            raise ValueError("Kích thước mảng 2 chiều phải dương")
        self._rows = rows
        self._cols = cols
        self._cells = [fill] * (rows * cols)

    @property
    def rows(self):
        return self._rows

    @property
    def cols(self):
        return self._cols

    def get(self, row, col):
        return self._cells[self._offset(row, col)]

    def set(self, row, col, value):
        self._cells[self._offset(row, col)] = value

    def in_bounds(self, row, col):
        return 0 <= row < self._rows and 0 <= col < self._cols

    def row(self, row):
        """Trả về các phần tử của một hàng (một tầng) — O(cols)."""
        start = self._offset(row, 0)
        return self._cells[start:start + self._cols]

    def __iter__(self):
        """Duyệt theo thứ tự hàng (tầng) rồi tới cột (phòng)."""
        return iter(list(self._cells))

    def __len__(self):
        return self._rows * self._cols

    def _offset(self, row, col):
        if not self.in_bounds(row, col):
            raise IndexError(f"Vị trí ({row}, {col}) nằm ngoài mảng {self._rows}x{self._cols}")
        return row * self._cols + col
