"""
Serializers for the monitoring app.
"""
from rest_framework import serializers
from .models import Transaction, Rule, Alert


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model."""
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_id',
            'account_id',
            'amount',
            'currency',
            'transaction_type',
            'timestamp',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RuleSerializer(serializers.ModelSerializer):
    """Serializer for Rule model."""
    
    class Meta:
        model = Rule
        fields = [
            'id',
            'name',
            'rule_type',
            'description',
            'is_active',
            'amount_threshold',
            'transaction_frequency_limit',
            'time_window_minutes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert model."""
    
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    transaction_id = serializers.CharField(source='transaction.transaction_id', read_only=True)
    
    class Meta:
        model = Alert
        fields = [
            'id',
            'rule',
            'rule_name',
            'transaction',
            'transaction_id',
            'account_id',
            'status',
            'details',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'rule', 'transaction', 'created_at', 'updated_at']
