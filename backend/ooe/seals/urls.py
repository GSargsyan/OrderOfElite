from django.urls import path
from .views import \
    get_tab_data, \
    compile_preview, \
    send, \
    discard_draft, \
    withdraw, \
    sign, \
    decline, \
    annul

urlpatterns = [
    path('api/seals/get_tab_data', get_tab_data, name='seals_get_tab_data'),
    path('api/seals/compile', compile_preview, name='seals_compile'),
    path('api/seals/send', send, name='seals_send'),
    path('api/seals/discard_draft', discard_draft, name='seals_discard_draft'),
    path('api/seals/withdraw', withdraw, name='seals_withdraw'),
    path('api/seals/sign', sign, name='seals_sign'),
    path('api/seals/decline', decline, name='seals_decline'),
    path('api/seals/annul', annul, name='seals_annul'),
]
