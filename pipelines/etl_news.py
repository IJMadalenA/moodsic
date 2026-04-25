"""ETL helpers for external news ingestion."""

from apps.context.services.news_service import NewsService


def run_news_etl(
    query: str = "music OR entertainment",
    language: str = "en",
    page_size: int = 20,
    category: str = "general",
) -> int:
    """Fetch and persist latest news context rows.

    Returns the number of persisted records.
    """
    records = NewsService.fetch_and_store_news(
        query=query,
        language=language,
        page_size=page_size,
        category=category,
    )
    return len(records)
