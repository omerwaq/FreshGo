"""
Brand Analyzer — fetches Fresh Go's Facebook page images,
analyzes visual style with Groq vision, saves brand profile.
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

BRAND_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "brand_profile.json")
FB_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")


def _get_page_images(limit: int = 6) -> list[str]:
    """Fetch recent post image URLs from the Facebook page."""
    urls = []
    try:
        # Get recent posts with attachments
        resp = requests.get(
            f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/posts",
            params={
                "fields": "attachments{media,type}",
                "limit": 20,
                "access_token": FB_TOKEN,
            },
            timeout=15,
        )
        data = resp.json()
        for post in data.get("data", []):
            attachments = post.get("attachments", {}).get("data", [])
            for att in attachments:
                media = att.get("media", {})
                img = media.get("image", {})
                url = img.get("src")
                if url:
                    urls.append(url)
                if len(urls) >= limit:
                    break
            if len(urls) >= limit:
                break
    except Exception as e:
        print(f"[Brand] Error fetching FB posts: {e}")

    # Also get page profile/cover photos
    try:
        resp = requests.get(
            f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}",
            params={
                "fields": "picture.type(large),cover",
                "access_token": FB_TOKEN,
            },
            timeout=10,
        )
        data = resp.json()
        pic = data.get("picture", {}).get("data", {}).get("url")
        cover = data.get("cover", {}).get("source")
        if pic:
            urls.insert(0, pic)
        if cover:
            urls.insert(0, cover)
    except Exception as e:
        print(f"[Brand] Error fetching page photos: {e}")

    return urls[:limit]


def _analyze_images_with_vision(image_urls: list[str]) -> str:
    """Use Groq vision to analyze brand style from multiple images."""
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    analyses = []
    for i, url in enumerate(image_urls[:4]):
        try:
            print(f"[Brand] Analyzing image {i+1}/{min(len(image_urls), 4)}: {url[:60]}...")
            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": url}},
                        {
                            "type": "text",
                            "text": (
                                "Analyze this Fresh Go dairy brand image. Extract: "
                                "1) Packaging design (colors, shape, logo style) "
                                "2) Photography style "
                                "3) Color palette used "
                                "4) Typography/text style if visible "
                                "5) Overall brand aesthetic "
                                "Under 80 words."
                            )
                        }
                    ]
                }],
                max_tokens=150,
            )
            analyses.append(response.choices[0].message.content.strip())
        except Exception as e:
            print(f"[Brand] Vision error on image {i+1}: {e}")

    if not analyses:
        return ""

    # Summarize all analyses into one brand profile
    try:
        summary_resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": (
                    f"Based on these analyses of {len(analyses)} Fresh Go brand images:\n\n"
                    + "\n\n".join(f"Image {i+1}: {a}" for i, a in enumerate(analyses))
                    + "\n\nCreate a concise brand style guide (under 120 words) that can be used "
                    "to generate new AI images consistent with this brand. Include: "
                    "exact colors, packaging style, photography mood, and key visual elements."
                )
            }],
            max_tokens=200,
        )
        return summary_resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Brand] Summary error: {e}")
        return "\n".join(analyses)


def analyze_facebook_page(page_url: str = None) -> dict:
    """
    Full pipeline: fetch page images → analyze with vision → save brand profile.
    Returns {"success": bool, "profile": str, "images_analyzed": int}
    """
    print(f"[Brand] Starting Facebook page analysis...")

    image_urls = _get_page_images(limit=6)
    if not image_urls:
        return {
            "success": False,
            "profile": "",
            "images_analyzed": 0,
            "message": "Koi images nahi mili Facebook page se. Make sure page public hai aur token valid hai."
        }

    print(f"[Brand] Found {len(image_urls)} images to analyze")
    brand_profile = _analyze_images_with_vision(image_urls)

    if brand_profile:
        # Save to file for persistent use
        profile_data = {
            "brand_profile": brand_profile,
            "images_analyzed": len(image_urls),
            "page_url": page_url or f"facebook.com/{FB_PAGE_ID}",
            "sample_images": image_urls[:3],
        }
        with open(BRAND_PROFILE_PATH, "w") as f:
            json.dump(profile_data, f, indent=2)
        print(f"[Brand] Profile saved to {BRAND_PROFILE_PATH}")
        return {"success": True, "profile": brand_profile,
                "images_analyzed": len(image_urls), "message": "Brand profile saved!"}

    return {"success": False, "profile": "", "images_analyzed": 0,
            "message": "Vision analysis failed. Try again."}


def load_brand_profile() -> str:
    """Load saved brand profile, returns empty string if none exists."""
    try:
        if os.path.exists(BRAND_PROFILE_PATH):
            with open(BRAND_PROFILE_PATH) as f:
                data = json.load(f)
            return data.get("brand_profile", "")
    except Exception:
        pass
    return ""
