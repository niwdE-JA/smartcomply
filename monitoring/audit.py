"""
Audit logging utilities for tracking changes to rules.
"""
import json
import logging
from .models import Rule, RuleAuditLog

logger = logging.getLogger(__name__)


def create_audit_log(rule, action, performed_by='system', changes=None, description=''):
    """
    Create an audit log entry for a rule change.
    
    Args:
        rule: Rule instance
        action: Type of action (CREATE, UPDATE, ACTIVATE, DEACTIVATE, DELETE)
        performed_by: User/system identifier who performed the action
        changes: Dict with 'before' and 'after' values
        description: Human-readable description of the change
    """
    try:
        audit_entry = RuleAuditLog.objects.create(
            rule=rule,
            action=action,
            performed_by=performed_by,
            changes=changes or {},
            description=description
        )
        logger.info(
            f"Audit log created: {rule.name} - {action} by {performed_by}",
            extra={
                'rule_id': str(rule.id),
                'action': action,
                'performed_by': performed_by,
            }
        )
        return audit_entry
    except Exception as e:
        logger.error(f"Failed to create audit log for rule {rule.name}: {str(e)}")
        return None


def get_field_changes(old_instance, new_instance, tracked_fields=None):
    """
    Compare two instances and return a dict of changed fields.
    
    Args:
        old_instance: Original instance before changes
        new_instance: Updated instance after changes
        tracked_fields: List of fields to track (if None, tracks common rule fields)
    
    Returns:
        Dict with 'before' and 'after' keys containing changed field values
    """
    if tracked_fields is None:
        tracked_fields = [
            'name', 'rule_type', 'description', 'is_active',
            'amount_threshold', 'transaction_frequency_limit', 'time_window_minutes'
        ]
    
    changes = {'before': {}, 'after': {}}
    
    for field in tracked_fields:
        old_value = getattr(old_instance, field, None)
        new_value = getattr(new_instance, field, None)
        
        # Convert Decimal to string for JSON serialization
        if hasattr(old_value, '__class__') and old_value.__class__.__name__ == 'Decimal':
            old_value = str(old_value)
        if hasattr(new_value, '__class__') and new_value.__class__.__name__ == 'Decimal':
            new_value = str(new_value)
        
        if old_value != new_value:
            changes['before'][field] = old_value
            changes['after'][field] = new_value
    
    # Return empty dict if no changes
    if not changes['before'] and not changes['after']:
        return {}
    
    return changes
