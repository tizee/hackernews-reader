"""Tests for Firebase API client."""

import httpx
import respx
import pytest

from hn.client import (
    BASE,
    fetch_item,
    fetch_user,
    fetch_stories,
    fetch_updates,
    summarize_story,
)

SAMPLE_STORY_RAW = {
    'id': 123,
    'title': 'Test Story',
    'url': 'https://example.com',
    'score': 42,
    'by': 'testuser',
    'time': 1609459200,
    'descendants': 5,
    'type': 'story',
}


class TestSummarizeStory:
    def test_extracts_all_fields(self):
        story = summarize_story(SAMPLE_STORY_RAW)
        assert story.id == 123
        assert story.title == 'Test Story'
        assert story.url == 'https://example.com'
        assert story.score == 42
        assert story.by == 'testuser'
        assert story.time == '2021-01-01 00:00 UTC'
        assert story.descendants == 5

    def test_handles_missing_fields(self):
        story = summarize_story({'id': 1})
        assert story.title is None
        assert story.score is None
        assert story.descendants == 0


class TestFetchStories:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_top_stories(self):
        respx.get(f'{BASE}/topstories.json').respond(json=[123, 456])
        respx.get(f'{BASE}/item/123.json').respond(json=SAMPLE_STORY_RAW)
        respx.get(f'{BASE}/item/456.json').respond(
            json={**SAMPLE_STORY_RAW, 'id': 456, 'title': 'Second'}
        )

        async with httpx.AsyncClient() as client:
            stories = await fetch_stories(client, 'top', limit=2)

        assert len(stories) == 2
        assert stories[0].id == 123
        assert stories[1].id == 456

    @respx.mock
    @pytest.mark.asyncio
    async def test_respects_limit(self):
        respx.get(f'{BASE}/topstories.json').respond(json=[1, 2, 3, 4, 5])
        respx.get(f'{BASE}/item/1.json').respond(json={**SAMPLE_STORY_RAW, 'id': 1})
        respx.get(f'{BASE}/item/2.json').respond(json={**SAMPLE_STORY_RAW, 'id': 2})

        async with httpx.AsyncClient() as client:
            stories = await fetch_stories(client, 'top', limit=2)

        assert len(stories) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_skips_failed_items(self):
        respx.get(f'{BASE}/topstories.json').respond(json=[1, 2])
        respx.get(f'{BASE}/item/1.json').respond(status_code=500)
        respx.get(f'{BASE}/item/2.json').respond(json={**SAMPLE_STORY_RAW, 'id': 2})

        async with httpx.AsyncClient() as client:
            stories = await fetch_stories(client, 'top', limit=2)

        assert len(stories) == 1
        assert stories[0].id == 2


class TestFetchItem:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_story_without_comments(self):
        respx.get(f'{BASE}/item/123.json').respond(
            json={
                **SAMPLE_STORY_RAW,
                'kids': [10, 20],
            }
        )

        async with httpx.AsyncClient() as client:
            item = await fetch_item(client, 123)

        assert item.id == 123
        assert item.kids_count == 2
        assert item.children is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_raises_for_missing_item(self):
        # Firebase returns literal "null" for missing items
        respx.get(f'{BASE}/item/999.json').respond(
            text='null', headers={'content-type': 'application/json'}
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match='999 not found'):
                await fetch_item(client, 999)

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_with_comments(self):
        respx.get(f'{BASE}/item/123.json').respond(
            json={
                **SAMPLE_STORY_RAW,
                'kids': [10],
            }
        )
        respx.get(f'{BASE}/item/10.json').respond(
            json={
                'id': 10,
                'by': 'commenter',
                'text': 'nice',
                'time': 1609459200,
                'type': 'comment',
            }
        )

        async with httpx.AsyncClient() as client:
            item = await fetch_item(client, 123, with_comments=True, comment_depth=1)

        assert item.children is not None
        assert len(item.children) == 1
        assert item.children[0].by == 'commenter'


class TestFetchUser:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_user_profile(self):
        respx.get(f'{BASE}/user/pg.json').respond(
            json={
                'id': 'pg',
                'karma': 99999,
                'created': 1160418111,
                'about': 'PG bio',
                'submitted': list(range(100)),
            }
        )

        async with httpx.AsyncClient() as client:
            user = await fetch_user(client, 'pg')

        assert user.id == 'pg'
        assert user.karma == 99999
        assert user.submitted_count == 100
        assert len(user.submitted) == 20  # truncated to 20

    @respx.mock
    @pytest.mark.asyncio
    async def test_raises_for_missing_user(self):
        # Firebase returns literal "null" for missing users
        respx.get(f'{BASE}/user/nobody.json').respond(
            text='null', headers={'content-type': 'application/json'}
        )

        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match='nobody not found'):
                await fetch_user(client, 'nobody')


class TestFetchUpdates:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_updates(self):
        respx.get(f'{BASE}/updates.json').respond(
            json={
                'items': [1, 2, 3],
                'profiles': ['pg', 'dang'],
            }
        )

        async with httpx.AsyncClient() as client:
            updates = await fetch_updates(client)

        assert updates.items == [1, 2, 3]
        assert updates.profiles == ['pg', 'dang']
