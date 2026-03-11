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
