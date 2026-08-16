from functools import wraps

from rest_framework.decorators import api_view
from rest_framework.response import Response

from ooe.base.utils import auth_by_token
from ooe.base.exceptions import OOEException
from ooe.seals.controllers import SealsController


def premium_required(view_func):
    """Must be applied below auth_by_token (needs request.user)."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_premium:
            return Response({
                'status': 'error',
                'message': 'Seals are available to Premium members only.',
            }, status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@api_view(['POST'])
@auth_by_token
@premium_required
def get_tab_data(request):
    return Response(SealsController.get_tab_data(request.user), status=200)


@api_view(['POST'])
@auth_by_token
@premium_required
def compile_preview(request):
    try:
        return Response(
            SealsController.compile_preview(
                user=request.user,
                counterparty_username=request.data.get('counterparty'),
                raw_text=request.data.get('raw_text'),
                deadline_days=request.data.get('deadline_days'),
                penalty_png_days=request.data.get('penalty_png_days'),
            ),
            status=200)
    except OOEException as e:
        return Response({
            'status': 'error',
            'message': str(e),
        }, status=400)


def _transition_view(controller_method):
    @api_view(['POST'])
    @auth_by_token
    @premium_required
    def view(request):
        try:
            return Response(
                controller_method(request.user, request.data.get('seal_id')),
                status=200)
        except OOEException as e:
            return Response({
                'status': 'error',
                'message': str(e),
            }, status=400)

    return view


send = _transition_view(SealsController.send)
discard_draft = _transition_view(SealsController.discard_draft)
withdraw = _transition_view(SealsController.withdraw)
sign = _transition_view(SealsController.sign)
decline = _transition_view(SealsController.decline)
annul = _transition_view(SealsController.annul)
