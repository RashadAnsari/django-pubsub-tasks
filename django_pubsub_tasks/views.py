import json
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from .tasks import Task


def verify_push_request(request):
    # The emulator does not sign push requests.
    if os.environ.get("PUBSUB_EMULATOR_HOST"):
        return

    audience = getattr(settings, "PUBSUB_PUSH_AUDIENCE", None)
    service_account = getattr(settings, "PUBSUB_PUSH_SERVICE_ACCOUNT", None)
    if not audience or not service_account:
        raise ImproperlyConfigured("Set PUBSUB_PUSH_AUDIENCE and PUBSUB_PUSH_SERVICE_ACCOUNT to verify push requests.")

    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme != "Bearer" or not token:
        raise PermissionDenied("Missing bearer token.")

    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(), audience=audience)
    except ValueError:
        raise PermissionDenied("Invalid token.")

    if claims.get("email") != service_account or not claims.get("email_verified"):
        raise PermissionDenied("Token was not issued for the push service account.")


@csrf_exempt
def pubsub_receiver(request, *args, **kwargs):
    verify_push_request(request)
    json_message = json.loads(request.body)
    task = Task.from_pubsub_message(json_message["message"]["data"])
    task.apply_sync(delivery_attempt=json_message.get("deliveryAttempt", 1))

    return JsonResponse({}, status=200)


@csrf_exempt
def dead_letter(request, *args, **kwargs):
    verify_push_request(request)
    json_message = json.loads(request.body)
    task = Task.from_pubsub_message(json_message["message"]["data"])
    task.on_dead()

    return JsonResponse({}, status=200)
