from django.contrib import admin

from ooe.grand_council.models import (
    CouncilTerm,
    CouncilMembership,
    OrderOfEliteVersion,
    Condition,
    OrderOfEliteApproval,
)
from ooe.grand_council.controllers import GrandCouncilController


class MembershipInline(admin.TabularInline):
    model = CouncilMembership
    extra = 0
    readonly_fields = ('seat', 'user', 'rank_snapshot', 'kills_snapshot', 'net_worth_snapshot')


class ConditionInline(admin.TabularInline):
    model = Condition
    extra = 0
    fields = ('order', 'title', 'condition_type', 'consequence', 'png_days', 'bounty_amount')


class ApprovalInline(admin.TabularInline):
    model = OrderOfEliteApproval
    extra = 0
    readonly_fields = ('member', 'decision', 'decided_at')


@admin.register(CouncilTerm)
class CouncilTermAdmin(admin.ModelAdmin):
    list_display = ('id', 'started_at', 'ended_at')
    inlines = [MembershipInline]


@admin.register(OrderOfEliteVersion)
class OrderOfEliteVersionAdmin(admin.ModelAdmin):
    list_display = ('version_number', 'status', 'author', 'submitted_at', 'published_at')
    list_filter = ('status',)
    inlines = [ConditionInline, ApprovalInline]
    actions = ['approve_pending', 'reject_pending']

    def approve_pending(self, request, queryset):
        count = 0
        for version in queryset.filter(status=OrderOfEliteVersion.OWNER_REVIEW):
            GrandCouncilController.owner_publish(version)
            count += 1
        self.message_user(request, f'{count} version(s) published.')
    approve_pending.short_description = 'Publish selected (owner-review only)'

    def reject_pending(self, request, queryset):
        count = 0
        for version in queryset.filter(status=OrderOfEliteVersion.OWNER_REVIEW):
            GrandCouncilController.owner_reject(version)
            count += 1
        self.message_user(request, f'{count} version(s) rejected.')
    reject_pending.short_description = 'Reject selected (owner-review only)'
