from django.db import models


class Notification(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    notif_type = models.CharField(max_length=30)
    message = models.CharField(max_length=255)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ooe_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read_at']),
        ]
