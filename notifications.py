"""
Notification service for Fresh Go.
Sends alerts to admin (new orders) and customers (status changes).
"""

import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_FB_ID     = os.getenv("ADMIN_FB_ID", "")
ADMIN_WA_PHONE  = os.getenv("ADMIN_WHATSAPP_PHONE", "")
BASE_URL        = os.getenv("BASE_URL", "http://localhost:8000")


# ── Admin Notifications ───────────────────────────────────────────────────────

def notify_admin_new_order(order_id: str, name: str, product: str,
                            quantity: str, address: str, platform: str):
    """Alert admin via Facebook and/or WhatsApp when a new order arrives."""
    msg = (
        f"🆕 New Order #{order_id}!\n\n"
        f"👤 Customer: {name}\n"
        f"🛒 {product} — {quantity}\n"
        f"📍 {address}\n"
        f"📱 via {platform.title()}\n\n"
        f"👉 Dashboard: {BASE_URL}/dashboard"
    )
    _send_fb(ADMIN_FB_ID, msg)
    _send_wa(ADMIN_WA_PHONE, msg)


def notify_admin_payment(order_id: str, name: str, amount: str):
    """Alert admin when a customer claims payment."""
    msg = (
        f"💰 Payment Claimed — Order #{order_id}\n\n"
        f"👤 {name}\n"
        f"💵 Amount: {amount}\n\n"
        f"Verify & mark paid: {BASE_URL}/dashboard"
    )
    _send_fb(ADMIN_FB_ID, msg)
    _send_wa(ADMIN_WA_PHONE, msg)


# ── Customer Notifications ────────────────────────────────────────────────────

_STATUS_MSGS = {
    "confirmed": (
        "✅ Your order #{id} has been confirmed!\n"
        "Our team will deliver today between 11 AM – 5 PM. — Fresh Go 🐄"
    ),
    "delivered": (
        "🎉 Your order #{id} has been delivered! Thank you for choosing Fresh Go. 🙏\n"
        "To place another order, just type 'order'. — Fresh Go 🐄"
    ),
    "cancelled": (
        "❌ Your order #{id} has been cancelled.\n"
        "For any concerns, please WhatsApp us: 0300-3147887 — Fresh Go 🐄"
    ),
    "paid": (
        "✅ Payment received for order #{id}! 🎉\n"
        "Thank you — Fresh Go 🐄"
    ),
}


def notify_customer_status(customer_id: str, order_id: str,
                            status: str, platform: str):
    """Send order status update to the customer on their original platform."""
    template = _STATUS_MSGS.get(status)
    if not template:
        return
    msg = template.format(id=order_id)

    if platform == "facebook":
        _send_fb(customer_id, msg)
    elif platform == "whatsapp":
        _send_wa(customer_id, msg)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _send_fb(recipient_id: str, text: str):
    if not recipient_id:
        return
    try:
        from facebook import send_message
        send_message(recipient_id, text)
    except Exception as e:
        print(f"[Notify FB Error] {e}")


def _send_wa(phone: str, text: str):
    if not phone:
        return
    try:
        from whatsapp import send_whatsapp_message
        send_whatsapp_message(phone, text)
    except Exception as e:
        print(f"[Notify WA Error] {e}")
