from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from .demo import apply_async

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tasks/", include("django_pubsub_tasks.urls")),
]

# Publishes the demo tasks; local development only.
if settings.DEBUG:
    urlpatterns.append(path("tasks/apply-async", apply_async, name="apply-async"))
