"""
Fresh Go — Automatic WhatsApp Bulk Sender
==========================================
Run this on your Mac to auto-send WhatsApp messages.

Steps:
1. pip install selenium openpyxl webdriver-manager
2. python bulk_whatsapp.py
3. Scan QR code in the browser that opens
4. Messages send automatically to all customers
"""

import time
import sys
import os
import openpyxl

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


DEFAULT_MESSAGE = """Assalam o Alaikum {name}! 🌿

Aaj aapka {quantity} Fresh Go doodh deliver ho gaya hai.
100% pure, hormone-free cow milk 🐄

Shukriya Fresh Go choose karne ke liye! ❤️
Koi sawaal ho: 0300-3147887"""


def clean_phone(phone: str) -> str:
    phone = str(phone).strip().replace(" ", "").replace("-", "").replace("+", "")
    if phone.startswith("0"):
        phone = "92" + phone[1:]
    if not phone.startswith("92"):
        phone = "92" + phone
    return phone


def read_excel(filepath: str) -> list:
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    headers = [str(ws.cell(1, c).value or "").strip().lower() for c in range(1, ws.max_column + 1)]

    name_col    = next((i for i, h in enumerate(headers) if "name"    in h), None)
    phone_col   = next((i for i, h in enumerate(headers) if "phone"   in h or "number" in h or "mobile" in h), None)
    qty_col     = next((i for i, h in enumerate(headers) if "qty"     in h or "quant"  in h or "litre"  in h), None)
    product_col = next((i for i, h in enumerate(headers) if "product" in h), None)

    if phone_col is None:
        print("❌ Phone Number column nahi mili Excel mein!")
        sys.exit(1)

    customers = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        phone = str(row[phone_col] or "").strip()
        if not phone or phone == "None":
            continue
        customers.append({
            "name":     str(row[name_col]    or "Customer").strip() if name_col    is not None else "Customer",
            "phone":    clean_phone(phone),
            "quantity": str(row[qty_col]     or "").strip()         if qty_col     is not None else "",
            "product":  str(row[product_col] or "doodh").strip()    if product_col is not None else "doodh",
        })
    return customers


def send_messages(customers: list, message_template: str = None):
    print(f"\n🐄 Fresh Go Bulk WhatsApp Sender")
    print(f"📋 {len(customers)} customers loaded\n")

    # Launch Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    # Keeps WhatsApp Web session alive between runs
    profile_dir = os.path.join(os.path.dirname(__file__), "whatsapp_session")
    os.makedirs(profile_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_dir}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    print("🌐 WhatsApp Web khul raha hai...")
    driver.get("https://web.whatsapp.com")

    print("📱 QR scan karo apne phone se (pehli baar)...")
    print("   Pehle scan ke baad next time automatic connect hoga.\n")

    # Wait for WhatsApp to load (QR scan + page load)
    try:
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-tab="3"], div[data-testid="chat-list"]'))
        )
        print("✅ WhatsApp Web connected!\n")
    except Exception:
        print("⏰ QR scan timeout. Dobara try karo.")
        driver.quit()
        return

    sent = 0
    failed = 0

    for i, c in enumerate(customers):
        name     = c["name"]
        phone    = c["phone"]
        qty      = c["quantity"]
        product  = c["product"]
        qty_text = f"{qty} {product}".strip() if qty else product

        msg = (message_template or DEFAULT_MESSAGE).format(
            name=name, quantity=qty_text, product=product
        )

        print(f"📤 [{i+1}/{len(customers)}] Sending to {name} ({phone})...")

        try:
            import urllib.parse
            encoded_msg = urllib.parse.quote(msg)
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"
            driver.get(url)

            # Wait for the message input box to appear
            input_box = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    'div[data-testid="conversation-compose-box-input"], '
                    'div[contenteditable="true"][data-tab="10"], '
                    'footer div[contenteditable="true"]'
                ))
            )
            time.sleep(2)  # Let text load into box

            # Press ENTER to send
            input_box.send_keys(Keys.ENTER)
            time.sleep(2.5)
            sent += 1
            print(f"   ✅ Sent!")

        except Exception as e:
            failed += 1
            print(f"   ❌ Failed: {e}")

        time.sleep(2)  # Small delay between messages

    print(f"\n{'='*40}")
    print(f"✅ Sent:   {sent}")
    print(f"❌ Failed: {failed}")
    print(f"{'='*40}")
    driver.quit()


if __name__ == "__main__":
    # Find Excel file
    excel_file = None
    for f in os.listdir(os.path.dirname(__file__) or "."):
        if f.endswith(".xlsx") and "FreshGo" in f:
            excel_file = f
            break

    if not excel_file:
        print("Excel file nahi mili. FreshGo_Customers_*.xlsx dashboard se download karo.")
        excel_path = input("Ya file ka full path paste karo: ").strip().strip('"')
    else:
        print(f"📂 Excel file mili: {excel_file}")
        excel_path = excel_file

    print("\n📝 Custom message likhna chahte ho? (Enter dabaiye default ke liye)")
    custom = input("Message: ").strip()

    customers = read_excel(excel_path)
    if not customers:
        print("Koi customers nahi mile.")
        sys.exit(1)

    print(f"\nCustomers:")
    for c in customers:
        print(f"  • {c['name']} — {c['phone']} — {c['quantity']} {c['product']}")

    confirm = input(f"\n{len(customers)} customers ko message bhejna hai? (yes/no): ").strip().lower()
    if confirm in ("yes", "y", "ha", "haan"):
        send_messages(customers, custom if custom else None)
    else:
        print("Cancelled.")
