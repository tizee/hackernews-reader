"""HN Firebase API client."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .text import strip_html
from .models import Item, User, Story, Comment, Updates, fmt_time

BASE = 'https://hacker-news.firebaseio.com/v0'

STORY_ENDPOINTS: dict[str, str] = {
    'top': 'topstories',
    'new': 'newstories',
    'best': 'beststories',
    'ask': 'askstories',
    'show': 'showstories',
    'job': 'jobstories',
}


async def fetch_json(client: httpx.AsyncClient, url: str) -> Any:
    """Fetch JSON from a URL."""
    resp = await client.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


async def fetch_item_raw(client: httpx.AsyncClient, item_id: int) -> dict[str, Any] | None:
    """Fetch a single raw item dict from the Firebase API."""
    try:
        data: Any = await fetch_json(client, f'{BASE}/item/{item_id}.json')
        if isinstance(data, dict):
            return data  # type: ignore[return-value]
        return None
    except Exception:
        return None


async def fetch_items_batch(client: httpx.AsyncClient, ids: list[int]) -> list[dict[str, Any]]:
    """Fetch multiple items concurrently."""
    tasks = [fetch_item_raw(client, i) for i in ids]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


def summarize_story(raw: dict[str, Any]) -> Story:
    """Convert a raw item dict to a Story summary."""
    return Story(
        id=raw.get('id', 0),
        title=raw.get('title'),
        url=raw.get('url'),
        score=raw.get('score'),
        by=raw.get('by'),
        time=fmt_time(raw.get('time')),
        descendants=raw.get('descendants', 0),
        type=raw.get('type'),
    )


async def _build_comment(
    client: httpx.AsyncClient,
    raw: dict[str, Any],
    max_depth: int,
    current_depth: int,
) -> Comment:
    """Recursively build a Comment tree."""
    kids = raw.get('kids', [])
    comment = Comment(
        id=raw.get('id', 0),
        by=raw.get('by'),
        time=fmt_time(raw.get('time')),
        text=strip_html(raw.get('text')),
    )

    if not kids or current_depth >= max_depth:
        comment.kids_count = len(kids)
        return comment

    child_raws = await fetch_items_batch(client, kids)
    for child_raw in child_raws:
        if child_raw.get('deleted') or child_raw.get('dead'):
            continue
        child = await _build_comment(client, child_raw, max_depth, current_depth + 1)
        comment.children.append(child)
    return comment


async def fetch_stories(
    client: httpx.AsyncClient,
    story_type: str = 'top',
    limit: int = 10,
) -> list[Story]:
    """Fetch a ranked story list from Firebase API."""
    endpoint = STORY_ENDPOINTS[story_type]
    ids_data: Any = await fetch_json(client, f'{BASE}/{endpoint}.json')
    ids: list[int] = ids_data[:limit]
    items = await fetch_items_batch(client, ids)
    return [summarize_story(it) for it in items]


async def fetch_item(
    client: httpx.AsyncClient,
    item_id: int,
    with_comments: bool = False,
    comment_depth: int = 2,
) -> Item:
    """Fetch a single item, optionally with comment tree."""
    raw = await fetch_item_raw(client, item_id)
    if raw is None:
        raise ValueError(f'Item {item_id} not found')

    kids: list[int] = raw.get('kids', [])
    children: list[Comment] | None = None
    kids_count = 0

    if with_comments and kids:
        child_raws = await fetch_items_batch(client, kids)
        children = []
        for child_raw in child_raws:
            if child_raw.get('deleted') or child_raw.get('dead'):
                continue
            c = await _build_comment(client, child_raw, comment_depth, 0)
            children.append(c)
    elif kids:
        kids_count = len(kids)

    return Item(
        id=raw.get('id', 0),
        type=raw.get('type', 'story'),
        title=raw.get('title'),
        url=raw.get('url'),
        text=strip_html(raw.get('text')),
        by=raw.get('by'),
        score=raw.get('score'),
        time=raw.get('time'),
        time_iso=fmt_time(raw.get('time')),
        descendants=raw.get('descendants', 0),
        children=children,
        kids_count=kids_count,
    )


async def fetch_user(client: httpx.AsyncClient, username: str) -> User:
    """Fetch a user profile."""
    data: Any = await fetch_json(client, f'{BASE}/user/{username}.json')
    if data is None:
        raise ValueError(f'User {username} not found')
    submitted: list[int] = data.get('submitted', [])
    return User(
        id=data['id'],
        karma=data.get('karma', 0),
        created=data.get('created'),
        created_iso=fmt_time(data.get('created')),
        about=strip_html(data.get('about')),
        submitted=submitted[:20],
        submitted_count=len(submitted),
    )


async def fetch_updates(client: httpx.AsyncClient) -> Updates:
    """Fetch recently changed items and profiles."""
    data: Any = await fetch_json(client, f'{BASE}/updates.json')
    return Updates(
        items=data.get('items', []),
        profiles=data.get('profiles', []),
    )
