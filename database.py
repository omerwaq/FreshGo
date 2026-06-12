"""
SQLite database layer for Fresh Go.
Tables: orders, conversations, scheduled_posts
Automatically migrates existing orders.json on first run.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "freshgo.db")
ORDERS_JSON = os.path.join(os.path.dirname(__file__), "orders.json")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        TEXT    UNIQUE NOT NULL,
            timestamp       TEXT    NOT NULL,
            platform        TEXT    DEFAULT 'facebook',
            customer_id     TEXT,
            name            TEXT,
            product         TEXT,
            quantity        TEXT,
            address         TEXT,
            status          TEXT    DEFAULT 'pending',
            payment_status  TEXT    DEFAULT 'unpaid',
            payment_method  TEXT,
            total_amount    TEXT,
            notes           TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            user_id      TEXT NOT NULL,
            platform     TEXT NOT NULL DEFAULT 'facebook',
            messages     TEXT DEFAULT '[]',
            last_updated TEXT,
            PRIMARY KEY (user_id, platform)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            topic          TEXT,
            post_text      TEXT,
            image_path     TEXT,
            video_path     TEXT,
            platform       TEXT    DEFAULT 'facebook',
            post_type      TEXT    DEFAULT 'image',
            scheduled_time TEXT    NOT NULL,
            status         TEXT    DEFAULT 'pending',
            created_at     TEXT,
            published_at   TEXT,
            error_msg      TEXT
        )
    """)

    # Add phone column if missing (migration for existing DBs)
    try:
        c.execute("ALTER TABLE orders ADD COLUMN phone TEXT")
        conn.commit()
    except Exception:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            full_name  TEXT DEFAULT '',
            role       TEXT DEFAULT 'staff',
            is_active  INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Brand assets stored as base64 so they survive Railway filesystem resets
    c.execute("""
        CREATE TABLE IF NOT EXISTS brand_assets (
            key        TEXT PRIMARY KEY,
            data_b64   TEXT NOT NULL,
            ext        TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()

    _migrate_orders_json()
    print("[DB] Database ready ✅")


def _migrate_orders_json():
    """Import orders.json into SQLite if not already done."""
    if not os.path.exists(ORDERS_JSON):
        return
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders")
    if c.fetchone()[0] > 0:
        conn.close()
        return  # Already migrated

    try:
        with open(ORDERS_JSON) as f:
            orders = json.load(f)
        for o in orders:
            c.execute("""
                INSERT OR IGNORE INTO orders
                (order_id, timestamp, name, product, quantity, address, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (o.get("order_id"), o.get("timestamp"), o.get("name"),
                  o.get("product"), o.get("quantity"), o.get("address"),
                  o.get("status", "pending")))
        conn.commit()
        print(f"[DB] Migrated {len(orders)} orders from orders.json ✅")
    except Exception as e:
        print(f"[DB Migration Warning] {e}")
    finally:
        conn.close()


# ── Orders ────────────────────────────────────────────────────────────────────

def save_order(data: dict, platform: str = "facebook", customer_id: str = None) -> str:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders")
    count = c.fetchone()[0]
    order_id = f"FG{count + 1:04d}"

    c.execute("""
        INSERT INTO orders
        (order_id, timestamp, platform, customer_id, name, product, quantity, address,
         status, payment_status, total_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'unpaid', ?)
    """, (
        order_id,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        platform, customer_id,
        data.get("name"), data.get("product"),
        data.get("quantity"), data.get("address"),
        data.get("total", "")
    ))
    conn.commit()
    conn.close()
    return order_id


def get_all_orders(limit: int = None, status_filter: str = None) -> list:
    conn = get_conn()
    c = conn.cursor()
    if status_filter and status_filter != "all":
        q = "SELECT * FROM orders WHERE status = ? ORDER BY id DESC"
        params = (status_filter,) if not limit else (status_filter,)
        if limit:
            q += " LIMIT ?"
            params = (status_filter, limit)
        c.execute(q, params)
    else:
        if limit:
            c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
        else:
            c.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_orders_by_customer(customer_id: str) -> list:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC", (customer_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_order(order_id: str) -> dict | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_order_status(order_id: str, status: str,
                        payment_status: str = None, notes: str = None) -> bool:
    conn = get_conn()
    c = conn.cursor()
    if payment_status and notes:
        c.execute(
            "UPDATE orders SET status=?, payment_status=?, notes=? WHERE order_id=?",
            (status, payment_status, notes, order_id)
        )
    elif payment_status:
        c.execute(
            "UPDATE orders SET status=?, payment_status=? WHERE order_id=?",
            (status, payment_status, order_id)
        )
    elif notes:
        c.execute(
            "UPDATE orders SET status=?, notes=? WHERE order_id=?",
            (status, notes, order_id)
        )
    else:
        c.execute("UPDATE orders SET status=? WHERE order_id=?", (status, order_id))
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_todays_customers() -> list:
    """Get all orders from today with name, phone, product, address."""
    conn = get_conn()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute(
        "SELECT order_id, name, phone, product, quantity, address, customer_id, platform "
        "FROM orders WHERE timestamp LIKE ? ORDER BY id DESC",
        (f"{today}%",)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    # For WhatsApp orders, customer_id is the phone number
    for row in rows:
        if not row.get("phone") and row.get("platform") == "whatsapp":
            row["phone"] = row.get("customer_id", "")
    return rows


def get_unpaid_customers() -> list:
    """
    Return one row per customer with unpaid orders.
    Includes each order's date, product, quantity, and amount.
    """
    conn = get_conn()
    c = conn.cursor()

    # Get individual unpaid orders
    c.execute("""
        SELECT name, phone, customer_id, platform,
               order_id, timestamp, product, quantity, total_amount
        FROM orders
        WHERE payment_status IN ('unpaid', 'pending', '')
          AND status NOT IN ('cancelled')
        ORDER BY COALESCE(NULLIF(phone,''), customer_id), timestamp ASC
    """)
    orders = [dict(r) for r in c.fetchall()]
    conn.close()

    # Group by customer
    grouped = {}
    for o in orders:
        key = o.get("phone") or o.get("customer_id") or o.get("name", "unknown")
        if o.get("platform") == "whatsapp" and not o.get("phone"):
            o["phone"] = o.get("customer_id", "")
        if key not in grouped:
            grouped[key] = {
                "name":        o["name"],
                "phone":       o.get("phone") or o.get("customer_id", ""),
                "platform":    o["platform"],
                "orders":      [],
                "total_due":   0,
            }
        # Format date: "Mon, 9 Jun"
        try:
            from datetime import datetime as dt
            d = dt.strptime(o["timestamp"][:10], "%Y-%m-%d")
            date_str = d.strftime("%a, %-d %b")
        except Exception:
            date_str = o["timestamp"][:10]

        amount = 0
        try:
            raw = str(o.get("total_amount") or "").strip()
            amount = int(float(raw)) if raw else 0
        except Exception:
            pass

        grouped[key]["orders"].append({
            "order_id": o["order_id"],
            "date":     date_str,
            "product":  o.get("product", ""),
            "quantity": o.get("quantity", ""),
            "amount":   amount,
        })
        grouped[key]["total_due"] += amount

    result = list(grouped.values())
    result.sort(key=lambda x: x["total_due"], reverse=True)
    return result


def get_stats() -> dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='confirmed'")
    confirmed = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='delivered'")
    delivered = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE payment_status='paid'")
    paid = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='cancelled'")
    cancelled = c.fetchone()[0]
    conn.close()
    return {
        "total": total, "pending": pending, "confirmed": confirmed,
        "delivered": delivered, "paid": paid, "cancelled": cancelled
    }


# ── Conversations ─────────────────────────────────────────────────────────────

def get_conversation(user_id: str, platform: str = "facebook") -> list:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT messages FROM conversations WHERE user_id=? AND platform=?",
        (user_id, platform)
    )
    row = c.fetchone()
    conn.close()
    return json.loads(row["messages"]) if row else []


def save_conversation(user_id: str, messages: list, platform: str = "facebook"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO conversations (user_id, platform, messages, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, platform) DO UPDATE SET
            messages=excluded.messages,
            last_updated=excluded.last_updated
    """, (user_id, platform, json.dumps(messages, ensure_ascii=False),
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


# ── Scheduled Posts ───────────────────────────────────────────────────────────

def create_scheduled_post(topic: str, post_text: str, image_path: str,
                           video_path: str, platform: str, post_type: str,
                           scheduled_time: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO scheduled_posts
        (topic, post_text, image_path, video_path, platform, post_type,
         scheduled_time, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (topic, post_text, image_path, video_path, platform, post_type,
          scheduled_time, datetime.now().isoformat()))
    post_id = c.lastrowid
    conn.commit()
    conn.close()
    return post_id


def get_pending_scheduled_posts() -> list:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM scheduled_posts
        WHERE status='pending' AND scheduled_time <= ?
        ORDER BY scheduled_time ASC
    """, (now,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_all_scheduled_posts() -> list:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM scheduled_posts ORDER BY scheduled_time DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def update_scheduled_post_status(post_id: int, status: str, error_msg: str = None):
    conn = get_conn()
    c = conn.cursor()
    published_at = datetime.now().isoformat() if status == "published" else None
    c.execute(
        "UPDATE scheduled_posts SET status=?, published_at=?, error_msg=? WHERE id=?",
        (status, published_at, error_msg, post_id)
    )
    conn.commit()
    conn.close()


def delete_scheduled_post(post_id: int) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM scheduled_posts WHERE id=? AND status='pending'", (post_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ── Admin Users ───────────────────────────────────────────────────────────────

def get_all_admin_users() -> list:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, role, is_active, created_at FROM admin_users ORDER BY created_at")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_admin_user_by_username(username: str) -> dict | None:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM admin_users WHERE username=? AND is_active=1", (username,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def create_admin_user(username: str, password: str, full_name: str, role: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO admin_users (username, password, full_name, role) VALUES (?,?,?,?)",
        (username.strip().lower(), password, full_name.strip(), role)
    )
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return user_id


def delete_admin_user(user_id: int) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM admin_users WHERE id=?", (user_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def update_admin_user(user_id: int, full_name: str | None, password: str | None, role: str | None):
    conn = get_conn()
    c = conn.cursor()
    if full_name is not None:
        c.execute("UPDATE admin_users SET full_name=? WHERE id=?", (full_name, user_id))
    if password is not None:
        c.execute("UPDATE admin_users SET password=? WHERE id=?", (password, user_id))
    if role is not None:
        c.execute("UPDATE admin_users SET role=? WHERE id=?", (role, user_id))
    conn.commit()
    conn.close()


# ── Brand Assets (persisted in DB so Railway filesystem resets don't wipe them) ─

def save_brand_asset_db(key: str, data_b64: str, ext: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO brand_assets(key, data_b64, ext, updated_at) VALUES(?,?,?,datetime('now'))"
        " ON CONFLICT(key) DO UPDATE SET data_b64=excluded.data_b64, ext=excluded.ext, updated_at=excluded.updated_at",
        (key, data_b64, ext)
    )
    conn.commit()
    conn.close()


def get_brand_asset_db(key: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT data_b64, ext FROM brand_assets WHERE key=?", (key,)).fetchone()
    conn.close()
    return dict(row) if row else None
