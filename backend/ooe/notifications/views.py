from rest_framework.decorators import api_view
from rest_framework.response import Response

from ooe.base.utils import auth_by_token
from ooe.base.exceptions import OOEException
from ooe.notifications.controllers import NotificationsController


@api_view(['POST'])
@auth_by_token
def get_notifications_data(request):
    return Response(
        NotificationsController(request.user).get_notifications_data(),
        status=200)


@api_view(['POST'])
@auth_by_token
def mark_read(request):
    try:
        return Response(
            NotificationsController(request.user).mark_read(request.data.get('notification_id')),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
def mark_all_read(request):
    return Response(
        NotificationsController(request.user).mark_all_read(),
        status=200)
