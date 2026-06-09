"""
APScheduler-based post scheduler for Fresh Go.
Checks every 60 seconds for posts/videos due to publish on Facebook or Instagram.
"""

import asyncio
import os
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler


_scheduler: AsyncIOScheduler | None = None


def start_scheduler():
    """Start the background scheduler. Call once at app startup."""
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Asia/Karachi")

    # Publish pending scheduled posts every 60 s
    _scheduler.add_job(
        _publish_due_posts,
        trigger="interval",
        seconds=60,
        id="publish_scheduled_posts",
        replace_existing=True,
    )

    # Auto-generate + schedule weekly branded post every Sunday at 09:00 AM PKT
    _scheduler.add_job(
        _auto_generate_weekly_post,
        trigger="cron",
        day_of_week="sun",
        hour=9,
        minute=0,
        id="weekly_auto_post",
        replace_existing=True,
    )

    _scheduler.start()
    print("[Scheduler] Started — 60 s publish check + weekly Sunday 9 AM post ✅")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


# ── Core Job ──────────────────────────────────────────────────────────────────

async def _publish_due_posts():
    """Fetch all pending posts whose scheduled_time has passed and publish them."""
    from database import get_pending_scheduled_posts, update_scheduled_post_status

    due = get_pending_scheduled_posts()
    if not due:
        return

    print(f"[Scheduler] {len(due)} post(s) due — publishing now")

    for post in due:
        try:
            await _publish_one(post)
            update_scheduled_post_status(post["id"], "published")
            print(f"[Scheduler] Post #{post['id']} published ✅ ({post['platform']})")
        except Exception as e:
            err = str(e)
            update_scheduled_post_status(post["id"], "failed", error_msg=err)
            print(f"[Scheduler] Post #{post['id']} FAILED: {err}")


async def _publish_one(post: dict):
    """Publish a single scheduled post to the target platform(s)."""
    from facebook import publish_post, publish_to_instagram, publish_video_to_facebook

    platform   = post.get("platform", "facebook")
    post_type  = post.get("post_type", "image")
    post_text  = post.get("post_text", "")
    image_path = post.get("image_path")
    video_path = post.get("video_path")

    tasks = []

    if platform in ("facebook", "both"):
        if post_type == "video" and video_path:
            tasks.append(asyncio.to_thread(publish_video_to_facebook, post_text, video_path))
        else:
            tasks.append(asyncio.to_thread(publish_post, post_text, image_path))

    if platform in ("instagram", "both"):
        if post_type == "video" and video_path:
            tasks.append(asyncio.to_thread(publish_to_instagram, post_text, None, video_path))
        else:
            tasks.append(asyncio.to_thread(publish_to_instagram, post_text, image_path, None))

    if tasks:
        await asyncio.gather(*tasks)


# ── Weekly Auto-Post ──────────────────────────────────────────────────────────

async def _auto_generate_weekly_post():
    """Generate a creative weekly post and publish it directly to Facebook."""
    from weekly_posts import generate_weekly_post
    from facebook import publish_post

    print("[Scheduler] Generating weekly branded post...")
    try:
        result = await generate_weekly_post()
        post_text  = result["text"]
        image_url  = result.get("image_url")
        theme_slug = result.get("theme_slug", "unknown")

        await asyncio.to_thread(publish_post, post_text, image_url)
        print(f"[Scheduler] Weekly post published ✅ — theme: {theme_slug}")
    except Exception as e:
        print(f"[Scheduler] Weekly post FAILED: {e}")


# ── Helper used by admin commands ─────────────────────────────────────────────

def parse_schedule_command(text: str) -> dict | None:
    """
    Parse: !schedule <topic> | <DD-MM-YYYY> <HH:MM> <fb|ig|both> [post|video]
    Returns {topic, date_str, time_str, platform, post_type} or None on parse error.

    Example:
        !schedule Eid sale on milk | 30-03-2025 10:00 both video
    """
    try:
        raw = text[len("!schedule"):].strip()
        parts = raw.split("|")
        if len(parts) != 2:
            return None

        topic     = parts[0].strip()
        remainder = parts[1].strip().split()

        if len(remainder) < 3:
            return None

        date_str  = remainder[0]        # DD-MM-YYYY
        time_str  = remainder[1]        # HH:MM
        platform  = remainder[2].lower()  # fb|ig|both -> facebook|instagram|both
        post_type = remainder[3].lower() if len(remainder) > 3 else "post"

        # Normalise platform aliases
        platform_map = {"fb": "facebook", "ig": "instagram", "both": "both",
                        "facebook": "facebook", "instagram": "instagram"}
        platform = platform_map.get(platform, "facebook")

        # Normalise post type
        post_type = "video" if post_type == "video" else "image"

        # Validate datetime
        scheduled_dt = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
        scheduled_str = scheduled_dt.strftime("%Y-%m-%d %H:%M")

        return {
            "topic":      topic,
            "platform":   platform,
            "post_type":  post_type,
            "scheduled":  scheduled_str,
            "display_dt": scheduled_dt.strftime("%d %b %Y at %I:%M %p"),
        }
    except Exception as e:
        print(f"[Schedule Parse Error] {e}")
        return None
