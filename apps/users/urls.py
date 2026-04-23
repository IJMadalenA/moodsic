from django.urls import path

from .views.profile_view import profile_view

app_name = "users"

urlpatterns = [
    path("profile/", profile_view, name="profile"),
]
