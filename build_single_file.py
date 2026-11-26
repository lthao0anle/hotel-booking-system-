"""Kịch bản đóng gói toàn bộ dự án thành 1 file hotel_booking_all_in_one.py và nén hotel_booking.zip."""

import pathlib
import zipfile

root = pathlib.Path(r"C:\Users\dell\.gemini\antigravity\scratch\hotel_booking")
order = [
    "hotel/models/enums.py",
    "hotel/config.py",
    "hotel/models/date_utils.py",
    "hotel/data_structures/matrix_2d.py",
    "hotel/data_structures/avl_tree.py",
    "hotel/data_structures/interval_schedule.py",
    "hotel/data_structures/linked_list.py",
    "hotel/data_structures/linked_queue.py",
    "hotel/data_structures/hash_table.py",
    "hotel/data_structures/max_heap.py",
    "hotel/data_structures/stack.py",
    "hotel/algorithms/merge_sort.py",
    "hotel/algorithms/quick_sort.py",
    "hotel/algorithms/binary_search.py",
    "hotel/algorithms/naive.py",
    "hotel/models/room.py",
    "hotel/models/booking.py",
    "hotel/models/customer.py",
    "hotel/models/waiting_entry.py",
    "hotel/models/service_request.py",
    "hotel/models/cancel_action.py",
    "hotel/models/payment.py",
    "hotel/services/errors.py",
    "hotel/services/id_generator.py",
    "hotel/services/room_service.py",
    "hotel/services/customer_service.py",
    "hotel/services/booking_service.py",
    "hotel/services/waiting_service.py",
    "hotel/services/undo_service.py",
    "hotel/services/service_request_service.py",
    "hotel/services/payment_service.py",
    "hotel/services/report_service.py",
    "hotel/services/storage_service.py",
    "hotel/services/seed_service.py",
    "hotel/services/hotel_manager.py",
    "hotel/ui/formatter.py",
    "hotel/benchmark.py",
    "hotel/ui/cli.py",
    "hotel/ui/gui.py",
    "main.py",
]

header = '''#!/usr/bin/env python3
"""
HỆ THỐNG QUẢN LÝ ĐẶT PHÒNG KHÁCH SẠN — BẢN GỘP 1 FILE DUY NHẤT (ALL-IN-ONE)
Học phần: Cấu trúc Dữ liệu và Giải thuật (MI3060)

Chỉ cần gửi 1 file này cho người khác, máy có cài Python 3.10+ là chạy được ngay:
  - Chạy menu dòng lệnh (CLI) : python hotel_booking_all_in_one.py
  - Chạy giao diện đồ họa     : python hotel_booking_all_in_one.py --gui
  - Chạy minh họa tự động     : python hotel_booking_all_in_one.py --demo
  - Chạy đo hiệu năng         : python hotel_booking_all_in_one.py --benchmark
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum, IntEnum
import json
from pathlib import Path
import random
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk
'''

sections = [header.strip()]
for rel in order:
    text = (root / rel).read_text(encoding="utf-8")
    lines = text.splitlines()
    out_lines = []
    skip_multiline_import = False
    for line in lines:
        if rel != "main.py" and line.strip().startswith('if __name__ == "__main__":'):
            break
        if skip_multiline_import:
            if ")" in line:
                skip_multiline_import = False
            continue
        stripped = line.strip()
        if stripped.startswith("from hotel.") or stripped.startswith("import hotel."):
            if "(" in stripped and ")" not in stripped:
                skip_multiline_import = True
            continue
        if line.startswith("import ") or line.startswith("from "):
            continue
        out_lines.append(line)
    body = "\n".join(out_lines).strip()
    if rel == "hotel/config.py":
        body = body.replace(
            "PROJECT_ROOT = Path(__file__).resolve().parent.parent",
            "PROJECT_ROOT = Path(__file__).resolve().parent",
        )
    sections.append(
        "# " + "=" * 76 + f"\n# MODULE: {rel}\n# " + "=" * 76 + "\n" + body
    )

target = root / "hotel_booking_all_in_one.py"
target.write_text("\n\n\n".join(sections) + "\n", encoding="utf-8")
print("Created single file:", target, "lines:", len(target.read_text(encoding="utf-8").splitlines()))

# Create double-click .bat launchers
(root / "Chay_Giao_Dien_GUI.bat").write_text(
    "@echo off\r\nchcp 65001 >nul\r\ncd /d \"%~dp0\"\r\npython main.py --gui\r\npause\r\n",
    encoding="utf-8",
)
(root / "Chay_Menu_CLI.bat").write_text(
    "@echo off\r\nchcp 65001 >nul\r\ncd /d \"%~dp0\"\r\npython main.py\r\npause\r\n",
    encoding="utf-8",
)

# Create hotel_booking.zip in parent and inside root
import shutil

zip_path = root.parent / "hotel_booking.zip"
inner_zip_path = root / "hotel_booking.zip"
excluded_dirs = {"__pycache__", "node_modules", ".next", ".git"}
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for file_path in root.rglob("*"):
        if (
            any(part in excluded_dirs for part in file_path.parts)
            or file_path.is_dir()
            or file_path.name == "hotel_booking.zip"
        ):
            continue
        arcname = pathlib.Path("hotel_booking") / file_path.relative_to(root)
        zf.write(file_path, arcname)

shutil.copy2(zip_path, inner_zip_path)
print("Created zip archive:", zip_path, "size:", zip_path.stat().st_size)
