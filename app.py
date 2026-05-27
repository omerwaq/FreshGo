import os
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from ai_engine   import get_support_reply, generate_post
from facebook    import send_message, publish_post
from state       import set_pending_post, get_pending_post, clear_pending_post, has_pending_post
from rate_limiter import is_allowed, seconds_until_reset
from order_flow  import (has_active_order, is_order_intent,
                          start_order, handle_order_step, get_all_orders)

load_dotenv()

app = FastAPI(title="Fresh Go AI Agent")
app.mount("/static", StaticFiles(directory="static"), name="static")

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "freshgo_secret_123")
ADMIN_FB_ID  = os.getenv("ADMIN_FB_ID", "")

CONFIRM_WORDS = {"yes", "yep", "post it", "confirm", "ok", "okay", "ha", "haan", "kar do", "post", "send"}
CANCEL_WORDS  = {"no", "nahi", "cancel", "nope", "stop", "na"}


def is_admin(sender_id: str) -> bool:
    if not ADMIN_FB_ID:
        return False
    return sender_id == ADMIN_FB_ID


# ─────────────────────────────────────────────
# Admin: post creator flow
# ─────────────────────────────────────────────
async def process_admin(sender_id: str, text: str, local_mode: bool = False) -> list:
    replies    = []
    text_lower = text.strip().lower()

    if has_pending_post(sender_id):
        if any(w in text_lower for w in CONFIRM_WORDS):
            pending   = get_pending_post(sender_id)
            post_text = pending["text"]
            image_url = pending.get("image_url")
            clear_pending_post(sender_id)

            if local_mode:
                replies.append({"type": "published", "text": post_text, "image_url": image_url})
                replies.append({"type": "message",   "text": "✅ [Local Test] Post simulated! Connect Facebook to go live. 🎉"})
            else:
                result = publish_post(post_text, image_url)
                if "id" in result or "post_id" in result:
                    replies.append({"type": "published", "text": post_text, "image_url": image_url})
                    replies.append({"type": "message",   "text": "✅ Post published on Fresh Go page! 🎉"})
                else:
                    err = result.get("error", {}).get("message", "Unknown error")
                    replies.append({"type": "message", "text": f"❌ Couldn't publish. Error: {err}"})
            return replies

        elif any(w in text_lower for w in CANCEL_WORDS):
            clear_pending_post(sender_id)
            replies.append({"type": "message", "text": "❌ Post cancelled. Send !post <topic> anytime."})
            return replies
        else:
            clear_pending_post(sender_id)
            replies.append({"type": "message", "text": "🔄 Regenerating with new topic..."})

    if text_lower.startswith("!post "):
        topic = text[6:].strip()
        if not topic:
            replies.append({"type": "message", "text": "Please add a topic.\nExample: !post Eid discount on fresh milk 🎉"})
            return replies

        replies.append({"type": "message", "text": f'⏳ Generating post + image about "{topic}"...'})
        result     = await generate_post(topic)          # ← now async
        post_text  = result["text"]
        image_url  = result["image_url"]

        set_pending_post(sender_id, {"text": post_text, "image_url": image_url})

        preview = (
            f"📋 Post Preview:\n\n{post_text}\n\n"
            f"──────────────\n"
            f"Reply yes to publish ✅\n"
            f"Reply no to cancel ❌"
        )
        replies.append({"type": "message", "text": preview})
        if image_url:
            replies.append({"type": "image", "url": image_url})

    elif text_lower == "!orders":
        orders = get_all_orders()
        if not orders:
            replies.append({"type": "message", "text": "📦 Koi order nahi mila abhi tak."})
        else:
            lines = [f"📦 Total orders: {len(orders)}\n"]
            for o in orders[-10:]:   # last 10 only
                lines.append(
                    f"#{o['order_id']} | {o['timestamp']}\n"
                    f"  {o['name']} — {o['product']} — {o['quantity']}\n"
                    f"  📍 {o['address']} | Status: {o['status']}"
                )
            replies.append({"type": "message", "text": "\n\n".join(lines)})

    elif text_lower == "!help":
        replies.append({"type": "message", "text": (
            "🐄 Fresh Go Admin Commands:\n\n"
            "!post <topic>  →  Generate a Facebook post\n"
            "!orders        →  View last 10 customer orders\n"
            "!help          →  Show this menu\n\n"
            "After post preview, reply yes or no."
        )})
    else:
        replies.append({"type": "message", "text": "Use !post <topic>, !orders, or !help 🐄"})

    return replies


# ─────────────────────────────────────────────
# Customer: support + order flow
# ─────────────────────────────────────────────
async def process_customer(sender_id: str, text: str) -> list:

    # ── Rate limit check ──────────────────────────────────────────────────────
    if not is_allowed(sender_id):
        wait = seconds_until_reset(sender_id)
        return [{"type": "message",
                 "text": f"Aap ne bohat zyada messages bheje hain 🙏 "
                         f"{wait} seconds baad try karen. — Fresh Go 🐄"}]

    # ── Order flow: in progress ───────────────────────────────────────────────
    if has_active_order(sender_id):
        reply = handle_order_step(sender_id, text)
        return [{"type": "message", "text": reply}]

    # ── Order flow: new intent detected ──────────────────────────────────────
    if is_order_intent(text):
        reply = start_order(sender_id)
        return [{"type": "message", "text": reply}]

    # ── Regular AI support reply ──────────────────────────────────────────────
    reply = get_support_reply(text, sender_id)
    return [{"type": "message", "text": reply}]


# ─────────────────────────────────────────────
# Facebook Webhook — Verification
# ─────────────────────────────────────────────
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        print("[Webhook] Verified ✅")
        return int(hub_challenge)
    return JSONResponse(status_code=403, content={"error": "Verification failed"})


# ─────────────────────────────────────────────
# Facebook Webhook — Receive Messages
# ─────────────────────────────────────────────
@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()

    if body.get("object") == "page":
        for entry in body.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id    = event.get("sender", {}).get("id")
                message_data = event.get("message", {})
                text         = message_data.get("text", "").strip()

                if not text or message_data.get("is_echo"):
                    continue

                print(f"[MSG] From {sender_id}: {text}")

                if is_admin(sender_id):
                    replies = await process_admin(sender_id, text)
                else:
                    replies = await process_customer(sender_id, text)

                for r in replies:
                    if r["type"] == "message":
                        send_message(sender_id, r["text"])

    return {"status": "ok"}


# ─────────────────────────────────────────────
# Local Test Chat
# ─────────────────────────────────────────────
@app.post("/chat")
async def local_chat(request: Request):
    data       = await request.json()
    message    = data.get("message", "").strip()
    admin_mode = data.get("is_admin", False)
    sender_id  = "admin_test" if admin_mode else "customer_test"

    if not message:
        return JSONResponse(status_code=400, content={"error": "Message required"})

    if admin_mode:
        replies = await process_admin(sender_id, message, local_mode=True)
    else:
        replies = await process_customer(sender_id, message)

    return {"replies": replies}


# ─────────────────────────────────────────────
# UI + Health
# ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open("chat.html", "r") as f:
        return f.read()


@app.get("/health")
async def health():
    from order_flow import get_all_orders
    orders = get_all_orders()
    return {
        "status":          "🐄 Fresh Go AI is running!",
        "admin_configured": bool(ADMIN_FB_ID),
        "total_orders":     len(orders),
    }


if __name__ == "__main__":
    import uvicorn
    print("🐄 Fresh Go AI Agent starting...")
    print("🔗 Webhook: http://localhost:8000/webhook")
    print("💻 Chat UI: http://localhost:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
