"""
HD video ad generator for Fresh Go.
Creates 1080x1080 MP4 slideshow ads from Pollinations images + Pillow text overlays.
Requires: imageio[ffmpeg], Pillow
"""

import os
import asyncio
import uuid
import textwrap
from pathlib import Path

STATIC_DIR  = os.path.join(os.path.dirname(__file__), "static")
VIDEOS_DIR  = os.path.join(STATIC_DIR, "videos")
IMAGES_DIR  = os.path.join(STATIC_DIR, "images")

# FreshGo brand colors — blue and white
BRAND_BLUE = (0, 86, 210)      # #0056D2 royal blue
WHITE      = (255, 255, 255)
BLACK      = (0, 0, 0)
OVERLAY_BG = (0, 20, 60, 180)  # deep blue-tinted semi-transparent overlay


def _get_font(size: int):
    """Return a PIL font — falls back to default if custom fonts unavailable."""
    from PIL import ImageFont
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _add_text_overlay(img, title: str, subtitle: str, cta: str):
    """Add Fresh Go branded text overlay to a PIL Image."""
    from PIL import Image, ImageDraw

    img = img.convert("RGBA")
    W, H = img.size

    # Semi-transparent bottom band
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_o  = ImageDraw.Draw(overlay)
    band_h  = int(H * 0.30)
    draw_o.rectangle([(0, H - band_h), (W, H)], fill=OVERLAY_BG)

    # Green accent line above text band
    draw_o.rectangle([(0, H - band_h - 6), (W, H - band_h)], fill=BRAND_BLUE + (255,))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    font_title    = _get_font(52)
    font_subtitle = _get_font(36)
    font_cta      = _get_font(32)

    # Title
    title_y = H - band_h + 18
    draw.text((W // 2, title_y), title, font=font_title,
              fill=WHITE, anchor="mt", stroke_width=1, stroke_fill=BLACK)

    # Subtitle (wrapped)
    sub_lines = textwrap.wrap(subtitle, width=38)
    sub_y = title_y + 65
    for line in sub_lines[:2]:
        draw.text((W // 2, sub_y), line, font=font_subtitle,
                  fill=(220, 220, 220), anchor="mt")
        sub_y += 42

    # CTA with green pill
    cta_y = H - 44
    cta_bbox = draw.textbbox((0, 0), cta, font=font_cta)
    cta_w = cta_bbox[2] - cta_bbox[0] + 40
    cta_x = (W - cta_w) // 2
    draw.rounded_rectangle(
        [(cta_x, cta_y - 6), (cta_x + cta_w, cta_y + 36)],
        radius=18, fill=BRAND_BLUE
    )
    draw.text((W // 2, cta_y + 15), cta, font=font_cta,
              fill=WHITE, anchor="mm")

    return img.convert("RGB")


def _build_frame(img_path: str, title: str, subtitle: str, cta: str,
                  width: int = 1080, height: int = 1080):
    """Load image, resize to target dimensions, add overlay. Returns PIL Image."""
    from PIL import Image
    img = Image.open(img_path).convert("RGB")
    img = img.resize((width, height), Image.LANCZOS)
    return _add_text_overlay(img, title, subtitle, cta)


def _crossfade_frames(img1, img2, n_frames: int = 18):
    """Generate crossfade numpy frames between two PIL images."""
    import numpy as np
    from PIL import Image
    arr1 = np.array(img1, dtype=float)
    arr2 = np.array(img2, dtype=float)
    for i in range(n_frames):
        alpha = i / n_frames
        blended = ((1 - alpha) * arr1 + alpha * arr2).astype("uint8")
        yield blended


def _write_video(frames_iter, output_path: str, fps: int = 24):
    """Write frames to MP4 using imageio + ffmpeg."""
    import imageio
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    writer = imageio.get_writer(
        output_path, fps=fps, codec="libx264",
        quality=8, pixelformat="yuv420p",
        output_params=["-movflags", "+faststart"]
    )
    for frame in frames_iter:
        writer.append_data(frame)
    writer.close()


def _generate_video_sync(image_paths: list[str], title: str, subtitle: str,
                          cta: str, hold_secs: int = 4, fps: int = 24,
                          width: int = 1080, height: int = 1080) -> str:
    """
    Blocking video generation — run via asyncio.to_thread().
    Returns local URL of the saved video (/static/videos/<uuid>.mp4).
    """
    import numpy as np

    hold_frames    = hold_secs * fps
    crossfade_n    = fps // 2

    slides = [_build_frame(p, title, subtitle, cta, width, height) for p in image_paths]

    def _all_frames():
        for idx, slide in enumerate(slides):
            arr = np.array(slide)
            for _ in range(hold_frames):
                yield arr
            # crossfade into next slide
            if idx < len(slides) - 1:
                yield from _crossfade_frames(slide, slides[idx + 1], crossfade_n)

    filename    = f"{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(VIDEOS_DIR, filename)
    _write_video(_all_frames(), output_path, fps=fps)

    local_url = f"/static/videos/{filename}"
    print(f"[Video] Saved → {local_url}")
    return local_url


# ── Public async API ──────────────────────────────────────────────────────────

async def generate_video_ad(topic: str, n_images: int = 3) -> dict:
    """
    Generate a branded video ad for the given topic.
    1. Generates n_images product images via existing Pollinations pipeline
    2. Creates a 1080x1080 MP4 slideshow with text overlays + crossfades
    Returns {"video_url": "/static/videos/<id>.mp4", "image_url": first image}
    """
    from image_gen import fetch_and_save_image

    # Collect real file paths, not just URLs
    image_tasks = [fetch_and_save_image(f"{topic} slide {i+1}") for i in range(n_images)]
    local_urls  = await asyncio.gather(*image_tasks)
    valid_urls  = [u for u in local_urls if u]

    if not valid_urls:
        print("[Video] No images generated — cannot create video")
        return {"video_url": None, "image_url": None}

    # Map /static/... URL → absolute file path
    base = os.path.dirname(__file__)
    image_paths = [os.path.join(base, u.lstrip("/")) for u in valid_urls]

    # Title / subtitle / CTA for the overlay
    title    = "FreshGo 🥛"
    subtitle = f"{topic} — 100% Pure Farm-Fresh Dairy"
    cta      = "Order Now: WhatsApp 0300-3147887"

    # 9:16 reels format for stories/TikTok, otherwise square
    vid_w, vid_h = 1080, 1080

    try:
        video_url = await asyncio.to_thread(
            _generate_video_sync, image_paths, title, subtitle, cta,
            4, 24, vid_w, vid_h
        )
    except Exception as e:
        print(f"[Video Error] {e}")
        return {"video_url": None, "image_url": valid_urls[0] if valid_urls else None}

    return {"video_url": video_url, "image_url": valid_urls[0]}
