"""
Admin configuration for the monitoring app.
"""
from django.contrib import admin
from .models import Transaction, Rule, Alert, RuleAuditLog


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'account_id', 'amount', 'transaction_type', 'timestamp', 'created_at']
    list_filter = ['transaction_type', 'currency', 'created_at']
    search_fields = ['transaction_id', 'account_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-timestamp']


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'is_active', 'created_by', 'created_at']
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
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
        ('Metadata', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )


@admin.register(RuleAuditLog)
class RuleAuditLogAdmin(admin.ModelAdmin):
    list_display = ['rule', 'action', 'performed_by', 'timestamp']
    list_filter = ['action', 'timestamp', 'performed_by']
    search_fields = ['rule__name', 'performed_by', 'description']
    readonly_fields = ['id', 'rule', 'action', 'performed_by', 'timestamp', 'changes', 'description']
    ordering = ['-timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('rule', 'action', 'performed_by', 'timestamp')
        }),
        ('Changes', {
            'fields': ('changes', 'description')
        }),
        ('Metadata', {
            'fields': ('id',),
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
