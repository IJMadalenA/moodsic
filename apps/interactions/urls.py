"""
URLs para el app interactions.
"""

from django.templatetags.static import static
from django.urls import path
from ninja import NinjaAPI, Swagger

from apps.interactions.views.api import router as interactions_router
from apps.interactions.views.playlist_api import router as playlist_router


class FixedSwagger(Swagger):
    def render_page(self, request, api, **kwargs):
        response = super().render_page(request, api, **kwargs)
        content = response.content.decode()

        # Sustituir URLs de CDN por locales
        content = content.replace(
            "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            static("vendor/swagger-ui/swagger-ui.css"),
        )
        content = content.replace(
            "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            static("vendor/swagger-ui/swagger-ui-bundle.js"),
        )

        # Asegurar que el preset también se carga localmente
        bundle_script_local = f'<script src="{static("vendor/swagger-ui/swagger-ui-bundle.js")}"></script>'
        preset_script_local = f'<script src="{static("vendor/swagger-ui/swagger-ui-standalone-preset.js")}"></script>'

        if bundle_script_local in content and preset_script_local not in content:
            content = content.replace(
                bundle_script_local, f"{bundle_script_local}\n    {preset_script_local}"
            )

        # Corregir error en el nombre del preset de Ninja
        content = content.replace(
            "SwaggerUIBundle.SwaggerUIStandalonePreset", "SwaggerUIStandalonePreset"
        )

        # Polyfill para crypto.randomUUID (necesario en contextos no seguros como 0.0.0.0)
        polyfill = """
    <script>
        if (!window.crypto) { window.crypto = {}; }
        if (!window.crypto.randomUUID) {
            window.crypto.randomUUID = function() {
                return ([1e7]+-1e3+-4e3+-8e3+-11e11).replace(/[018]/g, c =>
                    (c ^ (window.crypto.getRandomValues ? window.crypto.getRandomValues(new Uint8Array(1))[0] : (Math.random() * 16)) & 15 >> c / 4).toString(16)
                );
            };
        }
    </script>
"""
        if "</head>" in content:
            content = content.replace("</head>", f"{polyfill}\n</head>")

        # Sustituir favicon por uno local o neutral si es posible
        content = content.replace(
            "https://django-ninja.dev/img/favicon.svg",
            "https://static.djangoproject.com/img/icon-touch.png",  # Usar algo más común o simplemente dejarlo
        )

        response.content = content.encode()
        return response


# Crear API principal
api = NinjaAPI(
    title="Moodsic API - Interactions",
    version="1.0.0",
    urls_namespace="interactions",
    docs_url="/docs/",
    docs=FixedSwagger(settings={"layout": "StandaloneLayout"}),
)

# Registrar routers
api.add_router("", interactions_router, tags=["interactions"])
api.add_router("", playlist_router, tags=["playlists"])

urlpatterns = [
    path("", api.urls),
]
