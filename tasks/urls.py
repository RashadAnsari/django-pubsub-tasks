from django.urls import path

from .views import apply_async, dead_letter, pubsub_receiver

urlpatterns = [
    path("pubsub-receiver", pubsub_receiver, name="pubsub-receiver"),
    path("dead-letter", dead_letter, name="dead-letter"),
    path("apply-async", apply_async, name="apply-async"),
]
