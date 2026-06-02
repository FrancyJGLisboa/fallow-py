# Referenced only as the string "myproject.settings" (DJANGO_SETTINGS_MODULE) —
# never statically imported. Django loads it by name.
INSTALLED_APPS = [
    "django.contrib.admin",
    "blog",
]
ROOT_URLCONF = "myproject.urls"
