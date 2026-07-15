import json
import os
from pathlib import Path

POSTS_FILE = Path(os.environ.get("POSTS_FILE", "posts.json"))


def _load():
    if not POSTS_FILE.exists():
        return []
    return json.loads(POSTS_FILE.read_text(encoding="utf-8"))


def _save(posts):
    POSTS_FILE.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")


def all_posts():
    return _load()


def add_post(datum, uhrzeit, plattform, caption, media_url, hashtags):
    posts = _load()
    next_id = max((p["id"] for p in posts), default=0) + 1
    posts.append({
        "id": next_id,
        "datum": datum,
        "uhrzeit": uhrzeit,
        "plattform": plattform,
        "caption": caption,
        "media_url": media_url,
        "hashtags": hashtags,
        "status": "pending",
    })
    _save(posts)
    return next_id


def pending_posts():
    return [p for p in _load() if p["status"] == "pending"]


def set_status(post_id, status):
    update_field(post_id, "status", status)


def update_field(post_id, field, value):
    posts = _load()
    for p in posts:
        if p["id"] == post_id:
            p[field] = value
            break
    _save(posts)


def add_blank_rows(count):
    posts = _load()
    next_id = max((p["id"] for p in posts), default=0) + 1
    new_ids = []
    for i in range(count):
        posts.append({
            "id": next_id + i,
            "datum": "",
            "uhrzeit": "",
            "plattform": "twitter",
            "caption": "",
            "media_url": "",
            "hashtags": "",
            "status": "pending",
        })
        new_ids.append(next_id + i)
    _save(posts)
    return new_ids


def delete_post(post_id):
    posts = [p for p in _load() if p["id"] != post_id]
    _save(posts)
