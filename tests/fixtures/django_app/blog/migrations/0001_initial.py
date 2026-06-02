# Discovered and applied by Django's migration framework — never imported.
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Post",
            fields=[("title", models.CharField(max_length=200))],
        ),
    ]
