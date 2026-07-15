import os

import requests

BUFFER_API_KEY = os.environ["BUFFER_API_KEY"]
BUFFER_CHANNEL_SERVICE = os.environ.get("BUFFER_PROFILE_SERVICE", "twitter")
BUFFER_API = "https://api.buffer.com"

_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {BUFFER_API_KEY}",
}


def _graphql(query, variables=None):
    r = requests.post(
        BUFFER_API,
        headers=_HEADERS,
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"Buffer API hatası: {data['errors']}")
    return data["data"]


def get_organization_id():
    data = _graphql("query { account { organizations { id } } }")
    orgs = data["account"]["organizations"]
    if not orgs:
        raise RuntimeError("Hesapta organizasyon bulunamadı.")
    return orgs[0]["id"]


def get_channel_id(organization_id):
    query = """
    query GetChannels($organizationId: OrganizationId!) {
      channels(input: { organizationId: $organizationId }) {
        id
        service
      }
    }
    """
    data = _graphql(query, {"organizationId": organization_id})
    for ch in data["channels"]:
        if ch["service"] == BUFFER_CHANNEL_SERVICE:
            return ch["id"]
    raise RuntimeError(f"'{BUFFER_CHANNEL_SERVICE}' servisine bağlı kanal bulunamadı.")


def get_pending_count(organization_id, channel_id):
    query = """
    query GetPending($organizationId: OrganizationId!, $channelId: ChannelId!) {
      posts(
        input: {
          organizationId: $organizationId
          filter: { status: [scheduled], channelIds: [$channelId] }
        }
        first: 50
      ) {
        edges { node { id } }
      }
    }
    """
    data = _graphql(query, {"organizationId": organization_id, "channelId": channel_id})
    return len(data["posts"]["edges"])


def create_post(channel_id, text, media_url, due_at_iso):
    query = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id } }
        ... on MutationError { message }
      }
    }
    """
    input_data = {
        "channelId": channel_id,
        "text": text,
        "schedulingType": "automatic",
        "mode": "customScheduled",
        "dueAt": due_at_iso,
    }
    if media_url:
        input_data["assets"] = [{"link": {"url": media_url}}]

    data = _graphql(query, {"input": input_data})
    result = data["createPost"]
    if "message" in result:
        return {"success": False, "error": result["message"]}
    return {"success": True, "post": result.get("post")}
