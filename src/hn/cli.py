"""CLI entry point for the hn command."""

from __future__ import annotations

import sys
import asyncio
import argparse

from .client import STORY_ENDPOINTS, fetch_item, fetch_user, fetch_stories, fetch_updates
from .algolia import search_stories
from .formatters import md_item, md_user, md_stories, md_updates, output_json


def _output(data: object, md_text: str, use_json: bool) -> None:
    if use_json:
        print(output_json(data))
    else:
        print(md_text)


async def cmd_stories(args: argparse.Namespace) -> None:
    """Handle the stories subcommand."""
    import httpx

    async with httpx.AsyncClient() as client:
        if args.since or args.keyword:
            stories = await search_stories(
                client,
                story_type=args.type,
                since=args.since,
                limit=args.limit,
                keyword=args.keyword,
            )
        else:
            stories = await fetch_stories(client, args.type, args.limit)
    _output(stories, md_stories(stories, args.type), args.json)


async def cmd_item(args: argparse.Namespace) -> None:
    """Handle the item subcommand."""
    import httpx

    async with httpx.AsyncClient() as client:
        try:
            item = await fetch_item(client, args.id, args.with_comments, args.comment_depth)
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)
    _output(item, md_item(item), args.json)


async def cmd_user(args: argparse.Namespace) -> None:
    """Handle the user subcommand."""
    import httpx

    async with httpx.AsyncClient() as client:
        try:
            user = await fetch_user(client, args.username)
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)
    _output(user, md_user(user), args.json)


async def cmd_updates(args: argparse.Namespace) -> None:
    """Handle the updates subcommand."""
    import httpx

    async with httpx.AsyncClient() as client:
        updates = await fetch_updates(client)
    _output(updates, md_updates(updates), args.json)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description='Fetch Hacker News data')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of markdown')
    sub = parser.add_subparsers(dest='command', required=True)

    # stories
    p_stories = sub.add_parser('stories', help='Fetch story lists')
    p_stories.add_argument(
        '--type',
        choices=list(STORY_ENDPOINTS.keys()),
        default='top',
        help='Story list type (default: top)',
    )
    p_stories.add_argument('--limit', type=int, default=10, help='Number of stories (default: 10)')
    p_stories.add_argument(
        '--since',
        type=str,
        default=None,
        help='Time window: 1h, 6h, 24h, 3d, 7d, 2w. Uses Algolia search API.',
    )
    p_stories.add_argument(
        '--keyword',
        type=str,
        default=None,
        help='Search keyword. Uses Algolia search API.',
    )

    # item
    p_item = sub.add_parser('item', help='Fetch a single item')
    p_item.add_argument('id', type=int, help='Item ID')
    p_item.add_argument('--with-comments', action='store_true', help='Include comment tree')
    p_item.add_argument(
        '--comment-depth', type=int, default=2, help='Max comment depth (default: 2)'
    )

    # user
    p_user = sub.add_parser('user', help='Fetch user profile')
    p_user.add_argument('username', help='HN username')

    # updates
    sub.add_parser('updates', help='Fetch recently changed items and profiles')

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    commands: dict[str, object] = {
        'stories': cmd_stories,
        'item': cmd_item,
        'user': cmd_user,
        'updates': cmd_updates,
    }

    handler = commands[args.command]
    asyncio.run(handler(args))  # type: ignore[arg-type]
