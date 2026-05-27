# Simple in-memory state tracker
# Tracks users who have a post pending confirmation

pending_posts = {}  # { user_id: "post content string" }


def set_pending_post(user_id: str, post_content: str):
    pending_posts[user_id] = post_content


def get_pending_post(user_id: str):
    return pending_posts.get(user_id)


def clear_pending_post(user_id: str):
    pending_posts.pop(user_id, None)


def has_pending_post(user_id: str) -> bool:
    return user_id in pending_posts
