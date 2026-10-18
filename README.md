# django-pubsub-tasks

A Celery-like task queue for Django built on Google Cloud Pub/Sub push subscriptions. You decorate a function, call `.apply_async(...)` on it, and Pub/Sub delivers the task back to a Django view that runs it. There are no worker processes: your web server is the worker.

## How it works

1. `@async_task(queue="test")` wraps a function. Calling `.apply_async(*args, **kwargs)` serialises the function path, arguments and options to JSON and publishes it to the Pub/Sub topic named by `queue`.
2. A push subscription on that topic POSTs the message to `/tasks/pubsub-receiver`.
3. The view decodes the message, imports the function and runs it. If the function raises an error, the view returns a 500, and Pub/Sub retries with a 1 to 5 second backoff.
4. After the subscription's maximum delivery attempts (5), Pub/Sub moves the message to the dead-letter topic, whose push subscription calls `/tasks/dead-letter`, which runs the task's `on_dead` hook.

## Defining tasks

```python
from tasks.decorators import async_task
from tasks.pubsub import LoggedPubSubTask
from tasks.tasks import Task


@async_task(queue="test")
def add(x: int, y: int):
    return x + y


# bind=True passes the task object in as `task`
@async_task(queue="test", bind=True)
def add_bound(task: Task, x: int, y: int):
    return x + y


# LoggedPubSubTask records every task in the PubSubTaskLog model
@async_task(queue="test", bind=True, base_class=LoggedPubSubTask, max_delivery_attempts=3)
def add_logged(task: Task, x: int, y: int):
    return x + y


add.apply_async(x=2, y=3)
add_logged.apply_async(x=2, y=3, ordering_key="customer-42")
```

| Option | Meaning |
|---|---|
| `queue` | Pub/Sub topic to publish to |
| `bind` | Pass the task object to the function as the `task` keyword argument |
| `base_class` | `PubSubTask` (default) or `LoggedPubSubTask`, or your own subclass |
| `max_delivery_attempts` | Send the task to the dead-letter topic after this many attempts instead of waiting for the subscription limit. Must be below 5. It does not work with the emulator. |
| `ordering_key` (on `apply_async`) | Pub/Sub ordering key |

`LoggedPubSubTask` stores each task's parameters, status (`STARTED`, `SUCCEEDED`, `DEAD`), delivery attempts and timestamps in `PubSubTaskLog`, with full history via django-simple-history.

## Run locally

Requires Python 3.11, Poetry and Docker. A [shell.nix](shell.nix) is included if you use Nix.

```bash
poetry install
make up                    # start the Pub/Sub emulator on localhost:8532
python manage.py migrate
make create_local_pubsub   # create topics and push subscriptions
make runserver
```

Then open http://localhost:8000/tasks/apply-async (only routed when `DEBUG` is on) to publish the demo tasks in [tasks/views.py](tasks/views.py) and watch them run in the server log.

The emulator runs in Docker and pushes to `http://host.docker.internal:8000/tasks/...`, which works out of the box on Docker Desktop. On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the service in [docker-compose.yml](docker-compose.yml).

## Configuration

Everything is read from environment variables in [settings.py](django_pubsub_tasks/settings.py):

| Variable | Default | Meaning |
|---|---|---|
| `DJANGO_DEBUG` | `true` | When true, the app uses the emulator at `localhost:8532` unless `PUBSUB_EMULATOR_HOST` says otherwise |
| `DJANGO_SECRET_KEY` | `secret` in debug, required otherwise | Django secret key |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated hosts |
| `PUBSUB_PROJECT_ID` | `test-project` | Google Cloud project |
| `PUBSUB_DEAD_LETTER_TOPIC` | `test-dlq` | Dead-letter topic |
| `PUBSUB_MAX_DELIVERY_ATTEMPTS` | `5` | Must match the subscription's dead-letter policy |
| `PUBSUB_PUSH_BASE_URL` | `http://host.docker.internal:8000/tasks` | Push endpoint base used by `create_local_pubsub` |
| `PUBSUB_PUSH_AUDIENCE` | | Expected audience of the push token |
| `PUBSUB_PUSH_SERVICE_ACCOUNT` | | Service account the push subscription signs with |

## Running against real Pub/Sub

Set `DJANGO_DEBUG=false`, a real `DJANGO_SECRET_KEY`, and the project and topic variables above. Create push subscriptions to `/tasks/pubsub-receiver` and `/tasks/dead-letter` with [authentication enabled](https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions), and set `PUBSUB_PUSH_AUDIENCE` and `PUBSUB_PUSH_SERVICE_ACCOUNT` to the audience and service account of those subscriptions.

Outside the emulator, both receiver views check the request's Google-signed OIDC token: it must be valid, carry that audience, and be issued to that service account. Anything else gets a 403.

## Development

```bash
make local                  # lock, ruff format, ruff check
python manage.py test tasks
```
