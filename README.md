# django-pubsub-tasks

A Celery-like task queue for Django built on Google Cloud Pub/Sub push subscriptions. You decorate a function, call `.apply_async(...)` on it, and Pub/Sub delivers the task back to a Django view that runs it. There are no worker processes: your web server is the worker.

## How it works

1. `@async_task(queue="my-queue")` wraps a function. Calling `.apply_async(*args, **kwargs)` serialises the function path, arguments and options to JSON and publishes it to the Pub/Sub topic named by `queue`.
2. A push subscription on that topic POSTs the message to `pubsub-receiver`.
3. The view decodes the message, imports the function and runs it. If the function raises an error, the view returns a 500 and Pub/Sub retries it according to the subscription's retry policy.
4. After the subscription's maximum delivery attempts, Pub/Sub moves the message to the dead-letter topic, whose push subscription calls `dead-letter`, which runs the task's `on_dead` hook.

## Install

Requires Python 3.11+ and Django 5.1+.

```bash
pip install git+https://github.com/RashadAnsari/django-pubsub-tasks.git
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "simple_history",
    "django_pubsub_tasks",
]

PUBSUB_PROJECT_ID = "my-gcp-project"
PUBSUB_DEAD_LETTER_TOPIC = "my-dead-letter-topic"
```

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    # ...
    path("tasks/", include("django_pubsub_tasks.urls")),
]
```

```bash
python manage.py migrate
```

This adds two endpoints, `tasks/pubsub-receiver` and `tasks/dead-letter`, and the `PubSubTaskLog` model used by `LoggedPubSubTask`.

## Settings

| Setting | Required | Meaning |
|---|---|---|
| `PUBSUB_PROJECT_ID` | yes | Google Cloud project the topics live in |
| `PUBSUB_DEAD_LETTER_TOPIC` | yes | Topic that tasks are sent to when `max_delivery_attempts` is reached |
| `PUBSUB_MAX_DELIVERY_ATTEMPTS` | no, default `5` | Must match `max_delivery_attempts` in your subscriptions' dead-letter policy |
| `PUBSUB_PUSH_AUDIENCE` | outside the emulator | Audience of the push subscription's OIDC token |
| `PUBSUB_PUSH_SERVICE_ACCOUNT` | outside the emulator | Service account the push subscription signs its token with |

When the `PUBSUB_EMULATOR_HOST` environment variable is set, the client uses the emulator and the token check is skipped, since the emulator doesn't sign push requests.

## Pub/Sub setup

For each queue, create a topic and a push subscription to `https://<your-host>/tasks/pubsub-receiver`, with a dead-letter policy pointing at `PUBSUB_DEAD_LETTER_TOPIC`. Create a push subscription on the dead-letter topic to `https://<your-host>/tasks/dead-letter`.

Turn on [authentication for both push subscriptions](https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions) and set `PUBSUB_PUSH_AUDIENCE` and `PUBSUB_PUSH_SERVICE_ACCOUNT` to match. Both views reject requests with a 403 unless they carry a valid Google-signed token with that audience, issued to that service account.

## Defining tasks

```python
from django_pubsub_tasks.decorators import async_task
from django_pubsub_tasks.pubsub import LoggedPubSubTask
from django_pubsub_tasks.tasks import Task


@async_task(queue="emails")
def send_email(user_id: int):
    ...


# bind=True passes the task object in as `task`
@async_task(queue="emails", bind=True)
def send_digest(task: Task, user_id: int):
    ...


# LoggedPubSubTask records every task in the PubSubTaskLog model
@async_task(queue="billing", bind=True, base_class=LoggedPubSubTask, max_delivery_attempts=3)
def charge(task: Task, invoice_id: int):
    ...


send_email.apply_async(user_id=42)
charge.apply_async(invoice_id=7, ordering_key="customer-42")
```

| Option | Meaning |
|---|---|
| `queue` | Pub/Sub topic to publish to |
| `bind` | Pass the task object to the function as the `task` keyword argument |
| `base_class` | `PubSubTask` (default) or `LoggedPubSubTask`, or your own subclass |
| `max_delivery_attempts` | Send the task to the dead-letter topic after this many attempts instead of waiting for the subscription limit. Must be below `PUBSUB_MAX_DELIVERY_ATTEMPTS`. It doesn't work with the emulator. |
| `ordering_key` (on `apply_async`) | Pub/Sub ordering key |

Task arguments must be JSON-serialisable. `LoggedPubSubTask` stores each task's parameters, status (`STARTED`, `SUCCEEDED`, `DEAD`), delivery attempts and timestamps in `PubSubTaskLog`, with full history via django-simple-history.

## Example project

[example/](example/) is a Django project that uses the app against the local Pub/Sub emulator. Its [demo.py](example/demo.py) defines four demo tasks.

Requires Python 3.11, Poetry and Docker. A [shell.nix](shell.nix) is included if you use Nix.

```bash
poetry install
make up                    # start the Pub/Sub emulator on localhost:8532
python manage.py migrate
make create_local_pubsub   # create the demo topics and push subscriptions
make runserver
```

Then open http://localhost:8000/tasks/apply-async to publish the demo tasks and watch them run in the server log.

The emulator runs in Docker and pushes to `http://host.docker.internal:8000/tasks/...`, which works out of the box on Docker Desktop. On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the service in [docker-compose.yml](docker-compose.yml).

The example's [settings.py](example/settings.py) reads these environment variables:

| Variable | Default |
|---|---|
| `DJANGO_DEBUG` | `true`; also points the client at the emulator on `localhost:8532` |
| `DJANGO_SECRET_KEY` | `secret` in debug, required otherwise |
| `DJANGO_ALLOWED_HOSTS` | `*` |
| `PUBSUB_PROJECT_ID` | `test-project` |
| `PUBSUB_DEAD_LETTER_TOPIC` | `test-dlq` |
| `PUBSUB_MAX_DELIVERY_ATTEMPTS` | `5` |
| `PUBSUB_PUSH_BASE_URL` | `http://host.docker.internal:8000/tasks`, used by `create_local_pubsub` |
| `PUBSUB_PUSH_AUDIENCE`, `PUBSUB_PUSH_SERVICE_ACCOUNT` | unset |

## Development

```bash
make local                                 # lock, ruff format, ruff check
python manage.py test django_pubsub_tasks
```
