"""
Script de prueba: genera playlist via API y verifica almacenamiento en BD.
"""
import urllib.request
import urllib.parse
import json
import http.cookiejar

base = "http://127.0.0.1:8000"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

print("=" * 60)
print("PRUEBA DE FUNCIONAMIENTO — MOODSIC API")
print("=" * 60)

# 1. Obtener CSRF token del admin login
print("\n[1] Obteniendo CSRF token...")
resp = opener.open(f"{base}/admin/login/")
html = resp.read().decode()
csrf = ""
for line in html.split("\n"):
    if "csrfmiddlewaretoken" in line:
        start = line.find('value="') + 7
        end = line.find('"', start)
        csrf = line[start:end]
        break
print(f"    CSRF token: {'OK' if csrf else 'FALLIDO'}")

# 2. Login como testuser
print("\n[2] Iniciando sesión como testuser...")
data = urllib.parse.urlencode({
    "csrfmiddlewaretoken": csrf,
    "username": "anaramosluna",
    "password": "testpass123",
    "next": "/admin/",
}).encode()
req = urllib.request.Request(f"{base}/admin/login/", data=data, method="POST")
req.add_header("Referer", f"{base}/admin/login/")
req.add_header("Content-Type", "application/x-www-form-urlencoded")
resp2 = opener.open(req)
session_cookie = next((c.value for c in jar if c.name == "sessionid"), None)
print(f"    Session cookie: {'OK (' + session_cookie[:15] + '...)' if session_cookie else 'FALLIDO — usuario necesita is_staff=True'}")

if not session_cookie:
    print("\n  NOTA: El admin de Django requiere is_staff=True.")
    print("  Probando con el endpoint de login de allauth...")

# 3. Obtener CSRF para la API
csrf_cookie = next((c.value for c in jar if c.name == "csrftoken"), None)

# 4. Llamar al endpoint de generación de playlist
print("\n[3] Llamando a POST /api/interactions/playlists/generate/ ...")
payload = json.dumps({
    "name": "Mi Playlist Real con Moodsic",
    "count": 10,
    "use_context": True,
}).encode()
req_playlist = urllib.request.Request(
    f"{base}/api/interactions/playlists/generate/",
    data=payload,
    method="POST",
)
req_playlist.add_header("Content-Type", "application/json")
req_playlist.add_header("X-CSRFToken", csrf_cookie or "")

try:
    resp_playlist = opener.open(req_playlist)
    result = json.loads(resp_playlist.read().decode())
    print(f"    Status: 200 OK")
    print(f"    Respuesta:")
    print(json.dumps(result, indent=4, ensure_ascii=False))
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"    Status: {e.code}")
    try:
        print(f"    Respuesta: {json.dumps(json.loads(body), indent=4, ensure_ascii=False)}")
    except Exception:
        print(f"    Respuesta: {body[:500]}")

# 5. Verificar en la BD directamente via Django shell no disponible aquí
# Se verifica con GET /playlists/
print("\n[4] Verificando playlists guardadas (GET /api/interactions/playlists/) ...")
req_list = urllib.request.Request(f"{base}/api/interactions/playlists/", method="GET")
try:
    resp_list = opener.open(req_list)
    playlists = json.loads(resp_list.read().decode())
    print(f"    Status: 200 OK")
    print(f"    Playlists del usuario:")
    print(json.dumps(playlists, indent=4, ensure_ascii=False))
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"    Status: {e.code}")
    try:
        print(f"    Respuesta: {json.dumps(json.loads(body), indent=4, ensure_ascii=False)}")
    except Exception:
        print(f"    Respuesta: {body[:500]}")

print("\n" + "=" * 60)
