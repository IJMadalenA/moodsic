from django.contrib import admin
from unfold.admin import ModelAdmin

from ..models import WeatherContext


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
