from cities_light.models import City, Country
from django.core.management.base import BaseCommand

from apps.context.models import NewsContext, WeatherContext
from apps.music.models import Album, Artist, Track
from apps.users.models import User


class Command(BaseCommand):
    help = "Verifica la integridad y el estado de los datos en la base de datos"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("\n=== Moodsic Data Integrity Check ===\n")
        )

        # 1. Geographic Data
        countries = Country.objects.count()
        cities = City.objects.count()
        self.stdout.write("Geographic Data:")
        self.stdout.write(f"  - Countries: {countries}")
        self.stdout.write(f"  - Cities: {cities}")
        if countries == 0 or cities == 0:
            self.stdout.write(
                self.style.ERROR(
                    "  [!] CRITICAL: Geographic data is empty. Run 'python manage.py cities_light'."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("  [OK] Geographic data present."))

        # 2. Context Data
        weather = WeatherContext.objects.count()
        news = NewsContext.objects.count()
        self.stdout.write("\nContext Data:")
        self.stdout.write(f"  - Weather Records: {weather}")
        self.stdout.write(f"  - News Articles: {news}")
        if weather == 0:
            self.stdout.write(
                self.style.WARNING(
                    "  [!] Weather data is empty. Run 'python manage.py refresh_context'."
                )
            )
        if news == 0:
            self.stdout.write(
                self.style.WARNING(
                    "  [!] News data is empty. Run 'python manage.py refresh_context'."
                )
            )
        if weather > 0 and news > 0:
            self.stdout.write(self.style.SUCCESS("  [OK] Context data present."))

        # 3. Music Data
        tracks = Track.objects.count()
        artists = Artist.objects.count()
        albums = Album.objects.count()
        self.stdout.write("\nMusic Data:")
        self.stdout.write(f"  - Tracks: {tracks}")
        self.stdout.write(f"  - Artists: {artists}")
        self.stdout.write(f"  - Albums: {albums}")
        if tracks == 0:
            self.stdout.write(
                self.style.WARNING(
                    "  [!] Music data is empty. Users need to sync their Spotify account."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("  [OK] Music data present."))

        # 4. User Data
        total_users = User.objects.count()
        connected_users = User.objects.filter(is_spotify_connected=True).count()
        users_with_city = User.objects.filter(city__isnull=False).count()
        self.stdout.write("\nUser Data:")
        self.stdout.write(f"  - Total Users: {total_users}")
        self.stdout.write(f"  - Connected to Spotify: {connected_users}")
        self.stdout.write(f"  - Users with assigned City: {users_with_city}")

        self.stdout.write(self.style.SUCCESS("\n=== Check Completed ===\n"))
