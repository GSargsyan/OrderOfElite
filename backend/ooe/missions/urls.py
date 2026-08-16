from django.urls import path
from .views import \
    get_missions_tab_data, \
    start_mission, \
    party_mission_action

urlpatterns = [
    path('api/missions/get_missions_tab_data', get_missions_tab_data, name='get_missions_tab_data'),
    path('api/missions/start/<str:mission_name>', start_mission, name='start_mission'),
    path('api/missions/party/<str:mission_type>/<str:action>', party_mission_action, name='party_mission_action'),
]
