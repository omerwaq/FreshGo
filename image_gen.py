import requests
import urllib.parse
import os
import uuid
import time
import random

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static", "images")

# ── FreshGo Brand Identity ─────────────────────────────────────────────────────

FRESHGO_DEFAULT_IMAGE_PROMPT = (
    "Create a premium Facebook advertisement for FreshGo dairy products. "
    "Show fresh milk bottles, yogurt, and dairy products in a clean modern setting "
    "with blue and white branding. Use ultra-realistic commercial photography, "
    "professional lighting, healthy family-friendly atmosphere, and a trustworthy "
    "premium dairy brand aesthetic. Include space for promotional text and the "
    "FreshGo logo. High-resolution, social-media-ready, realistic advertising style."
)

FRESHGO_DEFAULT_VIDEO_PROMPT = (
    "Create a 15-30 second cinematic FreshGo dairy advertisement. "
    "Show fresh milk pouring into a glass, dairy farm scenes at sunrise, "
    "yogurt preparation, delivery to homes, and happy customers. "
    "Use smooth camera movements, premium lighting, blue and white branding, "
    "modern commercial style, uplifting background music, and clear space for "
    "FreshGo branding and offer text. Format for Facebook and Instagram Reels (9:16)."
)

# ── Reusable Campaign Templates ────────────────────────────────────────────────

CAMPAIGN_TEMPLATES = {
    "default": {
        "label": "✨ Default Brand Ad",
        "prompt": FRESHGO_DEFAULT_IMAGE_PROMPT,
    },
    "daily_milk": {
        "label": "🥛 Daily Milk Promotion",
        "prompt": (
            "Premium FreshGo fresh milk promotion: chilled glass milk bottles with "
            "condensation on a clean white marble surface, morning soft light, "
            "blue and white FreshGo branding elements, ultra-realistic DSLR product "
            "photography, pristine white background with blue accent, appetizing "
            "dairy ad, professional studio lighting, 8K sharp focus, photorealistic."
        ),
    },
    "yogurt": {
        "label": "🫙 Yogurt Promotion",
        "prompt": (
            "FreshGo fresh thick creamy yogurt in a premium white ceramic bowl, "
            "fresh berries and honey drizzle, clean blue and white brand styling, "
            "top-down professional food photography, soft natural morning light, "
            "modern kitchen counter setting, ultra-realistic commercial dairy ad, "
            "8K sharp focus, photorealistic, award-winning food photography."
        ),
    },
    "morning_delivery": {
        "label": "🌅 Fresh Morning Delivery",
        "prompt": (
            "FreshGo dairy morning delivery scene: fresh milk bottles on a doorstep "
            "at golden sunrise hour, Pakistani neighborhood, blue and white branded "
            "delivery bag, dew on cold glass bottles, warm cinematic golden light, "
            "ultra-realistic commercial photography, trust and freshness mood, "
            "8K DSLR, photorealistic advertising style."
        ),
    },
    "farm_to_home": {
        "label": "🏡 Farm to Home Branding",
        "prompt": (
            "FreshGo farm-to-home story: lush green dairy farm at sunrise in "
            "Pakistan with healthy cows, connected visually to a clean modern "
            "Pakistani home kitchen with fresh milk, blue and white branding "
            "throughout, wide cinematic shot, ultra-realistic commercial photography, "
            "family-friendly premium dairy brand, 8K photorealistic."
        ),
    },
    "eid_seasonal": {
        "label": "🌙 Eid / Seasonal Promotion",
        "prompt": (
            "Festive Eid celebration scene with FreshGo fresh dairy products as "
            "centerpiece: premium milk, yogurt, sweets on a beautifully decorated "
            "Pakistani family table, gold and blue decorations, warm celebratory "
            "lighting, blue and white FreshGo branding, ultra-realistic commercial "
            "photography, premium festive dairy advertisement, 8K photorealistic."
        ),
    },
    "trust_quality": {
        "label": "🏆 Trust & Quality Campaign",
        "prompt": (
            "FreshGo premium quality assurance: gleaming stainless steel dairy "
            "facility, fresh pure white milk being poured into clean glass bottles, "
            "blue and white branding, laboratory-clean modern environment, quality "
            "seal visible, ultra-realistic commercial photography, trustworthy "
            "premium dairy brand aesthetic, 8K DSLR photorealistic."
        ),
    },
}

# ── Platform Aspect Ratios ────────────────────────────────────────────────────

ASPECT_RATIOS = {
    "square":   {"width": 1080, "height": 1080, "label": "1:1 Square — Facebook Post"},
    "portrait": {"width": 1080, "height": 1350, "label": "4:5 Portrait — Instagram Post"},
    "story":    {"width": 1080, "height": 1920, "label": "9:16 Vertical — Stories & Reels"},
    "banner":   {"width": 1920, "height": 1080, "label": "16:9 Landscape — Banner & Ads"},
}

# ── Image System Prompt ────────────────────────────────────────────────────────

IMAGE_SYSTEM_PROMPT = """
You are an expert AI image prompt engineer for FreshGo — a premium Pakistani dairy brand.
Given a campaign topic and base prompt, enhance it with precise technical photography details.

FreshGo Brand Rules (MANDATORY — never break these):
- Brand name: FreshGo | Colors: Royal blue (#0056D2) and clean white
- Always include: fresh milk bottles or dairy products as the hero subject
- Always include: clean modern kitchen, dairy farm, or professional studio setting
- Style: Ultra-realistic DSLR commercial photography — NOT cartoon, NOT anime, NOT fantasy
- Mood: Trustworthy, premium, family-friendly, professional Pakistani dairy brand ad
- End every prompt with: ultra-sharp 8K, Canon EOS DSLR, professional studio lighting, photorealistic

NEVER generate: cartoons, anime, fantasy, sci-fi, abstract art, celebrities,
random unrelated people, unrelated objects, distorted or low-quality images.

Output ONLY the enhanced image prompt (under 130 words). No explanation, no quotes.
"""


def generate_image_prompt_via_ai(topic: str, campaign: str = "default") -> str:
    """Use Groq to enhance a brand-specific image prompt for the topic."""
    template = CAMPAIGN_TEMPLATES.get(campaign, CAMPAIGN_TEMPLATES["default"])
    base_prompt = template["prompt"]

    # If the topic adds custom detail, include it; otherwise just use the template
    user_message = (
        f"Base campaign prompt: {base_prompt}\n"
        f"Custom topic to incorporate: {topic}"
        if topic.strip() else f"Base campaign prompt: {base_prompt}"
    )

    try:
        from groq import Groq
        from dotenv import load_dotenv
        load_dotenv()

        try:
            from brand_analyzer import load_brand_profile
            brand_profile = load_brand_profile()
            brand_context = (
                f"\n\nSAVED BRAND PROFILE (follow this closely):\n{brand_profile}"
                if brand_profile else ""
            )
        except Exception:
            brand_context = ""

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": IMAGE_SYSTEM_PROMPT + brand_context},
                {"role": "user",   "content": user_message}
            ],
            max_tokens=200,
            temperature=0.8,
        )
        prompt = response.choices[0].message.content.strip()
        print(f"[Image Prompt] {prompt}")
        return prompt

    except Exception as e:
        print(f"[Image Prompt Fallback] {e}")
        return base_prompt + f", {topic}" if topic.strip() else base_prompt


def _try_pollinations(prompt: str, width: int = 1080, height: int = 1080) -> str | None:
    """Generate AI image via Pollinations (FLUX model) with retries."""
    encoded = urllib.parse.quote(prompt, safe='')
    for attempt in range(6):
        seed = random.randint(1, 999999)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?model=flux&width={width}&height={height}&nologo=true&seed={seed}"
        )
        print(f"[Image] Pollinations attempt {attempt+1}: seed={seed} {width}x{height}")
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


def _try_together(prompt: str, width: int = 1080, height: int = 1080) -> str | None:
    """Generate AI image via Together AI — FLUX.1-schnell-Free (no cost)."""
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("[Image] No TOGETHER_API_KEY set")
        return None

    # Together AI requires dimensions to be multiples of 32
    w = max(512, (width  // 32) * 32)
    h = max(512, (height // 32) * 32)
    print(f"[Image] Trying Together AI FLUX.1-schnell-Free {w}x{h}...")
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
                "width": w,
                "height": h,
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


def _make_product_ad(product_image_path: str, prompt: str,
                     logo_path: str | None = None) -> str | None:
    """
    Composite the real product image onto an AI-generated background using Pillow.
    Optionally overlays the brand logo in the bottom-right corner.
    """
    try:
        from PIL import Image, ImageFilter
        import base64, io

        os.makedirs(STATIC_DIR, exist_ok=True)

        # Load product image
        if product_image_path.startswith("data:"):
            img_data = product_image_path.split(",", 1)[1]
            product_img = Image.open(io.BytesIO(base64.b64decode(img_data))).convert("RGBA")
        else:
            product_img = Image.open(product_image_path).convert("RGBA")

        # Generate AI background
        bg_prompt = prompt + ", clean studio background, soft gradient, no products, no text, bokeh background"
        bg_path = _try_together(bg_prompt)
        if not bg_path:
            return None

        bg_full = os.path.join(os.path.dirname(__file__), bg_path.lstrip("/"))
        background = Image.open(bg_full).convert("RGBA").resize((1024, 1024))

        # Resize product to fit nicely (65% of canvas height, centered)
        max_h = int(1024 * 0.65)
        ratio = max_h / product_img.height
        new_w = int(product_img.width * ratio)
        product_resized = product_img.resize((new_w, max_h), Image.LANCZOS)

        # Add subtle drop shadow
        shadow = Image.new("RGBA", (new_w + 30, max_h + 30), (0, 0, 0, 0))
        shadow_layer = Image.new("RGBA", (new_w, max_h), (0, 0, 0, 80))
        shadow.paste(shadow_layer, (15, 15))
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))

        # Center-bottom placement
        x = (1024 - new_w) // 2
        y = 1024 - max_h - 60
        background.paste(shadow, (x - 15, y - 15), shadow)
        background.paste(product_resized, (x, y), product_resized)

        # Overlay brand logo in bottom-right corner
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo_max = int(1024 * 0.18)          # 18% of canvas
                logo_ratio = logo_max / max(logo.width, logo.height)
                logo_w = int(logo.width  * logo_ratio)
                logo_h = int(logo.height * logo_ratio)
                logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
                # Semi-transparent
                r, g, b, a = logo.split()
                a = a.point(lambda v: int(v * 0.88))
                logo = Image.merge("RGBA", (r, g, b, a))
                margin = 24
                lx = 1024 - logo_w - margin
                ly = 1024 - logo_h - margin
                background.paste(logo, (lx, ly), logo)
                print("[Image] Logo overlaid on post")
            except Exception as logo_err:
                print(f"[Image] Logo overlay skipped: {logo_err}")

        # Save composite
        filename = f"post_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(STATIC_DIR, filename)
        background.convert("RGB").save(filepath, "JPEG", quality=92)
        print(f"[Image] Product composite saved: /static/images/{filename}")
        return f"/static/images/{filename}"

    except Exception as e:
        print(f"[Image] Composite error: {e}")
        return None


def _download_and_save(prompt: str, width: int = 1080, height: int = 1080) -> str | None:
    """Generate AI image — Together AI primary, Pollinations fallback."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    result = _try_together(prompt, width, height)
    if result:
        return result
    print("[Image] Together AI failed — trying Pollinations fallback...")
    return _try_pollinations(prompt, width, height)


async def fetch_and_save_image(topic: str, aspect_ratio: str = "square",
                                campaign: str = "default") -> str | None:
    """Async: generate brand prompt via Groq, then generate image at requested aspect ratio."""
    try:
        import asyncio
        dims   = ASPECT_RATIOS.get(aspect_ratio, ASPECT_RATIOS["square"])
        prompt = generate_image_prompt_via_ai(topic, campaign)
        local_url = await asyncio.to_thread(
            _download_and_save, prompt, dims["width"], dims["height"]
        )
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
