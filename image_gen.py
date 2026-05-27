import requests
import urllib.parse
import os
import uuid

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static", "images")

FRESH_GO_STYLE = (
    "professional food photography, dairy farm, fresh milk, "
    "bright natural lighting, clean background, high quality, photorealistic"
)


def build_image_prompt(topic: str) -> str:
    return f"Fresh Go dairy farm: {topic}, {FRESH_GO_STYLE}"


def fetch_and_save_image(topic: str) -> str | None:
    """
    Download image from Pollinations server-side (bypasses browser auth issues).
    Saves to static/images/ and returns the local URL path like /static/images/abc.jpg
    """
    try:
        prompt  = build_image_prompt(topic)
        encoded = urllib.parse.quote(prompt)
        # Use model=flux for anonymous access — no login required
        url = f"{POLLINATIONS_URL.format(prompt=encoded)}?width=1024&height=1024&model=flux&nologo=true"

        print(f"[Image] Fetching from Pollinations...")
        headers = {"User-Agent": "FreshGoBot/1.0"}  # plain user-agent, no cookies
        response = requests.get(url, timeout=60, stream=True, headers=headers)
        response.raise_for_status()

        # Save to static folder
        os.makedirs(STATIC_DIR, exist_ok=True)
        filename  = f"{uuid.uuid4().hex}.jpg"
        filepath  = os.path.join(STATIC_DIR, filename)

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        local_url = f"/static/images/{filename}"
        print(f"[Image] Saved → {local_url}")
        return local_url

    except Exception as e:
        print(f"[Image Error] {e}")
        return None


def download_image(image_url: str) -> str:
    """Download an already-known image URL to a temp path (used for FB publishing)."""
    import tempfile
    response = requests.get(image_url, timeout=60, stream=True)
    response.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    for chunk in response.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name
