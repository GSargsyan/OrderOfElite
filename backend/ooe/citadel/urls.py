from django.urls import path
from .views import get_tab_data, enter, leave

urlpatterns = [
    path('api/citadel/get_tab_data', get_tab_data),
    path('api/citadel/enter', enter),
    path('api/citadel/leave', leave),
]
