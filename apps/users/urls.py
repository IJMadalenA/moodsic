from django.urls import path

from .views import profile_view

app_name = "users"

urlpatterns = [
    path("profile/", profile_view, name="profile"),
]

# allauth URLs should be outside the namespace to match expected names like 'account_logout'
# Or we can keep them here and use 'users:account_logout' if we want, but allauth usually expects global namespace.
