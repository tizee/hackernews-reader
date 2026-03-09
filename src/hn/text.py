"""HTML stripping and text utilities."""

from __future__ import annotations

import re
from html import unescape


def strip_html(html: str | None) -> str:
    """Strip HTML tags, convert links to markdown, unescape entities."""
    if not html:
        return ''
    text = html.replace('<p>', '\n\n').replace('<br>', '\n').replace('<br/>', '\n')
    text = re.sub(r'<a\s+href="([^"]*)"[^>]*>([^<]*)</a>', r'[\2](\1)', text)
    text = re.sub(r'<[^>]+>', '', text)
    return unescape(text).strip()
