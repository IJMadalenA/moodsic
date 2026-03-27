from django.shortcuts import redirect


def spotify_callback_redirect(request):
    """Redirige el callback de Spotify al endpoint de Allauth."""
    query_string = request.META.get("QUERY_STRING", "")
    target_url = "/accounts/spotify/login/callback/"
    if query_string:
        target_url = f"{target_url}?{query_string}"
    return redirect(target_url)
