"""
Initial migration for the monitoring app.

Creates Transaction, Rule (without `created_by`), and Alert models.
This aligns with the subsequent 0002_add_audit_trail migration which adds
`created_by` and creates the RuleAuditLog model.
"""
from django.db import migrations, models
import uuid
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('transaction_id', models.CharField(max_length=255, unique=True, db_index=True)),
                ('account_id', models.CharField(max_length=255, db_index=True)),
                ('amount', models.DecimalField(max_digits=20, decimal_places=2)),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('transaction_type', models.CharField(max_length=20, choices=[('TRANSFER', 'Transfer'), ('DEPOSIT', 'Deposit'), ('WITHDRAWAL', 'Withdrawal'), ('PAYMENT', 'Payment')])),
                ('timestamp', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-timestamp'],
                'indexes': [
                    models.Index(fields=['account_id', 'timestamp'], name='monitoring_txn_account_timestamp_idx'),
                    models.Index(fields=['transaction_id'], name='monitoring_txn_transaction_id_idx'),
                    models.Index(fields=['created_at'], name='monitoring_txn_created_at_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, unique=True, db_index=True)),
                ('rule_type', models.CharField(max_length=50, choices=[('LARGE_TRANSACTION', 'Large Transaction'), ('HIGH_FREQUENCY', 'High Transaction Frequency')])),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount_threshold', models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)),
                ('transaction_frequency_limit', models.IntegerField(default=5, null=True, blank=True)),
                ('time_window_minutes', models.IntegerField(default=1440, null=True, blank=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['is_active', 'created_at'], name='monitoring_r_is_active_created_at_idx'),
                    models.Index(fields=['rule_type'], name='monitoring_r_rule_type_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('account_id', models.CharField(max_length=255, db_index=True)),
                ('status', models.CharField(max_length=20, choices=[('ACTIVE', 'Active'), ('REVIEWED', 'Reviewed'), ('DISMISSED', 'Dismissed'), ('RESOLVED', 'Resolved')], default='ACTIVE', db_index=True)),
                ('details', models.JSONField(default=dict, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='monitoring.rule')),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='monitoring.transaction')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['account_id', 'created_at'], name='monitoring_a_account_created_at_idx'),
                    models.Index(fields=['status', 'created_at'], name='monitoring_a_status_created_at_idx'),
                    models.Index(fields=['rule', 'created_at'], name='monitoring_a_rule_created_at_idx'),
                ],
            },
        ),
    ]
