import pytest

from apps.interactions.models import Interaction
from apps.music.models import Album, Track


@pytest.mark.django_db
def test_interaction_properties(db):
    from apps.users.models.user import User

    user = User.objects.create_user(username="prop_user", email="p@test.com")
    al = Album.objects.create(name="A", spotify_id="a1")
    tr = Track.objects.create(
        name="T", spotify_id="t1", album=al, track_number=1, duration_ms=100000
    )

    # Test positive feedback
    i1 = Interaction.objects.create(
        user=user,
        track=tr,
        feedback="completed",
        play_duration=100,
        track_duration=100,
        reward=1.0,
    )
    assert i1.is_positive is True
    assert i1.completion_percentage == 100.0

    # Test skip feedback
    i2 = Interaction.objects.create(
        user=user,
        track=tr,
        feedback="skip",
        play_duration=10,
        track_duration=100,
        reward=-0.5,
    )
    assert i2.is_positive is False
    assert i2.completion_percentage == 10.0

    # Test immediate skip
    i3 = Interaction.objects.create(
        user=user,
        track=tr,
        feedback="skip_immediate",
        play_duration=2,
        track_duration=100,
        reward=-1.0,
    )
    assert i3.is_positive is False

    # Test replay
    i4 = Interaction.objects.create(
        user=user,
        track=tr,
        feedback="replay",
        play_duration=100,
        track_duration=100,
        reward=1.5,
    )
    assert i4.is_positive is True
