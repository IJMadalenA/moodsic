from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def profile_view(request):
    """
    Muestra el perfil del usuario autenticado.
    """
    return render(request, "users/profile.html", {"user": request.user})
