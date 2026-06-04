import requests
import urllib.parse
import os
import uuid

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static", "images")

# Fresh Go brand identity for the AI image prompter
FRESH_GO_BRAND = """
Brand: Fresh Go — a premium dairy farm from Nankana Sahib, Pakistan
Products: Pure cow milk (250 rs/litre) and desi ghee
Brand colors: Deep green and white
Vibe: Clean, natural, trustworthy, farm-fresh, Pakistani family values
Style: Warm golden light, lush green farm backgrounds, glass bottles of fresh milk,
       happy healthy cows, traditional Pakistani countryside feel
"""

IMAGE_SYSTEM_PROMPT = f"""
You are an expert AI image prompt engineer for the dairy brand "Fresh Go".
Given a post topic, write ONE highly detailed image generation prompt.

Brand context:
{FRESH_GO_BRAND}

Rules for your prompt:
- Be very specific and visual (describe lighting, colors, composition, mood)
- Always include: fresh white milk, green Farm Go branding feel, warm natural lighting
- Make it photorealistic and appetizing
- Include Pakistani/South Asian visual context where relevant (e.g. clay pots, green fields, traditional setting)
- End with quality boosters: sharp focus, 4K, professional food photography, award winning
- Keep it under 120 words
- Output ONLY the image prompt — no explanation, no quotes
"""


def generate_image_prompt_via_ai(topic: str) -> str:
    """Use Groq to write a smart, brand-specific image prompt for the topic."""
    try:
        from groq import Groq
        from dotenv import load_dotenv
        load_dotenv()

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": IMAGE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Post topic: {topic}"}
            ],
            max_tokens=180,
            temperature=0.85,
        )
        prompt = response.choices[0].message.content.strip()
        print(f"[Image Prompt] {prompt}")
        return prompt

    except Exception as e:
        print(f"[Image Prompt Fallback] {e}")
        # Fallback prompt if Groq fails
        return (
            f"Fresh Go dairy farm Pakistan: {topic}, fresh white cow milk in glass bottle, "
            "lush green fields, warm golden morning light, traditional clay pot, "
            "happy healthy cows, clean white background, "
            "professional food photography, 4K, sharp focus, photorealistic, award winning"
        )


def _download_and_save(prompt: str) -> str | None:
    """Download image from Picsum (always works, no auth, no rate limits) and save locally."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    seed = abs(hash(prompt)) % 1000  # deterministic seed per prompt for variety
    url = f"https://picsum.photos/seed/{seed}/1024/1024"
    print(f"[Image] Downloading from Picsum: {url}")
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        filename = f"post_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(STATIC_DIR, filename)
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        local_url = f"/static/images/{filename}"
        print(f"[Image] Saved: {local_url}")
        return local_url
    except Exception as e:
        print(f"[Image] Picsum failed: {e}")
        return None


async def fetch_and_save_image(topic: str) -> str | None:
    """
    Async: generate smart prompt via Groq, then download image in a thread.
    Server stays responsive while image downloads (no blocking).
    """
    try:
        prompt = generate_image_prompt_via_ai(topic)
        # Run blocking download in thread pool — doesn't freeze the server
        import asyncio
        local_url = await asyncio.to_thread(_download_and_save, prompt)
        return local_url
    except Exception as e:
        print(f"[Image Error] {e}")
        return None


def download_image(image_url: str) -> str:
    """Download a local /static/images/... path to a temp file for Facebook upload."""
    import tempfile

    if image_url.startswith("/static/"):
        # Already a local file — just return the full path
        return os.path.join(os.path.dirname(__file__), image_url.lstrip("/"))

    # Remote URL — download it
    response = requests.get(image_url, timeout=60, stream=True)
    response.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    for chunk in response.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name
