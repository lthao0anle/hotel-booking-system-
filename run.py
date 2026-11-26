"""Chạy API server FastAPI cho Hotel Booking Editorial System.

Cách dùng:
    python web_app/backend/run.py
"""

import os
import sys
import subprocess

# Ensure project root in sys.path
curr = os.path.dirname(os.path.abspath(__file__))
root_dir = curr
while curr and curr != os.path.dirname(curr):
    if os.path.exists(os.path.join(curr, "hotel", "services", "hotel_manager.py")):
        root_dir = curr
        break
    curr = os.path.dirname(curr)

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Try importing uvicorn, if missing try candidate python binaries with packages
try:
    import uvicorn
except ImportError:
    candidate_pythons = [
        r"C:\Users\dingg\AppData\Local\Python\bin\python.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Python\bin\python.exe"),
        os.path.expanduser(r"~\AppData\Local\Python\bin\python.exe"),
    ]
    for py in candidate_pythons:
        if os.path.exists(py) and py.lower() != sys.executable.lower():
            res = subprocess.call([py, __file__] + sys.argv[1:])
            sys.exit(res)
    raise

# Import FastAPI app directly
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
from api import app


def _free_port_if_in_use(port: int):
    """Giải phóng cổng port (mặc định 8000) nếu có tiến trình cũ đang chiếm giữ."""
    if os.name != "nt":
        return
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        my_pid = str(os.getpid())
        for line in out.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit() and pid != my_pid and pid != "0":
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False,
                        )
    except Exception:
        pass


def main():
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    _free_port_if_in_use(port)
    print(f"🚀 Khởi chạy FastAPI Backend Bridge tại http://{host}:{port} ...")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
