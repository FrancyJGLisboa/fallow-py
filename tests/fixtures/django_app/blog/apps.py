from django.apps import AppConfig


class BlogConfig(AppConfig):
    name = "blog"

    def ready(self) -> None:
        # Connects signal handlers as a side effect — no static import of them.
        from blog import signals  # noqa: F401
