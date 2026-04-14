"""Seed synthetic weather and news context for fully offline development."""

from __future__ import annotations

import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from apps.context.models import NewsContext, WeatherContext


class Command(BaseCommand):
    help = "Generate synthetic WeatherContext and NewsContext records without external APIs."

    WEATHER_TEMPLATES = [
        ("Clear", "clear sky", "01d"),
        ("Clouds", "scattered clouds", "03d"),
        ("Rain", "light rain", "10d"),
        ("Thunderstorm", "thunderstorm", "11d"),
        ("Snow", "light snow", "13d"),
        ("Fog", "foggy", "50d"),
    ]

    NEWS_TEMPLATES = [
        ("positive", 0.65, "record growth", "Market Pulse"),
        ("neutral", 0.05, "mixed outlook", "Daily Brief"),
        ("negative", -0.55, "unexpected decline", "Global Report"),
    ]

    CATEGORIES = ["general", "music", "markets", "sports", "politics"]

    def add_arguments(self, parser):
        parser.add_argument("--weather-count", type=int, default=50)
        parser.add_argument("--news-count", type=int, default=80)
        parser.add_argument("--days-back", type=int, default=15)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--clear-existing", action="store_true")

    def handle(self, *args, **options):
        self._ensure_required_tables_exist()

        rng = random.Random(options["seed"])
        weather_count = max(0, options["weather_count"])
        news_count = max(0, options["news_count"])
        days_back = max(1, options["days_back"])

        if options["clear_existing"]:
            WeatherContext.objects.all().delete()
            NewsContext.objects.all().delete()

        now = timezone.now()

        weather_created = 0
        for _ in range(weather_count):
            main_status, description, icon_code = rng.choice(self.WEATHER_TEMPLATES)
            timestamp = now - timedelta(
                days=rng.randint(0, days_back),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )
            temperature = round(rng.uniform(-3, 36), 1)
            feels_like = round(temperature + rng.uniform(-3, 3), 1)

            WeatherContext.objects.create(
                main_status=main_status,
                description=description,
                icon_code=icon_code,
                temperature=temperature,
                feels_like=feels_like,
                temp_min=round(temperature - rng.uniform(0, 4), 1),
                temp_max=round(temperature + rng.uniform(0, 5), 1),
                pressure=rng.randint(980, 1035),
                humidity=rng.randint(25, 95),
                visibility=rng.randint(4000, 10000),
                wind_speed=round(rng.uniform(0, 18), 1),
                wind_deg=rng.randint(0, 359),
                wind_gust=round(rng.uniform(0, 22), 1),
                clouds_all=rng.randint(0, 100),
                rain_1h=round(max(0, rng.gauss(0.6, 1.2)), 2),
                snow_1h=round(max(0, rng.gauss(0.2, 0.8)), 2),
                timestamp=timestamp,
                sunrise=timestamp.replace(hour=7, minute=0, second=0, microsecond=0),
                sunset=timestamp.replace(hour=19, minute=30, second=0, microsecond=0),
            )
            weather_created += 1

        news_created = 0
        for idx in range(news_count):
            label, base_score, phrase, source = rng.choice(self.NEWS_TEMPLATES)
            category = rng.choice(self.CATEGORIES)
            published_at = now - timedelta(
                days=rng.randint(0, days_back),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )
            score = max(-1.0, min(1.0, round(base_score + rng.uniform(-0.2, 0.2), 2)))
            NewsContext.objects.create(
                title=f"Synthetic {category} headline #{idx + 1}: {phrase}",
                source=source,
                url=f"https://offline.local/{category}/news/{options['seed']}-{idx}",
                summary=f"Offline generated article about {category} with sentiment {label}.",
                language="en",
                category=category,
                sentiment_score=score,
                sentiment_label=label,
                is_breaking=bool(rng.random() < 0.15),
                published_at=published_at,
            )
            news_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created synthetic context: {weather_created} weather rows and {news_created} news rows."
            )
        )

    def _ensure_required_tables_exist(self):
        existing = set(connection.introspection.table_names())
        required = {
            WeatherContext._meta.db_table,
            NewsContext._meta.db_table,
        }
        missing = sorted(required - existing)
        if missing:
            missing_text = ", ".join(missing)
            raise CommandError(
                "Missing required tables for synthetic context seeding: "
                f"{missing_text}. Run 'python manage.py migrate' first."
            )
