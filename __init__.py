"""Tầng Giao diện tương tác (CLI & Tkinter GUI)."""

from hotel.ui.cli import HotelCLI, run_demo_walkthrough
from hotel.ui.formatter import (
    format_bookings_table,
    format_customers_table,
    format_rooms_table,
    format_service_requests_table,
    format_undo_stack_table,
    format_vnd,
    format_waiting_table,
    render_floor_matrix,
    render_table,
)

__all__ = [
    "HotelCLI",
    "format_bookings_table",
    "format_customers_table",
    "format_rooms_table",
    "format_service_requests_table",
    "format_undo_stack_table",
    "format_vnd",
    "format_waiting_table",
    "render_floor_matrix",
    "render_table",
    "run_demo_walkthrough",
]
