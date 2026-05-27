import os
import asyncio
from collections import OrderedDict
from groq import Groq
from dotenv import load_dotenv
from prompts import SUPPORT_SYSTEM_PROMPT, POST_SYSTEM_PROMPT
from image_gen import fetch_and_save_image

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"

# ── LRU-capped conversation history (max 500 users) ──────────────────────────
MAX_USERS = 500
conversation_histories: OrderedDict = OrderedDict()


def _get_history(user_id: str) -> list:
    """Return history for user, evicting oldest if over capacity (LRU)."""
    if user_id in conversation_histories:
        conversation_histories.move_to_end(user_id)   # mark as recently used
        return conversation_histories[user_id]
    if len(conversation_histories) >= MAX_USERS:
        conversation_histories.popitem(last=False)     # evict oldest
    conversation_histories[user_id] = []
    return conversation_histories[user_id]


def _save_history(user_id: str, user_msg: str, bot_reply: str):
    """Append exchange to history, keep last 20 messages."""
    hist = _get_history(user_id)
    hist.append({"role": "user",      "content": user_msg})
    hist.append({"role": "assistant", "content": bot_reply})
    conversation_histories[user_id] = hist[-20:]


def get_support_reply(user_message: str, user_id: str) -> str:
    """Generate a customer support reply for a Facebook DM."""
    try:
        history  = _get_history(user_id)
        messages = (
            [{"role": "system", "content": SUPPORT_SYSTEM_PROMPT}]
            + history
            + [{"role": "user", "content": user_message}]
        )
        response = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=500, temperature=0.7,
        )
        reply = response.choices[0].message.content
        _save_history(user_id, user_message, reply)
        return reply

    except Exception as e:
        print(f"[AI Error] {e}")
        return "Maafi chahta hoon, abhi technical masla hai. Thodi der baad try karen ya 0300-3147887 pe WhatsApp karen. — Fresh Go 🐄"


async def generate_post(topic: str) -> dict:
    """
    Async: generate post text (Groq) + image (Pollinations) concurrently.
    Both run at the same time — faster than running sequentially.
    Returns: {"text": "...", "image_url": "..."}
    """
    try:
        # Run text generation + image generation concurrently
        text_task  = asyncio.to_thread(
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": POST_SYSTEM_PROMPT},
                    {"role": "user",   "content": f"Create a Facebook post for this topic: {topic}"}
                ],
                max_tokens=400,
                temperature=0.8,
            ).choices[0].message.content
        )
        image_task = fetch_and_save_image(topic)

        post_text, image_url = await asyncio.gather(text_task, image_task)
        return {"text": post_text, "image_url": image_url}

    except Exception as e:
        print(f"[Post Generation Error] {e}")
        return {"text": "Sorry, couldn't generate the post. Please try again.", "image_url": None}
