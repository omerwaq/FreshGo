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


ADMIN_SYSTEM_PROMPT = """
You are Fresh Go's smart social media manager AI. You work directly with the farm owner (admin) to create great posts together.

Fresh Go brand:
- Premium dairy farm from Nankana Sahib, Pakistan
- Products: Pure cow milk (250 rs/litre), Desi Ghee, Fresh Curd
- Delivers to all Lahore areas, 7am–5pm
- WhatsApp: 0300-3147887
- Brand colors: deep green and white
- Values: pure, hormone-free, farm-fresh, Pakistani family values

Your job:
- Have a natural conversation with the admin in Roman Urdu + English mix
- Help them brainstorm post ideas, suggest topics, improve captions
- When the admin wants to create a post (they say things like "post banao", "create ad", "make a post about X", "image banao", "iska post banao"), include this EXACT marker in your response: [POST_GENERATE: <topic>]
- The topic should be detailed enough for image generation (e.g. "morning fresh milk delivery Lahore 250rs per litre")
- Ask follow-up questions to get better details before generating
- Be friendly, creative, and help make posts that will attract customers

Example:
Admin: "doodh ki post banao morning delivery ke liye"
You: "Zaroor! Morning delivery bohot popular hai. Koi special offer hai ya normal price 250rs/litre? [POST_GENERATE: fresh cow milk morning delivery Lahore, 250rs per litre, pure hormone-free]"

Remember: ONLY include [POST_GENERATE: ...] when you are confident the admin wants to generate a post right now.
"""

ADMIN_HISTORY_KEY = "admin_conversation"


def admin_chat(message: str) -> tuple[str, str | None]:
    """
    Chat with admin. Returns (reply_text, post_topic_or_None).
    post_topic is extracted from [POST_GENERATE: topic] marker if present.
    """
    hist = _get_history(ADMIN_HISTORY_KEY, "admin")
    messages = (
        [{"role": "system", "content": ADMIN_SYSTEM_PROMPT}]
        + hist
        + [{"role": "user", "content": message}]
    )
    try:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=400, temperature=0.8,
        )
        reply = response.choices[0].message.content.strip()

        # Extract [POST_GENERATE: topic] marker if present
        post_topic = None
        if "[POST_GENERATE:" in reply:
            import re
            match = re.search(r'\[POST_GENERATE:\s*(.+?)\]', reply)
            if match:
                post_topic = match.group(1).strip()
            # Remove the marker from the visible reply
            reply = re.sub(r'\[POST_GENERATE:[^\]]*\]', '', reply).strip()

        _save_history(ADMIN_HISTORY_KEY, message, reply, "admin")
        return reply, post_topic
    except Exception as e:
        print(f"[Admin Chat Error] {e}")
        return "Maafi, technical masla aa gaya. Dobara try karen.", None


def analyze_reference_image(image_data_url: str) -> str:
    """Use Groq vision to analyze a reference image and describe its style for replication."""
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url}
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analyze this image for a dairy brand ad recreation. Describe in detail: "
                            "1) Photography style (studio/outdoor/lifestyle) "
                            "2) Lighting (soft/harsh/golden hour/studio) "
                            "3) Color palette and mood "
                            "4) Composition and layout "
                            "5) Subject placement "
                            "6) Overall visual style and quality "
                            "Keep it under 100 words, focused on recreating this style for a milk/dairy product."
                        )
                    }
                ]
            }],
            max_tokens=200,
        )
        analysis = response.choices[0].message.content.strip()
        print(f"[Vision Analysis] {analysis}")
        return analysis
    except Exception as e:
        print(f"[Vision Error] {e}")
        return "professional dairy product photography, clean background, warm lighting, high quality"


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
