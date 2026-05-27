import os
from groq import Groq
from dotenv import load_dotenv
from prompts import SUPPORT_SYSTEM_PROMPT, POST_SYSTEM_PROMPT
from image_gen import fetch_and_save_image

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"  # Best free model on Groq

# In-memory conversation history per user (resets when app restarts)
conversation_histories = {}


def get_support_reply(user_message: str, user_id: str) -> str:
    """Generate a customer support reply for a Facebook DM."""
    try:
        # Get or create conversation history for this user
        if user_id not in conversation_histories:
            conversation_histories[user_id] = []

        history = conversation_histories[user_id]

        # Build messages with system prompt + history + new message
        messages = (
            [{"role": "system", "content": SUPPORT_SYSTEM_PROMPT}]
            + history
            + [{"role": "user", "content": user_message}]
        )

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )

        reply = response.choices[0].message.content

        # Save to history (keep last 20 messages to avoid overload)
        conversation_histories[user_id].append({"role": "user", "content": user_message})
        conversation_histories[user_id].append({"role": "assistant", "content": reply})
        if len(conversation_histories[user_id]) > 20:
            conversation_histories[user_id] = conversation_histories[user_id][-20:]

        return reply

    except Exception as e:
        print(f"[AI Error] {e}")
        return "Thanks for reaching out! Our team will get back to you shortly. — Fresh Go Team 🐄"


def generate_post(topic: str) -> dict:
    """
    Generate a Facebook post + image for Fresh Go.
    Returns: {"text": "...", "image_url": "..."}
    """
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": POST_SYSTEM_PROMPT},
                {"role": "user", "content": f"Create a Facebook post for this topic: {topic}"}
            ],
            max_tokens=400,
            temperature=0.8,
        )
        post_text = response.choices[0].message.content

        # Download image server-side (avoids browser auth issues with Pollinations)
        image_url = fetch_and_save_image(topic)

        return {"text": post_text, "image_url": image_url}

    except Exception as e:
        print(f"[Post Generation Error] {e}")
        return {"text": "Sorry, couldn't generate the post. Please try again.", "image_url": None}
