from django.contrib.auth import get_user_model
from django.core.management import call_command

import pytest

from apps.context.models import NewsContext, WeatherContext
from pipelines.state_pipeline import build_latest_state_for_user

User = get_user_model()


@pytest.mark.django_db
def test_seed_synthetic_context_creates_rows():
    WeatherContext.objects.all().delete()
    NewsContext.objects.all().delete()

    call_command(
        "seed_synthetic_context",
        weather_count=7,
        news_count=9,
        days_back=3,
        seed=11,
        clear_existing=True,
    )

    assert WeatherContext.objects.count() == 7
    assert NewsContext.objects.count() == 9


@pytest.mark.django_db
def test_seeded_context_can_build_latest_state():
    call_command(
        "seed_synthetic_context",
        weather_count=3,
        news_count=5,
        days_back=2,
        seed=21,
        clear_existing=True,
    )

    user = User.objects.create_user(
        username="offline_state_user",
        email="offline_state_user@example.com",
        password="pass12345",
    )

    state = build_latest_state_for_user(user)

    assert state.shape == (45,)
