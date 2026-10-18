from typing import Optional

from .pubsub import PubSubTask
from .tasks import TaskWrapper


def async_task(
    queue: str,
    bind: bool = False,
    base_class: type = PubSubTask,
    max_delivery_attempts: Optional[int] = None,
):
    def decorator(func):
        return TaskWrapper.for_pubsub(func, queue, bind, base_class, max_delivery_attempts)

    return decorator
