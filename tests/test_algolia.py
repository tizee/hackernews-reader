"""Tests for Algolia search API client."""

import time as time_module
from unittest.mock import patch

import httpx
import respx
import pytest

from hn.algolia import (
    ALGOLIA_BASE,
    TYPE_TO_TAGS,
    parse_since,
    search_stories,
    build_algolia_url,
)


class TestParseSince:
    def test_parses_hours(self):
        with patch.object(time_module, 'time', return_value=1000000):
            ts = parse_since('24h')
        assert ts == 1000000 - 24 * 3600

    def test_parses_days(self):
        with patch.object(time_module, 'time', return_value=1000000):
            ts = parse_since('7d')
        assert ts == 1000000 - 7 * 86400

    def test_parses_minutes(self):
        with patch.object(time_module, 'time', return_value=1000000):
            ts = parse_since('30m')
        assert ts == 1000000 - 30 * 60

    def test_parses_weeks(self):
        with patch.object(time_module, 'time', return_value=1000000):
            ts = parse_since('2w')
        assert ts == 1000000 - 2 * 604800

    def test_rejects_invalid_format(self):
        with pytest.raises(ValueError, match='Invalid duration'):
            parse_since('abc')

    def test_rejects_missing_unit(self):
        with pytest.raises(ValueError, match='Invalid duration'):
            parse_since('24')

    def test_rejects_unknown_unit(self):
        with pytest.raises(ValueError, match='Invalid duration'):
            parse_since('5y')

    def test_case_insensitive(self):
        with patch.object(time_module, 'time', return_value=1000000):
            ts = parse_since('24H')
        assert ts == 1000000 - 24 * 3600


class TestBuildAlgoliaUrl:
    def test_top_uses_search_endpoint(self):
        url = build_algolia_url('top', since_ts=900000, limit=10)
        assert url.startswith(f'{ALGOLIA_BASE}/search?')
        assert 'tags=story' in url
        assert 'created_at_i>900000' in url
        assert 'hitsPerPage=10' in url

    def test_new_uses_search_by_date_endpoint(self):
        url = build_algolia_url('new', since_ts=900000, limit=10)
        assert url.startswith(f'{ALGOLIA_BASE}/search_by_date?')

    def test_ask_uses_ask_hn_tag(self):
        url = build_algolia_url('ask', since_ts=900000, limit=10)
        assert 'tags=ask_hn' in url

    def test_show_uses_show_hn_tag(self):
        url = build_algolia_url('show', since_ts=900000, limit=10)
        assert 'tags=show_hn' in url

    def test_keyword_appended_as_query(self):
        url = build_algolia_url('top', since_ts=900000, limit=10, keyword='rust')
        assert 'query=rust' in url

    def test_keyword_with_spaces_is_url_encoded(self):
        url = build_algolia_url('top', since_ts=900000, limit=10, keyword='hello world')
        assert 'query=hello%20world' in url

    def test_page_parameter(self):
        url = build_algolia_url('top', since_ts=900000, limit=10, page=3)
        assert 'page=3' in url


class TestSearchStories:
    ALGOLIA_HITS_RESPONSE = {
        'hits': [
            {
                'objectID': '42',
                'title': 'Algolia Story',
                'url': 'https://example.com/algolia',
                'points': 100,
                'author': 'alice',
                'created_at': '2021-01-01T00:00:00.000Z',
                'num_comments': 20,
            },
            {
                'objectID': '43',
                'title': 'Second Story',
                'url': None,
                'points': 50,
                'author': 'bob',
                'created_at': '2021-01-01T01:00:00.000Z',
                'num_comments': 5,
            },
        ],
        'nbHits': 2,
        'page': 0,
        'nbPages': 1,
        'hitsPerPage': 20,
    }

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_stories_from_algolia(self):
        respx.get(url__startswith=f'{ALGOLIA_BASE}/search?').respond(
            json=self.ALGOLIA_HITS_RESPONSE
        )

        async with httpx.AsyncClient() as client:
            stories = await search_stories(client, story_type='top', since='24h', limit=10)

        assert len(stories) == 2
        assert stories[0].id == 42
        assert stories[0].title == 'Algolia Story'
        assert stories[0].score == 100
        assert stories[0].by == 'alice'
        assert stories[0].descendants == 20

    @respx.mock
    @pytest.mark.asyncio
    async def test_story_without_url_gets_hn_link(self):
        respx.get(url__startswith=f'{ALGOLIA_BASE}/search?').respond(
            json=self.ALGOLIA_HITS_RESPONSE
        )

        async with httpx.AsyncClient() as client:
            stories = await search_stories(client, story_type='top', since='24h', limit=10)

        assert stories[1].url == 'https://news.ycombinator.com/item?id=43'

    @respx.mock
    @pytest.mark.asyncio
    async def test_new_type_uses_search_by_date(self):
        route = respx.get(url__startswith=f'{ALGOLIA_BASE}/search_by_date?').respond(
            json={'hits': [], 'nbHits': 0, 'page': 0, 'nbPages': 0, 'hitsPerPage': 20}
        )

        async with httpx.AsyncClient() as client:
            stories = await search_stories(client, story_type='new', since='24h', limit=10)

        assert route.called
        assert len(stories) == 0

    @pytest.mark.asyncio
    async def test_job_type_raises_error(self):
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match='job'):
                await search_stories(client, story_type='job', since='24h')

    @pytest.mark.asyncio
    async def test_missing_since_raises_error(self):
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match='--since is required'):
                await search_stories(client, story_type='top', since=None)

    @respx.mock
    @pytest.mark.asyncio
    async def test_keyword_search_succeeds(self):
        # URL construction with keyword is tested in TestBuildAlgoliaUrl.
        # Here we verify the end-to-end call completes.
        respx.get(url__startswith=f'{ALGOLIA_BASE}/search?').respond(
            json={'hits': [], 'nbHits': 0, 'page': 0, 'nbPages': 0, 'hitsPerPage': 20}
        )

        async with httpx.AsyncClient() as client:
            stories = await search_stories(
                client, story_type='top', since='24h', keyword='rust', limit=5
            )

        assert stories == []


class TestTypeToTags:
    def test_all_expected_types_mapped(self):
        assert 'top' in TYPE_TO_TAGS
        assert 'new' in TYPE_TO_TAGS
        assert 'best' in TYPE_TO_TAGS
        assert 'ask' in TYPE_TO_TAGS
        assert 'show' in TYPE_TO_TAGS

    def test_job_not_in_tags(self):
        assert 'job' not in TYPE_TO_TAGS
