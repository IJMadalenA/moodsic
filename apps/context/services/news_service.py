import logging
import time
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone

from ..models import NewsContext

logger = logging.getLogger(__name__)


class NewsService:
    """Service layer for fetching and persisting external news context."""

    ALLOWED_CATEGORIES = {"general", "music", "markets", "sports", "politics"}

    POSITIVE_WORDS = {
        "growth",
        "improve",
        "success",
        "win",
        "optimistic",
        "happy",
        "record",
        "strong",
        "up",
    }
    NEGATIVE_WORDS = {
        "crisis",
        "drop",
        "decline",
        "loss",
        "war",
        "fear",
        "down",
        "risk",
        "recession",
    }

    @classmethod
    def fetch_latest_news(
        cls,
        query: str = "music OR entertainment",
        language: str = "en",
        page_size: int = 20,
        category: str = "general",
        return_meta: bool = False,
    ) -> list[dict] | tuple[list[dict], dict]:
        """Fetch latest news from NewsAPI and return normalized dictionaries."""
        category = cls._normalize_category(category)

        api_key = getattr(settings, "NEWSAPI_KEY", "")
        base_url = getattr(
            settings,
            "NEWSAPI_BASE_URL",
            "https://newsapi.org/v2/everything",
        )

        if not api_key:
            logger.warning(
                "NEWSAPI_KEY is not configured; using cached local news when available"
            )
            cached_items = cls._get_cached_news(category=category, limit=page_size)
            if return_meta:
                return cached_items, {
                    "used_cached_news": bool(cached_items),
                    "news_source": "cache",
                }
            return cached_items

        is_top_headlines = "top-headlines" in base_url
        params = {
            "pageSize": max(1, min(page_size, 100)),
        }
        if is_top_headlines:
            params["country"] = "us"
        else:
            params["q"] = query
            params["language"] = language
            params["sortBy"] = "publishedAt"
        headers = {"X-Api-Key": api_key}

        timeout_seconds = int(getattr(settings, "EXTERNAL_API_TIMEOUT_SECONDS", 12))
        retries = int(getattr(settings, "EXTERNAL_API_RETRIES", 2))
        backoff_seconds = float(
            getattr(settings, "EXTERNAL_API_RETRY_BACKOFF_SECONDS", 0.5)
        )

        try:
            payload = None
            for attempt in range(retries + 1):
                try:
                    response = requests.get(
                        base_url,
                        params=params,
                        headers=headers,
                        timeout=max(2, timeout_seconds),
                    )
                    if response.status_code >= 500 or response.status_code == 429:
                        raise requests.HTTPError(response=response)
                    response.raise_for_status()
                    payload = response.json()
                    break
                except requests.RequestException:
                    if attempt >= retries:
                        raise
                    time.sleep(backoff_seconds * (2**attempt))

            if payload is None:
                raise requests.RequestException("No news payload received from provider")
        except requests.RequestException as exc:
            logger.warning(
                f"News provider unavailable, using cached news fallback: {exc}"
            )
            cached_items = cls._get_cached_news(category=category, limit=page_size)
            if return_meta:
                return cached_items, {
                    "used_cached_news": bool(cached_items),
                    "news_source": "cache",
                }
            return cached_items

        articles = payload.get("articles", [])
        normalized: list[dict] = []
        for article in articles:
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            if not title or not url:
                continue

            summary = (article.get("description") or "").strip()
            source = (article.get("source") or {}).get("name") or ""
            published_at = cls._parse_published_at(article.get("publishedAt"))
            sentiment_score, sentiment_label = cls._compute_sentiment(title, summary)

            normalized.append(
                {
                    "title": title,
                    "source": source,
                    "url": url,
                    "summary": summary,
                    "language": language,
                    "category": category,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "is_breaking": cls._is_breaking(title, summary),
                    "published_at": published_at,
                }
            )

        result = normalized or cls._get_cached_news(category=category, limit=page_size)
        if return_meta:
            return result, {
                "used_cached_news": not bool(normalized),
                "news_source": "provider" if normalized else "cache",
            }
        return result

    @classmethod
    def fetch_and_store_news(
        cls,
        query: str = "music OR entertainment",
        language: str = "en",
        page_size: int = 20,
        category: str = "general",
        return_meta: bool = False,
    ) -> list[NewsContext] | tuple[list[NewsContext], dict]:
        """Fetch news from provider and store unique items by URL."""
        items, meta = cls.fetch_latest_news(
            query=query,
            language=language,
            page_size=page_size,
            category=category,
            return_meta=True,
        )
        saved: list[NewsContext] = []
        for item in items:
            obj, _created = NewsContext.objects.update_or_create(
                url=item["url"],
                defaults=item,
            )
            saved.append(obj)
        if return_meta:
            return saved, meta
        return saved

    @classmethod
    def get_recent_news(cls, limit: int = 20) -> list[NewsContext]:
        return list(NewsContext.objects.all().order_by("-published_at")[:limit])

    @classmethod
    def _get_cached_news(cls, category: str = "general", limit: int = 20) -> list[dict]:
        queryset = NewsContext.objects.order_by("-published_at")
        if category and category != "all":
            queryset = queryset.filter(category=category)

        return [
            {
                "title": item.title,
                "source": item.source,
                "url": item.url,
                "summary": item.summary,
                "language": item.language,
                "category": item.category,
                "sentiment_score": item.sentiment_score,
                "sentiment_label": item.sentiment_label,
                "is_breaking": item.is_breaking,
                "published_at": item.published_at,
            }
            for item in queryset[: max(1, min(limit, 100))]
        ]

    @staticmethod
    def _parse_published_at(value: str | None):
        if not value:
            return timezone.now()
        try:
            # NewsAPI uses ISO datetime strings like 2026-03-01T10:22:11Z
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except ValueError:
            return timezone.now()

    @classmethod
    def _compute_sentiment(cls, title: str, summary: str) -> tuple[float, str]:
        text = f"{title} {summary}".lower()
        positive_hits = sum(1 for word in cls.POSITIVE_WORDS if word in text)
        negative_hits = sum(1 for word in cls.NEGATIVE_WORDS if word in text)
        score = float(positive_hits - negative_hits) / 5.0
        score = max(-1.0, min(1.0, score))
        if score > 0.15:
            label = "positive"
        elif score < -0.15:
            label = "negative"
        else:
            label = "neutral"
        return score, label

    @staticmethod
    def _is_breaking(title: str, summary: str) -> bool:
        text = f"{title} {summary}".lower()
        trigger_words = ("breaking", "urgent", "last hour", "latest")
        return any(word in text for word in trigger_words)

    @classmethod
    def _normalize_category(cls, category: str) -> str:
        normalized = (category or "general").strip().lower()
        if normalized not in cls.ALLOWED_CATEGORIES:
            return "general"
        return normalized
