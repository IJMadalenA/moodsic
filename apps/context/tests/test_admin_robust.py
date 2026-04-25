from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from apps.context.admin.weather_context import WeatherContextAdmin
from apps.context.models import WeatherContext


@pytest.mark.django_db
class TestContextAdmin:
    def test_weather_context_admin_methods(self):
        site = AdminSite()
        admin = WeatherContextAdmin(WeatherContext, site)

        obj = WeatherContext.objects.create(
            temperature=20.0,
            feels_like=19.0,
            main_status="Clear",
            description="Clear sky",
            timestamp=timezone.now(),
        )

        # Probar métodos custom del admin
        assert admin.get_location(obj) == "Unknown"

    @patch("apps.context.admin.weather_context.WeatherService.fetch_and_store_weather")
    def test_update_weather_action(self, mock_fetch, rf):
        from cities_light.models import City, Country

        site = AdminSite()
        admin = WeatherContextAdmin(WeatherContext, site)

        country = Country.objects.create(name="Spain", code2="ES")
        city = City.objects.create(
            name="Madrid", country=country, latitude=40, longitude=-3
        )

        WeatherContext.objects.create(
            city=city,
            temperature=20,
            feels_like=20,
            main_status="C",
            timestamp=timezone.now(),
        )

        request = rf.get("/")
        with patch.object(admin, "message_user"):
            admin.update_weather_action(request, WeatherContext.objects.all())
            assert mock_fetch.called

    @patch("apps.context.admin.weather_context.WeatherService.fetch_and_store_weather")
    def test_update_weather_view(self, mock_fetch, rf):
        from cities_light.models import City, Country

        site = AdminSite()
        admin = WeatherContextAdmin(WeatherContext, site)

        country = Country.objects.create(name="Spain", code2="ES")
        City.objects.create(name="Madrid", country=country, latitude=40, longitude=-3)

        request = rf.get("/")
        with patch.object(admin, "message_user"):
            response = admin.update_weather_view(request)
            assert mock_fetch.called
            assert response.status_code == 302
