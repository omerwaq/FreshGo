"""
Fresh Go — Automatic WhatsApp Bulk Sender
==========================================
Double-click "FreshGo WhatsApp Sender.command" on your Mac.
Fetches today's customers from Railway automatically, then sends messages via WhatsApp Web.
First run: scan QR code once. After that it stays logged in.
"""

import time, sys, os, json, ssl, urllib.request, urllib.parse
from datetime import datetime

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = ssl.create_default_context()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ────────────────────────────────────────────────────────────────────
RAILWAY_URL   = "https://freshgo-production.up.railway.app"
SESSION_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whatsapp_session")

DEFAULT_MESSAGE = """Dear {name}, 🌿

📅 {date}

Your Fresh Go {product} ({qty}) has been delivered today. 100% pure and natural — straight from our Nankana Sahib farm to your home. 🐄

Thank you for choosing Fresh Go! ❤️
Any questions? Call/WhatsApp: 0300-3147887"""


def clean_phone(phone: str) -> str:
    phone = str(phone).strip().replace(" ", "").replace("-", "").replace("+", "")
    if phone.startswith("0"):
        phone = "92" + phone[1:]
    elif not phone.startswith("92"):
        phone = "92" + phone
    return phone


def fetch_customers_from_railway() -> list:
    """Fetch today's customers from Railway. Returns only those with phone numbers."""
    print("📡 Railway se customers fetch ho rahe hain...")
    try:
        url = f"{RAILWAY_URL}/api/todays-customers"
        with urllib.request.urlopen(url, timeout=15, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
        customers = data.get("customers", [])
        for c in customers:
            if c.get("phone"):
                c["phone"] = clean_phone(str(c["phone"]))
        customers = [c for c in customers if c.get("phone")]
        print(f"✅ {len(customers)} customers mile Railway se\n")
        return customers
    except Exception as e:
        print(f"⚠️  Railway se fetch nahi hua: {e}")
        return []


def read_excel(filepath: str) -> list:
    """Read customers from an Excel file. Auto-detects Rider Delivery Report format."""
    try:
        import openpyxl, re
        wb = openpyxl.load_workbook(filepath)
        ws = wb.active

        # Find header row (skip title row if present)
        header_row = 1
        for r in range(1, 6):
            cells = [str(ws.cell(r, c).value or "").strip().lower() for c in range(1, ws.max_column + 1)]
            if any("customer" in h or "phone" in h for h in cells):
                header_row = r
                break

        headers = [str(ws.cell(header_row, c).value or "").strip().lower()
                   for c in range(1, ws.max_column + 1)]

        def find_col(*keywords):
            for kw in keywords:
                for i, h in enumerate(headers):
                    if kw in h:
                        return i
            return None

        name_col    = find_col("customer", "name")
        phone_col   = find_col("phone", "number", "mobile")
        qty_col     = find_col("quantity", "qty", "litre")
        product_col = find_col("product")
        area_col    = find_col("area")
        rider_col   = find_col("rider")
        amount_col  = find_col("amount")
        payment_col = find_col("cash")  # "cash/credit" column

        if phone_col is None:
            print("❌ Excel mein Phone/Number column nahi mila!")
            return []

        # Detect if this is a Rider Delivery Report
        is_delivery_report = rider_col is not None and area_col is not None

        customers = []
        for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
            if not row or all(v is None for v in row):
                continue
            phone = str(row[phone_col] or "").strip()
            if not phone or phone.lower() == "none" or not any(ch.isdigit() for ch in phone):
                continue

            # Strip trailing (ID) from customer name e.g. "Hassan Muhammad(8)"
            raw_name = str(row[name_col] or "Customer").strip() if name_col is not None else "Customer"
            name = re.sub(r"\s*\(\d+\)$", "", raw_name).strip() or "Customer"

            c = {
                "name":     name,
                "phone":    clean_phone(phone),
                "quantity": str(row[qty_col]     or "").strip() if qty_col     is not None else "",
                "product":  str(row[product_col] or "doodh").strip() if product_col is not None else "doodh",
            }
            if is_delivery_report:
                c["area"]    = str(row[area_col]    or "").strip() if area_col    is not None else ""
                c["rider"]   = str(row[rider_col]   or "").strip() if rider_col   is not None else ""
                c["amount"]  = str(row[amount_col]  or "").strip() if amount_col  is not None else ""
                c["payment"] = str(row[payment_col] or "").strip() if payment_col is not None else ""
            customers.append(c)

        if is_delivery_report:
            print(f"ℹ️  Rider Delivery Report format detected")
        return customers
    except Exception as e:
        print(f"❌ Excel read error: {e}")
        return []


def find_excel_file() -> str | None:
    """Look for any FreshGo Excel file in the same folder."""
    folder = os.path.dirname(os.path.abspath(__file__))
    for f in sorted(os.listdir(folder), reverse=True):
        if f.endswith((".xlsx", ".xls")) and not f.startswith("~"):
            return os.path.join(folder, f)
    return None


def get_customers() -> list:
    """Get customers: first from Railway, then fall back to Excel file."""
    customers = fetch_customers_from_railway()

    if customers:
        return customers

    print("ℹ️  Railway pe phone numbers nahi hain.")
    print("   Excel file se customers load kiye ja rahe hain...\n")

    # Try to find Excel automatically
    excel_path = find_excel_file()
    if excel_path:
        print(f"📂 Excel mili: {os.path.basename(excel_path)}")
        customers = read_excel(excel_path)
        if customers:
            print(f"✅ {len(customers)} customers Excel se mile\n")
            return customers

    # Ask user to provide Excel path
    print("📂 Excel file ka path paste karo (ya Enter dabaiye cancel ke liye):")
    path = input("Path: ").strip().strip('"').strip("'")
    if path and os.path.exists(path):
        customers = read_excel(path)
        if customers:
            print(f"✅ {len(customers)} customers mile\n")
    return customers


def send_messages(customers: list, message_template: str):
    print(f"🐄 Fresh Go WhatsApp Bulk Sender")
    print(f"📋 {len(customers)} customers ko message bheja jayega\n")

    os.makedirs(SESSION_DIR, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument(f"--user-data-dir={SESSION_DIR}")

    driver = webdriver.Chrome(options=options)

    print("🌐 WhatsApp Web khul raha hai...")
    driver.get("https://web.whatsapp.com")

    print("📱 Agar pehli baar hai to QR scan karo apne phone se.")
    print("   Pehle scan ke baad next time automatic connect hoga.\n")

    try:
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                'div[data-tab="3"], div[data-testid="chat-list"]'))
        )
        print("✅ WhatsApp Web connected!\n")
    except Exception:
        print("⏰ Timeout — dobara try karo.")
        driver.quit()
        sys.exit(1)

    sent, failed = 0, 0

    for i, c in enumerate(customers):
        name     = c.get("name", "Customer")
        phone    = c["phone"]
        quantity = c.get("quantity", "")
        product  = c.get("product", "milk")
        qty_text = f"{quantity} {product}".strip() if quantity else product
        unit = "kg" if "ghee" in product.lower() else "L"
        qty_with_unit = f"{quantity} {unit}" if quantity else f"1 {unit}"

        d = datetime.now()
        today = f"{d.day} {d.strftime('%B %Y')}"   # cross-platform, e.g. "12 June 2026"

        # Build delivery report message if extra fields are present
        area    = c.get("area", "")
        rider   = c.get("rider", "")
        amount  = c.get("amount", "")
        payment = c.get("payment", "")

        if rider and area and message_template == DEFAULT_MESSAGE:
            # Richer message for Rider Delivery Report Excel
            msg = (
                f"Dear {name}, 🌿\n\n"
                f"📅 {today}\n\n"
                f"Aaj aapki delivery complete ho gayi! ✅\n\n"
                f"📦 {product} — {qty_with_unit}\n"
                f"📍 Area: {area}\n"
                f"🚴 Rider: {rider}\n"
                + (f"💰 Amount: Rs. {amount}\n" if amount else "")
                + (f"💳 Payment: {payment}\n" if payment else "")
                + f"\nShukriya Fresh Go choose karne ke liye! ❤️\n"
                f"Mona Dairy Farms, Nankana Sahib 🐄\n"
                f"Call/WhatsApp: 0300-3147887"
            )
        else:
            msg = message_template.format(
                name=name,
                product=product,
                qty=qty_with_unit,
                quantity=qty_text,
                date=today,
            )

        print(f"📤 [{i+1}/{len(customers)}] {name} ({phone})...")

        try:
            url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(msg)}"
            driver.get(url)

            input_box = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    'div[data-testid="conversation-compose-box-input"], '
                    'div[contenteditable="true"][data-tab="10"], '
                    'footer div[contenteditable="true"]'
                ))
            )
            time.sleep(2)
            input_box.send_keys(Keys.ENTER)
            time.sleep(2.5)
            sent += 1
            print(f"   ✅ Sent!")

        except Exception as e:
            failed += 1
            print(f"   ❌ Failed: {e}")

        time.sleep(1.5)

    print(f"\n{'='*40}")
    print(f"✅ Sent:   {sent}")
    print(f"❌ Failed: {failed}")
    print(f"{'='*40}")
    driver.quit()


if __name__ == "__main__":
    customers = get_customers()

    if not customers:
        print("Aaj koi customers nahi hain jinka phone number ho.")
        input("Enter dabaiye band karne ke liye...")
        sys.exit(0)

    print("Customers:")
    for c in customers:
        print(f"  • {c.get('name','?')} — {c['phone']} — {c.get('quantity','')} {c.get('product','')}")

    print(f"\nMessage template (Enter dabaiye default ke liye, ya apna likhein):")
    custom = input("Message: ").strip()
    template = custom if custom else DEFAULT_MESSAGE

    confirm = input(f"\n{len(customers)} customers ko message bhejna hai? (yes/no): ").strip().lower()
    if confirm in ("yes", "y", "ha", "haan"):
        send_messages(customers, template)
    else:
        print("Cancelled.")

    input("\nEnter dabaiye band karne ke liye...")
