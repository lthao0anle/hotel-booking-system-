"""Điểm vào chính của Hệ thống Quản lý Đặt phòng Khách sạn (MI3060).

Cách chạy:
    python main.py              # Chạy giao diện dòng lệnh (CLI Menu tương tác)
    python main.py --gui        # Chạy giao diện đồ họa Tkinter (GUI)
    python main.py --demo       # Chạy kịch bản minh họa tự động 8 chức năng cốt lõi
    python main.py --benchmark  # Chạy đánh giá hiệu năng trên tập dữ liệu >= 2.000 bản ghi
    python main.py --reset      # Khởi tạo lại dữ liệu mẫu chuẩn vào data/hotel_data.json
"""

import argparse
import sys

from hotel.benchmark import format_benchmark_report
from hotel.services.hotel_manager import HotelManager
from hotel.ui.cli import HotelCLI, run_demo_walkthrough


def _configure_utf8_console():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Hệ thống Quản lý Đặt phòng Khách sạn — Cấu trúc Dữ liệu & Giải thuật (MI3060)"
    )
    parser.add_argument("--gui", action="store_true", help="Khởi chạy giao diện đồ họa Tkinter (GUI)")
    parser.add_argument("--demo", action="store_true", help="Chạy kịch bản minh họa tự động trên console")
    parser.add_argument("--benchmark", action="store_true", help="Chạy đo hiệu năng thực nghiệm (>= 2.000 bản ghi)")
    parser.add_argument("--reset", action="store_true", help="Khởi tạo lại dữ liệu mẫu trước khi chạy")
    return parser.parse_args(argv)


def main(argv=None):
    _configure_utf8_console()
    args = parse_args(argv)

    if args.benchmark:
        print("=== KẾT QUẢ ĐÁNH GIÁ HIỆU NĂNG THỰC NGHIỆM (CHƯƠNG 4 — >= 2.000 BẢN GHI) ===")
        print(format_benchmark_report())
        return

    if args.reset:
        manager = HotelManager(seed_if_empty=False, load_existing=False)
        manager.reset_with_sample_data()
        print("[OK] Đã khởi tạo lại dữ liệu mẫu tại data/hotel_data.json.")
    else:
        manager = HotelManager(seed_if_empty=True)

    if args.demo:
        run_demo_walkthrough(manager)
        return

    if args.gui:
        from hotel.ui.gui import HotelGUI

        app = HotelGUI(manager)
        app.run()
        return

    cli = HotelCLI(manager)
    cli.run()


if __name__ == "__main__":
    main()
