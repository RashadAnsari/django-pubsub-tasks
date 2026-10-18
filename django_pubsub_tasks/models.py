from django.db import models

from simple_history.models import HistoricalRecords


class TaskLog(models.Model):
    class TaskStatus(models.TextChoices):
        STARTED = "STARTED"
        SUCCEEDED = "SUCCEEDED"
        DEAD = "DEAD"

    id = models.CharField(max_length=64, primary_key=True)
    params = models.JSONField()
    queue = models.CharField(max_length=60, db_index=True)

    started_at = models.DateTimeField()
    delivery_attempts = models.IntegerField(default=0)
    last_delivery_attempt = models.DateTimeField(null=True)
    succeeded_at = models.DateTimeField(null=True)
    dead_at = models.DateTimeField(null=True)

    status = models.CharField(choices=TaskStatus.choices, max_length=20, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class PubSubTaskLog(TaskLog):
    history = HistoricalRecords()
    message_id = models.CharField(max_length=100, db_index=True)
