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
