# Connected in apps.py ready() via `from blog import signals`. The signal
# receivers are dispatched by Django, not called directly.
from django.db.models.signals import post_save
from django.dispatch import receiver

from blog.models import Post


@receiver(post_save, sender=Post)
def on_post_saved(sender, instance, **kwargs) -> None:
    pass
