"""Tests for markdown formatters."""

from hn.models import Item, User, Story, Comment, Updates
from hn.formatters import md_item, md_user, md_stories, md_updates


class TestMdStories:
    def test_renders_story_list_with_title(self):
        stories = [
            Story(
                id=1,
                title='Hello',
                url='https://x.com',
                score=10,
                by='pg',
                time='2021-01-01',
                descendants=3,
            )
        ]
        result = md_stories(stories, 'top')
        assert '# HN Top Stories' in result
        assert '[Hello](https://x.com)' in result
        assert '10 points by pg' in result
        assert '3 comments' in result

    def test_uses_hn_link_when_no_url(self):
        stories = [Story(id=42, title='Ask HN: test')]
        result = md_stories(stories, 'ask')
        assert 'news.ycombinator.com/item?id=42' in result

    def test_singular_comment(self):
        stories = [Story(id=1, title='X', descendants=1)]
        result = md_stories(stories, 'top')
        assert '1 comment' in result
        assert '1 comments' not in result


class TestMdItem:
    def test_renders_item_with_title(self):
        item = Item(id=1, title='Test', score=50, by='dang', time=1609459200, url='https://x.com')
        result = md_item(item)
        assert '# Test' in result
        assert '50 points' in result
        assert '[link](https://x.com)' in result

    def test_renders_kids_count_hint(self):
        item = Item(id=1, title='Test', kids_count=5)
        result = md_item(item)
        assert '5 comments (use --with-comments to fetch)' in result

    def test_renders_comment_tree(self):
        children = [Comment(id=10, by='alice', time='2021-01-01', text='Great!')]
        item = Item(id=1, title='Test', children=children)
        result = md_item(item)
        assert '## Comments (1 top-level)' in result
        assert 'alice' in result
        assert 'Great!' in result


class TestMdUser:
    def test_renders_user_profile(self):
        user = User(
            id='pg',
            karma=99999,
            created_iso='2006-10-09 18:21 UTC',
            submitted_count=5000,
            submitted=[1, 2, 3],
        )
        result = md_user(user)
        assert '# User: pg' in result
        assert '**Karma:** 99999' in result
        assert '**Submissions:** 5000 total' in result
        assert '1, 2, 3' in result


class TestMdUpdates:
    def test_renders_updates(self):
        updates = Updates(items=[1, 2], profiles=['pg'])
        result = md_updates(updates)
        assert 'Changed Items (2)' in result
        assert 'Changed Profiles (1)' in result
        assert 'pg' in result
