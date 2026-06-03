"""
Multi-step order capture flow for Fresh Go.
Supports Facebook and WhatsApp platforms.
Persists orders to SQLite via database.py.
Notifies admin on new orders.
"""

from datetime import datetime

from database import save_order, get_all_orders, get_orders_by_customer

ORDER_KEYWORDS = {
    "order", "khareedna", "lena hai", "chahiye", "mangwana",
    "book", "delivery chahiye", "order karna", "doodh chahiye",
    "ghee chahiye", "milk order", "buy", "purchase"
}

HISTORY_KEYWORDS = {"my orders", "meri orders", "mera order", "order history",
                    "purane orders", "check order", "order status"}

# Active orders in-progress: {user_id: {step, data, platform}}
_active_orders: dict = {}

STEPS = ["product", "quantity", "name", "address", "payment", "confirm"]

PAYMENT_INFO = (
    "💳 Payment Options:\n"
    "━━━━━━━━━━━━━━━━\n"
    "1️⃣  JazzCash: 0300-3147887\n"
    "2️⃣  EasyPaisa: 0300-3147887\n"
    "3️⃣  Cash on Delivery (COD)\n\n"
    "Payment method batain (1, 2 ya 3) — Fresh Go 🐄"
)

PAYMENT_MAP = {
    "1": "JazzCash", "jazzcash": "JazzCash", "jazz": "JazzCash",
    "2": "EasyPaisa", "easypaisa": "EasyPaisa", "easy": "EasyPaisa",
    "3": "COD", "cod": "COD", "cash": "COD", "cash on delivery": "COD",
}


# ── Public API ────────────────────────────────────────────────────────────────

def has_active_order(user_id: str) -> bool:
    return user_id in _active_orders


def is_order_intent(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in ORDER_KEYWORDS)


def is_history_intent(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in HISTORY_KEYWORDS)


def start_order(user_id: str, platform: str = "facebook") -> str:
    _active_orders[user_id] = {"step": "product", "data": {}, "platform": platform}
    return (
        "Zaroor! 🛒 Aap kya lena chahte hain?\n\n"
        "1️⃣  Doodh (Rs. 250/litre)\n"
        "2️⃣  Desi Ghee\n"
        "3️⃣  Dono (Doodh + Ghee)\n\n"
        "1, 2 ya 3 reply karen 😊 — Fresh Go 🐄"
    )


def get_customer_order_history(user_id: str) -> str:
    """Return a formatted string of this customer's past orders."""
    orders = get_orders_by_customer(user_id)
    if not orders:
        return (
            "Aap ne abhi tak koi order nahi diya 🛒\n"
            "'order' type karen nayi order ke liye! — Fresh Go 🐄"
        )
    lines = [f"📦 Aap ke orders ({len(orders)} total):\n"]
    for o in orders[:5]:
        status_emoji = {"pending": "⏳", "confirmed": "✅",
                        "delivered": "🎉", "cancelled": "❌"}.get(o["status"], "📦")
        lines.append(
            f"{status_emoji} #{o['order_id']} — {o['product']} ({o['quantity']})\n"
            f"   📍 {o['address']} | {o['timestamp']}"
        )
    lines.append("\nDobara order: 'order' type karen — Fresh Go 🐄")
    return "\n".join(lines)


def handle_order_step(user_id: str, text: str) -> str:
    order    = _active_orders[user_id]
    step     = order["step"]
    data     = order["data"]
    platform = order.get("platform", "facebook")
    t        = text.strip()

    if t.lower() in {"cancel", "band karo", "nahi", "chor do", "stop"}:
        del _active_orders[user_id]
        return "Order cancel ho gaya. Jab chahein dobara try karen! — Fresh Go 🐄"

    # ── Product ───────────────────────────────────────────────────────────────
    if step == "product":
        if t in {"1", "doodh", "milk", "doodh chahiye"}:
            data["product"] = "Doodh (Milk)"
        elif t in {"2", "ghee", "desi ghee"}:
            data["product"] = "Desi Ghee"
        elif t in {"3", "dono", "both", "doodh aur ghee"}:
            data["product"] = "Doodh + Desi Ghee"
        else:
            return "Sirf 1, 2 ya 3 type karen please 🙏 — Fresh Go 🐄"
        order["step"] = "quantity"
        if "Ghee" in data["product"] and "Doodh" not in data["product"]:
            return f"Kitna {data['product']} chahiye? (e.g. 1 kg) — Fresh Go 🐄"
        return "Kitna doodh chahiye? (e.g. 2 litre) — Fresh Go 🐄"

    # ── Quantity ──────────────────────────────────────────────────────────────
    elif step == "quantity":
        if len(t) < 1 or len(t) > 30:
            return "Quantity wazahat se batain, e.g. 2 litre ya 1 kg — Fresh Go 🐄"
        data["quantity"] = t
        order["step"]    = "name"
        return "Apna naam batain please? — Fresh Go 🐄"

    # ── Name ──────────────────────────────────────────────────────────────────
    elif step == "name":
        if len(t) < 2:
            return "Apna poora naam batain 🙏 — Fresh Go 🐄"
        data["name"]  = t
        order["step"] = "address"
        return "Delivery address kya hoga? (mohalla, area, Lahore) — Fresh Go 🐄"

    # ── Address ───────────────────────────────────────────────────────────────
    elif step == "address":
        if len(t) < 5:
            return "Thoda detail mein address batain taake delivery sahi jagah ho 🙏 — Fresh Go 🐄"
        data["address"] = t
        order["step"]   = "payment"
        return PAYMENT_INFO

    # ── Payment ───────────────────────────────────────────────────────────────
    elif step == "payment":
        method = PAYMENT_MAP.get(t.lower())
        if not method:
            return "1 (JazzCash), 2 (EasyPaisa) ya 3 (COD) type karen 🙏 — Fresh Go 🐄"
        data["payment"] = method
        order["step"]   = "confirm"

        total = _estimate_total(data)
        data["total"] = total

        payment_note = ""
        if method in ("JazzCash", "EasyPaisa"):
            payment_note = f"\n💳 Payment: {method} — 0300-3147887\n   (Order ke baad transfer karen)"
        else:
            payment_note = "\n💵 Payment: Cash on Delivery"

        summary = (
            f"📋 Order Summary:\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 Naam:       {data['name']}\n"
            f"🛒 Product:    {data['product']}\n"
            f"📦 Quantity:   {data['quantity']}\n"
            f"📍 Address:    {data['address']}\n"
            f"💰 Est. Total: {total}\n"
            f"🕐 Delivery:   Subah 11 se Sham 5{payment_note}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Confirm karna hai? (yes / no) — Fresh Go 🐄"
        )
        return summary

    # ── Confirm ───────────────────────────────────────────────────────────────
    elif step == "confirm":
        if t.lower() in {"yes", "haan", "ha", "confirm", "ok", "theek hai", "ji"}:
            order_id = save_order(data, platform=platform, customer_id=user_id)
            del _active_orders[user_id]

            # Notify admin asynchronously (fire-and-forget)
            _fire_notify(order_id, data, platform)

            payment_instr = ""
            if data.get("payment") in ("JazzCash", "EasyPaisa"):
                payment_instr = (
                    f"\n\n💳 Payment Instructions:\n"
                    f"{data['payment']} number: 0300-3147887\n"
                    f"Amount: {data.get('total', 'confirm karen')}\n"
                    f"Screenshot WhatsApp karen: 0300-3147887"
                )

            return (
                f"✅ Order confirm ho gaya! Order #{order_id}\n\n"
                f"Shukriya {data['name']} bhai/behen! 🎉\n"
                f"Delivery: Subah 11 se Sham 5 baje ke darmiyan.{payment_instr}\n\n"
                f"Order track: 'my orders' type karen — Fresh Go 🐄"
            )
        elif t.lower() in {"no", "nahi", "na", "cancel"}:
            del _active_orders[user_id]
            return "Order cancel ho gaya. Dobara: 'order' type karen 😊 — Fresh Go 🐄"
        else:
            return "Sirf yes ya no type karen please 🙏 — Fresh Go 🐄"

    return "Kuch masla hua. Dobara try karen ya 0300-3147887 pe WhatsApp karen. — Fresh Go 🐄"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _estimate_total(data: dict) -> str:
    product  = data.get("product", "")
    quantity = data.get("quantity", "").lower()
    try:
        num = float("".join(c for c in quantity if c.isdigit() or c == ".") or "0")
    except Exception:
        num = 0

    if "Doodh" in product and "Ghee" not in product:
        total = int(num * 250)
        return f"Rs. {total}" if total > 0 else "0300-3147887 pe confirm karen"
    elif "Ghee" in product and "Doodh" not in product:
        return "0300-3147887 pe ghee ki price confirm karen"
    else:
        milk_total = int(num * 250) if num > 0 else 0
        return f"Rs. {milk_total}+ (ghee price alag)"


def _fire_notify(order_id: str, data: dict, platform: str):
    """Non-blocking admin notification — best-effort."""
    try:
        from notifications import notify_admin_new_order
        import threading
        threading.Thread(
            target=notify_admin_new_order,
            args=(order_id, data.get("name", "?"), data.get("product", "?"),
                  data.get("quantity", "?"), data.get("address", "?"), platform),
            daemon=True
        ).start()
    except Exception as e:
        print(f"[Notify Error] {e}")
