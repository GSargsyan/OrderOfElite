from rest_framework.decorators import api_view
from rest_framework.response import Response

from ooe.base.utils import auth_by_token
from ooe.base.exceptions import OOEException
from ooe.citadel.controllers import CitadelController


@api_view(['POST'])
@auth_by_token
def get_tab_data(request):
    return Response(
        CitadelController.get_tab_data(user=request.user),
        status=200)


@api_view(['POST'])
@auth_by_token
def enter(request):
    try:
        return Response(
            CitadelController.enter(
                user=request.user,
                minutes=request.data.get('minutes'),
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
def leave(request):
    try:
        return Response(
            CitadelController.leave(user=request.user),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)
