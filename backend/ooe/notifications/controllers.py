import json

import redis
from django.utils import timezone

from ooe.base.exceptions import OOEException
from ooe.notifications.models import Notification

redis_client = redis.Redis(host='redis', port=6379, db=0)


def push(user, notif_type, message, payload=None):
    """
    Create a persisted notification for `user` and publish it for live
    delivery. This is the one entry point the rest of the codebase should
    call — same redis_client.publish(...) pattern already used by
    chat/assassination/black_market, with a DB row kept alongside so a
    player who's offline when it fires still sees it in their bell dropdown
    on next login.
    """
    notification = Notification.objects.create(
        user=user,
        notif_type=notif_type,
        message=message,
        payload=payload,
    )

    redis_client.publish(f'notification:{user.id}', json.dumps({
        'id': notification.id,
        'notif_type': notif_type,
        'message': message,
        'payload': payload,
        'created_at': notification.created_at.timestamp(),
    }))

    return notification


class NotificationsController:
    def __init__(self, user):
        self.user = user

    def get_notifications_data(self, limit=30):
        notifications = Notification.objects.filter(user=self.user)[:limit]

        return {
            'notifications': [{
                'id': n.id,
                'notif_type': n.notif_type,
                'message': n.message,
                'payload': n.payload,
                'created_at': n.created_at.timestamp(),
                'read': n.read_at is not None,
            } for n in notifications],
            'unread_count': Notification.objects.filter(user=self.user, read_at__isnull=True).count(),
        }

    def mark_read(self, notification_id):
        notification = Notification.objects.filter(id=notification_id, user=self.user).first()
        if notification is None:
            raise OOEException('Notification not found')

        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=['read_at'])

        return {'status': 'success'}

    def mark_all_read(self):
        Notification.objects.filter(
            user=self.user, read_at__isnull=True
        ).update(read_at=timezone.now())

        return {'status': 'success'}
