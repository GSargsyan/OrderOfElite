from django.urls import path
from .views import \
    get_tab_data, \
    create_draft, \
    add_condition, \
    update_condition, \
    remove_condition, \
    discard_draft, \
    submit_for_approval, \
    approve_draft, \
    reject_draft

urlpatterns = [
    path('api/grand_council/get_tab_data', get_tab_data, name='grand_council_get_tab_data'),
    path('api/grand_council/create_draft', create_draft, name='grand_council_create_draft'),
    path('api/grand_council/add_condition', add_condition, name='grand_council_add_condition'),
    path('api/grand_council/update_condition', update_condition, name='grand_council_update_condition'),
    path('api/grand_council/remove_condition', remove_condition, name='grand_council_remove_condition'),
    path('api/grand_council/discard_draft', discard_draft, name='grand_council_discard_draft'),
    path('api/grand_council/submit_for_approval', submit_for_approval, name='grand_council_submit_for_approval'),
    path('api/grand_council/approve_draft', approve_draft, name='grand_council_approve_draft'),
    path('api/grand_council/reject_draft', reject_draft, name='grand_council_reject_draft'),
]
