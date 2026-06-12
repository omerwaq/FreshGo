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

    # Try free model first, fall back to schnell if needed
    for model in ["black-forest-labs/FLUX.1-schnell-Free", "black-forest-labs/FLUX.1-schnell"]:
        print(f"[Image] Trying Together AI {model} {w}x{h}...")
        try:
            response = requests.post(
                "https://api.together.xyz/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "width": w,
                    "height": h,
                    "steps": 4,
                    "n": 1,
                },
                timeout=120,
            )
            print(f"[Image] Together AI {model} response {response.status_code}: {response.text[:300]}")
            if response.status_code == 200:
                import base64
                data = response.json()
                item = data["data"][0]

                if "url" in item:
                    img_response = requests.get(item["url"], timeout=60)
                    img_response.raise_for_status()
                    img_bytes = img_response.content
                elif "b64_json" in item:
                    img_bytes = base64.b64decode(item["b64_json"])
                else:
                    print(f"[Image] Together AI unknown format: {list(item.keys())}")
                    continue

                filename = f"post_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(STATIC_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                local_url = f"/static/images/{filename}"
                print(f"[Image] Together AI saved: {local_url}")
                return local_url
            else:
                print(f"[Image] Together AI {model} failed ({response.status_code}), trying next model...")
        except Exception as e:
            print(f"[Image] Together AI {model} exception: {e}")
    return None


def _try_huggingface(prompt: str, width: int = 1024, height: int = 1024) -> str | None:
    """Generate image via HuggingFace Inference API (free with HF_TOKEN)."""
    hf_token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
    headers = {"Content-Type": "application/json"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
    else:
        print("[Image] No HUGGINGFACE_TOKEN set — trying HF without auth (rate-limited)...")

    # Clamp to safe dimensions for HF
    w = min(max(512, (width // 64) * 64), 1024)
    h = min(max(512, (height // 64) * 64), 1024)

    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
    ]
    for model in models:
        url = f"https://api-inference.huggingface.co/models/{model}"
        print(f"[Image] Trying HuggingFace {model} {w}x{h}...")
        try:
            r = requests.post(
                url, headers=headers,
                json={"inputs": prompt, "parameters": {"width": w, "height": h}},
                timeout=120,
            )
            if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                filename = f"post_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(STATIC_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(r.content)
                local_url = f"/static/images/{filename}"
                print(f"[Image] HuggingFace saved: {local_url}")
                return local_url
            else:
                print(f"[Image] HuggingFace {model} → {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"[Image] HuggingFace {model} error: {e}")
    return None


def _make_product_ad(product_image_path: str, prompt: str,
                     logo_path: str | None = None) -> str | None:
    """
    Composite the real FreshGo product image onto a clean AI-generated background.
    The background prompt is intentionally kept product-free so no random bottles
    or competitor brands appear — only a clean setting behind the real packet.
    """
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        import base64, io

        os.makedirs(STATIC_DIR, exist_ok=True)

        # Load product image
        if product_image_path.startswith("data:"):
            img_data = product_image_path.split(",", 1)[1]
            product_img = Image.open(io.BytesIO(base64.b64decode(img_data))).convert("RGBA")
        else:
            product_img = Image.open(product_image_path).convert("RGBA")

        # ── Auto-crop front panel if this looks like a flat packaging layout ──
        # Flat layouts are significantly wider than tall (ratio > 1.4).
        # Crop the left 52% which is the front/display face of the packet.
        pw, ph = product_img.size
        if pw > ph * 1.4:
            crop_x = int(pw * 0.52)
            product_img = product_img.crop((0, 0, crop_x, ph))
            print(f"[Image] Flat layout detected — cropped to front panel: {crop_x}x{ph}")

        # ── Auto-remove background so only the packet shape remains ──────────
        try:
            from rembg import remove as rembg_remove
            import io as _io
            buf = _io.BytesIO()
            product_img.save(buf, format="PNG")
            buf.seek(0)
            cleaned = rembg_remove(buf.read())
            product_img = Image.open(_io.BytesIO(cleaned)).convert("RGBA")
            print("[Image] Background removed from product image ✅")
        except Exception as rmbg_err:
            print(f"[Image] rembg skipped (using original): {rmbg_err}")

        # ── Background prompt — NEVER include product/bottle/dairy mentions ──
        # We extract only the setting/mood words from the topic, not the product.
        # This prevents the AI from generating competitor bottles or random dairy.
        bg_prompt = (
            "Clean empty modern kitchen background, blue and white color scheme, "
            "soft natural morning light coming through window, smooth marble counter surface, "
            "very soft bokeh blur, no people, absolutely NO products NO bottles NO containers "
            "NO food items NO dairy items NO text, pure clean background only, "
            "professional advertising studio backdrop, ultra-realistic, 8K photography"
        )
        bg_path = _try_together(bg_prompt)
        if not bg_path:
            bg_path = _try_huggingface(bg_prompt)
        if not bg_path:
            bg_path = _try_pollinations(bg_prompt)

        if bg_path:
            bg_full = os.path.join(os.path.dirname(__file__), bg_path.lstrip("/"))
            background = Image.open(bg_full).convert("RGBA").resize((1024, 1024))
            bg_rgb = background.convert("RGB")
            bg_rgb = ImageEnhance.Brightness(bg_rgb).enhance(1.05)
            bg_rgb = ImageEnhance.Contrast(bg_rgb).enhance(1.1)
            background = bg_rgb.convert("RGBA")
        else:
            # ── Pillow-only fallback: premium blue gradient background ──────
            print("[Image] All AI APIs failed — generating gradient background with Pillow")
            import numpy as np
            W, H = 1024, 1024
            background = Image.new("RGBA", (W, H))
            # Vertical gradient: deep navy at top → royal blue → light blue at bottom
            top    = (0,  30, 100)
            mid    = (0,  86, 210)
            bottom = (80, 160, 255)
            pixels = []
            for y in range(H):
                t = y / H
                if t < 0.5:
                    r2 = t * 2
                    c = tuple(int(top[i]*(1-r2) + mid[i]*r2) for i in range(3)) + (255,)
                else:
                    r2 = (t - 0.5) * 2
                    c = tuple(int(mid[i]*(1-r2) + bottom[i]*r2) for i in range(3)) + (255,)
                pixels.extend([c] * W)
            background.putdata(pixels)
            # Add soft radial light burst in centre
            from PIL import ImageDraw, ImageFilter
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            for r in range(300, 0, -10):
                alpha = int(30 * (1 - r/300))
                draw.ellipse([W//2-r, H//2-r, W//2+r, H//2+r], fill=(255,255,255,alpha))
            overlay = overlay.filter(ImageFilter.GaussianBlur(40))
            background = Image.alpha_composite(background, overlay)

        # Resize product — fill 82% of canvas height, cap width at 80% of canvas
        canvas = 1024
        max_h  = int(canvas * 0.82)
        max_w  = int(canvas * 0.80)
        ratio  = min(max_h / product_img.height, max_w / product_img.width)
        new_h  = int(product_img.height * ratio)
        new_w  = int(product_img.width  * ratio)
        product_resized = product_img.resize((new_w, new_h), Image.LANCZOS)

        # Deep drop shadow
        shadow_pad = 50
        shadow = Image.new("RGBA", (new_w + shadow_pad*2, new_h + shadow_pad*2), (0,0,0,0))
        shadow_layer = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 130))
        shadow.paste(shadow_layer, (shadow_pad, shadow_pad))
        shadow = shadow.filter(ImageFilter.GaussianBlur(28))

        # Centre horizontally, sit near bottom with a little padding
        x = (canvas - new_w) // 2
        y = canvas - new_h - 30
        background.paste(shadow, (x - shadow_pad, y - shadow_pad + 20), shadow)
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


def _make_pillow_placeholder(topic: str = "", width: int = 1024, height: int = 1024) -> str | None:
    """Last-resort: generate a branded FreshGo placeholder image using only Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        os.makedirs(STATIC_DIR, exist_ok=True)
        W, H = width, height

        # Blue gradient background
        img = Image.new("RGBA", (W, H))
        top, mid, bot = (0, 30, 100), (0, 86, 210), (80, 160, 255)
        pixels = []
        for y in range(H):
            t = y / H
            if t < 0.5:
                r2 = t * 2
                c = tuple(int(top[i]*(1-r2) + mid[i]*r2) for i in range(3)) + (255,)
            else:
                r2 = (t - 0.5) * 2
                c = tuple(int(mid[i]*(1-r2) + bot[i]*r2) for i in range(3)) + (255,)
            pixels.extend([c] * W)
        img.putdata(pixels)

        # Soft white glow
        ov = Image.new("RGBA", (W, H), (0,0,0,0))
        d  = ImageDraw.Draw(ov)
        for r in range(min(W,H)//3, 0, -8):
            d.ellipse([W//2-r, H//2-r, W//2+r, H//2+r], fill=(255,255,255, int(25*(1-r/(min(W,H)/3)))))
        img = Image.alpha_composite(img, ov.filter(ImageFilter.GaussianBlur(30)))

        # FreshGo text
        draw = ImageDraw.Draw(img)
        try:
            fnt_big = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", min(W//6, 120), index=7)
            fnt_sm  = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", min(W//16, 50), index=3)
        except Exception:
            fnt_big = fnt_sm = ImageFont.load_default()

        brand = "FreshGo"
        bw = int(draw.textlength(brand, font=fnt_big))
        draw.text(((W-bw)//2 + 2, H//2 - 80 + 2), brand, fill=(0,30,100,180), font=fnt_big)
        draw.text(((W-bw)//2,     H//2 - 80),      brand, fill=(255,255,255,255), font=fnt_big)

        tag = topic[:50] if topic else "Pure Farm Dairy"
        tw  = int(draw.textlength(tag, font=fnt_sm))
        draw.text(((W-tw)//2, H//2 + 60), tag, fill=(180,220,255,230), font=fnt_sm)

        filename = f"post_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(STATIC_DIR, filename)
        img.convert("RGB").save(filepath, "JPEG", quality=92)
        print(f"[Image] Pillow placeholder saved: /static/images/{filename}")
        return f"/static/images/{filename}"
    except Exception as e:
        print(f"[Image] Pillow placeholder failed: {e}")
        return None


def _download_and_save(prompt: str, width: int = 1080, height: int = 1080) -> str | None:
    """Generate AI image — tries Together AI → HuggingFace → Pollinations → Pillow fallback."""
    os.makedirs(STATIC_DIR, exist_ok=True)

    result = _try_together(prompt, width, height)
    if result:
        return result

    print("[Image] Together AI failed — trying HuggingFace...")
    result = _try_huggingface(prompt, width, height)
    if result:
        return result

    print("[Image] HuggingFace failed — trying Pollinations...")
    result = _try_pollinations(prompt, width, height)
    if result:
        return result

    print("[Image] All AI APIs failed — using Pillow branded placeholder...")
    return _make_pillow_placeholder(prompt, width, height)


async def fetch_and_save_image(topic: str, aspect_ratio: str = "square",
                                campaign: str = "default") -> str | None:
    """Async: generate brand prompt via Groq, then generate image at requested aspect ratio.
    If a FreshGo packet image has been uploaded, composites it onto an AI background."""
    try:
        import asyncio
        dims   = ASPECT_RATIOS.get(aspect_ratio, ASPECT_RATIOS["square"])
        prompt = generate_image_prompt_via_ai(topic, campaign)

        # Use uploaded packet image if available — composite it onto AI background
        from brand_assets import get_packet_path, get_logo_path
        packet_path = get_packet_path()
        if packet_path:
            print(f"[Image] Using uploaded FreshGo packet: {packet_path}")
            logo_path = get_logo_path()
            local_url = await asyncio.to_thread(
                _make_product_ad, packet_path, prompt, logo_path
            )
            if local_url:
                return local_url
            print("[Image] Product ad composite failed — falling back to plain AI image")

        # No packet uploaded or composite failed — generate plain AI image
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
