"""Build end-to-end RL state from persisted context data."""

from django.contrib.auth import get_user_model

from apps.context.models import NewsContext, WeatherContext
from ml.state_builder import get_state_builder

User = get_user_model()


def build_latest_state_for_user(user: User, weather_id: int | None = None):
    """Construct a normalized state vector using latest weather and news rows."""
    builder = get_state_builder()

    weather = None
    weather_obj = None
    if weather_id:
        weather_obj = WeatherContext.objects.filter(id=weather_id).first()
    if weather_obj is None:
        weather_obj = WeatherContext.objects.order_by("-timestamp").first()

    if weather_obj is not None:
        weather = {
            "temperature": weather_obj.temperature,
            "feels_like": weather_obj.feels_like,
            "humidity": weather_obj.humidity,
            "wind_speed": weather_obj.wind_speed,
            "pressure": weather_obj.pressure,
            "visibility": weather_obj.visibility,
            "clouds_all": weather_obj.clouds_all,
            "rain_probability": weather_obj.rain_1h or 0,
            "main_status": weather_obj.main_status,
        }

    latest_news = list(NewsContext.objects.order_by("-published_at")[:20])
    news_contexts = [
        {
            "sentiment_score": n.sentiment_score,
            "sentiment_label": n.sentiment_label,
            "is_breaking": n.is_breaking,
        }
        for n in latest_news
    ]

    return builder.build_state(
        user=user,
        weather_context=weather,
        current_track=None,
        news_contexts=news_contexts,
    )
