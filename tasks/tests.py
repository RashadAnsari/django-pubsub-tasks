import os
from unittest import mock

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase, override_settings

from .views import verify_push_request

SERVICE_ACCOUNT = "push@test-project.iam.gserviceaccount.com"


@override_settings(PUBSUB_PUSH_AUDIENCE="https://example.com/tasks", PUBSUB_PUSH_SERVICE_ACCOUNT=SERVICE_ACCOUNT)
@mock.patch.dict(os.environ, {"PUBSUB_EMULATOR_HOST": ""})
class VerifyPushRequestTests(SimpleTestCase):
    def request(self, authorization=None):
        headers = {"HTTP_AUTHORIZATION": authorization} if authorization else {}
        return RequestFactory().post("/tasks/pubsub-receiver", **headers)

    def test_rejects_missing_token(self):
        with self.assertRaises(PermissionDenied):
            verify_push_request(self.request())

    @mock.patch("tasks.views.id_token.verify_oauth2_token", side_effect=ValueError)
    def test_rejects_invalid_token(self, _):
        with self.assertRaises(PermissionDenied):
            verify_push_request(self.request("Bearer bad"))

    @mock.patch("tasks.views.id_token.verify_oauth2_token")
    def test_rejects_other_service_account(self, verify):
        verify.return_value = {"email": "someone@example.com", "email_verified": True}
        with self.assertRaises(PermissionDenied):
            verify_push_request(self.request("Bearer token"))

    @mock.patch("tasks.views.id_token.verify_oauth2_token")
    def test_accepts_push_service_account(self, verify):
        verify.return_value = {"email": SERVICE_ACCOUNT, "email_verified": True}
        verify_push_request(self.request("Bearer token"))
        self.assertEqual(verify.call_args.kwargs["audience"], "https://example.com/tasks")

    def test_skips_check_for_emulator(self):
        with mock.patch.dict(os.environ, {"PUBSUB_EMULATOR_HOST": "localhost:8532"}):
            verify_push_request(self.request())
