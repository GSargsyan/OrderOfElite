from django.urls import path
from .views import get_profile_tab_data

urlpatterns = [
    path('api/dashboard/get_profile_tab_data', get_profile_tab_data, name='get_profile_tab_data'),
]
