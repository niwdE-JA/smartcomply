"""
API views for the monitoring app.

This module contains ViewSets for managing transactions, rules, and alerts.
All endpoints support filtering, searching, and pagination.
"""
import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .models import Transaction, Rule, Alert
from .serializers import TransactionSerializer, RuleSerializer, AlertSerializer
from .tasks import evaluate_transaction_rules

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    """Standard pagination for API responses."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing financial transactions.
    
    Supports:
    - Creating and listing transactions
    - Filtering by account_id, transaction_type, currency
    - Searching by transaction_id and account_id
    - Sorting by timestamp, amount, created_at
    - Automatic async rule evaluation on transaction creation
    """
    
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_id', 'transaction_type', 'currency']
    search_fields = ['transaction_id', 'account_id']
    ordering_fields = ['timestamp', 'amount', 'created_at']
    ordering = ['-timestamp']
    
    @extend_schema(
        summary='Create a new transaction',
        description='Submit a financial transaction for monitoring. The transaction will be automatically queued for rule evaluation.',
        request=TransactionSerializer,
        responses={201: TransactionSerializer},
        examples=[
            {
                'request': {
                    'transaction_id': 'TXN001',
                    'account_id': 'ACC123',
                    'amount': '5000.00',
                    'currency': 'USD',
                    'transaction_type': 'TRANSFER',
                    'timestamp': '2026-06-01T10:00:00Z'
                }
            }
        ]
    )
    def create(self, request, *args, **kwargs):
        """Override create to return custom response."""
        response = super().create(request, *args, **kwargs)
        response.status_code = status.HTTP_201_CREATED
        response.data['message'] = 'Transaction submitted for processing'
        return response
    
    def perform_create(self, serializer):
        """Create transaction and queue it for rule evaluation."""
        transaction = serializer.save()
        logger.info(f"Transaction created: {transaction.transaction_id}")
        
        # Queue the transaction for async rule evaluation
        evaluate_transaction_rules.delay(str(transaction.id))
        logger.info(f"Transaction {transaction.transaction_id} queued for rule evaluation")
    
    @extend_schema(
        summary='List all transactions',
        description='Retrieve a paginated list of transactions with optional filtering and sorting.',
        parameters=[
            OpenApiParameter(
                name='account_id',
                description='Filter by account ID',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='transaction_type',
                description='Filter by transaction type (TRANSFER, DEPOSIT, WITHDRAWAL, PAYMENT)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='currency',
                description='Filter by currency code (e.g., USD, EUR)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='search',
                description='Search by transaction_id or account_id',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='ordering',
                description='Sort by field: timestamp, amount, created_at (prefix with - for descending)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='page',
                description='Page number',
                required=False,
                type=OpenApiTypes.INT
            ),
            OpenApiParameter(
                name='page_size',
                description='Items per page (max 100)',
                required=False,
                type=OpenApiTypes.INT
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        """List transactions with filtering and pagination."""
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get transactions by account',
        description='Retrieve all transactions for a specific account.',
        parameters=[
            OpenApiParameter(
                name='account_id',
                description='Account ID (required)',
                required=True,
                type=OpenApiTypes.STR
            ),
        ],
    )
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
    """
    API endpoints for managing monitoring rules.
    
    Supports:
    - Creating rules (LARGE_TRANSACTION, HIGH_FREQUENCY)
    - Listing and filtering rules
    - Activating/deactivating rules
    - Rule configuration management
    """
    
    queryset = Rule.objects.all()
    serializer_class = RuleSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rule_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    @extend_schema(
        summary='Create a new rule',
        description='''Create a monitoring rule. Supported rule types:
        
- LARGE_TRANSACTION: Alert when transaction amount exceeds threshold
- HIGH_FREQUENCY: Alert when 5+ transactions occur within 24 hours
        ''',
        request=RuleSerializer,
        responses={201: RuleSerializer},
    )
    def create(self, request, *args, **kwargs):
        """Create a new rule."""
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Create rule."""
        rule = serializer.save()
        logger.info(f"Rule created: {rule.name} (type: {rule.rule_type})")
    
    def perform_update(self, serializer):
        """Update rule."""
        rule = serializer.save()
        logger.info(f"Rule updated: {rule.name}")
    
    @extend_schema(
        summary='Activate a rule',
        description='Enable a rule for monitoring.',
        responses={200: {'description': 'Rule activated successfully'}},
    )
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a rule."""
        rule = self.get_object()
        rule.is_active = True
        rule.save()
        logger.info(f"Rule activated: {rule.name}")
        return Response({'status': 'rule activated'})
    
    @extend_schema(
        summary='Deactivate a rule',
        description='Disable a rule from monitoring.',
        responses={200: {'description': 'Rule deactivated successfully'}},
    )
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a rule."""
        rule = self.get_object()
        rule.is_active = False
        rule.save()
        logger.info(f"Rule deactivated: {rule.name}")
        return Response({'status': 'rule deactivated'})


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for managing alerts (read-only).
    
    Supports:
    - Listing and filtering alerts
    - Searching alerts by account or transaction
    - Marking alerts as reviewed or dismissed
    - Status tracking (ACTIVE, REVIEWED, DISMISSED, RESOLVED)
    """
    
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rule', 'account_id', 'status']
    search_fields = ['account_id', 'transaction__transaction_id']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    @extend_schema(
        summary='List all alerts',
        description='Retrieve a paginated list of alerts with optional filtering.',
        parameters=[
            OpenApiParameter(
                name='rule',
                description='Filter by rule UUID',
                required=False,
                type=OpenApiTypes.UUID
            ),
            OpenApiParameter(
                name='account_id',
                description='Filter by account ID',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='status',
                description='Filter by alert status (ACTIVE, REVIEWED, DISMISSED, RESOLVED)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='search',
                description='Search by account_id or transaction_id',
                required=False,
                type=OpenApiTypes.STR
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        """List alerts with filtering and pagination."""
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary='Mark alert as reviewed',
        description='Update alert status to REVIEWED.',
        responses={200: {'description': 'Alert marked as reviewed'}},
    )
    @action(detail=True, methods=['post'])
    def mark_reviewed(self, request, pk=None):
        """Mark an alert as reviewed."""
        alert = self.get_object()
        alert.status = 'REVIEWED'
        alert.save()
        logger.info(f"Alert marked as reviewed: {alert.id}")
        return Response({'status': 'alert marked as reviewed'})
    
    @extend_schema(
        summary='Dismiss an alert',
        description='Update alert status to DISMISSED.',
        responses={200: {'description': 'Alert dismissed successfully'}},
    )
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss an alert."""
        alert = self.get_object()
        alert.status = 'DISMISSED'
        alert.save()
        logger.info(f"Alert dismissed: {alert.id}")
        return Response({'status': 'alert dismissed'})
    
    @extend_schema(
        summary='Get alerts by account',
        description='Retrieve all alerts for a specific account.',
        parameters=[
            OpenApiParameter(
                name='account_id',
                description='Account ID (required)',
                required=True,
                type=OpenApiTypes.STR
            ),
        ],
    )
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
