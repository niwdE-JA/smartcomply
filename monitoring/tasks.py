"""
Celery tasks for the monitoring app.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from celery import shared_task
from .models import Transaction, Rule, Alert
from .redis_utils import is_alert_duplicate, mark_alert_dedup, check_rate_limit

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def evaluate_transaction_rules(self, transaction_id):
    """
    Evaluate all active rules against a transaction.
    
    Args:
        transaction_id: UUID of the transaction to evaluate
    """
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        active_rules = Rule.objects.filter(is_active=True)
        
        logger.info(f"Evaluating {active_rules.count()} rules for transaction {transaction.transaction_id}")
        
        for rule in active_rules:
            if rule.rule_type == 'LARGE_TRANSACTION':
                check_large_transaction_rule(transaction, rule)
            elif rule.rule_type == 'HIGH_FREQUENCY':
                check_high_frequency_rule(transaction, rule)
        
        logger.info(f"Rule evaluation completed for transaction {transaction.transaction_id}")
        
    except Transaction.DoesNotExist:
        logger.warning(f"Transaction {transaction_id} not found")
    except Exception as exc:
        logger.error(f"Error evaluating rules for transaction {transaction_id}: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


def check_large_transaction_rule(transaction, rule):
    """
    Check if a transaction exceeds the configured amount threshold.
    
    Uses Redis deduplication to prevent duplicate alerts within a time window.
    
    Args:
        transaction: Transaction instance
        rule: Rule instance
    """
    if rule.amount_threshold is None:
        return
    
    if transaction.amount > rule.amount_threshold:
        logger.info(
            f"Large transaction rule triggered: {transaction.transaction_id} "
            f"({transaction.amount}) exceeds threshold ({rule.amount_threshold})"
        )
        
        # Check Redis deduplication (60 minute window for large transaction alerts)
        if is_alert_duplicate(rule.id, transaction.account_id, time_window_minutes=60):
            logger.info(
                f"Alert already exists for rule {rule.name} and account {transaction.account_id} "
                f"(dedup window: 60 minutes)"
            )
            return
        
        # Check if alert already exists in database (transaction-specific)
        alert_exists = Alert.objects.filter(
            transaction=transaction,
            rule=rule
        ).exists()
        
        if not alert_exists:
            Alert.objects.create(
                rule=rule,
                transaction=transaction,
                account_id=transaction.account_id,
                details={
                    'amount': str(transaction.amount),
                    'threshold': str(rule.amount_threshold),
                    'reason': 'Transaction amount exceeds configured threshold'
                }
            )
            # Mark as deduplicated in Redis
            mark_alert_dedup(rule.id, transaction.account_id, time_window_minutes=60)
            logger.info(f"Alert created for large transaction rule: {transaction.transaction_id}")


def check_high_frequency_rule(transaction, rule):
    """
    Check if an account has more than the configured number of transactions in the time window.
    
    Uses Redis deduplication to prevent duplicate alerts within a time window.
    
    Args:
        transaction: Transaction instance
        rule: Rule instance
    """
    if rule.transaction_frequency_limit is None or rule.time_window_minutes is None:
        return
    
    # Calculate the time window
    time_window_start = transaction.timestamp - timedelta(minutes=rule.time_window_minutes)
    
    # Count transactions for this account in the time window (including current)
    transaction_count = Transaction.objects.filter(
        account_id=transaction.account_id,
        timestamp__gte=time_window_start,
        timestamp__lte=transaction.timestamp
    ).count()
    
    if transaction_count > rule.transaction_frequency_limit:
        logger.info(
            f"High frequency rule triggered: {transaction.account_id} "
            f"({transaction_count}) exceeds limit ({rule.transaction_frequency_limit})"
        )
        
        # Check Redis deduplication (use rule's time window for dedup)
        if is_alert_duplicate(rule.id, transaction.account_id, 
                            time_window_minutes=rule.time_window_minutes):
            logger.info(
                f"Alert already exists for rule {rule.name} and account {transaction.account_id} "
                f"(dedup window: {rule.time_window_minutes} minutes)"
            )
            return
        
        # Create alert
        Alert.objects.create(
            rule=rule,
            transaction=transaction,
            account_id=transaction.account_id,
            details={
                'transaction_count': transaction_count,
                'limit': rule.transaction_frequency_limit,
                'time_window_minutes': rule.time_window_minutes,
                'reason': f'{transaction_count} transactions in {rule.time_window_minutes} minutes'
            }
        )
        # Mark as deduplicated in Redis
        mark_alert_dedup(rule.id, transaction.account_id, 
                        time_window_minutes=rule.time_window_minutes)
        logger.info(f"Alert created for high frequency rule: {transaction.account_id}")
