"""
Tests for the monitoring app.
"""
import pytest
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from monitoring.models import Transaction, Rule, Alert
from monitoring.tasks import evaluate_transaction_rules, check_large_transaction_rule, check_high_frequency_rule


class TestTransactionModel:
    """Tests for Transaction model."""
    
    @pytest.mark.django_db
    def test_create_transaction(self):
        """Test creating a transaction."""
        transaction = Transaction.objects.create(
            transaction_id='TXN001',
            account_id='ACC123',
            amount=Decimal('5000.00'),
            currency='USD',
            transaction_type='TRANSFER',
            timestamp=timezone.now()
        )
        
        assert transaction.transaction_id == 'TXN001'
        assert transaction.account_id == 'ACC123'
        assert transaction.amount == Decimal('5000.00')
        assert transaction.id is not None
    
    @pytest.mark.django_db
    def test_transaction_unique_transaction_id(self):
        """Test that transaction_id is unique."""
        Transaction.objects.create(
            transaction_id='TXN001',
            account_id='ACC123',
            amount=Decimal('5000.00'),
            currency='USD',
            transaction_type='TRANSFER',
            timestamp=timezone.now()
        )
        
        with pytest.raises(Exception):  # IntegrityError
            Transaction.objects.create(
                transaction_id='TXN001',
                account_id='ACC124',
                amount=Decimal('6000.00'),
                currency='USD',
                transaction_type='TRANSFER',
                timestamp=timezone.now()
            )


class TestRuleModel:
    """Tests for Rule model."""
    
    @pytest.mark.django_db
    def test_create_large_transaction_rule(self):
        """Test creating a large transaction rule."""
        rule = Rule.objects.create(
            name='Large Transaction Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True
        )
        
        assert rule.name == 'Large Transaction Rule'
        assert rule.rule_type == 'LARGE_TRANSACTION'
        assert rule.amount_threshold == Decimal('10000.00')
        assert rule.is_active is True
    
    @pytest.mark.django_db
    def test_create_high_frequency_rule(self):
        """Test creating a high frequency rule."""
        rule = Rule.objects.create(
            name='High Frequency Rule',
            rule_type='HIGH_FREQUENCY',
            transaction_frequency_limit=5,
            time_window_minutes=1440,
            is_active=True
        )
        
        assert rule.rule_type == 'HIGH_FREQUENCY'
        assert rule.transaction_frequency_limit == 5
        assert rule.time_window_minutes == 1440


class TestAlertModel:
    """Tests for Alert model."""
    
    @pytest.mark.django_db
    def test_create_alert(self):
        """Test creating an alert."""
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
            account_id=transaction.account_id,
            details={'amount': '15000', 'threshold': '10000'}
        )
        
        assert alert.rule == rule
        assert alert.transaction == transaction
        assert alert.status == 'ACTIVE'
        assert alert.details['amount'] == '15000'


class TestLargeTransactionRule:
    """Tests for large transaction rule evaluation."""
    
    @pytest.mark.django_db
    def test_large_transaction_triggers_alert(self):
        """Test that a large transaction triggers an alert."""
        rule = Rule.objects.create(
            name='Large Transaction Rule',
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
        
        check_large_transaction_rule(transaction, rule)
        
        alert = Alert.objects.get(transaction=transaction, rule=rule)
        assert alert is not None
        assert alert.status == 'ACTIVE'
    
    @pytest.mark.django_db
    def test_small_transaction_no_alert(self):
        """Test that a small transaction does not trigger an alert."""
        rule = Rule.objects.create(
            name='Large Transaction Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True
        )
        
        transaction = Transaction.objects.create(
            transaction_id='TXN001',
            account_id='ACC123',
            amount=Decimal('5000.00'),
            currency='USD',
            transaction_type='TRANSFER',
            timestamp=timezone.now()
        )
        
        check_large_transaction_rule(transaction, rule)
        
        alerts = Alert.objects.filter(transaction=transaction, rule=rule)
        assert alerts.count() == 0


class TestHighFrequencyRule:
    """Tests for high frequency rule evaluation."""
    
    @pytest.mark.django_db
    def test_high_frequency_triggers_alert(self):
        """Test that high transaction frequency triggers an alert."""
        rule = Rule.objects.create(
            name='High Frequency Rule',
            rule_type='HIGH_FREQUENCY',
            transaction_frequency_limit=5,
            time_window_minutes=1440,
            is_active=True
        )
        
        now = timezone.now()
        account_id = 'ACC123'
        
        # Create 6 transactions within 24 hours
        for i in range(6):
            Transaction.objects.create(
                transaction_id=f'TXN{i:03d}',
                account_id=account_id,
                amount=Decimal('1000.00'),
                currency='USD',
                transaction_type='TRANSFER',
                timestamp=now - timedelta(hours=23-i)
            )
        
        # Get the last transaction and check the rule
        last_transaction = Transaction.objects.latest('timestamp')
        check_high_frequency_rule(last_transaction, rule)
        
        alerts = Alert.objects.filter(rule=rule, account_id=account_id)
        assert alerts.count() >= 1
    
    @pytest.mark.django_db
    def test_low_frequency_no_alert(self):
        """Test that low transaction frequency does not trigger an alert."""
        rule = Rule.objects.create(
            name='High Frequency Rule',
            rule_type='HIGH_FREQUENCY',
            transaction_frequency_limit=5,
            time_window_minutes=1440,
            is_active=True
        )
        
        now = timezone.now()
        account_id = 'ACC123'
        
        # Create 3 transactions within 24 hours
        for i in range(3):
            Transaction.objects.create(
                transaction_id=f'TXN{i:03d}',
                account_id=account_id,
                amount=Decimal('1000.00'),
                currency='USD',
                transaction_type='TRANSFER',
                timestamp=now - timedelta(hours=23-i)
            )
        
        last_transaction = Transaction.objects.latest('timestamp')
        check_high_frequency_rule(last_transaction, rule)
        
        alerts = Alert.objects.filter(rule=rule, account_id=account_id)
        assert alerts.count() == 0


class TestRuleAuditLog:
    """Tests for RuleAuditLog model."""
    
    @pytest.mark.django_db
    def test_create_audit_log(self):
        """Test creating an audit log entry."""
        from monitoring.models import RuleAuditLog
        
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        audit_log = RuleAuditLog.objects.create(
            rule=rule,
            action='CREATE',
            performed_by='test_user',
            description='Rule created'
        )
        
        assert audit_log.rule == rule
        assert audit_log.action == 'CREATE'
        assert audit_log.performed_by == 'test_user'
        assert audit_log.id is not None
    
    @pytest.mark.django_db
    def test_audit_log_with_changes(self):
        """Test creating an audit log entry with change tracking."""
        from monitoring.models import RuleAuditLog
        
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        changes = {
            'before': {'is_active': True, 'amount_threshold': '10000.00'},
            'after': {'is_active': False, 'amount_threshold': '10000.00'}
        }
        
        audit_log = RuleAuditLog.objects.create(
            rule=rule,
            action='UPDATE',
            performed_by='test_user',
            changes=changes,
            description='Rule deactivated'
        )
        
        assert audit_log.changes == changes
        assert audit_log.action == 'UPDATE'
    
    @pytest.mark.django_db
    def test_audit_log_ordering(self):
        """Test that audit logs are ordered by timestamp descending."""
        from monitoring.models import RuleAuditLog
        
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        # Create multiple audit logs
        for i in range(3):
            RuleAuditLog.objects.create(
                rule=rule,
                action='UPDATE',
                performed_by='test_user',
                description=f'Update {i}'
            )
        
        logs = RuleAuditLog.objects.filter(rule=rule)
        assert logs.count() == 3
        
        # Verify descending order by timestamp
        log_list = list(logs)
        for i in range(1, len(log_list)):
            assert log_list[i-1].timestamp >= log_list[i].timestamp
    
    @pytest.mark.django_db
    def test_audit_log_actions(self):
        """Test all action types in audit log."""
        from monitoring.models import RuleAuditLog
        
        rule = Rule.objects.create(
            name='Test Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=True,
            created_by='test_user'
        )
        
        actions = ['CREATE', 'UPDATE', 'ACTIVATE', 'DEACTIVATE', 'DELETE']
        
        for action in actions:
            audit_log = RuleAuditLog.objects.create(
                rule=rule,
                action=action,
                performed_by='test_user',
                description=f'Rule {action.lower()}'
            )
            assert audit_log.action == action
        
        assert RuleAuditLog.objects.filter(rule=rule).count() == len(actions)
