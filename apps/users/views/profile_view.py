from cities_light.models import City
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def profile_view(request):
    """
    Muestra el perfil del usuario autenticado.
    """
    return render(request, "users/profile.html", {"user": request.user})


@login_required
def update_profile(request):
    """
    Actualiza los datos del perfil del usuario (ciudad, etc.).
    Acepta POST con los campos del formulario.
    """
    if request.method != "POST":
        return redirect("users:profile")

    user = request.user
    city_id = request.POST.get("city_id", "").strip()

    if city_id:
        try:
            city = City.objects.get(pk=city_id)
            user.city = city
            user.save(update_fields=["city"])
            messages.success(
                request, f"Ciudad actualizada a {city.name} ({city.country.name})."
            )
        except City.DoesNotExist:
            messages.error(request, "La ciudad seleccionada no es válida.")
    else:
        user.city = None
        user.save(update_fields=["city"])
        messages.success(request, "Ciudad eliminada del perfil.")

    return redirect("users:profile")


@login_required
def search_cities(request):
    """
    Endpoint AJAX que devuelve ciudades filtradas por nombre (JSON).
    Usado por el selector de ciudad en el perfil.
    """
    import json

    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return _json_response([])

    cities = (
        City.objects.filter(name__icontains=query)
        .select_related("country")
        .order_by("name")[:20]
    )
    data = [
        {"id": c.pk, "name": c.name, "country": c.country.name if c.country else ""}
        for c in cities
    ]
    return _json_response(data)


def _json_response(data):
    from django.http import JsonResponse
    return JsonResponse(data, safe=False)
