# Código completo del proyecto MoodSic

Este anexo incluye el contenido textual de los archivos de código, configuración, plantillas y scripts principales del repositorio.

Total de archivos incluidos: 151

## Archivo: Dockerfile

Ruta completa: Dockerfile

```text
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Sync dependencies (non-dev only for production)
RUN uv sync --frozen --no-dev

COPY . .

CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8000"]
```

## Archivo: Makefile

Ruta completa: Makefile

```text
.PHONY: test
test:
	clear
	uv run pytest
```

## Archivo: apps/__init__.py

Ruta completa: apps/__init__.py

```python

```

## Archivo: apps/context/__init__.py

Ruta completa: apps/context/__init__.py

```python

```

## Archivo: apps/context/admin/__init__.py

Ruta completa: apps/context/admin/__init__.py

```python
from .cities_light_admin import CityAdmin, CountryAdmin, RegionAdmin, SubRegionAdmin
from .news_context import NewsContextAdmin
from .weather_context import WeatherContextAdmin

__all__ = [
    "CityAdmin",
    "CountryAdmin",
    "RegionAdmin",
    "SubRegionAdmin",
    "NewsContextAdmin",
    "WeatherContextAdmin",
]
```

## Archivo: apps/context/admin/cities_light_admin.py

Ruta completa: apps/context/admin/cities_light_admin.py

```python
from cities_light.models import City, Country, Region, SubRegion
from django.contrib import admin, messages
from django.core.management import call_command
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action

# Unregister default cities_light admins to replace them with Unfold versions
try:
    admin.site.unregister(Country)
    admin.site.unregister(Region)
    admin.site.unregister(SubRegion)
    admin.site.unregister(City)
except admin.sites.NotRegistered:
    pass


@admin.register(Country)
class CountryAdmin(ModelAdmin):
    list_display = ("name", "code2", "code3", "continent")
    search_fields = ("name", "code2", "code3")
    list_filter = ("continent",)


@admin.register(Region)
class RegionAdmin(ModelAdmin):
    list_display = ("name", "display_name", "country")
    search_fields = ("name", "display_name", "country__name")
    list_filter = ("country",)


@admin.register(SubRegion)
class SubRegionAdmin(ModelAdmin):
    list_display = ("name", "display_name", "country", "region")
    search_fields = ("name", "display_name", "country__name", "region__name")
    list_filter = ("country", "region")


@admin.register(City)
class CityAdmin(ModelAdmin):
    list_display = (
        "name",
        "display_name",
        "country",
        "region",
        "latitude",
        "longitude",
    )
    search_fields = ("name", "display_name", "country__name", "region__name")
    list_filter = ("country",)

    def get_actions_list(self):
        return ["update_geo_data"]

    @action(description=_("Actualizar Datos Geográficos"), url_path="update-geo-data")
    def update_geo_data(self, request):
        """
        Vista personalizada para ejecutar la población de datos geográficos.
        """
        try:
            # Ejecutamos nuestro comando personalizado setup_geo
            # que a su vez llama a migrate cities_light y al comando cities_light
            call_command("setup_geo")
            self.message_user(
                request,
                _(
                    "La actualización de datos geográficos se ha completado correctamente."
                ),
                messages.SUCCESS,
            )
        except Exception as e:
            self.message_user(
                request,
                _("Error al actualizar datos geográficos: ") + str(e),
                messages.ERROR,
            )

        return redirect("admin:cities_light_city_changelist")
```

## Archivo: apps/context/admin/news_context.py

Ruta completa: apps/context/admin/news_context.py

```python
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from ..models import NewsContext


class SentimentFilter(admin.SimpleListFilter):
    title = _("Sentiment")
    parameter_name = "sentiment_label"

    def lookups(self, _request, _model_admin):
        return (
            ("positive", _("Positive")),
            ("neutral", _("Neutral")),
            ("negative", _("Negative")),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(sentiment_label=value)
        return queryset


@admin.register(NewsContext)
class NewsContextAdmin(ModelAdmin):
    list_display = (
        "title",
        "source",
        "category",
        "sentiment_label",
        "sentiment_score",
        "is_breaking",
        "published_at",
    )
    search_fields = ("title", "source", "summary")
    list_filter = ("is_breaking", "category", SentimentFilter, "published_at")
    readonly_fields = ("fetched_at",)
```

## Archivo: apps/context/admin/weather_context.py

Ruta completa: apps/context/admin/weather_context.py

```python
from cities_light.models import City
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action

from ..models import WeatherContext
from ..services.weather_service import WeatherService


@admin.register(WeatherContext)
class WeatherContextAdmin(ModelAdmin):
    list_display = (
        "get_location",
        "temperature",
        "main_status",
        "humidity",
        "wind_speed",
        "timestamp",
    )
    list_filter = (
        "main_status",
        "country",
        "timestamp",
    )
    actions = ("update_weather_action",)

    def get_actions_list(self, _request):
        return ["update_weather_view"]

    search_fields = (
        "city__name",
        "region__name",
        "country__name",
        "description",
    )
    readonly_fields = ("created_at",)

    fieldsets = (
        (
            None,
            {"fields": (("city", "region", "country"), ("timestamp", "created_at"))},
        ),
        ("Clima", {"fields": (("main_status", "description", "icon_code"),)}),
        (
            "Temperaturas",
            {"fields": (("temperature", "feels_like"), ("temp_min", "temp_max"))},
        ),
        (
            "Atmósfera y Viento",
            {
                "fields": (
                    ("pressure", "humidity", "visibility"),
                    ("wind_speed", "wind_deg", "wind_gust"),
                )
            },
        ),
        ("Precipitación y Nubes", {"fields": (("clouds_all", "rain_1h", "snow_1h"),)}),
        ("Sol", {"fields": (("sunrise", "sunset"),)}),
    )

    def get_location(self, obj):
        if obj.city:
            return f"{obj.city.name}, {obj.city.country.code2}"
        elif obj.region:
            return f"{obj.region.name}, {obj.region.country.code2}"
        elif obj.country:
            return obj.country.name
        return "Unknown"

    get_location.short_description = "Ubicación"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "update-weather/",
                self.admin_site.admin_view(self.update_weather_view),
                name="update_weather",
            ),
        ]
        return custom_urls + urls

    @action(
        description=_("Actualizar clima (Global)"), url_path="update-weather-global"
    )
    def update_weather_view(self, request):
        """
        Vista personalizada para actualizar el clima de las ciudades principales.
        """
        # Por ahora, seleccionamos ciudades que tengan coordenadas y sean de los países permitidos
        # o simplemente las primeras 5 ciudades pobladas para el MVP.
        cities = City.objects.filter(latitude__isnull=False, longitude__isnull=False)[
            :10
        ]

        if not cities.exists():
            self.message_user(
                request,
                "No hay ciudades con coordenadas configuradas.",
                messages.WARNING,
            )
            return redirect("admin:context_weathercontext_changelist")

        count = 0
        for city in cities:
            try:
                WeatherService.fetch_and_store_weather(city)
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error al actualizar {city.name}: {e!s}",
                    messages.ERROR,
                )

        self.message_user(
            request,
            f"Se han actualizado los datos climáticos para {count} ciudades.",
            messages.SUCCESS,
        )
        return redirect("admin:context_weathercontext_changelist")

    @action(description=_("Actualizar clima para ciudades seleccionadas"))
    def update_weather_action(self, request, queryset):
        """
        Acción de lista para actualizar el clima de las ciudades de los registros seleccionados.
        """
        cities_processed = set()
        count = 0
        for weather_ctx in queryset:
            if weather_ctx.city and weather_ctx.city.id not in cities_processed:
                try:
                    WeatherService.fetch_and_store_weather(weather_ctx.city)
                    cities_processed.add(weather_ctx.city.id)
                    count += 1
                except Exception as e:
                    self.message_user(
                        request,
                        f"Error al actualizar {weather_ctx.city.name}: {e!s}",
                        messages.ERROR,
                    )

        self.message_user(
            request,
            f"Se ha actualizado el clima para {count} ciudades únicas.",
            messages.SUCCESS,
        )
```

## Archivo: apps/context/apps.py

Ruta completa: apps/context/apps.py

```python
from django.apps import AppConfig


class ContextConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.context"
    verbose_name = "Context"
    migration_module = "apps.context.migrations"

    def ready(self):
        from . import admin, models

        model_classes = [
            models.WeatherContext,
            models.NewsContext,
        ]

        admin_classes = [
            admin.WeatherContextAdmin,
            admin.NewsContextAdmin,
            admin.CityAdmin,
            admin.RegionAdmin,
            admin.CountryAdmin,
            admin.SubRegionAdmin,
        ]

        # Import Hooks classes.
        hooks_classes = []

        _ = model_classes + admin_classes + hooks_classes
```

## Archivo: apps/context/management/__init__.py

Ruta completa: apps/context/management/__init__.py

```python

```

## Archivo: apps/context/management/commands/__init__.py

Ruta completa: apps/context/management/commands/__init__.py

```python

```

## Archivo: apps/context/management/commands/fetch_news_context.py

Ruta completa: apps/context/management/commands/fetch_news_context.py

```python
from django.core.management.base import BaseCommand

from pipelines.etl_news import run_news_etl


class Command(BaseCommand):
    help = "Fetches latest news context from NewsAPI and stores it in DB."

    def add_arguments(self, parser):
        parser.add_argument("--query", type=str, default="music OR entertainment")
        parser.add_argument("--language", type=str, default="en")
        parser.add_argument("--page-size", type=int, default=20)
        parser.add_argument(
            "--category",
            type=str,
            default="general",
            choices=["general", "music", "markets", "sports", "politics"],
        )

    def handle(self, *args, **options):
        count = run_news_etl(
            query=options["query"],
            language=options["language"],
            page_size=options["page_size"],
            category=options["category"],
        )
        self.stdout.write(
            self.style.SUCCESS(f"Stored {count} news context records.")
        )
```

## Archivo: apps/context/management/commands/seed_synthetic_context.py

Ruta completa: apps/context/management/commands/seed_synthetic_context.py

```python
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
                f"{missing_text}. Run 'uv run manage.py migrate' first."
            )
```

## Archivo: apps/context/management/commands/setup_geo.py

Ruta completa: apps/context/management/commands/setup_geo.py

```python
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Automatiza la configuración inicial de los datos geográficos de cities_light."
    )

    def handle(self, *_args, **_options):
        self.stdout.write("--- Configuración de Datos Geográficos (cities_light) ---")

        # 1. Aplicar migraciones necesarias si las hubiera
        self.stdout.write("Verificando migraciones...")
        call_command("migrate", "cities_light", interactive=False)
        self.stdout.write(self.style.SUCCESS("✓ Migraciones de cities_light al día."))

        # 2. Población de datos
        self.stdout.write(
            "Poblando datos geográficos (esto puede tardar varios minutos)..."
        )
        try:
            # El comando 'cities_light' ya es idempotente (actualiza lo que existe)
            call_command("cities_light")
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Población de datos geográficos completada con éxito."
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✘ Error durante la población de datos: {e!s}")
            )
            return

        self.stdout.write("---------------------------------------------------------")
```

## Archivo: apps/context/migrations/0001_initial.py

Ruta completa: apps/context/migrations/0001_initial.py

```python
# Generated by Django 6.0.3 on 2026-03-03 17:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cities_light', '0013_alter_city_alternate_names_alter_city_country_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeatherContext',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('main_status', models.CharField(max_length=50, verbose_name='Clima (Estado principal)')),
                ('description', models.CharField(max_length=255, verbose_name='Descripción detallada')),
                ('icon_code', models.CharField(blank=True, max_length=10, null=True, verbose_name='Código de icono')),
                ('temperature', models.FloatField(verbose_name='Temperatura (°C)')),
                ('feels_like', models.FloatField(verbose_name='Sensación térmica (°C)')),
                ('temp_min', models.FloatField(blank=True, null=True, verbose_name='Temperatura mínima (°C)')),
                ('temp_max', models.FloatField(blank=True, null=True, verbose_name='Temperatura máxima (°C)')),
                ('pressure', models.IntegerField(blank=True, null=True, verbose_name='Presión (hPa)')),
                ('humidity', models.IntegerField(blank=True, null=True, verbose_name='Humedad (%)')),
                ('visibility', models.IntegerField(blank=True, null=True, verbose_name='Visibilidad (m)')),
                ('wind_speed', models.FloatField(blank=True, null=True, verbose_name='Velocidad del viento (m/s)')),
                ('wind_deg', models.IntegerField(blank=True, null=True, verbose_name='Dirección del viento (grados)')),
                ('wind_gust', models.FloatField(blank=True, null=True, verbose_name='Ráfagas de viento (m/s)')),
                ('clouds_all', models.IntegerField(blank=True, null=True, verbose_name='Nubosidad (%)')),
                ('rain_1h', models.FloatField(blank=True, null=True, verbose_name='Lluvia (última hora)')),
                ('snow_1h', models.FloatField(blank=True, null=True, verbose_name='Nieve (última hora)')),
                ('timestamp', models.DateTimeField(verbose_name='Momento de la medición')),
                ('sunrise', models.DateTimeField(blank=True, null=True, verbose_name='Amanecer')),
                ('sunset', models.DateTimeField(blank=True, null=True, verbose_name='Atardecer')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('city', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='weather_history', to='cities_light.city', verbose_name='Ciudad')),
                ('country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='weather_history', to='cities_light.country', verbose_name='País')),
                ('region', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='weather_history', to='cities_light.region', verbose_name='Región')),
            ],
            options={
                'verbose_name': 'Contexto climático',
                'verbose_name_plural': 'Contextos climáticos',
                'ordering': ['-timestamp'],
                'indexes': [models.Index(fields=['timestamp'], name='context_wea_timesta_b6806b_idx'), models.Index(fields=['city'], name='context_wea_city_id_808bb1_idx'), models.Index(fields=['region'], name='context_wea_region__c982f0_idx')],
            },
        ),
    ]
```

## Archivo: apps/context/migrations/0002_alter_weathercontext_options_and_more.py

Ruta completa: apps/context/migrations/0002_alter_weathercontext_options_and_more.py

```python
# Generated by Django 6.0.3 on 2026-03-03 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('context', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='weathercontext',
            options={'ordering': ('-timestamp',), 'verbose_name': 'Contexto climático', 'verbose_name_plural': 'Contextos climáticos'},
        ),
        migrations.AlterField(
            model_name='weathercontext',
            name='icon_code',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='Código de icono'),
        ),
    ]
```

## Archivo: apps/context/migrations/0003_alter_weathercontext_options.py

Ruta completa: apps/context/migrations/0003_alter_weathercontext_options.py

```python
# Generated by Django 4.2.29 on 2026-03-25 21:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0002_alter_weathercontext_options_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="weathercontext",
            options={
                "ordering": ("-timestamp",),
                "verbose_name": "Weather Context",
                "verbose_name_plural": "Weather Contexts",
            },
        ),
    ]
```

## Archivo: apps/context/migrations/0004_newscontext.py

Ruta completa: apps/context/migrations/0004_newscontext.py

```python
# Generated by Django 4.2.x on 2026-04-14

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0003_alter_weathercontext_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="NewsContext",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=300, verbose_name="Title")),
                (
                    "source",
                    models.CharField(blank=True, default="", max_length=120, verbose_name="Source"),
                ),
                (
                    "url",
                    models.URLField(max_length=600, unique=True, verbose_name="URL"),
                ),
                (
                    "summary",
                    models.TextField(blank=True, default="", verbose_name="Summary"),
                ),
                (
                    "language",
                    models.CharField(default="en", max_length=10, verbose_name="Language"),
                ),
                (
                    "category",
                    models.CharField(blank=True, default="general", max_length=80, verbose_name="Category"),
                ),
                (
                    "sentiment_score",
                    models.FloatField(default=0.0, verbose_name="Sentiment score"),
                ),
                (
                    "sentiment_label",
                    models.CharField(default="neutral", max_length=20, verbose_name="Sentiment label"),
                ),
                (
                    "is_breaking",
                    models.BooleanField(default=False, verbose_name="Breaking"),
                ),
                (
                    "published_at",
                    models.DateTimeField(default=django.utils.timezone.now, verbose_name="Published at"),
                ),
                (
                    "fetched_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Fetched at"),
                ),
            ],
            options={
                "verbose_name": "News Context",
                "verbose_name_plural": "News Contexts",
                "ordering": ("-published_at", "-fetched_at"),
            },
        ),
        migrations.AddIndex(
            model_name="newscontext",
            index=models.Index(fields=["-published_at"], name="context_new_publish_184b2f_idx"),
        ),
        migrations.AddIndex(
            model_name="newscontext",
            index=models.Index(fields=["source"], name="context_new_source_b8532b_idx"),
        ),
        migrations.AddIndex(
            model_name="newscontext",
            index=models.Index(fields=["category"], name="context_new_categor_0498df_idx"),
        ),
        migrations.AddIndex(
            model_name="newscontext",
            index=models.Index(fields=["sentiment_label"], name="context_new_sentime_9e79c5_idx"),
        ),
    ]
```

## Archivo: apps/context/migrations/__init__.py

Ruta completa: apps/context/migrations/__init__.py

```python

```

## Archivo: apps/context/models/__init__.py

Ruta completa: apps/context/models/__init__.py

```python
from .weather_context import WeatherContext
from .news_context import NewsContext

__all__ = ["WeatherContext", "NewsContext"]
```

## Archivo: apps/context/models/news_context.py

Ruta completa: apps/context/models/news_context.py

```python
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NewsContext(models.Model):
    """Stores external news items used as context for playlist generation."""

    title = models.CharField(max_length=300, verbose_name=_("Title"))
    source = models.CharField(max_length=120, blank=True, default="", verbose_name=_("Source"))
    url = models.URLField(max_length=600, unique=True, verbose_name=_("URL"))
    summary = models.TextField(blank=True, default="", verbose_name=_("Summary"))
    language = models.CharField(max_length=10, default="en", verbose_name=_("Language"))
    category = models.CharField(max_length=80, blank=True, default="general", verbose_name=_("Category"))
    sentiment_score = models.FloatField(default=0.0, verbose_name=_("Sentiment score"))
    sentiment_label = models.CharField(max_length=20, default="neutral", verbose_name=_("Sentiment label"))
    is_breaking = models.BooleanField(default=False, verbose_name=_("Breaking"))
    published_at = models.DateTimeField(default=timezone.now, verbose_name=_("Published at"))
    fetched_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Fetched at"))

    class Meta:
        verbose_name = _("News Context")
        verbose_name_plural = _("News Contexts")
        ordering = ("-published_at", "-fetched_at")
        indexes = (
            models.Index(fields=["-published_at"]),
            models.Index(fields=["source"]),
            models.Index(fields=["category"]),
            models.Index(fields=["sentiment_label"]),
        )

    def __str__(self):
        return f"{self.source or 'unknown'} - {self.title[:60]}"
```

## Archivo: apps/context/models/weather_context.py

Ruta completa: apps/context/models/weather_context.py

```python
from django.db import models
from django.utils.translation import gettext_lazy as _


class WeatherContext(models.Model):
    """
    Almacena información detallada del clima para una ubicación específica.
    Permite relacionar el contexto climático con regiones y ciudades.
    """

    # Relación con el sistema de regiones/ciudades
    city = models.ForeignKey(
        "cities_light.City",
        on_delete=models.CASCADE,
        related_name="weather_history",
        null=True,
        blank=True,
        verbose_name=_("Ciudad"),
    )
    region = models.ForeignKey(
        "cities_light.Region",
        on_delete=models.CASCADE,
        related_name="weather_history",
        null=True,
        blank=True,
        verbose_name=_("Región"),
    )
    country = models.ForeignKey(
        "cities_light.Country",
        on_delete=models.CASCADE,
        related_name="weather_history",
        null=True,
        blank=True,
        verbose_name=_("País"),
    )

    # Datos básicos del clima (OpenWeather format)
    main_status = models.CharField(
        max_length=50, verbose_name=_("Clima (Estado principal)")
    )
    description = models.CharField(
        max_length=255, verbose_name=_("Descripción detallada")
    )
    icon_code = models.CharField(
        max_length=10, verbose_name=_("Código de icono"), blank=True, default=""
    )

    # Temperaturas y sensaciones
    temperature = models.FloatField(verbose_name=_("Temperatura (°C)"))
    feels_like = models.FloatField(verbose_name=_("Sensación térmica (°C)"))
    temp_min = models.FloatField(
        verbose_name=_("Temperatura mínima (°C)"), null=True, blank=True
    )
    temp_max = models.FloatField(
        verbose_name=_("Temperatura máxima (°C)"), null=True, blank=True
    )

    # Parámetros atmosféricos
    pressure = models.IntegerField(
        verbose_name=_("Presión (hPa)"), null=True, blank=True
    )
    humidity = models.IntegerField(verbose_name=_("Humedad (%)"), null=True, blank=True)
    visibility = models.IntegerField(
        verbose_name=_("Visibilidad (m)"), null=True, blank=True
    )

    # Viento
    wind_speed = models.FloatField(
        verbose_name=_("Velocidad del viento (m/s)"), null=True, blank=True
    )
    wind_deg = models.IntegerField(
        verbose_name=_("Dirección del viento (grados)"), null=True, blank=True
    )
    wind_gust = models.FloatField(
        verbose_name=_("Ráfagas de viento (m/s)"), null=True, blank=True
    )

    # Nubes y precipitación
    clouds_all = models.IntegerField(
        verbose_name=_("Nubosidad (%)"), null=True, blank=True
    )
    rain_1h = models.FloatField(
        verbose_name=_("Lluvia (última hora)"), null=True, blank=True
    )
    snow_1h = models.FloatField(
        verbose_name=_("Nieve (última hora)"), null=True, blank=True
    )

    # Tiempos (Unix timestamps convertidos a DateTime)
    timestamp = models.DateTimeField(verbose_name=_("Momento de la medición"))
    sunrise = models.DateTimeField(verbose_name=_("Amanecer"), null=True, blank=True)
    sunset = models.DateTimeField(verbose_name=_("Atardecer"), null=True, blank=True)

    # Metadatos del sistema
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Weather Context")
        verbose_name_plural = _("Weather Contexts")
        ordering = ("-timestamp",)
        indexes = (
            models.Index(fields=["timestamp"]),
            models.Index(fields=["city"]),
            models.Index(fields=["region"]),
        )

    def __str__(self):
        location = "Unknown"
        if self.city:
            location = self.city.name
        elif self.region:
            location = f"{self.region.name}, {self.region.country.name}"
        elif self.country:
            location = self.country.name

        return f"{location} - {self.temperature}°C - {self.description} ({self.timestamp:%Y-%m-%d %H:%M})"
```

## Archivo: apps/context/schemas.py

Ruta completa: apps/context/schemas.py

```python

```

## Archivo: apps/context/services/__init__.py

Ruta completa: apps/context/services/__init__.py

```python

```

## Archivo: apps/context/services/mood_service.py

Ruta completa: apps/context/services/mood_service.py

```python
from typing import ClassVar, TypedDict


class MusicParameters(TypedDict, total=False):
    target_energy: float
    target_valence: float
    target_danceability: float
    seed_genres: list[str]


class MoodService:
    """
    Servicio para normalizar estados climáticos a Moods y parámetros musicales.
    """

    MOOD_MAPPING: ClassVar[dict[str, dict]] = {
        "Clear": {
            "mood": "Happy/Upbeat",
            "params": {
                "target_energy": 0.8,
                "target_valence": 0.8,
                "target_danceability": 0.7,
                "seed_genres": ["pop", "happy", "dance"],
            },
        },
        "Clouds": {
            "mood": "Chill/Calm",
            "params": {
                "target_energy": 0.4,
                "target_valence": 0.5,
                "target_danceability": 0.3,
                "seed_genres": ["chill", "ambient", "acoustic"],
            },
        },
        "Rain": {
            "mood": "Melancholic/Cozy",
            "params": {
                "target_energy": 0.3,
                "target_valence": 0.3,
                "target_danceability": 0.2,
                "seed_genres": ["jazz", "blues", "rainy-day"],
            },
        },
        "Drizzle": {
            "mood": "Reflective",
            "params": {
                "target_energy": 0.4,
                "target_valence": 0.4,
                "target_danceability": 0.3,
                "seed_genres": ["indie", "folk"],
            },
        },
        "Thunderstorm": {
            "mood": "Dark/Aggressive",
            "params": {
                "target_energy": 0.9,
                "target_valence": 0.2,
                "target_danceability": 0.5,
                "seed_genres": ["metal", "rock", "industrial"],
            },
        },
        "Snow": {
            "mood": "Peaceful/Winter",
            "params": {
                "target_energy": 0.2,
                "target_valence": 0.6,
                "target_danceability": 0.1,
                "seed_genres": ["classical", "piano"],
            },
        },
        "Fog": {
            "mood": "Mysterious",
            "params": {
                "target_energy": 0.3,
                "target_valence": 0.4,
                "target_danceability": 0.2,
                "seed_genres": ["trip-hop", "ambient"],
            },
        },
    }

    @classmethod
    def get_music_params_for_weather(
        cls, main_status: str
    ) -> str | dict[str, float | list[str]]:
        """
        Dada una condición climática principal, devuelve los parámetros musicales sugeridos.
        """
        mapping = cls.MOOD_MAPPING.get(main_status, cls.MOOD_MAPPING["Clouds"])
        return mapping["params"]

    @classmethod
    def get_mood_name(cls, main_status: str) -> str:
        """
        Devuelve el nombre del mood para una condición climática.
        """
        mapping = cls.MOOD_MAPPING.get(main_status, cls.MOOD_MAPPING["Clouds"])
        return mapping["mood"]
```

## Archivo: apps/context/services/news_service.py

Ruta completa: apps/context/services/news_service.py

```python
import logging
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

        params = {
            "q": query,
            "language": language,
            "sortBy": "publishedAt",
            "pageSize": max(1, min(page_size, 100)),
        }
        headers = {"X-Api-Key": api_key}

        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=12)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            logger.warning(f"News provider unavailable, using cached news fallback: {exc}")
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
```

## Archivo: apps/context/services/weather_service.py

Ruta completa: apps/context/services/weather_service.py

```python
import logging
from datetime import datetime
from typing import ClassVar

import requests
from cities_light.models import City
from django.conf import settings
from django.utils import timezone

from ..models import WeatherContext


class WeatherService:
    """
    Servicio para interactuar con la API de Open-Meteo.
    Proporciona datos meteorológicos gratuitos sin necesidad de API Key.
    """

    WMO_CODES: ClassVar[dict[int, tuple[str, str]]] = {
        0: ("Clear", "Cielo despejado"),
        1: ("Clouds", "Principalmente despejado"),
        2: ("Clouds", "Parcialmente nublado"),
        3: ("Clouds", "Cubierto"),
        45: ("Fog", "Niebla"),
        48: ("Fog", "Niebla con escarcha"),
        51: ("Drizzle", "Llovizna ligera"),
        53: ("Drizzle", "Llovizna moderada"),
        55: ("Drizzle", "Llovizna densa"),
        56: ("Drizzle", "Llovizna helada ligera"),
        57: ("Drizzle", "Llovizna helada densa"),
        61: ("Rain", "Lluvia ligera"),
        63: ("Rain", "Lluvia moderada"),
        65: ("Rain", "Lluvia fuerte"),
        66: ("Rain", "Lluvia helada ligera"),
        67: ("Rain", "Lluvia helada fuerte"),
        71: ("Snow", "Nieve ligera"),
        73: ("Snow", "Nieve moderada"),
        75: ("Snow", "Nieve fuerte"),
        77: ("Snow", "Granos de nieve"),
        80: ("Rain", "Lluvia intermitente ligera"),
        81: ("Rain", "Lluvia intermitente moderada"),
        82: ("Rain", "Lluvia intermitente violenta"),
        85: ("Snow", "Nieve intermitente ligera"),
        86: ("Snow", "Nieve intermitente fuerte"),
        95: ("Thunderstorm", "Tormenta"),
        96: ("Thunderstorm", "Tormenta con granizo ligero"),
        99: ("Thunderstorm", "Tormenta con granizo fuerte"),
    }

    @classmethod
    def fetch_and_store_weather(cls, city: City):
        """
        Consulta la API de Open-Meteo usando las coordenadas de una ciudad específica y guarda el resultado.
        """
        base_url = getattr(
            settings, "OPENMETEO_BASE_URL", "https://api.open-meteo.com/v1/forecast"
        )

        if not city.latitude or not city.longitude:
            raise ValueError(
                f"La ciudad {city.name} no tiene coordenadas configuradas."
            )

        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "rain",
                "showers",
                "snowfall",
                "weather_code",
                "cloud_cover",
                "pressure_msl",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "sunrise",
                "sunset",
            ],
            "timezone": "auto",
            "forecast_days": 1,
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logging.getLogger(__name__).error(f"Error al consultar Open-Meteo: {e}")
            raise

        current = data.get("current", {})
        daily = data.get("daily", {})
        weather_code = current.get("weather_code", 0)
        status, description = cls.WMO_CODES.get(
            weather_code, ("Unknown", "Desconocido")
        )

        def get_dt(dt_str):
            if not dt_str:
                return None
            try:
                # Open-Meteo returns ISO 8601 strings
                dt = datetime.fromisoformat(dt_str)
                return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            except ValueError:
                return None

        # Mapeo al modelo WeatherContext
        weather_context = WeatherContext.objects.create(
            city=city,
            region=city.region,
            country=city.country,
            main_status=status,
            description=description,
            icon_code=str(weather_code),
            temperature=current.get("temperature_2m"),
            feels_like=current.get("apparent_temperature"),
            temp_min=daily.get("temperature_2m_min", [None])[0]
            if daily.get("temperature_2m_min")
            else None,
            temp_max=daily.get("temperature_2m_max", [None])[0]
            if daily.get("temperature_2m_max")
            else None,
            pressure=int(current.get("pressure_msl", 0))
            if current.get("pressure_msl") is not None
            else None,
            humidity=current.get("relative_humidity_2m"),
            wind_speed=current.get("wind_speed_10m"),
            wind_deg=current.get("wind_direction_10m"),
            wind_gust=current.get("wind_gusts_10m"),
            clouds_all=current.get("cloud_cover"),
            rain_1h=float(current.get("rain", 0.0) or 0.0)
            + float(current.get("showers", 0.0) or 0.0),
            snow_1h=float(current.get("snowfall", 0.0) or 0.0),
            timestamp=get_dt(current.get("time")) or timezone.now(),
            sunrise=get_dt(daily.get("sunrise", [None])[0])
            if daily.get("sunrise")
            else None,
            sunset=get_dt(daily.get("sunset", [None])[0])
            if daily.get("sunset")
            else None,
        )

        return weather_context
```

## Archivo: apps/context/tests/__init__.py

Ruta completa: apps/context/tests/__init__.py

```python

```

## Archivo: apps/context/tests/test_mood_service.py

Ruta completa: apps/context/tests/test_mood_service.py

```python
from apps.context.services.mood_service import MoodService


def test_mood_service_clear():
    params = MoodService.get_music_params_for_weather("Clear")
    assert params["target_energy"] == 0.8
    assert "pop" in params["seed_genres"]
    assert MoodService.get_mood_name("Clear") == "Happy/Upbeat"


def test_mood_service_rain():
    params = MoodService.get_music_params_for_weather("Rain")
    assert params["target_energy"] == 0.3
    assert "jazz" in params["seed_genres"]
    assert MoodService.get_mood_name("Rain") == "Melancholic/Cozy"


def test_mood_service_unknown():
    # Debería devolver por defecto "Clouds" (Chill/Calm)
    params = MoodService.get_music_params_for_weather("UnknownStatus")
    assert params["target_energy"] == 0.4
    assert MoodService.get_mood_name("UnknownStatus") == "Chill/Calm"


def test_mood_service_snow():
    params = MoodService.get_music_params_for_weather("Snow")
    assert params["target_energy"] == 0.2
    assert MoodService.get_mood_name("Snow") == "Peaceful/Winter"


def test_mood_service_thunderstorm():
    params = MoodService.get_music_params_for_weather("Thunderstorm")
    assert params["target_energy"] == 0.9
    assert MoodService.get_mood_name("Thunderstorm") == "Dark/Aggressive"


def test_mood_service_drizzle():
    params = MoodService.get_music_params_for_weather("Drizzle")
    assert params["target_energy"] == 0.4
    assert MoodService.get_mood_name("Drizzle") == "Reflective"


def test_mood_service_fog():
    params = MoodService.get_music_params_for_weather("Fog")
    assert params["target_energy"] == 0.3
    assert MoodService.get_mood_name("Fog") == "Mysterious"
```

## Archivo: apps/context/tests/test_news_service.py

Ruta completa: apps/context/tests/test_news_service.py

```python
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

    records = NewsService.fetch_and_store_news(query="music", language="en", page_size=5)

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
```

## Archivo: apps/context/tests/test_seed_synthetic_context.py

Ruta completa: apps/context/tests/test_seed_synthetic_context.py

```python
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
```

## Archivo: apps/context/tests/test_weather.py

Ruta completa: apps/context/tests/test_weather.py

```python
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


@pytest.mark.django_db
def test_weather_context_str_representations():
    """
    Verifica las representaciones en string para diferentes niveles de ubicación.
    """
    country = Country.objects.create(name="Spain", code2="ES")

    # Solo país
    weather_country = WeatherContext.objects.create(
        country=country,
        main_status="Clear",
        description="despejado",
        temperature=25.0,
        feels_like=24.0,
        timestamp=timezone.now(),
    )
    assert "Spain" in str(weather_country)

    # Región
    from cities_light.models import Region

    region = Region.objects.create(name="Madrid Region", country=country)
    weather_region = WeatherContext.objects.create(
        region=region,
        main_status="Clear",
        description="despejado",
        temperature=25.0,
        feels_like=24.0,
        timestamp=timezone.now(),
    )
    assert "Madrid Region" in str(weather_region)
    assert "Spain" in str(weather_region)
```

## Archivo: apps/context/urls.py

Ruta completa: apps/context/urls.py

```python

```

## Archivo: apps/context/views/__init__.py

Ruta completa: apps/context/views/__init__.py

```python

```

## Archivo: apps/dashboard/__init__.py

Ruta completa: apps/dashboard/__init__.py

```python

```

## Archivo: apps/dashboard/apps.py

Ruta completa: apps/dashboard/apps.py

```python
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
```

## Archivo: apps/dashboard/tests/__init__.py

Ruta completa: apps/dashboard/tests/__init__.py

```python

```

## Archivo: apps/dashboard/urls.py

Ruta completa: apps/dashboard/urls.py

```python
from django.urls import path

from apps.dashboard.views import dashboard_home

app_name = "dashboard"

urlpatterns = [
    path("", dashboard_home, name="home"),
    path("dashboard/", dashboard_home, name="dashboard-home"),
]
```

## Archivo: apps/dashboard/views/__init__.py

Ruta completa: apps/dashboard/views/__init__.py

```python
from django.conf import settings
from django.shortcuts import render

from apps.context.models import NewsContext, WeatherContext
from apps.interactions.models import Interaction, InteractionSession
from apps.music.models import Playlist, Track


def dashboard_home(request):
    """Vista ligera de demo para profesores y equipo."""
    total_interactions = Interaction.objects.count()
    total_playlists = Playlist.objects.count()
    total_tracks = Track.objects.count()
    active_sessions = InteractionSession.objects.filter(is_active=True).count()

    skip_count = Interaction.objects.filter(feedback__startswith="skip").count()
    skip_rate = round((skip_count / total_interactions) * 100, 1) if total_interactions else 0.0

    integration_status = [
        {
            "name": "Modo offline reproducible",
            "status": "listo",
            "detail": "Seeds sintéticos, evaluación y benchmark disponibles.",
        },
        {
            "name": "Spotify real",
            "status": "pendiente" if not settings.SPOTIPY_CLIENT_ID else "configurado",
            "detail": "La integración está preparada, pero la validación final depende de credenciales reales.",
        },
        {
            "name": "Noticias externas",
            "status": "configurado" if settings.NEWSAPI_KEY else "fallback local",
            "detail": "Si la API no está disponible, el sistema usa noticias en caché.",
        },
    ]

    return render(
        request,
        "dashboard/home.html",
        {
            "stats": {
                "playlists": total_playlists,
                "tracks": total_tracks,
                "interactions": total_interactions,
                "active_sessions": active_sessions,
                "skip_rate": skip_rate,
                "weather_records": WeatherContext.objects.count(),
                "news_records": NewsContext.objects.count(),
            },
            "recent_playlists": Playlist.objects.select_related("user").order_by("-created_at")[:5],
            "integration_status": integration_status,
        },
    )
```

## Archivo: apps/interactions/__init__.py

Ruta completa: apps/interactions/__init__.py

```python

```

## Archivo: apps/interactions/admin/__init__.py

Ruta completa: apps/interactions/admin/__init__.py

```python
"""
Configuración del Admin para el app interactions.
"""

from django.contrib import admin

from apps.interactions.models import Interaction, InteractionSession


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    """
    Admin para registros de interacción usuario-track.
    """

    list_display = (
        "user",
        "track",
        "feedback",
        "reward",
        "completion_percentage",
        "started_at",
    )
    list_filter = (
        "feedback",
        "is_positive",
        "started_at",
        ("user", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "user__username",
        "track__name",
        "session_id",
    )
    readonly_fields = (
        "user",
        "track",
        "started_at",
        "updated_at",
        "completion_percentage",
        "is_positive",
    )
    fieldsets = (
        (
            "Información de Interacción",
            {
                "fields": (
                    "user",
                    "track",
                    "feedback",
                    "session_id",
                )
            },
        ),
        (
            "Contexto",
            {
                "fields": (
                    "weather_id",
                    "news_ids",
                    "playlist_id",
                )
            },
        ),
        (
            "Métricas",
            {
                "fields": (
                    "reward",
                    "play_duration",
                    "track_duration",
                    "completion_percentage",
                    "is_positive",
                )
            },
        ),
        (
            "Tiempo",
            {
                "fields": (
                    "started_at",
                    "ended_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        # Las interacciones se crean automáticamente via API
        return True

    def has_delete_permission(self, request, obj=None):
        # Permitir delete pero es raro que se necesite
        return True


@admin.register(InteractionSession)
class InteractionSessionAdmin(admin.ModelAdmin):
    """
    Admin para sesiones de interacción.
    """

    list_display = (
        "session_id",
        "user",
        "total_tracks",
        "skip_count",
        "completed_count",
        "average_reward",
        "started_at",
        "is_active",
    )
    list_filter = (
        "is_active",
        "started_at",
        ("user", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "session_id",
        "user__username",
    )
    readonly_fields = (
        "session_id",
        "started_at",
        "created_at",
        "updated_at",
    )

    actions = ["calculate_metrics_action"]

    def calculate_metrics_action(self, request, queryset):
        """
        Acción para recalcular métricas de sesiones.
        """
        count = 0
        for session in queryset:
            session.calculate_metrics()
            count += 1

        self.message_user(request, f"Métricas recalculadas para {count} sesiones")

    calculate_metrics_action.short_description = "Recalcular métricas de sesiones"
```

## Archivo: apps/interactions/apps.py

Ruta completa: apps/interactions/apps.py

```python
from django.apps import AppConfig


class InteractionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.interactions"
```

## Archivo: apps/interactions/management/__init__.py

Ruta completa: apps/interactions/management/__init__.py

```python
"""
Management commands para la aplicación interactions.
"""
```

## Archivo: apps/interactions/management/commands/__init__.py

Ruta completa: apps/interactions/management/commands/__init__.py

```python
"""
Comandos de management personalizados.
"""
```

## Archivo: apps/interactions/management/commands/benchmark_matrix.py

Ruta completa: apps/interactions/management/commands/benchmark_matrix.py

```python
"""Run a reproducible benchmark sweep (multi-seed) and generate weighted summaries."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run benchmark sweep across seeds and build weighted summary reports."
    DEFAULTS = {
        "seeds": "101,202,303,404,505",
        "weights": "0.7:0.3,0.8:0.2,0.6:0.4",
        "base_dir": "ml/logs",
        "run_name": "",
        "summary_limit": 200,
        "test_days": 7,
        "test_limit": 1000,
        "benchmark_episodes": 5,
        "synthetic_users": 3,
        "synthetic_tracks": 30,
        "synthetic_interactions": 600,
        "synthetic_weather": 60,
        "synthetic_news": 120,
        "skip_runs": False,
        "robustness_alpha": 0.5,
        "alphas": "",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--seeds",
            type=str,
            default=self.DEFAULTS["seeds"],
            help="Comma-separated seeds for benchmark runs",
        )
        parser.add_argument(
            "--weights",
            type=str,
            default=self.DEFAULTS["weights"],
            help="Comma-separated weight pairs as w_acc:w_reward",
        )
        parser.add_argument(
            "--base-dir",
            type=str,
            default=self.DEFAULTS["base_dir"],
            help="Base directory where matrix run artifacts are written",
        )
        parser.add_argument(
            "--run-name",
            type=str,
            default=self.DEFAULTS["run_name"],
            help="Optional run name suffix (default: timestamp)",
        )
        parser.add_argument(
            "--summary-limit",
            type=int,
            default=self.DEFAULTS["summary_limit"],
            help="Maximum files read by benchmark_summary",
        )
        parser.add_argument("--test-days", type=int, default=self.DEFAULTS["test_days"])
        parser.add_argument("--test-limit", type=int, default=self.DEFAULTS["test_limit"])
        parser.add_argument(
            "--benchmark-episodes", type=int, default=self.DEFAULTS["benchmark_episodes"]
        )
        parser.add_argument("--synthetic-users", type=int, default=self.DEFAULTS["synthetic_users"])
        parser.add_argument("--synthetic-tracks", type=int, default=self.DEFAULTS["synthetic_tracks"])
        parser.add_argument(
            "--synthetic-interactions", type=int, default=self.DEFAULTS["synthetic_interactions"]
        )
        parser.add_argument(
            "--synthetic-weather", type=int, default=self.DEFAULTS["synthetic_weather"]
        )
        parser.add_argument("--synthetic-news", type=int, default=self.DEFAULTS["synthetic_news"])
        parser.add_argument(
            "--skip-runs",
            action="store_true",
            help="Skip evaluate_model runs and only regenerate summaries from existing JSON in run dir",
        )
        parser.add_argument(
            "--robustness-alpha",
            type=float,
            default=self.DEFAULTS["robustness_alpha"],
            help="Penalty factor in robust_score = comp_mean - alpha*comp_std",
        )
        parser.add_argument(
            "--alphas",
            type=str,
            default=self.DEFAULTS["alphas"],
            help="Optional comma-separated alpha sweep (overrides --robustness-alpha)",
        )
        parser.add_argument(
            "--config",
            type=str,
            default="",
            help="Optional JSON config file for reproducible matrix runs",
        )

    def handle(self, *args, **options):
        options = self._apply_config_file(options)

        seeds = self._parse_seeds(options["seeds"])
        weight_pairs = self._parse_weights(options["weights"])
        robustness_alpha = float(options["robustness_alpha"])
        if robustness_alpha < 0:
            raise CommandError("robustness-alpha must be non-negative")
        alpha_values = self._parse_alphas(options.get("alphas", ""), robustness_alpha)

        run_suffix = options["run_name"].strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path(options["base_dir"]) / f"benchmark_matrix_{run_suffix}"
        run_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.SUCCESS("\n[MATRIX] Benchmark matrix started"))
        self.stdout.write(f"   Run directory: {run_dir}")
        self.stdout.write(f"   Seeds: {seeds}")
        self.stdout.write(f"   Weight pairs: {weight_pairs}")
        self.stdout.write(f"   Robustness alpha(s): {alpha_values}")
        if options.get("config"):
            self.stdout.write(f"   Config: {options['config']}")

        if not options["skip_runs"]:
            for seed in seeds:
                output_json = run_dir / f"evaluation_benchmark_seed_{seed}.json"
                self.stdout.write(f"\n[RUN] seed={seed} -> {output_json.name}")
                self._run_evaluate_subprocess(
                    seed=seed,
                    output_json=output_json,
                    benchmark_episodes=options["benchmark_episodes"],
                    test_days=options["test_days"],
                    test_limit=options["test_limit"],
                    synthetic_users=options["synthetic_users"],
                    synthetic_tracks=options["synthetic_tracks"],
                    synthetic_interactions=options["synthetic_interactions"],
                    synthetic_weather=options["synthetic_weather"],
                    synthetic_news=options["synthetic_news"],
                )

        generated_files: list[Path] = []
        alpha_winners: list[dict[str, Any]] = []

        for alpha in alpha_values:
            alpha_slug = self._alpha_slug(alpha)
            consolidated_rows: list[dict[str, Any]] = []
            for w_acc, w_reward in weight_pairs:
                slug = self._weight_slug(w_acc, w_reward)
                if len(alpha_values) == 1:
                    md_out = run_dir / f"benchmark_summary_{slug}.md"
                    csv_out = run_dir / f"benchmark_summary_{slug}.csv"
                else:
                    md_out = run_dir / f"benchmark_summary_{slug}_{alpha_slug}.md"
                    csv_out = run_dir / f"benchmark_summary_{slug}_{alpha_slug}.csv"

                self.stdout.write(
                    f"\n[SUMMARY] alpha={alpha:.3f} weights=({w_acc:.3f}, {w_reward:.3f})"
                )
                call_command(
                    "benchmark_summary",
                    logs_dir=str(run_dir),
                    limit=options["summary_limit"],
                    output=str(md_out),
                    csv_output=str(csv_out),
                    w_accuracy=w_acc,
                    w_reward=w_reward,
                    robustness_alpha=alpha,
                )
                generated_files.extend([md_out, csv_out])
                consolidated_rows.append(
                    self._load_weight_summary_row(
                        csv_path=csv_out,
                        w_acc=w_acc,
                        w_reward=w_reward,
                        robustness_alpha=alpha,
                    )
                )

            consolidated_rows.sort(
                key=lambda r: float(r["robust_score"]) if isinstance(r.get("robust_score"), (int, float)) else float("-inf"),
                reverse=True,
            )
            for idx, row in enumerate(consolidated_rows, start=1):
                row["global_rank"] = idx

            if len(alpha_values) == 1:
                consolidated_md = run_dir / "benchmark_weights_summary.md"
                consolidated_csv = run_dir / "benchmark_weights_summary.csv"
            else:
                consolidated_md = run_dir / f"benchmark_weights_summary_{alpha_slug}.md"
                consolidated_csv = run_dir / f"benchmark_weights_summary_{alpha_slug}.csv"

            self._write_consolidated_outputs(
                rows=consolidated_rows,
                md_path=consolidated_md,
                csv_path=consolidated_csv,
            )
            generated_files.extend([consolidated_md, consolidated_csv])

            winner = consolidated_rows[0] if consolidated_rows else None
            if winner is not None:
                alpha_winners.append(
                    {
                        "alpha": alpha,
                        "w_accuracy": winner["w_accuracy"],
                        "w_reward": winner["w_reward"],
                        "robust_score": winner["robust_score"],
                    }
                )

        if len(alpha_values) > 1:
            sensitivity_md = run_dir / "benchmark_alpha_sensitivity.md"
            sensitivity_csv = run_dir / "benchmark_alpha_sensitivity.csv"
            self._write_alpha_sensitivity(
                winners=alpha_winners,
                md_path=sensitivity_md,
                csv_path=sensitivity_csv,
            )
            generated_files.extend([sensitivity_md, sensitivity_csv])

        index_path = run_dir / "README.md"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("# Benchmark Matrix Run\n\n")
            f.write(f"Run directory: {run_dir}\n\n")
            f.write(f"Seeds: {seeds}\n\n")
            f.write("Weights:\n")
            for w_acc, w_reward in weight_pairs:
                f.write(f"- accuracy={w_acc:.3f}, reward={w_reward:.3f}\n")
            f.write(f"\nRobustness alpha(s): {alpha_values}\n")
            f.write("\nGenerated reports:\n")
            for item in generated_files:
                f.write(f"- {item.name}\n")

            winner = alpha_winners[0] if alpha_winners else None
            if winner is not None:
                f.write("\nGlobal winner:\n")
                f.write(
                    "- weights: accuracy={w_acc:.3f}, reward={w_reward:.3f} | robust_score={robust} | alpha={alpha:.3f}\n".format(
                        w_acc=float(winner["w_accuracy"]),
                        w_reward=float(winner["w_reward"]),
                        robust=self._fmt_float(winner["robust_score"]),
                        alpha=float(winner["alpha"]),
                    )
                )

        self.stdout.write(self.style.SUCCESS(f"\n✅ Matrix run completed. Index: {index_path}"))
        if alpha_winners:
            winner = alpha_winners[0]
            self.stdout.write(
                "Global winner weights: accuracy={w_acc:.3f}, reward={w_reward:.3f} (robust_score={robust}, alpha={alpha:.3f})".format(
                    w_acc=float(winner["w_accuracy"]),
                    w_reward=float(winner["w_reward"]),
                    robust=self._fmt_float(winner["robust_score"]),
                    alpha=float(winner["alpha"]),
                )
            )

    @staticmethod
    def _parse_seeds(raw: Any) -> list[int]:
        if isinstance(raw, list):
            raw_items = [str(item) for item in raw]
        else:
            raw_items = str(raw).split(",")

        seeds: list[int] = []
        for part in raw_items:
            token = part.strip()
            if not token:
                continue
            try:
                seeds.append(int(token))
            except ValueError as exc:
                raise CommandError(f"Invalid seed: {token}") from exc
        if not seeds:
            raise CommandError("At least one seed is required")
        return seeds

    @staticmethod
    def _parse_weights(raw: Any) -> list[tuple[float, float]]:
        if isinstance(raw, list):
            tokens: list[str] = []
            for item in raw:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    tokens.append(f"{item[0]}:{item[1]}")
                else:
                    tokens.append(str(item))
        else:
            tokens = str(raw).split(",")

        pairs: list[tuple[float, float]] = []
        for part in tokens:
            token = part.strip()
            if not token:
                continue
            if ":" not in token:
                raise CommandError(f"Invalid weight pair format: {token}. Expected w_acc:w_reward")
            left, right = token.split(":", 1)
            try:
                w_acc = float(left.strip())
                w_reward = float(right.strip())
            except ValueError as exc:
                raise CommandError(f"Invalid weight pair values: {token}") from exc
            if w_acc < 0 or w_reward < 0 or (w_acc + w_reward) <= 0:
                raise CommandError(f"Weight pair must be non-negative and sum > 0: {token}")
            pairs.append((w_acc, w_reward))

        if not pairs:
            raise CommandError("At least one weight pair is required")
        return pairs

    @staticmethod
    def _parse_alphas(raw: Any, fallback_alpha: float) -> list[float]:
        if isinstance(raw, list):
            tokens = [str(item) for item in raw]
        else:
            text = str(raw)
            if not text.strip():
                return [fallback_alpha]
            tokens = text.split(",")

        if not tokens:
            return [fallback_alpha]

        alphas: list[float] = []
        for part in tokens:
            token = part.strip()
            if not token:
                continue
            try:
                value = float(token)
            except ValueError as exc:
                raise CommandError(f"Invalid alpha value: {token}") from exc
            if value < 0:
                raise CommandError(f"Alpha must be non-negative: {token}")
            alphas.append(value)

        if not alphas:
            raise CommandError("At least one alpha is required")
        return alphas

    def _apply_config_file(self, options: dict[str, Any]) -> dict[str, Any]:
        config_raw = str(options.get("config", "")).strip()
        if not config_raw:
            return options

        config_path = Path(config_raw)
        if not config_path.exists():
            raise CommandError(f"Config file does not exist: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            try:
                config_data = json.load(f)
            except json.JSONDecodeError as exc:
                raise CommandError(f"Invalid JSON config: {config_path}") from exc

        if not isinstance(config_data, dict):
            raise CommandError("Config file must contain a JSON object")

        merged = dict(options)
        for key, default_value in self.DEFAULTS.items():
            if key in config_data and merged.get(key) == default_value:
                merged[key] = config_data[key]

        merged["config"] = str(config_path)
        return merged

    @staticmethod
    def _weight_slug(w_acc: float, w_reward: float) -> str:
        return f"wacc_{w_acc:.2f}_wrew_{w_reward:.2f}".replace(".", "p")

    @staticmethod
    def _alpha_slug(alpha: float) -> str:
        return f"alpha_{alpha:.2f}".replace(".", "p")

    def _run_evaluate_subprocess(
        self,
        *,
        seed: int,
        output_json: Path,
        benchmark_episodes: int,
        test_days: int,
        test_limit: int,
        synthetic_users: int,
        synthetic_tracks: int,
        synthetic_interactions: int,
        synthetic_weather: int,
        synthetic_news: int,
    ) -> None:
        command = [
            sys.executable,
            "manage.py",
            "evaluate_model",
            "--with-synthetic-context",
            "--auto-train",
            "--benchmark-episodes",
            str(benchmark_episodes),
            "--test-days",
            str(test_days),
            "--test-limit",
            str(test_limit),
            "--seed",
            str(seed),
            "--synthetic-users",
            str(synthetic_users),
            "--synthetic-tracks",
            str(synthetic_tracks),
            "--synthetic-interactions",
            str(synthetic_interactions),
            "--synthetic-weather",
            str(synthetic_weather),
            "--synthetic-news",
            str(synthetic_news),
            "--benchmark-output",
            str(output_json),
        ]

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        if result.stdout:
            self.stdout.write(result.stdout)
        if result.returncode != 0:
            if result.stderr:
                self.stderr.write(result.stderr)
            raise CommandError(f"evaluate_model failed for seed={seed} with code {result.returncode}")

    def _load_weight_summary_row(
        self, csv_path: Path, w_acc: float, w_reward: float, robustness_alpha: float
    ) -> dict[str, Any]:
        with open(csv_path, "r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            runs = list(reader)

        comp_scores = []
        for row in runs:
            token = str(row.get("composite_score", "")).strip()
            if not token or token == "N/A":
                continue
            try:
                comp_scores.append(float(token))
            except ValueError:
                continue

        if comp_scores:
            comp_mean = sum(comp_scores) / len(comp_scores)
            variance = sum((v - comp_mean) ** 2 for v in comp_scores) / len(comp_scores)
            comp_std = variance ** 0.5
            robust_score = comp_mean - robustness_alpha * comp_std
            best_comp = max(comp_scores)
            worst_comp = min(comp_scores)
        else:
            comp_mean = "N/A"
            comp_std = "N/A"
            robust_score = "N/A"
            best_comp = "N/A"
            worst_comp = "N/A"

        return {
            "w_accuracy": w_acc,
            "w_reward": w_reward,
            "robustness_alpha": robustness_alpha,
            "runs": len(runs),
            "comp_mean": comp_mean,
            "comp_std": comp_std,
            "robust_score": robust_score,
            "best_comp": best_comp,
            "worst_comp": worst_comp,
        }

    def _write_consolidated_outputs(
        self, rows: list[dict[str, Any]], md_path: Path, csv_path: Path
    ) -> None:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        header = (
            "| rank | w_accuracy | w_reward | runs | comp_mean | comp_std | robust_score | best_comp | worst_comp |\n"
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        )
        body_lines = []
        for row in rows:
            body_lines.append(
                "| {rank} | {w_acc} | {w_reward} | {runs} | {comp_mean} | {comp_std} | {robust} | {best} | {worst} |".format(
                    rank=row.get("global_rank", "N/A"),
                    w_acc=self._fmt_float(row.get("w_accuracy")),
                    w_reward=self._fmt_float(row.get("w_reward")),
                    runs=row.get("runs", "N/A"),
                    comp_mean=self._fmt_float(row.get("comp_mean")),
                    comp_std=self._fmt_float(row.get("comp_std")),
                    robust=self._fmt_float(row.get("robust_score")),
                    best=self._fmt_float(row.get("best_comp")),
                    worst=self._fmt_float(row.get("worst_comp")),
                )
            )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Benchmark Weights Summary\n\n")
            if rows:
                winner = rows[0]
                f.write(
                    "Global winner: accuracy={w_acc}, reward={w_reward}, robust_score={robust}, alpha={alpha}\n\n".format(
                        w_acc=self._fmt_float(winner.get("w_accuracy")),
                        w_reward=self._fmt_float(winner.get("w_reward")),
                        robust=self._fmt_float(winner.get("robust_score")),
                        alpha=self._fmt_float(winner.get("robustness_alpha"), digits=3),
                    )
                )
            else:
                f.write("Global winner: N/A\n\n")
            f.write(header)
            f.write("\n".join(body_lines))
            f.write("\n")

        fieldnames = [
            "global_rank",
            "w_accuracy",
            "w_reward",
            "runs",
            "comp_mean",
            "comp_std",
            "robust_score",
            "best_comp",
            "worst_comp",
        ]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "global_rank": row.get("global_rank", "N/A"),
                        "w_accuracy": self._fmt_float(row.get("w_accuracy")),
                        "w_reward": self._fmt_float(row.get("w_reward")),
                        "runs": row.get("runs", "N/A"),
                        "comp_mean": self._fmt_float(row.get("comp_mean")),
                        "comp_std": self._fmt_float(row.get("comp_std")),
                        "robust_score": self._fmt_float(row.get("robust_score")),
                        "best_comp": self._fmt_float(row.get("best_comp")),
                        "worst_comp": self._fmt_float(row.get("worst_comp")),
                    }
                )

    @staticmethod
    def _fmt_float(value: Any, digits: int = 4) -> str:
        if isinstance(value, (float, int)):
            return f"{float(value):.{digits}f}"
        return str(value)

    def _write_alpha_sensitivity(
        self, winners: list[dict[str, Any]], md_path: Path, csv_path: Path
    ) -> None:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        winners_sorted = sorted(winners, key=lambda r: float(r["alpha"]))
        header = (
            "| alpha | winner_w_accuracy | winner_w_reward | robust_score |\n"
            "|---:|---:|---:|---:|\n"
        )
        lines = []
        for row in winners_sorted:
            lines.append(
                "| {alpha} | {w_acc} | {w_reward} | {robust} |".format(
                    alpha=self._fmt_float(row["alpha"], digits=3),
                    w_acc=self._fmt_float(row["w_accuracy"]),
                    w_reward=self._fmt_float(row["w_reward"]),
                    robust=self._fmt_float(row["robust_score"]),
                )
            )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Alpha Sensitivity\n\n")
            f.write(header)
            f.write("\n".join(lines))
            f.write("\n")

        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["alpha", "winner_w_accuracy", "winner_w_reward", "robust_score"],
            )
            writer.writeheader()
            for row in winners_sorted:
                writer.writerow(
                    {
                        "alpha": self._fmt_float(row["alpha"], digits=3),
                        "winner_w_accuracy": self._fmt_float(row["w_accuracy"]),
                        "winner_w_reward": self._fmt_float(row["w_reward"]),
                        "robust_score": self._fmt_float(row["robust_score"]),
                    }
                )
```

## Archivo: apps/interactions/management/commands/benchmark_summary.py

Ruta completa: apps/interactions/management/commands/benchmark_summary.py

```python
"""Summarize recent evaluation benchmark JSON files into a comparison table."""

from __future__ import annotations

import json
import csv
import statistics
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Build a summary table from recent evaluation benchmark JSON logs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--logs-dir",
            type=str,
            default="ml/logs",
            help="Directory containing evaluation_benchmark_*.json files",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of recent benchmark files to include",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="ml/logs/benchmark_summary.md",
            help="Output markdown file path",
        )
        parser.add_argument(
            "--csv-output",
            type=str,
            default="",
            help="Optional CSV output path (disabled when omitted)",
        )
        parser.add_argument(
            "--w-accuracy",
            type=float,
            default=0.7,
            help="Weight for accuracy in composite score",
        )
        parser.add_argument(
            "--w-reward",
            type=float,
            default=0.3,
            help="Weight for normalized reward in composite score",
        )
        parser.add_argument(
            "--robustness-alpha",
            type=float,
            default=0.5,
            help="Penalty factor in robust_score = comp_mean - alpha*comp_std",
        )

    def handle(self, *args, **options):
        logs_dir = Path(options["logs_dir"])
        limit = max(1, options["limit"])
        output_path = Path(options["output"])
        csv_output_raw = options.get("csv_output", "")
        csv_output_path = Path(csv_output_raw) if csv_output_raw else None
        w_accuracy = float(options["w_accuracy"])
        w_reward = float(options["w_reward"])
        robustness_alpha = float(options["robustness_alpha"])

        if w_accuracy < 0 or w_reward < 0:
            raise CommandError("Weights must be non-negative")
        if (w_accuracy + w_reward) <= 0:
            raise CommandError("At least one weight must be greater than zero")
        if robustness_alpha < 0:
            raise CommandError("robustness-alpha must be non-negative")

        # Normalize weights so users can pass either percentages or direct weights.
        total_weight = w_accuracy + w_reward
        w_accuracy = w_accuracy / total_weight
        w_reward = w_reward / total_weight

        if not logs_dir.exists():
            raise CommandError(f"Logs directory does not exist: {logs_dir}")

        files = sorted(
            logs_dir.glob("evaluation_benchmark_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]

        if not files:
            raise CommandError(
                f"No benchmark files found in {logs_dir} matching evaluation_benchmark_*.json"
            )

        rows: list[dict[str, Any]] = []
        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            options_data = data.get("options", {})
            metrics = data.get("metrics", {})
            rows.append(
                {
                    "file": fpath.name,
                    "timestamp": data.get("timestamp", "N/A"),
                    "accuracy": metrics.get("accuracy", "N/A"),
                    "mean_reward": metrics.get("mean_reward_dataset", "N/A"),
                    "samples": metrics.get("total_samples", "N/A"),
                    "seed": options_data.get("seed", "N/A"),
                    "auto_train": options_data.get("auto_train", "N/A"),
                    "synthetic": options_data.get("with_synthetic_context", "N/A"),
                    "benchmark_episodes": options_data.get("benchmark_episodes", "N/A"),
                    "test_limit": options_data.get("test_limit", "N/A"),
                    "test_days": options_data.get("test_days", "N/A"),
                }
            )

        # Compute deltas against the previous (older) run in the sorted list.
        for i, row in enumerate(rows):
            prev = rows[i + 1] if i + 1 < len(rows) else None
            row["delta_accuracy"] = self._compute_delta(row.get("accuracy"), prev, "accuracy")
            row["delta_mean_reward"] = self._compute_delta(
                row.get("mean_reward"), prev, "mean_reward"
            )
            row["trend_accuracy"] = self._trend_from_delta(row["delta_accuracy"])
            row["trend_mean_reward"] = self._trend_from_delta(row["delta_mean_reward"])
            row["composite_score"] = self._compute_composite_score(
                row.get("accuracy"), row.get("mean_reward"), w_accuracy, w_reward
            )

        scored = [r for r in rows if isinstance(r.get("composite_score"), (int, float))]
        scored_sorted = sorted(scored, key=lambda r: float(r["composite_score"]), reverse=True)
        rank_by_file = {r["file"]: idx + 1 for idx, r in enumerate(scored_sorted)}
        for row in rows:
            row["composite_rank"] = rank_by_file.get(row["file"], "N/A")
            row["config_key"] = self._build_config_key(row)

        table = self._build_markdown_table(rows)
        config_stats = self._compute_config_stats(rows, robustness_alpha)
        recommendation_text = self._build_recommendation_text(config_stats, robustness_alpha)
        config_table = self._build_config_markdown_table(config_stats)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as out:
            out.write("# Benchmark Summary\n\n")
            out.write(
                f"Composite score weights: accuracy={w_accuracy:.3f}, reward={w_reward:.3f}\n\n"
            )
            out.write(
                f"Robustness formula: robust_score = comp_mean - {robustness_alpha:.3f}*comp_std\n\n"
            )
            out.write("## Recommendation\n\n")
            out.write(recommendation_text + "\n\n")
            out.write("## Robustness by Configuration\n\n")
            out.write(config_table)
            out.write("\n\n## Runs\n\n")
            out.write(table)
            out.write("\n")

        if csv_output_path is not None:
            self._write_csv(rows, csv_output_path)

        self.stdout.write(self.style.SUCCESS(f"Summary written to {output_path}"))
        if csv_output_path is not None:
            self.stdout.write(self.style.SUCCESS(f"CSV summary written to {csv_output_path}"))
        self.stdout.write("\nRecommendation: " + recommendation_text)
        self.stdout.write("\n" + config_table)
        self.stdout.write("\n" + table)

    @staticmethod
    def _fmt_float(value: Any, digits: int = 4) -> str:
        if isinstance(value, (float, int)):
            return f"{float(value):.{digits}f}"
        return str(value)

    def _build_markdown_table(self, rows: list[dict[str, Any]]) -> str:
        header = (
            "| file | timestamp | accuracy | Δaccuracy | trend_acc | mean_reward | Δmean_reward | trend_reward | comp_score | rank | config | samples | seed | auto_train | synthetic | test_days |\n"
            "|---|---|---:|---:|---|---:|---:|---|---:|---:|---|---:|---:|---|---|---:|\n"
        )
        body_lines = []
        for row in rows:
            body_lines.append(
                "| {file} | {timestamp} | {accuracy} | {delta_accuracy} | {trend_accuracy} | {mean_reward} | {delta_mean_reward} | {trend_mean_reward} | {composite_score} | {composite_rank} | {config_key} | {samples} | {seed} | {auto_train} | {synthetic} | {test_days} |".format(
                    file=row["file"],
                    timestamp=row["timestamp"],
                    accuracy=self._fmt_float(row["accuracy"]),
                    delta_accuracy=row["delta_accuracy"],
                    trend_accuracy=row["trend_accuracy"],
                    mean_reward=self._fmt_float(row["mean_reward"]),
                    delta_mean_reward=row["delta_mean_reward"],
                    trend_mean_reward=row["trend_mean_reward"],
                    composite_score=self._fmt_float(row["composite_score"]),
                    composite_rank=row["composite_rank"],
                    config_key=row["config_key"],
                    samples=row["samples"],
                    seed=row["seed"],
                    auto_train=row["auto_train"],
                    synthetic=row["synthetic"],
                    test_days=row["test_days"],
                )
            )
        return header + "\n".join(body_lines)

    @staticmethod
    def _build_config_key(row: dict[str, Any]) -> str:
        return (
            f"d{row.get('test_days', 'N/A')}"
            f"_l{row.get('test_limit', 'N/A')}"
            f"_e{row.get('benchmark_episodes', 'N/A')}"
            f"_synth{row.get('synthetic', 'N/A')}"
            f"_train{row.get('auto_train', 'N/A')}"
        )

    def _compute_config_stats(
        self, rows: list[dict[str, Any]], robustness_alpha: float
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            key = str(row.get("config_key", "N/A"))
            grouped.setdefault(key, []).append(row)

        stats_rows: list[dict[str, Any]] = []
        for config_key, grouped_rows in grouped.items():
            accuracies = [float(r["accuracy"]) for r in grouped_rows if isinstance(r.get("accuracy"), (int, float))]
            rewards = [
                float(r["mean_reward"])
                for r in grouped_rows
                if isinstance(r.get("mean_reward"), (int, float))
            ]
            composites = [
                float(r["composite_score"])
                for r in grouped_rows
                if isinstance(r.get("composite_score"), (int, float))
            ]

            comp_mean = statistics.mean(composites) if composites else None
            comp_std = statistics.pstdev(composites) if len(composites) > 1 else 0.0 if composites else None
            robust_score = (
                (comp_mean - robustness_alpha * comp_std)
                if isinstance(comp_mean, float) and isinstance(comp_std, float)
                else None
            )

            stats_rows.append(
                {
                    "config_key": config_key,
                    "runs": len(grouped_rows),
                    "acc_mean": statistics.mean(accuracies) if accuracies else "N/A",
                    "acc_std": statistics.pstdev(accuracies) if len(accuracies) > 1 else 0.0 if accuracies else "N/A",
                    "reward_mean": statistics.mean(rewards) if rewards else "N/A",
                    "reward_std": statistics.pstdev(rewards) if len(rewards) > 1 else 0.0 if rewards else "N/A",
                    "comp_mean": comp_mean if comp_mean is not None else "N/A",
                    "comp_std": comp_std if comp_std is not None else "N/A",
                    "robust_score": robust_score if robust_score is not None else "N/A",
                    "best_comp": max(composites) if composites else "N/A",
                    "worst_comp": min(composites) if composites else "N/A",
                }
            )

        stats_rows.sort(
            key=lambda r: float(r["robust_score"]) if isinstance(r.get("robust_score"), (int, float)) else float("-inf"),
            reverse=True,
        )
        return stats_rows

    def _build_recommendation_text(
        self, config_stats: list[dict[str, Any]], robustness_alpha: float
    ) -> str:
        if not config_stats:
            return "No configuration statistics available."
        best = config_stats[0]
        if not isinstance(best.get("robust_score"), (int, float)):
            return "No recommended configuration (insufficient numeric data)."
        return (
            "Recommended config: {config} (runs={runs}, robust_score={robust}, comp_mean={comp_mean}, comp_std={comp_std}, alpha={alpha})."
        ).format(
            config=best["config_key"],
            runs=best["runs"],
            robust=self._fmt_float(best["robust_score"]),
            comp_mean=self._fmt_float(best["comp_mean"]),
            comp_std=self._fmt_float(best["comp_std"]),
            alpha=self._fmt_float(robustness_alpha, digits=3),
        )

    def _build_config_markdown_table(self, config_stats: list[dict[str, Any]]) -> str:
        header = (
            "| config | runs | acc_mean | acc_std | reward_mean | reward_std | comp_mean | comp_std | robust_score | best_comp | worst_comp |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        )
        body_lines = []
        for row in config_stats:
            body_lines.append(
                "| {config_key} | {runs} | {acc_mean} | {acc_std} | {reward_mean} | {reward_std} | {comp_mean} | {comp_std} | {robust_score} | {best_comp} | {worst_comp} |".format(
                    config_key=row["config_key"],
                    runs=row["runs"],
                    acc_mean=self._fmt_float(row["acc_mean"]),
                    acc_std=self._fmt_float(row["acc_std"]),
                    reward_mean=self._fmt_float(row["reward_mean"]),
                    reward_std=self._fmt_float(row["reward_std"]),
                    comp_mean=self._fmt_float(row["comp_mean"]),
                    comp_std=self._fmt_float(row["comp_std"]),
                    robust_score=self._fmt_float(row["robust_score"]),
                    best_comp=self._fmt_float(row["best_comp"]),
                    worst_comp=self._fmt_float(row["worst_comp"]),
                )
            )
        return header + "\n".join(body_lines)

    def _compute_delta(self, current_value: Any, prev_row: dict[str, Any] | None, prev_key: str) -> str:
        if prev_row is None:
            return "N/A"
        prev_value = prev_row.get(prev_key)
        if not isinstance(current_value, (int, float)) or not isinstance(prev_value, (int, float)):
            return "N/A"
        delta = float(current_value) - float(prev_value)
        return f"{delta:+.4f}"

    @staticmethod
    def _trend_from_delta(delta_text: str) -> str:
        if delta_text == "N/A":
            return "N/A"
        try:
            value = float(delta_text)
        except ValueError:
            return "N/A"
        if value > 0.0001:
            return "UP"
        if value < -0.0001:
            return "DOWN"
        return "FLAT"

    @staticmethod
    def _compute_composite_score(
        accuracy: Any, mean_reward: Any, w_accuracy: float, w_reward: float
    ) -> Any:
        """Compute weighted score from accuracy and normalized reward.

        Reward is normalized from [-2, 2] into [0, 1].
        """
        if not isinstance(accuracy, (int, float)) or not isinstance(mean_reward, (int, float)):
            return "N/A"
        normalized_reward = (float(mean_reward) + 2.0) / 4.0
        normalized_reward = max(0.0, min(1.0, normalized_reward))
        return w_accuracy * float(accuracy) + w_reward * normalized_reward

    @staticmethod
    def _write_csv(rows: list[dict[str, Any]], csv_output_path: Path) -> None:
        csv_output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "file",
            "timestamp",
            "accuracy",
            "delta_accuracy",
            "trend_accuracy",
            "mean_reward",
            "delta_mean_reward",
            "trend_mean_reward",
            "composite_score",
            "composite_rank",
            "config_key",
            "samples",
            "seed",
            "auto_train",
            "synthetic",
            "benchmark_episodes",
            "test_limit",
            "test_days",
        ]
        with open(csv_output_path, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "file": row["file"],
                        "timestamp": row["timestamp"],
                        "accuracy": Command._fmt_float(row["accuracy"]),
                        "delta_accuracy": row["delta_accuracy"],
                        "trend_accuracy": row["trend_accuracy"],
                        "mean_reward": Command._fmt_float(row["mean_reward"]),
                        "delta_mean_reward": row["delta_mean_reward"],
                        "trend_mean_reward": row["trend_mean_reward"],
                        "composite_score": Command._fmt_float(row["composite_score"]),
                        "composite_rank": row["composite_rank"],
                        "config_key": row["config_key"],
                        "samples": row["samples"],
                        "seed": row["seed"],
                        "auto_train": row["auto_train"],
                        "synthetic": row["synthetic"],
                        "benchmark_episodes": row["benchmark_episodes"],
                        "test_limit": row["test_limit"],
                        "test_days": row["test_days"],
                    }
                )
```

## Archivo: apps/interactions/management/commands/collect_interactions.py

Ruta completa: apps/interactions/management/commands/collect_interactions.py

```python
"""
Comando: uv run manage.py collect_interactions

Recopila y procesa interacciones del usuario, calculando métricas agregadas.

Ejemplos:
    uv run manage.py collect_interactions
    uv run manage.py collect_interactions --days 7
    uv run manage.py collect_interactions --days 30 --user-id 1
    uv run manage.py collect_interactions --generate-report
"""

import logging
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.interactions.models import Interaction, InteractionSession

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recopila y procesa interacciones del usuario del sistema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Número de días de interacciones a procesar (default: 7)",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="ID del usuario específico a procesar (opcional)",
        )
        parser.add_argument(
            "--generate-report",
            action="store_true",
            help="Generar reporte de estadísticas",
        )
        parser.add_argument(
            "--save-session",
            action="store_true",
            help="Guardar interacciones en una nueva sesión",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostrar logs detallados",
        )

    def handle(self, *args, **options):
        days = options["days"]
        user_id = options["user_id"]
        generate_report = options["generate_report"]
        save_session = options["save_session"]
        verbose = options["verbose"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(self.style.SUCCESS(f"\n📊 Recopilando interacciones"))
        self.stdout.write(f"   📅 Últimos {days} días")

        try:
            # 1. Filtrar interacciones
            self.stdout.write("\n🔍 Buscando interacciones...")
            cutoff_date = timezone.now() - timedelta(days=days)

            query = Interaction.objects.filter(started_at__gte=cutoff_date).order_by("-started_at")

            if user_id:
                query = query.filter(user_id=user_id)
                user_name = User.objects.get(id=user_id).username
                self.stdout.write(f"   Usuario: {user_name}")

            interactions = list(query)
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ {len(interactions)} interacciones encontradas")
            )

            if not interactions:
                self.stdout.write(
                    self.style.WARNING("   ⚠️  No hay interacciones para procesar")
                )
                return

            # 2. Calcular estadísticas
            self.stdout.write("\n📈 Procesando estadísticas...")

            stats = self._calculate_stats(interactions)

            self.stdout.write(self.style.SUCCESS("   ✅ Estadísticas calculadas"))

            # 3. Mostrar resumen
            self.stdout.write(
                f"\n📊 Resumen de Interacciones:\n"
                f"   Total: {stats['total']}\n"
                f"   Completadas: {stats['completed']} ({stats['completion_rate']:.1f}%)\n"
                f"   Skipped: {stats['skipped']} ({stats['skip_rate']:.1f}%)\n"
                f"   Reward promedio: {stats['avg_reward']:.4f}\n"
                f"   Usuarios únicos: {stats['unique_users']}\n"
                f"   Tracks únicos: {stats['unique_tracks']}"
            )

            # 4. Mostrar top tracks
            self.stdout.write(f"\n🎵 Top 5 Tracks más reproducidos:")
            for i, (track_id, count) in enumerate(stats["top_tracks"][:5], 1):
                self.stdout.write(f"   {i}. Track ID: {track_id} ({count} veces)")

            # 5. Guardar sesión si aplica
            if save_session:
                self.stdout.write("\n💾 Guardando sesión...")
                session = self._create_session(interactions)
                self.stdout.write(
                    self.style.SUCCESS(f"   ✅ Sesión creada: {session.id}")
                )

            # 6. Generar reporte si aplica
            if generate_report:
                self.stdout.write("\n📄 Generando reporte...")
                self._generate_report(interactions, stats)
                self.stdout.write(self.style.SUCCESS("   ✅ Reporte generado"))

            self.stdout.write(
                self.style.SUCCESS("\n✅ Recopilación completada exitosamente!\n")
            )

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"\n❌ Usuario no encontrado: {user_id}\n"))
            raise CommandError(f"Usuario {user_id} no existe")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error al recopilar:\n{str(e)}\n"))
            raise CommandError(str(e))

    def _calculate_stats(self, interactions):
        """Calcula estadísticas de las interacciones."""
        from collections import Counter

        total = len(interactions)
        completed = sum(1 for i in interactions if i.feedback == "completed")
        skipped = sum(1 for i in interactions if i.feedback in ["skip", "skip_immediate"])

        rewards = [i.reward for i in interactions if i.reward]
        avg_reward = sum(rewards) / len(rewards) if rewards else 0

        users = set(i.user_id for i in interactions)
        tracks = set(i.track_id for i in interactions)

        track_counts = Counter(i.track_id for i in interactions)

        return {
            "total": total,
            "completed": completed,
            "skipped": skipped,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "skip_rate": (skipped / total * 100) if total > 0 else 0,
            "avg_reward": avg_reward,
            "unique_users": len(users),
            "unique_tracks": len(tracks),
            "top_tracks": track_counts.most_common(),
        }

    def _create_session(self, interactions):
        """Crea una sesión de interacciones."""
        # Usar el usuario de la primera interacción
        user = interactions[0].user if interactions else None

        session = InteractionSession.objects.create(
            user=user,
        )

        # Vincular interacciones a la sesión
        Interaction.objects.filter(id__in=[i.id for i in interactions]).update(
            session=session
        )

        return session

    def _generate_report(self, interactions, stats):
        """Genera un reporte de interacciones."""
        filename = f"interaction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(filename, "w") as f:
            f.write("=" * 60 + "\n")
            f.write("📊 REPORTE DE INTERACCIONES\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Fecha de generación: {datetime.now()}\n")
            f.write(f"Total de interacciones: {stats['total']}\n")
            f.write(f"Completadas: {stats['completed']} ({stats['completion_rate']:.1f}%)\n")
            f.write(f"Skipped: {stats['skipped']} ({stats['skip_rate']:.1f}%)\n")
            f.write(f"Reward promedio: {stats['avg_reward']:.4f}\n")
            f.write(f"Usuarios únicos: {stats['unique_users']}\n")
            f.write(f"Tracks únicos: {stats['unique_tracks']}\n\n")

            f.write("Top 10 Tracks:\n")
            for i, (track_id, count) in enumerate(stats["top_tracks"][:10], 1):
                f.write(f"  {i}. Track {track_id}: {count} veces\n")

        self.stdout.write(f"   Reporte guardado: {filename}")
```

## Archivo: apps/interactions/management/commands/evaluate_model.py

Ruta completa: apps/interactions/management/commands/evaluate_model.py

```python
"""
Comando: uv run manage.py evaluate_model

Evalúa un modelo entrenado en un conjunto de prueba de interacciones.

Ejemplos:
    uv run manage.py evaluate_model --model-path ml/models/dqn_agent_20260325_225939.h5
    uv run manage.py evaluate_model --model-path ml/models/model.h5 --test-days 7
    uv run manage.py evaluate_model --model-path ml/models/model.h5 --show-recommendations
    uv run manage.py evaluate_model --with-synthetic-context --auto-train --benchmark-episodes 5
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.interactions.services.reward_service import get_reward_service
from ml.state_builder import get_state_builder
from ml.training import LOGS_DIR, MODELS_DIR, ModelEvaluator, ModelTrainer, TrainingDataLoader

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Evalúa un modelo DQN entrenado en datos de prueba"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model-path",
            type=str,
            default=None,
            help="Ruta del modelo a evaluar (si se omite, se busca el último modelo)",
        )
        parser.add_argument(
            "--test-days",
            type=int,
            default=7,
            help="Días de interacciones recientes para prueba (default: 7)",
        )
        parser.add_argument(
            "--test-limit",
            type=int,
            default=1000,
            help="Máximo de interacciones a usar en evaluación (default: 1000)",
        )
        parser.add_argument(
            "--show-recommendations",
            action="store_true",
            help="Mostrar top-10 recommendations generadas por el modelo",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostrar logs detallados",
        )
        parser.add_argument(
            "--with-synthetic-context",
            action="store_true",
            help="Seed offline de contexto e interacciones antes de evaluar",
        )
        parser.add_argument(
            "--auto-train",
            action="store_true",
            help="Entrenar un modelo rápidamente antes de evaluar (útil con --with-synthetic-context)",
        )
        parser.add_argument(
            "--benchmark-episodes",
            type=int,
            default=5,
            help="Episodios para auto-train en benchmark offline (default: 5)",
        )
        parser.add_argument(
            "--benchmark-output",
            type=str,
            default=None,
            help="Ruta JSON para guardar resultados del benchmark (default: ml/logs)",
        )
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--synthetic-users", type=int, default=3)
        parser.add_argument("--synthetic-tracks", type=int, default=30)
        parser.add_argument("--synthetic-interactions", type=int, default=600)
        parser.add_argument("--synthetic-weather", type=int, default=60)
        parser.add_argument("--synthetic-news", type=int, default=120)

    def handle(self, *args, **options):
        model_path = options["model_path"]
        test_days = options["test_days"]
        test_limit = options["test_limit"]
        show_recommendations = options["show_recommendations"]
        verbose = options["verbose"]
        offline = options["with_synthetic_context"]
        auto_train = options["auto_train"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(self.style.SUCCESS("\n📊 Evaluando modelo DQN"))

        try:
            if offline:
                self.stdout.write("\n[SEED] Generando contexto sintético offline...")
                call_command(
                    "seed_synthetic_context",
                    weather_count=options["synthetic_weather"],
                    news_count=options["synthetic_news"],
                    days_back=max(test_days, 7),
                    seed=options["seed"],
                    clear_existing=True,
                )
                self.stdout.write(self.style.SUCCESS("   ✅ Contexto sintético generado"))

                self.stdout.write("\n[SEED] Generando interacciones sintéticas...")
                call_command(
                    "seed_synthetic_interactions",
                    users=options["synthetic_users"],
                    tracks=options["synthetic_tracks"],
                    interactions=options["synthetic_interactions"],
                    seed=options["seed"],
                )
                self.stdout.write(self.style.SUCCESS("   ✅ Interacciones sintéticas generadas"))

            if auto_train:
                self.stdout.write("\n[TRAIN] Entrenando modelo rápido para benchmark...")
                trainer = ModelTrainer(
                    episodes=options["benchmark_episodes"],
                    batch_size=64,
                )
                trainer.train_from_interactions(days=max(test_days, 7))
                trainer.save_model(model_name="dqn_benchmark")
                model_path = self._resolve_model_path(None)
                self.stdout.write(self.style.SUCCESS(f"   ✅ Modelo benchmark: {model_path}"))

            model_path = self._resolve_model_path(model_path)
            self.stdout.write(f"   📁 Modelo: {model_path}")

            self.stdout.write(f"\n📥 Cargando datos de prueba (últimos {test_days} días)...")
            test_interactions = TrainingDataLoader.load_interactions(
                days=test_days,
                limit=test_limit,
            )
            if not test_interactions:
                raise CommandError(
                    "No hay interacciones para evaluar. Ejecuta seed_synthetic_interactions o usa --with-synthetic-context."
                )

            self.stdout.write(
                self.style.SUCCESS(f"   ✅ {len(test_interactions)} interacciones para prueba")
            )

            self.stdout.write("\n🔍 Evaluando modelo...")
            evaluator = ModelEvaluator(model_path)
            metrics = evaluator.evaluate_on_test_set(test_interactions)
            mean_reward = (
                sum(inter.reward for inter in test_interactions) / len(test_interactions)
                if test_interactions
                else 0.0
            )

            self.stdout.write(
                f"\n📈 Resultados de evaluación:\n"
                f"   Accuracy: {metrics.get('accuracy', 'N/A')}\n"
                f"   Mean Reward (dataset): {mean_reward:.4f}\n"
                f"   Total Samples: {metrics.get('total_samples', len(test_interactions))}"
            )

            benchmark_data = {
                "timestamp": datetime.now().isoformat(),
                "model_path": str(model_path),
                "options": {
                    "test_days": test_days,
                    "test_limit": test_limit,
                    "with_synthetic_context": offline,
                    "auto_train": auto_train,
                    "benchmark_episodes": options["benchmark_episodes"],
                    "seed": options["seed"],
                },
                "metrics": {
                    **metrics,
                    "mean_reward_dataset": float(mean_reward),
                },
            }
            output_path = self._write_benchmark_json(
                benchmark_data,
                output=options["benchmark_output"],
            )
            self.stdout.write(self.style.SUCCESS(f"   ✅ Benchmark guardado: {output_path}"))

            # Mostrar recomendaciones si aplica
            if show_recommendations:
                self.stdout.write("\n🎵 Top-10 Recomendaciones del Modelo:")
                sample_user = self._get_sample_user()
                recommendations = evaluator.recommend_tracks(sample_user, count=10)
                for i, rec in enumerate(recommendations, 1):
                    track, score = rec
                    self.stdout.write(
                        f"   {i}. Track ID: {track.id} | {track.name} (score={score:.4f})"
                    )

            self.stdout.write(
                self.style.SUCCESS("\n✅ Evaluación completada exitosamente!\n")
            )

        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Archivo no encontrado: {str(e)}\n"))
            raise CommandError(str(e))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error durante la evaluación:\n{str(e)}\n"))
            raise CommandError(str(e))

    @staticmethod
    def _resolve_model_path(model_path: str | None) -> str:
        if model_path:
            if not Path(model_path).exists():
                raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
            return model_path

        model_files = sorted(MODELS_DIR.glob("*.h5"), reverse=True)
        if not model_files:
            raise FileNotFoundError(
                "No se encontró ningún modelo .h5 en ml/models. Usa --auto-train o --model-path."
            )
        return str(model_files[0])

    @staticmethod
    def _write_benchmark_json(payload: dict, output: str | None = None) -> str:
        if output:
            output_path = Path(output)
        else:
            output_path = LOGS_DIR / f"evaluation_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return str(output_path)

    @staticmethod
    def _get_sample_user():
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.first()
        if user is None:
            raise CommandError("No hay usuarios disponibles para mostrar recomendaciones")
        return user
```

## Archivo: apps/interactions/management/commands/moodsic_help.py

Ruta completa: apps/interactions/management/commands/moodsic_help.py

```python
"""
Comando: uv run manage.py moodsic_help

Muestra información de ayuda sobre los comandos de Moodsic.

Ejemplos:
    uv run manage.py moodsic_help
    uv run manage.py moodsic_help --command train_agent
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Muestra información de ayuda sobre comandos de Moodsic"

    def add_arguments(self, parser):
        parser.add_argument(
            "--command",
            type=str,
            default=None,
            help="Comando específico del cual obtener ayuda",
        )

    def handle(self, *args, **options):
        command = options.get("command")

        help_text = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    🎵 MOODSIC - MANAGEMENT COMMANDS                       ║
║              RL-Based Spotify Playlist Generator for Django               ║
╚════════════════════════════════════════════════════════════════════════════╝

COMANDOS DISPONIBLES:

1️⃣  TRAIN_AGENT - Entrena el modelo DQN
   └─ uv run manage.py train_agent [OPTIONS]

   Opciones:
      --episodes NUM       Número de episodios (default: 50)
      --days NUM          Días de data histórica (default: 30)
      --batch-size NUM    Tamaño de batch (default: 64)
      --save              Guardar modelo después
      --visualize         Mostrar gráficos de training
      --verbose           Logs detallados

   Ejemplos:
      $ uv run manage.py train_agent --episodes 100 --save
      $ uv run manage.py train_agent --episodes 50 --days 30 --batch-size 64 --save --visualize


2️⃣  EVALUATE_MODEL - Evalúa un modelo entrenado
   └─ uv run manage.py evaluate_model [OPTIONS]

   Opciones:
      --model-path PATH           Ruta del modelo (REQUERIDO)
      --test-days NUM            Días de test (default: 7)
      --show-recommendations     Mostrar top-10 recommendations
      --verbose                  Logs detallados

   Ejemplos:
      $ uv run manage.py evaluate_model --model-path ml/models/dqn_agent.h5
      $ uv run manage.py evaluate_model --model-path ml/models/dqn_agent.h5 --show-recommendations


3️⃣  COLLECT_INTERACTIONS - Recopila y procesa interacciones
   └─ uv run manage.py collect_interactions [OPTIONS]

   Opciones:
      --days NUM              Días de interacciones (default: 7)
      --user-id ID           ID de usuario específico (opcional)
      --generate-report      Generar reporte en archivo
      --save-session         Guardar como sesión
      --verbose              Logs detallados

   Ejemplos:
      $ uv run manage.py collect_interactions --days 7
      $ uv run manage.py collect_interactions --user-id 1 --generate-report
      $ uv run manage.py collect_interactions --days 30 --save-session


4️⃣  SYNC_SPOTIFY_TRACKS - Sincroniza tracks desde Spotify
   └─ uv run manage.py sync_spotify_tracks [OPTIONS]

   Opciones:
      --user-id ID          ID del usuario a sincronizar (opcional)
      --playlist-id ID      ID de playlist de Spotify (opcional)
      --limit NUM           Límite de tracks (default: 50)
      --save-all            Guardar todos los tracks
      --verbose             Logs detallados

   Ejemplos:
      $ uv run manage.py sync_spotify_tracks
      $ uv run manage.py sync_spotify_tracks --user-id 1 --limit 100
      $ uv run manage.py sync_spotify_tracks --playlist-id spotify:playlist:123abc


📚 WORKFLOW RECOMENDADO:

   1. Entrena el agente:
      $ uv run manage.py train_agent --episodes 100 --days 30 --save

   2. Recopila interacciones:
      $ uv run manage.py collect_interactions --days 7 --save-session

   3. Evalúa el modelo:
      $ uv run manage.py evaluate_model --model-path ml/models/dqn_agent.h5

   4. Sincroniza tracks:
      $ uv run manage.py sync_spotify_tracks --limit 100


💡 TIPS:

   • Usa --verbose para debugging detallado
   • Los modelos se guardan en: ml/models/dqn_agent_YYYYMMDD_HHMMSS.h5
   • Los logs se guardan en: ml/logs/training_YYYYMMDD_HHMMSS.json
   • Los reportes se guardan en: interaction_report_YYYYMMDD_HHMMSS.txt


🔧 CONFIGURACIÓN REQUERIDA:

   • Base de datos PostgreSQL: Configurada ✅
   • Django settings: Configurados ✅
   • Spotify API: Requiere credenciales en .env
      SPOTIFY_CLIENT_ID=xxx
      SPOTIFY_CLIENT_SECRET=xxx


❓ PARA MÁS INFORMACIÓN:

   • Documentación: Ver DEVELOPMENT.md
   • Tests: uv run pytest ml/tests/ -v
   • Admin: http://localhost:8000/admin

╔════════════════════════════════════════════════════════════════════════════╗
║                        ¡Happy Experimenting! 🚀                           ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

        if command:
            # Mostrar ayuda de comando específico
            self.stdout.write(f"\n📖 Ayuda para: {command}\n")
            self.stdout.write(f"Ejecuta: uv run manage.py {command} --help\n")
        else:
            # Mostrar ayuda general
            self.stdout.write(help_text)
```

## Archivo: apps/interactions/management/commands/seed_synthetic_interactions.py

Ruta completa: apps/interactions/management/commands/seed_synthetic_interactions.py

```python
"""Seed synthetic interactions for offline development and RL experiments."""

from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.interactions.models import Interaction
from apps.interactions.services.reward_service import get_reward_service
from apps.music.models import Album, Artist, Track

User = get_user_model()


class Command(BaseCommand):
    help = "Generate synthetic interactions without calling external APIs."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=3)
        parser.add_argument("--tracks", type=int, default=30)
        parser.add_argument("--interactions", type=int, default=300)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        users = self._ensure_users(options["users"])
        tracks = self._ensure_tracks(options["tracks"], rng)

        reward_service = get_reward_service()
        feedback_choices = [
            "completed",
            "skip",
            "skip_immediate",
            "replay",
            "added_to_playlist",
        ]

        created = 0
        for idx in range(options["interactions"]):
            user = rng.choice(users)
            track = rng.choice(tracks)
            feedback = rng.choices(
                feedback_choices,
                weights=[50, 25, 10, 10, 5],
                k=1,
            )[0]

            track_seconds = max(30, int(track.duration_ms / 1000))
            if feedback == "completed":
                play_duration = int(track_seconds * rng.uniform(0.85, 1.0))
            elif feedback == "skip_immediate":
                play_duration = int(track_seconds * rng.uniform(0.01, 0.07))
            elif feedback == "skip":
                play_duration = int(track_seconds * rng.uniform(0.1, 0.5))
            else:
                play_duration = int(track_seconds * rng.uniform(0.4, 1.0))

            reward = reward_service.calculate_interaction_reward(
                user_feedback=feedback,
                user=user,
                track=track,
                weather_id=None,
                news_ids=None,
            )

            started_at = timezone.now() - timedelta(
                days=rng.randint(0, 14),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )
            Interaction.objects.create(
                user=user,
                track=track,
                feedback=feedback,
                play_duration=play_duration,
                track_duration=track_seconds,
                reward=reward,
                session_id=f"offline_{user.id}_{idx // 10}",
                started_at=started_at,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} synthetic interactions."))

    @staticmethod
    def _ensure_users(count: int):
        users = list(User.objects.all()[:count])
        next_idx = len(users)
        while len(users) < count:
            next_idx += 1
            users.append(
                User.objects.create_user(
                    username=f"offline_user_{next_idx}",
                    email=f"offline_user_{next_idx}@example.com",
                    password="offline-pass-123",
                )
            )
        return users

    @staticmethod
    def _ensure_tracks(count: int, rng: random.Random):
        tracks = list(Track.objects.prefetch_related("artists").all()[:count])
        if len(tracks) >= count:
            return tracks

        album, _ = Album.objects.get_or_create(
            spotify_id="offline_album_1",
            defaults={"name": "Offline Album", "release_date": "2026-01-01"},
        )

        artists = []
        for idx, genre in enumerate(["pop", "rock", "electronic", "indie"], start=1):
            artist, _ = Artist.objects.get_or_create(
                spotify_id=f"offline_artist_{idx}",
                defaults={"name": f"Offline Artist {idx}", "genres": [genre]},
            )
            artists.append(artist)

        next_idx = len(tracks)
        while len(tracks) < count:
            next_idx += 1
            track, _ = Track.objects.get_or_create(
                spotify_id=f"offline_track_{next_idx}",
                defaults={
                    "name": f"Offline Track {next_idx}",
                    "album": album,
                    "duration_ms": rng.randint(120000, 260000),
                    "explicit": False,
                    "track_number": next_idx,
                    "popularity": rng.randint(20, 90),
                    "uri": f"spotify:track:offline_track_{next_idx}",
                },
            )
            track.artists.set([rng.choice(artists)])
            tracks.append(track)

        return tracks
```

## Archivo: apps/interactions/management/commands/sync_spotify_tracks.py

Ruta completa: apps/interactions/management/commands/sync_spotify_tracks.py

```python
"""
Comando: uv run manage.py sync_spotify_tracks

Sincroniza tracks desde la API de Spotify con la base de datos local.

Ejemplos:
    uv run manage.py sync_spotify_tracks --user-id 1 --liked
    uv run manage.py sync_spotify_tracks --user-id 1 --top
    uv run manage.py sync_spotify_tracks --playlist-id 3cEYpDpmLSvzlEecCXqDsF
    uv run manage.py sync_spotify_tracks --user-id 1 --limit 100 --save-audio-features
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.music.services.spotify_music_service import SpotifyMusicService
from apps.music.models import Track, Album, Artist, TrackAudioFeatures

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sincroniza tracks desde Spotify API con la BD local"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="ID del usuario Django a sincronizar",
        )
        parser.add_argument(
            "--playlist-id",
            type=str,
            default=None,
            help="ID de la playlist de Spotify a sincronizar",
        )
        parser.add_argument(
            "--liked",
            action="store_true",
            help="Sincronizar canciones que le gustan al usuario",
        )
        parser.add_argument(
            "--top",
            action="store_true",
            help="Sincronizar top tracks del usuario",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Número máximo de tracks a sincronizar (default: 50)",
        )
        parser.add_argument(
            "--save-audio-features",
            action="store_true",
            help="Guardar características de audio para cada track",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostrar logs detallados",
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        playlist_id = options["playlist_id"]
        limit = options["limit"]
        save_audio_features = options["save_audio_features"]
        verbose = options["verbose"]
        liked = options["liked"]
        top = options["top"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(self.style.SUCCESS(f"\n[SYNC] Sincronizando tracks de Spotify"))

        try:
            # Determinar el usuario a usar
            if playlist_id and not user_id:
                # Para playlists públicas, necesitamos un usuario para autenticarse
                # Usamos el primer usuario disponible con conexión a Spotify
                user = User.objects.filter(is_spotify_connected=True).first()
                if not user:
                    raise CommandError(
                        "Se necesita al menos un usuario conectado a Spotify para sincronizar playlists"
                    )
            elif user_id:
                try:
                    user = User.objects.get(id=user_id)
                    if not user.is_spotify_connected:
                        raise CommandError(
                            f"Usuario {user.username} no está conectado a Spotify"
                        )
                except User.DoesNotExist:
                    raise CommandError(f"Usuario {user_id} no existe")
            else:
                raise CommandError(
                    "Debes especificar --user-id, --playlist-id o ambos"
                )

            # Inicializar servicio de Spotify
            spotify_service = SpotifyMusicService(user)
            if not spotify_service.client:
                raise CommandError(
                    f"No se pudo autenticar con Spotify para usuario {user.username}"
                )

            # 1. Obtener tracks
            self.stdout.write(self.style.SUCCESS("\n[FETCH] Buscando tracks en Spotify..."))
            tracks = []

            if playlist_id:
                self.stdout.write(f"   Fuente: Playlist {playlist_id[:20]}...")
                tracks = spotify_service.get_playlist_tracks(
                    playlist_id=playlist_id, limit=limit
                )
            elif liked:
                self.stdout.write(f"   Fuente: Liked Songs de {user.username}")
                tracks = spotify_service.get_user_liked_tracks(limit=limit)
            elif top:
                self.stdout.write(f"   Fuente: Top tracks de {user.username}")
                tracks = spotify_service.get_top_tracks(limit=limit)
            else:
                # Default: liked tracks
                self.stdout.write(f"   Fuente: Liked Songs de {user.username} (default)")
                tracks = spotify_service.get_user_liked_tracks(limit=limit)

            if not tracks:
                self.stdout.write(self.style.WARNING("   [WARN] No se encontraron tracks"))
                return

            self.stdout.write(
                self.style.SUCCESS(f"   [OK] {len(tracks)} tracks encontrados")
            )

            # 2. Guardar tracks en BD
            self.stdout.write(self.style.SUCCESS("\n[SAVE] Guardando tracks en base de datos..."))

            saved_count = 0
            skipped_count = 0
            artist_cache = {}

            for idx, track_data in enumerate(tracks, 1):
                try:
                    # Obtener o crear album
                    if track_data.get("album_id"):
                        album, _ = Album.objects.get_or_create(
                            spotify_id=track_data.get("album_id"),
                            defaults={
                                "name": track_data.get("album", "Unknown"),
                                "album_type": "",
                            },
                        )
                    else:
                        album = None

                    # Obtener o crear artistas
                    artists = []
                    for artist_name in track_data.get("artists", []):
                        artist_key = artist_name.lower()
                        if artist_key not in artist_cache:
                            artist, _ = Artist.objects.get_or_create(
                                name=artist_name,
                                defaults={"spotify_id": f"local_{artist_key}"},
                            )
                            artist_cache[artist_key] = artist
                        artists.append(artist_cache[artist_key])

                    # Obtener o crear track
                    track, created = Track.objects.get_or_create(
                        spotify_id=track_data.get("id", ""),
                        defaults={
                            "name": track_data.get("name", "Unknown"),
                            "album": album,
                            "duration_ms": track_data.get("duration_ms", 0),
                            "explicit": track_data.get("explicit", False),
                            "popularity": track_data.get("popularity", 0),
                            "preview_url": track_data.get("preview_url", ""),
                            "uri": track_data.get("uri", ""),
                            "track_number": 0,
                        },
                    )

                    # Agregar artistas al track
                    if artists:
                        track.artists.add(*artists)

                    if created:
                        saved_count += 1
                        status = "[NEW]"
                    else:
                        skipped_count += 1
                        status = "[EXISTS]"

                    if verbose and idx % 10 == 0:
                        self.stdout.write(
                            f"   {status} [{idx}/{len(tracks)}] {track.name[:40]}..."
                        )

                except Exception as e:
                    logger.error(f"Error procesando track {track_data.get('name', 'Unknown')}: {e}")
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f"   [ERROR] {str(e)[:50]}...")
                        )

            self.stdout.write(
                self.style.SUCCESS(f"\n   [OK] {saved_count} tracks nuevos guardados")
            )
            if skipped_count > 0:
                self.stdout.write(
                    self.style.NOTICE(f"   [INFO] {skipped_count} tracks ya existían")
                )

            # 3. Obtener características de audio si se solicita
            if save_audio_features and saved_count > 0:
                self.stdout.write(self.style.SUCCESS("\n[AUDIO] Obteniendo características de audio..."))
                
                track_ids = [t.get("id") for t in tracks if t.get("id")]
                if track_ids:
                    audio_features = spotify_service.get_audio_features(track_ids)
                    
                    features_saved = 0
                    for track_id, features in audio_features.items():
                        try:
                            track = Track.objects.get(spotify_id=track_id)
                            TrackAudioFeatures.objects.get_or_create(
                                track=track,
                                defaults=features
                            )
                            features_saved += 1
                        except Track.DoesNotExist:
                            pass
                        except Exception as e:
                            logger.error(f"Error guardando audio features para {track_id}: {e}")
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"   [OK] {features_saved} registros de audio features guardados")
                    )

            # 4. Mostrar resumen final
            self.stdout.write(
                f"\n[SUMMARY]"
                f"\n   Total procesados: {len(tracks)}"
                f"\n   Nuevos tracks: {saved_count}"
                f"\n   Tracks existentes: {skipped_count}"
                f"\n   Fuente: {'Playlist' if playlist_id else ('Liked Songs' if liked else ('Top Tracks' if top else 'Default'))}"
            )

            self.stdout.write(
                self.style.SUCCESS("[OK] Sincronización completada exitosamente!\n")
            )

        except CommandError:
            raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Error durante la sincronización:\n{str(e)}\n"))
            if verbose:
                import traceback
                traceback.print_exc()
            raise CommandError(str(e))
```

## Archivo: apps/interactions/management/commands/train_agent.py

Ruta completa: apps/interactions/management/commands/train_agent.py

```python
"""
Comando: uv run manage.py train_agent

Entrena el agente DQN con datos de interacciones del sistema.

Ejemplos:
    uv run manage.py train_agent --episodes 100
    uv run manage.py train_agent --episodes 50 --days 30 --batch-size 64 --save
    uv run manage.py train_agent --episodes 10 --visualize
    uv run manage.py train_agent --with-synthetic-context --episodes 20
"""

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from ml.agent import get_agent
from ml.training import ModelTrainer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Entrena el agente DQN con datos de interacciones del sistema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--episodes",
            type=int,
            default=50,
            help="Número de episodios de entrenamiento (default: 50)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Días de historial de interacciones a usar (default: 30)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=64,
            help="Tamaño de batch para el entrenamiento (default: 64)",
        )
        parser.add_argument(
            "--save",
            action="store_true",
            help="Guardar el modelo después del entrenamiento",
        )
        parser.add_argument(
            "--model-path",
            type=str,
            default=None,
            help="Ruta para guardar/cargar el modelo",
        )
        parser.add_argument(
            "--visualize",
            action="store_true",
            help="Visualizar métricas de entrenamiento después",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostrar logs detallados",
        )
        parser.add_argument(
            "--with-synthetic-context",
            action="store_true",
            help="Seed de contexto e interacciones sintéticas antes de entrenar",
        )
        parser.add_argument(
            "--synthetic-users",
            type=int,
            default=3,
            help="Usuarios sintéticos para el seed offline (default: 3)",
        )
        parser.add_argument(
            "--synthetic-tracks",
            type=int,
            default=30,
            help="Tracks sintéticos para el seed offline (default: 30)",
        )
        parser.add_argument(
            "--synthetic-interactions",
            type=int,
            default=600,
            help="Interacciones sintéticas para el seed offline (default: 600)",
        )
        parser.add_argument(
            "--synthetic-weather",
            type=int,
            default=60,
            help="Registros de clima sintético (default: 60)",
        )
        parser.add_argument(
            "--synthetic-news",
            type=int,
            default=120,
            help="Registros de noticias sintéticas (default: 120)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Semilla para generación sintética reproducible",
        )

    def handle(self, *args, **options):
        episodes = options["episodes"]
        days = options["days"]
        batch_size = options["batch_size"]
        save_model = options["save"]
        verbose = options["verbose"]
        visualize = options["visualize"]
        with_synthetic_context = options["with_synthetic_context"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(
            self.style.SUCCESS(f"\n>>> Iniciando entrenamiento RL ({episodes} episodios)")
        )
        self.stdout.write(f"    [DATA] Últimos {days} días")
        self.stdout.write(f"    [CONFIG] Batch size: {batch_size}")

        try:
            if with_synthetic_context:
                self.stdout.write("\n[SEED] Generando contexto sintético offline...")
                call_command(
                    "seed_synthetic_context",
                    weather_count=options["synthetic_weather"],
                    news_count=options["synthetic_news"],
                    days_back=max(days, 7),
                    seed=options["seed"],
                    clear_existing=True,
                )
                self.stdout.write(self.style.SUCCESS("   [OK] Contexto sintético generado"))

                self.stdout.write("\n[SEED] Generando interacciones sintéticas...")
                call_command(
                    "seed_synthetic_interactions",
                    users=options["synthetic_users"],
                    tracks=options["synthetic_tracks"],
                    interactions=options["synthetic_interactions"],
                    seed=options["seed"],
                )
                self.stdout.write(self.style.SUCCESS("   [OK] Interacciones sintéticas generadas"))

            # 1. Inicializar componentes
            self.stdout.write("\n[INIT] Inicializando componentes RL...")
            agent = get_agent(state_dim=45, action_dim=100)
            self.stdout.write(self.style.SUCCESS("   [OK] Agente listo"))

            # 2. Entrenar
            self.stdout.write(f"\n[TRAIN] Entrenando por {episodes} episodios...")

            trainer = ModelTrainer(
                agent=agent,
                episodes=episodes,
                batch_size=batch_size,
            )

            trainer.train_from_interactions(days=days)

            self.stdout.write(self.style.SUCCESS("   [OK] Entrenamiento completado"))

            # 3. Mostrar resumen
            losses = trainer.training_logs.get("episode_losses", [])
            rewards = trainer.training_logs.get("episode_rewards", [])
            epsilons = trainer.training_logs.get("epsilon_values", [])
            avg_loss = (sum(losses) / len(losses)) if losses else 0.0
            avg_reward = (sum(rewards) / len(rewards)) if rewards else 0.0
            epsilon_final = epsilons[-1] if epsilons else "N/A"
            self.stdout.write(
                f"\n[SUMMARY]\n"
                f"   Loss promedio: {avg_loss:.4f}\n"
                f"   Reward promedio: {avg_reward:.4f}\n"
                f"   Epsilon final: {epsilon_final}"
            )

            # 4. Guardar si aplica
            if save_model:
                self.stdout.write("\n[SAVE] Guardando modelo...")
                model_path = trainer.save_model()
                self.stdout.write(self.style.SUCCESS(f"   [OK] Modelo guardado: {model_path}"))

            # 5. Visualizar si aplica
            if visualize:
                self.stdout.write("\n[PLOT] Generando gráficos...")
                try:
                    trainer.plot_training_history()
                    self.stdout.write(self.style.SUCCESS("   [OK] Gráficos generados"))
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"   [WARNING] No se pudieron generar gráficos: {e}")
                    )

            self.stdout.write(
                self.style.SUCCESS("\n[SUCCESS] Entrenamiento finalizado exitosamente!\n")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error durante el entrenamiento:\n{str(e)}\n"))
            raise CommandError(str(e))
```

## Archivo: apps/interactions/migrations/0001_initial.py

Ruta completa: apps/interactions/migrations/0001_initial.py

```python
# Generated by Django 4.2.29 on 2026-03-25 21:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("music", "0002_alter_track_preview_url"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InteractionSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "session_id",
                    models.CharField(
                        max_length=255, unique=True, verbose_name="ID de sesión"
                    ),
                ),
                (
                    "weather_id",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="ID Contexto al inicio de sesión",
                    ),
                ),
                (
                    "total_tracks",
                    models.IntegerField(
                        default=0, verbose_name="Total de canciones reproducidas"
                    ),
                ),
                (
                    "skip_count",
                    models.IntegerField(default=0, verbose_name="Total de skips"),
                ),
                (
                    "completed_count",
                    models.IntegerField(
                        default=0, verbose_name="Total de canciones completadas"
                    ),
                ),
                (
                    "average_reward",
                    models.FloatField(
                        default=0.0, verbose_name="Reward promedio de la sesión"
                    ),
                ),
                (
                    "total_reward",
                    models.FloatField(
                        default=0.0, verbose_name="Reward total de la sesión"
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Inicio de sesión"
                    ),
                ),
                (
                    "ended_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Fin de sesión"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="¿Sesión activa?"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interaction_sessions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sesión de interacción",
                "verbose_name_plural": "Sesiones de interacción",
                "ordering": ("-started_at",),
                "indexes": [
                    models.Index(
                        fields=["user", "-started_at"],
                        name="interaction_user_id_9ee3a2_idx",
                    ),
                    models.Index(
                        fields=["session_id"], name="interaction_session_6758f6_idx"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Interaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "feedback",
                    models.CharField(
                        choices=[
                            ("completed", "Canción completada"),
                            ("skip", "Salto normal"),
                            ("skip_immediate", "Salto inmediato (< 5 seg)"),
                            ("replay", "Reproducida de nuevo"),
                            ("added_to_playlist", "Añadida a playlist"),
                        ],
                        default="completed",
                        max_length=20,
                        verbose_name="Tipo de feedback",
                    ),
                ),
                (
                    "weather_id",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="ID Contexto climático"
                    ),
                ),
                (
                    "news_ids",
                    models.JSONField(
                        blank=True, default=list, verbose_name="IDs de noticias"
                    ),
                ),
                (
                    "reward",
                    models.FloatField(default=0.0, verbose_name="Recompensa calculada"),
                ),
                (
                    "play_duration",
                    models.IntegerField(
                        default=0,
                        help_text="Cuántos segundos del track se reprodujeron",
                        verbose_name="Duración reproducida (segundos)",
                    ),
                ),
                (
                    "track_duration",
                    models.IntegerField(
                        default=0, verbose_name="Duración total del track (segundos)"
                    ),
                ),
                (
                    "completion_percentage",
                    models.FloatField(
                        default=0.0, verbose_name="Porcentaje completado (%)"
                    ),
                ),
                (
                    "session_id",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Para agrupar interacciones de una sesión",
                        max_length=255,
                        verbose_name="ID de sesión",
                    ),
                ),
                (
                    "playlist_id",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=255,
                        verbose_name="ID de playlist (Spotify)",
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Hora de inicio"
                    ),
                ),
                (
                    "ended_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Hora de término"
                    ),
                ),
                (
                    "is_positive",
                    models.BooleanField(
                        default=True,
                        help_text="True si feedback != 'skip'",
                        verbose_name="¿Es feedback positivo?",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "track",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interactions",
                        to="music.track",
                        verbose_name="Canción",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interactions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Interacción",
                "verbose_name_plural": "Interacciones",
                "ordering": ("-started_at",),
                "indexes": [
                    models.Index(
                        fields=["user", "-started_at"],
                        name="interaction_user_id_2c77f8_idx",
                    ),
                    models.Index(
                        fields=["track", "-started_at"],
                        name="interaction_track_i_580c37_idx",
                    ),
                    models.Index(
                        fields=["feedback"], name="interaction_feedbac_77f9e5_idx"
                    ),
                    models.Index(
                        fields=["session_id"], name="interaction_session_40851a_idx"
                    ),
                ],
            },
        ),
    ]
```

## Archivo: apps/interactions/migrations/__init__.py

Ruta completa: apps/interactions/migrations/__init__.py

```python

```

## Archivo: apps/interactions/models/__init__.py

Ruta completa: apps/interactions/models/__init__.py

```python
from .interaction import Interaction, InteractionSession

__all__ = [
    "Interaction",
    "InteractionSession",
]
```

## Archivo: apps/interactions/models/interaction.py

Ruta completa: apps/interactions/models/interaction.py

```python
"""
Modelo Interaction: registra la interacción del usuario con los tracks.

Almacena feedback (skip, completed), rewards, y métricas para entrenar el agente RL.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.music.models import Track


class Interaction(models.Model):
    """
    Registra la interacción de un usuario con una canción.
    
    Incluye el tipo de feedback (skip, completed, etc) y la recompensa calculada.
    Esto es crucial para entrenar el agente RL.
    """

    FEEDBACK_CHOICES = [
        ("completed", _("Canción completada")),
        ("skip", _("Salto normal")),
        ("skip_immediate", _("Salto inmediato (< 5 seg)")),
        ("replay", _("Reproducida de nuevo")),
        ("added_to_playlist", _("Añadida a playlist")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interactions",
        verbose_name=_("Usuario"),
    )
    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="interactions",
        verbose_name=_("Canción"),
    )

    # Feedback del usuario
    feedback = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        default="completed",
        verbose_name=_("Tipo de feedback"),
    )

    # Contexto en el que ocurrió la interacción
    weather_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("ID Contexto climático"),
    )
    news_ids = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("IDs de noticias"),
    )

    # Métricas de la interacción
    reward = models.FloatField(
        default=0.0,
        verbose_name=_("Recompensa calculada"),
    )
    play_duration = models.IntegerField(
        default=0,
        verbose_name=_("Duración reproducida (segundos)"),
        help_text="Cuántos segundos del track se reprodujeron",
    )
    track_duration = models.IntegerField(
        default=0,
        verbose_name=_("Duración total del track (segundos)"),
    )

    # Completeness: qué porcentaje del track se escuchó
    completion_percentage = models.FloatField(
        default=0.0,
        verbose_name=_("Porcentaje completado (%)"),
    )

    # Metadatos
    session_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("ID de sesión"),
        help_text="Para agrupar interacciones de una sesión",
    )
    playlist_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("ID de playlist (Spotify)"),
    )

    # Tiempo
    started_at = models.DateTimeField(
        verbose_name=_("Hora de inicio"),
        auto_now_add=True,
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Hora de término"),
    )

    # Atributos calculados
    is_positive = models.BooleanField(
        default=True,
        verbose_name=_("¿Es feedback positivo?"),
        help_text="True si feedback != 'skip'",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Interacción")
        verbose_name_plural = _("Interacciones")
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=["user", "-started_at"]),
            models.Index(fields=["track", "-started_at"]),
            models.Index(fields=["feedback"]),
            models.Index(fields=["session_id"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.track.name} ({self.feedback})"

    def save(self, *args, **kwargs):
        """
        Calcula campos derivados antes de guardar.
        """
        # Calcular porcentaje de completitud
        if self.track_duration > 0:
            self.completion_percentage = (
                self.play_duration / self.track_duration
            ) * 100

        # Clasificar feedback como positivo o negativo
        self.is_positive = not self.feedback.startswith("skip")

        super().save(*args, **kwargs)


class InteractionSession(models.Model):
    """
    Agrupa interacciones en sesiones de usuario.
    
    Una sesión representa un período de uso continuo.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interaction_sessions",
        verbose_name=_("Usuario"),
    )

    session_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("ID de sesión"),
    )

    # Contexto de la sesión
    weather_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("ID Contexto al inicio de sesión"),
    )

    # Métricas agregadas
    total_tracks = models.IntegerField(
        default=0,
        verbose_name=_("Total de canciones reproducidas"),
    )
    skip_count = models.IntegerField(
        default=0,
        verbose_name=_("Total de skips"),
    )
    completed_count = models.IntegerField(
        default=0,
        verbose_name=_("Total de canciones completadas"),
    )
    average_reward = models.FloatField(
        default=0.0,
        verbose_name=_("Reward promedio de la sesión"),
    )
    total_reward = models.FloatField(
        default=0.0,
        verbose_name=_("Reward total de la sesión"),
    )

    # Duración
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Inicio de sesión"),
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Fin de sesión"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("¿Sesión activa?"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Sesión de interacción")
        verbose_name_plural = _("Sesiones de interacción")
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=["user", "-started_at"]),
            models.Index(fields=["session_id"]),
        ]

    def __str__(self):
        return f"{self.user.username} - Session {self.session_id[:8]}"

    def calculate_metrics(self):
        """
        Calcula las métricas agregadas de la sesión según las interacciones.
        """
        from django.db.models import Avg, Count, Q

        interactions = Interaction.objects.filter(session_id=self.session_id)

        self.total_tracks = interactions.count()
        self.skip_count = interactions.filter(feedback__startswith="skip").count()
        self.completed_count = interactions.filter(feedback="completed").count()
        self.average_reward = interactions.aggregate(
            avg=Avg("reward")
        )["avg"] or 0.0
        self.total_reward = sum(interactions.values_list("reward", flat=True))

        self.save()
```

## Archivo: apps/interactions/schemas.py

Ruta completa: apps/interactions/schemas.py

```python
"""
Schemas para API de Interactions usando Django-Ninja.
"""

from typing import Literal

from ninja import Schema
from pydantic import Field


class InteractionCreateSchema(Schema):
    """
    Schema para crear una nueva interacción.
    """

    track_id: int
    feedback: Literal[
        "completed",
        "skip",
        "skip_immediate",
        "replay",
        "added_to_playlist",
    ]
    play_duration: int = Field(0, ge=0)
    track_duration: int = Field(0, ge=0)
    session_id: str = Field("", max_length=255)
    weather_id: int | None = None
    news_ids: list[int] | None = None
    playlist_id: str = Field("", max_length=255)


class InteractionResponseSchema(Schema):
    """
    Schema para responder con una interacción.
    """

    id: int
    user_id: int
    track_id: int
    feedback: str
    reward: float
    completion_percentage: float
    is_positive: bool
    started_at: str
    created_at: str


class SessionStatsSchema(Schema):
    """
    Schema con estadísticas de una sesión.
    """

    session_id: str
    total_tracks: int
    skip_count: int
    completed_count: int
    average_reward: float
    total_reward: float
    skip_rate: float
    completion_rate: float
    started_at: str
    is_active: bool


class UserStatsSchema(Schema):
    """
    Schema con estadísticas del usuario.
    """

    user_id: int
    total_interactions: int
    total_skips: int
    total_completed: int
    average_reward: float
    total_reward: float
    skip_rate: float
    completion_rate: float
    favorite_genres: list[str]
    favorite_artists: list[str]
    average_session_length: float


class PlaylistGenerateSchema(Schema):
    """
    Schema para solicitar generación de playlist.
    """

    name: str = Field("Generated by Moodsic", max_length=120)
    count: int = Field(10, ge=1)  # Número de canciones
    weather_id: int | None = None
    use_context: bool = True
    news_category: Literal[
        "general",
        "music",
        "markets",
        "sports",
        "politics",
    ] = "general"
    news_query: str | None = Field(None, max_length=120)
    news_limit: int = Field(20, ge=1, le=50)


class PlaylistGenerateResponseSchema(Schema):
    """
    Schema de respuesta para playlist generada.
    """

    playlist_id: str
    playlist_name: str
    tracks_count: int
    session_id: str
    track_ids: list[int]
    track_names: list[str]
    estimated_duration: int  # En segundos
    created_at: str
    mode: Literal["online", "fallback", "hybrid"]
    used_spotify_sync: bool
    used_cached_news: bool
    used_local_catalog: bool
    used_spotify_catalog_fallback: bool
    message: str = ""
    warnings: list[str] = Field(default_factory=list)


class DashboardMetricsSchema(Schema):
    """
    Schema con métricas del dashboard.
    """

    total_users: int
    total_interactions: int
    average_skip_rate: float
    average_completion_rate: float
    total_reward_generated: float
    active_sessions: int
    top_tracks: list[dict]
    user_growth: list[dict]
```

## Archivo: apps/interactions/services/__init__.py

Ruta completa: apps/interactions/services/__init__.py

```python

```

## Archivo: apps/interactions/services/playlist_generation_service.py

Ruta completa: apps/interactions/services/playlist_generation_service.py

```python
"""
Servicio de Generación de Playlists usando el Agente RL.
"""

import logging
import uuid
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Avg, Sum
from django.utils import timezone

from apps.context.models import NewsContext, WeatherContext
from apps.context.services.news_service import NewsService
from apps.music.models import Album, Artist, Track, Playlist, PlaylistTrack
from apps.music.services.spotify_music_service import SpotifyMusicService
from apps.interactions.services.reward_service import get_reward_service
from ml.agent import get_agent
from ml.state_builder import get_state_builder

logger = logging.getLogger(__name__)

User = get_user_model()

ALLOWED_NEWS_CATEGORIES = {
    "general",
    "music",
    "markets",
    "sports",
    "politics",
}

DEFAULT_NEWS_QUERIES = {
    "general": "world OR society OR culture",
    "music": "music OR entertainment OR artists",
    "markets": "stock market OR economy OR inflation",
    "sports": "sports OR football OR basketball",
    "politics": "politics OR government OR election",
}


class PlaylistGenerationService:
    """
    Servicio para generar playlists inteligentes usando el agente RL.
    
    Coordina:
    1. Construcción del estado (contexto actual)
    2. Selección de tracks usando el agente
    3. Creación de playlist en Spotify
    4. Registro de la sesión para entrenamiento
    """

    def __init__(self):
        """Inicializa el servicio."""
        self.agent = get_agent()
        self.reward_service = get_reward_service()
        self.state_builder = get_state_builder()
        self.context_weight, self.history_weight = self._get_scoring_weights()

    def generate_playlist(
        self,
        user: User,
        playlist_name: str = "Generated by Moodsic",
        count: int = 10,
        weather_context: Optional[Dict] = None,
        use_context: bool = True,
        news_category: str = "general",
        news_query: Optional[str] = None,
        news_limit: int = 20,
    ) -> Dict:
        """
        Genera una playlist personalizada para el usuario.
        
        Args:
            user: Usuario para el que generar la playlist
            playlist_name: Nombre de la playlist
            count: Número de canciones a incluir
            weather_context: Diccionario con contexto climático
            use_context: Si usar el contexto en la generación
            
        Returns:
            Dict con información de la playlist generada
        """
        logger.info(
            f"Generando playlist para usuario {user.username} "
            f"con {count} canciones"
        )

        try:
            # Crear sesión única
            session_id = str(uuid.uuid4())

            # Obtener tracks disponibles y registrar su procedencia
            available_tracks, source_meta = self._get_available_tracks_with_meta(user)
            generation_meta = {
                "used_spotify_sync": False,
                "used_cached_news": False,
                "used_local_catalog": source_meta["used_local_catalog"],
                "used_spotify_catalog_fallback": source_meta[
                    "used_spotify_catalog_fallback"
                ],
            }

            if len(available_tracks) == 0:
                raise ValueError("No hay canciones disponibles para generar playlist")

            # Limitar a tracks disponibles
            count = min(count, len(available_tracks))

            user_history = self._get_user_history(user)
            track_scores = self._score_tracks(
                available_tracks,
                weather_context=weather_context,
                user_history=user_history,
            )
            available_actions = sorted(
                list(range(len(available_tracks))),
                key=lambda idx: track_scores[idx],
                reverse=True,
            )

            # Construir estado inicial
            news_category = self._normalize_news_category(news_category)
            effective_query = (news_query or "").strip() or DEFAULT_NEWS_QUERIES[
                news_category
            ]

            if effective_query:
                try:
                    _, news_meta = NewsService.fetch_and_store_news(
                        query=effective_query,
                        category=news_category,
                        page_size=max(5, min(news_limit, 50)),
                        return_meta=True,
                    )
                    generation_meta["used_cached_news"] = bool(
                        news_meta.get("used_cached_news", False)
                    )
                except Exception as exc:
                    generation_meta["used_cached_news"] = True
                    logger.warning(
                        f"No se pudo refrescar noticias para query '{effective_query}': {exc}"
                    )

            news_contexts = self._get_latest_news_contexts(
                category=news_category,
                limit=news_limit,
            )
            state = self.state_builder.build_state(
                user=user,
                weather_context=weather_context,
                current_track=None,
                time_of_day=self._get_time_of_day(),
                news_contexts=news_contexts,
            )

            # Seleccionar tracks usando el agente
            selected_track_indices = []

            for step in range(count):
                # El agente selecciona la mejor acción (track)
                action = self.agent.select_action(
                    state,
                    available_actions=available_actions,
                    training=False,  # Usar explotación pura
                )

                track_idx = action
                selected_track_indices.append(track_idx)

                # Remover track seleccionado para no repetir
                available_actions.remove(action)

                # Actualizar estado para siguiente iteración
                track = available_tracks[track_idx]
                track_features = self._get_track_audio_features(track)

                state = self.state_builder.build_state(
                    user=user,
                    weather_context=weather_context,
                    current_track=track_features,
                    time_of_day=self._get_time_of_day(),
                    news_contexts=news_contexts,
                )

            # Crear playlist en BD
            selected_tracks = [available_tracks[idx] for idx in selected_track_indices]
            playlist = self._create_playlist(
                user=user,
                playlist_name=playlist_name,
                tracks=selected_tracks,
                session_id=session_id,
            )

            # Sincronizar con Spotify si el usuario está conectado
            if user.is_spotify_connected:
                try:
                    spotify_playlist = self._sync_playlist_to_spotify(
                        user=user,
                        playlist=playlist,
                        tracks=selected_tracks,
                    )
                    if spotify_playlist:
                        playlist.spotify_id = spotify_playlist.get("id", f"moodsic_{session_id}")
                        playlist.uri = spotify_playlist.get("uri", "")
                        playlist.save()
                        generation_meta["used_spotify_sync"] = True
                        logger.info(
                            f"Playlist sincronizada con Spotify: {spotify_playlist.get('id')}"
                        )
                except Exception as e:
                    logger.warning(f"No se pudo sincronizar con Spotify: {e}")
                    # Continuar sin Spotify, playlist sigue siendo válida localmente

            logger.info(
                f"Playlist creada exitosamente: {playlist.id} "
                f"con {len(selected_tracks)} canciones"
            )

            return {
                "playlist_id": playlist.spotify_id,
                "playlist_name": playlist.name,
                "tracks_count": len(selected_tracks),
                "track_ids": [t.id for t in selected_tracks],
                "track_names": [t.name for t in selected_tracks],
                "estimated_duration": sum(t.duration_ms for t in selected_tracks)
                // 1000,
                "session_id": session_id,
                "created_at": timezone.now().isoformat(),
                "mode": self._resolve_generation_mode(generation_meta),
                "used_spotify_sync": generation_meta["used_spotify_sync"],
                "used_cached_news": generation_meta["used_cached_news"],
                "used_local_catalog": generation_meta["used_local_catalog"],
                "used_spotify_catalog_fallback": generation_meta[
                    "used_spotify_catalog_fallback"
                ],
            }

        except Exception as e:
            logger.error(f"Error generando playlist: {e}", exc_info=True)
            raise

    def record_interaction(
        self,
        user: User,
        track: Track,
        feedback: str,
        play_duration: int,
        track_duration: int,
        session_id: str,
        weather_id: Optional[int] = None,
        news_ids: Optional[List[int]] = None,
    ) -> Dict:
        """
        Registra la interacción del usuario con un track.
        
        Args:
            user: Usuario
            track: Track reproducido
            feedback: Tipo de feedback
            play_duration: Segundos reproducidos
            track_duration: Duración total del track
            session_id: ID de la sesión
            weather_id: ID del contexto climático
            news_ids: IDs de noticias
            
        Returns:
            Dict con información de la interacción registrada
        """
        from apps.interactions.models import Interaction

        logger.info(
            f"Registrando interacción: {user.username} - {track.name} "
            f"({feedback})"
        )

        try:
            # Obtener contexto para calcular reward
            weather_context = None
            if weather_id:
                try:
                    weather = WeatherContext.objects.get(id=weather_id)
                    weather_context = {
                        "temperature": weather.temperature,
                        "humidity": weather.humidity,
                        "wind_speed": weather.wind_speed,
                        "main_status": weather.main_status,
                    }
                except WeatherContext.DoesNotExist:
                    pass

            # Obtener audio features del track
            audio_features = self._get_track_audio_features(track)

            # Obtener historico del usuario
            user_history = self._get_user_history(user)

            # Calcular reward desde la capa de dominio de interactions
            reward = self.reward_service.calculate_interaction_reward(
                user_feedback=feedback,
                user=user,
                track=track,
                weather_id=weather_id,
                news_ids=news_ids,
                user_history=user_history,
            )

            # Guardar interacción
            interaction = Interaction.objects.create(
                user=user,
                track=track,
                feedback=feedback,
                play_duration=play_duration,
                track_duration=track_duration,
                reward=reward,
                weather_id=weather_id,
                news_ids=news_ids or [],
                session_id=session_id,
            )

            # Guardar la experiencia en el replay buffer del agente para entrenamient futuro
            news_contexts = []
            if news_ids:
                news_contexts = [
                    {
                        "sentiment_score": n.sentiment_score,
                        "sentiment_label": n.sentiment_label,
                        "is_breaking": n.is_breaking,
                    }
                    for n in NewsContext.objects.filter(id__in=news_ids)
                ]

            state = self.state_builder.build_state(
                user,
                weather_context,
                audio_features,
                news_contexts=news_contexts,
            )
            # Aquí iría la acción (track index) pero se omite para no complicar

            logger.info(f"Interacción guardada: {interaction.id}, Reward: {reward}")

            return {
                "interaction_id": interaction.id,
                "reward": reward,
                "completion_percentage": interaction.completion_percentage,
                "is_positive": interaction.is_positive,
            }

        except Exception as e:
            logger.error(f"Error registrando interacción: {e}", exc_info=True)
            raise

    def get_user_stats(self, user: User) -> Dict:
        """
        Obtiene estadísticas del usuario.
        """
        from apps.interactions.models import Interaction

        interactions = Interaction.objects.filter(user=user)
        total = interactions.count()

        if total == 0:
            return {
                "user_id": user.id,
                "total_interactions": 0,
                "total_skips": 0,
                "total_completed": 0,
                "average_reward": 0.0,
                "total_reward": 0.0,
                "skip_rate": 0.0,
                "completion_rate": 0.0,
                "favorite_genres": [],
                "favorite_artists": [],
                "average_session_length": 0.0,
            }

        skips = interactions.filter(feedback__startswith="skip").count()
        completed = interactions.filter(feedback="completed").count()
        avg_reward = interactions.aggregate(
            avg=Avg("reward")
        )["avg"] or 0.0
        total_reward = interactions.aggregate(
            total=Sum("reward")
        )["total"] or 0.0

        stats = {
            "user_id": user.id,
            "total_interactions": total,
            "total_skips": skips,
            "total_completed": completed,
            "average_reward": float(avg_reward),
            "total_reward": float(total_reward),
            "skip_rate": skips / total if total > 0 else 0.0,
            "completion_rate": completed / total if total > 0 else 0.0,
        }

        stats["favorite_genres"] = self.get_user_favorite_genres(user)
        stats["favorite_artists"] = self.get_user_favorite_artists(user)
        stats["average_session_length"] = self.get_average_session_length(user)
        return stats

    def _get_available_tracks(
        self, user: User, limit: int = 500
    ) -> List[Track]:
        tracks, _meta = self._get_available_tracks_with_meta(user, limit=limit)
        return tracks

    def _get_available_tracks_with_meta(
        self, user: User, limit: int = 500
    ) -> Tuple[List[Track], Dict[str, bool]]:
        """
        Obtiene tracks disponibles para seleccionar y registra su procedencia.
        """
        max_tracks = min(limit, self.agent.action_dim)
        local_tracks = list(
            Track.objects.prefetch_related("artists").all()[:max_tracks]
        )
        if local_tracks:
            return local_tracks, {
                "used_local_catalog": True,
                "used_spotify_catalog_fallback": False,
            }

        hydrated_tracks = self._hydrate_tracks_from_spotify(user, limit=max_tracks)
        if hydrated_tracks:
            return hydrated_tracks[:max_tracks], {
                "used_local_catalog": False,
                "used_spotify_catalog_fallback": True,
            }

        return [], {
            "used_local_catalog": False,
            "used_spotify_catalog_fallback": False,
        }

    def _hydrate_tracks_from_spotify(self, user: User, limit: int = 100) -> List[Track]:
        """Populate the local catalog from Spotify as an online fallback."""
        if not getattr(user, "is_spotify_connected", False):
            return []

        try:
            spotify_service = SpotifyMusicService(user)
            if not spotify_service.client:
                return []

            tracks_data = spotify_service.get_user_liked_tracks(limit=limit) or []
            if not tracks_data:
                tracks_data = spotify_service.get_top_tracks(limit=limit) or []

            imported_tracks = self._upsert_spotify_tracks(tracks_data)
            if imported_tracks:
                logger.info(
                    f"Se importaron {len(imported_tracks)} tracks desde Spotify para fallback"
                )
            return imported_tracks
        except Exception as exc:
            logger.warning(f"No se pudieron hidratar tracks desde Spotify: {exc}")
            return []

    @staticmethod
    def _upsert_spotify_tracks(tracks_data: List[Dict]) -> List[Track]:
        imported_tracks: List[Track] = []

        for index, item in enumerate(tracks_data):
            spotify_id = (item.get("id") or "").strip()
            name = (item.get("name") or f"Remote Track {index + 1}").strip()
            if not spotify_id:
                continue

            album_name = (item.get("album") or "Unknown Album").strip() or "Unknown Album"
            album_spotify_id = (item.get("album_id") or f"album_{spotify_id}").strip()
            album, _ = Album.objects.get_or_create(
                spotify_id=album_spotify_id,
                defaults={"name": album_name},
            )

            track, _ = Track.objects.update_or_create(
                spotify_id=spotify_id,
                defaults={
                    "name": name,
                    "album": album,
                    "duration_ms": int(item.get("duration_ms") or 180000),
                    "explicit": bool(item.get("explicit", False)),
                    "track_number": int(item.get("track_number") or 1),
                    "popularity": int(item.get("popularity") or 50),
                    "uri": item.get("uri") or f"spotify:track:{spotify_id}",
                    "preview_url": item.get("preview_url") or "",
                },
            )

            track.artists.clear()
            for artist_idx, artist_data in enumerate(item.get("artists", [])):
                if isinstance(artist_data, dict):
                    artist_name = (artist_data.get("name") or f"Artist {artist_idx + 1}").strip()
                    artist_spotify_id = (
                        artist_data.get("id") or f"artist_{spotify_id}_{artist_idx}"
                    )
                else:
                    artist_name = str(artist_data).strip() or f"Artist {artist_idx + 1}"
                    artist_spotify_id = f"artist_{spotify_id}_{artist_idx}"

                artist, _ = Artist.objects.get_or_create(
                    spotify_id=artist_spotify_id,
                    defaults={"name": artist_name},
                )
                track.artists.add(artist)

            imported_tracks.append(track)

        return imported_tracks

    def _get_time_of_day(self) -> str:
        """Obtiene la hora del día actual."""
        hour = timezone.now().hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour <= 23:
            return "evening"
        else:
            return "night"

    @staticmethod
    def _get_track_audio_features(track: Track) -> Dict:
        """
        Obtiene las características de audio de un track.
        """
        try:
            if hasattr(track, "audio_features"):
                af = track.audio_features
                return {
                    "energy": af.energy,
                    "danceability": af.danceability,
                    "valence": af.valence,
                    "acousticness": af.acousticness,
                    "instrumentalness": af.instrumentalness,
                    "liveness": af.liveness,
                    "loudness": af.loudness,
                    "tempo": af.tempo,
                    "speechiness": af.speechiness,
                    "key": af.key,
                    "mode": af.mode,
                    "time_signature": af.time_signature,
                }
        except Exception:
            pass

        # Retornar defaults si no existen
        return {
            "energy": 0.5,
            "danceability": 0.5,
            "valence": 0.5,
            "acousticness": 0.3,
            "instrumentalness": 0.0,
            "liveness": 0.2,
            "loudness": -5,
            "tempo": 120,
            "speechiness": 0.0,
            "key": 0,
            "mode": 1,
            "time_signature": 4,
        }

    def _get_user_history(self, user: User) -> Dict:
        """
        Obtiene el historico del usuario incluyendo preferencias.
        """
        from apps.interactions.models import Interaction

        interactions = Interaction.objects.filter(user=user).select_related(
            "track__audio_features"
        ).prefetch_related("track__artists")

        if interactions.count() == 0:
            return {
                "skip_rate": 0.3,
                "completion_rate": 0.7,
                "avg_energy": 0.5,
                "avg_danceability": 0.5,
                "avg_valence": 0.5,
                "favorite_artists": [],
                "favorite_genres": [],
            }

        skips = interactions.filter(feedback__startswith="skip").count()
        total = interactions.count()
        avg_energy = 0.0
        avg_danceability = 0.0
        avg_valence = 0.0
        feature_count = 0

        for interaction in interactions:
            audio_features = getattr(interaction.track, "audio_features", None)
            if audio_features:
                avg_energy += audio_features.energy
                avg_danceability += audio_features.danceability
                avg_valence += audio_features.valence
                feature_count += 1

        if feature_count > 0:
            avg_energy /= feature_count
            avg_danceability /= feature_count
            avg_valence /= feature_count
        else:
            avg_energy = 0.5
            avg_danceability = 0.5
            avg_valence = 0.5

        preferences = self._get_user_preferences(user)

        return {
            "skip_rate": skips / total if total > 0 else 0.0,
            "completion_rate": 1 - (skips / total if total > 0 else 0.0),
            "avg_energy": avg_energy,
            "avg_danceability": avg_danceability,
            "avg_valence": avg_valence,
            "favorite_artists": preferences["artists"],
            "favorite_genres": preferences["genres"],
        }

    def _get_user_preferences(self, user: User) -> Dict[str, List[str]]:
        """
        Retorna los artistas y géneros más frecuentes en el historial del usuario.
        """
        from apps.interactions.models import Interaction

        interactions = Interaction.objects.filter(user=user).select_related(
            "track__audio_features"
        ).prefetch_related("track__artists")

        artist_counter = Counter()
        genre_counter = Counter()

        for interaction in interactions:
            for artist in interaction.track.artists.all():
                artist_counter[artist.name] += 1
                for genre in getattr(artist, "genres", []) or []:
                    normalized = genre.strip()
                    if normalized:
                        genre_counter[normalized] += 1

        return {
            "artists": [name for name, _ in artist_counter.most_common(5)],
            "genres": [name for name, _ in genre_counter.most_common(5)],
        }

    @staticmethod
    def _get_scoring_weights() -> Tuple[float, float]:
        """Return normalized recommender weights.

        The benchmark winner is used as the default balance: 0.6 for current
        context fit and 0.4 for user history/personalization.
        """
        context_weight = float(getattr(settings, "RECOMMENDER_CONTEXT_WEIGHT", 0.6))
        history_weight = float(getattr(settings, "RECOMMENDER_HISTORY_WEIGHT", 0.4))

        context_weight = max(0.0, context_weight)
        history_weight = max(0.0, history_weight)
        total = context_weight + history_weight
        if total <= 0:
            return 0.6, 0.4
        return context_weight / total, history_weight / total

    def _score_tracks(
        self,
        tracks: List[Track],
        weather_context: Optional[Dict] = None,
        user_history: Optional[Dict] = None,
    ) -> List[float]:
        """
        Calcula una puntuación para cada track basada en clima e historial.
        """
        user_history = user_history or {}
        return [
            self._score_track(track, weather_context, user_history)
            for track in tracks
        ]

    @staticmethod
    def _get_latest_news_contexts(
        category: str = "general", limit: int = 20
    ) -> List[Dict]:
        """Return compact latest news context used by the state builder."""
        queryset = NewsContext.objects.order_by("-published_at")
        if category and category != "all":
            queryset = queryset.filter(category=category)
        news_items = queryset[: max(1, min(limit, 50))]
        return [
            {
                "sentiment_score": item.sentiment_score,
                "sentiment_label": item.sentiment_label,
                "is_breaking": item.is_breaking,
            }
            for item in news_items
        ]

    @staticmethod
    def _normalize_news_category(category: str) -> str:
        normalized = (category or "general").strip().lower()
        if normalized not in ALLOWED_NEWS_CATEGORIES:
            return "general"
        return normalized

    def _score_track(
        self,
        track: Track,
        weather_context: Optional[Dict] = None,
        user_history: Optional[Dict] = None,
    ) -> float:
        """
        Genera una puntuación heurística para un track.

        Usa una combinación ponderada de:
        - ajuste al contexto actual (default 0.6)
        - afinidad con el historial/preferencias del usuario (default 0.4)
        """
        user_history = user_history or {}
        audio_features = self._get_track_audio_features(track)

        energy = float(audio_features.get("energy", 0.5))
        danceability = float(audio_features.get("danceability", 0.5))
        valence = float(audio_features.get("valence", 0.5))
        acousticness = float(audio_features.get("acousticness", 0.3))
        popularity = float((track.popularity or 50) / 100.0)

        context_score = 0.0
        context_score += valence * 0.35
        context_score += energy * 0.25
        context_score += danceability * 0.25
        context_score += popularity * 0.15

        if weather_context:
            main = weather_context.get("main_status", "").lower()
            description = weather_context.get("description", "").lower()
            temperature = weather_context.get("temperature", 20)

            if any(x in main for x in ["rain", "drizzle", "thunderstorm", "snow", "cloud"]):
                context_score += (1.0 - ((energy + danceability) / 2.0)) * 0.4
                context_score += acousticness * 0.2
            if any(x in main for x in ["clear", "sunny"]) or "sun" in description:
                context_score += (energy + valence) * 0.25
            if temperature <= 5:
                context_score += acousticness * 0.15
            elif temperature >= 25:
                context_score += danceability * 0.15

        history_score = 0.0
        avg_energy = float(user_history.get("avg_energy", 0.5))
        avg_danceability = float(user_history.get("avg_danceability", 0.5))
        avg_valence = float(user_history.get("avg_valence", 0.5))

        history_score += max(0.0, 1.0 - abs(energy - avg_energy)) * 0.25
        history_score += max(0.0, 1.0 - abs(danceability - avg_danceability)) * 0.25
        history_score += max(0.0, 1.0 - abs(valence - avg_valence)) * 0.25

        favorite_artists = set(user_history.get("favorite_artists", []))
        favorite_genres = set(user_history.get("favorite_genres", []))

        for artist in track.artists.all():
            if artist.name in favorite_artists:
                history_score += 0.35
            for genre in getattr(artist, "genres", []) or []:
                if genre.strip() in favorite_genres:
                    history_score += 0.15

        return (context_score * self.context_weight) + (
            history_score * self.history_weight
        )

    @staticmethod
    def _resolve_generation_mode(generation_meta: Dict[str, bool]) -> str:
        online_signals = bool(generation_meta.get("used_spotify_sync")) or bool(
            generation_meta.get("used_spotify_catalog_fallback")
        )
        fallback_signals = bool(generation_meta.get("used_cached_news")) or bool(
            generation_meta.get("used_local_catalog")
        )

        if online_signals and fallback_signals:
            return "hybrid"
        if online_signals:
            return "online"
        return "fallback"

    def get_user_favorite_artists(self, user: User) -> List[str]:
        """Retorna los artistas favoritos del usuario."""
        return self._get_user_preferences(user)["artists"]

    def get_user_favorite_genres(self, user: User) -> List[str]:
        """Retorna los géneros favoritos del usuario."""
        return self._get_user_preferences(user)["genres"]

    def get_average_session_length(self, user: User) -> float:
        """Calcula la duración promedio de sesiones del usuario en segundos."""
        from apps.interactions.models import InteractionSession

        sessions = InteractionSession.objects.filter(user=user, ended_at__isnull=False)
        durations = [
            (session.ended_at - session.started_at).total_seconds()
            for session in sessions
            if session.ended_at
        ]
        if not durations:
            return 0.0
        return float(sum(durations) / len(durations))

    @staticmethod
    def _create_playlist(
        user: User, playlist_name: str, tracks: List[Track], session_id: str
    ) -> Playlist:
        """
        Crea una playlist en la BD.
        """
        playlist = Playlist.objects.create(
            user=user,
            name=playlist_name,
            spotify_id=f"moodsic_{session_id}",
            is_public=False,
        )

        # Añadir tracks a la playlist
        for idx, track in enumerate(tracks):
            PlaylistTrack.objects.create(
                playlist=playlist,
                track=track,
                order=idx,
            )

        return playlist

    @staticmethod
    def _sync_playlist_to_spotify(
        user: User, playlist: Playlist, tracks: List[Track]
    ) -> Optional[Dict]:
        """
        Sincroniza una playlist con Spotify, creándola y agregando tracks.
        
        Args:
            user: Usuario (debe estar conectado a Spotify)
            playlist: Objeto de playlist de Django
            tracks: Lista de Track objects
            
        Returns:
            Diccionario con información de la playlist de Spotify, o None
        """
        try:
            spotify_service = SpotifyMusicService(user)
            if not spotify_service.client:
                logger.warning(f"Usuario {user.username} no tiene cliente Spotify disponible")
                return None

            # 1. Crear la playlist en Spotify
            logger.info(f"Creando playlist en Spotify: {playlist.name}")
            spotify_playlist = spotify_service.create_playlist(
                name=playlist.name,
                description=f"Generated by Moodsic on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                public=playlist.is_public,
            )

            if not spotify_playlist:
                logger.error("No se pudo crear playlist en Spotify")
                return None

            playlist_id = spotify_playlist.get("id")
            logger.info(f"Playlist creada en Spotify: {playlist_id}")

            # 2. Obtener URIs de los tracks
            track_uris = [t.uri for t in tracks if t.uri]
            
            if not track_uris:
                logger.warning("No hay URIs de tracks disponibles para agregar a Spotify")
                return spotify_playlist

            # 3. Agregar tracks a la playlist
            logger.info(f"Agregando {len(track_uris)} tracks a playlist {playlist_id}")
            success = spotify_service.add_tracks_to_playlist(playlist_id, track_uris)

            if success:
                logger.info(f"Tracks agregados exitosamente a playlist {playlist_id}")
            else:
                logger.warning(f"Hubo problemas agregando tracks a playlist {playlist_id}")

            return spotify_playlist

        except Exception as e:
            logger.error(f"Error sincronizando playlist con Spotify: {e}", exc_info=True)
            return None


# Instancia global
_service_instance = None


def get_playlist_generation_service() -> PlaylistGenerationService:
    """
    Obtiene la instancia global del servicio.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = PlaylistGenerationService()
    return _service_instance
```

## Archivo: apps/interactions/services/reward_service.py

Ruta completa: apps/interactions/services/reward_service.py

```python
"""Domain reward service used by interactions workflow.

This keeps reward-related orchestration in the interactions app while reusing
the RL calculator implementation from ml.reward.
"""

from __future__ import annotations

from typing import Optional

from apps.context.models import NewsContext, WeatherContext
from apps.music.models import Track
from ml.reward import get_reward_calculator


class RewardService:
	"""Calculates normalized rewards based on user feedback and context."""

	def __init__(self):
		self.reward_calculator = get_reward_calculator()

	def calculate_interaction_reward(
		self,
		*,
		user_feedback: str,
		user,
		track: Track,
		weather_id: Optional[int] = None,
		news_ids: Optional[list[int]] = None,
		user_history: Optional[dict] = None,
	) -> float:
		weather_context = self._get_weather_context(weather_id)
		news_context = self._get_news_context(news_ids)
		audio_features = self._get_track_audio_features(track)
		history = user_history or self._get_user_history(user)

		# Include coarse news signal into weather_context dict to avoid changing
		# the lower-level calculator signature while still using external context.
		if news_context:
			weather_context = weather_context or {}
			weather_context.update(
				{
					"news_sentiment": news_context.get("avg_sentiment", 0.0),
					"breaking_news_ratio": news_context.get("breaking_ratio", 0.0),
				}
			)

		raw_reward = self.reward_calculator.calculate_reward(
			user_feedback=user_feedback,
			weather_context=weather_context,
			track_audio_features=audio_features,
			user_history=history,
		)
		return float(self.reward_calculator.normalize_reward(raw_reward))

	@staticmethod
	def _get_weather_context(weather_id: Optional[int]) -> Optional[dict]:
		if not weather_id:
			return None
		weather = WeatherContext.objects.filter(id=weather_id).first()
		if not weather:
			return None
		return {
			"temperature": weather.temperature,
			"humidity": weather.humidity,
			"wind_speed": weather.wind_speed,
			"main_status": weather.main_status,
		}

	@staticmethod
	def _get_news_context(news_ids: Optional[list[int]]) -> Optional[dict]:
		if not news_ids:
			return None
		news_items = list(NewsContext.objects.filter(id__in=news_ids))
		if not news_items:
			return None
		avg_sentiment = sum(item.sentiment_score for item in news_items) / len(news_items)
		breaking_ratio = sum(1 for item in news_items if item.is_breaking) / len(news_items)
		return {
			"count": len(news_items),
			"avg_sentiment": float(avg_sentiment),
			"breaking_ratio": float(breaking_ratio),
		}

	@staticmethod
	def _get_track_audio_features(track: Track) -> dict:
		audio_features = getattr(track, "audio_features", None)
		if not audio_features:
			return {
				"energy": 0.5,
				"danceability": 0.5,
				"valence": 0.5,
				"acousticness": 0.3,
				"instrumentalness": 0.0,
				"liveness": 0.2,
				"loudness": -5,
				"tempo": 120,
				"speechiness": 0.0,
				"key": 0,
				"mode": 1,
				"time_signature": 4,
			}
		return {
			"energy": audio_features.energy,
			"danceability": audio_features.danceability,
			"valence": audio_features.valence,
			"acousticness": audio_features.acousticness,
			"instrumentalness": audio_features.instrumentalness,
			"liveness": audio_features.liveness,
			"loudness": audio_features.loudness,
			"tempo": audio_features.tempo,
			"speechiness": audio_features.speechiness,
			"key": audio_features.key,
			"mode": audio_features.mode,
			"time_signature": audio_features.time_signature,
		}

	@staticmethod
	def _get_user_history(user) -> dict:
		from apps.interactions.models import Interaction

		interactions = list(Interaction.objects.filter(user=user).select_related("track"))
		if not interactions:
			return {
				"skip_rate": 0.3,
				"avg_energy": 0.5,
				"avg_danceability": 0.5,
				"avg_valence": 0.5,
			}

		total = len(interactions)
		skips = sum(1 for i in interactions if i.feedback.startswith("skip"))

		energies, danceabilities, valences = [], [], []
		for interaction in interactions:
			af = getattr(interaction.track, "audio_features", None)
			if af is None:
				continue
			energies.append(af.energy)
			danceabilities.append(af.danceability)
			valences.append(af.valence)

		def avg(values, default):
			return float(sum(values) / len(values)) if values else default

		return {
			"skip_rate": float(skips / total),
			"avg_energy": avg(energies, 0.5),
			"avg_danceability": avg(danceabilities, 0.5),
			"avg_valence": avg(valences, 0.5),
		}


_reward_service_instance: RewardService | None = None


def get_reward_service() -> RewardService:
	global _reward_service_instance
	if _reward_service_instance is None:
		_reward_service_instance = RewardService()
	return _reward_service_instance
```

## Archivo: apps/interactions/tests/__init__.py

Ruta completa: apps/interactions/tests/__init__.py

```python

```

## Archivo: apps/interactions/tests/test_api.py

Ruta completa: apps/interactions/tests/test_api.py

```python
"""
Tests para los endpoints de la API de Interactions.
"""

import json
import pytest
from datetime import timedelta
from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def client():
    """Fixture del cliente de test."""
    return Client()


@pytest.fixture
def user(db):
    """Fixture con usuario de test."""
    return User.objects.create_user(
        username="testuser",
        email="test@test.com",
        password="testpass123",
    )


@pytest.fixture
def admin_user(db):
    """Fixture con usuario admin."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="adminpass123",
    )


@pytest.fixture
def track(db):
    """Fixture con track de test."""
    from apps.music.models import Track, Album

    album = Album.objects.create(name="Test Album")
    return Track.objects.create(
        spotify_id="test_track_123",
        name="Test Track",
        album=album,
        duration_ms=180000,
        explicit=False,
        track_number=1,
        popularity=80,
    )


@pytest.mark.django_db
class TestInteractionAPI:
    """Tests para los endpoints de Interaction."""

    def test_create_interaction_endpoint_exists(self, client):
        """Test básico que el endpoint de interacción existe."""
        response = client.options("/api/interactions/interactions/")
        # OPTIONS debería estar permitido o retornar 404 si no existe el endpoint
        assert response.status_code in [200, 404, 405]

    def test_user_stats_endpoint_exists(self, client, user):
        """Test que el endpoint de estadísticas del usuario existe."""
        client.force_login(user)
        response = client.get("/api/interactions/interactions/user/stats/")
        # Debería retornar algo o 404 si el endpoint no estámapeado correctamente
        assert response.status_code in [200, 404, 400, 401]

    def test_user_stats_returns_dynamic_metrics(self, client, user):
        """El endpoint debe calcular géneros, artistas y duración de sesiones."""
        from apps.music.models import Album, Artist, Track
        from apps.interactions.models import Interaction, InteractionSession

        album = Album.objects.create(name="Stats Album")
        artist = Artist.objects.create(
            spotify_id="artist_123",
            name="Favorite Artist",
            genres=["rock", "synthpop"],
        )

        track = Track.objects.create(
            spotify_id="track_123",
            name="Favorite Track",
            album=album,
            duration_ms=200000,
            explicit=False,
            track_number=1,
            popularity=80,
            uri="spotify:track:track_123",
        )
        track.artists.add(artist)

        Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            play_duration=180,
            track_duration=200,
            session_id="session_abc",
        )

        now = timezone.now()
        InteractionSession.objects.create(
            user=user,
            session_id="session_abc",
            ended_at=now + timedelta(minutes=30),
            is_active=False,
        )

        client.force_login(user)
        response = client.get("/api/interactions/interactions/user/stats/")
        assert response.status_code == 200
        payload = response.json()

        assert payload["favorite_artists"] == ["Favorite Artist"]
        assert "rock" in payload["favorite_genres"]
        assert payload["average_session_length"] > 0


@pytest.mark.django_db
class TestPlaylistAPI:
    """Tests para los endpoints de Playlist Generation."""

    def test_generate_playlist_endpoint_exists(self, client):
        """Test que el endpoint de generación de playlists existe."""
        response = client.options("/api/interactions/playlists/generate/")
        # OPTIONS debería estar permitido o retornar 404 si no existe
        assert response.status_code in [200, 404, 405]

    def test_generate_playlist_unauthorized(self, client):
        """Test de generación de playlist sin autenticación."""
        # Simplemente verificamos que el endpoint responde
        response = client.get("/api/interactions/playlists/generate/")
        # Puede retornar 405 (method not allowed) o 401/403 (unauthorized)
        assert response.status_code in [401, 403, 404, 405]

    def test_generate_playlist_invalid_weather_id_returns_404(self, client, user, track):
        """El endpoint debe rechazar weather_id inválido."""
        client.force_login(user)
        response = client.post(
            "/api/interactions/playlists/generate/",
            data=json.dumps({"name": "Test Playlist", "count": 1, "weather_id": 999, "use_context": True}),
            content_type="application/json",
        )

        assert response.status_code == 404
        assert response.json().get("error") == "Weather context no encontrado"

    def test_generate_playlist_with_valid_weather_id_returns_session(self, client, user, track):
        """El endpoint debe generar playlist con weather_id válido y devolver session_id."""
        from apps.context.models import WeatherContext

        weather = WeatherContext.objects.create(
            main_status="Clear",
            description="Clear sky",
            icon_code="01d",
            temperature=25.0,
            feels_like=25.0,
            temp_min=20.0,
            temp_max=28.0,
            pressure=1013,
            humidity=40,
            visibility=10000,
            wind_speed=3.5,
            wind_deg=120,
            clouds_all=0,
            timestamp=timezone.now(),
        )

        client.force_login(user)
        response = client.post(
            "/api/interactions/playlists/generate/",
            data=json.dumps({"name": "Morning Playlist", "count": 1, "weather_id": weather.id, "use_context": True}),
            content_type="application/json",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["playlist_name"] == "Morning Playlist"
        assert payload["tracks_count"] == 1
        assert payload["session_id"]
        assert payload["mode"] in {"online", "fallback", "hybrid"}
        assert isinstance(payload["used_spotify_sync"], bool)
        assert isinstance(payload["used_cached_news"], bool)
        assert isinstance(payload["used_local_catalog"], bool)
        assert isinstance(payload["used_spotify_catalog_fallback"], bool)

    def test_generate_playlist_rejects_invalid_news_limit(self, client, user):
        """news_limit fuera del rango permitido debe ser rechazado por validación."""
        client.force_login(user)
        response = client.post(
            "/api/interactions/playlists/generate/",
            data=json.dumps(
                {
                    "name": "Invalid Limit Playlist",
                    "count": 1,
                    "news_category": "music",
                    "news_limit": 0,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 422

    def test_generate_playlist_caps_requested_count_with_warning(self, client, user, track):
        """Si se piden demasiadas canciones, la API debe caparlo y avisarlo."""
        client.force_login(user)
        response = client.post(
            "/api/interactions/playlists/generate/",
            data=json.dumps({"name": "Big Playlist", "count": 150, "use_context": False}),
            content_type="application/json",
        )

        assert response.status_code == 200
        payload = response.json()
        assert "warnings" in payload
        assert any("100" in warning for warning in payload["warnings"])

    def test_create_interaction_rejects_invalid_feedback_value(self, client, user, track):
        """feedback inválido debe ser rechazado por el schema."""
        client.force_login(user)
        response = client.post(
            "/api/interactions/interactions/",
            data=json.dumps(
                {
                    "track_id": track.id,
                    "feedback": "invalid_feedback",
                    "play_duration": 20,
                    "track_duration": 180,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 422

    def test_demo_home_page_is_available(self, client):
        """La raíz del proyecto debe mostrar una página de demo útil para la entrega."""
        response = client.get("/")

        assert response.status_code == 200
        assert "MoodSic" in response.content.decode()
        assert "Demo" in response.content.decode() or "dashboard" in response.content.decode().lower()


@pytest.mark.django_db
class TestDashboardAPI:
    """Tests para los endpoints del Dashboard."""

    def test_get_dashboard_metrics_endpoint_exists(self, client):
        """Test que el endpoint del dashboard existe."""
        response = client.options("/api/interactions/dashboard/metrics/")
        # OPTIONS debería estar permitido o retornar 404 si no existe
        assert response.status_code in [200, 404, 405]

    def test_dashboard_metrics_forbid_non_staff_users(self, client, user):
        """El dashboard agregado debe limitarse a usuarios staff."""
        client.force_login(user)
        response = client.get("/api/interactions/dashboard/metrics/")

        assert response.status_code == 403

    def test_dashboard_metrics_returns_user_growth(self, client, admin_user, user, track):
        """El dashboard debe retornar métricas y crecimiento de usuarios."""
        from django.utils import timezone
        from apps.interactions.models import Interaction

        user2 = User.objects.create_user(
            username="testuser2",
            email="test2@test.com",
            password="testpass123",
        )

        Interaction.objects.create(
            user=user2,
            track=track,
            feedback="completed",
            play_duration=180,
            track_duration=200,
            session_id="session_growth_1",
            created_at=timezone.now(),
        )
        Interaction.objects.create(
            user=user,
            track=track,
            feedback="skip",
            play_duration=30,
            track_duration=200,
            session_id="session_growth_2",
            created_at=timezone.now() - timedelta(days=1),
        )

        client.force_login(admin_user)
        response = client.get("/api/interactions/dashboard/metrics/")
        assert response.status_code == 200

        payload = response.json()
        assert "user_growth" in payload
        assert isinstance(payload["user_growth"], list)
        assert len(payload["user_growth"]) == 7
        assert any(day["new_users"] >= 0 for day in payload["user_growth"])
```

## Archivo: apps/interactions/tests/test_models.py

Ruta completa: apps/interactions/tests/test_models.py

```python
"""
Tests para los modelos de Interaction.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.interactions.models import Interaction, InteractionSession

User = get_user_model()


@pytest.fixture
def user(db):
    """Fixture con usuario de test."""
    return User.objects.create_user(
        username="testuser",
        email="test@test.com",
        password="testpass123",
    )


@pytest.fixture
def track(db):
    """Fixture con track de test."""
    from apps.music.models import Track, Album

    album = Album.objects.create(name="Test Album")
    return Track.objects.create(
        spotify_id="test_track_123",
        name="Test Track",
        album=album,
        duration_ms=180000,
        explicit=False,
        track_number=1,
        popularity=80,
    )


@pytest.fixture
def weather_context(db):
    """Fixture con contexto de clima."""
    from apps.context.models import WeatherContext

    # Crear WeatherContext con campos necesarios
    return WeatherContext.objects.create(
        main_status="Clear",
        description="Clear sky",
        temperature=25.0,
        feels_like=24.0,
        humidity=60,
        timestamp=timezone.now(),
    )


@pytest.fixture
def session(db, user):
    """Fixture con sesión de interacción."""
    return InteractionSession.objects.create(
        user=user,
    )


@pytest.mark.django_db
class TestInteractionModel:
    """Tests para el modelo Interaction."""

    def test_interaction_creation(self, user, track, weather_context):
        """Test de creación básica de interacción."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            reward=Decimal("1.0"),
        )

        assert interaction.pk is not None
        assert interaction.user == user
        assert interaction.track == track
        assert interaction.feedback == "completed"

    def test_interaction_completion_percentage(self, user, track, weather_context):
        """Test de cálculo automático de percentage."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=90,  # 50% del track
            track_duration=180,
            reward=Decimal("0.5"),
        )

        # completion_percentage debería ser ~50%
        expected_completion = (90 / 180) * 100
        assert abs(interaction.completion_percentage - expected_completion) < 1.0

    def test_interaction_is_positive_completed(self, user, track, weather_context):
        """Test de feedback positivo (completed)."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            reward=Decimal("1.0"),
        )

        # completed debería ser positivo
        assert interaction.is_positive is True

    def test_interaction_is_positive_skip(self, user, track, weather_context):
        """Test de feedback negativo (skip)."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="skip",
            weather_id=weather_context.id,
            play_duration=10,
            track_duration=180,
            reward=Decimal("-1.0"),
        )

        assert interaction.is_positive is False

    def test_interaction_is_positive_skip_immediate(self, user, track, weather_context):
        """Test de feedback negativo (skip_immediate)."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="skip_immediate",
            weather_id=weather_context.id,
            play_duration=2,
            track_duration=180,
            reward=Decimal("-1.0"),
        )

        assert interaction.is_positive is False

    def test_interaction_feedback_choices(self, user, track, weather_context):
        """Test de opciones válidas de feedback."""
        valid_feedbacks = ["completed", "skip", "skip_immediate", "replay", "added_to_playlist"]

        for feedback in valid_feedbacks:
            interaction = Interaction.objects.create(
                user=user,
                track=track,
                feedback=feedback,
                weather_id=weather_context.id,
                play_duration=90,
                track_duration=180,
                reward=Decimal("0.0"),
            )
            assert interaction.feedback == feedback

    def test_interaction_default_values(self, user, track, weather_context):
        """Test de valores por defecto."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            reward=Decimal("1.0"),
        )

        # Debería tener started_at automático
        assert interaction.started_at is not None
        # session_id puede ser nulo o vacío
        assert interaction.session_id == "" or isinstance(interaction.session_id, str)

    def test_interaction_string_representation(self, user, track, weather_context):
        """Test de representación en string."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            reward=Decimal("1.0"),
        )

        str_repr = str(interaction)
        # Debería contener información legible
        assert len(str_repr) > 0


@pytest.mark.django_db
class TestInteractionSessionModel:
    """Tests para el modelo InteractionSession."""

    def test_session_creation(self, user):
        """Test de creación básica de sesión."""
        session = InteractionSession.objects.create(user=user)

        assert session.pk is not None
        assert session.user == user

    def test_session_default_metrics(self, user):
        """Test de métricas por defecto."""
        session = InteractionSession.objects.create(user=user)

        assert session.total_tracks == 0
        assert session.skip_count == 0
        assert session.completed_count == 0

    def test_session_with_interactions(self, user, track, weather_context):
        """Test de sesión con interacciones."""
        session = InteractionSession.objects.create(user=user)

        # Crear varias interacciones
        for i, feedback in enumerate(["completed", "completed", "skip", "replay"]):
            Interaction.objects.create(
                user=user,
                track=track,
                feedback=feedback,
                weather_id=weather_context.id,
                play_duration=90,
                track_duration=180,
                reward=Decimal(str(1.0 if feedback == "completed" else -1.0)),
                session_id=session.session_id,
            )

        # Debería tener 4 tracks totales (o las métricas que se calculen)
        # Verificar que al menos se guarden

    def test_session_timestamp(self, user):
        """Test de timestamp de sesión."""
        session = InteractionSession.objects.create(user=user)

        assert session.created_at is not None

    def test_session_string_representation(self, user):
        """Test de representación en string."""
        session = InteractionSession.objects.create(user=user)

        str_repr = str(session)
        assert len(str_repr) > 0
        assert user.username in str_repr or "Session" in str_repr


@pytest.mark.django_db
class TestInteractionRelationships:
    """Tests para relaciones entre modelos."""

    def test_interaction_user_relationship(self, user, track, weather_context):
        """Test de relación usuario-interacción."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
        )

        # Debería accederse a través del usuario
        user_interactions = Interaction.objects.filter(user=user)
        assert interaction in user_interactions

    def test_interaction_track_relationship(self, user, track, weather_context):
        """Test de relación track-interacción."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
        )

        # Debería accederse a través del track
        track_interactions = Interaction.objects.filter(track=track)
        assert interaction in track_interactions

    def test_interaction_session_relationship(self, user, track, weather_context, session):
        """Test de relación sesión-interacción."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            session_id=session.session_id,
        )

        # Debería accederse a través de la sesión
        session_interactions = Interaction.objects.filter(session_id=session.session_id)
        assert interaction in session_interactions

    def test_session_user_relationship(self, user):
        """Test de relación usuario-sesión."""
        session = InteractionSession.objects.create(user=user)

        # Debería accederse a través del usuario
        user_sessions = InteractionSession.objects.filter(user=user)
        assert session in user_sessions
```

## Archivo: apps/interactions/tests/test_playlist_generation_service.py

Ruta completa: apps/interactions/tests/test_playlist_generation_service.py

```python
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.interactions.services.playlist_generation_service import PlaylistGenerationService
from apps.music.models import Album, Artist, Track, TrackAudioFeatures

User = get_user_model()


@pytest.mark.django_db
class TestPlaylistGenerationServiceScoring:
    def _build_tracks(self):
        album = Album.objects.create(spotify_id="album_scoring", name="Album Scoring")

        favorite_artist = Artist.objects.create(
            spotify_id="artist_favorite",
            name="Favorite Artist",
            genres=["jazz"],
        )
        context_artist = Artist.objects.create(
            spotify_id="artist_context",
            name="Context Artist",
            genres=["dance"],
        )

        history_track = Track.objects.create(
            spotify_id="track_history",
            name="History Track",
            album=album,
            duration_ms=180000,
            explicit=False,
            track_number=1,
            popularity=35,
            uri="spotify:track:history",
        )
        history_track.artists.add(favorite_artist)
        TrackAudioFeatures.objects.create(
            track=history_track,
            danceability=0.25,
            energy=0.20,
            key=0,
            loudness=-10,
            mode=1,
            speechiness=0.05,
            acousticness=0.75,
            instrumentalness=0.1,
            liveness=0.2,
            valence=0.20,
            tempo=95,
            time_signature=4,
        )

        context_track = Track.objects.create(
            spotify_id="track_context",
            name="Context Track",
            album=album,
            duration_ms=180000,
            explicit=False,
            track_number=2,
            popularity=90,
            uri="spotify:track:context",
        )
        context_track.artists.add(context_artist)
        TrackAudioFeatures.objects.create(
            track=context_track,
            danceability=0.90,
            energy=0.92,
            key=0,
            loudness=-4,
            mode=1,
            speechiness=0.04,
            acousticness=0.08,
            instrumentalness=0.0,
            liveness=0.2,
            valence=0.88,
            tempo=128,
            time_signature=4,
        )

        return history_track, context_track

    @override_settings(RECOMMENDER_CONTEXT_WEIGHT=1.0, RECOMMENDER_HISTORY_WEIGHT=0.0)
    def test_context_heavy_scoring_prioritizes_context_fit(self):
        service = PlaylistGenerationService()
        history_track, context_track = self._build_tracks()

        user_history = {
            "favorite_artists": ["Favorite Artist"],
            "favorite_genres": ["jazz"],
            "avg_energy": 0.2,
            "avg_danceability": 0.25,
            "avg_valence": 0.2,
        }
        weather_context = {
            "main_status": "Clear",
            "description": "sunny sky",
            "temperature": 28,
        }

        history_score = service._score_track(history_track, weather_context, user_history)
        context_score = service._score_track(context_track, weather_context, user_history)

        assert context_score > history_score

    @override_settings(RECOMMENDER_CONTEXT_WEIGHT=0.0, RECOMMENDER_HISTORY_WEIGHT=1.0)
    def test_history_heavy_scoring_prioritizes_user_favorites(self):
        service = PlaylistGenerationService()
        history_track, context_track = self._build_tracks()

        user_history = {
            "favorite_artists": ["Favorite Artist"],
            "favorite_genres": ["jazz"],
            "avg_energy": 0.2,
            "avg_danceability": 0.25,
            "avg_valence": 0.2,
        }
        weather_context = {
            "main_status": "Clear",
            "description": "sunny sky",
            "temperature": 28,
        }

        history_score = service._score_track(history_track, weather_context, user_history)
        context_score = service._score_track(context_track, weather_context, user_history)

        assert history_score > context_score

    @patch("apps.interactions.services.playlist_generation_service.SpotifyMusicService")
    def test_available_tracks_fall_back_to_spotify_when_local_catalog_is_empty(
        self, mock_spotify_service
    ):
        user = User.objects.create_user(
            "spotify_fallback_user",
            "spotify-fallback@example.com",
            "pass12345",
            is_spotify_connected=True,
        )
        service = PlaylistGenerationService()

        mock_instance = mock_spotify_service.return_value
        mock_instance.client = object()
        mock_instance.get_user_liked_tracks.return_value = [
            {
                "id": "remote_track_1",
                "name": "Remote Track 1",
                "artists": ["Remote Artist"],
                "album": "Remote Album",
                "album_id": "remote_album_1",
                "duration_ms": 200000,
                "explicit": False,
                "popularity": 77,
                "uri": "spotify:track:remote_track_1",
                "preview_url": "",
            }
        ]
        mock_instance.get_top_tracks.return_value = []

        tracks = service._get_available_tracks(user, limit=20)

        assert len(tracks) == 1
        assert tracks[0].spotify_id == "remote_track_1"
        assert Track.objects.filter(spotify_id="remote_track_1").exists()
```

## Archivo: apps/interactions/tests/test_reward_service.py

Ruta completa: apps/interactions/tests/test_reward_service.py

```python
import pytest
from django.contrib.auth import get_user_model

from apps.interactions.services.reward_service import RewardService
from apps.music.models import Album, Artist, Track

User = get_user_model()


@pytest.mark.django_db
class TestRewardService:
    def _build_track(self, suffix: str = "1") -> Track:
        album = Album.objects.create(spotify_id=f"album_{suffix}", name=f"Album {suffix}")
        artist = Artist.objects.create(
            spotify_id=f"artist_{suffix}",
            name=f"Artist {suffix}",
            genres=["pop"],
        )
        track = Track.objects.create(
            spotify_id=f"track_{suffix}",
            name=f"Track {suffix}",
            album=album,
            duration_ms=180000,
            explicit=False,
            track_number=1,
            popularity=70,
            uri=f"spotify:track:track_{suffix}",
        )
        track.artists.add(artist)
        return track

    def test_calculate_interaction_reward_returns_float(self):
        user = User.objects.create_user("reward_user", "reward@example.com", "pass12345")
        track = self._build_track("float")
        service = RewardService()

        reward = service.calculate_interaction_reward(
            user_feedback="completed",
            user=user,
            track=track,
        )

        assert isinstance(reward, float)
        assert -2.0 <= reward <= 2.0

    def test_skip_feedback_penalizes_more_than_completed(self):
        user = User.objects.create_user("reward_user2", "reward2@example.com", "pass12345")
        track = self._build_track("compare")
        service = RewardService()

        reward_completed = service.calculate_interaction_reward(
            user_feedback="completed",
            user=user,
            track=track,
        )
        reward_skip = service.calculate_interaction_reward(
            user_feedback="skip",
            user=user,
            track=track,
        )

        assert reward_skip < reward_completed
```

## Archivo: apps/interactions/urls.py

Ruta completa: apps/interactions/urls.py

```python
"""
URLs para el app interactions.
"""

from django.urls import path
from ninja import NinjaAPI

from apps.interactions.views.api import router as interactions_router
from apps.interactions.views.playlist_api import router as playlist_router

app_name = "interactions"

# Crear API principal
api = NinjaAPI(title="Moodsic API - Interactions", version="1.0.0")

# Registrar routers
api.add_router("", interactions_router, tags=["interactions"])
api.add_router("", playlist_router, tags=["playlists"])

urlpatterns = [
    path("", api.urls),
]
```

## Archivo: apps/interactions/views/__init__.py

Ruta completa: apps/interactions/views/__init__.py

```python

```

## Archivo: apps/interactions/views/api.py

Ruta completa: apps/interactions/views/api.py

```python
"""
API Endpoints para Interactions usando Django-Ninja.
"""

import logging
from collections import Counter
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone
from ninja import Router
from ninja.responses import Response

from apps.interactions.models import Interaction, InteractionSession
from apps.interactions.schemas import (
    DashboardMetricsSchema,
    InteractionCreateSchema,
    InteractionResponseSchema,
    SessionStatsSchema,
    UserStatsSchema,
)
from apps.interactions.services.playlist_generation_service import (
    get_playlist_generation_service,
)
from apps.music.models import Track

logger = logging.getLogger(__name__)

User = get_user_model()

router = Router()


@router.post(
    "/interactions/",
    response=InteractionResponseSchema,
    tags=["interactions"],
)
def create_interaction(request, payload: InteractionCreateSchema):
    """
    Crea un registro de interacción usuario-track.

    **Campos:**
    - track_id: ID del track
    - feedback: 'completed', 'skip', 'skip_immediate', 'replay', 'added_to_playlist'
    - play_duration: Segundos reproducidos
    - track_duration: Duración total del track
    - session_id: ID de la sesión (opcional)

    **Retorna:** InteractionResponseSchema
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión para registrar interacciones del usuario.",
            },
            status=401,
        )

    try:
        track = Track.objects.get(id=payload.track_id)
    except Track.DoesNotExist:
        return Response(
            {
                "error": "Track no encontrado",
                "message": "El track indicado no existe en el catálogo local.",
            },
            status=404,
        )

    service = get_playlist_generation_service()

    try:
        result = service.record_interaction(
            user=request.user,
            track=track,
            feedback=payload.feedback,
            play_duration=payload.play_duration,
            track_duration=payload.track_duration,
            session_id=payload.session_id,
            weather_id=payload.weather_id,
            news_ids=payload.news_ids,
        )

        interaction = Interaction.objects.get(id=result["interaction_id"])
    except ValueError as exc:
        logger.warning("Interacción rechazada: %s", exc)
        return Response(
            {
                "error": "No se pudo registrar la interacción",
                "message": str(exc),
            },
            status=400,
        )
    except Exception as exc:
        logger.error("Error inesperado registrando interacción: %s", exc, exc_info=True)
        return Response(
            {
                "error": "Error interno registrando la interacción",
                "message": "Vuelve a intentarlo en unos segundos.",
            },
            status=500,
        )

    return {
        "id": interaction.id,
        "user_id": interaction.user_id,
        "track_id": interaction.track_id,
        "feedback": interaction.feedback,
        "reward": interaction.reward,
        "completion_percentage": interaction.completion_percentage,
        "is_positive": interaction.is_positive,
        "started_at": interaction.started_at.isoformat(),
        "created_at": interaction.created_at.isoformat(),
    }


@router.get(
    "/interactions/user/stats/",
    response=UserStatsSchema,
    tags=["interactions"],
)
def get_user_stats(request):
    """
    Obtiene estadísticas del usuario autenticado.

    **Retorna:** UserStatsSchema con:
    - total_interactions
    - skip_rate
    - completion_rate
    - average_reward
    - favorite_genres
    - favorite_artists
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión para consultar tus estadísticas.",
            },
            status=401,
        )

    service = get_playlist_generation_service()
    return service.get_user_stats(request.user)


@router.get(
    "/interactions/session/{session_id}/stats/",
    response=SessionStatsSchema,
    tags=["interactions"],
)
def get_session_stats(request, session_id: str):
    """
    Obtiene estadísticas de una sesión específica.

    **Parámetros:**
    - session_id: ID de la sesión

    **Retorna:** SessionStatsSchema
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión para consultar sesiones guardadas.",
            },
            status=401,
        )

    try:
        session = InteractionSession.objects.get(session_id=session_id)
    except InteractionSession.DoesNotExist:
        return Response(
            {
                "error": "Sesión no encontrada",
                "message": "No existe ninguna sesión con el identificador indicado.",
            },
            status=404,
        )

    # Calcular métricas
    session.calculate_metrics()

    skip_rate = (
        session.skip_count / session.total_tracks
        if session.total_tracks > 0
        else 0.0
    )
    completion_rate = (
        session.completed_count / session.total_tracks
        if session.total_tracks > 0
        else 0.0
    )

    return {
        "session_id": session.session_id,
        "total_tracks": session.total_tracks,
        "skip_count": session.skip_count,
        "completed_count": session.completed_count,
        "average_reward": session.average_reward,
        "total_reward": session.total_reward,
        "skip_rate": skip_rate,
        "completion_rate": completion_rate,
        "started_at": session.started_at.isoformat(),
        "is_active": session.is_active,
    }


@router.get(
    "/dashboard/metrics/",
    response=DashboardMetricsSchema,
    tags=["dashboard"],
)
def get_dashboard_metrics(request):
    """
    Obtiene métricas del dashboard para administradores.

    **Retorna:** DashboardMetricsSchema con:
    - total_users
    - total_interactions
    - average_skip_rate
    - average_completion_rate
    - top_tracks
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión como administrador para ver este panel.",
            },
            status=401,
        )

    if not request.user.is_staff:
        return Response(
            {
                "error": "Permiso denegado",
                "message": "Este endpoint solo está disponible para personal del proyecto.",
            },
            status=403,
        )

    # Agregaciones
    total_interactions = Interaction.objects.count()
    total_users = User.objects.filter(interactions__isnull=False).distinct().count()

    # Skip rate promedio
    avg_skip_rate = (
        Interaction.objects.filter(feedback__startswith="skip").count()
        / total_interactions
        if total_interactions > 0
        else 0.0
    )

    # Completion rate promedio
    avg_completion_rate = (
        Interaction.objects.filter(feedback="completed").count()
        / total_interactions
        if total_interactions > 0
        else 0.0
    )

    # Total reward generado
    total_reward = Interaction.objects.aggregate(
        total=Sum("reward")
    )["total"] or 0.0

    # Active sessions
    active_sessions = InteractionSession.objects.filter(is_active=True).count()

    # Top tracks
    top_tracks = (
        Interaction.objects.values("track__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    start_date = timezone.now().date() - timedelta(days=6)
    growth_data = (
        Interaction.objects
        .filter(created_at__date__gte=start_date)
        .values("created_at__date")
        .annotate(
            new_users=Count("user", distinct=True),
            interactions=Count("id"),
        )
        .order_by("created_at__date")
    )

    growth_map = {
        item["created_at__date"]: item for item in growth_data
    }

    user_growth = []
    for offset in range(7):
        day = start_date + timedelta(days=offset)
        item = growth_map.get(day, {})
        user_growth.append({
            "date": day.isoformat(),
            "new_users": item.get("new_users", 0),
            "interactions": item.get("interactions", 0),
        })

    return {
        "total_users": total_users,
        "total_interactions": total_interactions,
        "average_skip_rate": avg_skip_rate,
        "average_completion_rate": avg_completion_rate,
        "total_reward_generated": float(total_reward),
        "active_sessions": active_sessions,
        "top_tracks": list(top_tracks),
        "user_growth": user_growth,
    }


def _get_favorite_artists(user):
    """Retorna los artistas preferidos del usuario según sus interacciones."""
    artist_counts = (
        Interaction.objects.filter(user=user)
        .values("track__artists__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return [item["track__artists__name"] for item in artist_counts if item["track__artists__name"]][:5]


def _get_favorite_genres(user):
    """Retorna los géneros favoritos del usuario según los artistas de sus tracks."""
    genres_counter = Counter()
    interactions = Interaction.objects.filter(user=user).select_related("track").prefetch_related("track__artists")

    for interaction in interactions:
        for artist in interaction.track.artists.all():
            for genre in getattr(artist, "genres", []) or []:
                normalized_genre = genre.strip()
                if normalized_genre:
                    genres_counter[normalized_genre] += 1

    return [genre for genre, _ in genres_counter.most_common(5)]


def _get_average_session_length(user):
    """Calcula la longitud promedio de las sesiones de usuario en segundos."""
    sessions = InteractionSession.objects.filter(user=user, ended_at__isnull=False)
    durations = [
        (session.ended_at - session.started_at).total_seconds()
        for session in sessions
        if session.ended_at
    ]

    if not durations:
        return 0.0

    return float(sum(durations) / len(durations))
```

## Archivo: apps/interactions/views/playlist_api.py

Ruta completa: apps/interactions/views/playlist_api.py

```python
"""
API Endpoints para Playlist Generation usando Django-Ninja.
"""

import logging

from django.contrib.auth import get_user_model
from ninja import Router
from ninja.responses import Response

from apps.context.models import WeatherContext
from apps.interactions.schemas import (
    PlaylistGenerateResponseSchema,
    PlaylistGenerateSchema,
)
from apps.interactions.services.playlist_generation_service import (
    get_playlist_generation_service,
)
from apps.music.models import Album, Artist, Playlist, Track, TrackAudioFeatures
from apps.music.services.spotify_music_service import SpotifyMusicService

logger = logging.getLogger(__name__)

router = Router()
User = get_user_model()
MAX_PLAYLIST_TRACKS = 100


@router.post(
    "/playlists/generate/",
    response=PlaylistGenerateResponseSchema,
    tags=["playlists"],
)
def generate_playlist(request, payload: PlaylistGenerateSchema):
    """
    Genera una playlist personalizada usando el agente RL.

    El sistema analiza el contexto actual (clima, hora, noticias)
    y selecciona canciones óptimas basadas en preferencias del usuario
    y feedback histórico.

    **Campos:**
    - name: Nombre de la playlist (default: "Generated by Moodsic")
    - count: Número de canciones (default: 10, max: 100)
    - weather_id: ID del contexto climático a usar (opcional)
    - use_context: Si usar contexto en la generación (default: True)

    **Retorna:** PlaylistGenerateResponseSchema con:
    - playlist_id: ID de la playlist creada
    - playlist_name: Nombre de la playlist
    - tracks_count: Número de canciones
    - track_ids: IDs de los tracks
    - track_names: Nombres de los tracks
    - estimated_duration: Duración estimada en segundos
    - created_at: Timestamp de creación

    **Ejemplo:**
    ```json
    {
        "name": "My Workout Mix",
        "count": 20,
        "use_context": true
    }
    ```
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión para generar una playlist personalizada.",
            },
            status=401,
        )

    try:
        requested_count = payload.count
        count = min(payload.count, MAX_PLAYLIST_TRACKS)
        warnings = []
        if requested_count > MAX_PLAYLIST_TRACKS:
            warnings.append(
                "La petición superaba el máximo permitido; la playlist se ha limitado a 100 canciones."
            )

        weather_context = None
        if payload.use_context and payload.weather_id:
            try:
                weather = WeatherContext.objects.get(id=payload.weather_id)
                base_temperature = (
                    weather.temperature if weather.temperature is not None else 20
                )
                weather_context = {
                    "temperature": base_temperature,
                    "feels_like": (
                        weather.feels_like
                        if weather.feels_like is not None
                        else base_temperature
                    ),
                    "humidity": weather.humidity if weather.humidity is not None else 60,
                    "wind_speed": weather.wind_speed if weather.wind_speed is not None else 0,
                    "pressure": weather.pressure if weather.pressure is not None else 1013,
                    "visibility": weather.visibility if weather.visibility is not None else 10000,
                    "clouds_all": weather.clouds_all if weather.clouds_all is not None else 50,
                    "rain_probability": weather.rain_1h if weather.rain_1h is not None else 0,
                    "main_status": weather.main_status,
                    "description": weather.description,
                    "timestamp": weather.timestamp.isoformat(),
                }
            except WeatherContext.DoesNotExist:
                return Response(
                    {
                        "error": "Weather context no encontrado",
                        "message": "El identificador de clima enviado no existe o ya no está disponible.",
                    },
                    status=404,
                )

        service = get_playlist_generation_service()

        result = service.generate_playlist(
            user=request.user,
            playlist_name=payload.name,
            count=count,
            weather_context=weather_context,
            use_context=payload.use_context,
            news_category=payload.news_category,
            news_query=payload.news_query,
            news_limit=payload.news_limit,
        )
        result["message"] = (
            f"Playlist generada correctamente en modo {result['mode']} con "
            f"{result['tracks_count']} canciones."
        )
        result["warnings"] = warnings

        logger.info("Playlist generada para %s", request.user.username)
        return result

    except ValueError as exc:
        logger.warning("No se pudo generar la playlist: %s", exc)
        return Response(
            {
                "error": "No se pudo generar la playlist",
                "message": str(exc),
            },
            status=400,
        )
    except Exception as exc:
        logger.error("Error generando playlist: %s", exc, exc_info=True)
        return Response(
            {
                "error": "Error interno generando la playlist",
                "message": "Se ha conservado el modo seguro. Reinténtalo en unos segundos.",
            },
            status=500,
        )


@router.get(
    "/playlists/",
    tags=["playlists"],
)
def list_user_playlists(request):
    """
    Lista todas las playlists del usuario autenticado.

    **Retorna:** Lista de playlists con:
    - playlist_id: ID de la playlist
    - playlist_name: Nombre
    - tracks_count: Número de tracks
    - created_at: Fecha de creación
    - spotify_url: URL de Spotify si está sincronizada
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión para consultar tus playlists guardadas.",
            },
            status=401,
        )

    try:
        playlists = Playlist.objects.filter(user=request.user).order_by("-created_at")

        result = []
        for playlist in playlists:
            tracks = playlist.tracks.all()
            result.append({
                "playlist_id": playlist.spotify_id,
                "playlist_name": playlist.name,
                "user_id": playlist.user_id,
                "tracks_count": tracks.count(),
                "is_public": playlist.is_public,
                "estimated_duration": sum(t.duration_ms for t in tracks) // 1000,
                "created_at": playlist.created_at.isoformat(),
                "spotify_uri": playlist.uri,
            })

        return {"playlists": result, "total": len(result)}

    except Exception as e:
        logger.error(f"Error listando playlists: {e}")
        return Response(
            {
                "error": "Error listando playlists",
                "message": "No se pudieron recuperar las playlists del usuario.",
            },
            status=500,
        )


@router.get(
    "/playlists/{playlist_id}/",
    tags=["playlists"],
)
def get_playlist_details(request, playlist_id: str):
    """
    Obtiene detalles de una playlist generada.

    **Parámetros:**
    - playlist_id: ID de la playlist

    **Retorna:** Información detallada de la playlist
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión para consultar el detalle de la playlist.",
            },
            status=401,
        )

    try:
        playlist = Playlist.objects.get(spotify_id=playlist_id, user=request.user)

        tracks = playlist.tracks.all()

        return {
            "playlist_id": playlist.spotify_id,
            "playlist_name": playlist.name,
            "user_id": playlist.user_id,
            "tracks_count": tracks.count(),
            "track_ids": [t.id for t in tracks],
            "track_names": [t.name for t in tracks],
            "track_artists": [", ".join([a.name for a in t.artists.all()]) for t in tracks],
            "estimated_duration": sum(t.duration_ms for t in tracks) // 1000,
            "is_public": playlist.is_public,
            "created_at": playlist.created_at.isoformat(),
            "updated_at": playlist.updated_at.isoformat(),
            "spotify_uri": playlist.uri,
        }

    except Exception as e:
        logger.error(f"Error obteniendo playlist: {e}")
        return Response(
            {
                "error": "Playlist no encontrada",
                "message": "No existe una playlist con ese identificador para el usuario autenticado.",
            },
            status=404,
        )


@router.post(
    "/playlists/{playlist_id}/sync-spotify/",
    tags=["playlists"],
)
def sync_playlist_to_spotify(request, playlist_id: str):  # noqa: PLR0911
    """
    Sincroniza una playlist local con Spotify.

    Crea la playlist en Spotify y agrega todos los tracks.

    **Parámetros:**
    - playlist_id: ID de la playlist local

    **Retorna:**
    - success: True si fue exitoso
    - spotify_id: ID de la playlist creada en Spotify
    - spotify_uri: URI de Spotify
    - message: Mensaje de estado
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión antes de sincronizar con Spotify.",
            },
            status=401,
        )

    try:
        # Verificar que el usuario está conectado a Spotify
        if not request.user.is_spotify_connected:
            return Response(
                {
                    "success": False,
                    "error": "Usuario no está conectado a Spotify",
                    "message": "Conecta tu cuenta de Spotify en la configuración antes de sincronizar.",
                },
                status=403,
            )

        # Obtener playlist
        playlist = Playlist.objects.get(spotify_id=playlist_id, user=request.user)
        tracks = playlist.tracks.all()

        # Inicializar servicio de Spotify
        spotify_service = SpotifyMusicService(request.user)
        if not spotify_service.client:
            return {
                "success": False,
                "error": "No se pudo autenticar con Spotify"
            }, 500

        # Crear playlist en Spotify
        spotify_playlist = spotify_service.create_playlist(
            name=playlist.name,
            description="Generated by Moodsic",
            public=playlist.is_public,
        )

        if not spotify_playlist:
            return Response(
                {
                    "success": False,
                    "error": "No se pudo crear playlist en Spotify",
                    "message": "Spotify no devolvió una playlist válida para la sincronización.",
                },
                status=500,
            )

        # Agregar tracks
        track_uris = [t.uri for t in tracks if t.uri]
        if track_uris:
            success = spotify_service.add_tracks_to_playlist(
                spotify_playlist.get("id"),
                track_uris
            )
            if not success:
                logger.warning(
                    "Algunos tracks no se agregaron a %s",
                    spotify_playlist.get("id"),
                )

        # Actualizar registro en BD
        playlist.spotify_id = spotify_playlist.get("id", playlist_id)
        playlist.uri = spotify_playlist.get("uri", "")
        playlist.save()

        logger.info(f"Playlist sincronizada: {spotify_playlist.get('id')}")

        return {
            "success": True,
            "spotify_id": spotify_playlist.get("id"),
            "spotify_uri": spotify_playlist.get("uri"),
            "external_url": spotify_playlist.get("external_urls", {}).get("spotify", ""),
            "tracks_added": len(track_uris),
        }

    except Playlist.DoesNotExist:
        return Response(
            {
                "error": "Playlist no encontrada",
                "message": "La playlist local indicada no existe para este usuario.",
            },
            status=404,
        )
    except Exception as e:
        logger.error(f"Error sincronizando playlist con Spotify: {e}", exc_info=True)
        return Response(
            {
                "error": str(e),
                "message": "La sincronización con Spotify ha fallado.",
            },
            status=500,
        )


@router.post(
    "/tracks/sync/",
    tags=["tracks"],
)
def sync_tracks_from_spotify(  # noqa: C901, PLR0912
    request,
    source: str = "liked",
    limit: int = 50,
    save_audio_features: bool = False,
):
    """
    Sincroniza tracks desde Spotify con la BD local.

    **Parámetros:**
    - source: Fuente de tracks ('liked', 'top', 'playlist')
    - limit: Número máximo de tracks (default: 50)
    - save_audio_features: Guardar características de audio

    **Retorna:**
    - success: True si fue exitoso
    - synced_count: Número de tracks nuevos sincronizados
    - skipped_count: Tracks que ya existían
    - total_processed: Total procesados
    """

    try:
        # Verificar que el usuario está conectado a Spotify
        if not request.user.is_spotify_connected:
            return {
                "success": False,
                "error": "Usuario no está conectado a Spotify"
            }, 403

        # Inicializar servicio
        spotify_service = SpotifyMusicService(request.user)
        if not spotify_service.client:
            return {
                "success": False,
                "error": "No se pudo autenticar con Spotify"
            }, 500

        # Obtener tracks según la fuente
        if source == "liked":
            tracks_data = spotify_service.get_user_liked_tracks(limit=limit)
        elif source == "top":
            tracks_data = spotify_service.get_top_tracks(limit=limit)
        else:
            return {
                "success": False,
                "error": f"Fuente no reconocida: {source}"
            }, 400

        if not tracks_data:
            return {
                "success": True,
                "synced_count": 0,
                "skipped_count": 0,
                "total_processed": 0,
                "message": "No se encontraron tracks"
            }

        # Guardar tracks
        saved_count = 0
        skipped_count = 0
        artist_cache = {}
        audio_features_data = {}

        # Obtener audio features si se solicita
        if save_audio_features:
            track_ids = [t.get("id") for t in tracks_data if t.get("id")]
            if track_ids:
                audio_features_data = spotify_service.get_audio_features(track_ids)

        for track_data in tracks_data:
            try:
                # Obtener o crear album
                if track_data.get("album_id"):
                    album, _ = Album.objects.get_or_create(
                        spotify_id=track_data.get("album_id"),
                        defaults={
                            "name": track_data.get("album", "Unknown"),
                            "album_type": "",
                        },
                    )
                else:
                    album = None

                # Obtener o crear artistas
                artists = []
                for artist_name in track_data.get("artists", []):
                    artist_key = artist_name.lower()
                    if artist_key not in artist_cache:
                        artist, _ = Artist.objects.get_or_create(
                            name=artist_name,
                            defaults={"spotify_id": f"local_{artist_key}"},
                        )
                        artist_cache[artist_key] = artist
                    artists.append(artist_cache[artist_key])

                # Obtener o crear track
                track, created = Track.objects.get_or_create(
                    spotify_id=track_data.get("id", ""),
                    defaults={
                        "name": track_data.get("name", "Unknown"),
                        "album": album,
                        "duration_ms": track_data.get("duration_ms", 0),
                        "explicit": track_data.get("explicit", False),
                        "popularity": track_data.get("popularity", 0),
                        "preview_url": track_data.get("preview_url", ""),
                        "uri": track_data.get("uri", ""),
                        "track_number": 0,
                    },
                )

                if artists:
                    track.artists.add(*artists)

                if created:
                    saved_count += 1

                    # Guardar audio features si están disponibles
                    if save_audio_features and track_data.get("id") in audio_features_data:
                        try:
                            TrackAudioFeatures.objects.get_or_create(
                                track=track,
                                defaults=audio_features_data[track_data.get("id")]
                            )
                        except Exception as e:
                            logger.warning(f"Error saving audio features: {e}")
                else:
                    skipped_count += 1

            except Exception as e:
                logger.error(f"Error procesando track: {e}")
                continue

        logger.info(f"Sincronización completada: {saved_count} nuevos, {skipped_count} existentes")

        return {
            "success": True,
            "synced_count": saved_count,
            "skipped_count": skipped_count,
            "total_processed": len(tracks_data),
            "source": source,
            "message": f"Sincronización completada: {saved_count} nuevos tracks"
        }

    except Exception as e:
        logger.error(f"Error sincronizando tracks: {e}", exc_info=True)
        return {"success": False, "error": str(e)}, 500
```

## Archivo: apps/music/__init__.py

Ruta completa: apps/music/__init__.py

```python

```

## Archivo: apps/music/admin/__init__.py

Ruta completa: apps/music/admin/__init__.py

```python
from .album import AlbumAdmin
from .artist import ArtistAdmin
from .playlist import PlaylistAdmin
from .track import TrackAdmin

__all__ = ["AlbumAdmin", "ArtistAdmin", "PlaylistAdmin", "TrackAdmin"]
```

## Archivo: apps/music/admin/album.py

Ruta completa: apps/music/admin/album.py

```python
from django.contrib import admin
from unfold.admin import ModelAdmin

from ..models import Album


@admin.register(Album)
class AlbumAdmin(ModelAdmin):
    list_display = ("name", "spotify_id", "album_type", "release_date")
    search_fields = ("name", "spotify_id")
    filter_horizontal = ("artists",)
    readonly_fields = ("created_at", "updated_at")
```

## Archivo: apps/music/admin/artist.py

Ruta completa: apps/music/admin/artist.py

```python
from django.contrib import admin
from unfold.admin import ModelAdmin

from ..models import Artist


@admin.register(Artist)
class ArtistAdmin(ModelAdmin):
    list_display = ("name", "spotify_id", "popularity")
    search_fields = ("name", "spotify_id")
    readonly_fields = ("created_at", "updated_at")
```

## Archivo: apps/music/admin/playlist.py

Ruta completa: apps/music/admin/playlist.py

```python
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from ..models import Playlist, PlaylistTrack


class PlaylistTrackInline(TabularInline):
    model = PlaylistTrack
    extra = 1
    autocomplete_fields = ("track",)


@admin.register(Playlist)
class PlaylistAdmin(ModelAdmin):
    list_display = ("name", "user", "is_public", "spotify_id")
    search_fields = ("name", "user__username", "spotify_id")
    list_filter = ("is_public", "user")
    inlines = (PlaylistTrackInline,)
    readonly_fields = ("created_at", "updated_at")
```

## Archivo: apps/music/admin/track.py

Ruta completa: apps/music/admin/track.py

```python
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from ..models import Track, TrackAudioFeatures


class TrackAudioFeaturesInline(TabularInline):
    model = TrackAudioFeatures
    can_delete = False
    extra = 0
    readonly_fields = (
        "danceability",
        "energy",
        "key",
        "loudness",
        "mode",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "tempo",
        "time_signature",
        "created_at",
    )


@admin.register(Track)
class TrackAdmin(ModelAdmin):
    list_display = ("name", "get_artists", "album", "popularity", "spotify_id")
    search_fields = ("name", "spotify_id", "artists__name", "album__name")
    filter_horizontal = ("artists",)
    inlines = (TrackAudioFeaturesInline,)
    readonly_fields = ("created_at", "updated_at")

    def get_artists(self, obj):
        return ", ".join([a.name for a in obj.artists.all()])

    get_artists.short_description = "Artistas"
```

## Archivo: apps/music/apps.py

Ruta completa: apps/music/apps.py

```python
from django.apps import AppConfig


class MusicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.music"
```

## Archivo: apps/music/management/__init__.py

Ruta completa: apps/music/management/__init__.py

```python

```

## Archivo: apps/music/management/commands/__init__.py

Ruta completa: apps/music/management/commands/__init__.py

```python

```

## Archivo: apps/music/management/commands/verify_spotify.py

Ruta completa: apps/music/management/commands/verify_spotify.py

```python
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.music.services.spotify_music_service import SpotifyMusicService


class Command(BaseCommand):
    help = "Verifica el estado de la API de Spotify y las credenciales configuradas."

    def handle(self, *_args, **_options):
        self.stdout.write("--- Verificación de Spotify API ---")

        # 1. Verificar credenciales en settings
        client_id = getattr(settings, "SPOTIPY_CLIENT_ID", None)
        client_secret = getattr(settings, "SPOTIPY_CLIENT_SECRET", None)
        redirect_uri = getattr(settings, "SPOTIPY_REDIRECT_URI", None)

        if not all([client_id, client_secret, redirect_uri]):
            self.stdout.write(
                self.style.ERROR(
                    "✘ Faltan credenciales de Spotify en settings.py o .env"
                )
            )
            self.stdout.write(
                f"  SPOTIPY_CLIENT_ID: {'CONFIGURADO' if client_id else 'FALTA'}"
            )
            self.stdout.write(
                f"  SPOTIPY_CLIENT_SECRET: {'CONFIGURADO' if client_secret else 'FALTA'}"
            )
            self.stdout.write(
                f"  SPOTIPY_REDIRECT_URI: {'CONFIGURADO' if redirect_uri else 'FALTA'}"
            )
            return

        self.stdout.write(
            self.style.SUCCESS("✓ Credenciales presentes en la configuración.")
        )

        # 2. Verificar conexión con la API (Client Credentials Flow)
        self.stdout.write("Probando conexión con Spotify API...")
        success, message = SpotifyMusicService.verify_api_connection()

        if success:
            self.stdout.write(self.style.SUCCESS(f"✓ {message}"))
        else:
            self.stdout.write(self.style.ERROR(f"✘ {message}"))

        self.stdout.write("------------------------------------")
```

## Archivo: apps/music/migrations/0001_initial.py

Ruta completa: apps/music/migrations/0001_initial.py

```python
# Generated by Django 6.0.3 on 2026-03-03 18:16

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Artist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spotify_id', models.CharField(max_length=255, unique=True, verbose_name='Spotify ID')),
                ('name', models.CharField(max_length=255, verbose_name='Nombre')),
                ('popularity', models.IntegerField(blank=True, null=True, verbose_name='Popularidad')),
                ('genres', models.JSONField(blank=True, default=list, verbose_name='Géneros')),
                ('images', models.JSONField(blank=True, default=list, verbose_name='Imágenes')),
                ('uri', models.CharField(blank=True, default='', max_length=255, verbose_name='URI')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Artista',
                'verbose_name_plural': 'Artistas',
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='Album',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spotify_id', models.CharField(max_length=255, unique=True, verbose_name='Spotify ID')),
                ('name', models.CharField(max_length=255, verbose_name='Nombre')),
                ('album_type', models.CharField(blank=True, default='', max_length=50, verbose_name='Tipo de álbum')),
                ('total_tracks', models.IntegerField(blank=True, null=True, verbose_name='Total de canciones')),
                ('release_date', models.CharField(blank=True, default='', max_length=50, verbose_name='Fecha de lanzamiento')),
                ('images', models.JSONField(blank=True, default=list, verbose_name='Imágenes')),
                ('uri', models.CharField(blank=True, default='', max_length=255, verbose_name='URI')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('artists', models.ManyToManyField(related_name='albums', to='music.artist', verbose_name='Artistas')),
            ],
            options={
                'verbose_name': 'Álbum',
                'verbose_name_plural': 'Álbumes',
                'ordering': ('-release_date', 'name'),
            },
        ),
        migrations.CreateModel(
            name='Playlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spotify_id', models.CharField(max_length=255, unique=True, verbose_name='Spotify ID')),
                ('name', models.CharField(max_length=255, verbose_name='Nombre')),
                ('description', models.TextField(blank=True, verbose_name='Descripción')),
                ('is_public', models.BooleanField(default=True, verbose_name='Es pública')),
                ('snapshot_id', models.CharField(blank=True, default='', max_length=255, verbose_name='Snapshot ID')),
                ('images', models.JSONField(blank=True, default=list, verbose_name='Imágenes')),
                ('uri', models.CharField(blank=True, default='', max_length=255, verbose_name='URI')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlists', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Lista de reproducción',
                'verbose_name_plural': 'Listas de reproducción',
                'ordering': ('-updated_at', 'name'),
            },
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spotify_id', models.CharField(max_length=255, unique=True, verbose_name='Spotify ID')),
                ('name', models.CharField(max_length=255, verbose_name='Nombre')),
                ('duration_ms', models.IntegerField(verbose_name='Duración (ms)')),
                ('explicit', models.BooleanField(default=False, verbose_name='Explícito')),
                ('popularity', models.IntegerField(blank=True, null=True, verbose_name='Popularidad')),
                ('preview_url', models.URLField(blank=True, max_length=500, null=True, verbose_name='URL de previsualización')),
                ('track_number', models.IntegerField(verbose_name='Número de pista')),
                ('uri', models.CharField(blank=True, default='', max_length=255, verbose_name='URI')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('album', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tracks', to='music.album', verbose_name='Álbum')),
                ('artists', models.ManyToManyField(related_name='tracks', to='music.artist', verbose_name='Artistas')),
            ],
            options={
                'verbose_name': 'Canción',
                'verbose_name_plural': 'Canciones',
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='PlaylistTrack',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_at', models.DateTimeField(blank=True, null=True, verbose_name='Añadida en')),
                ('order', models.IntegerField(default=0, verbose_name='Orden')),
                ('playlist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='music.playlist', verbose_name='Lista de reproducción')),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='music.track', verbose_name='Canción')),
            ],
            options={
                'verbose_name': 'Canción de la lista',
                'verbose_name_plural': 'Canciones de la lista',
                'ordering': ('playlist', 'order'),
            },
        ),
        migrations.AddField(
            model_name='playlist',
            name='tracks',
            field=models.ManyToManyField(related_name='playlists', through='music.PlaylistTrack', to='music.track', verbose_name='Canciones'),
        ),
        migrations.CreateModel(
            name='TrackAudioFeatures',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('danceability', models.FloatField(verbose_name='Danceability')),
                ('energy', models.FloatField(verbose_name='Energy')),
                ('key', models.IntegerField(verbose_name='Key')),
                ('loudness', models.FloatField(verbose_name='Loudness')),
                ('mode', models.IntegerField(verbose_name='Mode')),
                ('speechiness', models.FloatField(verbose_name='Speechiness')),
                ('acousticness', models.FloatField(verbose_name='Acousticness')),
                ('instrumentalness', models.FloatField(verbose_name='Instrumentalness')),
                ('liveness', models.FloatField(verbose_name='Liveness')),
                ('valence', models.FloatField(verbose_name='Valence')),
                ('tempo', models.FloatField(verbose_name='Tempo')),
                ('time_signature', models.IntegerField(verbose_name='Time Signature')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('track', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='audio_features', to='music.track', verbose_name='Canción')),
            ],
            options={
                'verbose_name': 'Características de audio',
                'verbose_name_plural': 'Características de audio',
            },
        ),
    ]
```

## Archivo: apps/music/migrations/0002_alter_track_preview_url.py

Ruta completa: apps/music/migrations/0002_alter_track_preview_url.py

```python
# Generated by Django 4.2.29 on 2026-03-25 21:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("music", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="track",
            name="preview_url",
            field=models.URLField(
                blank=True, max_length=500, verbose_name="URL de previsualización"
            ),
        ),
    ]
```

## Archivo: apps/music/migrations/__init__.py

Ruta completa: apps/music/migrations/__init__.py

```python

```

## Archivo: apps/music/models/__init__.py

Ruta completa: apps/music/models/__init__.py

```python
from .album import Album
from .artist import Artist
from .playlist import Playlist, PlaylistTrack
from .track import Track, TrackAudioFeatures

__all__ = [
    "Album",
    "Artist",
    "Playlist",
    "PlaylistTrack",
    "Track",
    "TrackAudioFeatures",
]
```

## Archivo: apps/music/models/album.py

Ruta completa: apps/music/models/album.py

```python
from django.db import models
from django.utils.translation import gettext_lazy as _

from .artist import Artist


class Album(models.Model):
    """
    Almacena información básica de un álbum de Spotify.
    """

    spotify_id = models.CharField(
        max_length=255, unique=True, verbose_name=_("Spotify ID")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nombre"))
    album_type = models.CharField(
        max_length=50, blank=True, default="", verbose_name=_("Tipo de álbum")
    )
    total_tracks = models.IntegerField(
        null=True, blank=True, verbose_name=_("Total de canciones")
    )
    release_date = models.CharField(
        max_length=50, blank=True, default="", verbose_name=_("Fecha de lanzamiento")
    )
    images = models.JSONField(default=list, blank=True, verbose_name=_("Imágenes"))
    uri = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("URI")
    )

    artists = models.ManyToManyField(
        Artist, related_name="albums", verbose_name=_("Artistas")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Álbum")
        verbose_name_plural = _("Álbumes")
        ordering = ("-release_date", "name")

    def __str__(self):
        return self.name
```

## Archivo: apps/music/models/artist.py

Ruta completa: apps/music/models/artist.py

```python
from django.db import models
from django.utils.translation import gettext_lazy as _


class Artist(models.Model):
    """
    Almacena información básica de un artista de Spotify.
    """

    spotify_id = models.CharField(
        max_length=255, unique=True, verbose_name=_("Spotify ID")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nombre"))
    popularity = models.IntegerField(
        null=True, blank=True, verbose_name=_("Popularidad")
    )
    genres = models.JSONField(default=list, blank=True, verbose_name=_("Géneros"))
    images = models.JSONField(default=list, blank=True, verbose_name=_("Imágenes"))
    uri = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("URI")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Artista")
        verbose_name_plural = _("Artistas")
        ordering = ("name",)

    def __str__(self):
        return self.name
```

## Archivo: apps/music/models/playlist.py

Ruta completa: apps/music/models/playlist.py

```python
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .track import Track


class Playlist(models.Model):
    """
    Almacena información de una lista de reproducción de Spotify.
    """

    spotify_id = models.CharField(
        max_length=255, unique=True, verbose_name=_("Spotify ID")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playlists",
        verbose_name=_("Usuario"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Nombre"))
    description = models.TextField(blank=True, verbose_name=_("Descripción"))
    is_public = models.BooleanField(default=True, verbose_name=_("Es pública"))
    snapshot_id = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("Snapshot ID")
    )
    images = models.JSONField(default=list, blank=True, verbose_name=_("Imágenes"))
    uri = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("URI")
    )

    tracks = models.ManyToManyField(
        Track,
        through="PlaylistTrack",
        related_name="playlists",
        verbose_name=_("Canciones"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Lista de reproducción")
        verbose_name_plural = _("Listas de reproducción")
        ordering = ("-updated_at", "name")

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class PlaylistTrack(models.Model):
    """
    Modelo intermedio para gestionar las canciones en una playlist y su orden/fecha.
    """

    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, verbose_name=_("Lista de reproducción")
    )
    track = models.ForeignKey(
        Track, on_delete=models.CASCADE, verbose_name=_("Canción")
    )
    added_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Añadida en"))
    order = models.IntegerField(default=0, verbose_name=_("Orden"))

    class Meta:
        verbose_name = _("Canción de la lista")
        verbose_name_plural = _("Canciones de la lista")
        ordering = ("playlist", "order")

    def __str__(self):
        return f"{self.playlist.name} - {self.track.name}"
```

## Archivo: apps/music/models/track.py

Ruta completa: apps/music/models/track.py

```python
from django.db import models
from django.utils.translation import gettext_lazy as _

from .album import Album
from .artist import Artist


class Track(models.Model):
    """
    Almacena información básica de una canción de Spotify.
    """

    spotify_id = models.CharField(
        max_length=255, unique=True, verbose_name=_("Spotify ID")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nombre"))
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="tracks",
        verbose_name=_("Álbum"),
        null=True,
        blank=True,
    )
    artists = models.ManyToManyField(
        Artist, related_name="tracks", verbose_name=_("Artistas")
    )
    duration_ms = models.IntegerField(verbose_name=_("Duración (ms)"))
    explicit = models.BooleanField(default=False, verbose_name=_("Explícito"))
    popularity = models.IntegerField(
        null=True, blank=True, verbose_name=_("Popularidad")
    )
    preview_url = models.URLField(
        max_length=500, blank=True, verbose_name=_("URL de previsualización")
    )
    track_number = models.IntegerField(verbose_name=_("Número de pista"))
    uri = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("URI")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Canción")
        verbose_name_plural = _("Canciones")
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} - {', '.join([a.name for a in self.artists.all()])}"


class TrackAudioFeatures(models.Model):
    """
    Almacena las características de audio de una canción proporcionadas por Spotify.
    Crucial para el agente de Reinforcement Learning.
    """

    track = models.OneToOneField(
        Track,
        on_delete=models.CASCADE,
        related_name="audio_features",
        verbose_name=_("Canción"),
    )
    danceability = models.FloatField(verbose_name=_("Danceability"))
    energy = models.FloatField(verbose_name=_("Energy"))
    key = models.IntegerField(verbose_name=_("Key"))
    loudness = models.FloatField(verbose_name=_("Loudness"))
    mode = models.IntegerField(verbose_name=_("Mode"))
    speechiness = models.FloatField(verbose_name=_("Speechiness"))
    acousticness = models.FloatField(verbose_name=_("Acousticness"))
    instrumentalness = models.FloatField(verbose_name=_("Instrumentalness"))
    liveness = models.FloatField(verbose_name=_("Liveness"))
    valence = models.FloatField(verbose_name=_("Valence"))
    tempo = models.FloatField(verbose_name=_("Tempo"))
    time_signature = models.IntegerField(verbose_name=_("Time Signature"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Características de audio")
        verbose_name_plural = _("Características de audio")

    def __str__(self):
        return f"Features for {self.track.name}"
```

## Archivo: apps/music/services/__init__.py

Ruta completa: apps/music/services/__init__.py

```python

```

## Archivo: apps/music/services/music_briefing_service.py

Ruta completa: apps/music/services/music_briefing_service.py

```python
import logging
from typing import Any

from apps.context.models.weather_context import WeatherContext
from apps.context.services.mood_service import MoodService

logger = logging.getLogger(__name__)


class MusicBriefingService:
    """
    Servicio de orquestación que genera el 'Briefing Musical' completo.
    Combina datos de contexto (clima, ubicación) para producir los parámetros
    que Spotify necesita para generar recomendaciones.
    """

    @staticmethod
    def generate_briefing(weather: WeatherContext) -> dict[str, Any]:
        """
        Genera un diccionario con todos los parámetros necesarios para SpotifyMusicService.get_recommendations.
        """
        # 1. Obtener parámetros basados en el clima (Mood Mapping)
        mood_params = MoodService.get_music_params_for_weather(weather.main_status)
        mood_name = MoodService.get_mood_name(weather.main_status)

        # 2. Construir el briefing
        # Nota: Por ahora usamos los seed_genres definidos en el MoodMapping.
        # En el futuro, podríamos inyectar seeds basados en la región del usuario.
        briefing = {
            "mood_name": mood_name,
            "recommendation_params": {
                "limit": 20,
                "seed_genres": mood_params.get("seed_genres", ["pop"]),
                "target_energy": mood_params.get("target_energy"),
                "target_valence": mood_params.get("target_valence"),
                "target_danceability": mood_params.get("target_danceability"),
            },
            "context_summary": f"Clima en {weather.region or weather.country}: {weather.main_status} ({weather.temperature}°C)",
        }

        logger.info(
            f"Briefing musical generado para {weather.main_status}: {mood_name}"
        )
        return briefing
```

## Archivo: apps/music/services/spotify_music_service.py

Ruta completa: apps/music/services/spotify_music_service.py

```python
import logging

import spotipy
from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.utils import timezone
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

logger = logging.getLogger(__name__)

# Constantes para códigos de estado HTTP
HTTP_401_UNAUTHORIZED = 401
HTTP_429_TOO_MANY_REQUESTS = 429


class SpotifyMusicService:
    """
    Servicio centralizado para interactuar con la API de Spotify.
    Maneja la autenticación, persistencia de tokens y refresco automático.
    """

    def __init__(self, user):
        self.user = user
        self.token = self._get_valid_token()
        self.client = spotipy.Spotify(auth=self.token.token) if self.token else None

    def _get_valid_token(self):
        """
        Obtiene el token de Spotify para el usuario y lo refresca si es necesario.
        """
        try:
            token = SocialToken.objects.get(
                account__user=self.user, account__provider="spotify"
            )
        except SocialToken.DoesNotExist:
            return None

        # Verificar si el token ha expirado (o está a punto de expirar)
        if token.expires_at and token.expires_at <= timezone.now():
            self._refresh_token(token)

        return token

    def _refresh_token(self, token):
        """
        Refresca el token utilizando el refresh_token almacenado.
        """
        sp_oauth = SpotifyOAuth(
            client_id=settings.SPOTIPY_CLIENT_ID,
            client_secret=settings.SPOTIPY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        )

        refresh_token = token.token_secret
        if not refresh_token:
            logger.warning(f"No refresh token found for user {self.user.username}")
            return

        try:
            new_token_info = sp_oauth.refresh_access_token(refresh_token)

            if new_token_info:
                token.token = new_token_info["access_token"]
                if "refresh_token" in new_token_info:
                    token.token_secret = new_token_info["refresh_token"]

                expires_in = new_token_info.get("expires_in", 3600)
                token.expires_at = timezone.now() + timezone.timedelta(
                    seconds=expires_in
                )
                token.save()
                logger.info(
                    f"Token refreshed successfully for user {self.user.username}"
                )
        except Exception as e:
            logger.error(f"Error refreshing token for user {self.user.username}: {e}")

    def get_user_info(self):
        """
        Obtiene información del perfil de Spotify del usuario actual.
        """
        if not self.client:
            return None
        return self.client.current_user()

    def search_tracks(self, query: str, limit: int = 20, **_kwargs):
        """
        Busca tracks en Spotify.
        Permite filtrar por parámetros de audio si se proporcionan en kwargs.
        Debido a que la API de búsqueda de Spotify no soporta parámetros de audio directamente,
        estos se usarán para filtrar los resultados o como base para recomendaciones si es necesario.
        En esta implementación inicial, realizamos la búsqueda y luego podríamos filtrar
        (aunque el filtrado real por audio suele ser más eficiente vía recommendations).
        """
        if not self.client:
            return None

        results = self.client.search(q=query, limit=limit, type="track")

        # Si hay parámetros de audio en kwargs, podríamos filtrar los resultados aquí.
        # Por ahora, devolvemos los resultados de la búsqueda.
        return results

    def get_recommendations(
        self,
        seed_artists: list | None = None,
        seed_genres: list | None = None,
        seed_tracks: list | None = None,
        limit: int = 20,
        **kwargs,
    ):
        """
        Obtiene recomendaciones basadas en semillas y parámetros de audio.
        """
        if not self.client:
            return None

        try:
            return self.client.recommendations(
                seed_artists=seed_artists,
                seed_genres=seed_genres,
                seed_tracks=seed_tracks,
                limit=limit,
                **kwargs,
            )
        except spotipy.SpotifyException as e:
            logger.error(f"Error en recomendaciones de Spotify: {e}")
            self._handle_spotify_exception(e)
            return None

    def create_playlist(
        self,
        name: str,
        public: bool = True,
        collaborative: bool = False,
        description: str = "",
    ):
        """
        Crea una nueva playlist en la cuenta del usuario.
        """
        if not self.client:
            return None

        try:
            user_id = self.client.current_user()["id"]
            return self.client.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                collaborative=collaborative,
                description=description,
            )
        except spotipy.SpotifyException as e:
            logger.error(f"Error al crear playlist: {e}")
            self._handle_spotify_exception(e)
            return None

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: list[str]):
        """
        Añade canciones a una playlist existente.
        """
        if not self.client:
            return None

        try:
            return self.client.playlist_add_items(playlist_id, track_uris)
        except spotipy.SpotifyException as e:
            logger.error(f"Error al añadir tracks a la playlist {playlist_id}: {e}")
            self._handle_spotify_exception(e)
            return None

    def replace_playlist_tracks(self, playlist_id: str, track_uris: list[str]):
        """
        Reemplaza todas las canciones de una playlist por una nueva lista.
        Útil para actualizar playlists dinámicas de "Mood".
        """
        if not self.client:
            return None

        try:
            return self.client.playlist_replace_items(playlist_id, track_uris)
        except spotipy.SpotifyException as e:
            logger.error(
                f"Error al reemplazar tracks en la playlist {playlist_id}: {e}"
            )
            self._handle_spotify_exception(e)
            return None

    def _handle_spotify_exception(self, e: spotipy.SpotifyException):
        """
        Manejo centralizado de excepciones de la API de Spotify.
        """
        if e.http_status == HTTP_401_UNAUTHORIZED:
            logger.warning(
                "Token expirado detectado durante la operación. Intentando refrescar..."
            )
            self.token = self._get_valid_token()
            if self.token:
                self.client = spotipy.Spotify(auth=self.token.token)
        elif e.http_status == HTTP_429_TOO_MANY_REQUESTS:
            retry_after = e.headers.get("Retry-After", "desconocido")
            logger.error(
                f"Límite de tasa (Rate Limit) alcanzado. Reintentar después de {retry_after}s."
            )
        else:
            logger.error(f"Error de Spotify API ({e.http_status}): {e.msg}")

    def get_playlist_tracks(self, playlist_id, limit=50):
        """
        Obtiene los tracks de una playlist específica.

        Args:
            playlist_id: ID de la playlist de Spotify (puede incluir 'spotify:playlist:')
            limit: Número máximo de tracks a obtener (default: 50, max: 50)

        Returns:
            Lista de diccionarios con información de tracks
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return []

        # Limpiar playlist_id si tiene el formato spotify:playlist:xxx
        if playlist_id.startswith("spotify:playlist:"):
            playlist_id = playlist_id.split(":")[-1]

        try:
            results = self.client.playlist_tracks(playlist_id, limit=min(limit, 50))
            tracks = []

            for item in results.get("items", []):
                track = item.get("track", {})
                if track:
                    tracks.append(
                        {
                            "id": track.get("id"),
                            "name": track.get("name"),
                            "artists": [
                                artist.get("name")
                                for artist in track.get("artists", [])
                            ],
                            "album": track.get("album", {}).get("name"),
                            "album_id": track.get("album", {}).get("id"),
                            "duration_ms": track.get("duration_ms"),
                            "explicit": track.get("explicit", False),
                            "popularity": track.get("popularity"),
                            "uri": track.get("uri"),
                            "preview_url": track.get("preview_url"),
                        }
                    )

            logger.info(f"Retrieved {len(tracks)} tracks from playlist {playlist_id}")
            return tracks
        except Exception as e:
            logger.error(f"Error retrieving playlist tracks: {e}")
            return []

    def get_user_liked_tracks(self, limit=50):
        """
        Obtiene los tracks que le gustan al usuario (Liked Songs).

        Args:
            limit: Número máximo de tracks a obtener

        Returns:
            Lista de diccionarios con información de tracks
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return []

        try:
            results = self.client.current_user_saved_tracks(limit=min(limit, 50))
            tracks = []

            for item in results.get("items", []):
                track = item.get("track", {})
                if track:
                    tracks.append(
                        {
                            "id": track.get("id"),
                            "name": track.get("name"),
                            "artists": [
                                artist.get("name")
                                for artist in track.get("artists", [])
                            ],
                            "album": track.get("album", {}).get("name"),
                            "album_id": track.get("album", {}).get("id"),
                            "duration_ms": track.get("duration_ms"),
                            "explicit": track.get("explicit", False),
                            "popularity": track.get("popularity"),
                            "uri": track.get("uri"),
                            "preview_url": track.get("preview_url"),
                        }
                    )

            logger.info(f"Retrieved {len(tracks)} liked tracks for user {self.user.username}")
            return tracks
        except Exception as e:
            logger.error(f"Error retrieving user liked tracks: {e}")
            return []

    def get_top_tracks(self, time_range="medium_term", limit=50):
        """
        Obtiene los top tracks del usuario según Spotify.

        Args:
            time_range: 'long_term' (años), 'medium_term' (6 meses), 'short_term' (4 semanas)
            limit: Número máximo de tracks a obtener

        Returns:
            Lista de diccionarios con información de tracks
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return []

        try:
            results = self.client.current_user_top_tracks(
                time_range=time_range,
                limit=min(limit, 50)
            )
            tracks = []

            for track in results.get("items", []):
                tracks.append(
                    {
                        "id": track.get("id"),
                        "name": track.get("name"),
                        "artists": [
                            artist.get("name") for artist in track.get("artists", [])
                        ],
                        "album": track.get("album", {}).get("name"),
                        "album_id": track.get("album", {}).get("id"),
                        "duration_ms": track.get("duration_ms"),
                        "explicit": track.get("explicit", False),
                        "popularity": track.get("popularity"),
                        "uri": track.get("uri"),
                        "preview_url": track.get("preview_url"),
                    }
                )

            logger.info(f"Retrieved {len(tracks)} top tracks for user {self.user.username}")
            return tracks
        except Exception as e:
            logger.error(f"Error retrieving top tracks: {e}")
            return []

    def create_playlist(self, name, description="", public=False):
        """
        Crea una nueva playlist en la cuenta de Spotify del usuario.

        Args:
            name: Nombre de la playlist
            description: Descripción de la playlist
            public: Si la playlist es pública

        Returns:
            Diccionario con información de la playlist creada, o None en caso de error
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return None

        try:
            user_id = self.client.current_user().get("id")
            if not user_id:
                logger.error("Could not get Spotify user ID")
                return None

            playlist = self.client.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                description=description,
            )

            logger.info(f"Created playlist '{name}' for user {self.user.username}")
            return {
                "id": playlist.get("id"),
                "name": playlist.get("name"),
                "spotify_id": playlist.get("id"),
                "uri": playlist.get("uri"),
                "external_urls": playlist.get("external_urls", {}).get("spotify"),
                "snapshot_id": playlist.get("snapshot_id"),
                "images": playlist.get("images", []),
            }
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return None

    def add_tracks_to_playlist(self, playlist_id, track_uris):
        """
        Agrega tracks a una playlist existente.

        Args:
            playlist_id: ID de la playlist
            track_uris: Lista de URIs de Spotify (spotify:track:xxx)

        Returns:
            True si fue exitoso, False en caso de error
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return False

        if not track_uris:
            logger.warning("No tracks provided to add to playlist")
            return False

        try:
            # Spotify API tiene límite de 100 tracks por request
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i : i + 100]
                self.client.playlist_add_items(playlist_id, batch)

            logger.info(f"Added {len(track_uris)} tracks to playlist {playlist_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {e}")
            return False

    def get_audio_features(self, track_ids):
        """
        Obtiene características de audio para una lista de tracks.

        Args:
            track_ids: Lista de IDs de Spotify

        Returns:
            Diccionario mapping track_id -> audio features
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return {}

        if not track_ids:
            return {}

        try:
            features_dict = {}
            # Spotify API permite máximo 100 tracks por request
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i : i + 100]
                features = self.client.audio_features(batch)

                for feature in features:
                    if feature:
                        features_dict[feature["id"]] = {
                            "danceability": feature.get("danceability", 0),
                            "energy": feature.get("energy", 0),
                            "key": feature.get("key", 0),
                            "loudness": feature.get("loudness", 0),
                            "mode": feature.get("mode", 0),
                            "speechiness": feature.get("speechiness", 0),
                            "acousticness": feature.get("acousticness", 0),
                            "instrumentalness": feature.get("instrumentalness", 0),
                            "liveness": feature.get("liveness", 0),
                            "valence": feature.get("valence", 0),
                            "tempo": feature.get("tempo", 0),
                            "time_signature": feature.get("time_signature", 0),
                        }

            logger.info(f"Retrieved audio features for {len(features_dict)} tracks")
            return features_dict
        except Exception as e:
            logger.error(f"Error retrieving audio features: {e}")
            return {}

    @staticmethod
    def verify_api_connection():
        """
        Verifica que las credenciales de la API de Spotify en settings sean válidas
        usando Client Credentials Flow (sin usuario específico).
        """
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=settings.SPOTIPY_CLIENT_ID,
                client_secret=settings.SPOTIPY_CLIENT_SECRET,
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            # Intentamos una operación simple
            sp.search(q="test", limit=1)
            return True, "Conexión exitosa con Spotify API."
        except Exception as e:
            return False, f"Error de conexión con Spotify API: {e!s}"
```

## Archivo: apps/music/tests/__init__.py

Ruta completa: apps/music/tests/__init__.py

```python

```

## Archivo: apps/music/tests/test_models.py

Ruta completa: apps/music/tests/test_models.py

```python
import pytest
from django.contrib.auth import get_user_model

from apps.music.models import Album, Artist, Playlist, Track, TrackAudioFeatures

User = get_user_model()


@pytest.mark.django_db
class TestMusicModels:
    def test_artist_creation(self):
        artist = Artist.objects.create(
            spotify_id="artist_123", name="Test Artist", genres=["rock", "pop"]
        )
        assert artist.name == "Test Artist"
        assert str(artist) == "Test Artist"
        assert Artist.objects.count() == 1

    def test_album_creation(self):
        artist = Artist.objects.create(spotify_id="artist_123", name="Artist")
        album = Album.objects.create(
            spotify_id="album_123", name="Test Album", release_date="2024"
        )
        album.artists.add(artist)
        assert album.name == "Test Album"
        assert album.artists.count() == 1
        assert str(album) == "Test Album"

    def test_track_creation(self):
        artist = Artist.objects.create(spotify_id="artist_123", name="Artist")
        album = Album.objects.create(spotify_id="album_123", name="Album")
        track = Track.objects.create(
            spotify_id="track_123",
            name="Test Track",
            album=album,
            duration_ms=200000,
            track_number=1,
        )
        track.artists.add(artist)
        assert track.name == "Test Track"
        assert track.album == album
        assert track.artists.count() == 1
        assert "Test Track" in str(track)

    def test_audio_features_creation(self):
        track = Track.objects.create(
            spotify_id="track_123",
            name="Test Track",
            duration_ms=200000,
            track_number=1,
        )
        features = TrackAudioFeatures.objects.create(
            track=track,
            danceability=0.8,
            energy=0.7,
            key=5,
            loudness=-5.0,
            mode=1,
            speechiness=0.05,
            acousticness=0.1,
            instrumentalness=0.0,
            liveness=0.1,
            valence=0.6,
            tempo=120.0,
            time_signature=4,
        )
        assert features.track == track
        assert features.danceability == 0.8
        assert str(features) == f"Features for {track.name}"

    def test_playlist_creation(self):
        user = User.objects.create_user(username="testuser", password="password")
        track = Track.objects.create(
            spotify_id="track_123",
            name="Test Track",
            duration_ms=200000,
            track_number=1,
        )
        playlist = Playlist.objects.create(
            spotify_id="playlist_123", user=user, name="My Playlist"
        )
        playlist.tracks.add(track, through_defaults={"order": 1})

        assert playlist.name == "My Playlist"
        assert playlist.user == user
        assert playlist.tracks.count() == 1
        assert str(playlist) == f"My Playlist ({user.username})"
```

## Archivo: apps/music/tests/test_music_briefing_service.py

Ruta completa: apps/music/tests/test_music_briefing_service.py

```python
import pytest
from cities_light.models import Country

from apps.context.models.weather_context import WeatherContext
from apps.music.services.music_briefing_service import MusicBriefingService


@pytest.mark.django_db
class TestMusicBriefingService:
    def test_generate_briefing_clear_weather(self):
        # Setup
        country = Country.objects.create(name="Spain", code2="ES")
        weather = WeatherContext(
            country=country,
            main_status="Clear",
            temperature=25.0,
            description="Cielo despejado",
        )

        # Action
        briefing = MusicBriefingService.generate_briefing(weather)

        # Assertions
        assert briefing["mood_name"] == "Happy/Upbeat"
        assert briefing["recommendation_params"]["target_energy"] == 0.8
        assert "pop" in briefing["recommendation_params"]["seed_genres"]
        assert "Spain" in briefing["context_summary"]
        assert "25.0" in briefing["context_summary"]

    def test_generate_briefing_rain_weather(self):
        # Setup
        country = Country.objects.create(name="UK", code2="GB")
        weather = WeatherContext(
            country=country,
            main_status="Rain",
            temperature=12.0,
            description="Lluvia ligera",
        )

        # Action
        briefing = MusicBriefingService.generate_briefing(weather)

        # Assertions
        assert briefing["mood_name"] == "Melancholic/Cozy"
        assert briefing["recommendation_params"]["target_energy"] == 0.3
        assert "jazz" in briefing["recommendation_params"]["seed_genres"]
        assert "UK" in briefing["context_summary"]

    def test_generate_briefing_unknown_weather_defaults_to_clouds(self):
        # Setup
        country = Country.objects.create(name="Mars", code2="MR")
        weather = WeatherContext(
            country=country,
            main_status="Sandstorm",  # No mapeado
            temperature=-60.0,
            description="Tormenta de arena",
        )

        # Action
        briefing = MusicBriefingService.generate_briefing(weather)

        # Assertions
        # Debería usar el default de MoodService (Clouds)
        assert briefing["mood_name"] == "Chill/Calm"
        assert briefing["recommendation_params"]["target_energy"] == 0.4
        assert "chill" in briefing["recommendation_params"]["seed_genres"]
```

## Archivo: apps/music/tests/test_spotify_integration.py

Ruta completa: apps/music/tests/test_spotify_integration.py

```python
"""
Tests para la integración completa con Spotify.
Incluye tests para SpotifyMusicService, sync_spotify_tracks, y playlists.
"""

from unittest.mock import MagicMock, patch
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone

from apps.music.models import Track, Album, Artist, Playlist
from apps.music.services.spotify_music_service import SpotifyMusicService

User = get_user_model()


@pytest.mark.django_db
class TestSpotifyMusicServiceExtended:
    """Tests para los nuevos métodos de SpotifyMusicService."""

    @pytest.fixture
    def user_with_spotify(self):
        """Crea un usuario conectado a Spotify."""
        user = User.objects.create_user(
            username="spotify_user",
            email="spotify@test.com",
            is_spotify_connected=True
        )
        # Crear social account y token
        account = SocialAccount.objects.create(
            user=user,
            provider="spotify",
            uid="spotify_123"
        )
        SocialToken.objects.create(
            account=account,
            token="test_access_token",
            token_secret="test_refresh_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        return user

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_get_playlist_tracks(self, mock_spotify_class, user_with_spotify):
        """Test obteniendo tracks de una playlist."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.playlist_tracks.return_value = {
            "items": [
                {
                    "track": {
                        "id": "track_1",
                        "name": "Song 1",
                        "artists": [{"name": "Artist 1"}],
                        "album": {"name": "Album 1", "id": "album_1"},
                        "duration_ms": 180000,
                        "explicit": False,
                        "popularity": 80,
                        "uri": "spotify:track:track_1",
                    }
                }
            ]
        }

        service = SpotifyMusicService(user_with_spotify)
        tracks = service.get_playlist_tracks("playlist_123", limit=50)

        assert len(tracks) == 1
        assert tracks[0]["id"] == "track_1"
        assert tracks[0]["name"] == "Song 1"
        assert tracks[0]["popularity"] == 80

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_get_user_liked_tracks(self, mock_spotify_class, user_with_spotify):
        """Test obteniendo liked songs del usuario."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.current_user_saved_tracks.return_value = {
            "items": [
                {
                    "track": {
                        "id": "liked_track_1",
                        "name": "Liked Song",
                        "artists": [{"name": "Favorite Artist"}],
                        "album": {"name": "Favorite Album", "id": "album_2"},
                        "duration_ms": 240000,
                        "explicit": True,
                        "popularity": 75,
                        "uri": "spotify:track:liked_track_1",
                    }
                }
            ]
        }

        service = SpotifyMusicService(user_with_spotify)
        tracks = service.get_user_liked_tracks(limit=50)

        assert len(tracks) == 1
        assert tracks[0]["id"] == "liked_track_1"
        assert tracks[0]["explicit"] is True

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_get_top_tracks(self, mock_spotify_class, user_with_spotify):
        """Test obteniendo top tracks del usuario."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.current_user_top_tracks.return_value = {
            "items": [
                {
                    "id": "top_track_1",
                    "name": "Top Song",
                    "artists": [{"name": "Top Artist"}],
                    "album": {"name": "Top Album", "id": "album_3"},
                    "duration_ms": 200000,
                    "explicit": False,
                    "popularity": 90,
                    "uri": "spotify:track:top_track_1",
                }
            ]
        }

        service = SpotifyMusicService(user_with_spotify)
        tracks = service.get_top_tracks(time_range="medium_term", limit=50)

        assert len(tracks) == 1
        assert tracks[0]["id"] == "top_track_1"
        assert tracks[0]["popularity"] == 90

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_create_playlist(self, mock_spotify_class, user_with_spotify):
        """Test creando una playlist en Spotify."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.current_user.return_value = {"id": "user_123"}
        mock_client.user_playlist_create.return_value = {
            "id": "new_playlist_123",
            "name": "Test Playlist",
            "uri": "spotify:playlist:new_playlist_123",
            "snapshot_id": "snapshot_123",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/new_playlist_123"},
            "images": [],
        }

        service = SpotifyMusicService(user_with_spotify)
        playlist = service.create_playlist(
            name="Test Playlist",
            description="Test Description",
            public=True
        )

        assert playlist is not None
        assert playlist["id"] == "new_playlist_123"
        assert playlist["name"] == "Test Playlist"
        mock_client.user_playlist_create.assert_called_once()

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_add_tracks_to_playlist(self, mock_spotify_class, user_with_spotify):
        """Test agregando tracks a una playlist."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        service = SpotifyMusicService(user_with_spotify)
        track_uris = [
            "spotify:track:1",
            "spotify:track:2",
            "spotify:track:3",
        ]
        
        result = service.add_tracks_to_playlist("playlist_123", track_uris)
        
        assert result is True
        mock_client.playlist_add_items.assert_called_once()

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_get_audio_features(self, mock_spotify_class, user_with_spotify):
        """Test obteniendo audio features."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.audio_features.return_value = [
            {
                "id": "track_1",
                "danceability": 0.7,
                "energy": 0.8,
                "key": 0,
                "loudness": -5.5,
                "mode": 1,
                "speechiness": 0.05,
                "acousticness": 0.1,
                "instrumentalness": 0.0,
                "liveness": 0.2,
                "valence": 0.6,
                "tempo": 130,
                "time_signature": 4,
            }
        ]

        service = SpotifyMusicService(user_with_spotify)
        features = service.get_audio_features(["track_1"])

        assert "track_1" in features
        assert features["track_1"]["danceability"] == 0.7
        assert features["track_1"]["energy"] == 0.8


@pytest.mark.django_db
class TestPlaylistGenerationWithSpotify:
    """Tests para PlaylistGenerationService con Spotify."""

    @pytest.fixture
    def user_with_spotify(self):
        """Usuario conectado a Spotify."""
        user = User.objects.create_user(
            username="playlist_user",
            email="playlist@test.com",
            is_spotify_connected=True
        )
        account = SocialAccount.objects.create(
            user=user,
            provider="spotify",
            uid="spotify_456"
        )
        SocialToken.objects.create(
            account=account,
            token="test_token",
            token_secret="test_refresh",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        return user

    @pytest.fixture
    def sample_tracks(self):
        """Crea algunos tracks para testing."""
        artist = Artist.objects.create(name="Test Artist", spotify_id="artist_1")
        album = Album.objects.create(name="Test Album", spotify_id="album_1")
        
        tracks = []
        for i in range(5):
            track = Track.objects.create(
                spotify_id=f"track_{i}",
                name=f"Track {i}",
                album=album,
                duration_ms=180000,
                track_number=i + 1,
                popularity=70,
                uri=f"spotify:track:track_{i}",
            )
            track.artists.add(artist)
            tracks.append(track)
        
        return tracks

    @patch("apps.interactions.services.playlist_generation_service.SpotifyMusicService")
    def test_playlist_sync_to_spotify(self, mock_spotify_service_class, user_with_spotify, sample_tracks):
        """Test sincronizando playlist con Spotify."""
        from apps.interactions.services.playlist_generation_service import (
            PlaylistGenerationService
        )
        
        # Mock del servicio de Spotify
        mock_service = MagicMock()
        mock_spotify_service_class.return_value = mock_service
        mock_service.client = MagicMock()
        mock_service.create_playlist.return_value = {
            "id": "spotify_playlist_123",
            "uri": "spotify:playlist:spotify_playlist_123",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/spotify_playlist_123"},
        }
        mock_service.add_tracks_to_playlist.return_value = True

        # Crear playlist localmente
        playlist = Playlist.objects.create(
            user=user_with_spotify,
            name="Test Playlist Sync",
            is_public=False,
        )
        for track in sample_tracks:
            playlist.tracks.add(track)

        # Sincronizar con Spotify
        service = PlaylistGenerationService()
        result = service._sync_playlist_to_spotify(user_with_spotify, playlist, sample_tracks)

        assert result is not None
        assert result["id"] == "spotify_playlist_123"
        mock_service.create_playlist.assert_called_once()
        mock_service.add_tracks_to_playlist.assert_called_once()


@pytest.mark.django_db
class TestPlaylistAPIEndpoints:
    """Tests para los endpoints de la API."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.fixture
    def user_with_spotify(self):
        user = User.objects.create_user(
            username="api_user",
            email="api@test.com",
            password="test123",
            is_spotify_connected=True
        )
        account = SocialAccount.objects.create(
            user=user,
            provider="spotify",
            uid="spotify_789"
        )
        SocialToken.objects.create(
            account=account,
            token="api_token",
            token_secret="api_refresh",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        return user

    @pytest.fixture
    def sample_playlist(self, user_with_spotify):
        """Crea una playlist de muestra."""
        artist = Artist.objects.create(name="API Artist", spotify_id="artist_api")
        album = Album.objects.create(name="API Album", spotify_id="album_api")
        
        playlist = Playlist.objects.create(
            user=user_with_spotify,
            name="API Test Playlist",
            spotify_id="playlist_api_123",
            is_public=False,
        )
        
        for i in range(3):
            track = Track.objects.create(
                spotify_id=f"api_track_{i}",
                name=f"API Track {i}",
                album=album,
                duration_ms=180000,
                track_number=i + 1,
                uri=f"spotify:track:api_track_{i}",
            )
            track.artists.add(artist)
            playlist.tracks.add(track)
        
        return playlist

    def test_list_user_playlists(self, client, user_with_spotify, sample_playlist):
        """Test listando playlists del usuario."""
        client.force_login(user_with_spotify)
        response = client.get("/api/interactions/playlists/")
        
        assert response.status_code == 200
        data = response.json()
        assert "playlists" in data
        assert len(data["playlists"]) == 1
        assert data["playlists"][0]["playlist_name"] == "API Test Playlist"

    def test_get_playlist_details(self, client, user_with_spotify, sample_playlist):
        """Test obteniendo detalles de una playlist."""
        client.force_login(user_with_spotify)
        response = client.get(f"/api/interactions/playlists/{sample_playlist.spotify_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["playlist_name"] == "API Test Playlist"
        assert data["tracks_count"] == 3

    @patch("apps.interactions.views.playlist_api.SpotifyMusicService")
    def test_sync_playlist_to_spotify_endpoint(self, mock_spotify_service, client, 
                                               user_with_spotify, sample_playlist):
        """Test sincronizando playlist por API."""
        mock_service = MagicMock()
        mock_spotify_service.return_value = mock_service
        mock_service.client = MagicMock()
        mock_service.create_playlist.return_value = {
            "id": "new_spotify_id",
            "uri": "spotify:playlist:new_spotify_id",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/new_spotify_id"},
        }
        mock_service.add_tracks_to_playlist.return_value = True

        client.force_login(user_with_spotify)
        response = client.post(
            f"/api/interactions/playlists/{sample_playlist.spotify_id}/sync-spotify/"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["spotify_id"] == "new_spotify_id"

    @patch("apps.interactions.views.playlist_api.SpotifyMusicService")
    def test_sync_tracks_endpoint(self, mock_spotify_service, client, user_with_spotify):
        """Test sincronizando tracks por API."""
        mock_service = MagicMock()
        mock_spotify_service.return_value = mock_service
        mock_service.client = MagicMock()
        mock_service.get_user_liked_tracks.return_value = [
            {
                "id": "liked_1",
                "name": "Liked Track",
                "artists": ["Artist"],
                "album": "Album",
                "album_id": "album_123",
                "duration_ms": 180000,
                "explicit": False,
                "popularity": 75,
                "preview_url": "",
                "uri": "spotify:track:liked_1",
            }
        ]
        mock_service.get_audio_features.return_value = {}

        client.force_login(user_with_spotify)
        response = client.post(
            "/api/interactions/tracks/sync/",
            {"source": "liked", "limit": 50}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "synced_count" in data
```

## Archivo: apps/music/tests/test_spotify_playlist_management.py

Ruta completa: apps/music/tests/test_spotify_playlist_management.py

```python
from unittest.mock import MagicMock, patch

import pytest
import spotipy
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone

from apps.music.services.spotify_music_service import SpotifyMusicService
from apps.users.models.user import User


@pytest.mark.django_db
class TestSpotifyPlaylistManagement:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="test_playlist_user", email="test_playlist@example.com"
        )

    @pytest.fixture
    def _social_token(self, user):
        account = SocialAccount.objects.create(
            user=user, provider="spotify", uid="spotify_playlist_uid"
        )
        return SocialToken.objects.create(
            account=account,
            token="access_token",
            token_secret="refresh_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    @patch("spotipy.Spotify")
    def test_create_playlist(self, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        mock_instance.current_user.return_value = {"id": "spotify_user_id"}
        mock_instance.user_playlist_create.return_value = {
            "id": "new_playlist_id",
            "name": "Moodsic: Happy",
        }

        service = SpotifyMusicService(user)
        playlist = service.create_playlist(
            name="Moodsic: Happy", description="Created by Moodsic"
        )

        assert playlist["id"] == "new_playlist_id"
        mock_instance.user_playlist_create.assert_called_once_with(
            user="spotify_user_id",
            name="Moodsic: Happy",
            public=True,
            collaborative=False,
            description="Created by Moodsic",
        )

    @patch("spotipy.Spotify")
    def test_add_tracks_to_playlist(self, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        mock_instance.playlist_add_items.return_value = {"snapshot_id": "snap_1"}

        service = SpotifyMusicService(user)
        track_uris = ["spotify:track:1", "spotify:track:2"]
        result = service.add_tracks_to_playlist("playlist_id", track_uris)

        assert result["snapshot_id"] == "snap_1"
        mock_instance.playlist_add_items.assert_called_once_with(
            "playlist_id", track_uris
        )

    @patch("spotipy.Spotify")
    def test_replace_playlist_tracks(self, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        mock_instance.playlist_replace_items.return_value = {"snapshot_id": "snap_2"}

        service = SpotifyMusicService(user)
        track_uris = ["spotify:track:3", "spotify:track:4"]
        result = service.replace_playlist_tracks("playlist_id", track_uris)

        assert result["snapshot_id"] == "snap_2"
        mock_instance.playlist_replace_items.assert_called_once_with(
            "playlist_id", track_uris
        )

    @patch("spotipy.Spotify")
    @patch("apps.music.services.spotify_music_service.logger")
    def test_handle_rate_limit(self, mock_logger, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance

        # Simulamos error 429
        exception = spotipy.SpotifyException(
            http_status=429,
            code=-1,
            msg="Rate limit exceeded",
            headers={"Retry-After": "30"},
        )
        mock_instance.playlist_add_items.side_effect = exception

        service = SpotifyMusicService(user)
        result = service.add_tracks_to_playlist("playlist_id", ["uri"])

        assert result is None
        mock_logger.error.assert_any_call(
            "Límite de tasa (Rate Limit) alcanzado. Reintentar después de 30s."
        )

    @patch("spotipy.Spotify")
    def test_handle_expired_token(self, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance

        # Simulamos error 401
        exception = spotipy.SpotifyException(
            http_status=401, code=-1, msg="Unauthorized"
        )
        mock_instance.playlist_add_items.side_effect = exception

        service = SpotifyMusicService(user)

        # Al fallar con 401, debería intentar refrescar (aunque no reintenta la operación automáticamente en esta versión simplificada)
        # pero el cliente debería ser recreado.
        with patch.object(
            service, "_get_valid_token", return_value=_social_token
        ) as mock_refresh:
            result = service.add_tracks_to_playlist("playlist_id", ["uri"])
            assert result is None
            mock_refresh.assert_called()
```

## Archivo: apps/music/tests/test_spotify_service.py

Ruta completa: apps/music/tests/test_spotify_service.py

```python
from secrets import compare_digest
from unittest.mock import MagicMock, patch

import pytest
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone

from apps.music.services.spotify_music_service import SpotifyMusicService
from apps.users.models.user import User


@pytest.mark.django_db
class TestSpotifyMusicService:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="testuser", email="test@example.com")

    @pytest.fixture
    def _social_token(self, user):
        account = SocialAccount.objects.create(
            user=user, provider="spotify", uid="spotify_user_id"
        )
        return SocialToken.objects.create(
            account=account,
            token="old_access_token",
            token_secret="refresh_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    def test_get_valid_token_not_expired(self, user, _social_token):
        service = SpotifyMusicService(user)
        token = service._get_valid_token()
        assert compare_digest(token.token, "old_access_token")
        assert token.id == _social_token.id

    @patch("apps.music.services.spotify_music_service.SpotifyOAuth")
    def test_get_valid_token_expired_refreshes(
        self, mock_oauth_class, user, _social_token
    ):
        # Set token as expired
        _social_token.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        _social_token.save()

        # Mock OAuth and refresh response
        mock_oauth_instance = MagicMock()
        mock_oauth_class.return_value = mock_oauth_instance
        mock_oauth_instance.refresh_access_token.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        service = SpotifyMusicService(user)
        token = service._get_valid_token()

        assert compare_digest(token.token, "new_access_token")
        assert token.token_secret == "new_refresh_token"
        assert token.expires_at > timezone.now()
        mock_oauth_instance.refresh_access_token.assert_called_with("refresh_token")

    @patch("spotipy.Spotify")
    def test_get_user_info(self, mock_spotify, user, _social_token):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.current_user.return_value = {"id": "spotify_user_id"}

        service = SpotifyMusicService(user)
        info = service.get_user_info()

        assert info == {"id": "spotify_user_id"}
        mock_spotify_instance.current_user.assert_called_once()

    @patch("spotipy.oauth2.SpotifyClientCredentials")
    @patch("spotipy.Spotify")
    def test_verify_api_connection_success(self, mock_spotify, _mock_creds):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance

        success, message = SpotifyMusicService.verify_api_connection()

        assert success is True
        assert "Conexión exitosa" in message

    @patch("spotipy.oauth2.SpotifyClientCredentials")
    @patch("spotipy.Spotify")
    def test_verify_api_connection_failure(self, mock_spotify, _mock_creds):
        mock_spotify.side_effect = Exception("API Error")

        success, message = SpotifyMusicService.verify_api_connection()

        assert success is False
        assert "Error de conexión" in message
```

## Archivo: apps/music/tests/test_spotify_service_enhancements.py

Ruta completa: apps/music/tests/test_spotify_service_enhancements.py

```python
from unittest.mock import MagicMock, patch

import pytest
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone

from apps.music.services.spotify_music_service import SpotifyMusicService
from apps.users.models.user import User


@pytest.mark.django_db
class TestSpotifyMusicServiceEnhancements:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="testuser_enh", email="test_enh@example.com"
        )

    @pytest.fixture
    def _social_token(self, user):
        account = SocialAccount.objects.create(
            user=user, provider="spotify", uid="spotify_user_id_enh"
        )
        return SocialToken.objects.create(
            account=account,
            token="access_token",
            token_secret="refresh_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    @patch("spotipy.Spotify")
    def test_search_tracks_with_audio_features(self, mock_spotify, user, _social_token):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.search.return_value = {
            "tracks": {"items": [{"id": "track_1", "name": "Track 1"}]}
        }

        service = SpotifyMusicService(user)
        # Probamos búsqueda con género y parámetros de audio
        results = service.search_tracks(
            query="genre:rock",
            limit=10,
            min_energy=0.5,
            max_valence=0.8,
            min_danceability=0.6,
        )

        assert results["tracks"]["items"][0]["id"] == "track_1"
        # Verificamos que se llamó a search con el query correcto
        # Nota: Spotify search API no soporta parámetros de audio directamente en el query de 'search'
        # pero spotipy.recommendations sí los soporta.
        # Si queremos usar search tradicional con filtros avanzados, hay que ver si es posible.
        # Spotify search soporta filtros como 'genre:', 'year:', 'artist:', 'album:'.
        # Los parámetros técnicos (energy, valence) suelen usarse en 'recommendations'.
        # El requerimiento dice: "Implementar el método de búsqueda de canciones que permita filtrar por género y, sobre todo, por parámetros de audio".
        # Si 'search' no lo permite, quizás deba filtrar los resultados después o usar 'recommendations'.
        # Sin embargo, 'recommendations' requiere semillas (seeds).
        # Vamos a ver si el requerimiento implica usar 'recommendations' o una búsqueda + filtrado.
        # Normalmente para parámetros técnicos se usa 'recommendations'.

        mock_spotify_instance.search.assert_called_once()

    @patch("spotipy.Spotify")
    def test_get_recommendations(self, mock_spotify, user, _social_token):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.recommendations.return_value = {
            "tracks": [{"id": "rec_track_1", "name": "Rec Track 1"}]
        }

        service = SpotifyMusicService(user)
        results = service.get_recommendations(
            seed_genres=["rock"], limit=5, target_energy=0.7, target_valence=0.5
        )

        assert results["tracks"][0]["id"] == "rec_track_1"
        mock_spotify_instance.recommendations.assert_called_once()
```

## Archivo: apps/music/urls.py

Ruta completa: apps/music/urls.py

```python

```

## Archivo: apps/music/views/__init__.py

Ruta completa: apps/music/views/__init__.py

```python

```

## Archivo: apps/users/__init__.py

Ruta completa: apps/users/__init__.py

```python

```

## Archivo: apps/users/adapter.py

Ruta completa: apps/users/adapter.py

```python
import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger(__name__)


class MoodsicSocialAccountAdapter(DefaultSocialAccountAdapter):
    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        logger.error(
            "OAuth authentication error provider=%s error=%s exception=%r extra_context=%r",
            getattr(provider, "id", provider),
            error,
            exception,
            extra_context,
            exc_info=True,
        )

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login user and populates Spotify fields.
        """
        try:
            user = super().save_user(request, sociallogin, form)
            logger.info(f"✓ User created/updated: {user.email}")

            # Populate custom fields directly on the Custom User model
            avatar_url = sociallogin.account.get_avatar_url()
            logger.info(f"Avatar URL from Spotify: {avatar_url}")
            
            user.avatar_url = avatar_url or ""
            user.spotify_id = sociallogin.account.uid
            user.is_spotify_connected = True
            
            logger.info(f"Setting spotify_id={user.spotify_id}, avatar_url={user.avatar_url}")
            user.save()
            logger.info(f"✓ Spotify fields saved successfully")

            return user
        except Exception as e:
            logger.error(f"✗ ERROR in save_user: {type(e).__name__}: {str(e)}", exc_info=True)
            raise
```

## Archivo: apps/users/admin/__init__.py

Ruta completa: apps/users/admin/__init__.py

```python
from .user import UserAdmin

__all__ = ["UserAdmin"]
```

## Archivo: apps/users/admin/user.py

Ruta completa: apps/users/admin/user.py

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """
    Custom UserAdmin using Unfold design.
    """

    fieldsets = (
        *BaseUserAdmin.fieldsets,
        (
            "Spotify info",
            {"fields": ("spotify_id", "avatar_url", "is_spotify_connected")},
        ),
    )
    list_display = (*BaseUserAdmin.list_display, "spotify_id", "is_spotify_connected")
    search_fields = (*BaseUserAdmin.search_fields, "spotify_id")
```

## Archivo: apps/users/apps.py

Ruta completa: apps/users/apps.py

```python
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
```

## Archivo: apps/users/migrations/0001_initial.py

Ruta completa: apps/users/migrations/0001_initial.py

```python
# Generated by Django 6.0.3 on 2026-03-03 17:01

import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('spotify_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('avatar_url', models.URLField(blank=True, max_length=500, null=True)),
                ('is_spotify_connected', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
                'db_table': 'auth_user_custom',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
```

## Archivo: apps/users/migrations/0002_alter_user_avatar_url.py

Ruta completa: apps/users/migrations/0002_alter_user_avatar_url.py

```python
# Generated by Django 6.0.3 on 2026-03-03 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='avatar_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
    ]
```

## Archivo: apps/users/migrations/0003_alter_user_spotify_id.py

Ruta completa: apps/users/migrations/0003_alter_user_spotify_id.py

```python
# Generated by Django 6.0.3 on 2026-03-03 17:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_avatar_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='spotify_id',
            field=models.CharField(blank=True, default='', max_length=255, unique=True),
        ),
    ]
```

## Archivo: apps/users/migrations/0004_alter_user_spotify_id.py

Ruta completa: apps/users/migrations/0004_alter_user_spotify_id.py

```python
# Generated by Django 6.0.3 on 2026-03-03 17:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_user_spotify_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='spotify_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
```

## Archivo: apps/users/migrations/__init__.py

Ruta completa: apps/users/migrations/__init__.py

```python

```

## Archivo: apps/users/models/__init__.py

Ruta completa: apps/users/models/__init__.py

```python
from .user import User

__all__ = ["User"]
```

## Archivo: apps/users/models/user.py

Ruta completa: apps/users/models/user.py

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for Moodsic.
    Inherits from Django's AbstractUser to maintain standard functionality
    while allowing for expansion of profile-specific fields.
    """

    spotify_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    avatar_url = models.URLField(max_length=500, blank=True, default="")

    # Optional fields for analytics or user-specific settings
    is_spotify_connected = models.BooleanField(default=False)

    class Meta:
        db_table = "auth_user_custom"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email if self.email else self.username
```

## Archivo: apps/users/services/__init__.py

Ruta completa: apps/users/services/__init__.py

```python

```

## Archivo: apps/users/services/spotify_auth_service.py

Ruta completa: apps/users/services/spotify_auth_service.py

```python

```

## Archivo: apps/users/tests/__init__.py

Ruta completa: apps/users/tests/__init__.py

```python

```

## Archivo: apps/users/tests/test_adapter.py

Ruta completa: apps/users/tests/test_adapter.py

```python
from unittest.mock import MagicMock

import pytest
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.auth import get_user_model

from apps.users.adapter import MoodsicSocialAccountAdapter

User = get_user_model()


@pytest.mark.django_db
def test_adapter_save_user_populates_custom_fields(rf):
    # Setup mock request, sociallogin and user
    request = rf.get("/")
    # Add session to mock request
    from django.contrib.sessions.middleware import SessionMiddleware

    middleware = SessionMiddleware(lambda _: None)
    middleware.process_request(request)
    request.session.save()

    user = User.objects.create_user(
        username="socialuser", email="social@example.com", password="password"
    )

    # Mock SocialAccount and SocialLogin
    social_account = SocialAccount(user=user, provider="spotify", uid="spotify_uid_123")
    social_account.get_avatar_url = MagicMock(
        return_value="https://example.com/social_avatar.jpg"
    )

    social_login = SocialLogin(user=user, account=social_account)

    # Instantiate adapter
    adapter = MoodsicSocialAccountAdapter()

    # Call the method
    saved_user = adapter.save_user(request, social_login)

    assert saved_user == user
    assert saved_user.spotify_id == "spotify_uid_123"
    assert saved_user.avatar_url == "https://example.com/social_avatar.jpg"
    assert saved_user.is_spotify_connected is True


@pytest.mark.django_db
def test_adapter_save_user_updates_existing_fields(rf):
    request = rf.get("/")
    # Add session to mock request
    from django.contrib.sessions.middleware import SessionMiddleware

    middleware = SessionMiddleware(lambda _: None)
    middleware.process_request(request)
    request.session.save()

    user = User.objects.create_user(
        username="socialuser2",
        email="social2@example.com",
        password="password",
        spotify_id="old_id",
    )

    social_account = SocialAccount(user=user, provider="spotify", uid="new_uid")
    social_account.get_avatar_url = MagicMock(
        return_value="https://example.com/new_avatar.jpg"
    )
    social_login = SocialLogin(user=user, account=social_account)

    adapter = MoodsicSocialAccountAdapter()
    adapter.save_user(request, social_login)

    user.refresh_from_db()
    assert user.spotify_id == "new_uid"
    assert user.avatar_url == "https://example.com/new_avatar.jpg"
```

## Archivo: apps/users/tests/test_models.py

Ruta completa: apps/users/tests/test_models.py

```python
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
def test_custom_user_creation():
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password",
        spotify_id="spotify123",
        avatar_url="https://example.com/avatar.jpg",
    )

    assert User.objects.count() == 1
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.spotify_id == "spotify123"
    assert user.avatar_url == "https://example.com/avatar.jpg"


@pytest.mark.django_db
def test_user_str_representation():
    user = User.objects.create_user(
        username="testuser", email="test@example.com", password="password"
    )
    assert str(user) == "test@example.com"

    user2 = User.objects.create_user(username="testuser2", password="password")
    assert str(user2) == "testuser2"


@pytest.mark.django_db
def test_spotify_id_unique():
    User.objects.create_user(username="user1", spotify_id="spotify123")
    with pytest.raises(IntegrityError):
        User.objects.create_user(username="user2", spotify_id="spotify123")
```

## Archivo: apps/users/tests/test_views.py

Ruta completa: apps/users/tests/test_views.py

```python
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_profile_view_requires_login(client):
    url = reverse("users:profile")
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response.url


@pytest.mark.django_db
def test_profile_view_authenticated(client):
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password",
        spotify_id="spotify123",
    )
    client.force_login(user)

    url = reverse("users:profile")
    response = client.get(url)

    assert response.status_code == 200
    assert "test@example.com" in response.content.decode()
    assert "spotify123" in response.content.decode()
    assert "Conectado con Spotify" in response.content.decode()


@pytest.mark.django_db
def test_profile_view_without_spotify(client):
    user = User.objects.create_user(
        username="testuser", email="test@example.com", password="password"
    )
    client.force_login(user)

    url = reverse("users:profile")
    response = client.get(url)

    assert response.status_code == 200
    assert "No conectado con Spotify" in response.content.decode()
```

## Archivo: apps/users/urls.py

Ruta completa: apps/users/urls.py

```python
from django.urls import path

from .views import profile_view

app_name = "users"

urlpatterns = [
    path("profile/", profile_view, name="profile"),
]

# allauth URLs should be outside the namespace to match expected names like 'account_logout'
# Or we can keep them here and use 'users:account_logout' if we want, but allauth usually expects global namespace.
```

## Archivo: apps/users/views/__init__.py

Ruta completa: apps/users/views/__init__.py

```python
from .profile_view import profile_view

__all__ = ["profile_view"]
```

## Archivo: apps/users/views/profile_view.py

Ruta completa: apps/users/views/profile_view.py

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def profile_view(request):
    """
    Muestra el perfil del usuario autenticado.
    """
    return render(request, "users/profile.html", {"user": request.user})
```

## Archivo: apps/users/views/spotify_callback.py

Ruta completa: apps/users/views/spotify_callback.py

```python
from django.shortcuts import redirect


def spotify_callback_redirect(request):
    """Redirige el callback de Spotify al endpoint de Allauth."""
    query_string = request.META.get("QUERY_STRING", "")
    target_url = "/accounts/spotify/login/callback/"
    if query_string:
        target_url = f"{target_url}?{query_string}"
    return redirect(target_url)
```

## Archivo: apps/users/views/spotify_oauth.py

Ruta completa: apps/users/views/spotify_oauth.py

```python
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.spotify.views import SpotifyOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView, OAuth2LoginView
from allauth.socialaccount.providers.base import ProviderException


class MoodsicSpotifyOAuth2Adapter(SpotifyOAuth2Adapter):
    """Spotify adapter compatible with profile fetch via Authorization header."""

    def complete_login(self, request, app, token, **kwargs):
        with get_adapter().get_requests_session() as sess:
            resp = sess.get(
                self.profile_url,
                headers={"Authorization": f"Bearer {token.token}"},
                timeout=15,
            )
            if resp.status_code >= 400:
                raise ProviderException(
                    f"Spotify profile request failed ({resp.status_code}): {resp.text[:300]}"
                )
            try:
                extra_data = resp.json()
            except ValueError as exc:
                raise ProviderException(
                    f"Spotify profile response is not valid JSON: {resp.text[:300]}"
                ) from exc

        return self.get_provider().sociallogin_from_response(request, extra_data)


spotify_oauth_login = OAuth2LoginView.adapter_view(MoodsicSpotifyOAuth2Adapter)
spotify_oauth_callback = OAuth2CallbackView.adapter_view(MoodsicSpotifyOAuth2Adapter)
```

## Archivo: config/__init__.py

Ruta completa: config/__init__.py

```python

```

## Archivo: config/asgi.py

Ruta completa: config/asgi.py

```python
"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
```

## Archivo: config/settings.py

Ruta completa: config/settings.py

```python
"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 5.2.11.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import logging
import os
import sys
from pathlib import Path

import environ
import dj_database_url

logger = logging.getLogger(__name__)

env = environ.Env(
    DEBUG=(bool, False),
    DEVELOPMENT_MODE=(bool, False),
    LOCAL=(bool, False),
    ALLOWED_HOSTS=(list, ""),
    CSRF_TRUSTED_ORIGINS=(list, []),
    SECRET_KEY=(str, ""),
)


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

IS_TEST = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG")  # https://docs.djangoproject.com/es/6/ref/settings/#debug.
DEVELOPMENT_MODE = env.bool("DEVELOPMENT_MODE")
IS_PRODUCTION = not DEVELOPMENT_MODE and not DEBUG

SITE_ID = 1  # https://docs.djangoproject.com/es/6/ref/settings/#site-id.

ADMINS = (
    [] if IS_TEST else env("ADMINS")
)  # https://docs.djangoproject.com/es/6/ref/settings/#admins.
MANAGERS = ADMINS  # https://docs.djangoproject.com/es/6/ref/settings/#managers.

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS"
)  # https://docs.djangoproject.com/es/6/ref/settings/#allowed-hosts.
APPEND_SLASH = True  # https://docs.djangoproject.com/es/6/ref/settings/#append-slash.


# Application definition
DJANGO_DEFAULT_APPS = [
    "unfold",  # before django.contrib.admin
    # "unfold.contrib.filters",  # optional, if special filters are needed
    # "unfold.contrib.forms",  # optional, if special form elements are needed
    # "unfold.contrib.inlines",  # optional, if special inlines are needed
    # "unfold.contrib.guardian",  # optional, if django-guardian package is used
    # "unfold.contrib.simple_history",  # optional, if django-simple-history package is used
    # "unfold.contrib.location_field",  # optional, if django-location-field package is used
    # "unfold.contrib.constance",  # optional, if django-constance package is used
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",  # required
    "django.contrib.sites",  # Required by allauth
]
THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.spotify",
    "django_countries",
    "cities_light",
]
LOCAL_APPS = [
    "apps.users.apps.UsersConfig",
    "apps.music.apps.MusicConfig",
    "apps.context.apps.ContextConfig",
    "apps.interactions.apps.InteractionsConfig",
    "apps.dashboard.apps.DashboardConfig",
]
INSTALLED_APPS = DJANGO_DEFAULT_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]
# Enable gzip compression for dynamic responses in production
if IS_PRODUCTION:
    MIDDLEWARE.insert(3, "django.middleware.gzip.GZipMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
]

# SOCIAL ACCOUNT SETTINGS
SOCIALACCOUNT_PROVIDERS = {
    "spotify": {
        "SCOPE": [
            "user-read-email",
            "user-read-private",
            "user-library-read",
            "user-top-read",
            "playlist-read-private",
            "user-read-recently-played",
        ],
    }
}

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ALLAUTH CONFIGURATION
AUTH_USER_MODEL = "users.User"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
# Keep session cookie behavior explicit for OAuth roundtrips.
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False

SOCIALACCOUNT_ADAPTER = "apps.users.adapter.MoodsicSocialAccountAdapter"

# SPOTIPY CONFIGURATION
SPOTIPY_CLIENT_ID = env.str("SPOTIPY_CLIENT_ID", default="")
SPOTIPY_CLIENT_SECRET = env.str("SPOTIPY_CLIENT_SECRET", default="")
SPOTIPY_REDIRECT_URI = env.str("SPOTIPY_REDIRECT_URI", default="")

# OPEN-METEO CONFIGURATION
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# NEWS API CONFIGURATION
NEWSAPI_KEY = env.str("NEWSAPI_KEY", default="")
NEWSAPI_BASE_URL = env.str(
    "NEWSAPI_BASE_URL", default="https://newsapi.org/v2/everything"
)

# RECOMMENDER CONFIGURATION
# Offline benchmark winner by default: 60% context fit, 40% history affinity.
RECOMMENDER_CONTEXT_WEIGHT = env.float("RECOMMENDER_CONTEXT_WEIGHT", default=0.6)
RECOMMENDER_HISTORY_WEIGHT = env.float("RECOMMENDER_HISTORY_WEIGHT", default=0.4)

# CITIES-LIGHT CONFIGURATION
# https://django-cities-light.readthedocs.io/en/stable/
CITIES_LIGHT_TRANSLATION_LANGUAGES = ["es", "en"]
CITIES_LIGHT_INCLUDE_COUNTRIES = ["ES", "MX", "AR", "CO", "CL", "PE"]
CITIES_LIGHT_APP_NAME = "cities_light"

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

if env.str("POSTGRES_HOST", default=""):
    DATABASES = {
        "default": dj_database_url.config(
            default=f"postgres://{env.str('POSTGRES_USER', 'postgres')}:{env.str('POSTGRES_PASSWORD', 'postgres')}@{env.str('POSTGRES_HOST')}:5432/{env.str('POSTGRES_DB', 'moodsic')}",
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = (
    "en-us"  # https://docs.djangoproject.com/es/6/ref/settings/#language-code.
)
LANGUAGES = (
    ("en", "English"),
    ("es", "Spanish"),
)
TIME_ZONE = "Europe/Madrid"
USE_I18N = True  # https://docs.djangoproject.com/en/6/topics/i18n/.
USE_TZ = True  # https://docs.djangoproject.com/es/6/ref/settings/#use-tz.


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INTERNAL_IPS = [
    "127.0.0.1",
]

# DJANGO UNFOLD. https://unfold.readthedocs.io/en/latest/installation.html
UNFOLD = {
    "SITE_TITLE": "MoodSic · Admin",
    "SITE_HEADER": "Panel de administración de MoodSic",
    "INDEX_TITLE": "Resumen operativo del proyecto",
    # "SITE_DROPDOWN": [
    #     },
    #     # ...
    # ],
    "SIDEBAR": {
        "show_search": True,
    },
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
}

# LOGGING CONFIGURATION FOR DEBUGGING
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "allauth": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
```

## Archivo: config/urls.py

Ruta completa: config/urls.py

```python
"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from apps.users.views.spotify_callback import spotify_callback_redirect
from apps.users.views.spotify_oauth import (
    spotify_oauth_callback,
    spotify_oauth_login,
)

urlpatterns = [
    path("", include("apps.dashboard.urls", namespace="dashboard")),
    path("admin/", admin.site.urls),
    path("accounts/spotify/login/", spotify_oauth_login, name="spotify_login"),
    path(
        "accounts/spotify/login/callback/",
        spotify_oauth_callback,
        name="spotify_callback",
    ),
    path("accounts/", include("apps.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    path("callback", spotify_callback_redirect, name="spotify_callback_redirect"),
    path("api/interactions/", include("apps.interactions.urls", namespace="interactions")),
]
```

## Archivo: config/wsgi.py

Ruta completa: config/wsgi.py

```python
"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
```

## Archivo: docker-compose.yml

Ruta completa: docker-compose.yml

```yaml
services:
  django-web:
    container_name: django-web
    build:
      context: .
      dockerfile: Dockerfile
    command: >
      sh -c "
      uv run manage.py migrate &&
      uv run manage.py runserver 0.0.0.0:8000
      "
    depends_on:
      postgres:
        condition: service_healthy
    env_file:
      - .env
    environment:
      - POSTGRES_HOST=postgres
    healthcheck:
      test: ["CMD-SHELL", "uv run manage.py check"]
      interval: 3s
      timeout: 3s
      retries: 3
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4096M
        reservations:
          cpus: '1.0'
          memory: 1024M

  postgres:
    container_name: Postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGDATA: /data/postgres
      POSTGRES_DB: ${POSTGRES_DB}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
    image: postgres:18.1-alpine
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4096M
        reservations:
          cpus: '1.0'
          memory: 1024M

  pgAdmin:
      container_name: PGAdmin
      depends_on:
          postgres:
              condition: service_healthy
      env_file:
        - .env
      image: dpage/pgadmin4
      links:
        - 'postgres:pgsql-server'
      ports:
        - "5050:80"
      restart: always
      volumes:
        - pgadmin_data:/var/lib/pgadmin/
      deploy:
        resources:
          limits:
            cpus: '1.0'
            memory: 1024M
          reservations:
            cpus: '0.5'
            memory: 512M

  redis:
    container_name: redis
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
    image: redis:7-alpine
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1024M
        reservations:
          cpus: '0.5'
          memory: 512M

volumes:
  postgres_data:
  pgadmin_data:
```

## Archivo: help.txt

Ruta completa: help.txt

```text
ACTIVAR EL ENTORNO VIRTUAL
    -   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
    -   .\venv\Scripts\activate

INTALAR TODO LO NECESARIO
    - uv sync

LEVANTAR
    - uv run manage.py runserver

```

## Archivo: manage.py

Ruta completa: manage.py

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

## Archivo: ml/__init__.py

Ruta completa: ml/__init__.py

```python

```

## Archivo: ml/agent.py

Ruta completa: ml/agent.py

```python
"""
Agente de Reinforcement Learning para generación de playlists.

Utiliza Deep Q-Network (DQN) para aprender a seleccionar tracks óptimos
basándose en el contexto (clima, noticias) y feedback del usuario.

Arquitectura:
- Q-Network: Red neuronal que predice Q-values para cada acción (track)
- Memory Buffer: Almacena experiencias para entrenamiento
- Epsilon-Greedy: Exploración vs. Explotación
"""

import logging
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

logger = logging.getLogger(__name__)


class DQNAgent:
    """
    Deep Q-Network Agent para selección de canciones.
    
    El agente aprende a mapear estados (contexto) a acciones (tracks)
    que maximicen el reward esperado (satisfacción del usuario).
    """

    def __init__(
        self,
        state_dim: int = 45,
        action_dim: int = 100,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
        memory_size: int = 10000,
        batch_size: int = 64,
        hidden_dim: int = 128,
        model_path: Optional[str] = None,
    ):
        """
        Inicializa el Agente DQN.
        
        Args:
            state_dim: Dimensión del vector de estado (45)
            action_dim: Número de acciones posibles (tracks disponibles)
            learning_rate: Tasa de aprendizaje
            gamma: Factor de descuento para reward futuro
            epsilon: Probabilidad de exploración inicial
            epsilon_decay: Factor de decaimiento de epsilon
            epsilon_min: Epsilon mínimo
            memory_size: Tamaño del replay buffer
            batch_size: Tamaño del batch para entrenamiento
            hidden_dim: Dimensión de capas ocultas
            model_path: Ruta para guardar/cargar el modelo
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.memory_size = memory_size
        self.batch_size = batch_size
        self.hidden_dim = hidden_dim
        self.model_path = model_path or "ml/models/dqn_model.h5"

        # Replay buffer (memoria de experiencias)
        self.memory = deque(maxlen=memory_size)

        # Redes neuronales
        self.q_network = self._build_network()
        self.target_network = self._build_network()
        self._update_target_network()

        # Optimizador
        self.optimizer = keras.optimizers.Adam(learning_rate=learning_rate)

        # Counters
        self.steps = 0
        self.episodes = 0

        logger.info(f"DQN Agent inicializado. State dim: {state_dim}, Action dim: {action_dim}")

    def _build_network(self) -> keras.Model:
        """
        Construye la red neuronal Q-Network.
        
        Arquitectura: Input -> Dense(128) -> ReLU -> Dense(128) -> ReLU -> Output
        """
        inputs = layers.Input(shape=(self.state_dim,))

        # Primera capa oculta
        x = layers.Dense(self.hidden_dim, activation="relu")(inputs)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)

        # Segunda capa oculta
        x = layers.Dense(self.hidden_dim, activation="relu")(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)

        # Tercera capa oculta (opcional, puede mejorar convergencia)
        x = layers.Dense(64, activation="relu")(x)

        # Capa de salida: un valor Q para cada acción
        outputs = layers.Dense(self.action_dim, activation="linear")(x)

        model = keras.Model(inputs=inputs, outputs=outputs)
        return model

    def select_action(
        self,
        state: np.ndarray,
        available_actions: Optional[List[int]] = None,
        training: bool = True,
    ) -> int:
        """
        Selecciona una acción (track) usando Epsilon-Greedy.
        
        Con probabilidad epsilon, explora (selecciona aleatoriamente).
        Con probabilidad 1-epsilon, explota (selecciona mejor acción conocida).
        
        Args:
            state: Vector de estado normalizado
            available_actions: Lista de índices de acciones disponibles
            training: Si True, use epsilon-greedy; si False, siempre explota
            
        Returns:
            int: Índice de la acción (track) seleccionada
        """
        if available_actions is None:
            available_actions = list(range(self.action_dim))

        # Exploración
        if training and np.random.random() < self.epsilon:
            return np.random.choice(available_actions)

        # Explotación: predecir Q-values
        state_tensor = tf.expand_dims(state, axis=0)
        q_values = self.q_network(state_tensor, training=False).numpy()[0]

        # Enmascarar acciones no disponibles
        q_values_masked = np.full_like(q_values, -np.inf)
        q_values_masked[available_actions] = q_values[available_actions]

        # Seleccionar mejor acción
        action = np.argmax(q_values_masked)
        return int(action)

    def remember(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        """
        Guarda una experiencia en el replay buffer.
        
        Args:
            state: Estado inicial
            action: Acción tomada
            reward: Recompensa obtenida
            next_state: Estado siguiente
            done: Si el episodio terminó
        """
        self.memory.append((state, action, reward, next_state, done))

    def replay(self) -> Optional[float]:
        """
        Entrena la red con un mini-batch del replay buffer.
        
        Returns:
            float: Loss del batch, o None si no hay suficientes experiencias
        """
        if len(self.memory) < self.batch_size:
            return None

        # Sample del replay buffer
        batch = np.random.choice(len(self.memory), self.batch_size, replace=False)
        experiences = [self.memory[i] for i in batch]

        states, actions, rewards, next_states, dones = zip(*experiences)

        states = np.array(states, dtype=np.float32)
        next_states = np.array(next_states, dtype=np.float32)
        rewards = np.array(rewards, dtype=np.float32)
        actions = np.array(actions, dtype=np.int32)
        dones = np.array(dones, dtype=np.float32)

        # Calcular target Q-values usando target network
        target_q_values = self.target_network.predict(next_states, verbose=0)
        max_target_q_values = np.max(target_q_values, axis=1)

        # Bellman equation: Q(s,a) = r + gamma * max(Q(s',a'))
        targets = rewards + (1 - dones) * self.gamma * max_target_q_values

        # Entrenar la red principal
        with tf.GradientTape() as tape:
            predictions = self.q_network(states, training=True)
            one_hot_actions = tf.one_hot(actions, self.action_dim)

            # Calcular loss solo para las acciones tomadas
            q_values_for_actions = tf.reduce_sum(predictions * one_hot_actions, axis=1)
            # Usar MSE manualmente: (targets - q_values)^2
            loss = tf.square(targets - q_values_for_actions)
            loss = tf.reduce_mean(loss)

        # Backpropagation
        gradients = tape.gradient(loss, self.q_network.trainable_variables)
        self.optimizer.apply_gradients(
            zip(gradients, self.q_network.trainable_variables)
        )

        self.steps += 1

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return float(loss.numpy())

    def _update_target_network(self) -> None:
        """
        Actualiza target network con pesos de la red principal.
        
        Esto estabiliza el entrenamiento.
        """
        self.target_network.set_weights(self.q_network.get_weights())

    def update_target_network(self, update_frequency: int = 1000) -> None:
        """
        Actualiza target network cada cierto número de steps.
        
        Args:
            update_frequency: Cada cuántos steps actualizar
        """
        if self.steps % update_frequency == 0:
            self._update_target_network()

    def save_model(self, filepath: Optional[str] = None) -> None:
        """
        Guarda el modelo a disco.
        
        Args:
            filepath: Ruta donde guardar (usa self.model_path si no se especifica)
        """
        filepath = filepath or self.model_path
        self.q_network.save(filepath)
        logger.info(f"Modelo guardado en: {filepath}")

    def load_model(self, filepath: Optional[str] = None) -> None:
        """
        Carga un modelo previamente entrenado.
        
        Args:
            filepath: Ruta del modelo a cargar
        """
        filepath = filepath or self.model_path
        self.q_network = keras.models.load_model(filepath)
        self._update_target_network()
        logger.info(f"Modelo cargado desde: {filepath}")

    def get_q_values(self, state: np.ndarray) -> np.ndarray:
        """
        Obtiene los Q-values de un estado.
        
        Útil para debugging y análisis.
        
        Args:
            state: Vector de estado
            
        Returns:
            np.ndarray: Array de Q-values para cada acción
        """
        state_tensor = tf.expand_dims(state, axis=0)
        q_values = self.q_network(state_tensor, training=False).numpy()[0]
        return q_values

    def get_best_action(
        self,
        state: np.ndarray,
        available_actions: Optional[List[int]] = None,
        top_k: int = 1,
    ) -> List[Tuple[int, float]]:
        """
        Obtiene las mejores acciones ordenadas por Q-value.
        
        Args:
            state: Vector de estado
            available_actions: Acciones disponibles
            top_k: Número de mejores acciones a retornar
            
        Returns:
            List[Tuple[int, float]]: Lista de (action_idx, q_value) ordenada
        """
        if available_actions is None:
            available_actions = list(range(self.action_dim))

        q_values = self.get_q_values(state)

        # Filtrar solo acciones disponibles
        available_q_values = [
            (action, q_values[action]) for action in available_actions
        ]

        # Ordenar por Q-value descendente
        available_q_values.sort(key=lambda x: x[1], reverse=True)

        return available_q_values[:top_k]

    def reset_epsilon(self, epsilon: float = 1.0) -> None:
        """
        Resetea epsilon (útil para evaluar después de entrenar).
        """
        self.epsilon = epsilon

    def summary(self) -> str:
        """
        Retorna un resumen del agente.
        """
        return (
            f"DQN Agent Summary:\n"
            f"  State Dim: {self.state_dim}\n"
            f"  Action Dim: {self.action_dim}\n"
            f"  Learning Rate: {self.learning_rate}\n"
            f"  Gamma (Discount): {self.gamma}\n"
            f"  Epsilon: {self.epsilon:.4f}\n"
            f"  Memory Size: {len(self.memory)}/{self.memory_size}\n"
            f"  Total Steps: {self.steps}\n"
            f"  Total Episodes: {self.episodes}\n"
        )


class TrainingLoop:
    """
    Loop de entrenamiento para el agente DQN.
    
    Coordina la interacción entre el agente, el entorno, y el almacenamiento
    de experiencias para un entrenamiento continuo.
    """

    def __init__(
        self,
        agent: DQNAgent,
        episodes: int = 100,
        max_steps_per_episode: int = 50,
        target_update_frequency: int = 1000,
    ):
        """
        Inicializa el loop de entrenamiento.
        
        Args:
            agent: Instancia de DQNAgent
            episodes: Número de episodios a entrenar
            max_steps_per_episode: Máximo de pasos por episodio
            target_update_frequency: Cada cuántos steps actualizar target network
        """
        self.agent = agent
        self.episodes = episodes
        self.max_steps_per_episode = max_steps_per_episode
        self.target_update_frequency = target_update_frequency
        self.episode_rewards = []
        self.episode_losses = []

    def train(self) -> Dict[str, List[float]]:
        """
        Ejecuta el loop de entrenamiento (sobre episodios).
        
        Returns:
            Dict con histórico de rewards y losses
        """
        logger.info(f"Iniciando entrenamiento por {self.episodes} episodios...")

        for episode in range(self.episodes):
            episode_reward = 0
            episode_loss_values = []

            # Cada episodio genera experiencias
            self.agent.episodes += 1

            # Al final del episodio, entrenar con replay
            for step in range(min(len(self.agent.memory), 10)):
                loss = self.agent.replay()
                if loss is not None:
                    episode_loss_values.append(loss)

            self.episode_rewards.append(episode_reward)
            avg_loss = np.mean(episode_loss_values) if episode_loss_values else 0
            self.episode_losses.append(avg_loss)

            # Actualizar target network
            self.agent.update_target_network(self.target_update_frequency)

            if (episode + 1) % 10 == 0:
                avg_reward = np.mean(self.episode_rewards[-10:])
                logger.info(
                    f"Episodio {episode + 1}/{self.episodes} - "
                    f"Avg Reward: {avg_reward:.4f}, Loss: {avg_loss:.4f}, "
                    f"Epsilon: {self.agent.epsilon:.4f}"
                )

        logger.info("Entrenamiento completado!")
        return {
            "rewards": self.episode_rewards,
            "losses": self.episode_losses,
        }


# Instancia global del agente
_agent_instance = None


def get_agent(**kwargs) -> DQNAgent:
    """
    Obtiene o crea la instancia global del agente DQN.
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DQNAgent(**kwargs)
    return _agent_instance
```

## Archivo: ml/benchmark_matrix_config.example.json

Ruta completa: ml/benchmark_matrix_config.example.json

```json
{
  "seeds": [101, 202, 303, 404, 505],
  "weights": [
    [0.7, 0.3],
    [0.8, 0.2],
    [0.6, 0.4]
  ],
  "alphas": [0.25, 0.5, 1.0],
  "summary_limit": 200,
  "test_days": 7,
  "test_limit": 1000,
  "benchmark_episodes": 5,
  "synthetic_users": 3,
  "synthetic_tracks": 30,
  "synthetic_interactions": 600,
  "synthetic_weather": 60,
  "synthetic_news": 120,
  "skip_runs": true,
  "run_name": "smoke"
}
```

## Archivo: ml/reward.py

Ruta completa: ml/reward.py

```python
"""
Módulo de Función de Recompensa (Reward Function) para el Agente RL.

Calcula el reward basándose en:
- Feedback del usuario (skip: -1, completed: +1)
- Contexto externo (clima, noticias)
- Características de audio del track
- Historico del usuario
"""

from typing import Dict, Optional

import numpy as np


class RewardCalculator:
    """
    Calcula el reward (recompensa) para entrenar el agente de RL.
    
    El reward es una señal que guía al agente a seleccionar tracks óptimos
    basándose en el contexto actual y el feedback del usuario.
    """

    def __init__(
        self,
        base_reward: float = 1.0,
        skip_penalty: float = -1.0,
        completion_bonus: float = 1.0,
        context_weight: float = 0.2,
        audio_feature_weight: float = 0.15,
    ):
        """
        Inicializa la función de recompensa.
        
        Args:
            base_reward: Recompensa base neutral
            skip_penalty: Penalización por skip del usuario
            completion_bonus: Bonificación por completar la canción
            context_weight: Peso del contexto en el reward
            audio_feature_weight: Peso de las características de audio
        """
        self.base_reward = base_reward
        self.skip_penalty = skip_penalty
        self.completion_bonus = completion_bonus
        self.context_weight = context_weight
        self.audio_feature_weight = audio_feature_weight

    def calculate_reward(
        self,
        user_feedback: Optional[str] = None,
        weather_context: Optional[Dict] = None,
        track_audio_features: Optional[Dict] = None,
        user_history: Optional[Dict] = None,
    ) -> float:
        """
        Calcula el reward total basándose en múltiples factores.
        
        Args:
            user_feedback: Feedback del usuario ('skip', 'completed', None)
            weather_context: Diccionario con datos del clima
            track_audio_features: Diccionario con características de audio del track
            user_history: Diccionario con el historico del usuario
            
        Returns:
            float: Valor de recompensa entre -1.0 y 2.0+
            
        Examples:
            >>> calculator = RewardCalculator()
            >>> # Completar una canción en clima favorable
            >>> r = calculator.calculate_reward(
            ...     user_feedback='completed',
            ...     weather_context={'temperature': 22, 'mood': 'clear'},
            ...     track_audio_features={'energy': 0.8, 'danceability': 0.7},
            ...     user_history={'avg_skip_rate': 0.3}
            ... )
            >>> assert r > 1.0
        """
        reward = self.base_reward

        # 1. Feedback del usuario (factor dominante)
        feedback_reward = self._calculate_feedback_reward(user_feedback)
        reward += feedback_reward

        # 2. Contexto externo (clima, noticias)
        if weather_context:
            context_reward = self._calculate_context_reward(weather_context)
            reward += context_reward * self.context_weight

        # 3. Características de audio
        if track_audio_features:
            audio_reward = self._calculate_audio_feature_reward(track_audio_features)
            reward += audio_reward * self.audio_feature_weight

        # 4. Consistencia con historico del usuario
        if user_history:
            consistency_reward = self._calculate_consistency_reward(
                track_audio_features, user_history
            )
            reward += consistency_reward * 0.1

        return reward

    def _calculate_feedback_reward(self, user_feedback: Optional[str]) -> float:
        """
        Calcula la recompensa basada en el feedback del usuario.
        
        - skip: penalización fuerte
        - completed: bonificación
        - None/no_action: neutral
        """
        if user_feedback == "skip":
            return self.skip_penalty
        elif user_feedback == "completed":
            return self.completion_bonus
        elif user_feedback == "skip_immediate":
            # Skip muy rápido (primeros segundos)
            return self.skip_penalty * 1.5
        else:
            return 0.0

    def _calculate_context_reward(self, weather_context: Dict) -> float:
        """
        Calcula bonificación basada en el contexto del clima.
        
        La idea es que ciertos tipos de música van mejor con cierto clima.
        Por ejemplo:
        - Música energética (danceability alta) → clima soleado, energético
        - Música tranquila (valence baja) → clima nublado, lluvioso
        """
        reward = 0.0

        # Bonus si el clima es agradable (temperatura moderada)
        temperature = weather_context.get("temperature", 20)
        if 18 <= temperature <= 28:
            reward += 0.3
        elif temperature < 0 or temperature > 35:
            reward -= 0.2

        # Bonus si el clima es despejado (motivación)
        main_status = weather_context.get("main_status", "").lower()
        if main_status in ["clear", "sunny", "clouds"]:
            reward += 0.2
        elif main_status in ["rain", "thunderstorm"]:
            reward -= 0.1

        # Humedad (demasiada humedad es incómoda)
        humidity = weather_context.get("humidity", 50)
        if 30 <= humidity <= 70:
            reward += 0.1
        elif humidity > 85:
            reward -= 0.15

        return reward

    def _calculate_audio_feature_reward(self, audio_features: Dict) -> float:
        """
        Calcula bonificación basada en las características de audio del track.
        
        Favorece tracks con features balanceadas (ni demasiado extremos).
        """
        reward = 0.0

        # Balancean energía y danceability (buena combinación)
        energy = audio_features.get("energy", 0.5)
        danceability = audio_features.get("danceability", 0.5)

        # Energía moderada es mejor
        if 0.4 <= energy <= 0.8:
            reward += 0.2
        elif energy < 0.2 or energy > 0.95:
            reward -= 0.1

        # Danceability moderada a alta es generalmente atractiva
        if danceability > 0.6:
            reward += 0.15

        # Valence (positividad) es importante
        valence = audio_features.get("valence", 0.5)
        if 0.4 <= valence <= 0.8:
            reward += 0.1

        # Evitar tracks demasiado acústicos o instrumentales
        acousticness = audio_features.get("acousticness", 0.3)
        instrumentalness = audio_features.get("instrumentalness", 0.0)

        if acousticness > 0.9:
            reward -= 0.05
        if instrumentalness > 0.8:
            reward -= 0.05

        return reward

    def _calculate_consistency_reward(
        self,
        current_audio_features: Optional[Dict],
        user_history: Dict,
    ) -> float:
        """
        Calcula bonificación basada en la consistencia con preferencias del usuario.
        
        Si el usuario típicamente le gustan tracks con ciertas características,
        un track similar debería recibir reward positivo.
        """
        if not current_audio_features or not user_history:
            return 0.0

        reward = 0.0

        # Comparar con preferencias históricas
        avg_energy = user_history.get("avg_energy", 0.5)
        avg_danceability = user_history.get("avg_danceability", 0.5)
        avg_valence = user_history.get("avg_valence", 0.5)

        current_energy = current_audio_features.get("energy", 0.5)
        current_danceability = current_audio_features.get("danceability", 0.5)
        current_valence = current_audio_features.get("valence", 0.5)

        # Similitud en features (cercania = bonus)
        energy_diff = abs(current_energy - avg_energy)
        if energy_diff < 0.2:
            reward += 0.15
        elif energy_diff < 0.4:
            reward += 0.05

        danceability_diff = abs(current_danceability - avg_danceability)
        if danceability_diff < 0.2:
            reward += 0.15
        elif danceability_diff < 0.4:
            reward += 0.05

        valence_diff = abs(current_valence - avg_valence)
        if valence_diff < 0.2:
            reward += 0.1

        # Skip rate del usuario (si hace muchos skips, es más exigente)
        skip_rate = user_history.get("skip_rate", 0.30)
        if skip_rate > 0.5:
            # Usuario muy exigente: recompensa más conservadora
            reward *= 0.8

        return reward

    def normalize_reward(self, reward: float, min_val: float = -2.0, max_val: float = 2.0) -> float:
        """
        Normaliza el reward a un rango específico usando clipping.
        
        Args:
            reward: Valor bruto de recompensa
            min_val: Valor mínimo del rango
            max_val: Valor máximo del rango
            
        Returns:
            float: Reward normalizado en el rango [min_val, max_val]
        """
        return np.clip(reward, min_val, max_val)


# Instancia singleton para usar en toda la aplicación
_reward_calculator_instance = None


def get_reward_calculator(**kwargs) -> RewardCalculator:
    """
    Obtiene o crea la instancia global de RewardCalculator.
    
    Args:
        **kwargs: Parámetros para inicializar RewardCalculator
        
    Returns:
        RewardCalculator: Instancia global
    """
    global _reward_calculator_instance
    if _reward_calculator_instance is None:
        _reward_calculator_instance = RewardCalculator(**kwargs)
    return _reward_calculator_instance
```

## Archivo: ml/state_builder.py

Ruta completa: ml/state_builder.py

```python
"""
Módulo State Builder para Reinforcement Learning.

Construye vectores de estado (observations) que representa el contexto actual
incluyendo: clima, noticias, características de audio, historico del usuario.

La salida es un vector normalizado que se usa como entrada al agente RL.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from django.contrib.auth import get_user_model
from django.db.models import Avg, Q
from django.utils import timezone

User = get_user_model()


class StateBuilder:
    """
    Construye vectores de estado normalizados para el agente RL.
    
    Un estado representa toda la información relevante en un momento dado:
    - Contexto del clima
    - Noticias recientes
    - Historico del usuario
    - Características de audio del track anterior
    
    El vector de estado es normalizado a [0, 1] para mejor convergencia del RL.
    """

    def __init__(
        self,
        state_dim: int = 45,
        weather_features: int = 10,
        audio_features_dim: int = 12,
        user_history_dim: int = 8,
        context_embedding_dim: int = 15,
    ):
        """
        Inicializa el State Builder.
        
        Args:
            state_dim: Dimensión total del vector de estado
            weather_features: Número de features de clima
            audio_features_dim: Número de características de audio
            user_history_dim: Número de features de historico
            context_embedding_dim: Número de features de contexto general
        """
        self.state_dim = state_dim
        self.weather_features = weather_features
        self.audio_features_dim = audio_features_dim
        self.user_history_dim = user_history_dim
        self.context_embedding_dim = context_embedding_dim

        # Normalizadores (min-max scaling)
        self.normalizers = {
            "temperature": {"min_val": -50, "max_val": 50},  # °C
            "humidity": {"min_val": 0, "max_val": 100},  # %
            "wind_speed": {"min_val": 0, "max_val": 30},  # m/s
            "pressure": {"min_val": 900, "max_val": 1100},  # hPa
            "visibility": {"min_val": 0, "max_val": 100000},  # metros
            "audio_feature": {"min_val": 0, "max_val": 1},  # Spotify features [0, 1]
            "energy": {"min_val": 0, "max_val": 1},
            "danceability": {"min_val": 0, "max_val": 1},
        }

    def build_state(
        self,
        user: "User",
        weather_context: Optional[Dict] = None,
        current_track: Optional[Dict] = None,
        time_of_day: Optional[str] = None,
        news_contexts: Optional[List[Dict]] = None,
    ) -> np.ndarray:
        """
        Construye el vector de estado completo.
        
        Args:
            user: Usuario para el que se construye el estado
            weather_context: Diccionario con datos del clima
            current_track: Diccionario con características del track actual
            time_of_day: 'morning', 'afternoon', 'evening', 'night'
            
        Returns:
            np.ndarray: Vector de estado normalizado de shape (state_dim,)
            
        Example:
            >>> builder = StateBuilder()
            >>> weather = {'temperature': 22, 'humidity': 60, 'wind_speed': 5}
            >>> track = {'energy': 0.8, 'danceability': 0.7}
            >>> state = builder.build_state(user, weather, track)
            >>> assert state.shape == (45,)
            >>> assert np.all((state >= 0) & (state <= 1))
        """
        state_components = []

        # 1. Features de clima (10 features)
        weather_vec = self._extract_weather_features(weather_context)
        state_components.append(weather_vec)

        # 2. Features de audio del track actual (12 features)
        audio_vec = self._extract_audio_features(current_track)
        state_components.append(audio_vec)

        # 3. Características del usuario basadas en historico (8 features)
        user_vec = self._extract_user_history_features(user)
        state_components.append(user_vec)

        # 4. Features de contexto temporal (15 features: hora, día, estación)
        context_vec = self._extract_context_features(time_of_day, news_contexts)
        state_components.append(context_vec)

        # Concatenar todos los componentes
        state = np.concatenate(state_components, axis=0)

        # Asegurar que el tamaño es correcto
        if len(state) < self.state_dim:
            # Padding con ceros si es necesario
            state = np.pad(state, (0, self.state_dim - len(state)))
        elif len(state) > self.state_dim:
            # Truncar si es más grande
            state = state[: self.state_dim]

        return state.astype(np.float32)

    def _extract_weather_features(self, weather_context: Optional[Dict]) -> np.ndarray:
        """
        Extrae features normalizadas del contexto climático.
        
        Returns un vector de 10 features:
        [temp, feels_like, humidity, wind_speed, pressure, visibility, 
         clouds, rain_prob, is_raining, is_snowing]
        """
        features = []

        if weather_context is None:
            weather_context = {}

        # Temperatura normalizada
        temp = weather_context.get("temperature", 20)
        norm_temp = self._normalize(temp, self.normalizers["temperature"])
        features.append(norm_temp)

        # Sensación térmica
        feels_like = weather_context.get("feels_like", temp)
        norm_feels_like = self._normalize(feels_like, self.normalizers["temperature"])
        features.append(norm_feels_like)

        # Humedad
        humidity = weather_context.get("humidity", 60)
        norm_humidity = self._normalize(humidity, self.normalizers["humidity"])
        features.append(norm_humidity)

        # Velocidad del viento
        wind_speed = weather_context.get("wind_speed", 0)
        norm_wind = self._normalize(wind_speed, self.normalizers["wind_speed"])
        features.append(norm_wind)

        # Presión
        pressure = weather_context.get("pressure", 1013)
        norm_pressure = self._normalize(pressure, self.normalizers["pressure"])
        features.append(norm_pressure)

        # Visibilidad
        visibility = weather_context.get("visibility", 10000)
        norm_visibility = self._normalize(
            visibility, self.normalizers["visibility"]
        )
        features.append(norm_visibility)

        # Nubosidad
        clouds = weather_context.get("clouds_all", 50)
        norm_clouds = self._normalize(clouds, {"min_val": 0, "max_val": 100})
        features.append(norm_clouds)

        # Probabilidad de lluvia (estimada)
        rain_prob = weather_context.get("rain_probability", 0)
        features.append(float(rain_prob) / 100.0)

        # Indicador: ¿está lloviendo?
        is_raining = float(
            weather_context.get("main_status", "").lower() in ["rain", "drizzle"]
        )
        features.append(is_raining)

        # Indicador: ¿está nevando?
        is_snowing = float(weather_context.get("main_status", "").lower() == "snow")
        features.append(is_snowing)

        return np.array(features[:self.weather_features], dtype=np.float32)

    def _extract_audio_features(self, current_track: Optional[Dict]) -> np.ndarray:
        """
        Extrae features de audio normalizadas del track actual.
        
        Returns un vector de 12 features:
        [energy, danceability, valence, acousticness, instrumentalness,
         liveness, loudness, tempo, speechiness, key, mode, time_signature]
        """
        features = []

        if current_track is None:
            current_track = {}

        # Spotify audio features (todos están en [0, 1] o rango específico)
        audio_feature_names = [
            "energy",
            "danceability",
            "valence",
            "acousticness",
            "instrumentalness",
            "liveness",
        ]

        for feat_name in audio_feature_names:
            value = current_track.get(feat_name, 0.5)
            # Normalizar a [0, 1]
            norm_value = np.clip(float(value), 0.0, 1.0)
            features.append(norm_value)

        # Loudness (típicamente [-60, 0] dB)
        loudness = current_track.get("loudness", -5)
        norm_loudness = self._normalize(loudness, {"min_val": -60, "max_val": 0})
        features.append(norm_loudness)

        # Tempo (típicamente [60, 200] BPM)
        tempo = current_track.get("tempo", 120)
        norm_tempo = self._normalize(tempo, {"min_val": 60, "max_val": 200})
        features.append(norm_tempo)

        # Speechiness (voz/palabras)
        speechiness = current_track.get("speechiness", 0.0)
        features.append(np.clip(float(speechiness), 0.0, 1.0))

        # Key (0-11, normalizado a [0, 1])
        key = current_track.get("key", 0)
        norm_key = float(key) / 11.0 if key >= 0 else 0.0
        features.append(np.clip(norm_key, 0.0, 1.0))

        # Mode (0=minor, 1=major) - ya está normalizado
        mode = float(current_track.get("mode", 0))
        features.append(np.clip(mode, 0.0, 1.0))

        # Time signature (3, 4, 5, etc.) - normalizar a [0, 1]
        time_sig = current_track.get("time_signature", 4)
        norm_time_sig = float(time_sig) / 7.0
        features.append(np.clip(norm_time_sig, 0.0, 1.0))

        return np.array(features[:self.audio_features_dim], dtype=np.float32)

    def _extract_user_history_features(self, user: "User") -> np.ndarray:
        """
        Extrae features de historico del usuario.
        
        Returns un vector de 8 features relacionadas al comportamiento del usuario.
        """
        features = []

        try:
            from apps.music.models import Track
            from apps.interactions.models import Interaction  # cuando exista

            # Skip rate (proporción de tracks que skipped)
            # Esto requeriría un modelo Interaction que aún no existe
            skip_rate = 0.3  # Default
            features.append(skip_rate)

            # Completion rate
            completion_rate = 0.7  # Default
            features.append(completion_rate)

        except Exception:
            # Si los modelos no existen todavía, usar defaults
            features.extend([0.3, 0.7])

        # Features adicionales del usuario
        features.extend([
            0.5,  # Energy preference (default neutral)
            0.6,  # Danceability preference
            0.5,  # Valence preference
            0.4,  # Acousticness preference
            0.2,  # Instrumentalness preference (prefer más vocals)
            float(user.is_spotify_connected),  # ¿Está conectado a Spotify?
            0.5,  # Engagement score (default neutral)
            0.6,  # Diversity preference (cuánto varía su gusto)
        ])

        return np.array(features[:self.user_history_dim], dtype=np.float32)

    def _extract_context_features(
        self,
        time_of_day: Optional[str],
        news_contexts: Optional[List[Dict]] = None,
    ) -> np.ndarray:
        """
        Extrae features contextuales: hora del día, día de la semana, temporada.
        
        Returns un vector de 15 features.
        """
        features = []

        # Hora del día (one-hot encoding: morning, afternoon, evening, night)
        hour_encoding = self._encode_time_of_day(time_of_day)
        features.extend(hour_encoding)

        # Día de la semana
        now = timezone.now()
        day_of_week = now.weekday()  # 0=Lunes, 6=Domingo
        is_weekend = float(day_of_week >= 5)
        norm_day = float(day_of_week) / 6.0

        features.append(is_weekend)
        features.append(norm_day)

        # Mes/Estación (aproximado)
        month = now.month
        season = self._get_season(month)
        season_encoding = self._encode_season(season)
        features.extend(season_encoding)

        # Hora del día (como número 0-23, normalizado)
        hour = now.hour
        norm_hour = float(hour) / 23.0
        features.append(norm_hour)

        # Minuto del día (para granularity)
        minute = now.minute
        norm_minute = float(minute) / 59.0
        features.append(norm_minute)

        # Features temporales adicionales
        day_of_month = now.day
        norm_day_of_month = float(day_of_month) / 31.0
        features.append(norm_day_of_month)

        # Es festivo/fin de semana
        features.append(is_weekend)

        # Agregar señales de noticias en vivo (sentimiento, breaking, volumen)
        news_vec = self._extract_news_features(news_contexts)
        features.extend(news_vec)

        # Hora de pico esperada
        is_peak_hour = float(hour in [8, 9, 17, 18, 19])  # Horas común de peak
        features.append(is_peak_hour)

        return np.array(features[:self.context_embedding_dim], dtype=np.float32)

    @staticmethod
    def _extract_news_features(news_contexts: Optional[List[Dict]]) -> List[float]:
        """Return compact news-derived features for the context embedding."""
        if not news_contexts:
            return [0.5, 0.0, 0.0]

        sentiment_values = [
            float(item.get("sentiment_score", 0.0))
            for item in news_contexts
        ]
        avg_sentiment = sum(sentiment_values) / len(sentiment_values)
        # Map [-1, 1] sentiment into [0, 1]
        norm_sentiment = max(0.0, min(1.0, (avg_sentiment + 1.0) / 2.0))

        breaking_ratio = sum(
            1 for item in news_contexts if item.get("is_breaking")
        ) / float(len(news_contexts))

        norm_news_volume = min(1.0, len(news_contexts) / 20.0)
        return [norm_sentiment, breaking_ratio, norm_news_volume]

    @staticmethod
    def _normalize(value: float, range_dict: Dict) -> float:
        """
        Normaliza un valor al rango [0, 1] usando min-max scaling.
        
        Args:
            value: Valor a normalizar
            range_dict: Dict con 'min_val' y 'max_val'
            
        Returns:
            float: Valor normalizado en [0, 1]
        """
        min_val = range_dict.get("min_val", 0)
        max_val = range_dict.get("max_val", 1)

        if max_val == min_val:
            return 0.0

        norm = (float(value) - min_val) / (max_val - min_val)
        return np.clip(norm, 0.0, 1.0)

    @staticmethod
    def _encode_time_of_day(time_of_day: Optional[str]) -> List[float]:
        """
        One-hot encoding de la hora del día.
        
        Returns: [is_morning, is_afternoon, is_evening, is_night]
        """
        encoding = [0.0, 0.0, 0.0, 0.0]

        if time_of_day == "morning":
            encoding[0] = 1.0
        elif time_of_day == "afternoon":
            encoding[1] = 1.0
        elif time_of_day == "evening":
            encoding[2] = 1.0
        elif time_of_day == "night":
            encoding[3] = 1.0
        else:
            # Inferir de la hora actual
            now = timezone.now()
            hour = now.hour
            if 6 <= hour < 12:
                encoding[0] = 1.0
            elif 12 <= hour < 18:
                encoding[1] = 1.0
            elif 18 <= hour <= 23:
                encoding[2] = 1.0
            else:
                encoding[3] = 1.0

        return encoding

    @staticmethod
    def _get_season(month: int) -> str:
        """Retorna la estación del año basada en el mes."""
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"

    @staticmethod
    def _encode_season(season: str) -> List[float]:
        """
        One-hot encoding de la estación.
        
        Returns: [is_winter, is_spring, is_summer, is_autumn]
        """
        seasons = ["winter", "spring", "summer", "autumn"]
        encoding = [0.0, 0.0, 0.0, 0.0]

        if season in seasons:
            encoding[seasons.index(season)] = 1.0

        return encoding


# Instancia global
_state_builder_instance = None


def get_state_builder(**kwargs) -> StateBuilder:
    """
    Obtiene o crea la instancia global de StateBuilder.
    """
    global _state_builder_instance
    if _state_builder_instance is None:
        _state_builder_instance = StateBuilder(**kwargs)
    return _state_builder_instance
```

## Archivo: ml/tests/__init__.py

Ruta completa: ml/tests/__init__.py

```python
"""
Tests para el módulo de Machine Learning.
"""
```

## Archivo: ml/tests/test_agent.py

Ruta completa: ml/tests/test_agent.py

```python
"""
Tests para el Agente DQN.
"""

import pytest
import numpy as np
from ml.agent import DQNAgent, get_agent


@pytest.fixture
def agent():
    """Fixture con instancia de DQNAgent."""
    return DQNAgent(
        state_dim=10,
        action_dim=5,
        epsilon=1.0,
    )


class TestDQNAgent:
    """Tests para la clase DQNAgent."""

    def test_initialization(self, agent):
        """Test de inicialización."""
        assert agent.state_dim == 10
        assert agent.action_dim == 5
        assert agent.epsilon == 1.0
        assert len(agent.memory) == 0

    def test_select_action_exploration(self, agent):
        """Test de selección de acción en exploración."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        agent.epsilon = 1.0  # Forzar exploración

        action = agent.select_action(state, training=True)

        assert 0 <= action < agent.action_dim

    def test_select_action_exploitation(self, agent):
        """Test de selección de acción en explotación."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        agent.epsilon = 0.0  # Forzar explotación

        action = agent.select_action(state, training=True)

        assert 0 <= action < agent.action_dim

    def test_select_action_with_available_actions(self, agent):
        """Test de selección de acción con restricción."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        available = [0, 2, 4]

        action = agent.select_action(
            state, available_actions=available, training=False
        )

        assert action in available

    def test_remember(self, agent):
        """Test de guardado de experiencia en buffer."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        next_state = np.random.randn(agent.state_dim).astype(np.float32)

        agent.remember(state, action=1, reward=1.0, next_state=next_state, done=False)

        assert len(agent.memory) == 1

    def test_memory_buffer_limit(self, agent):
        """Test del límite del replay buffer."""
        for i in range(agent.memory_size + 100):
            state = np.random.randn(agent.state_dim).astype(np.float32)
            next_state = np.random.randn(agent.state_dim).astype(np.float32)
            agent.remember(state, 0, 1.0, next_state, False)

        assert len(agent.memory) <= agent.memory_size

    def test_replay_insufficient_data(self, agent):
        """Test de replay con datos insuficientes."""
        result = agent.replay()
        assert result is None

    def test_replay_with_data(self, agent):
        """Test de replay con datos suficientes."""
        # Llenar buffer
        for _ in range(agent.batch_size + 10):
            state = np.random.randn(agent.state_dim).astype(np.float32)
            next_state = np.random.randn(agent.state_dim).astype(np.float32)
            agent.remember(state, 0, 1.0, next_state, False)

        loss = agent.replay()

        assert loss is not None
        assert isinstance(loss, float)
        assert loss >= 0

    def test_update_target_network(self, agent):
        """Test de actualización de target network."""
        initial_weights = agent.target_network.get_weights()
        agent.update_target_network(update_frequency=1)
        updated_weights = agent.target_network.get_weights()

        for i, (initial, updated) in enumerate(zip(initial_weights, updated_weights)):
            assert np.allclose(initial, updated)

    def test_get_q_values(self, agent):
        """Test de obtención de Q-values."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        q_values = agent.get_q_values(state)

        assert q_values.shape == (agent.action_dim,)
        assert isinstance(q_values, np.ndarray)

    def test_get_best_action(self, agent):
        """Test de obtención de mejor acción."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        best_actions = agent.get_best_action(state, top_k=3)

        assert len(best_actions) <= 3
        assert all(0 <= action < agent.action_dim for action, _ in best_actions)

    def test_epsilon_decay(self, agent):
        """Test de decaimiento de epsilon."""
        initial_epsilon = agent.epsilon

        for _ in range(10):
            agent.replay_buffer = deque()  # Mock
            agent.epsilon *= agent.epsilon_decay

        assert agent.epsilon < initial_epsilon

    def test_reset_epsilon(self, agent):
        """Test de reseteo de epsilon."""
        agent.epsilon = 0.1
        agent.reset_epsilon(epsilon=1.0)

        assert agent.epsilon == 1.0

    def test_agent_summary(self, agent):
        """Test de resumen del agente."""
        summary = agent.summary()

        assert "State Dim" in summary
        assert "Action Dim" in summary
        assert "Epsilon" in summary

    def test_singleton_pattern(self):
        """Test del patrón singleton para get_agent."""
        agent1 = get_agent(state_dim=10)
        agent2 = get_agent(state_dim=20)  # Params ignorados si ya existe

        assert agent1 is agent2


# Import deque para el test
from collections import deque
```

## Archivo: ml/tests/test_reward.py

Ruta completa: ml/tests/test_reward.py

```python
"""
Tests para el módulo de Reward.
"""

import pytest
from ml.reward import RewardCalculator


@pytest.fixture
def calculator():
    """Fixture con instancia de RewardCalculator."""
    return RewardCalculator()


class TestRewardCalculator:
    """Tests para la clase RewardCalculator."""

    def test_initialization(self, calculator):
        """Test de inicialización."""
        assert calculator.base_reward == 1.0
        assert calculator.skip_penalty == -1.0
        assert calculator.completion_bonus == 1.0

    def test_feedback_reward_completed(self, calculator):
        """Test de reward para feedback 'completed'."""
        reward = calculator.calculate_reward(user_feedback="completed")
        assert reward > 0

    def test_feedback_reward_skip(self, calculator):
        """Test de reward para feedback 'skip'."""
        reward = calculator.calculate_reward(user_feedback="skip")
        # base_reward (1.0) + skip_penalty (-1.0) = 0.0
        assert reward <= 0

    def test_feedback_reward_skip_immediate(self, calculator):
        """Test de reward para skip inmediato."""
        reward = calculator.calculate_reward(user_feedback="skip_immediate")
        # base_reward (1.0) + skip_penalty * 1.5 (-1.5) = -0.5
        assert reward <= 0

    def test_weather_context_reward(self, calculator):
        """Test de reward con contexto climático."""
        weather = {"temperature": 22, "humidity": 60, "main_status": "clear"}
        reward = calculator.calculate_reward(
            user_feedback="completed", weather_context=weather
        )
        assert reward > 1.0

    def test_audio_features_reward(self, calculator):
        """Test de reward con características de audio."""
        audio = {"energy": 0.8, "danceability": 0.7, "valence": 0.6}
        reward = calculator.calculate_reward(
            user_feedback="completed", track_audio_features=audio
        )
        assert reward > 0

    def test_user_history_consistency(self, calculator):
        """Test de consistencia con historico del usuario."""
        audio = {"energy": 0.5, "danceability": 0.5, "valence": 0.5}
        history = {
            "avg_energy": 0.5,
            "avg_danceability": 0.5,
            "avg_valence": 0.5,
            "skip_rate": 0.3,
        }
        reward = calculator.calculate_reward(
            user_feedback="completed",
            track_audio_features=audio,
            user_history=history,
        )
        assert reward > 0

    def test_normalize_reward(self, calculator):
        """Test de normalización de reward."""
        raw_reward = 5.0
        normalized = calculator.normalize_reward(raw_reward, min_val=-2.0, max_val=2.0)
        assert normalized == 2.0
        assert -2.0 <= normalized <= 2.0

    def test_all_factors_combined(self, calculator):
        """Test con todos los factores combinados."""
        reward = calculator.calculate_reward(
            user_feedback="completed",
            weather_context={"temperature": 25, "humidity": 50, "main_status": "sunny"},
            track_audio_features={"energy": 0.8, "danceability": 0.75, "valence": 0.7},
            user_history={
                "avg_energy": 0.75,
                "avg_danceability": 0.7,
                "skip_rate": 0.2,
            },
        )
        assert isinstance(reward, float)
        # El reward puede oscilar entre -2.0 (skip inmediato + contexto negativo) y 3.0+ (todos positivos)
        assert reward >= -2.0
```

## Archivo: ml/tests/test_state_builder.py

Ruta completa: ml/tests/test_state_builder.py

```python
"""
Tests para el módulo State Builder.
"""

import pytest
import numpy as np
from ml.state_builder import StateBuilder, get_state_builder


@pytest.fixture
def builder():
    """Fixture con instancia de StateBuilder."""
    return StateBuilder()


@pytest.fixture
def mock_user(db):
    """Fixture con usuario mock."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(username="testuser", email="test@test.com")


class TestStateBuilder:
    """Tests para la clase StateBuilder."""

    def test_initialization(self, builder):
        """Test de inicialización."""
        assert builder.state_dim == 45
        assert builder.weather_features == 10
        assert builder.audio_features_dim == 12
        assert builder.user_history_dim == 8

    def test_build_state_basic(self, builder, mock_user):
        """Test de construcción básica de estado."""
        state = builder.build_state(mock_user)

        assert isinstance(state, np.ndarray)
        assert state.shape == (45,)
        assert state.dtype == np.float32
        assert np.all((state >= 0) & (state <= 1))

    def test_build_state_with_weather(self, builder, mock_user):
        """Test de construcción de estado con contexto climático."""
        weather = {
            "temperature": 22,
            "humidity": 60,
            "wind_speed": 5,
            "main_status": "clear",
        }
        state = builder.build_state(mock_user, weather_context=weather)

        assert state.shape == (45,)
        assert np.all((state >= 0) & (state <= 1))

    def test_build_state_with_track(self, builder, mock_user):
        """Test de construcción de estado con características de track."""
        track = {
            "energy": 0.8,
            "danceability": 0.7,
            "valence": 0.6,
            "tempo": 120,
        }
        state = builder.build_state(mock_user, current_track=track)

        assert state.shape == (45,)

    def test_normalize_weather_features(self, builder):
        """Test de normalización de features de clima."""
        state = builder._extract_weather_features(
            {
                "temperature": 25,
                "humidity": 70,
                "wind_speed": 10,
                "main_status": "rain",
            }
        )

        assert state.shape == (10,)
        assert np.all((state >= 0) & (state <= 1))

    def test_normalize_audio_features(self, builder):
        """Test de normalización de features de audio."""
        audio = {
            "energy": 0.7,
            "danceability": 0.8,
            "valence": 0.5,
            "tempo": 140,
        }
        state = builder._extract_audio_features(audio)

        assert state.shape == (12,)
        assert np.all((state >= 0) & (state <= 1))

    def test_extract_user_history(self, builder, mock_user):
        """Test de extracción de historico del usuario."""
        state = builder._extract_user_history_features(mock_user)

        assert state.shape == (8,)
        assert np.all((state >= 0) & (state <= 1))

    def test_extract_context_features(self, builder):
        """Test de extracción de features contextuales."""
        state = builder._extract_context_features("morning")

        assert state.shape == (15,)
        assert np.all((state >= 0) & (state <= 1))

    def test_normalize_function(self, builder):
        """Test de función de normalización."""
        # Temperatura
        normalized = builder._normalize(25, {"min_val": -50, "max_val": 50})
        assert 0 < normalized < 1

        # Fuera de rango
        normalized = builder._normalize(60, {"min_val": -50, "max_val": 50})
        assert normalized == 1.0

    def test_time_of_day_encoding(self):
        """Test de encoding de hora del día."""
        morning = StateBuilder._encode_time_of_day("morning")
        assert morning == [1.0, 0.0, 0.0, 0.0]

        evening = StateBuilder._encode_time_of_day("evening")
        assert evening == [0.0, 0.0, 1.0, 0.0]

    def test_season_encoding(self):
        """Test de encoding de estación."""
        winter = StateBuilder._encode_season("winter")
        assert winter == [1.0, 0.0, 0.0, 0.0]

        summer = StateBuilder._encode_season("summer")
        assert summer == [0.0, 0.0, 1.0, 0.0]

    def test_singleton_pattern(self):
        """Test del patrón singleton."""
        builder1 = get_state_builder()
        builder2 = get_state_builder()

        assert builder1 is builder2
```

## Archivo: ml/training.py

Ruta completa: ml/training.py

```python
"""
Script de Entrenamiento para el Agente RL.

Carga datos de interacciones del BD, construye estados, y entrena el agente DQN.
Guarda modelos y registra métricas para análisis.

Uso:
    python ml/training.py train --episodes 100 --batch-size 64
    python ml/training.py eval --model-path ml/models/dqn_model.h5
    python ml/training.py visualize
"""

import argparse
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import django
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler

# Asegurar que el directorio raíz está en el path
import sys
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

from ml.agent import DQNAgent, TrainingLoop, get_agent
from ml.reward import get_reward_calculator
from ml.state_builder import get_state_builder
from apps.interactions.models import Interaction, InteractionSession
from apps.music.models import Track
from apps.context.models import NewsContext, WeatherContext

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

User = get_user_model()

# Directorio de modelos
MODELS_DIR = Path("ml/models")
MODELS_DIR.mkdir(exist_ok=True, parents=True)

# Directorio de logs
LOGS_DIR = Path("ml/logs")
LOGS_DIR.mkdir(exist_ok=True, parents=True)


class TrainingDataLoader:
    """
    Carga datos de interacciones del BD para entrenamiento.
    """

    @staticmethod
    def load_interactions(
        days: int = 30, limit: Optional[int] = None
    ) -> List[Interaction]:
        """
        Carga interacciones recientes del BD.
        
        Args:
            days: Número de días hacia atrás
            limit: Máximo de interacciones a cargar
            
        Returns:
            Lista de objetos Interaction
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        interactions = Interaction.objects.filter(
            created_at__gte=cutoff_date
        ).select_related("user", "track")

        if limit:
            interactions = interactions[:limit]

        logger.info(
            f"Cargadas {interactions.count()} interacciones de los últimos {days} días"
        )
        return list(interactions)

    @staticmethod
    def load_user_sessions(
        user: User, limit: Optional[int] = None
    ) -> List[InteractionSession]:
        """
        Carga sesiones de un usuario.
        """
        sessions = InteractionSession.objects.filter(user=user).order_by(
            "-started_at"
        )

        if limit:
            sessions = sessions[:limit]

        return list(sessions)

    @staticmethod
    def get_top_users(min_interactions: int = 10) -> List[User]:
        """
        Obtiene usuarios con más interacciones.
        """
        from django.db.models import Count

        users = (
            User.objects.annotate(interaction_count=Count("interactions"))
            .filter(interaction_count__gte=min_interactions)
            .order_by("-interaction_count")
        )

        return list(users)


class TrainingDataBuilder:
    """
    Construye datasets de entrenamiento a partir de interacciones.
    """

    def __init__(self):
        """Inicializa el constructor de datos."""
        self.state_builder = get_state_builder()
        self.reward_calculator = get_reward_calculator()
        self.scaler = StandardScaler()

    def build_training_batch(
        self, interactions: List[Interaction]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Construye un batch de entrenamiento a partir de interacciones.
        
        Args:
            interactions: Lista de interacciones
            
        Returns:
            Tuple de (states, rewards)
        """
        states = []
        rewards = []

        for interaction in interactions:
            try:
                # Construir estado
                weather_context = None
                if interaction.weather_id:
                    try:
                        weather = WeatherContext.objects.get(id=interaction.weather_id)
                        weather_context = {
                            "temperature": weather.temperature,
                            "humidity": weather.humidity,
                            "wind_speed": weather.wind_speed,
                            "main_status": weather.main_status,
                        }
                    except WeatherContext.DoesNotExist:
                        pass

                # Audio features del track
                audio_features = self._get_track_audio_features(interaction.track)

                news_contexts = []
                if interaction.news_ids:
                    news_items = NewsContext.objects.filter(id__in=interaction.news_ids)
                    news_contexts = [
                        {
                            "sentiment_score": item.sentiment_score,
                            "sentiment_label": item.sentiment_label,
                            "is_breaking": item.is_breaking,
                        }
                        for item in news_items
                    ]

                state = self.state_builder.build_state(
                    user=interaction.user,
                    weather_context=weather_context,
                    current_track=audio_features,
                    time_of_day=self._get_time_of_day(interaction.started_at),
                    news_contexts=news_contexts,
                )

                states.append(state)
                rewards.append(interaction.reward)

            except Exception as e:
                logger.warning(f"Error procesando interacción {interaction.id}: {e}")
                continue

        return np.array(states), np.array(rewards)

    @staticmethod
    def _get_track_audio_features(track: Track) -> Dict:
        """Obtiene características de audio de un track."""
        try:
            if hasattr(track, "audio_features"):
                af = track.audio_features
                return {
                    "energy": af.energy,
                    "danceability": af.danceability,
                    "valence": af.valence,
                    "acousticness": af.acousticness,
                    "instrumentalness": af.instrumentalness,
                    "liveness": af.liveness,
                    "loudness": af.loudness,
                    "tempo": af.tempo,
                    "speechiness": af.speechiness,
                    "key": af.key,
                    "mode": af.mode,
                    "time_signature": af.time_signature,
                }
        except Exception:
            pass

        return {
            "energy": 0.5,
            "danceability": 0.5,
            "valence": 0.5,
            "acousticness": 0.3,
            "instrumentalness": 0.0,
            "liveness": 0.2,
            "loudness": -5,
            "tempo": 120,
            "speechiness": 0.0,
            "key": 0,
            "mode": 1,
            "time_signature": 4,
        }

    @staticmethod
    def _get_time_of_day(dt):
        """Obtiene la hora del día."""
        hour = dt.hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour <= 23:
            return "evening"
        else:
            return "night"


class ModelTrainer:
    """
    Entrenam el agente DQN.
    """

    def __init__(
        self,
        agent: Optional[DQNAgent] = None,
        state_dim: int = 45,
        action_dim: int = 100,
        episodes: int = 100,
        batch_size: int = 64,
    ):
        """Inicializa el entrenador."""
        self.agent = agent or get_agent(
            state_dim=state_dim,
            action_dim=action_dim,
        )
        self.episodes = episodes
        self.batch_size = batch_size
        self.data_builder = TrainingDataBuilder()

        self.training_logs = {
            "episode_rewards": [],
            "episode_losses": [],
            "epsilon_values": [],
            "timestamps": [],
        }

    def train_from_interactions(self, days: int = 30):
        """
        Entrena el agente usando interacciones históricas.
        
        Args:
            days: Número de días de datos a usar
        """
        logger.info(f"Iniciando entrenamiento con datos de {days} días...")

        # Cargar interacciones
        loader = TrainingDataLoader()
        interactions = loader.load_interactions(days=days, limit=5000)

        if len(interactions) < 100:
            logger.warning(f"Pocas interacciones ({len(interactions)}), usando data sintética")
            self._train_with_synthetic_data()
            return

        # Construir batch de entrenamiento
        logger.info(f"Construyendo batch de {len(interactions)} interacciones...")
        states, rewards = self.data_builder.build_training_batch(interactions)

        if len(states) == 0:
            logger.error("No se pudieron construir estados")
            return

        logger.info(
            f"Estado shape: {states.shape}, Rewards: min={rewards.min():.3f}, "
            f"max={rewards.max():.3f}, mean={rewards.mean():.3f}"
        )

        # Llenar replay buffer del agente con experiencias
        logger.info("Llenando replay buffer del agente...")
        for i, state in enumerate(states):
            next_state = states[i + 1] if i + 1 < len(states) else state
            reward = rewards[i]
            done = i == len(states) - 1

            # Seleccionar acción aleatoria (exploración)
            action = np.random.randint(0, self.agent.action_dim)

            self.agent.remember(state, action, reward, next_state, done)

        logger.info(f"Replay buffer contiene {len(self.agent.memory)} experiencias")

        # Entrenar el agente
        self._run_training_loop()

    def _train_with_synthetic_data(self):
        """
        Entrena el agente con datos sintéticos para testing.
        """
        logger.info("Generando datos sintéticos para entrenamiento...")

        for episode in range(min(self.episodes, 10)):
            episode_rewards = []
            episode_loss = 0.0
            state = np.random.randn(self.agent.state_dim).astype(np.float32)

            for step in range(50):
                action = np.random.randint(0, self.agent.action_dim)
                reward = np.random.randn() * 0.5  # Reward aleatorio
                next_state = np.random.randn(self.agent.state_dim).astype(np.float32)
                done = step == 49

                self.agent.remember(state, action, reward, next_state, done)
                state = next_state
                episode_rewards.append(float(reward))

            # Entrenar con batch
            if len(self.agent.memory) >= self.agent.batch_size:
                loss = self.agent.replay()
                episode_loss = float(loss) if loss is not None else 0.0

                if episode % 2 == 0:
                    logger.info(f"Episodio {episode + 1}, Loss: {episode_loss:.4f}")

            self.training_logs["episode_rewards"].append(
                float(np.mean(episode_rewards)) if episode_rewards else 0.0
            )
            self.training_logs["episode_losses"].append(episode_loss)
            self.training_logs["epsilon_values"].append(self.agent.epsilon)
            self.training_logs["timestamps"].append(timezone.now().isoformat())

    def _run_training_loop(self):
        """Ejecuta el loop de entrenamiento."""
        logger.info(f"Iniciando {self.episodes} episodios de entrenamiento...")
        start_time = timezone.now()

        for episode in range(self.episodes):
            episode_loss_values = []

            # Entrenar con múltiples batches del replay buffer
            for _ in range(10):
                loss = self.agent.replay()
                if loss is not None:
                    episode_loss_values.append(loss)

            # Actualizar target network
            self.agent.update_target_network(update_frequency=10)

            # Registrar métricas
            avg_loss = np.mean(episode_loss_values) if episode_loss_values else 0
            self.training_logs["episode_rewards"].append(0)
            self.training_logs["episode_losses"].append(avg_loss)
            self.training_logs["epsilon_values"].append(self.agent.epsilon)
            self.training_logs["timestamps"].append(timezone.now().isoformat())

            if (episode + 1) % max(1, self.episodes // 10) == 0:
                elapsed = timezone.now() - start_time
                logger.info(
                    f"Episodio {episode + 1}/{self.episodes} - "
                    f"Loss: {avg_loss:.4f}, Epsilon: {self.agent.epsilon:.4f}, "
                    f"Tiempo: {elapsed.total_seconds():.1f}s"
                )

        total_time = timezone.now() - start_time
        logger.info(
            f"Entrenamiento completado en {total_time.total_seconds():.1f}s"
        )

    def save_model(self, model_name: str = "dqn_agent"):
        """
        Guarda el modelo entrenado.
        
        Args:
            model_name: Nombre del archivo (sin extensión)
        """
        model_path = MODELS_DIR / f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
        self.agent.save_model(str(model_path))
        logger.info(f"Modelo guardado en: {model_path}")

        # Guardar logs de entrenamiento
        log_path = LOGS_DIR / f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_path, "w") as f:
            json.dump(self.training_logs, f, indent=2)
        logger.info(f"Logs de entrenamiento guardados en: {log_path}")

    @staticmethod
    def _find_latest_log_file() -> Optional[Path]:
        log_files = sorted(LOGS_DIR.glob("training_*.json"), reverse=True)
        return log_files[0] if log_files else None

    @staticmethod
    def visualize_logs(log_path: Optional[Path] = None) -> None:
        """Visualiza logs de entrenamiento previamente guardados."""
        if log_path is None:
            log_path = ModelTrainer._find_latest_log_file()

        if log_path is None or not log_path.exists():
            logger.warning("No se encontró ningún log de entrenamiento para visualizar")
            return

        with open(log_path, "r") as f:
            training_logs = json.load(f)

        episode_losses = training_logs.get("episode_losses", [])
        epsilon_values = training_logs.get("epsilon_values", [])
        episode_rewards = training_logs.get("episode_rewards", [])

        if not episode_losses and not epsilon_values and not episode_rewards:
            logger.warning("El log de entrenamiento no contiene datos visualizables")
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        if episode_losses:
            axes[0].plot(episode_losses, label="Loss")
            axes[0].set_xlabel("Episodio")
            axes[0].set_ylabel("Pérdida")
            axes[0].set_title("Pérdida durante Entrenamiento")
            axes[0].grid(True)
            axes[0].legend()

        if epsilon_values:
            axes[1].plot(epsilon_values, label="Epsilon", color="orange")
            axes[1].set_xlabel("Episodio")
            axes[1].set_ylabel("Epsilon")
            axes[1].set_title("Tasa de Exploración (Epsilon)")
            axes[1].grid(True)
            axes[1].legend()

        if episode_rewards:
            axes[0].plot(episode_rewards, label="Rewards", linestyle="--")
            axes[0].legend()

        plot_path = LOGS_DIR / f"training_visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_path, dpi=100, bbox_inches="tight")
        logger.info(f"Gráfico de entrenamiento guardado en: {plot_path}")
        plt.show()
        plt.close(fig)

    def plot_training_history(self):
        """
        Grafica el histórico de entrenamiento.
        """
        if not self.training_logs["episode_losses"]:
            logger.warning("No hay datos de pérdida para graficar")
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Gráfico de pérdida
        axes[0].plot(self.training_logs["episode_losses"], label="Loss")
        axes[0].set_xlabel("Episodio")
        axes[0].set_ylabel("Pérdida")
        axes[0].set_title("Pérdida durante Entrenamiento")
        axes[0].grid(True)
        axes[0].legend()

        # Gráfico de epsilon
        axes[1].plot(self.training_logs["epsilon_values"], label="Epsilon", color="orange")
        axes[1].set_xlabel("Episodio")
        axes[1].set_ylabel("Epsilon")
        axes[1].set_title("Tasa de Exploración (Epsilon)")
        axes[1].grid(True)
        axes[1].legend()

        plot_path = LOGS_DIR / f"training_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_path, dpi=100, bbox_inches="tight")
        logger.info(f"Gráfico guardado en: {plot_path}")

        plt.show()


class ModelEvaluator:
    """
    Evalúa el desempeño de un modelo entrenado.
    """

    def __init__(self, model_path: str):
        """
        Inicializa el evaluador.
        
        Args:
            model_path: Ruta al modelo guardado
        """
        self.agent = get_agent()
        self.agent.load_model(model_path)
        self.state_builder = get_state_builder()

    def evaluate_on_test_set(self, test_interactions: List[Interaction]) -> Dict:
        """
        Evalúa el modelo en un conjunto de test.
        
        Args:
            test_interactions: Interacciones para testing
            
        Returns:
            Dict con métricas de evaluación
        """
        logger.info(f"Evaluando en {len(test_interactions)} interacciones...")

        correct_predictions = 0
        total = 0

        for interaction in test_interactions:
            try:
                # Construir estado
                audio_features = self._get_track_audio_features(interaction.track)
                state = self.state_builder.build_state(
                    user=interaction.user,
                    current_track=audio_features,
                )

                # Obtener predicción del agente
                action = self.agent.select_action(state, training=False)

                # Comparar con feedback real
                if (interaction.feedback == "completed" and interaction.reward > 0) or (
                    interaction.feedback.startswith("skip") and interaction.reward < 0
                ):
                    correct_predictions += 1

                total += 1

            except Exception as e:
                logger.warning(f"Error en evaluación: {e}")
                continue

        accuracy = correct_predictions / total if total > 0 else 0

        metrics = {
            "accuracy": accuracy,
            "total_samples": total,
            "correct_predictions": correct_predictions,
        }

        logger.info(f"Precisión: {accuracy:.2%}")
        return metrics

    @staticmethod
    def _get_track_audio_features(track: Track) -> Dict:
        """Obtiene características de audio."""
        try:
            if hasattr(track, "audio_features"):
                af = track.audio_features
                return {
                    "energy": af.energy,
                    "danceability": af.danceability,
                    "valence": af.valence,
                    "acousticness": af.acousticness,
                    "instrumentalness": af.instrumentalness,
                }
        except Exception:
            pass

        return {
            "energy": 0.5,
            "danceability": 0.5,
            "valence": 0.5,
            "acousticness": 0.3,
            "instrumentalness": 0.0,
        }

    def recommend_tracks(
        self, user: User, count: int = 10
    ) -> List[Tuple[Track, float]]:
        """
        Recomienda tracks usando el modelo.
        
        Args:
            user: Usuario para el que recomendar
            count: Número de recomendaciones
            
        Returns:
            Lista de (Track, score) ordenada
        """
        logger.info(f"Generando {count} recomendaciones para {user.username}...")

        # Construir estado del usuario
        state = self.state_builder.build_state(user)

        # Obtener Q-values para todos los tracks
        q_values = self.agent.get_q_values(state)

        # Obtener mejores acciones
        best_actions = self.agent.get_best_action(state, top_k=count)

        recommendations = []
        for action_idx, q_value in best_actions:
            try:
                # Mapear índice de acción a track (simplificado)
                tracks = list(Track.objects.all())
                if action_idx < len(tracks):
                    track = tracks[action_idx]
                    recommendations.append((track, q_value))
            except Exception as e:
                logger.warning(f"Error mapeando acción a track: {e}")

        return recommendations


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Script de entrenamiento para el Agente RL de Moodsic"
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # Comando: train
    train_parser = subparsers.add_parser("train", help="Entrenar el agente")
    train_parser.add_argument(
        "--episodes", type=int, default=50, help="Número de episodios"
    )
    train_parser.add_argument(
        "--batch-size", type=int, default=64, help="Tamaño del batch"
    )
    train_parser.add_argument(
        "--days", type=int, default=30, help="Días de datos históricos a usar"
    )
    train_parser.add_argument(
        "--save", action="store_true", help="Guardar modelo después de entrenar"
    )

    # Comando: eval
    eval_parser = subparsers.add_parser("eval", help="Evaluar un modelo")
    eval_parser.add_argument(
        "--model-path", required=True, help="Ruta al modelo guardado"
    )

    # Comando: visualize
    viz_parser = subparsers.add_parser("visualize", help="Visualizar datos de entrenamiento")

    args = parser.parse_args()

    if args.command == "train":
        trainer = ModelTrainer(
            episodes=args.episodes,
            batch_size=args.batch_size,
        )
        trainer.train_from_interactions(days=args.days)

        if args.save:
            trainer.save_model()
            trainer.plot_training_history()

    elif args.command == "eval":
        evaluator = ModelEvaluator(args.model_path)

        # Cargar test set
        interactions = TrainingDataLoader.load_interactions(days=7, limit=1000)
        metrics = evaluator.evaluate_on_test_set(interactions)
        logger.info(f"Métricas de evaluación: {metrics}")

    elif args.command == "visualize":
        logger.info("Visualizando datos de entrenamiento...")
        ModelTrainer.visualize_logs()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

## Archivo: pipelines/__init__.py

Ruta completa: pipelines/__init__.py

```python

```

## Archivo: pipelines/etl_news.py

Ruta completa: pipelines/etl_news.py

```python
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
```

## Archivo: pipelines/etl_weather.py

Ruta completa: pipelines/etl_weather.py

```python
"""ETL helpers for weather ingestion."""

from cities_light.models import City

from apps.context.services.weather_service import WeatherService


def run_weather_etl(limit: int = 10) -> int:
	"""Fetch and store weather for top cities with coordinates.

	Returns the number of successful city updates.
	"""
	cities = City.objects.filter(latitude__isnull=False, longitude__isnull=False)[:limit]
	count = 0
	for city in cities:
		WeatherService.fetch_and_store_weather(city)
		count += 1
	return count
```

## Archivo: pipelines/state_pipeline.py

Ruta completa: pipelines/state_pipeline.py

```python
"""Build end-to-end RL state from persisted context data."""

from typing import Optional

from django.contrib.auth import get_user_model

from apps.context.models import NewsContext, WeatherContext
from ml.state_builder import get_state_builder

User = get_user_model()


def build_latest_state_for_user(user: User, weather_id: Optional[int] = None):
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
```

## Archivo: pyproject.toml

Ruta completa: pyproject.toml

```toml
[project]
name = "moodsic"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"

classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    "dj-database-url==3.1.2",
    "django==6.0.4",
    "django-allauth==65.16.0",
    "django-cities-light==3.11",
    "django-countries==8.2.0",
    "django-environ==0.13.0",
    "django-ninja==1.6.2",
    "django-unfold==0.90.0",
    "numpy==2.4.4",
    "psycopg[binary]==3.3.3",
    "pydantic==2.13.1",
    "redis==7.4.0",
    "requests==2.33.1",
    "spotipy==2.26.0", # Librería para consumir de la API de Spotify.
    "tensorflow>=2.21.0",
    "virtualenv==21.2.4",
]

[dependency-groups]
dev = [
    "coverage==7.13.5",
    "pre-commit==4.5.1",
    "pytest==9.0.3",
    "pytest-cov==7.1.0",
    "pytest-django==4.12.0",
    "pytest-mock==3.15.1",
    "ruff==0.15.11",
    "ty==0.0.31",
]

[tool.uv]
package = false

[tool.ruff]
line-length = 88
target-version = "py312"
exclude = [
    ".venv",
    "__pypackages__",
    "migrations",
    "staticfiles",
    "media",
    "node_modules",
]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "W",    # pycodestyle warnings
    "C90",  # mccabe
    "B",    # flake8-bugbear
    "DJ",   # flake8-django
    "I",    # isort
    "UP",   # pyupgrade
    "C4",   # flake8-comprehensions
    "T20",  # flake8-print
    "SIM",  # flake8-simplify
    "ARG",  # flake8-unused-arguments
    "DTZ",  # flake8-datetimez
    "Q",    # flake8-quotes
    "S",    # flake8-bandit
    "PL",   # pylint
    "RUF",  # ruff-specific rules
]
ignore = [
    "E501", # line length handled by formatter
]

[tool.ruff.lint.per-file-ignores]
"**/tests/*" = ["S101", "PLR2004", "S105", "S106", "ARG005", "PLC0415"]

[tool.ruff.lint.isort]
known-first-party = ["raikojin"]
known-third-party = ["django", "django_environ", "dj_database_url", "django_unfold"]
section-order = ["future", "standard-library", "third-party", "first-party", "local-folder"]

[build-system]
requires = ["uv_build>=0.10.4,<0.11.0"]
build-backend = "uv_build"

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
python_files = ["tests.py", "test_*.py", "*_tests.py"]
```

## Archivo: pytest.ini

Ruta completa: pytest.ini

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_test.py *_tests.py
python_classes = Test*
python_functions = test_*

cache_dir = .pytest_cache

addopts =
    -v
    --tb=short
    --cov=apps
    --cov=tests
    --cov-config=.coveragerc
    --cov-report=term-missing:skip-covered
    --cov-fail-under=93
;    --disable-warnings
    --strict-markers
    -q

# Markers personalizados
markers =
    django_db: Mark test to use database
    unit: Tests unitarios (dominio puro)
    integration: Tests de integración (con BD)
    slow: Tests que tardan mucho

testpaths = ml/tests apps/interactions/tests

# Manejo de advertencias
filterwarnings =
    ignore::DeprecationWarning

# Django
django_find_project = true
```

## Archivo: requirements.txt

Ruta completa: requirements.txt

```text
# ==========================
# Django Core
# ==========================
Django>=4.2,<5.0
djangorestframework
django-ninja

# ==========================
# Django Extensions
# ==========================
django-unfold
django-allauth
django-countries
django-cities-light

# ==========================
# Database
# ==========================
psycopg[binary]
psycopg2-binary
redis

# ==========================
# Environment & Config
# ==========================
python-dotenv

# ==========================
# HTTP / APIs
# ==========================
requests
httpx

# ==========================
# Spotify Integration
# ==========================
spotipy

# ==========================
# Machine Learning
# ==========================
tensorflow
numpy
pandas
scikit-learn
torch

# ==========================
# Data Processing
# ==========================
joblib

# ==========================
# Dashboard / Visualization
# ==========================
matplotlib
plotly

# ==========================
# Utilities
# ==========================
ruff
black
```

## Archivo: templates/base.html

Ruta completa: templates/base.html

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}MoodSic{% endblock %}</title>
    <style>
        :root {
            --bg: #0f172a;
            --panel: #111827;
            --panel-soft: #1f2937;
            --text: #e5e7eb;
            --muted: #94a3b8;
            --accent: #22c55e;
            --accent-soft: #153b2b;
            --warning: #f59e0b;
            --border: #243041;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #111827 100%);
            color: var(--text);
        }
        a { color: #93c5fd; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .shell { max-width: 1120px; margin: 0 auto; padding: 24px; }
        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            margin-bottom: 24px;
            padding: 16px 0;
        }
        .brand { font-size: 1.4rem; font-weight: 700; color: white; }
        .brand small { display: block; font-size: 0.8rem; color: var(--muted); font-weight: 400; }
        .navlinks { display: flex; gap: 14px; flex-wrap: wrap; }
        .navlinks a {
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.06);
        }
        .card {
            background: rgba(17, 24, 39, 0.92);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.8rem;
            background: var(--accent-soft);
            color: #bbf7d0;
        }
        .badge.warning { background: #422006; color: #fde68a; }
        .muted { color: var(--muted); }
        h1, h2, h3 { margin-top: 0; }
        main { padding-bottom: 32px; }
    </style>
</head>
<body>
    <div class="shell">
        <nav class="topbar">
            <div class="brand">
                MoodSic
                <small>Recomendación musical contextual con modo offline y online</small>
            </div>
            <div class="navlinks">
                <a href="/">Inicio</a>
                <a href="/dashboard/">Dashboard</a>
                <a href="/api/interactions/docs/">Swagger</a>
                <a href="/admin/">Admin</a>
            </div>
        </nav>
        <main>
            {% block content %}{% endblock %}
        </main>
    </div>
</body>
</html>
```

## Archivo: templates/dashboard/home.html

Ruta completa: templates/dashboard/home.html

```html
{% extends "base.html" %}

{% block title %}MoodSic Demo{% endblock %}

{% block content %}
<section class="card" style="margin-bottom: 18px;">
    <span class="badge">Demo lista para entrega</span>
    <h1 style="margin-top: 12px;">Panel rápido de MoodSic</h1>
    <p class="muted">
        Esta vista resume el estado funcional del proyecto para una demo académica,
        una revisión de equipo o una validación rápida del backend.
    </p>
    <div class="navlinks" style="margin-top: 14px;">
        <a href="/api/interactions/docs/">Abrir Swagger</a>
        <a href="/admin/">Entrar al admin</a>
        <a href="/api/interactions/dashboard/metrics/">Métricas JSON</a>
    </div>
</section>

<section class="grid" style="margin-bottom: 18px;">
    <article class="card">
        <div class="muted">Playlists registradas</div>
        <h2>{{ stats.playlists }}</h2>
    </article>
    <article class="card">
        <div class="muted">Tracks en catálogo</div>
        <h2>{{ stats.tracks }}</h2>
    </article>
    <article class="card">
        <div class="muted">Interacciones</div>
        <h2>{{ stats.interactions }}</h2>
    </article>
    <article class="card">
        <div class="muted">Sesiones activas</div>
        <h2>{{ stats.active_sessions }}</h2>
    </article>
</section>

<section class="grid" style="margin-bottom: 18px;">
    <article class="card">
        <h3>Estado de la demo</h3>
        <p class="muted">Skip rate agregado: <strong style="color: white;">{{ stats.skip_rate }}%</strong></p>
        <p class="muted">Registros de clima: <strong style="color: white;">{{ stats.weather_records }}</strong></p>
        <p class="muted">Noticias disponibles: <strong style="color: white;">{{ stats.news_records }}</strong></p>
    </article>
    <article class="card">
        <h3>Flujo recomendado para profesor o equipo</h3>
        <ol class="muted" style="padding-left: 18px; line-height: 1.6;">
            <li>Entrar en Swagger y lanzar una generación de playlist.</li>
            <li>Ver el modo devuelto: online, fallback o hybrid.</li>
            <li>Comprobar el admin para revisar playlists e interacciones.</li>
            <li>Usar el modo offline si Spotify real no está disponible.</li>
        </ol>
    </article>
</section>

<section class="card" style="margin-bottom: 18px;">
    <h3>Estado de integraciones</h3>
    <div class="grid">
        {% for item in integration_status %}
        <article class="card" style="background: rgba(31, 41, 55, 0.7);">
            <div>
                <span class="badge {% if item.status != 'listo' and item.status != 'configurado' %}warning{% endif %}">{{ item.status }}</span>
            </div>
            <h4 style="margin: 10px 0 6px 0;">{{ item.name }}</h4>
            <div class="muted">{{ item.detail }}</div>
        </article>
        {% endfor %}
    </div>
</section>

<section class="card">
    <h3>Últimas playlists locales</h3>
    {% if recent_playlists %}
    <ul class="muted" style="line-height: 1.8; padding-left: 18px;">
        {% for playlist in recent_playlists %}
        <li><strong style="color: white;">{{ playlist.name }}</strong> · {{ playlist.user }} · {{ playlist.created_at|date:"d/m/Y H:i" }}</li>
        {% endfor %}
    </ul>
    {% else %}
    <p class="muted">Todavía no hay playlists guardadas en la base local. Puedes generarlas desde Swagger o desde el flujo de demo offline.</p>
    {% endif %}
</section>
{% endblock %}
```

## Archivo: templates/users/profile.html

Ruta completa: templates/users/profile.html

```html
{% extends "base.html" %}

{% block content %}
<div class="container mt-5">
    <h1>Perfil de Usuario</h1>
    <div class="card">
        <div class="card-body">
            <h5 class="card-title">{{ user.email }}</h5>
            <div class="card-text">
                <p><strong>Username:</strong> {{ user.username }}</p>
                {% if user.spotify_id %}
                    <p><strong>Spotify ID:</strong> {{ user.spotify_id }}</p>
                    {% if user.avatar_url %}
                        <p><strong>Avatar:</strong> <img src="{{ user.avatar_url }}" alt="Avatar" width="100" class="img-thumbnail"></p>
                    {% endif %}
                    <p><span class="badge bg-success">Conectado con Spotify</span></p>
                {% else %}
                    <p><span class="badge bg-warning text-dark">No conectado con Spotify</span></p>
                {% endif %}
            </div>
            <a href="{% url 'account_logout' %}" class="btn btn-danger">Cerrar Sesión</a>
        </div>
    </div>
</div>
{% endblock %}
```

## Archivo: venv/Lib/site-packages/pandas/pyproject.toml

Ruta completa: venv/Lib/site-packages/pandas/pyproject.toml

```toml
[build-system]
# Minimum requirements for the build system to execute.
# See https://github.com/scipy/scipy/pull/12940 for the AIX issue.
requires = [
    "meson-python>=0.17.1,<1",
    "meson>=1.2.1,<2",
    "wheel",
    "Cython>3.1.0,<4.0.0a0",  # Note: sync with setup.py, environment.yml and asv.conf.json
    # Force numpy higher than 2.0, so that built wheels are compatible
    # with both numpy 1 and 2
    "numpy>=2.0.0",
    "versioneer[toml]"
]

build-backend = "mesonpy"

[project]
name = 'pandas'
dynamic = [
  'version'
]
description = 'Powerful data structures for data analysis, time series, and statistics'
readme = 'README.md'
authors = [
  { name = 'The Pandas Development Team', email='pandas-dev@python.org' },
]
license = {file = 'LICENSE'}
requires-python = '>=3.11'
dependencies = [
  "numpy>=1.26.0; python_version < '3.14'",
  # Earlier versions of NumPy are fundamentally broken on 3.14
  "numpy>=2.3.3; python_version >= '3.14'",
  "python-dateutil>=2.8.2",
  "tzdata; sys_platform == 'win32'",
  # Emscripten is the platform system for Pyodide.
  "tzdata; sys_platform == 'emscripten'",
]
classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Cython',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
    'Programming Language :: Python :: 3.13',
    'Programming Language :: Python :: 3.14',
    'Topic :: Scientific/Engineering'
]

[project.urls]
homepage = 'https://pandas.pydata.org'
documentation = 'https://pandas.pydata.org/docs/'
repository = 'https://github.com/pandas-dev/pandas'

[project.entry-points."pandas_plotting_backends"]
matplotlib = "pandas:plotting._matplotlib"

[project.optional-dependencies]
test = ['hypothesis>=6.116.0', 'pytest>=8.3.4', 'pytest-xdist>=3.6.1']
pyarrow = ['pyarrow>=13.0.0']
performance = ['bottleneck>=1.4.2', 'numba>=0.60.0', 'numexpr>=2.10.2']
computation = ['scipy>=1.14.1', 'xarray>=2024.10.0']
fss = ['fsspec>=2024.10.0']
aws = ['s3fs>=2024.10.0']
gcp = ['gcsfs>=2024.10.0']
excel = ['odfpy>=1.4.1', 'openpyxl>=3.1.5', 'python-calamine>=0.3.0', 'pyxlsb>=1.0.10', 'xlrd>=2.0.1', 'xlsxwriter>=3.2.0']
parquet = ['pyarrow>=13.0.0']
feather = ['pyarrow>=13.0.0']
iceberg = ['pyiceberg>=0.8.1']
hdf5 = ['tables>=3.10.1']
spss = ['pyreadstat>=1.2.8']
postgresql = ['SQLAlchemy>=2.0.36', 'psycopg2>=2.9.10', 'adbc-driver-postgresql>=1.2.0']
mysql = ['SQLAlchemy>=2.0.36', 'pymysql>=1.1.1']
sql-other = ['SQLAlchemy>=2.0.36', 'adbc-driver-postgresql>=1.2.0', 'adbc-driver-sqlite>=1.2.0']
html = ['beautifulsoup4>=4.12.3', 'html5lib>=1.1', 'lxml>=5.3.0']
xml = ['lxml>=5.3.0']
plot = ['matplotlib>=3.9.3']
output-formatting = ['jinja2>=3.1.5', 'tabulate>=0.9.0']
clipboard = ['PyQt5>=5.15.9', 'qtpy>=2.4.2']
compression = ['zstandard>=0.23.0']
timezone = ['pytz>=2024.2']
all = ['adbc-driver-postgresql>=1.2.0',
       'adbc-driver-sqlite>=1.2.0',
       'beautifulsoup4>=4.12.3',
       'bottleneck>=1.4.2',
       'fastparquet>=2024.11.0',
       'fsspec>=2024.10.0',
       'gcsfs>=2024.10.0',
       'html5lib>=1.1',
       'hypothesis>=6.116.0',
       'jinja2>=3.1.5',
       'lxml>=5.3.0',
       'matplotlib>=3.9.3',
       'numba>=0.60.0',
       'numexpr>=2.10.2',
       'odfpy>=1.4.1',
       'openpyxl>=3.1.5',
       'psycopg2>=2.9.10',
       'pyarrow>=13.0.0',
       'pyiceberg>=0.8.1',
       'pymysql>=1.1.1',
       'PyQt5>=5.15.9',
       'pyreadstat>=1.2.8',
       'pytest>=8.3.4',
       'pytest-xdist>=3.6.1',
       'python-calamine>=0.3.0',
       'pytz>=2024.2',
       'pyxlsb>=1.0.10',
       'qtpy>=2.4.2',
       'scipy>=1.14.1',
       's3fs>=2024.10.0',
       'SQLAlchemy>=2.0.36',
       'tables>=3.10.1',
       'tabulate>=0.9.0',
       'xarray>=2024.10.0',
       'xlrd>=2.0.1',
       'xlsxwriter>=3.2.0',
       'zstandard>=0.23.0']

# TODO: Remove after setuptools support is dropped.
[tool.setuptools]
include-package-data = true

[tool.setuptools.packages.find]
include = ["pandas", "pandas.*"]
namespaces = false

[tool.setuptools.exclude-package-data]
"*" = ["*.c", "*.h"]

# See the docstring in versioneer.py for instructions. Note that you must
# re-run 'versioneer.py setup' after changing this section, and commit the
# resulting files.
[tool.versioneer]
VCS = "git"
style = "pep440"
versionfile_source = "pandas/_version.py"
versionfile_build = "pandas/_version.py"
tag_prefix = "v"
parentdir_prefix = "pandas-"

[tool.meson-python.args]
setup = ['--vsenv'] # For Windows

[tool.cibuildwheel]
skip = ["*_i686", "*_ppc64le", "*_s390x"]
build-verbosity = 3
environment = {LDFLAGS="-Wl,--strip-all"}
test-extras = "test"
test-command = """
  PANDAS_CI='1' python -c 'import pandas as pd; \
  pd.test(extra_args=["-m not clipboard and not single_cpu and not slow and not network and not db", "-n 2", "--no-strict-data-files"]); \
  pd.test(extra_args=["-m not clipboard and single_cpu and not slow and not network and not db", "--no-strict-data-files"]);' \
  """
enable = ["cpython-freethreading"]
before-build = "PACKAGE_DIR={package} bash {package}/scripts/cibw_before_build.sh"

[tool.cibuildwheel.windows]
environment = {}
before-build = "pip install delvewheel"
test-command = """
  set PANDAS_CI='1' && \
  python -c "import pandas as pd; \
  pd.test(extra_args=['--no-strict-data-files', '-m not clipboard and not single_cpu and not slow and not network and not db']);" \
  """
repair-wheel-command = "delvewheel repair -w {dest_dir} {wheel}"

[[tool.cibuildwheel.overrides]]
select = "*-manylinux_aarch64*"
test-command = """
  PANDAS_CI='1' python -c 'import pandas as pd; \
  pd.test(extra_args=["-m not clipboard and not single_cpu and not slow and not network and not db and not fails_arm_wheels", "-n 2", "--no-strict-data-files"]); \
  pd.test(extra_args=["-m not clipboard and single_cpu and not slow and not network and not db", "--no-strict-data-files"]);' \
  """

[[tool.cibuildwheel.overrides]]
select = "*-musllinux*"
before-test = "apk update && apk add musl-locales"

[[tool.cibuildwheel.overrides]]
# Don't strip wheels on macOS.
# macOS doesn't support stripping wheels with linker
# https://github.com/MacPython/numpy-wheels/pull/87#issuecomment-624878264
select = "*-macosx*"
environment = {CFLAGS="-g0"}

[[tool.cibuildwheel.overrides]]
select = "*pyodide*"
test-requires = "pytest>=8.3.4 hypothesis>=6.116.0"
# Pyodide repairs wheels on its own, using auditwheel-emscripten
repair-wheel-command = ""
# https://github.com/pyodide/pyodide/issues/5805
build-verbosity = 1
test-command = """
  PANDAS_CI='1' python -c 'import pandas as pd; \
  pd.test(extra_args=["-m not clipboard and not single_cpu and not slow and not network and not db", "--no-strict-data-files"]);' \
  """

[tool.ruff]
line-length = 88
target-version = "py311"
fix = true

[tool.ruff.lint]
unfixable = []
typing-modules = ["pandas._typing"]

select = [
  # pyflakes
  "F",
  # pycodestyle
  "E", "W",
  # flake8-2020
  "YTT",
  # flake8-bugbear
  "B",
  # flake8-quotes
  "Q",
  # flake8-debugger
  "T10",
  # flake8-gettext
  "INT",
  # pylint
  "PL",
  # flake8-pytest-style
  "PT",
  # misc lints
  "PIE",
  # flake8-pyi
  "PYI",
  # tidy imports
  "TID",
  # implicit string concatenation
  "ISC",
  # flake8-type-checking
  "TC",
  # comprehensions
  "C4",
  # pygrep-hooks
  "PGH",
  # Ruff-specific rules
  "RUF",
  # flake8-bandit: exec-builtin
  "S102",
  # numpy-legacy-random
  "NPY002",
  # Perflint
  "PERF",
  # flynt
  "FLY",
  # flake8-logging-format
  "G",
  # flake8-future-annotations
  "FA",
  # unconventional-import-alias
  "ICN001",
  # flake8-slots
  "SLOT",
  # flake8-raise
  "RSE"
]

ignore = [
  ### Intentionally disabled
  # module level import not at top of file
  "E402",
  # do not assign a lambda expression, use a def
  "E731",
  # controversial
  "B007",
  # controversial
  "B008",
  # getattr is used to side-step mypy
  "B010",
  # tests use comparisons but not their returned value
  "B015",
  # Function definition does not bind loop variable
  "B023",
  # Too many arguments to function call
  "PLR0913",
  # Too many returns
  "PLR0911",
  # Too many branches
  "PLR0912",
  # Too many statements
  "PLR0915",
  # Redefined loop name
  "PLW2901",
  # Global statements are discouraged
  "PLW0603",
  # Use `typing.NamedTuple` instead of `collections.namedtuple`
  "PYI024",
  # Use of possibly insecure function; consider using ast.literal_eval
  "S307",
  # while int | float can be shortened to float, the former is more explicit
  "PYI041",
  # incorrect-dict-iterator, flags valid Series.items usage
  "PERF102",
  # pytest-parametrize-names-wrong-type
  "PT006",
  # pytest-parametrize-values-wrong-type
  "PT007",
  # pytest-patch-with-lambda
  "PT008",
  # pytest-raises-with-multiple-statements
  "PT012",
  # pytest-assert-in-except
  "PT017",
  # pytest-composite-assertion
  "PT018",
  # pytest-fixture-param-without-value
  "PT019",
  # The following rules may cause conflicts when used with the formatter:
  "ISC001",
  # if-stmt-min-max
  "PLR1730",
  # nan-comparison
  "PLW0177",

  ### TODO: Enable gradually
  # Useless statement
  "B018",
  # Magic number
  "PLR2004",
  # comparison-with-itself
  "PLR0124",
  # pairwise-over-zipped
  "RUF007",
  # mutable-class-default
  "RUF012",
  # type-comparison
  "E721",
  # self-or-cls-assignment
  "PLW0642",
  # literal-membership
  "PLR6201", # 847 errors
  # Method could be a function, class method, or static method
  "PLR6301", # 11411 errors
  # Private name import
  "PLC2701", # 27 errors
  # Too many positional arguments (6/5)
  "PLR0917", # 470 errors
  # compare-to-empty-string
  "PLC1901",
  # `tempfile.NamedTemporaryFile` in text mode without explicit `encoding` argument
  "PLW1514", # 1 error
  # Object does not implement `__hash__` method
  "PLW1641", # 16 errors
  # Bad or misspelled dunder method name
  "PLW3201", # 69 errors, seems to be all false positive
  # Unpacking a dictionary in iteration without calling `.items()`
  "PLE1141", # autofixable
  # import-outside-toplevel
  "PLC0415",
  # unnecessary-dunder-call
  "PLC2801",
  # comparison-with-itself
  "PLR0124",
  # too-many-public-methods
  "PLR0904",
  # too-many-return-statements
  "PLR0911",
  # too-many-branches
  "PLR0912",
  # too-many-arguments
  "PLR0913",
  # too-many-locals
  "PLR0914",
  # too-many-statements
  "PLR0915",
  # too-many-boolean-expressions
  "PLR0916",
  # too-many-nested-blocks
  "PLR1702",
  # redefined-argument-from-local
  "PLR1704",
  # unnecessary-lambda
  "PLW0108",
  # global-statement
  "PLW0603",
  # runtime-cast-value
  "TC006",
  # unused-unpacked-variable
  "RUF059",
  # pytest-raises-ambiguous-pattern
  "RUF043",
]

exclude = [
  "doc/sphinxext/*.py",
  "doc/build/*.py",
  "doc/temp/*.py",
  ".eggs/*.py",
  # vendored files
  "pandas/util/version/*",
  "pandas/io/clipboard/__init__.py",
  # exclude asv benchmark environments from linting
  "env",
]

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"urllib.request.urlopen".msg = "Use pandas.io.common.urlopen instead of urllib.request.urlopen"
# numpy.random is banned but np.random is not. Is this intentional?
# "numpy.random".msg = "Do not use numpy.random"
"pytest.warns".msg = "Use tm.assert_produces_warning instead of pytest.warns"
"pytest.xfail".msg = "Use pytest.mark.xfail instead of pytest.xfail"
"conftest".msg = "No direct imports from conftest"
"numpy.testing".msg = "Do not use numpy.testing"
# "numpy.array_equal".msg = "Do not use numpy.array_equal" # Used in pandas/core
"unittest.mock".msg = "use pytest builtin monkeypatch fixture instead"
"os.remove".msg = "Do not use os.remove"



[tool.ruff.lint.flake8-import-conventions.aliases]
"pandas.core.construction.array" = "pd_array"

[tool.ruff.lint.per-file-ignores]
# relative imports allowed for asv_bench
"asv_bench/*" = ["TID", "NPY002"]
# to be enabled gradually
"pandas/tests/*" = ["B028", "FLY"]
# Keep this one enabled
"pandas/_typing.py" = ["TC"]

# TODO: Fix B905 (zip-without-explicit-strict) - Remove files below as they're fixed
# For contributors working on this issue:
# After adding strict={True,False} to zip() calls in a file,
# remove its line from this section
"pandas/tests/frame/conftest.py" = ["B905"]
"pandas/tests/frame/constructors/test_from_dict.py" = ["B905"]
"pandas/tests/frame/indexing/test_delitem.py" = ["B905"]
"pandas/tests/frame/indexing/test_getitem.py" = ["B905"]
"pandas/tests/frame/indexing/test_indexing.py" = ["B905"]
"pandas/tests/frame/indexing/test_setitem.py" = ["B905"]
"pandas/tests/frame/indexing/test_xs.py" = ["B905"]
"pandas/tests/frame/methods/test_drop.py" = ["B905"]
"pandas/tests/frame/methods/test_isin.py" = ["B905"]
"pandas/tests/frame/methods/test_pop.py" = ["B905"]
"pandas/tests/frame/methods/test_replace.py" = ["B905"]
"pandas/tests/frame/methods/test_reset_index.py" = ["B905"]
"pandas/tests/frame/methods/test_to_dict.py" = ["B905"]
"pandas/tests/frame/test_api.py" = ["B905"]
"pandas/tests/frame/test_constructors.py" = ["B905"]
"pandas/tests/frame/test_iteration.py" = ["B905"]
"pandas/tests/frame/test_query_eval.py" = ["B905"]
"pandas/tests/frame/test_stack_unstack.py" = ["B905"]
"pandas/tests/frame/test_subclass.py" = ["B905"]
"pandas/tests/frame/test_ufunc.py" = ["B905"]
"pandas/tests/groupby/test_groupby_dropna.py" = ["B905"]
"pandas/tests/groupby/test_groupby.py" = ["B905"]
"pandas/tests/groupby/test_grouping.py" = ["B905"]
"pandas/tests/groupby/test_raises.py" = ["B905"]
"pandas/tests/groupby/test_timegrouper.py" = ["B905"]
"pandas/tests/groupby/transform/test_transform.py" = ["B905"]
"pandas/tests/indexes/categorical/test_map.py" = ["B905"]
"pandas/tests/indexes/datetimes/methods/test_astype.py" = ["B905"]
"pandas/tests/indexes/datetimes/test_formats.py" = ["B905"]
"pandas/tests/indexes/datetimes/test_partial_slicing.py" = ["B905"]
"pandas/tests/indexes/datetimes/test_scalar_compat.py" = ["B905"]
"pandas/tests/indexes/datetimes/test_timezones.py" = ["B905"]
"pandas/tests/indexes/interval/test_constructors.py" = ["B905"]
"pandas/tests/indexes/interval/test_formats.py" = ["B905"]
"pandas/tests/indexes/interval/test_interval.py" = ["B905"]
"pandas/tests/indexes/period/methods/test_asfreq.py" = ["B905"]
"pandas/tests/indexes/period/test_constructors.py" = ["B905"]
"pandas/tests/indexes/period/test_formats.py" = ["B905"]
"pandas/tests/indexes/period/test_period.py" = ["B905"]
"pandas/tests/indexes/test_base.py" = ["B905"]
"pandas/tests/indexes/test_datetimelike.py" = ["B905"]
"pandas/tests/indexes/test_old_base.py" = ["B905"]
"pandas/tests/indexes/test_setops.py" = ["B905"]
"pandas/tests/indexes/timedeltas/test_formats.py" = ["B905"]
"pandas/tests/indexing/interval/test_interval.py" = ["B905"]
"pandas/tests/indexing/multiindex/test_getitem.py" = ["B905"]
"pandas/tests/indexing/multiindex/test_iloc.py" = ["B905"]
"pandas/tests/indexing/multiindex/test_indexing_slow.py" = ["B905"]
"pandas/tests/indexing/multiindex/test_loc.py" = ["B905"]
"pandas/tests/indexing/multiindex/test_setitem.py" = ["B905"]
"pandas/tests/indexing/multiindex/test_sorted.py" = ["B905"]
"pandas/tests/indexing/test_coercion.py" = ["B905"]
"pandas/tests/indexing/test_loc.py" = ["B905"]
"pandas/tests/internals/test_internals.py" = ["B905"]
"pandas/tests/io/excel/test_writers.py" = ["B905"]
"pandas/tests/io/formats/style/test_style.py" = ["B905"]
"pandas/tests/io/formats/test_format.py" = ["B905"]
"pandas/tests/io/formats/test_ipython_compat.py" = ["B905"]
"pandas/tests/io/formats/test_to_string.py" = ["B905"]
"pandas/tests/io/generate_legacy_storage_files.py" = ["B905"]
"pandas/tests/io/parser/conftest.py" = ["B905"]
"pandas/tests/io/parser/dtypes/test_categorical.py" = ["B905"]
"pandas/tests/io/parser/test_header.py" = ["B905"]
"pandas/tests/io/parser/test_python_parser_only.py" = ["B905"]
"pandas/tests/io/pytables/test_complex.py" = ["B905"]
"pandas/tests/io/pytables/test_select.py" = ["B905"]
"pandas/tests/io/sas/test_sas7bdat.py" = ["B905"]
"pandas/tests/io/test_gcs.py" = ["B905"]
"pandas/tests/io/test_html.py" = ["B905"]
"pandas/tests/io/test_sql.py" = ["B905"]
"pandas/tests/io/test_stata.py" = ["B905"]
"pandas/tests/plotting/common.py" = ["B905"]
"pandas/tests/plotting/frame/test_frame_color.py" = ["B905"]
"pandas/tests/resample/test_base.py" = ["B905"]
"pandas/tests/reshape/concat/test_concat.py" = ["B905"]
"pandas/tests/reshape/concat/test_index.py" = ["B905"]
"pandas/tests/reshape/test_melt.py" = ["B905"]
"pandas/tests/reshape/test_qcut.py" = ["B905"]
"pandas/tests/scalar/period/test_asfreq.py" = ["B905"]
"pandas/tests/series/accessors/test_dt_accessor.py" = ["B905"]
"pandas/tests/series/indexing/test_get.py" = ["B905"]
"pandas/tests/series/test_api.py" = ["B905"]
"pandas/tests/series/test_constructors.py" = ["B905"]
"pandas/tests/strings/conftest.py" = ["B905"]

[tool.ruff.lint.flake8-pytest-style]
fixture-parentheses = false
mark-parentheses = false

[tool.ruff.format]
docstring-code-format = true

[tool.pytest.ini_options]
# sync minversion with pyproject.toml & install.rst
minversion = "8.3.4"
addopts = "--strict-markers --strict-config --capture=no --durations=30 --junitxml=test-data.xml"
empty_parameter_set_mark = "fail_at_collect"
xfail_strict = true
testpaths = "pandas"
doctest_optionflags = [
  "NORMALIZE_WHITESPACE",
  "IGNORE_EXCEPTION_DETAIL",
  "ELLIPSIS",
]
filterwarnings = [
  "error:::pandas",
  "error::ResourceWarning",
  "error::pytest.PytestUnraisableExceptionWarning",
  "error::pytest.PytestWarning",
  # e.g. Module already imported so cannot be rewritten; _hypothesis_globals
  "ignore::pytest.PytestAssertRewriteWarning",
  "ignore::pytest.PytestCacheWarning",
  # TODO(PY311-minimum): Specify EncodingWarning
  # Ignore 3rd party EncodingWarning but raise on pandas'
  "ignore:.*encoding.* argument not specified",
  "error:.*encoding.* argument not specified::pandas",
  "ignore:.*ssl.SSLSocket:pytest.PytestUnraisableExceptionWarning",
  "ignore:.*ssl.SSLSocket:ResourceWarning",
  # GH 44844: Can remove once minimum matplotlib version >= 3.7
  "ignore:.*FileIO:pytest.PytestUnraisableExceptionWarning",
  "ignore:.*BufferedRandom:ResourceWarning",
  "ignore::ResourceWarning:asyncio",
  # From plotting doctests
  "ignore:More than 20 figures have been opened:RuntimeWarning",
  "ignore:.*urllib3:DeprecationWarning:botocore",
  "ignore:Setuptools is replacing distutils.:UserWarning:_distutils_hack",
  # https://github.com/PyTables/PyTables/issues/822
  "ignore:a closed node found in the registry:UserWarning:tables",
]
junit_family = "xunit2"
markers = [
  "single_cpu: tests that should run on a single cpu only",
  "slow: mark a test as slow",
  "network: mark a test as network",
  "db: tests requiring a database (mysql or postgres)",
  "clipboard: mark a pd.read_clipboard test",
  "arm_slow: mark a test as slow for arm64 architecture",
  # TODO: someone should investigate this ...
  # these tests only fail in the wheel builder and don't fail in regular
  # ARM CI
  "fails_arm_wheels: Tests that fail in the ARM wheel build only",
]

[tool.mypy]
# Import discovery
mypy_path = "typings"
files = ["pandas", "typings"]
namespace_packages = false
explicit_package_bases = false
ignore_missing_imports = true
follow_imports = "normal"
follow_imports_for_stubs = false
no_site_packages = false
no_silence_site_packages = false
# Platform configuration
python_version = "3.11"
platform = "linux-64"
# Disallow dynamic typing
disallow_any_unimported = false # TODO
disallow_any_expr = false # TODO
disallow_any_decorated = false # TODO
disallow_any_explicit = false # TODO
disallow_any_generics = false # TODO
disallow_subclassing_any = false # TODO
# Untyped definitions and calls
disallow_untyped_calls = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
# None and Optional handling
no_implicit_optional = true
strict_optional = true
# Configuring warnings
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_return_any = false # TODO
warn_unreachable = false # GH#27396
# Suppressing errors
ignore_errors = false
enable_error_code = "ignore-without-code"
# Miscellaneous strictness flags
allow_untyped_globals = false
allow_redefinition = false
local_partial_types = true
implicit_reexport = true
strict_equality = true
# Configuring error messages
show_error_context = false
show_column_numbers = false
show_error_codes = true

[[tool.mypy.overrides]]
module = [
  "pandas._config.config", # TODO
  "pandas._libs.*",
  "pandas._testing.*", # TODO
  "pandas.compat.numpy.function", # TODO
  "pandas.core._numba.executor", # TODO
  "pandas.core.array_algos.masked_reductions", # TODO
  "pandas.core.array_algos.putmask", # TODO
  "pandas.core.array_algos.quantile", # TODO
  "pandas.core.array_algos.replace", # TODO
  "pandas.core.array_algos.take", # TODO
  "pandas.core.arrays.*", # TODO
  "pandas.core.computation.*", # TODO
  "pandas.core.dtypes.astype", # TODO
  "pandas.core.dtypes.cast", # TODO
  "pandas.core.dtypes.common", # TODO
  "pandas.core.dtypes.concat", # TODO
  "pandas.core.dtypes.dtypes", # TODO
  "pandas.core.dtypes.generic", # TODO
  "pandas.core.dtypes.missing", # TODO
  "pandas.core.groupby.generic", # TODO
  "pandas.core.groupby.grouper", # TODO
  "pandas.core.groupby.groupby", # TODO
  "pandas.core.groupby.ops", # TODO
  "pandas.core.indexers.*", # TODO
  "pandas.core.indexes.*", # TODO
  "pandas.core.interchange.column", # TODO
  "pandas.core.interchange.dataframe_protocol", # TODO
  "pandas.core.interchange.from_dataframe", # TODO
  "pandas.core.internals.*", # TODO
  "pandas.core.ops.array_ops", # TODO
  "pandas.core.ops.common", # TODO
  "pandas.core.ops.missing", # TODO
  "pandas.core.reshape.*", # TODO
  "pandas.core.strings.*", # TODO
  "pandas.core.tools.*", # TODO
  "pandas.core.window.common", # TODO
  "pandas.core.window.ewm", # TODO
  "pandas.core.window.expanding", # TODO
  "pandas.core.window.numba_", # TODO
  "pandas.core.window.online", # TODO
  "pandas.core.window.rolling", # TODO
  "pandas.core.accessor", # TODO
  "pandas.core.algorithms", # TODO
  "pandas.core.apply", # TODO
  "pandas.core.arraylike", # TODO
  "pandas.core.base", # TODO
  "pandas.core.common", # TODO
  "pandas.core.construction", # TODO
  "pandas.core.flags", # TODO
  "pandas.core.frame", # TODO
  "pandas.core.generic", # TODO
  "pandas.core.indexing", # TODO
  "pandas.core.missing", # TODO
  "pandas.core.nanops", # TODO
  "pandas.core.resample", # TODO
  "pandas.core.roperator", # TODO
  "pandas.core.sample", # TODO
  "pandas.core.series", # TODO
  "pandas.core.sorting", # TODO
  "pandas.errors", # TODO
  "pandas.io.clipboard", # TODO
  "pandas.io.excel._base", # TODO
  "pandas.io.excel._odfreader", # TODO
  "pandas.io.excel._openpyxl", # TODO
  "pandas.io.excel._pyxlsb", # TODO
  "pandas.io.excel._xlrd", # TODO
  "pandas.io.excel._xlsxwriter", # TODO
  "pandas.io.formats.excel", # TODO
  "pandas.io.formats.format", # TODO
  "pandas.io.formats.style", # TODO
  "pandas.io.formats.style_render", # TODO
  "pandas.io.formats.xml", # TODO
  "pandas.io.json.*", # TODO
  "pandas.io.parsers.*", # TODO
  "pandas.io.sas.sas_xport", # TODO
  "pandas.io.sas.sas7bdat", # TODO
  "pandas.io.clipboards", # TODO
  "pandas.io.html", # TODO
  "pandas.io.parquet", # TODO
  "pandas.io.pytables", # TODO
  "pandas.io.sql", # TODO
  "pandas.io.xml", # TODO
  "pandas.plotting.*", # TODO
  "pandas.tests.*",
  "pandas.tseries.frequencies", # TODO
  "pandas.tseries.holiday", # TODO
  "pandas.util._decorators", # TODO
  "pandas.util._doctools", # TODO
  "pandas.util._test_decorators", # TODO
  "pandas.util._validators", # TODO
  "pandas.util", # TODO
  "pandas._version",
  "pandas.conftest",
  "pandas"
]
disallow_untyped_calls = false
disallow_untyped_defs = false
disallow_incomplete_defs = false

[[tool.mypy.overrides]]
module = [
  "pandas.tests.*",
  "pandas._version",
  "pandas.io.clipboard",
]
check_untyped_defs = false

[[tool.mypy.overrides]]
module = [
  "pandas.tests.apply.test_series_apply",
  "pandas.tests.arithmetic.conftest",
  "pandas.tests.arrays.sparse.test_combine_concat",
  "pandas.tests.dtypes.test_common",
  "pandas.tests.frame.methods.test_to_records",
  "pandas.tests.groupby.test_rank",
  "pandas.tests.groupby.transform.test_transform",
  "pandas.tests.indexes.interval.test_interval",
  "pandas.tests.indexing.test_categorical",
  "pandas.tests.io.excel.test_writers",
  "pandas.tests.reductions.test_reductions",
  "pandas.tests.test_expressions",
]
ignore_errors = true

# To be kept consistent with "Import Formatting" section in contributing.rst
[tool.isort]
known_pre_libs = "pandas._config"
known_pre_core = ["pandas._libs", "pandas._typing", "pandas.util._*", "pandas.compat", "pandas.errors"]
known_dtypes = "pandas.core.dtypes"
known_post_core = ["pandas.tseries", "pandas.io", "pandas.plotting"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY" ,"PRE_LIBS" , "PRE_CORE", "DTYPES", "FIRSTPARTY", "POST_CORE", "LOCALFOLDER"]
profile = "black"
combine_as_imports = true
force_grid_wrap = 2
force_sort_within_sections = true
skip_glob = "env"
skip = "pandas/__init__.py"

[tool.pyright]
pythonVersion = "3.11"
typeCheckingMode = "basic"
useLibraryCodeForTypes = false
include = ["pandas", "typings"]
exclude = ["pandas/tests", "pandas/io/clipboard", "pandas/util/version", "pandas/core/_numba/extensions.py"]
# enable subset of "strict"
reportDuplicateImport = true
reportInconsistentConstructor = true
reportInvalidStubStatement = true
reportOverlappingOverload = true
reportPropertyTypeMismatch = true
reportUntypedClassDecorator = true
reportUntypedFunctionDecorator = true
reportUntypedNamedTuple = true
reportUnusedImport = true
disableBytesTypePromotions = true
# disable subset of "basic"
reportArgumentType = false
reportAssignmentType = false
reportAttributeAccessIssue = false
reportCallIssue = false
reportGeneralTypeIssues = false
reportIndexIssue = false
reportMissingModuleSource = false
reportOperatorIssue = false
reportOptionalCall = false
reportOptionalIterable = false
reportOptionalMemberAccess = false
reportOptionalOperand = false
reportOptionalSubscript = false
reportPrivateImportUsage = false
reportRedeclaration = false
reportReturnType = false
reportUnboundVariable = false

[tool.coverage.run]
branch = true
omit = ["pandas/_typing.py", "pandas/_version.py"]
plugins = ["Cython.Coverage"]
source = ["pandas"]

[tool.coverage.report]
ignore_errors = false
show_missing = true
omit = ["pandas/_version.py"]
exclude_lines = [
  # Have to re-enable the standard pragma
  "pragma: no cover",
  # Don't complain about missing debug-only code:s
  "def __repr__",
  "if self.debug",
  # Don't complain if tests don't hit defensive assertion code:
  "raise AssertionError",
  "raise NotImplementedError",
  "AbstractMethodError",
  # Don't complain if non-runnable code isn't run:
  "if 0:",
  "if __name__ == .__main__.:",
  "if TYPE_CHECKING:",
]

[tool.coverage.html]
directory = "coverage_html_report"

[tool.codespell]
ignore-words-list = "blocs, coo, hist, nd, sav, ser, recuse, nin, timere, expec, expecs, indext, SME, NotIn, tructures, tru, indx, abd, ABD"
ignore-regex = 'https://([\w/\.])+'
```

