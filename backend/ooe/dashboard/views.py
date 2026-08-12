from rest_framework.decorators import api_view
from rest_framework.response import Response

from ooe.base.utils import auth_by_token
from ooe.dashboard.controllers import ProfileController


@api_view(['POST'])
@auth_by_token
def get_profile_tab_data(request):
    return Response(ProfileController.get_profile_tab_data(request.user), status=200)
