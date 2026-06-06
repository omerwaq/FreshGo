import requests
import urllib.parse
import os
import uuid
import time
import random

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

STRICT BRAND RULES — non-negotiable:
- Style: DSLR product photography, studio lighting, ultra-realistic — NOT AI-looking, NOT surreal, NOT fantasy
- Subject: fresh white milk in glass bottle OR dairy products (ghee, curd) as main hero — clearly visible and appetizing
- Setting: clean white or soft green studio background, OR lush Pakistani green farm at golden hour
- NO hands holding products unnaturally, NO weird distortions, NO text on products
- Colors: clean white milk, deep green accents, warm golden light
- Mood: premium, trustworthy, fresh, healthy — like a professional Pakistani dairy brand ad
- End with: ultra sharp, 8K, Canon EOS product photography, studio lighting, photorealistic
- Under 100 words — output ONLY the prompt, no quotes, no explanation
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


def _try_pollinations(prompt: str) -> str | None:
    """Generate AI image via Pollinations (FLUX model) with retries."""
    encoded = urllib.parse.quote(prompt, safe='')
    for attempt in range(6):
        seed = random.randint(1, 999999)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?model=flux&width=1024&height=1024&nologo=true&seed={seed}"
        )
        print(f"[Image] Pollinations attempt {attempt+1}: seed={seed}")
        try:
            response = requests.get(url, timeout=120)
            ctype = response.headers.get("content-type", "")
            if response.status_code == 200 and "image" in ctype:
                filename = f"post_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(STATIC_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)
                local_url = f"/static/images/{filename}"
                print(f"[Image] Pollinations saved: {local_url}")
                return local_url
            else:
                print(f"[Image] Pollinations {response.status_code} — retrying in 5s...")
                time.sleep(5)
        except Exception as e:
            print(f"[Image] Pollinations error: {e} — retrying in 5s...")
            time.sleep(5)
    return None


def _try_together(prompt: str) -> str | None:
    """Generate AI image via Together AI — FLUX.1-schnell-Free (no cost)."""
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("[Image] No TOGETHER_API_KEY set")
        return None

    print("[Image] Trying Together AI FLUX.1-schnell-Free...")
    try:
        response = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": prompt,
                "width": 1024,
                "height": 1024,
                "steps": 4,
                "n": 1,
            },
            timeout=120,
        )
        print(f"[Image] Together AI response {response.status_code}: {response.text[:500]}")
        if response.status_code == 200:
            import base64
            data = response.json()
            item = data["data"][0]

            # Handle URL response
            if "url" in item:
                img_url = item["url"]
                print(f"[Image] Together AI returned URL: {img_url}")
                img_response = requests.get(img_url, timeout=60)
                img_response.raise_for_status()
                img_bytes = img_response.content
            # Handle base64 response
            elif "b64_json" in item:
                img_bytes = base64.b64decode(item["b64_json"])
            else:
                print(f"[Image] Together AI unknown response format: {item.keys()}")
                return None

            filename = f"post_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(STATIC_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(img_bytes)
            local_url = f"/static/images/{filename}"
            print(f"[Image] Together AI saved: {local_url}")
            return local_url
        return None
    except Exception as e:
        print(f"[Image] Together AI exception: {e}")
        return None


def _download_and_save(prompt: str) -> str | None:
    """Generate AI image via Together AI (free FLUX model). v2"""
    os.makedirs(STATIC_DIR, exist_ok=True)
    return _try_together(prompt)


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
