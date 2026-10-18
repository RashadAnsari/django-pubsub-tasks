from django.conf import settings
from django.core.management.base import BaseCommand

from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1
from google.protobuf import duration_pb2


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        publisher = pubsub_v1.PublisherClient()
        subscriber = pubsub_v1.SubscriberClient()

        project_id = settings.PUBSUB_PROJECT_ID
        base_url = settings.PUBSUB_PUSH_BASE_URL

        topic = "test"
        subscription = "test-sub"
        topic_path = publisher.topic_path(project_id, topic)
        subscription_path = subscriber.subscription_path(project_id, subscription)
        push_config = pubsub_v1.types.PushConfig(push_endpoint=f"{base_url}/pubsub-receiver")

        dead_letter_topic = settings.PUBSUB_DEAD_LETTER_TOPIC
        dead_letter_subscription = "test-dlq-sub"
        dead_letter_topic_path = publisher.topic_path(project_id, dead_letter_topic)
        dead_letter_subscription_path = subscriber.subscription_path(project_id, dead_letter_subscription)
        dead_letter_push_config = pubsub_v1.types.PushConfig(push_endpoint=f"{base_url}/dead-letter")

        try:
            publisher.create_topic(request={"name": topic_path})
            self.stdout.write(self.style.SUCCESS(f"Topic '{topic}' created."))
        except AlreadyExists:
            self.stdout.write(self.style.WARNING(f"Topic '{topic}' already exists."))

        try:
            publisher.create_topic(request={"name": dead_letter_topic_path})
            self.stdout.write(self.style.SUCCESS(f"Topic '{dead_letter_topic}' created."))
        except AlreadyExists:
            self.stdout.write(self.style.WARNING(f"Topic '{dead_letter_topic}' already exists."))

        retry_policy = pubsub_v1.types.RetryPolicy(
            minimum_backoff=duration_pb2.Duration(seconds=1),
            maximum_backoff=duration_pb2.Duration(seconds=5),
        )
        dead_letter_policy = pubsub_v1.types.DeadLetterPolicy(
            dead_letter_topic=dead_letter_topic_path,
            max_delivery_attempts=settings.PUBSUB_MAX_DELIVERY_ATTEMPTS,
        )

        try:
            subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "push_config": push_config,
                    "retry_policy": retry_policy,
                    "ack_deadline_seconds": 60,
                    # "enable_message_ordering": True, # TODO: enable when the issue with message ordering and the dead letter queue for the Pub/Sub emulator is fixed.
                    "dead_letter_policy": dead_letter_policy,
                    "enable_exactly_once_delivery": True,
                }
            )
            self.stdout.write(self.style.SUCCESS(f"Subscription '{subscription}' created."))
        except AlreadyExists:
            self.stdout.write(self.style.WARNING(f"Subscription '{subscription}' already exists."))

        try:
            subscriber.create_subscription(
                request={
                    "name": dead_letter_subscription_path,
                    "topic": dead_letter_topic_path,
                    "push_config": dead_letter_push_config,
                    "ack_deadline_seconds": 60,
                }
            )
            self.stdout.write(self.style.SUCCESS(f"Subscription '{dead_letter_subscription}' created."))
        except AlreadyExists:
            self.stdout.write(self.style.WARNING(f"Subscription '{dead_letter_subscription}' already exists."))
