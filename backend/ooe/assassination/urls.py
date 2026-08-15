from django.urls import path
from .views import initiate_search, get_search_history, get_attack_panel_data, attempt_assassination

urlpatterns = [
    path('api/assassination/search', initiate_search, name='initiate_search'),
    path('api/assassination/get_search_history', get_search_history, name='get_search_history'),
    path('api/assassination/get_attack_panel_data', get_attack_panel_data, name='get_attack_panel_data'),
    path('api/assassination/attempt', attempt_assassination, name='attempt_assassination'),
]
