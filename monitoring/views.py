"""
API views for the monitoring app.
"""
import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import Transaction, Rule, Alert
from .serializers import TransactionSerializer, RuleSerializer, AlertSerializer
from .tasks import evaluate_transaction_rules

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for Transaction model."""
    
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_id', 'transaction_type', 'currency']
    search_fields = ['transaction_id', 'account_id']
    ordering_fields = ['timestamp', 'amount', 'created_at']
    ordering = ['-timestamp']
    
    def perform_create(self, serializer):
        """Create transaction and queue it for rule evaluation."""
        transaction = serializer.save()
        logger.info(f"Transaction created: {transaction.transaction_id}")
        
        # Queue the transaction for async rule evaluation
        evaluate_transaction_rules.delay(str(transaction.id))
        logger.info(f"Transaction {transaction.transaction_id} queued for rule evaluation")
        
    def create(self, request, *args, **kwargs):
        """Override create to return custom response."""
        response = super().create(request, *args, **kwargs)
        response.status_code = status.HTTP_201_CREATED
        response.data['message'] = 'Transaction submitted for processing'
        return response
    
    @action(detail=False, methods=['get'])
    def by_account(self, request):
        """Get transactions for a specific account."""
        account_id = request.query_params.get('account_id')
        if not account_id:
            return Response(
                {'error': 'account_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transactions = self.queryset.filter(account_id=account_id)
        page = self.paginate_queryset(transactions)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)


class RuleViewSet(viewsets.ModelViewSet):
    """ViewSet for Rule model."""
    
    queryset = Rule.objects.all()
    serializer_class = RuleSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rule_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Create rule."""
        rule = serializer.save()
        logger.info(f"Rule created: {rule.name} (type: {rule.rule_type})")
    
    def perform_update(self, serializer):
        """Update rule."""
        rule = serializer.save()
        logger.info(f"Rule updated: {rule.name}")
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a rule."""
        rule = self.get_object()
        rule.is_active = True
        rule.save()
        logger.info(f"Rule activated: {rule.name}")
        return Response({'status': 'rule activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a rule."""
        rule = self.get_object()
        rule.is_active = False
        rule.save()
        logger.info(f"Rule deactivated: {rule.name}")
        return Response({'status': 'rule deactivated'})


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Alert model (read-only)."""
    
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rule', 'account_id', 'status']
    search_fields = ['account_id', 'transaction__transaction_id']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def mark_reviewed(self, request, pk=None):
        """Mark an alert as reviewed."""
        alert = self.get_object()
        alert.status = 'REVIEWED'
        alert.save()
        logger.info(f"Alert marked as reviewed: {alert.id}")
        return Response({'status': 'alert marked as reviewed'})
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss an alert."""
        alert = self.get_object()
        alert.status = 'DISMISSED'
        alert.save()
        logger.info(f"Alert dismissed: {alert.id}")
        return Response({'status': 'alert dismissed'})
    
    @action(detail=False, methods=['get'])
    def by_account(self, request):
        """Get alerts for a specific account."""
        account_id = request.query_params.get('account_id')
        if not account_id:
            return Response(
                {'error': 'account_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alerts = self.queryset.filter(account_id=account_id)
        page = self.paginate_queryset(alerts)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
