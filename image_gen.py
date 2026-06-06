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

STRICT BRAND RULES — these are non-negotiable:
- ONLY realistic photography or cinematic photorealistic style — NO cartoons, NO anime, NO fantasy, NO abstract art, NO illustrations, NO paintings
- Image MUST clearly show: milk, dairy products, dairy farming, cows, or FreshGo branding — NOTHING unrelated
- Always include fresh white milk (glass bottles, poured milk, or dairy products) as the hero subject
- Deep green and white color palette — clean, premium, trustworthy
- Include Pakistani / South Asian farm context where relevant (green fields, clay pots, traditional countryside)
- Warm golden morning light, lush green backgrounds
- Commercial advertisement quality — like a professional dairy brand photoshoot
- End with: sharp focus, 4K resolution, professional commercial food photography, photorealistic, award winning
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


def _try_huggingface(prompt: str) -> str | None:
    """Generate AI image via HuggingFace — handles model cold-start retries."""
    from dotenv import load_dotenv
    load_dotenv()
    hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
    if not hf_token:
        print("[Image] No HUGGINGFACE_API_TOKEN set")
        return None

    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
        "runwayml/stable-diffusion-v1-5",
    ]
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Accept": "image/jpeg",
    }

    for model in models:
        print(f"[Image] Trying HuggingFace model: {model}")
        for attempt in range(4):
            try:
                response = requests.post(
                    f"https://router.huggingface.co/hf-inference/models/{model}",
                    headers=headers,
                    json={"inputs": prompt},
                    timeout=120,
                )
                ctype = response.headers.get("content-type", "")
                if response.status_code == 200 and "image" in ctype:
                    filename = f"post_{uuid.uuid4().hex[:8]}.jpg"
                    filepath = os.path.join(STATIC_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    local_url = f"/static/images/{filename}"
                    print(f"[Image] HuggingFace saved ({model}): {local_url}")
                    return local_url

                # Model is loading — wait and retry
                if response.status_code == 503:
                    try:
                        wait = response.json().get("estimated_time", 20)
                    except Exception:
                        wait = 20
                    print(f"[Image] Model loading, waiting {wait}s...")
                    time.sleep(min(wait + 5, 60))
                    continue

                print(f"[Image] HuggingFace {response.status_code}: {response.text[:300]}")
                break  # non-503 error, try next model

            except Exception as e:
                print(f"[Image] HuggingFace exception ({model}): {e}")
                time.sleep(5)

    return None


def _download_and_save(prompt: str) -> str | None:
    """Generate AI image via HuggingFace (Pollinations dropped — now paid for server-side)."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    return _try_huggingface(prompt)


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
