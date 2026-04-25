from django.core.management.base import BaseCommand

from pipelines.etl_news import run_news_etl


class Command(BaseCommand):
    help = "Fetches latest news context from NewsAPI and stores it in DB."

    def add_arguments(self, parser):
        parser.add_argument("--query", type=str, default="music OR entertainment")
        parser.add_argument("--language", type=str, default="en")
        parser.add_argument("--page-size", type=int, default=20)
        parser.add_argument(
            "--category",
            type=str,
            default="general",
            choices=["general", "music", "markets", "sports", "politics"],
        )

    def handle(self, *args, **options):
        count = run_news_etl(
            query=options["query"],
            language=options["language"],
            page_size=options["page_size"],
            category=options["category"],
        )
        self.stdout.write(self.style.SUCCESS(f"Stored {count} news context records."))
