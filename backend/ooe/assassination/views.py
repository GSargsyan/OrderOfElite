from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ooe.base.utils import auth_by_token, blocked_in_citadel
from ooe.base.exceptions import OOEException
from ooe.assassination.controllers import AssassinationController


@api_view(['POST'])
@auth_by_token
def get_search_history(request):
    return Response(AssassinationController(request.user).get_search_history(), status=200)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def initiate_search(request):
    target_username = request.data.get('username')
    search_type = request.data.get('search_type')

    try:
        return Response(
            AssassinationController(request.user).initiate_search(target_username, search_type),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
def get_attack_panel_data(request):
    target_username = request.data.get('username')
    return Response(
        AssassinationController(request.user).get_attack_panel_data(target_username),
        status=200)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
def attempt_assassination(request):
    # No @transaction.atomic here on purpose — the controller manages its
    # own atomic block internally so the Redis publish (below the block,
    # inside the controller) only fires once the kill has truly committed.
    target_username = request.data.get('username')
    budget = request.data.get('budget')
    attack_type = request.data.get('attack_type')

    try:
        return Response(
            AssassinationController(request.user).attempt_assassination(target_username, budget, attack_type),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)
