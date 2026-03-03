from unittest.mock import MagicMock, patch

import pytest
from cities_light.models import City, Country
from django.utils import timezone

from apps.context.models import WeatherContext
from apps.context.services.weather_service import WeatherService


@pytest.mark.django_db
def test_weather_context_creation():
    """
    Verifica que el modelo WeatherContext se cree correctamente y funcione su representación en string.
    """
    country = Country.objects.create(name="Spain", code2="ES")
    city = City.objects.create(
        name="Madrid", country=country, latitude=40.4168, longitude=-3.7038
    )

    weather = WeatherContext.objects.create(
        city=city,
        main_status="Clouds",
        description="nubes dispersas",
        temperature=20.5,
        feels_like=19.8,
        timestamp=timezone.now(),
    )

    assert "Madrid" in str(weather)
    assert "20.5°C" in str(weather)
    assert WeatherContext.objects.count() == 1


@pytest.mark.django_db
@patch("requests.get")
def test_weather_service_fetch_and_store(mock_get):
    """
    Simula una llamada a la API de Open-Meteo y verifica que los datos se almacenen correctamente.
    """
    country = Country.objects.create(name="Spain", code2="ES")
    city = City.objects.create(
        name="Madrid", country=country, latitude=40.4168, longitude=-3.7038
    )

    # Mock de la respuesta de Open-Meteo
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "current": {
            "time": "2024-03-03T18:00",
            "temperature_2m": 25.0,
            "apparent_temperature": 24.5,
            "weather_code": 0,
            "relative_humidity_2m": 50,
            "pressure_msl": 1013.0,
            "wind_speed_10m": 5.0,
            "wind_direction_10m": 180,
            "cloud_cover": 0,
            "rain": 0.0,
            "showers": 0.0,
            "snowfall": 0.0,
        },
        "daily": {
            "temperature_2m_max": [26.0],
            "temperature_2m_min": [24.0],
            "sunrise": ["2024-03-03T07:00"],
            "sunset": ["2024-03-03T19:00"],
        },
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    weather = WeatherService.fetch_and_store_weather(city)

    assert weather.temperature == 25.0
    assert weather.temp_max == 26.0
    assert weather.temp_min == 24.0
    assert weather.main_status == "Clear"
    assert weather.description == "Cielo despejado"
    assert weather.city == city
    assert weather.sunrise is not None
    assert weather.sunset is not None
    assert WeatherContext.objects.count() == 1


@pytest.mark.django_db
def test_weather_service_no_coordinates():
    """
    Verifica que el servicio lance un ValueError si la ciudad no tiene coordenadas.
    """
    country = Country.objects.create(name="Spain", code2="ES")
    city = City.objects.create(name="Madrid", country=country)  # No coordinates

    with pytest.raises(ValueError, match="no tiene coordenadas configuradas"):
        WeatherService.fetch_and_store_weather(city)


@pytest.mark.django_db
@patch("requests.get")
def test_weather_service_api_exception(mock_get):
    """
    Verifica que el servicio lance una excepción si la API falla.
    """
    import requests

    country = Country.objects.create(name="Spain", code2="ES")
    city = City.objects.create(
        name="Madrid", country=country, latitude=40.4, longitude=-3.7
    )

    mock_get.side_effect = requests.exceptions.RequestException("API down")

    with pytest.raises(requests.exceptions.RequestException):
        WeatherService.fetch_and_store_weather(city)


@pytest.mark.django_db
@patch("requests.get")
def test_weather_service_partial_response(mock_get):
    """
    Verifica que el servicio sea robusto frente a respuestas parciales (nulos o datos faltantes).
    """
    country = Country.objects.create(name="Spain", code2="ES")
    city = City.objects.create(
        name="Madrid", country=country, latitude=40.4, longitude=-3.7
    )

    mock_response = MagicMock()
    # Respuesta mínima necesaria para no fallar en el procesamiento básico
    mock_response.json.return_value = {
        "current": {
            "time": "2024-03-03T18:00",
            "temperature_2m": 25.0,
            "apparent_temperature": 24.5,
            # Faltan muchos campos
        },
        "daily": {
            # Faltan todos los campos diarios
        },
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    weather = WeatherService.fetch_and_store_weather(city)

    assert weather.temperature == 25.0
    assert weather.temp_max is None
    assert weather.main_status == "Clear"  # Default for code 0 if missing
    assert WeatherContext.objects.count() == 1
