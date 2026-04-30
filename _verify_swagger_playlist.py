import requests
from allauth.socialaccount.models import SocialToken
from apps.users.models import User

playlist_id = "784cnPHoS5QuX8dhO6ZZ7W"
user = User.objects.get(username="anaramosluna")
token_obj = (
    SocialToken.objects.filter(account__user=user, account__provider="spotify")
    .order_by("-id")
    .first()
)

headers = {"Authorization": f"Bearer {token_obj.token}"}
res = requests.get(f"https://api.spotify.com/v1/playlists/{playlist_id}", headers=headers, timeout=20)

print("STATUS", res.status_code)
if res.ok:
    data = res.json()
    print("ID", data.get("id"))
    print("NAME", data.get("name"))
    print("URI", data.get("uri"))
    print("URL", data.get("external_urls", {}).get("spotify"))
    print("TRACKS_TOTAL", data.get("tracks", {}).get("total"))
else:
    print("BODY", res.text[:500])
