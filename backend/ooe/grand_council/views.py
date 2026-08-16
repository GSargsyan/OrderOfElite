from functools import wraps

from rest_framework.decorators import api_view
from rest_framework.response import Response

from ooe.base.utils import auth_by_token
from ooe.base.exceptions import OOEException
from ooe.grand_council.controllers import GrandCouncilController
from ooe.grand_council.models import OrderOfEliteApproval


def council_member_required(view_func):
    """Must be applied below auth_by_token (needs request.user)."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not GrandCouncilController.is_current_council_member(request.user):
            return Response({
                'status': 'error',
                'message': 'This action is reserved for current Grand Council members.',
            }, status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@api_view(['POST'])
@auth_by_token
def get_tab_data(request):
    return Response(GrandCouncilController.get_tab_data(request.user), status=200)


@api_view(['POST'])
@auth_by_token
@council_member_required
def create_draft(request):
    try:
        return Response(GrandCouncilController.create_draft(request.user), status=200)
    except OOEException as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)


@api_view(['POST'])
@auth_by_token
@council_member_required
def add_condition(request):
    try:
        return Response(
            GrandCouncilController.add_condition(
                user=request.user,
                version_id=request.data.get('version_id'),
                title=request.data.get('title'),
                content=request.data.get('content'),
                condition_type=request.data.get('condition_type'),
                consequence=request.data.get('consequence'),
                png_days=request.data.get('png_days'),
                bounty_amount=request.data.get('bounty_amount'),
            ),
            status=200)
    except OOEException as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)


@api_view(['POST'])
@auth_by_token
@council_member_required
def update_condition(request):
    try:
        return Response(
            GrandCouncilController.update_condition(
                user=request.user,
                version_id=request.data.get('version_id'),
                condition_id=request.data.get('condition_id'),
                title=request.data.get('title'),
                content=request.data.get('content'),
                condition_type=request.data.get('condition_type'),
                consequence=request.data.get('consequence'),
                png_days=request.data.get('png_days'),
                bounty_amount=request.data.get('bounty_amount'),
            ),
            status=200)
    except OOEException as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)


@api_view(['POST'])
@auth_by_token
@council_member_required
def remove_condition(request):
    try:
        return Response(
            GrandCouncilController.remove_condition(
                user=request.user,
                version_id=request.data.get('version_id'),
                condition_id=request.data.get('condition_id'),
            ),
            status=200)
    except OOEException as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)


def _version_transition_view(controller_method):
    @api_view(['POST'])
    @auth_by_token
    @council_member_required
    def view(request):
        try:
            return Response(
                controller_method(request.user, request.data.get('version_id')),
                status=200)
        except OOEException as e:
            return Response({
                'status': 'error',
                'message': str(e),
            }, status=400)

    return view


def _vote_view(decision):
    @api_view(['POST'])
    @auth_by_token
    @council_member_required
    def view(request):
        try:
            return Response(
                GrandCouncilController.cast_vote(
                    request.user, request.data.get('version_id'), decision),
                status=200)
        except OOEException as e:
            return Response({
                'status': 'error',
                'message': str(e),
            }, status=400)

    return view


discard_draft = _version_transition_view(GrandCouncilController.discard_draft)
submit_for_approval = _version_transition_view(GrandCouncilController.submit_for_approval)
approve_draft = _vote_view(OrderOfEliteApproval.APPROVE)
reject_draft = _vote_view(OrderOfEliteApproval.REJECT)
