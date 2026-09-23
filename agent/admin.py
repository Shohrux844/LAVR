from django.contrib import admin
from .models import Agent, AgentBalance


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "phone",
        "user",
        "commission_rate",
        "balance_limit",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "first_name",
        "last_name",
        "phone",
        "user__username",
    )

    autocomplete_fields = ("user",)


@admin.register(AgentBalance)
class AgentBalanceAdmin(admin.ModelAdmin):
    list_display = ['agent', 'date', 'given_amount', 'returned_amount', 'remaining']
    list_filter = ['date']
