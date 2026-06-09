"""
Admin configuration for the monitoring app.
"""
from django.contrib import admin
from .models import Transaction, Rule, Alert


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'account_id', 'amount', 'transaction_type', 'timestamp', 'created_at']
    list_filter = ['transaction_type', 'currency', 'created_at']
    search_fields = ['transaction_id', 'account_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-timestamp']


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'is_active', 'created_at']
    list_filter = ['rule_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'rule_type', 'description', 'is_active')
        }),
        ('Rule Configuration', {
            'fields': ('amount_threshold', 'transaction_frequency_limit', 'time_window_minutes')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['id', 'rule', 'account_id', 'status', 'created_at']
    list_filter = ['rule', 'status', 'created_at']
    search_fields = ['account_id', 'transaction__transaction_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Alert Information', {
            'fields': ('rule', 'transaction', 'account_id', 'status')
        }),
        ('Details', {
            'fields': ('details',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
