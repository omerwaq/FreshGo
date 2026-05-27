import os
import requests
from dotenv import load_dotenv
from image_gen import download_image

load_dotenv()

PAGE_ID      = os.getenv("FACEBOOK_PAGE_ID")
ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")


def send_message(recipient_id: str, message: str):
    """Send a text message to a Facebook user via Messenger."""
    url = "https://graph.facebook.com/v19.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "access_token": ACCESS_TOKEN
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"[Facebook Error] Send message failed: {response.text}")
    return response.json()


def publish_post(message: str, image_url: str = None) -> dict:
    """
    Publish a post to the Fresh Go Facebook page.
    If image_url is provided, posts as a photo with caption.
    """
    if image_url:
        return _publish_photo_post(message, image_url)
    return _publish_text_post(message)


def _publish_text_post(message: str) -> dict:
    """Post text-only to the page feed."""
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    payload = {"message": message, "access_token": ACCESS_TOKEN}
    response = requests.post(url, data=payload)
    result = response.json()
    if "id" in result:
        print(f"[Facebook] Text post published! ID: {result['id']}")
    else:
        print(f"[Facebook Error] {result}")
    return result


def _publish_photo_post(message: str, image_url: str) -> dict:
    """Upload local image and post it with a caption to the page."""
    try:
        # image_url is now a local path like /static/images/abc.jpg
        if image_url.startswith("/static/"):
            image_path = os.path.join(os.path.dirname(__file__), image_url.lstrip("/"))
        else:
            # Fallback: download from remote URL
            image_path = download_image(image_url)

        print(f"[Image] Uploading from {image_path}")
        url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
        with open(image_path, "rb") as img_file:
            response = requests.post(
                url,
                data={"caption": message, "access_token": ACCESS_TOKEN},
                files={"source": ("post.jpg", img_file, "image/jpeg")}
            )

        result = response.json()
        if "id" in result or "post_id" in result:
            print(f"[Facebook] Photo post published! {result}")
        else:
            print(f"[Facebook Error] {result}")
        return result

    except Exception as e:
        print(f"[Facebook Photo Error] {e} — falling back to text post")
        return _publish_text_post(message)
