import sys
from unittest.mock import MagicMock

import pytest

# Mock matplotlib and sklearn before any imports that might use them
mock_plt = MagicMock()
sys.modules["matplotlib"] = mock_plt
sys.modules["matplotlib.pyplot"] = mock_plt

mock_sklearn = MagicMock()
sys.modules["sklearn"] = mock_sklearn
sys.modules["sklearn.metrics"] = mock_sklearn
sys.modules["sklearn.model_selection"] = mock_sklearn
sys.modules["sklearn.preprocessing"] = mock_sklearn


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test to ensure a clean state."""
    import apps.interactions.services.playlist_generation_service as pgs
    import apps.interactions.services.reward_service as rs

    pgs._playlist_generation_service_instance = None
    rs._reward_service_instance = None
    yield
