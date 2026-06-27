"""Seed deterministic mock e-commerce data for local dev / tests / eval.

English-first per project definition v1. Covers the cases the refund flow and
the 5 intents need: in-window returnable item, out-of-window item, non-returnable
category (e.g. final-sale), high-value item (triggers escalation), delivery
exception, active coupon.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from retailcare.data.db import init_db, session_scope
from retailcare.data.models import (
    Compensation,
    Coupon,
    Order,
    OrderItem,
    Shipment,
    Ticket,
)

NOW = datetime(2026, 6, 16, 12, 0, 0)


def seed(reset: bool = True) -> None:
    # The mock world's "now" is the seed epoch — pin the clock so return-window
    # eligibility is deterministic for tests/eval (clock falls back to wall-clock
    # in production when no mock data is seeded).
    from retailcare import clock
    clock.set_now(NOW)
    init_db()
    with session_scope() as s:
        if reset:
            for model in (Ticket, Compensation, Shipment, OrderItem, Coupon, Order):
                s.query(model).delete()

        # USER u1 — order with one in-window returnable item + one final-sale item
        s.add(Order(order_id="O1001", user_id="u1", status="delivered",
                    currency="USD", total_amount=149.0, created_at=NOW - timedelta(days=10)))
        s.add(OrderItem(item_id="I1", order_id="O1001", sku="SKU-TSHIRT", name="Cotton T-Shirt",
                        category="apparel", price=29.0, qty=1,
                        delivered_at=NOW - timedelta(days=7),
                        returnable_until=NOW + timedelta(days=23)))  # 30-day window, in-window
        s.add(OrderItem(item_id="I2", order_id="O1001", sku="SKU-GIFTCARD", name="Gift Card $120",
                        category="final_sale", price=120.0, qty=1,
                        delivered_at=NOW - timedelta(days=7),
                        returnable_until=None))  # non-returnable
        s.add(Shipment(order_id="O1001", carrier="UPS", tracking_no="1Z999AA10123456784",
                       status="delivered", last_update=NOW - timedelta(days=7),
                       eta=NOW - timedelta(days=7)))

        # USER u2 — out-of-window item + high-value electronics (escalation)
        s.add(Order(order_id="O1002", user_id="u2", status="delivered",
                    currency="USD", total_amount=899.0, created_at=NOW - timedelta(days=60)))
        s.add(OrderItem(item_id="I3", order_id="O1002", sku="SKU-MUG", name="Ceramic Mug",
                        category="home", price=15.0, qty=1,
                        delivered_at=NOW - timedelta(days=55),
                        returnable_until=NOW - timedelta(days=25)))  # out of window
        s.add(OrderItem(item_id="I4", order_id="O1002", sku="SKU-LAPTOP", name="UltraBook 14",
                        category="electronics", price=884.0, qty=1,
                        delivered_at=NOW - timedelta(days=55),
                        returnable_until=NOW + timedelta(days=5)))  # in-window but high-value
        s.add(Shipment(order_id="O1002", carrier="FedEx", tracking_no="7712 3456 7890",
                       status="delivered", last_update=NOW - timedelta(days=55)))

        # USER u3 — shipment in transit with exception (delivery issue intent)
        s.add(Order(order_id="O1003", user_id="u3", status="shipped",
                    currency="USD", total_amount=45.0, created_at=NOW - timedelta(days=3)))
        s.add(OrderItem(item_id="I5", order_id="O1003", sku="SKU-BOOK", name="Paperback Novel",
                        category="books", price=45.0, qty=1))
        s.add(Shipment(order_id="O1003", carrier="USPS", tracking_no="9400 1000 0000",
                       status="exception", last_update=NOW - timedelta(hours=6),
                       eta=NOW + timedelta(days=2)))

        # USER u4 — boundary values around the $200 high-value threshold (RET-003)
        s.add(Order(order_id="O1004", user_id="u4", status="delivered",
                    currency="USD", total_amount=400.0, created_at=NOW - timedelta(days=8)))
        s.add(OrderItem(item_id="I6", order_id="O1004", sku="SKU-HEADPHONE", name="Headphones",
                        category="electronics", price=199.0, qty=1,
                        delivered_at=NOW - timedelta(days=5),
                        returnable_until=NOW + timedelta(days=25)))  # just under threshold
        s.add(OrderItem(item_id="I7", order_id="O1004", sku="SKU-MONITOR", name="27in Monitor",
                        category="electronics", price=201.0, qty=1,
                        delivered_at=NOW - timedelta(days=5),
                        returnable_until=NOW + timedelta(days=25)))  # just over threshold
        s.add(Shipment(order_id="O1004", carrier="UPS", tracking_no="1Z999AA10000000001",
                       status="delivered", last_update=NOW - timedelta(days=5)))

        # USER u4 — perishable (non-returnable) + mid-value apparel (eligible low-value)
        s.add(Order(order_id="O1005", user_id="u4", status="delivered",
                    currency="USD", total_amount=105.0, created_at=NOW - timedelta(days=6)))
        s.add(OrderItem(item_id="I8", order_id="O1005", sku="SKU-COFFEE", name="Fresh Coffee Beans",
                        category="perishable", price=25.0, qty=1,
                        delivered_at=NOW - timedelta(days=4),
                        returnable_until=NOW + timedelta(days=26)))  # perishable -> non-returnable
        s.add(OrderItem(item_id="I9", order_id="O1005", sku="SKU-JACKET", name="Rain Jacket",
                        category="apparel", price=80.0, qty=1,
                        delivered_at=NOW - timedelta(days=4),
                        returnable_until=NOW + timedelta(days=26)))  # eligible low-value
        s.add(Shipment(order_id="O1005", carrier="FedEx", tracking_no="7712 0000 0001",
                       status="delivered", last_update=NOW - timedelta(days=4)))

        # USER u5 — not-yet-delivered order (cannot return) + delivered cheap item
        s.add(Order(order_id="O1006", user_id="u5", status="shipped",
                    currency="USD", total_amount=60.0, created_at=NOW - timedelta(days=2)))
        s.add(OrderItem(item_id="I10", order_id="O1006", sku="SKU-LAMP", name="Desk Lamp",
                        category="home", price=35.0, qty=1,
                        delivered_at=None, returnable_until=None))  # not delivered
        s.add(Shipment(order_id="O1006", carrier="USPS", tracking_no="9400 2000 0001",
                       status="in_transit", last_update=NOW - timedelta(hours=12),
                       eta=NOW + timedelta(days=1)))

        # USER u5 — small electronics for defective (low-value defective -> human, RET-004)
        s.add(Order(order_id="O1007", user_id="u5", status="delivered",
                    currency="USD", total_amount=49.0, created_at=NOW - timedelta(days=9)))
        s.add(OrderItem(item_id="I11", order_id="O1007", sku="SKU-EARBUDS", name="Wireless Earbuds",
                        category="electronics", price=49.0, qty=1,
                        delivered_at=NOW - timedelta(days=6),
                        returnable_until=NOW + timedelta(days=24)))
        s.add(Shipment(order_id="O1007", carrier="UPS", tracking_no="1Z999AA10000000007",
                       status="delivered", last_update=NOW - timedelta(days=6)))

        # coupons
        s.add(Coupon(coupon_id="C1", user_id="u1", code="WELCOME10", kind="percent",
                     value=10.0, status="active", expires_at=NOW + timedelta(days=30)))
        s.add(Coupon(coupon_id="C2", user_id="u2", code="EXPIRED5", kind="fixed",
                     value=5.0, status="expired", expires_at=NOW - timedelta(days=5)))
        s.add(Coupon(coupon_id="C3", user_id="u4", code="SAVE15", kind="percent",
                     value=15.0, status="active", expires_at=NOW + timedelta(days=10)))


if __name__ == "__main__":
    seed()
    print("✅ seeded mock data")
