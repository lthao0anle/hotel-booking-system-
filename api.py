"""FastAPI Backend Bridge for Hotel Booking System.

Kết nối trực tiếp với lớp Facade HotelManager (CTDL & GT - MI3060).
Cung cấp REST API đầy đủ cho Next.js Frontend mà không làm thay đổi source code hotel/.
"""

import os
import sys
from datetime import date, datetime
from typing import Any, Dict, List, Optional

# Tìm thư mục gốc dự án chứa gói hotel
curr = os.path.dirname(os.path.abspath(__file__))
root_dir = curr
while curr and curr != os.path.dirname(curr):
    if os.path.exists(os.path.join(curr, "hotel", "services", "hotel_manager.py")):
        root_dir = curr
        break
    curr = os.path.dirname(curr)

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from hotel.config import (
    VIP_DISCOUNT_RATES,
    VIP_SPENDING_THRESHOLDS,
    get_vip_tier_progress,
)
from hotel.models.date_utils import format_date, parse_date
from hotel.models.enums import (
    BookingStatus,
    PaymentMethod,
    PaymentStatus,
    RoomStatus,
    RoomType,
    ServiceType,
    UrgencyLevel,
    VipLevel,
)
from hotel.services.errors import (
    HotelError,
    NotFoundError,
    RoomUnavailableError,
)
from hotel.services.hotel_manager import HotelManager

app = FastAPI(
    title="Hotel Booking Editorial API Bridge",
    description="REST API Bridge connecting Next.js to HotelManager (CTDL & GT MI3060)",
    version="1.0.0",
)

# Enable CORS for Next.js frontend (default ports: 3000, 3001, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_browser_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# Initialize HotelManager with standard data file
manager = HotelManager(seed_if_empty=True, load_existing=True)


# ---------------------------------------------------------------------------
# Helper Serializers
# ---------------------------------------------------------------------------
def serialize_room(room):
    if room is None:
        return None
    maint = getattr(room, "under_maintenance", False)
    return {
        "room_id": room.room_id,
        "floor": room.floor,
        "room_number": room.room_number,
        "room_type": room.room_type.value if hasattr(room.room_type, "value") else str(room.room_type),
        "price_per_night": room.price_per_night,
        "is_maintenance": maint,
        "under_maintenance": maint,
    }


def serialize_booking(b):
    if b is None:
        return None
    if isinstance(b, (tuple, list)) and len(b) == 2:
        b = b[1]
    return {
        "booking_id": b.booking_id,
        "customer_id": b.customer_id,
        "room_id": b.room_id,
        "check_in": b.check_in.isoformat() if isinstance(b.check_in, date) else str(b.check_in),
        "check_out": b.check_out.isoformat() if isinstance(b.check_out, date) else str(b.check_out),
        "status": b.status.value if hasattr(b.status, "value") else str(b.status),
        "total_price": getattr(b, "total_price", 0),
        "num_nights": getattr(b, "num_nights", 0),
        "created_at": b.created_at.isoformat() if hasattr(b, "created_at") and isinstance(b.created_at, date) else str(getattr(b, "created_at", "")),
    }


def serialize_customer(c):
    if c is None:
        return None
    try:
        manager.sync_customer_vip(c.customer_id)
    except Exception:
        pass
    vip_int = int(c.vip_level) if hasattr(c, "vip_level") else 0
    vip_enum = VipLevel(vip_int)
    try:
        vip_prog = manager.customer_vip_progress(c.customer_id)
        paid_tx_count = vip_prog.get("paid_transaction_count", 0)
    except Exception:
        vip_prog = get_vip_tier_progress(vip_enum, 0)
        paid_tx_count = 0
    next_vip = vip_prog.get("next_vip")
    return {
        "customer_id": c.customer_id,
        "full_name": c.full_name,
        "cccd": c.cccd,
        "phone": c.phone,
        "vip_level": vip_int,
        "vip_label": vip_enum.label,
        "total_paid": vip_prog["total_paid"],
        "qualifying_spending": vip_prog.get("qualifying_spending", vip_prog["total_paid"]),
        "discount_rate": vip_prog["discount_rate"],
        "earned_vip": int(vip_prog["earned_vip"]),
        "next_vip": int(next_vip) if next_vip is not None else None,
        "next_vip_label": next_vip.label if next_vip is not None else None,
        "next_threshold": vip_prog["next_threshold"],
        "amount_to_next_vip": vip_prog["amount_to_next_vip"],
        "progress_percent": vip_prog["progress_percent"],
        "paid_transaction_count": paid_tx_count,
    }


def serialize_payment(tx):
    if tx is None:
        return None
    amount = getattr(tx, "total_amount", getattr(tx, "amount", 0))
    return {
        "payment_id": tx.payment_id,
        "booking_id": tx.booking_id,
        "customer_id": tx.customer_id,
        "room_id": getattr(tx, "room_id", ""),
        "room_cost": getattr(tx, "room_cost", 0),
        "service_cost": getattr(tx, "service_cost", 0),
        "extra_fee": getattr(tx, "extra_fee", 0),
        "discount_amount": getattr(tx, "discount_amount", 0),
        "amount": amount,
        "total_amount": amount,
        "payment_method": tx.payment_method.value if hasattr(tx.payment_method, "value") else str(tx.payment_method),
        "status": tx.status.value if hasattr(tx.status, "value") else str(tx.status),
        "paid_at": tx.paid_at.isoformat() if isinstance(tx.paid_at, (date, datetime)) else str(tx.paid_at),
        "note": getattr(tx, "note", ""),
    }


def serialize_service_request(req):
    if req is None:
        return None
    return {
        "request_id": req.request_id,
        "room_id": req.room_id,
        "service_type": req.service_type.value if hasattr(req.service_type, "value") else str(req.service_type),
        "urgency": req.urgency.value if hasattr(req.urgency, "value") else str(req.urgency),
        "note": req.note,
        "customer_id": getattr(req, "customer_id", ""),
        "requested_at": req.requested_at.isoformat() if isinstance(req.requested_at, date) else str(req.requested_at),
    }


def serialize_waiting_entry(entry):
    if entry is None:
        return None
    prio = getattr(entry, "priority", 0)
    return {
        "entry_id": entry.entry_id,
        "customer_id": entry.customer_id,
        "room_type": entry.room_type.value if hasattr(entry.room_type, "value") else str(entry.room_type),
        "check_in": entry.check_in.isoformat() if isinstance(entry.check_in, date) else str(entry.check_in),
        "check_out": entry.check_out.isoformat() if isinstance(entry.check_out, date) else str(entry.check_out),
        "created_at": entry.requested_at.isoformat() if hasattr(entry, "requested_at") and isinstance(entry.requested_at, date) else str(getattr(entry, "requested_at", "")),
        "is_vip": prio > 0,
        "vip_level": prio,
    }


# ---------------------------------------------------------------------------
# API Routes: Health & System
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": "Hotel Booking Editorial API Bridge",
        "design_system": "Tangerine Capital TC-04",
        "total_rooms": manager.rooms.floors * manager.rooms.rooms_per_floor,
        "floors": manager.rooms.floors,
        "rooms_per_floor": manager.rooms.rooms_per_floor,
    }


@app.post("/api/system/reset-sample")
def reset_sample_data():
    manager.reset_with_sample_data()
    return {"message": "Đã thiết lập lại dữ liệu mẫu thành công."}


# ---------------------------------------------------------------------------
# API Routes: 1. Rooms & Floor Map (Matrix 2D)
# ---------------------------------------------------------------------------
@app.get("/api/rooms")
def get_all_rooms():
    all_rooms = []
    for floor in range(1, manager.rooms.floors + 1):
        for room in manager.rooms.floor_rooms(floor):
            all_rooms.append(serialize_room(room))
    return all_rooms


@app.get("/api/rooms/floor-map")
def get_floor_map(on_date: Optional[str] = None):
    target_date = parse_date(on_date) if on_date else date.today()
    grid = manager.floor_map(on_date=target_date)
    serialized_grid = []
    for row in grid:
        serialized_row = []
        for cell in row:
            room = cell["room"]
            status = cell["status"]
            booking = cell["booking"]
            serialized_row.append({
                "room": serialize_room(room),
                "status": status.value if hasattr(status, "value") else str(status),
                "booking": serialize_booking(booking),
            })
        serialized_grid.append(serialized_row)
    return {
        "target_date": target_date.isoformat(),
        "floors": manager.rooms.floors,
        "rooms_per_floor": manager.rooms.rooms_per_floor,
        "grid": serialized_grid,
    }


@app.get("/api/rooms/{room_id}")
def get_room_detail(room_id: str):
    try:
        room = manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Không tìm thấy phòng")
        return serialize_room(room)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class MaintenanceRequest(BaseModel):
    under_maintenance: bool


@app.post("/api/rooms/{room_id}/maintenance")
def set_room_maintenance(room_id: str, req: MaintenanceRequest):
    try:
        room = manager.set_room_maintenance(room_id, req.under_maintenance)
        return serialize_room(room)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# API Routes: 2 & 3. Room Search, Filtering & Budget Suggestion (AVL + Sorts)
# ---------------------------------------------------------------------------
@app.get("/api/rooms/search/available")
def search_available_rooms(
    check_in: str = Query(..., description="YYYY-MM-DD or DD/MM/YYYY"),
    check_out: str = Query(..., description="YYYY-MM-DD or DD/MM/YYYY"),
    room_type: Optional[str] = None,
    min_price: float = 0,
    max_price: float = float("inf"),
    sort_by: str = "price",
    reverse: bool = False,
    algorithm: str = "merge",
):
    try:
        d_in = parse_date(check_in)
        d_out = parse_date(check_out)
        rtype = RoomType(room_type) if room_type else None
        rooms = manager.find_available_rooms(
            check_in=d_in,
            check_out=d_out,
            room_type=rtype,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            reverse=reverse,
            algorithm=algorithm,
        )
        return [serialize_room(r) for r in rooms]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class BudgetSuggestRequest(BaseModel):
    budget: float
    room_type: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None


@app.post("/api/rooms/search/suggest-budget")
def suggest_budget(req: BudgetSuggestRequest):
    try:
        d_in = parse_date(req.check_in) if req.check_in else None
        d_out = parse_date(req.check_out) if req.check_out else None
        rtype = RoomType(req.room_type) if req.room_type else None
        room = manager.suggest_room_by_budget(
            budget=req.budget,
            room_type=rtype,
            check_in=d_in,
            check_out=d_out,
        )
        return serialize_room(room)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# API Routes: 4. Customers & Stay History (Hash Table + Singly Linked List)
# ---------------------------------------------------------------------------
@app.get("/api/customers")
def get_all_customers():
    customers = manager.customers.all_customers()
    return [serialize_customer(c) for c in customers]


@app.get("/api/customers/lookup/{query}")
def lookup_customer(query: str):
    try:
        c = manager.lookup_customer(query)
        if not c:
            raise HTTPException(status_code=404, detail="Không tìm thấy khách hàng")
        return serialize_customer(c)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class RegisterCustomerRequest(BaseModel):
    full_name: str
    cccd: str
    phone: str
    vip_level: int = 0


@app.post("/api/customers")
def register_customer(req: RegisterCustomerRequest):
    try:
        c = manager.register_customer(
            full_name=req.full_name,
            cccd=req.cccd,
            phone=req.phone,
            vip_level=req.vip_level,
        )
        return serialize_customer(c)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class SetVipRequest(BaseModel):
    vip_level: int


@app.post("/api/customers/{customer_id}/vip")
def set_customer_vip(customer_id: str, req: SetVipRequest):
    try:
        c = manager.set_customer_vip(customer_id, req.vip_level)
        return serialize_customer(c)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/customers/{customer_id}/history")
def get_customer_history(customer_id: str):
    try:
        history_nodes = manager.customer_stay_history(customer_id)
        # SinglyLinkedList has to_list()
        items = history_nodes.to_list() if hasattr(history_nodes, "to_list") else list(history_nodes)
        return [serialize_booking(b) for b in items]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/customers/{customer_id}/vip-progress")
def get_customer_vip_progress(customer_id: str):
    try:
        prog = manager.customer_vip_progress(customer_id)
        next_vip = prog.get("next_vip")
        return {
            "customer": serialize_customer(prog["customer"]),
            "customer_id": prog["customer_id"],
            "current_vip": int(prog["current_vip"]),
            "current_vip_label": prog["current_vip"].label,
            "earned_vip": int(prog["earned_vip"]),
            "earned_vip_label": prog["earned_vip"].label,
            "effective_vip": int(prog["effective_vip"]),
            "total_paid": prog["total_paid"],
            "paid_transaction_count": prog["paid_transaction_count"],
            "discount_rate": prog["discount_rate"],
            "next_vip": int(next_vip) if next_vip is not None else None,
            "next_vip_label": next_vip.label if next_vip is not None else None,
            "next_threshold": prog["next_threshold"],
            "amount_to_next_vip": prog["amount_to_next_vip"],
            "progress_percent": prog["progress_percent"],
            "thresholds": {int(k): v for k, v in VIP_SPENDING_THRESHOLDS.items()},
            "discount_rates": {int(k): v for k, v in VIP_DISCOUNT_RATES.items()},
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/customers/{customer_id}/sync-vip")
def sync_customer_vip(customer_id: str):
    try:
        res = manager.sync_customer_vip(customer_id)
        return {
            "customer": serialize_customer(res["customer"]),
            "old_vip": int(res["old_vip"]),
            "new_vip": int(res["new_vip"]),
            "earned_vip": int(res["earned_vip"]),
            "changed": res["changed"],
            "upgraded": res["upgraded"],
            "total_paid": res["total_paid"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# API Routes: 5. Bookings (AVL Tree / Interval Schedule)
# ---------------------------------------------------------------------------
@app.get("/api/bookings")
def get_all_bookings():
    bookings = manager.bookings.all_bookings()
    return [serialize_booking(b) for b in bookings]


@app.get("/api/bookings/{booking_id}")
def get_booking(booking_id: str):
    try:
        b = manager.bookings.get_booking(booking_id)
        if not b:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn đặt phòng")
        return serialize_booking(b)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class CreateBookingRequest(BaseModel):
    customer_id: str
    room_id: str
    check_in: str
    check_out: str


@app.post("/api/bookings")
def create_booking(req: CreateBookingRequest):
    try:
        d_in = parse_date(req.check_in)
        d_out = parse_date(req.check_out)
        cust_before = manager.customers.get_customer(req.customer_id)
        old_vip = int(cust_before.vip_level)
        b = manager.book_room(
            customer_id=req.customer_id,
            room_id=req.room_id,
            check_in=d_in,
            check_out=d_out,
        )
        cust_after = manager.customers.get_customer(b.customer_id)
        new_vip = int(cust_after.vip_level)
        data = serialize_booking(b)
        data.update(
            {
                "previous_vip_level": old_vip,
                "previous_vip_label": VipLevel(old_vip).label,
                "new_vip_level": new_vip,
                "new_vip_label": VipLevel(new_vip).label,
                "vip_upgraded": new_vip > old_vip,
                "customer_total_paid": manager.customer_total_paid(b.customer_id),
            }
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class BookOrWaitRequest(BaseModel):
    customer_id: str
    room_type: str
    check_in: str
    check_out: str


@app.post("/api/bookings/book-or-wait")
def book_or_wait(req: BookOrWaitRequest):
    try:
        d_in = parse_date(req.check_in)
        d_out = parse_date(req.check_out)
        rtype = RoomType(req.room_type)
        cust_before = manager.customers.get_customer(req.customer_id)
        old_vip = int(cust_before.vip_level)
        status_tag, obj = manager.book_by_type_or_wait(
            customer_id=req.customer_id,
            room_type=rtype,
            check_in=d_in,
            check_out=d_out,
        )
        if status_tag == "BOOKED":
            cust_after = manager.customers.get_customer(obj.customer_id)
            new_vip = int(cust_after.vip_level)
            bk_data = serialize_booking(obj)
            bk_data.update(
                {
                    "previous_vip_level": old_vip,
                    "previous_vip_label": VipLevel(old_vip).label,
                    "new_vip_level": new_vip,
                    "new_vip_label": VipLevel(new_vip).label,
                    "vip_upgraded": new_vip > old_vip,
                    "customer_total_paid": manager.customer_total_paid(obj.customer_id),
                }
            )
            return {"outcome": "BOOKED", "booking": bk_data}
        else:
            return {"outcome": "WAITING", "waiting_entry": serialize_waiting_entry(obj)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/bookings/{booking_id}/check-in")
def check_in_booking(booking_id: str):
    try:
        b = manager.check_in(booking_id)
        return serialize_booking(b)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class CheckOutRequest(BaseModel):
    auto_fulfill: bool = True


@app.post("/api/bookings/{booking_id}/check-out")
def check_out_booking(booking_id: str, req: CheckOutRequest):
    try:
        b = manager.check_out(booking_id, auto_fulfill=req.auto_fulfill)
        return serialize_booking(b)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class CancelBookingRequest(BaseModel):
    cancelled_by: str = "STAFF"
    auto_fulfill: bool = True


@app.post("/api/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str, req: CancelBookingRequest):
    try:
        action, fulfilled = manager.cancel_booking(
            booking_id=booking_id,
            cancelled_by=req.cancelled_by,
            auto_fulfill=req.auto_fulfill,
        )
        fulfilled_bookings = [
            serialize_booking(pair[1] if isinstance(pair, (tuple, list)) else pair)
            for pair in fulfilled
        ]
        return {
            "message": f"Đã hủy đơn {booking_id} thành công.",
            "booking_id": action.booking_id,
            "room_id": action.room_id,
            "fulfilled_waiting_count": len(fulfilled_bookings),
            "fulfilled_entries": fulfilled_bookings,
            "can_undo": not manager.undo._undo_stack.is_empty(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/bookings/undo-last-cancel")
def undo_last_cancel():
    try:
        action, booking = manager.undo_last_cancellation()
        return {
            "message": f"Đã hoàn tác hủy đơn {booking.booking_id} thành công.",
            "booking": serialize_booking(booking),
            "can_undo": not manager.undo._undo_stack.is_empty(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# API Routes: 6. Waiting List (Max-Heap VIP + FIFO Queue Regular)
# ---------------------------------------------------------------------------
@app.get("/api/waiting-list")
def get_waiting_list():
    vip_list = manager.waiting._vip_heap.to_sorted_list()
    regular_list = list(manager.waiting._normal_queue)
    return {
        "vip": [serialize_waiting_entry(e) for e in vip_list],
        "regular": [serialize_waiting_entry(e) for e in regular_list],
        "total_vip": len(vip_list),
        "total_regular": len(regular_list),
    }


class AddWaitingRequest(BaseModel):
    customer_id: str
    room_type: str
    check_in: str
    check_out: str


@app.post("/api/waiting-list")
def add_waiting_entry(req: AddWaitingRequest):
    try:
        d_in = parse_date(req.check_in)
        d_out = parse_date(req.check_out)
        rtype = RoomType(req.room_type)
        entry = manager.add_to_waiting_list(req.customer_id, rtype, d_in, d_out)
        return serialize_waiting_entry(entry)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/waiting-list/process")
def process_waiting(room_type: Optional[str] = None):
    try:
        rtype = RoomType(room_type) if room_type else None
        fulfilled = manager.process_waiting_list(room_type=rtype)
        fulfilled_bookings = [
            serialize_booking(pair[1] if isinstance(pair, (tuple, list)) else pair)
            for pair in fulfilled
        ]
        return {
            "fulfilled_count": len(fulfilled_bookings),
            "fulfilled": fulfilled_bookings,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# API Routes: 7. Service Requests (Max-Heap by Urgency)
# ---------------------------------------------------------------------------
@app.get("/api/services/requests")
def get_service_requests():
    requests = manager.service_requests.all_requests()
    return [serialize_service_request(r) for r in requests]


class CreateServiceRequest(BaseModel):
    room_id: str
    service_type: str
    urgency: Optional[str] = None
    note: str = ""
    customer_id: str = ""


@app.post("/api/services/requests")
def submit_service_request(req: CreateServiceRequest):
    try:
        stype = ServiceType(req.service_type)
        urg = None
        if req.urgency:
            val = str(req.urgency).upper()
            if val in ("CRITICAL", "EMERGENCY", "3"):
                urg = UrgencyLevel.EMERGENCY
            elif val in ("HIGH", "NORMAL", "2"):
                urg = UrgencyLevel.NORMAL
            elif val in ("LOW", "1"):
                urg = UrgencyLevel.LOW
            else:
                try:
                    urg = UrgencyLevel(int(req.urgency))
                except Exception:
                    urg = UrgencyLevel.NORMAL
        r = manager.submit_service_request(
            room_id=req.room_id,
            service_type=stype,
            urgency=urg,
            note=req.note,
            customer_id=req.customer_id,
        )
        return serialize_service_request(r)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/services/requests/process-next")
def process_next_service_request():
    try:
        r = manager.process_next_service_request()
        if not r:
            return {"message": "Không có yêu cầu dịch vụ nào trong hàng chờ.", "request": None}
        return {"message": "Đã xử lý yêu cầu dịch vụ tiếp theo.", "request": serialize_service_request(r)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# API Routes: 8. Payments & Billing (Hash Table + Singly Linked List)
# ---------------------------------------------------------------------------
@app.get("/api/payments")
def get_all_payments():
    txs = manager.all_payments()
    return [serialize_payment(t) for t in txs]


@app.get("/api/payments/calculate/{booking_id}")
def calculate_cost(booking_id: str, extra_fee: float = 0):
    try:
        cost = manager.calculate_booking_cost(booking_id, extra_fee=extra_fee)
        b = cost["booking"]
        c = cost["customer"]
        r = cost["room"]
        return {
            "booking_id": b.booking_id,
            "customer_id": c.customer_id,
            "customer_name": c.full_name,
            "room_id": r.room_id,
            "room_type": r.room_type.value if hasattr(r.room_type, "value") else str(r.room_type),
            "price_per_night": cost["price_per_night"],
            "num_nights": cost["num_nights"],
            "room_charge": cost["room_cost"],
            "service_charge": cost["service_cost"],
            "service_count": len(cost.get("service_items", [])),
            "extra_fee": cost["extra_fee"],
            "vip_level": int(cost["vip_level"]),
            "vip_discount_rate": cost["applied_discount_rate"],
            "vip_discount_amount": cost["discount_amount"],
            "total_amount": cost["total_amount"],
            "paid_amount": cost["paid_amount"],
            "remaining_amount": cost["remaining_amount"],
            "is_paid": cost["is_paid"],
            "customer_total_paid": cost["customer_total_paid"],
            "projected_total_paid": cost["projected_total_paid"],
            "projected_vip_level": int(cost["projected_vip_level"]),
            "will_upgrade_vip": cost["will_upgrade_vip"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class ProcessPaymentRequest(BaseModel):
    booking_id: str
    payment_method: str = "CASH"
    extra_fee: float = 0
    note: str = ""
    auto_check_out: bool = False


@app.post("/api/payments/process")
def process_payment(req: ProcessPaymentRequest):
    try:
        booking = manager.bookings.get_booking(req.booking_id)
        cust_before = manager.customers.get_customer(booking.customer_id)
        old_vip = (
            int(booking.vip_level_at_booking)
            if getattr(booking, "vip_level_at_booking", None) is not None
            else int(cust_before.vip_level)
        )
        tx = manager.process_payment(
            booking_id=req.booking_id,
            payment_method=req.payment_method,
            extra_fee=req.extra_fee,
            note=req.note,
            auto_check_out=req.auto_check_out,
        )
        cust = manager.customers.get_customer(tx.customer_id)
        new_vip = int(cust.vip_level)
        total_paid = manager.customer_total_paid(tx.customer_id)
        data = serialize_payment(tx)
        data.update(
            {
                "previous_vip_level": old_vip,
                "previous_vip_label": VipLevel(old_vip).label,
                "new_vip_level": new_vip,
                "new_vip_label": VipLevel(new_vip).label,
                "vip_upgraded": new_vip > old_vip,
                "customer_total_paid": total_paid,
            }
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class RefundRequest(BaseModel):
    identifier: str
    reason: str = ""


@app.post("/api/payments/refund")
def refund_payment(req: RefundRequest):
    try:
        tx = manager.refund_payment(req.identifier, reason=req.reason)
        data = serialize_payment(tx)
        try:
            cust = manager.customers.get_customer(tx.customer_id)
            data["new_vip_level"] = int(cust.vip_level)
            data["customer_total_paid"] = manager.customer_total_paid(tx.customer_id)
        except Exception:
            pass
        return data
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/payments/lookup")
def lookup_payments(query: str):
    try:
        txs = manager.lookup_payments(query)
        return [serialize_payment(t) for t in txs]
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# API Routes: 9. Reports & Analytics
# ---------------------------------------------------------------------------
@app.get("/api/reports/revenue")
def get_revenue_summary():
    data = manager.reports.revenue_summary()
    # Convert RoomType keys to string
    by_type = {
        (k.value if hasattr(k, "value") else str(k)): v
        for k, v in data["revenue_by_type"].items()
    }
    nights_by_type = {
        (k.value if hasattr(k, "value") else str(k)): v
        for k, v in data["nights_by_type"].items()
    }
    return {
        **data,
        "revenue_by_type": by_type,
        "nights_by_type": nights_by_type,
    }


@app.get("/api/reports/occupancy")
def get_occupancy(target_date: Optional[str] = None):
    d = parse_date(target_date) if target_date else date.today()
    data = manager.reports.occupancy_on(d)
    return {
        "date": d.isoformat(),
        "total_rooms": data["total_rooms"],
        "booked_rooms": data["booked_rooms"],
        "occupancy_rate": data["occupancy_rate"],
        "empty_rooms": data["empty_rooms"],
        "maintenance_rooms": data["maintenance_rooms"],
    }


@app.get("/api/reports/top-customers")
def get_top_customers(k: int = 5):
    top = manager.reports.top_customers(limit=k)
    return [
        {
            "customer": serialize_customer(item["customer"]),
            "booking_count": item["booking_count"],
            "total_nights": item.get("total_nights", 0),
            "total_spent": item["total_spent"],
            "total_paid": item.get("total_paid", 0),
        }
        for item in top
    ]


# ==============================================================================
# PHỤC VỤ TRỰC TIẾP FRONTEND STATIC BUILD (TANGERINE EDITORIAL UI)
# ==============================================================================
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

_backend_dir = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.normpath(os.path.join(_backend_dir, "..", "frontend", "out"))

if os.path.isdir(out_dir):
    next_static_dir = os.path.join(out_dir, "_next")
    if os.path.isdir(next_static_dir):
        app.mount("/_next", StaticFiles(directory=next_static_dir), name="next_static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # 1. Trả về tệp tin trực tiếp nếu tồn tại (favicon.ico, ảnh, etc.)
        file_path = os.path.join(out_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)

        # 2. Trả về index.html bên trong thư mục (vd: rooms/ -> rooms/index.html)
        dir_index = os.path.join(out_dir, full_path, "index.html")
        if os.path.isfile(dir_index):
            return FileResponse(dir_index)

        # 3. Trả về {path}.html nếu truy cập không có gạch chéo
        direct_html = os.path.join(out_dir, f"{full_path}.html")
        if os.path.isfile(direct_html):
            return FileResponse(direct_html)

        # 4. Mặc định trả về trang chủ index.html
        root_index = os.path.join(out_dir, "index.html")
        if os.path.isfile(root_index):
            return FileResponse(root_index)

        raise HTTPException(status_code=404, detail="Frontend file not found")



