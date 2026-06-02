# Referenced only as the string "myproject.urls" (ROOT_URLCONF). Django's URL
# resolver imports it and the view via string path.
from django.urls import path

from blog import views

urlpatterns = [
    path("", views.index),
]
