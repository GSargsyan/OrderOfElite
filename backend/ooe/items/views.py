from django.db import transaction

from rest_framework.decorators import api_view
from rest_framework.response import Response
from ooe.base.utils import auth_by_token, blocked_in_citadel

from ooe.base.exceptions import OOEException
from ooe.items.controllers import ItemsController


@api_view(['POST'])
@auth_by_token
def get_user_houses(request):
    return Response(
        ItemsController().get_user_houses(user=request.user),
        status=200)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def buy_house(request):
    try:
        return Response(
            ItemsController().buy_house(
                user=request.user,
                house_name=request.data['house_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def sell_house(request):
    try:
        return Response(
            ItemsController().sell_house(
                user=request.user,
                house_name=request.data['house_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def equip_house(request):
    try:
        return Response(
            ItemsController().equip_house(
                user=request.user,
                house_name=request.data['house_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def unequip_house(request):
    try:
        return Response(
            ItemsController().unequip_house(user=request.user),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
def get_user_cars(request):
    return Response(
        ItemsController().get_user_cars(user=request.user),
        status=200)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def buy_car(request):
    try:
        return Response(
            ItemsController().buy_car(
                user=request.user,
                car_name=request.data['car_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def sell_car(request):
    try:
        return Response(
            ItemsController().sell_car(
                user=request.user,
                car_name=request.data['car_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def equip_car(request):
    try:
        return Response(
            ItemsController().equip_car(
                user=request.user,
                car_name=request.data['car_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def unequip_car(request):
    try:
        return Response(
            ItemsController().unequip_car(user=request.user),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
def get_user_guns(request):
    return Response(
        ItemsController().get_user_guns(user=request.user),
        status=200)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def buy_gun(request):
    try:
        return Response(
            ItemsController().buy_gun(
                user=request.user,
                gun_name=request.data['gun_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def sell_gun(request):
    try:
        return Response(
            ItemsController().sell_gun(
                user=request.user,
                gun_name=request.data['gun_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def equip_gun(request):
    try:
        return Response(
            ItemsController().equip_gun(
                user=request.user,
                gun_name=request.data['gun_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def unequip_gun(request):
    try:
        return Response(
            ItemsController().unequip_gun(user=request.user),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
def get_user_airplanes(request):
    return Response(
        ItemsController().get_user_airplanes(user=request.user),
        status=200)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def buy_airplane(request):
    try:
        return Response(
            ItemsController().buy_airplane(
                user=request.user,
                airplane_name=request.data['airplane_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


@api_view(['POST'])
@auth_by_token
@blocked_in_citadel
@transaction.atomic
def sell_airplane(request):
    try:
        return Response(
            ItemsController().sell_airplane(
                user=request.user,
                airplane_name=request.data['airplane_name'],
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)
