from functools import wraps
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status


def auth_by_token(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Get the token from headers (or wherever you store it)
        token_key = request.headers.get('Authorization', '').split(' ')[-1]

        try:
            token = Token.objects.get(key=token_key)
            request.user = token.user
        except Token.DoesNotExist:
            return Response({"error": "Unauthorized"},
                            status=status.HTTP_401_UNAUTHORIZED)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def blocked_in_citadel(view_func):
    """
    Rejects the request if the user is inside the Citadel.
    Must be applied below auth_by_token (needs request.user).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        from ooe.citadel.controllers import CitadelController

        if CitadelController.get_active_stay(request.user):
            return Response({
                'status': 'error',
                'message': 'No business shall be conducted on Citadel grounds.',
            }, status=status.HTTP_400_BAD_REQUEST)

        return view_func(request, *args, **kwargs)

    return _wrapped_view