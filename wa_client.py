"""
WhatsApp Web automation running on Railway server.
Scan QR once from dashboard — then send from any device.
"""
import asyncio, base64, os, json, time
from playwright.async_api import async_playwright, Page

SESSION_FILE = os.path.join(os.path.dirname(__file__), "wa_session.json")

class WAClient:
    def __init__(self):
        self._pw = None
        self._browser = None
        self._page: Page = None
        self._ready = False
        self._qr_base64 = None
        self._lock = asyncio.Lock()

    async def start(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"]
        )
        ctx_args = {}
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE) as f:
                    storage = json.load(f)
                ctx_args["storage_state"] = storage
                print("[WA] Session loaded from file")
            except Exception:
                pass

        ctx = await self._browser.new_context(**ctx_args)
        self._page = await ctx.new_page()
        await self._page.goto("https://web.whatsapp.com", timeout=60000)
        asyncio.create_task(self._watch_state())

    async def _watch_state(self):
        while True:
            try:
                # Check if QR code is visible
                qr_el = await self._page.query_selector('canvas[aria-label="Scan this QR code to link a device"]')
                if qr_el:
                    self._ready = False
                    qr_img = await qr_el.screenshot()
                    self._qr_base64 = base64.b64encode(qr_img).decode()
                else:
                    # Check if chat list is visible (connected)
                    chat = await self._page.query_selector('div[data-testid="chat-list"], #app .two')
                    if chat:
                        if not self._ready:
                            print("[WA] Connected! Saving session...")
                            self._ready = True
                            self._qr_base64 = None
                            try:
                                storage = await self._page.context.storage_state()
                                with open(SESSION_FILE, "w") as f:
                                    json.dump(storage, f)
                            except Exception as e:
                                print(f"[WA] Session save error: {e}")
            except Exception:
                pass
            await asyncio.sleep(2)

    @property
    def is_ready(self): return self._ready

    @property
    def qr_base64(self): return self._qr_base64

    async def send_message(self, phone: str, text: str) -> bool:
        if not self._ready:
            return False
        async with self._lock:
            try:
                import urllib.parse
                phone = phone.replace(" ","").replace("-","").replace("+","")
                if phone.startswith("0"):
                    phone = "92" + phone[1:]
                url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(text)}"
                await self._page.goto(url, timeout=30000)

                # Wait for input box
                input_box = await self._page.wait_for_selector(
                    'div[contenteditable="true"][data-tab="10"], '
                    'div[data-testid="conversation-compose-box-input"]',
                    timeout=20000
                )
                await asyncio.sleep(1.5)
                await input_box.press("Enter")
                await asyncio.sleep(2)
                print(f"[WA] Sent to {phone}")
                return True
            except Exception as e:
                print(f"[WA] Send error to {phone}: {e}")
                return False

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()


# Global singleton
_client: WAClient = None

async def get_client() -> WAClient:
    global _client
    if _client is None:
        _client = WAClient()
        await _client.start()
    return _client
