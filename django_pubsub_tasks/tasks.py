import base64
import importlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict

from dataclass_wizard import fromdict


@dataclass
class TaskParams:
    func: str
    args: tuple
    kwargs: Dict[str, Any]
    id: str
    bind: bool
    base_class: str


class Task:
    @classmethod
    def resolve_callable(self, callable: str) -> Callable:
        module, name = callable.rsplit(".", 1)
        module = importlib.import_module(module)
        attr = getattr(module, name)
        return attr

    @classmethod
    def from_pubsub_message(self, message_data: str) -> "Task":
        from .pubsub import PubSubTaskParams

        str_task_params = base64.b64decode(message_data).decode("utf-8")
        json_task_params = json.loads(str_task_params)
        task_params = fromdict(PubSubTaskParams, json_task_params)
        task_class = self.resolve_callable(task_params.base_class)
        return task_class(task_params)

    def apply_async(self, queue: str) -> str:
        raise NotImplementedError("apply_async method must be implemented")

    def apply_sync(self, *args, **kwargs):
        raise NotImplementedError("apply_sync method must be implemented")

    def is_last_attempt(self):
        raise NotImplementedError("is_last_attempt method must be implemented")

    def on_success(self):
        raise NotImplementedError("on_success method must be implemented")

    def on_failure(self, exc_info):
        raise NotImplementedError("on_failure method must be implemented")

    def on_dead(self):
        raise NotImplementedError("on_dead method must be implemented")


class TaskWrapper:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    @classmethod
    def for_pubsub(self, *args, **kwargs) -> "TaskWrapper":
        from .pubsub import PubSubTaskWrapper

        return PubSubTaskWrapper(*args, **kwargs)

    def type_to_str(self, type):
        return f"{type.__module__}.{type.__name__}"

    def apply_async(self, *args, **kwargs):
        raise NotImplementedError("apply_async method must be implemented")
