from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NewsContext(models.Model):
    """Stores external news items used as context for playlist generation."""

    title = models.CharField(max_length=300, verbose_name=_("Title"))
    source = models.CharField(
        max_length=120, blank=True, default="", verbose_name=_("Source")
    )
    url = models.URLField(max_length=600, unique=True, verbose_name=_("URL"))
    summary = models.TextField(blank=True, default="", verbose_name=_("Summary"))
    language = models.CharField(max_length=10, default="en", verbose_name=_("Language"))
    category = models.CharField(
        max_length=80, blank=True, default="general", verbose_name=_("Category")
    )
    sentiment_score = models.FloatField(default=0.0, verbose_name=_("Sentiment score"))
    sentiment_label = models.CharField(
        max_length=20, default="neutral", verbose_name=_("Sentiment label")
    )
    is_breaking = models.BooleanField(default=False, verbose_name=_("Breaking"))
    published_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("Published at")
    )
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
