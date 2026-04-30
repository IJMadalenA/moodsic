from django.urls import path

from .views.profile_view import profile_view, update_profile, search_cities

app_name = "users"

urlpatterns = [
    path("profile/", profile_view, name="profile"),
    path("profile/update/", update_profile, name="update_profile"),
    path("profile/cities/", search_cities, name="search_cities"),
]
