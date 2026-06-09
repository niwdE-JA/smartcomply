"""
Tests for API endpoints.
"""
import pytest
import json
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from monitoring.models import Transaction, Rule, Alert


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestTransactionAPI:
    """Tests for Transaction API endpoints."""
    
    def test_create_transaction(self, api_client):
        """Test creating a transaction via API."""
        data = {
            'transaction_id': 'TXN001',
            'account_id': 'ACC123',
            'amount': '5000.00',
            'currency': 'USD',
            'transaction_type': 'TRANSFER',
            'timestamp': timezone.now().isoformat()
        }
        
        response = api_client.post('/api/v1/transactions/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['transaction_id'] == 'TXN001'
        assert Transaction.objects.count() == 1
    
    def test_list_transactions(self, api_client):
        """Test listing transactions."""
        # Create test transactions
        for i in range(5):
            Transaction.objects.create(
                transaction_id=f'TXN{i:03d}',
                account_id='ACC123',
                amount=Decimal(f'{1000 + i * 100}.00'),
                currency='USD',
                transaction_type='TRANSFER',
                timestamp=timezone.now()
            )
        
        response = api_client.get('/api/v1/transactions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
    
    def test_list_transactions_with_filtering(self, api_client):
        """Test filtering transactions by account_id."""
        Transaction.objects.create(
            transaction_id='TXN001',
            account_id='ACC123',
            amount=Decimal('5000.00'),
            currency='USD',
            transaction_type='TRANSFER',
            timestamp=timezone.now()
        )
        
        Transaction.objects.create(
            transaction_id='TXN002',
            account_id='ACC124',
            amount=Decimal('6000.00'),
            currency='USD',
            transaction_type='TRANSFER',
            timestamp=timezone.now()
        )
        
        response = api_client.get('/api/v1/transactions/?account_id=ACC123')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['account_id'] == 'ACC123'
    
    def test_list_transactions_with_ordering(self, api_client):
        """Test ordering transactions."""
        now = timezone.now()
        
        for i in range(3):
            Transaction.objects.create(
                transaction_id=f'TXN{i:03d}',
                account_id='ACC123',
                amount=Decimal(f'{1000 + i * 100}.00'),
                currency='USD',
                transaction_type='TRANSFER',
                timestamp=now - timedelta(hours=i)
            )
        
        response = api_client.get('/api/v1/transactions/?ordering=amount')
        
        assert response.status_code == status.HTTP_200_OK
        amounts = [Decimal(t['amount']) for t in response.data['results']]
        assert amounts == sorted(amounts)


@pytest.mark.django_db
class TestRuleAPI:
    """Tests for Rule API endpoints."""
    
    def test_create_rule(self, api_client):
        """Test creating a rule."""
        data = {
            'name': 'Large Transaction Rule',
            'rule_type': 'LARGE_TRANSACTION',
            'amount_threshold': '10000.00',
            'is_active': True
        }
        
        response = api_client.post('/api/v1/rules/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Large Transaction Rule'
        assert Rule.objects.count() == 1
    
    def test_list_rules(self, api_client):
        """Test listing rules."""
        Rule.objects.create(
            name='Rule 1',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True
        )
        
        Rule.objects.create(
            name='Rule 2',
            rule_type='HIGH_FREQUENCY',
            transaction_frequency_limit=5,
            is_active=True
        )
        
        response = api_client.get('/api/v1/rules/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
    
    def test_activate_rule(self, api_client):
        """Test activating a rule."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=False
        )
        
        response = api_client.post(f'/api/v1/rules/{rule.id}/activate/')
        
        assert response.status_code == status.HTTP_200_OK
        rule.refresh_from_db()
        assert rule.is_active is True
    
    def test_deactivate_rule(self, api_client):
        """Test deactivating a rule."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True
        )
        
        response = api_client.post(f'/api/v1/rules/{rule.id}/deactivate/')
        
        assert response.status_code == status.HTTP_200_OK
        rule.refresh_from_db()
        assert rule.is_active is False


@pytest.mark.django_db
class TestAlertAPI:
    """Tests for Alert API endpoints."""
    
    def test_list_alerts(self, api_client):
        """Test listing alerts."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True
        )
        
        transaction = Transaction.objects.create(
            transaction_id='TXN001',
            account_id='ACC123',
            amount=Decimal('15000.00'),
            currency='USD',
            transaction_type='TRANSFER',
            timestamp=timezone.now()
        )
        
        Alert.objects.create(
            rule=rule,
            transaction=transaction,
            account_id='ACC123'
        )
        
        response = api_client.get('/api/v1/alerts/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
    
    def test_mark_alert_reviewed(self, api_client):
        """Test marking an alert as reviewed."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True
        )
        
        transaction = Transaction.objects.create(
            transaction_id='TXN001',
            account_id='ACC123',
            amount=Decimal('15000.00'),
            currency='USD',
            transaction_type='TRANSFER',
            timestamp=timezone.now()
        )
        
        alert = Alert.objects.create(
            rule=rule,
            transaction=transaction,
            account_id='ACC123'
        )
        
        response = api_client.post(f'/api/v1/alerts/{alert.id}/mark_reviewed/')
        
        assert response.status_code == status.HTTP_200_OK
        alert.refresh_from_db()
        assert alert.status == 'REVIEWED'
    
    def test_dismiss_alert(self, api_client):
        """Test dismissing an alert."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True
        )
        
        transaction = Transaction.objects.create(
            transaction_id='TXN001',
            account_id='ACC123',
            amount=Decimal('15000.00'),
            currency='USD',
            transaction_type='TRANSFER',
            timestamp=timezone.now()
        )
        
        alert = Alert.objects.create(
            rule=rule,
            transaction=transaction,
            account_id='ACC123'
        )
        
        response = api_client.post(f'/api/v1/alerts/{alert.id}/dismiss/')
        
        assert response.status_code == status.HTTP_200_OK
        alert.refresh_from_db()
        assert alert.status == 'DISMISSED'


class TestRuleAuditLogAPI:
    """Tests for RuleAuditLog API endpoints."""
    
    @pytest.mark.django_db
    def test_list_audit_logs(self, api_client):
        """Test listing all audit logs."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        from monitoring.models import RuleAuditLog
        RuleAuditLog.objects.create(
            rule=rule,
            action='CREATE',
            performed_by='test_user',
            description='Rule created'
        )
        
        response = api_client.get('/api/v1/audit-logs/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1
    
    @pytest.mark.django_db
    def test_audit_log_filtering_by_rule(self, api_client):
        """Test filtering audit logs by rule."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        from monitoring.models import RuleAuditLog
        RuleAuditLog.objects.create(
            rule=rule,
            action='CREATE',
            performed_by='test_user',
            description='Rule created'
        )
        
        response = api_client.get(f'/api/v1/audit-logs/?rule={rule.id}')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1
    
    @pytest.mark.django_db
    def test_audit_log_filtering_by_action(self, api_client):
        """Test filtering audit logs by action."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        from monitoring.models import RuleAuditLog
        RuleAuditLog.objects.create(
            rule=rule,
            action='CREATE',
            performed_by='test_user',
            description='Rule created'
        )
        
        response = api_client.get('/api/v1/audit-logs/?action=CREATE')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1
    
    @pytest.mark.django_db
    def test_audit_log_search(self, api_client):
        """Test searching audit logs."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        from monitoring.models import RuleAuditLog
        RuleAuditLog.objects.create(
            rule=rule,
            action='CREATE',
            performed_by='test_user',
            description='Rule created'
        )
        
        response = api_client.get('/api/v1/audit-logs/?search=Test%20Rule')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1
    
    @pytest.mark.django_db
    def test_get_audit_logs_by_rule(self, api_client):
        """Test getting audit logs for a specific rule."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        from monitoring.models import RuleAuditLog
        RuleAuditLog.objects.create(
            rule=rule,
            action='CREATE',
            performed_by='test_user',
            description='Rule created'
        )
        
        response = api_client.get(f'/api/v1/audit-logs/by_rule/?rule_id={rule.id}')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1


class TestRuleActivateDeactivate:
    """Tests for rule activation/deactivation with audit logging."""
    
    @pytest.mark.django_db
    def test_activate_rule_creates_audit_log(self, api_client):
        """Test that activating a rule creates an audit log."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=False,
            created_by='test_user'
        )
        
        response = api_client.post(f'/api/v1/rules/{rule.id}/activate/')
        
        assert response.status_code == status.HTTP_200_OK
        rule.refresh_from_db()
        assert rule.is_active is True
        
        # Verify audit log was created
        from monitoring.models import RuleAuditLog
        audit_log = RuleAuditLog.objects.filter(
            rule=rule,
            action='ACTIVATE'
        ).first()
        
        assert audit_log is not None
        assert 'activated' in audit_log.description.lower()
    
    @pytest.mark.django_db
    def test_deactivate_rule_creates_audit_log(self, api_client):
        """Test that deactivating a rule creates an audit log."""
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        response = api_client.post(f'/api/v1/rules/{rule.id}/deactivate/')
        
        assert response.status_code == status.HTTP_200_OK
        rule.refresh_from_db()
        assert rule.is_active is False
        
        # Verify audit log was created
        from monitoring.models import RuleAuditLog
        audit_log = RuleAuditLog.objects.filter(
            rule=rule,
            action='DEACTIVATE'
        ).first()
        
        assert audit_log is not None
        assert 'deactivated' in audit_log.description.lower()
