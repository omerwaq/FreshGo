import os
import asyncio
from collections import OrderedDict
from groq import Groq
from dotenv import load_dotenv
from prompts import SUPPORT_SYSTEM_PROMPT, POST_SYSTEM_PROMPT
from image_gen import fetch_and_save_image

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"

# In-memory LRU cache (fast path) — also written through to SQLite
MAX_USERS = 500
conversation_histories: OrderedDict = OrderedDict()


def _get_history(user_id: str, platform: str = "facebook") -> list:
    cache_key = f"{platform}:{user_id}"
    if cache_key in conversation_histories:
        conversation_histories.move_to_end(cache_key)
        return conversation_histories[cache_key]

    # Cache miss — load from DB
    try:
        from database import get_conversation
        hist = get_conversation(user_id, platform)
    except Exception:
        hist = []

    if len(conversation_histories) >= MAX_USERS:
        conversation_histories.popitem(last=False)
    conversation_histories[cache_key] = hist
    return hist


def _save_history(user_id: str, user_msg: str, bot_reply: str,
                  platform: str = "facebook"):
    cache_key = f"{platform}:{user_id}"
    hist = _get_history(user_id, platform)
    hist.append({"role": "user",      "content": user_msg})
    hist.append({"role": "assistant", "content": bot_reply})
    hist = hist[-20:]
    conversation_histories[cache_key] = hist

    # Persist to DB (fire-and-forget in thread)
    try:
        import threading
        from database import save_conversation
        threading.Thread(
            target=save_conversation,
            args=(user_id, hist, platform),
            daemon=True
        ).start()
    except Exception as e:
        print(f"[History Persist Error] {e}")


def get_support_reply(user_message: str, user_id: str,
                      platform: str = "facebook") -> str:
    try:
        history  = _get_history(user_id, platform)
        messages = (
            [{"role": "system", "content": SUPPORT_SYSTEM_PROMPT}]
            + history
            + [{"role": "user", "content": user_message}]
        )
        response = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=500, temperature=0.7,
        )
        reply = response.choices[0].message.content
        _save_history(user_id, user_message, reply, platform)
        return reply
    except Exception as e:
        print(f"[AI Error] {e}")
        return ("Maafi chahta hoon, abhi technical masla hai. "
                "Thodi der baad try karen ya 0300-3147887 pe WhatsApp karen. — Fresh Go 🐄")


def _post_text_only(topic: str) -> str:
    """Blocking post text generation (called via asyncio.to_thread)."""
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": POST_SYSTEM_PROMPT},
            {"role": "user",   "content": f"Create a Facebook post for: {topic}"}
        ],
        max_tokens=400,
        temperature=0.8,
    ).choices[0].message.content


async def generate_post(topic: str) -> dict:
    """
    Async: generate post text (Groq) + image (Pollinations) concurrently.
    Returns {"text": "...", "image_url": "..."}
    """
    try:
        text_task  = asyncio.to_thread(_post_text_only, topic)
        image_task = fetch_and_save_image(topic)
        post_text, image_url = await asyncio.gather(text_task, image_task)
        return {"text": post_text, "image_url": image_url}
    except Exception as e:
        print(f"[Post Generation Error] {e}")
        return {"text": "Sorry, couldn't generate the post. Please try again.",
                "image_url": None}
