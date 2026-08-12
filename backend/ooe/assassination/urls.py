from django.urls import path
from .views import initiate_search, get_search_history

urlpatterns = [
    path('api/assassination/search', initiate_search, name='initiate_search'),
    path('api/assassination/get_search_history', get_search_history, name='get_search_history'),
]
