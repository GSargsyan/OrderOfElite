from django.db import transaction

from rest_framework.decorators import api_view
from rest_framework.response import Response

from ooe.base.utils import auth_by_token, blocked_in_citadel
from ooe.base.exceptions import OOEException
from ooe.travel.controllers import TravelController


@api_view(['POST'])
@auth_by_token
def get_travel_tab_data(request):
    return Response(
        TravelController.get_travel_tab_data(user=request.user),
        status=200,
    )


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def initiate_travel(request):
    try:
        return Response(
            TravelController.initiate_travel(
                user=request.user,
                destination_city_name=request.data['destination_city'],
                airplane_key=request.data['airplane_key'],
            ),
            status=200,
        )
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)
