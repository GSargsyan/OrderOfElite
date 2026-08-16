from django.urls import path
from .views import \
    get_notifications_data, \
    mark_read, \
    mark_all_read

urlpatterns = [
    path('api/notifications/get_notifications_data', get_notifications_data, name='get_notifications_data'),
    path('api/notifications/mark_read', mark_read, name='mark_read'),
    path('api/notifications/mark_all_read', mark_all_read, name='mark_all_read'),
]
