"""Markdown and JSON output formatters."""

from __future__ import annotations

import json
from typing import Any

from .models import Item, User, Story, Comment, Updates, fmt_time

HN_ITEM_LINK = 'https://news.ycombinator.com/item?id={}'


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    if n == 1:
        return f'{n} {singular}'
    return f'{n} {plural or singular + "s"}'


def md_stories(stories: list[Story], story_type: str) -> str:
    """Render a list of stories as markdown."""
    lines = [f'# HN {story_type.title()} Stories\n']
    for i, s in enumerate(stories, 1):
        title = s.title or '(no title)'
        url = s.url
        hn_link = HN_ITEM_LINK.format(s.id)
        score = s.score or 0
        comments = s.descendants or 0
        by = s.by or '?'
        time = s.time or '?'

        title_part = f'[{title}]({url})' if url else f'[{title}]({hn_link})'
        lines.append(f'{i}. {title_part}')
        lines.append(
            f'   {score} points by {by} | {time} | [{_plural(comments, "comment")}]({hn_link})'
        )
    return '\n'.join(lines)


def md_item(item: Item) -> str:
    """Render a single item as markdown."""
    lines: list[str] = []
    hn_link = HN_ITEM_LINK.format(item.id)

    if item.title:
        lines.append(f'# {item.title}')
    else:
        lines.append(f'# {item.type.title()} {item.id}')

    meta: list[str] = []
    if item.score is not None:
        meta.append(f'{item.score} points')
    if item.by:
        meta.append(f'by {item.by}')
    if item.time is not None:
        meta.append(fmt_time(item.time) or '')
    if meta:
        lines.append(' | '.join(meta))

    link_parts = [f'[HN discussion]({hn_link})']
    if item.url:
        link_parts.insert(0, f'[link]({item.url})')
    lines.append(' | '.join(link_parts))
    lines.append('')

    if item.text:
        lines.append(item.text)
        lines.append('')

    if item.children:
        lines.append(f'## Comments ({len(item.children)} top-level)\n')
        lines.extend(_md_comment(child, depth=0) for child in item.children)

    if item.kids_count and not item.children:
        lines.append(f'*{_plural(item.kids_count, "comment")} (use --with-comments to fetch)*')

    return '\n'.join(lines)


def _md_comment(comment: Comment, depth: int) -> str:
    indent = '  ' * depth
    by = comment.by or '?'
    time = comment.time or ''
    text = comment.text
    wrapped = ('\n' + indent + '> ').join(text.split('\n'))

    lines = [f'{indent}> {by} ({time}):']
    lines.append(f'{indent}> {wrapped}')

    if comment.kids_count:
        lines.append(f'{indent}> *[{_plural(comment.kids_count, "reply", "replies")} hidden]*')
    lines.append('')

    lines.extend(_md_comment(child, depth + 1) for child in comment.children)

    return '\n'.join(lines)


def md_user(user: User) -> str:
    """Render a user profile as markdown."""
    lines = [f'# User: {user.id}\n']
    lines.append(f'- **Karma:** {user.karma}')
    lines.append(f'- **Created:** {user.created_iso}')
    lines.append(f'- **Submissions:** {user.submitted_count} total')

    if user.about:
        lines.append(f'\n## About\n\n{user.about}')

    if user.submitted:
        lines.append(f'\n## Recent Submissions (latest {len(user.submitted)} IDs)\n')
        lines.append(', '.join(str(s) for s in user.submitted))

    return '\n'.join(lines)


def md_updates(updates: Updates) -> str:
    """Render recently changed items as markdown."""
    lines = ['# HN Recent Updates\n']
    lines.append(f'## Changed Items ({len(updates.items)})\n')
    lines.append(', '.join(str(i) for i in updates.items[:30]))
    if len(updates.items) > 30:
        lines.append(f'\n*...and {len(updates.items) - 30} more*')
    lines.append(f'\n## Changed Profiles ({len(updates.profiles)})\n')
    lines.append(', '.join(updates.profiles[:30]))
    if len(updates.profiles) > 30:
        lines.append(f'\n*...and {len(updates.profiles) - 30} more*')
    return '\n'.join(lines)


def output_json(data: Any) -> str:
    """Serialize data to JSON string."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=_serialize)


def _serialize(obj: Any) -> Any:
    """Default serializer for dataclasses."""
    if hasattr(obj, '__dataclass_fields__'):
        from dataclasses import asdict

        return asdict(obj)
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')
