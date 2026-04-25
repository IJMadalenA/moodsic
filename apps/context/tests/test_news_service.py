from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.context.models import NewsContext
from apps.context.services.news_service import NewsService


@pytest.mark.django_db
@override_settings(NEWSAPI_KEY="fake-key")
@patch("apps.context.services.news_service.requests.get")
def test_fetch_and_store_news(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "articles": [
            {
                "title": "Breaking music growth in Europe",
                "description": "Record success for independent artists",
                "url": "https://example.com/news/1",
                "source": {"name": "Music Daily"},
                "publishedAt": "2026-04-10T10:00:00Z",
            },
            {
                "title": "Markets decline but concerts remain strong",
                "description": "Fans keep engagement high",
                "url": "https://example.com/news/2",
                "source": {"name": "Culture Wire"},
                "publishedAt": "2026-04-10T09:30:00Z",
            },
        ]
    }
    mock_get.return_value = mock_response

    records = NewsService.fetch_and_store_news(
        query="music", language="en", page_size=5
    )

    assert len(records) == 2
    assert NewsContext.objects.count() == 2
    first = NewsContext.objects.get(url="https://example.com/news/1")
    assert first.source == "Music Daily"
    assert first.sentiment_label in {"positive", "neutral", "negative"}


@pytest.mark.django_db
@override_settings(NEWSAPI_KEY="")
def test_fetch_news_without_key_returns_empty_list():
    items = NewsService.fetch_latest_news(query="music")
    assert items == []


@pytest.mark.django_db
@override_settings(NEWSAPI_KEY="")
def test_fetch_news_without_key_uses_cached_items_when_available():
    NewsContext.objects.create(
        title="Cached music headline",
        source="Local Cache",
        url="https://example.com/cached-news",
        summary="Cached summary",
        language="en",
        category="music",
        sentiment_score=0.2,
        sentiment_label="positive",
        is_breaking=False,
    )

    items = NewsService.fetch_latest_news(query="music", category="music", page_size=5)

    assert len(items) == 1
    assert items[0]["title"] == "Cached music headline"
    assert items[0]["source"] == "Local Cache"


def test_normalize_category_supported_values():
    assert NewsService._normalize_category("music") == "music"
    assert NewsService._normalize_category("Markets") == "markets"


def test_normalize_category_invalid_falls_back_to_general():
    assert NewsService._normalize_category("finance") == "general"
