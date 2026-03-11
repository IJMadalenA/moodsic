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
