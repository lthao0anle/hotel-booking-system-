"""Tiện ích ngày tháng: định dạng hiển thị dd/mm/yyyy, lưu trữ ISO yyyy-mm-dd."""

from datetime import date, datetime

DISPLAY_FORMAT = "%d/%m/%Y"
_ACCEPTED_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


def parse_date(text):
    """Chuyển chuỗi (dd/mm/yyyy hoặc yyyy-mm-dd) thành `date`; ném ValueError nếu sai."""
    cleaned = (text or "").strip()
    for fmt in _ACCEPTED_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Ngày không hợp lệ: '{text}'. Định dạng đúng: dd/mm/yyyy")


def format_date(value):
    return value.strftime(DISPLAY_FORMAT)


def to_iso(value):
    return value.isoformat()


def from_iso(text):
    return date.fromisoformat(text)
