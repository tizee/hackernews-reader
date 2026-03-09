"""Data models for Hacker News items."""

from datetime import datetime, timezone
from dataclasses import field, dataclass


def _empty_int_list() -> list[int]:
    return []


def _empty_str_list() -> list[str]:
    return []


def _empty_comment_list() -> list['Comment']:
    return []


@dataclass
class Story:
    """A summarized HN story."""

    id: int
    title: str | None = None
    url: str | None = None
    score: int | None = None
    by: str | None = None
    time: str | None = None
    descendants: int = 0
    type: str | None = None


@dataclass
class Comment:
    """A comment with optional nested children."""

    id: int
    by: str | None = None
    time: str | None = None
    text: str = ''
    children: list['Comment'] = field(default_factory=_empty_comment_list)
    kids_count: int = 0


@dataclass
class Item:
    """A full HN item (story, comment, job, poll)."""

    id: int
    type: str = 'story'
    title: str | None = None
    url: str | None = None
    text: str | None = None
    by: str | None = None
    score: int | None = None
    time: int | None = None
    time_iso: str | None = None
    descendants: int = 0
    children: list[Comment] | None = None
    kids_count: int = 0


@dataclass
class User:
    """An HN user profile."""

    id: str
    karma: int = 0
    created: int | None = None
    created_iso: str | None = None
    about: str | None = None
    submitted: list[int] = field(default_factory=_empty_int_list)
    submitted_count: int = 0


@dataclass
class Updates:
    """Recently changed items and profiles."""

    items: list[int] = field(default_factory=_empty_int_list)
    profiles: list[str] = field(default_factory=_empty_str_list)


def fmt_time(unix_ts: int | None) -> str | None:
    """Format a unix timestamp to ISO-like UTC string."""
    if unix_ts is None:
        return None
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
