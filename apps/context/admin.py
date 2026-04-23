from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import NewsContext, WeatherContext


@admin.register(WeatherContext)
class WeatherContextAdmin(ModelAdmin):
    list_display = ("city", "main_status", "temperature", "timestamp")
    list_filter = ("main_status", "country", "timestamp")
    search_fields = ("city__name", "description")

@admin.register(NewsContext)
class NewsContextAdmin(ModelAdmin):
    list_display = ("title", "source", "sentiment_label", "published_at")
    list_filter = ("sentiment_label", "category", "source")
    search_fields = ("title", "summary")
