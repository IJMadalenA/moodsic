import pytest
from django.test import Client


@pytest.mark.django_db
class TestInteractionsURLs:
    def test_swagger_ui_rendering(self):
        client = Client()
        # El endpoint de docs está en /api/interactions/docs/
        response = client.get("/api/interactions/docs/")
        assert response.status_code == 200
        # Verificar que el polifill o sustituciones ocurrieron
        content = response.content.decode()
        assert "window.crypto.randomUUID" in content
        assert "SwaggerUIStandalonePreset" in content
