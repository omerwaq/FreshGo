"""
WhatsApp Business Cloud API client for Fresh Go.
Requires Meta WhatsApp Business account credentials in .env
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

WA_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WA_TOKEN    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WA_VERIFY   = os.getenv("WHATSAPP_VERIFY_TOKEN", "freshgo_wa_secret")


def _is_configured() -> bool:
    return bool(WA_PHONE_ID and WA_TOKEN)


def _headers() -> dict:
    return {"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"}


def _api_url() -> str:
    return f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages"


# ── Send ──────────────────────────────────────────────────────────────────────

def send_whatsapp_message(phone: str, text: str) -> dict | None:
    """Send a plain text WhatsApp message."""
    if not _is_configured():
        print("[WhatsApp] Credentials not configured — skipping send")
        return None
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text, "preview_url": False}
    }
    resp = requests.post(_api_url(), json=payload, headers=_headers(), timeout=15)
    if resp.status_code != 200:
        print(f"[WhatsApp Error] {resp.status_code}: {resp.text}")
    return resp.json()


def send_whatsapp_image(phone: str, image_url: str, caption: str = "") -> dict | None:
    """Send an image message via WhatsApp (image_url must be publicly accessible)."""
    if not _is_configured():
        return None
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "image",
        "image": {"link": image_url, "caption": caption}
    }
    resp = requests.post(_api_url(), json=payload, headers=_headers(), timeout=15)
    if resp.status_code != 200:
        print(f"[WhatsApp Image Error] {resp.text}")
    return resp.json()


def send_whatsapp_template(phone: str, template_name: str, lang: str = "en_US") -> dict | None:
    """Send a pre-approved WhatsApp template message (required for first contact)."""
    if not _is_configured():
        return None
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {"name": template_name, "language": {"code": lang}}
    }
    resp = requests.post(_api_url(), json=payload, headers=_headers(), timeout=15)
    return resp.json()


# ── Parse Incoming Webhook ────────────────────────────────────────────────────

def parse_whatsapp_webhook(body: dict) -> list[dict]:
    """
    Parse incoming WhatsApp Cloud API webhook payload.
    Returns list of {phone, text, msg_id} dicts.
    """
    messages = []
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                # Skip delivery/read receipts — only handle incoming messages
                for msg in value.get("messages", []):
                    if msg.get("type") == "text":
                        messages.append({
                            "phone":  msg["from"],
                            "text":   msg["text"]["body"],
                            "msg_id": msg["id"],
                        })
    except Exception as e:
        print(f"[WhatsApp Parse Error] {e}")
    return messages


def verify_whatsapp_webhook(mode: str, token: str, challenge: str) -> str | None:
    """Verify WhatsApp webhook subscription. Returns challenge on success."""
    if mode == "subscribe" and token == WA_VERIFY:
        return challenge
    return None
