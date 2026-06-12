"""
Brand Assets for FreshGo.
Images are saved to both the local filesystem (fast reads) and SQLite (persistence).
On Railway, the filesystem resets on each deployment; the DB restore ensures
the files are always available after startup.
"""

import base64
import json
import os

BRAND_DIR   = os.path.join(os.path.dirname(__file__), "static", "brand")
CONFIG_PATH = os.path.join(BRAND_DIR, "brand_config.json")


def _ensure_dir():
    os.makedirs(BRAND_DIR, exist_ok=True)


def _load() -> dict:
    _ensure_dir()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(data: dict):
    _ensure_dir()
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Internal: restore a single asset file from DB ─────────────────────────────

def _restore_file(key: str) -> str | None:
    """Decode base64 from DB → write file → return web URL, or None if not in DB."""
    try:
        from database import get_brand_asset_db
        asset = get_brand_asset_db(key)
        if not asset:
            return None
        _ensure_dir()
        file_bytes = base64.b64decode(asset["data_b64"])
        ext  = asset["ext"]
        path = os.path.join(BRAND_DIR, f"{key}.{ext}")
        with open(path, "wb") as f:
            f.write(file_bytes)
        rel = f"/static/brand/{key}.{ext}"
        cfg = _load()
        cfg[f"{key}_path"] = rel
        _save(cfg)
        print(f"[Brand] Restored {key} from DB → {rel}")
        return rel
    except Exception as e:
        print(f"[Brand] Restore {key} failed: {e}")
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def save_logo(file_bytes: bytes, ext: str = "png") -> str:
    _ensure_dir()
    path = os.path.join(BRAND_DIR, f"logo.{ext}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    rel = f"/static/brand/logo.{ext}"
    cfg = _load()
    cfg["logo_path"] = rel
    _save(cfg)
    # Persist to DB so it survives Railway filesystem resets
    try:
        from database import save_brand_asset_db
        save_brand_asset_db("logo", base64.b64encode(file_bytes).decode(), ext)
    except Exception as e:
        print(f"[Brand] DB save logo failed: {e}")
    return rel


def save_packet(file_bytes: bytes, ext: str = "png") -> str:
    _ensure_dir()
    path = os.path.join(BRAND_DIR, f"packet.{ext}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    rel = f"/static/brand/packet.{ext}"
    cfg = _load()
    cfg["packet_path"] = rel
    _save(cfg)
    try:
        from database import save_brand_asset_db
        save_brand_asset_db("packet", base64.b64encode(file_bytes).decode(), ext)
    except Exception as e:
        print(f"[Brand] DB save packet failed: {e}")
    return rel


def get_logo_path() -> str | None:
    cfg = _load()
    rel = cfg.get("logo_path")
    if rel:
        full = os.path.join(os.path.dirname(__file__), rel.lstrip("/"))
        if os.path.exists(full):
            return full
    # File missing (Railway redeploy) — restore from DB
    rel = _restore_file("logo")
    if rel:
        return os.path.join(os.path.dirname(__file__), rel.lstrip("/"))
    return None


def get_packet_path() -> str | None:
    cfg = _load()
    rel = cfg.get("packet_path")
    if rel:
        full = os.path.join(os.path.dirname(__file__), rel.lstrip("/"))
        if os.path.exists(full):
            return full
    rel = _restore_file("packet")
    if rel:
        return os.path.join(os.path.dirname(__file__), rel.lstrip("/"))
    return None


def get_asset_urls() -> dict:
    """Return {logo_url, packet_url} — restores files from DB if missing."""
    cfg = _load()
    logo_url   = cfg.get("logo_path")
    packet_url = cfg.get("packet_path")

    # Check each file actually exists on disk; restore from DB if not
    if logo_url:
        full = os.path.join(os.path.dirname(__file__), logo_url.lstrip("/"))
        if not os.path.exists(full):
            logo_url = _restore_file("logo")
    else:
        logo_url = _restore_file("logo")

    if packet_url:
        full = os.path.join(os.path.dirname(__file__), packet_url.lstrip("/"))
        if not os.path.exists(full):
            packet_url = _restore_file("packet")
    else:
        packet_url = _restore_file("packet")

    return {"logo_url": logo_url, "packet_url": packet_url}


def get_next_theme_index() -> int:
    cfg = _load()
    idx = cfg.get("theme_index", 0)
    cfg["theme_index"] = idx + 1
    _save(cfg)
    return idx
