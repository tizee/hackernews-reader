"""HN Algolia Search API client for time-based queries."""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import quote

import httpx

from .models import Story

ALGOLIA_BASE = 'http://hn.algolia.com/api/v1'

# Maps --type values to Algolia tag filters
TYPE_TO_TAGS: dict[str, str] = {
    'top': 'story',
    'new': 'story',
    'best': 'story',
    'ask': 'ask_hn',
    'show': 'show_hn',
}

# Duration pattern: number + unit (h=hours, d=days, w=weeks, m=minutes)
_DURATION_RE = re.compile(r'^(\d+)([mhdw])$')

_UNIT_SECONDS: dict[str, int] = {
    'm': 60,
    'h': 3600,
    'd': 86400,
    'w': 604800,
}


def parse_since(since: str) -> int:
    """Parse a duration string into a Unix timestamp.

    Args:
        since: Duration string like '24h', '7d', '30m', '2w'.

    Returns:
        Unix timestamp representing (now - duration).

    Raises:
        ValueError: If the duration string is invalid.
    """
    match = _DURATION_RE.match(since.strip().lower())
    if not match:
        raise ValueError(f'Invalid duration: {since!r}. Use format like 1h, 6h, 24h, 3d, 7d, 2w.')
    amount = int(match.group(1))
    unit = match.group(2)
    if amount <= 0:
        raise ValueError(f'Duration must be positive, got: {since!r}')
    seconds = amount * _UNIT_SECONDS[unit]
    return int(time.time()) - seconds


def _hit_to_story(hit: dict[str, Any]) -> Story:
    """Convert an Algolia hit to a Story."""
    object_id = hit.get('objectID', '0')
    hn_url = f'https://news.ycombinator.com/item?id={object_id}'
    return Story(
        id=int(object_id),
        title=hit.get('title'),
        url=hit.get('url') or hn_url,
        score=hit.get('points'),
        by=hit.get('author'),
        time=hit.get('created_at'),
        descendants=hit.get('num_comments', 0),
        type='story',
    )


def build_algolia_url(
    story_type: str,
    since_ts: int,
    limit: int,
    keyword: str | None = None,
    page: int = 0,
) -> str:
    """Build the Algolia search URL.

    Args:
        story_type: One of top/new/best/ask/show.
        since_ts: Unix timestamp for lower time bound.
        limit: Number of results per page.
        keyword: Optional search query.
        page: Page number (0-indexed).

    Returns:
        The full Algolia API URL.
    """
    # Use search_by_date for 'new' (date-sorted), search for others (relevance-sorted)
    endpoint = 'search_by_date' if story_type == 'new' else 'search'

    tags = TYPE_TO_TAGS.get(story_type, 'story')
    params = [
        f'tags={tags}',
        f'numericFilters=created_at_i>{since_ts}',
        f'hitsPerPage={limit}',
        f'page={page}',
    ]

    if keyword:
        params.append(f'query={quote(keyword)}')

    return f'{ALGOLIA_BASE}/{endpoint}?{"&".join(params)}'


async def search_stories(
    client: httpx.AsyncClient,
    story_type: str = 'top',
    since: str | None = None,
    limit: int = 10,
    keyword: str | None = None,
) -> list[Story]:
    """Search HN stories via Algolia with optional time filter.

    Args:
        client: httpx async client.
        story_type: Story type (top/new/best/ask/show).
        since: Duration string like '24h', '7d'. Required.
        limit: Max number of results.
        keyword: Optional keyword search query.

    Returns:
        List of Story objects.

    Raises:
        ValueError: If story_type is 'job' (unsupported by Algolia) or since is invalid.
    """
    if story_type == 'job':
        raise ValueError(
            "Algolia search does not support 'job' type. "
            'Use Firebase API (omit --since) for job listings.'
        )

    if since is None:
        raise ValueError('--since is required for Algolia search.')

    since_ts = parse_since(since)
    url = build_algolia_url(story_type, since_ts, limit, keyword)

    resp = await client.get(url, timeout=15)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()

    hits: list[dict[str, Any]] = data.get('hits', [])
    return [_hit_to_story(h) for h in hits[:limit]]
