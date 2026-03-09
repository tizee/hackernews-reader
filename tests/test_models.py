"""Tests for data models and utilities."""

from hn.text import strip_html
from hn.models import Story, Comment, fmt_time


class TestFmtTime:
    def test_formats_unix_timestamp_to_utc(self):
        assert fmt_time(1609459200) == '2021-01-01 00:00 UTC'

    def test_returns_none_for_none(self):
        assert fmt_time(None) is None


class TestStripHtml:
    def test_converts_paragraph_tags_to_newlines(self):
        assert '\n\n' in strip_html('<p>hello<p>world')

    def test_converts_links_to_markdown(self):
        result = strip_html('<a href="http://example.com">click</a>')
        assert result == '[click](http://example.com)'

    def test_strips_remaining_tags(self):
        assert strip_html('<b>bold</b>') == 'bold'

    def test_unescapes_html_entities(self):
        assert strip_html('&amp; &lt;') == '& <'

    def test_returns_empty_for_none(self):
        assert strip_html(None) == ''

    def test_returns_empty_for_empty_string(self):
        assert strip_html('') == ''


class TestStoryDataclass:
    def test_defaults(self):
        s = Story(id=1)
        assert s.id == 1
        assert s.title is None
        assert s.descendants == 0


class TestCommentDataclass:
    def test_children_default_empty(self):
        c = Comment(id=1)
        assert c.children == []
        assert c.kids_count == 0

    def test_children_not_shared_between_instances(self):
        c1 = Comment(id=1)
        c2 = Comment(id=2)
        c1.children.append(Comment(id=3))
        assert len(c2.children) == 0
