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
        ]

        admin_classes = [
            admin.WeatherContextAdmin,
            admin.CityAdmin,
            admin.RegionAdmin,
            admin.CountryAdmin,
            admin.SubRegionAdmin,
        ]

        # Import Hooks classes.
        hooks_classes = []

        _ = model_classes + admin_classes + hooks_classes
