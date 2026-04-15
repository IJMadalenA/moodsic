from django.urls import path

from apps.dashboard.views import dashboard_home

app_name = "dashboard"

urlpatterns = [
    path("", dashboard_home, name="home"),
    path("dashboard/", dashboard_home, name="dashboard-home"),
]
