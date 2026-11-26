"""Cấu hình chung của hệ thống."""

from pathlib import Path

from hotel.models.enums import RoomType, ServiceType, VipLevel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_FILE = PROJECT_ROOT / "data" / "hotel_data.json"

# Sơ đồ khách sạn mặc định: 8 tầng × 10 phòng.
DEFAULT_FLOORS = 8
DEFAULT_ROOMS_PER_FLOOR = 10

# Giá cơ bản / đêm (VND) theo loại phòng; mỗi tầng cao hơn cộng thêm phụ phí.
BASE_PRICE_BY_TYPE = {
    RoomType.SINGLE: 500_000,
    RoomType.DOUBLE: 800_000,
    RoomType.SUITE: 1_500_000,
}
FLOOR_SURCHARGE = 50_000

ROOM_DESCRIPTION_BY_TYPE = {
    RoomType.SINGLE: "1 giường đơn, phòng tắm riêng, Wi-Fi",
    RoomType.DOUBLE: "1 giường đôi hoặc 2 giường đơn, TV, minibar",
    RoomType.SUITE: "Phòng khách riêng, bồn tắm, view thành phố",
}

# Đơn giá dịch vụ nội bộ phát sinh (VND / lượt) dùng khi tính tổng chi phí thanh toán.
SERVICE_PRICE_BY_TYPE = {
    ServiceType.CLEANING: 50_000,
    ServiceType.FOOD: 150_000,
    ServiceType.MEDICAL: 200_000,
    ServiceType.OTHER: 100_000,
}

# Tỷ lệ chiết khấu / giảm giá theo hạng VIP khi thanh toán hóa đơn.
VIP_DISCOUNT_RATES = {
    VipLevel.NORMAL: 0.0,
    VipLevel.SILVER: 0.03,
    VipLevel.GOLD: 0.05,
    VipLevel.PLATINUM: 0.10,
}

# Mốc tổng số tiền đã thanh toán tích lũy (VND) để tự động xét và nâng hạng VIP.
VIP_SPENDING_THRESHOLDS = {
    VipLevel.NORMAL: 0,
    VipLevel.SILVER: 3_000_000,
    VipLevel.GOLD: 8_000_000,
    VipLevel.PLATINUM: 15_000_000,
}


def evaluate_vip_level_by_spending(total_paid):
    """Xác định hạng VIP tương ứng với tổng số tiền đã thanh toán tích lũy (VND)."""
    paid = max(0, int(total_paid or 0))
    if paid >= VIP_SPENDING_THRESHOLDS[VipLevel.PLATINUM]:
        return VipLevel.PLATINUM
    if paid >= VIP_SPENDING_THRESHOLDS[VipLevel.GOLD]:
        return VipLevel.GOLD
    if paid >= VIP_SPENDING_THRESHOLDS[VipLevel.SILVER]:
        return VipLevel.SILVER
    return VipLevel.NORMAL


def get_vip_tier_progress(current_vip, total_paid):
    """Tính tiến độ tích lũy chi tiêu và số tiền còn thiếu để lên hạng VIP tiếp theo."""
    vip = VipLevel(int(current_vip))
    paid = max(0, int(total_paid or 0))
    earned_vip = evaluate_vip_level_by_spending(paid)
    effective_vip = VipLevel(max(int(vip), int(earned_vip)))

    next_vip = None
    next_threshold = None
    amount_to_next_vip = 0
    progress_percent = 100.0

    if effective_vip < VipLevel.PLATINUM:
        next_vip = VipLevel(int(effective_vip) + 1)
        next_threshold = VIP_SPENDING_THRESHOLDS[next_vip]
        current_floor = VIP_SPENDING_THRESHOLDS[effective_vip]
        amount_to_next_vip = max(0, next_threshold - paid)
        span = max(1, next_threshold - current_floor)
        if paid <= current_floor:
            progress_percent = round(min(100.0, (paid / max(1, next_threshold)) * 100.0), 1)
        else:
            progress_percent = round(min(100.0, ((paid - current_floor) / span) * 100.0), 1)

    return {
        "current_vip": vip,
        "earned_vip": earned_vip,
        "effective_vip": effective_vip,
        "total_paid": paid,
        "discount_rate": VIP_DISCOUNT_RATES.get(vip, 0.0),
        "next_vip": next_vip,
        "next_threshold": next_threshold,
        "amount_to_next_vip": amount_to_next_vip,
        "progress_percent": progress_percent,
    }


# Giới hạn nghiệp vụ.
MAX_STAY_NIGHTS = 30
