import os
from datetime import datetime
from zoneinfo import ZoneInfo

import buffer_client
import posts_store

QUEUE_LIMIT = int(os.environ.get("QUEUE_LIMIT", "10"))
TZ = ZoneInfo("Europe/Istanbul")


def _due_at_iso(datum, uhrzeit):
    dt = datetime.strptime(f"{datum} {uhrzeit}", "%d.%m.%Y %H:%M").replace(tzinfo=TZ)
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def fill_queue():
    organization_id = buffer_client.get_organization_id()
    channel_id = buffer_client.get_channel_id(organization_id)
    pending_count = buffer_client.get_pending_count(organization_id, channel_id)
    room = QUEUE_LIMIT - pending_count
    log = [f"Buffer kuyruğunda {pending_count} post var, {room} boş yer var."]

    if room <= 0:
        log.append("Kuyruk dolu, çıkılıyor.")
        return log

    scheduled = 0
    for post in posts_store.pending_posts():
        if scheduled >= room:
            break
        try:
            due_at = _due_at_iso(post["datum"], post["uhrzeit"])
        except ValueError:
            log.append(f"#{post['id']}: tarih/saat hatalı, atlanıyor.")
            continue

        text = f"{post['caption']}\n\n{post['hashtags']}".strip()
        result = buffer_client.create_post(channel_id, text, post["media_url"], due_at)

        if result.get("success"):
            posts_store.set_status(post["id"], "queued")
            scheduled += 1
            log.append(f"#{post['id']} kuyruğa eklendi.")
        else:
            log.append(f"#{post['id']} eklenemedi: {result.get('error', result)}")

    return log
