"""
Structured order capture flow for Fresh Go.

Steps:
  1. Detect order intent  →  ask product choice
  2. Customer picks product  →  ask quantity
  3. Customer gives quantity  →  ask name
  4. Customer gives name      →  ask address
  5. Customer gives address   →  show summary + confirm
  6. Customer confirms        →  save order + thank you

Orders saved to orders.json
"""

import json
import os
from datetime import datetime

ORDERS_FILE = os.path.join(os.path.dirname(__file__), "orders.json")

# Keywords that trigger order flow (Roman Urdu + English)
ORDER_KEYWORDS = {
    "order", "khareedna", "lena hai", "chahiye", "mangwana",
    "book", "delivery chahiye", "order karna", "doodh chahiye",
    "ghee chahiye", "milk order", "buy", "purchase"
}

# Active orders in progress: {user_id: {step, data}}
_active_orders: dict = {}

STEPS = ["product", "quantity", "name", "address", "confirm"]


# ── Public API ────────────────────────────────────────────────────────────────

def has_active_order(user_id: str) -> bool:
    return user_id in _active_orders


def is_order_intent(text: str) -> bool:
    """Check if message contains order-related keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in ORDER_KEYWORDS)


def start_order(user_id: str) -> str:
    """Kick off the order flow. Returns the first question."""
    _active_orders[user_id] = {"step": "product", "data": {}}
    return (
        "Zaroor! 🛒 Aap kya lena chahte hain?\n\n"
        "1️⃣  Doodh (Rs. 250/litre)\n"
        "2️⃣  Desi Ghee\n"
        "3️⃣  Dono (Doodh + Ghee)\n\n"
        "1, 2 ya 3 reply karen 😊 — Fresh Go 🐄"
    )


def handle_order_step(user_id: str, text: str) -> str:
    """
    Process the current order step.
    Returns the next question or final confirmation message.
    """
    order   = _active_orders[user_id]
    step    = order["step"]
    data    = order["data"]
    t       = text.strip()

    # ── Allow cancel at any point ──
    if t.lower() in {"cancel", "band karo", "nahi", "chor do", "stop"}:
        del _active_orders[user_id]
        return "Order cancel ho gaya. Jab chahein dobara try karen! — Fresh Go 🐄"

    # ── Step: Product ──────────────────────────────────────────────────────────
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
        product = data["product"]
        if "Ghee" in product and "Doodh" not in product:
            return f"Kitna {product} chahiye? (example: 1 kg) — Fresh Go 🐄"
        return f"Kitna doodh chahiye? (example: 2 litre) — Fresh Go 🐄"

    # ── Step: Quantity ─────────────────────────────────────────────────────────
    elif step == "quantity":
        if len(t) < 1 or len(t) > 30:
            return "Quantity thodi wazahat se batain, example: 2 litre ya 1 kg — Fresh Go 🐄"
        data["quantity"] = t
        order["step"]    = "name"
        return "Apna naam batain please? — Fresh Go 🐄"

    # ── Step: Name ────────────────────────────────────────────────────────────
    elif step == "name":
        if len(t) < 2:
            return "Apna poora naam batain 🙏 — Fresh Go 🐄"
        data["name"]  = t
        order["step"] = "address"
        return "Delivery address kya hoga? (mohalla, area, Lahore) — Fresh Go 🐄"

    # ── Step: Address ─────────────────────────────────────────────────────────
    elif step == "address":
        if len(t) < 5:
            return "Thoda detail mein address batain taake delivery sahi jagah ho 🙏 — Fresh Go 🐄"
        data["address"] = t
        order["step"]   = "confirm"

        # Calculate estimated total
        total = _estimate_total(data)

        summary = (
            f"📋 Order Summary:\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 Naam:     {data['name']}\n"
            f"🛒 Product:  {data['product']}\n"
            f"📦 Quantity: {data['quantity']}\n"
            f"📍 Address:  {data['address']}\n"
            f"💰 Est. Total: {total}\n"
            f"🕐 Delivery: Subah 11 baje se sham 5 baje tak\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Confirm karna hai? (yes / no) — Fresh Go 🐄"
        )
        return summary

    # ── Step: Confirm ─────────────────────────────────────────────────────────
    elif step == "confirm":
        if t.lower() in {"yes", "haan", "ha", "confirm", "ok", "theek hai", "ji"}:
            order_id = _save_order(data)
            del _active_orders[user_id]
            return (
                f"✅ Order confirm ho gaya! Order #{order_id}\n\n"
                f"Shukriya {data['name']} bhai/behen! 🎉\n"
                f"Hamari team subah 11 se sham 5 baje ke darmiyan deliver karegi.\n"
                f"Koi masla ho to WhatsApp karen: 0300-3147887 — Fresh Go 🐄"
            )
        elif t.lower() in {"no", "nahi", "na", "cancel"}:
            del _active_orders[user_id]
            return "Order cancel ho gaya. Dobara order karne ke liye 'order' type karen 😊 — Fresh Go 🐄"
        else:
            return "Sirf yes ya no type karen please 🙏 — Fresh Go 🐄"

    return "Kuch masla hua. Dobara try karen ya 0300-3147887 pe WhatsApp karen. — Fresh Go 🐄"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _estimate_total(data: dict) -> str:
    """Simple price estimate based on product and quantity."""
    product  = data.get("product", "")
    quantity = data.get("quantity", "").lower()

    try:
        # Extract number from quantity string
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
        return f"Rs. {milk_total}+ (ghee price alag hoga)"


def _save_order(data: dict) -> str:
    """Save order to orders.json and return order ID."""
    orders = []
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r") as f:
                orders = json.load(f)
        except Exception:
            orders = []

    order_id = f"FG{len(orders) + 1:04d}"
    orders.append({
        "order_id":  order_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "name":      data.get("name"),
        "product":   data.get("product"),
        "quantity":  data.get("quantity"),
        "address":   data.get("address"),
        "status":    "pending"
    })

    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)

    print(f"[Order] Saved #{order_id} — {data.get('name')} — {data.get('product')}")
    return order_id


def get_all_orders() -> list:
    """Return all saved orders (for admin review)."""
    if not os.path.exists(ORDERS_FILE):
        return []
    with open(ORDERS_FILE, "r") as f:
        return json.load(f)
