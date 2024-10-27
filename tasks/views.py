import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .decorators import async_task
from .pubsub import LoggedPubSubTask
from .tasks import Task


@csrf_exempt
def pubsub_receiver(request, *args, **kwargs):
    json_message = json.loads(request.body)
    task = Task.from_pubsub_message(json_message["message"]["data"])
    task.apply_sync(delivery_attempt=json_message.get("deliveryAttempt", 1))

    return JsonResponse({}, status=200)


@csrf_exempt
def dead_letter(request, *args, **kwargs):
    json_message = json.loads(request.body)
    task = Task.from_pubsub_message(json_message["message"]["data"])
    task.on_dead()

    return JsonResponse({}, status=200)


@async_task(queue="test")
def add_task_1(x: int, y: int):
    print(f"Adding {x} and {y}: 1")
    return x + y


@async_task(queue="test", bind=True)
def add_task_2(task: Task, x: int, y: int):
    print(f"Adding {x} and {y}: 2")
    return x + y


@async_task(
    queue="test",
    bind=True,
    base_class=LoggedPubSubTask,
)
def add_task_3(task: Task, x: int, y: int):
    print(f"Adding {x} and {y}: 3")
    return x + y


@async_task(
    queue="test",
    bind=True,
    base_class=LoggedPubSubTask,
    max_delivery_attempts=3,  # This does not work with emulator
)
def add_task_4(task: Task, x: int, y: int):
    print(f"Adding {x} and {y}: 4")
    return x + y


def apply_async(request, *args, **kwargs):
    add_task_1.apply_async(x=2, y=3)
    add_task_2.apply_async(x=2, y=3)
    add_task_3.apply_async(x=2, y=3)
    add_task_4.apply_async(x=2, y=3)
    add_task_4.apply_async(x=2, y=3, ordering_key="test")
    return JsonResponse({}, status=200)
