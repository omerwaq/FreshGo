"""
Facebook & Instagram publishing for Fresh Go.
Handles: Messenger send, FB page posts (text/image/video), Instagram posts/reels.
"""

import os
import requests
from dotenv import load_dotenv
from image_gen import download_image

load_dotenv()

PAGE_ID       = os.getenv("FACEBOOK_PAGE_ID")
ACCESS_TOKEN  = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")   # Instagram Business Account ID
BASE_URL      = os.getenv("BASE_URL", "http://localhost:8000")

FB_API = "https://graph.facebook.com/v19.0"


# ── Messenger ─────────────────────────────────────────────────────────────────

def send_message(recipient_id: str, message: str) -> dict:
    """Send a text message to a Facebook user via Messenger."""
    resp = requests.post(
        f"{FB_API}/me/messages",
        json={
            "recipient": {"id": recipient_id},
            "message":   {"text": message},
            "access_token": ACCESS_TOKEN,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"[FB Messenger Error] {resp.text}")
    return resp.json()


# ── Facebook Page Posts ───────────────────────────────────────────────────────

def publish_post(message: str, image_url: str = None) -> dict:
    """Publish a post to the Fresh Go Facebook page (text or image)."""
    if image_url:
        return _publish_photo_post(message, image_url)
    return _publish_text_post(message)


def _publish_text_post(message: str) -> dict:
    resp = requests.post(
        f"{FB_API}/{PAGE_ID}/feed",
        data={"message": message, "access_token": ACCESS_TOKEN},
        timeout=15,
    )
    result = resp.json()
    if "id" in result:
        print(f"[FB] Text post published! ID: {result['id']}")
    else:
        print(f"[FB Error] {result}")
    return result


def _publish_photo_post(message: str, image_url: str) -> dict:
    try:
        if image_url.startswith("/static/"):
            image_path = os.path.join(os.path.dirname(__file__), image_url.lstrip("/"))
        else:
            image_path = download_image(image_url)

        with open(image_path, "rb") as img_file:
            resp = requests.post(
                f"{FB_API}/{PAGE_ID}/photos",
                data={"caption": message, "access_token": ACCESS_TOKEN},
                files={"source": ("post.jpg", img_file, "image/jpeg")},
                timeout=60,
            )
        result = resp.json()
        if "id" in result or "post_id" in result:
            print(f"[FB] Photo post published! {result}")
        else:
            print(f"[FB Error] {result}")
        return result
    except Exception as e:
        print(f"[FB Photo Error] {e} — falling back to text post")
        return _publish_text_post(message)


def publish_video_to_facebook(message: str, video_path: str) -> dict:
    """Upload and publish a video to the Facebook page."""
    try:
        if video_path.startswith("/static/"):
            abs_path = os.path.join(os.path.dirname(__file__), video_path.lstrip("/"))
        else:
            abs_path = video_path

        with open(abs_path, "rb") as vf:
            resp = requests.post(
                f"{FB_API}/{PAGE_ID}/videos",
                data={"description": message, "access_token": ACCESS_TOKEN},
                files={"source": ("ad.mp4", vf, "video/mp4")},
                timeout=120,
            )
        result = resp.json()
        if "id" in result:
            print(f"[FB] Video published! ID: {result['id']}")
        else:
            print(f"[FB Video Error] {result}")
        return result
    except Exception as e:
        print(f"[FB Video Error] {e}")
        return {"error": str(e)}


# ── Instagram Posts ───────────────────────────────────────────────────────────

def publish_to_instagram(caption: str, image_url: str = None,
                          video_url: str = None) -> dict:
    """
    Publish a photo or video reel to Instagram Business.
    image_url / video_url must be PUBLICLY accessible URLs.
    For local dev, set BASE_URL to your ngrok/production URL.
    """
    if not IG_ACCOUNT_ID:
        print("[Instagram] INSTAGRAM_ACCOUNT_ID not configured — skipping")
        return {"error": "Instagram not configured"}

    if video_url:
        return _publish_ig_video(caption, video_url)
    if image_url:
        return _publish_ig_image(caption, image_url)
    return {"error": "No media provided"}


def _make_public_url(local_path: str) -> str:
    """Convert a /static/... local path to a publicly accessible URL."""
    if local_path.startswith("http"):
        return local_path
    return f"{BASE_URL}{local_path}"


def _publish_ig_image(caption: str, image_url: str) -> dict:
    """Two-step Instagram image post: create container → publish."""
    try:
        public_url = _make_public_url(image_url)

        # Step 1: create media container
        resp = requests.post(
            f"{FB_API}/{IG_ACCOUNT_ID}/media",
            params={
                "image_url":    public_url,
                "caption":      caption,
                "access_token": ACCESS_TOKEN,
            },
            timeout=60,
        )
        result = resp.json()
        creation_id = result.get("id")
        if not creation_id:
            print(f"[Instagram Error] Container creation failed: {result}")
            return result

        # Step 2: publish
        pub_resp = requests.post(
            f"{FB_API}/{IG_ACCOUNT_ID}/media_publish",
            params={"creation_id": creation_id, "access_token": ACCESS_TOKEN},
            timeout=30,
        )
        pub_result = pub_resp.json()
        if "id" in pub_result:
            print(f"[Instagram] Image published! ID: {pub_result['id']}")
        else:
            print(f"[Instagram Error] {pub_result}")
        return pub_result

    except Exception as e:
        print(f"[Instagram Image Error] {e}")
        return {"error": str(e)}


def _publish_ig_video(caption: str, video_url: str) -> dict:
    """Two-step Instagram reel: create container (media_type=REELS) → publish."""
    try:
        public_url = _make_public_url(video_url)

        resp = requests.post(
            f"{FB_API}/{IG_ACCOUNT_ID}/media",
            params={
                "media_type":   "REELS",
                "video_url":    public_url,
                "caption":      caption,
                "share_to_feed": "true",
                "access_token": ACCESS_TOKEN,
            },
            timeout=120,
        )
        result = resp.json()
        creation_id = result.get("id")
        if not creation_id:
            print(f"[Instagram Video Error] Container failed: {result}")
            return result

        # Poll for ready status (up to 60 s)
        for _ in range(12):
            import time
            time.sleep(5)
            status_resp = requests.get(
                f"{FB_API}/{creation_id}",
                params={"fields": "status_code", "access_token": ACCESS_TOKEN},
                timeout=15,
            )
            status = status_resp.json().get("status_code")
            if status == "FINISHED":
                break
            if status == "ERROR":
                return {"error": "Video processing failed on Instagram"}

        pub_resp = requests.post(
            f"{FB_API}/{IG_ACCOUNT_ID}/media_publish",
            params={"creation_id": creation_id, "access_token": ACCESS_TOKEN},
            timeout=30,
        )
        pub_result = pub_resp.json()
        if "id" in pub_result:
            print(f"[Instagram] Reel published! ID: {pub_result['id']}")
        else:
            print(f"[Instagram Error] {pub_result}")
        return pub_result

    except Exception as e:
        print(f"[Instagram Video Error] {e}")
        return {"error": str(e)}
