import importlib
import json
import uuid
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.utils import timezone

from dataclass_wizard import asdict
from google.cloud import pubsub_v1

from .models import PubSubTaskLog
from .tasks import Task, TaskParams, TaskWrapper

PROJECT_ID = settings.PUBSUB_PROJECT_ID
DEAD_LETTER_TOPIC = settings.PUBSUB_DEAD_LETTER_TOPIC
MAX_CONFIGURED_DELIVERY_ATTEMPTS = settings.PUBSUB_MAX_DELIVERY_ATTEMPTS
publisher = pubsub_v1.PublisherClient(
    publisher_options=pubsub_v1.types.PublisherOptions(
        enable_message_ordering=True,
    ),
)


@dataclass
class PubSubTaskParams(TaskParams):
    ordering_key: str
    max_delivery_attempts: Optional[int]


class PubSubTask(Task):
    def __init__(self, params: PubSubTaskParams):
        self.params = params

    def apply_async(self, queue: str) -> str:
        task_params_str = json.dumps(asdict(self.params))
        message_bytes = task_params_str.encode("utf-8")
        topic_path = publisher.topic_path(PROJECT_ID, queue)
        future = publisher.publish(topic_path, message_bytes, ordering_key=self.params.ordering_key)
        print(f"Task {self.params.func} with ID {self.params.id} published to queue {queue}")
        return future.result()

    def apply_sync(self, delivery_attempt: int = 1):
        try:
            print(f"Applying task {self.params.func} with ID {self.params.id}")
            self.delivery_attempt = delivery_attempt
            task_func = self.resolve_callable(self.params.func)
            kwargs = self.params.kwargs.copy()
            if self.params.bind:
                kwargs["task"] = self
            task_func(*self.params.args, **kwargs)
            self.on_success()
        except Exception as exc_info:
            print(f"Error executing task {self.params.func} with ID {self.params.id}: {exc_info}")
            self.on_failure(exc_info=exc_info)

    def is_last_attempt(self):
        if not self.params.max_delivery_attempts:
            return False

        return self.delivery_attempt >= self.params.max_delivery_attempts

    def on_success(self):
        print(f"Task {self.params.func} with ID {self.params.id} executed successfully")

    def on_failure(self, exc_info):
        if not self.is_last_attempt() or self.delivery_attempt >= MAX_CONFIGURED_DELIVERY_ATTEMPTS:
            raise exc_info

        self.apply_async(queue=DEAD_LETTER_TOPIC)

    def on_dead(self):
        delivery_attempts = self.params.max_delivery_attempts or MAX_CONFIGURED_DELIVERY_ATTEMPTS
        print(f"Task {self.params.func} with ID {self.params.id} failed after {delivery_attempts} attempts")


class LoggedPubSubTask(PubSubTask):
    def apply_async(self, queue) -> str:
        message_id = super().apply_async(queue)

        task_log, created = PubSubTaskLog.objects.get_or_create(
            id=self.params.id,
            defaults={
                "params": asdict(self.params),
                "queue": queue,
                "started_at": timezone.now(),
                "status": PubSubTaskLog.TaskStatus.STARTED,
                "message_id": message_id,
            },
        )
        if not created:
            task_log.queue = queue
            task_log.started_at = timezone.now()
            task_log.status = PubSubTaskLog.TaskStatus.STARTED
            task_log.message_id = message_id
            task_log.save()

        return message_id

    def apply_sync(self, delivery_attempt=1):
        task_log = PubSubTaskLog.objects.filter(id=self.params.id).first()
        if task_log:
            task_log.delivery_attempts += 1
            task_log.last_delivery_attempt = timezone.now()
            task_log.save()

        return super().apply_sync(delivery_attempt)

    def on_success(self):
        task_log = PubSubTaskLog.objects.filter(id=self.params.id).first()
        if task_log:
            task_log.succeeded_at = timezone.now()
            task_log.status = PubSubTaskLog.TaskStatus.SUCCEEDED
            task_log.save()

        return super().on_success()

    def on_dead(self):
        task_log = PubSubTaskLog.objects.filter(id=self.params.id).first()
        if task_log:
            task_log.dead_at = timezone.now()
            task_log.status = PubSubTaskLog.TaskStatus.DEAD
            task_log.save()

        return super().on_dead()


class PubSubTaskWrapper(TaskWrapper):
    def __init__(
        self,
        func,
        queue: str,
        bind: bool = False,
        base_class: type = PubSubTask,
        max_delivery_attempts: Optional[int] = None,
    ):
        assert issubclass(base_class, PubSubTask), "base must be a subclass of PubSubTask"
        assert (
            not max_delivery_attempts or max_delivery_attempts < MAX_CONFIGURED_DELIVERY_ATTEMPTS
        ), f"max_delivery_attempts must be less than {MAX_CONFIGURED_DELIVERY_ATTEMPTS}"

        super().__init__(func)
        self.queue = queue
        self.bind = bind
        self.base_class = base_class
        self.max_delivery_attempts = max_delivery_attempts

    def apply_async(self, *args, ordering_key: str = "", **kwargs):
        task_params = PubSubTaskParams(
            func=self.type_to_str(self.func),
            args=args,
            kwargs=kwargs,
            id=str(uuid.uuid4()),
            bind=self.bind,
            base_class=self.type_to_str(self.base_class),
            ordering_key=ordering_key,
            max_delivery_attempts=self.max_delivery_attempts,
        )
        task = self.base_class(task_params)
        task.apply_async(self.queue)
