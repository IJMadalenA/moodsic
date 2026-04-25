from unittest.mock import patch

import pytest

from pipelines.etl_news import run_news_etl


@pytest.mark.django_db
class TestETLRobust:
    @patch("apps.context.services.news_service.NewsService.fetch_and_store_news")
    def test_run_news_etl_empty(self, mock_fetch):
        mock_fetch.return_value = []
        count = run_news_etl()
        assert count == 0

    @patch("apps.context.services.news_service.NewsService.fetch_and_store_news")
    def test_run_news_etl_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("API Down")
        count = run_news_etl()
        assert count == 0
