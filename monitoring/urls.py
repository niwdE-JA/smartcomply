"""
URL configuration for the monitoring app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, RuleViewSet, AlertViewSet, RuleAuditLogViewSet

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'rules', RuleViewSet, basename='rule')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'audit-logs', RuleAuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
