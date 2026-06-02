# Loaded by Django's app registry, not by any static import. The classic
# false-positive trap for naive dead-code tools.
from django.db import models


class Post(models.Model):
    title = models.CharField(max_length=200)
