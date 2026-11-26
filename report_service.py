"""Chức năng mở rộng: Thống kê doanh thu, tỷ lệ lấp đầy và top khách hàng."""

from datetime import date

from hotel.algorithms.merge_sort import merge_sort
from hotel.models.enums import BookingStatus, RoomStatus, RoomType


class ReportService:
    def __init__(self, room_service, customer_service, booking_service, payment_service=None):
        self._room_service = room_service
        self._customer_service = customer_service
        self._booking_service = booking_service
        self._payment_service = payment_service

    def revenue_summary(self):
        """Thống kê doanh thu tổng, theo loại phòng và theo tháng (YYYY-MM).

        Chỉ tính các đơn không bị hủy (CONFIRMED, CHECKED_IN, CHECKED_OUT).
        """
        by_type = {rtype: 0 for rtype in RoomType}
        nights_by_type = {rtype: 0 for rtype in RoomType}
        by_month = {}
        realized_revenue = 0      # Đã nhận/trả phòng (CHECKED_IN + CHECKED_OUT)
        confirmed_revenue = 0     # Đã xác nhận (CONFIRMED)
        active_count = 0
        cancelled_count = 0

        for booking in self._booking_service.all_bookings():
            if booking.status == BookingStatus.CANCELLED:
                cancelled_count += 1
                continue
            active_count += 1
            amount = booking.total_price
            if booking.status in (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT):
                realized_revenue += amount
            else:
                confirmed_revenue += amount

            room = self._room_service.get_room(booking.room_id)
            by_type[room.room_type] += amount
            nights_by_type[room.room_type] += booking.num_nights

            month_key = booking.check_in.strftime("%Y-%m")
            by_month[month_key] = by_month.get(month_key, 0) + amount

        sorted_months = merge_sort(list(by_month.items()), key=lambda kv: kv[0])
        return {
            "total_revenue": realized_revenue + confirmed_revenue,
            "realized_revenue": realized_revenue,
            "confirmed_revenue": confirmed_revenue,
            "active_bookings": active_count,
            "cancelled_bookings": cancelled_count,
            "revenue_by_type": by_type,
            "nights_by_type": nights_by_type,
            "revenue_by_month": sorted_months,
        }

    def occupancy_on(self, target_date=None):
        """Tỷ lệ lấp đầy phòng tại một ngày cụ thể."""
        on_date = target_date or date.today()
        rooms = self._room_service.all_rooms()
        total = len(rooms)
        booked = 0
        maintenance = 0
        empty = 0

        for room in rooms:
            status = self._booking_service.room_status_on(room.room_id, on_date)
            if status == RoomStatus.BOOKED:
                booked += 1
            elif status == RoomStatus.MAINTENANCE:
                maintenance += 1
            else:
                empty += 1

        bookable = max(1, total - maintenance)
        return {
            "date": on_date,
            "total_rooms": total,
            "booked_rooms": booked,
            "empty_rooms": empty,
            "maintenance_rooms": maintenance,
            "occupancy_rate": round((booked / total) * 100.0, 2) if total else 0.0,
            "effective_occupancy_rate": round((booked / bookable) * 100.0, 2),
        }

    def top_customers(self, limit=5):
        """Top khách hàng theo tổng chi tiêu và số đêm lưu trú (sắp bằng Merge Sort)."""
        stats = []
        for customer in self._customer_service.all_customers():
            history = customer.history.to_list()
            active = [b for b in history if b.status != BookingStatus.CANCELLED]
            total_spent = sum(b.total_price for b in active)
            total_nights = sum(b.num_nights for b in active)
            if self._payment_service is not None:
                try:
                    self._payment_service.sync_customer_vip(customer.customer_id, allow_downgrade=False)
                except Exception:
                    pass
                total_paid = self._payment_service.get_customer_total_paid(customer.customer_id)
            else:
                try:
                    self._customer_service.evaluate_and_update_vip(
                        customer.customer_id, total_spent, allow_downgrade=False
                    )
                except Exception:
                    pass
                total_paid = total_spent
            stats.append(
                {
                    "customer": customer,
                    "booking_count": len(active),
                    "total_nights": total_nights,
                    "total_spent": total_spent,
                    "total_paid": total_paid,
                }
            )
        ranked = merge_sort(
            stats,
            key=lambda item: (item["total_spent"], item["total_nights"], item["booking_count"]),
            reverse=True,
        )
        return ranked[: max(0, limit)]
