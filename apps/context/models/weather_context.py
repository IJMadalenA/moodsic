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
