"""
Tests for Celery tasks.
"""
import pytest
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from monitoring.models import Transaction, Rule, Alert
from monitoring.tasks import evaluate_transaction_rules


@pytest.mark.django_db
class TestCeleryTasks:
    """Tests for Celery tasks."""
    
    def test_evaluate_transaction_rules_large_transaction(self):
        """Test evaluating rules for a large transaction."""
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
        
        # Call the task
        evaluate_transaction_rules(str(transaction.id))
        
        # Check that an alert was created
        alert = Alert.objects.get(transaction=transaction, rule=rule)
        assert alert is not None
        assert alert.status == 'ACTIVE'
    
    def test_evaluate_transaction_rules_high_frequency(self):
        """Test evaluating rules for high frequency transactions."""
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
        
        # Get the last transaction
        last_transaction = Transaction.objects.filter(account_id=account_id).latest('timestamp')
        
        # Call the task
        evaluate_transaction_rules(str(last_transaction.id))
        
        # Check that an alert was created
        alerts = Alert.objects.filter(rule=rule, account_id=account_id)
        assert alerts.count() >= 1
    
    def test_evaluate_transaction_rules_no_rules_triggered(self):
        """Test evaluating rules when no rules are triggered."""
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
        
        # Call the task
        evaluate_transaction_rules(str(transaction.id))
        
        # Check that no alert was created
        alerts = Alert.objects.filter(transaction=transaction, rule=rule)
        assert alerts.count() == 0
    
    def test_evaluate_transaction_rules_inactive_rules_ignored(self):
        """Test that inactive rules are not evaluated."""
        rule = Rule.objects.create(
            name='Large Transaction Rule',
            rule_type='LARGE_TRANSACTION',
            amount_threshold=Decimal('10000.00'),
            is_active=False
        )
        
        transaction = Transaction.objects.create(
            transaction_id='TXN001',
            account_id='ACC123',
            amount=Decimal('15000.00'),
            currency='USD',
            transaction_type='TRANSFER',
            timestamp=timezone.now()
        )
        
        # Call the task
        evaluate_transaction_rules(str(transaction.id))
        
        # Check that no alert was created (rule is inactive)
        alerts = Alert.objects.filter(transaction=transaction, rule=rule)
        assert alerts.count() == 0
