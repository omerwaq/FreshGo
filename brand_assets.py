"""
Brand Assets for Fresh Go.
Stores logo and packet image paths so every generated post stays on-brand.
"""

import json
import os

BRAND_DIR    = os.path.join(os.path.dirname(__file__), "static", "brand")
CONFIG_PATH  = os.path.join(BRAND_DIR, "brand_config.json")

os.makedirs(BRAND_DIR, exist_ok=True)


def _load() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}


def _save(data: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_logo_path() -> str | None:
    """Return absolute filesystem path to the saved logo, or None."""
    cfg = _load()
    rel = cfg.get("logo_path")
    if not rel:
        return None
    full = os.path.join(os.path.dirname(__file__), rel.lstrip("/"))
    return full if os.path.exists(full) else None


def get_packet_path() -> str | None:
    """Return absolute filesystem path to the saved packet image, or None."""
    cfg = _load()
    rel = cfg.get("packet_path")
    if not rel:
        return None
    full = os.path.join(os.path.dirname(__file__), rel.lstrip("/"))
    return full if os.path.exists(full) else None


def save_logo(file_bytes: bytes, ext: str = "png") -> str:
    """Save logo bytes; return web-accessible relative URL."""
    path = os.path.join(BRAND_DIR, f"logo.{ext}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    rel = f"/static/brand/logo.{ext}"
    cfg = _load()
    cfg["logo_path"] = rel
    _save(cfg)
    return rel


def save_packet(file_bytes: bytes, ext: str = "png") -> str:
    """Save packet image bytes; return web-accessible relative URL."""
    path = os.path.join(BRAND_DIR, f"packet.{ext}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    rel = f"/static/brand/packet.{ext}"
    cfg = _load()
    cfg["packet_path"] = rel
    _save(cfg)
    return rel


def get_asset_urls() -> dict:
    """Return {logo_url, packet_url} for the dashboard (web paths)."""
    cfg = _load()
    return {
        "logo_url":   cfg.get("logo_path"),
        "packet_url": cfg.get("packet_path"),
    }


def get_next_theme_index() -> int:
    """Return the next theme index and advance the counter."""
    cfg = _load()
    idx = cfg.get("theme_index", 0)
    cfg["theme_index"] = idx + 1
    _save(cfg)
    return idx
