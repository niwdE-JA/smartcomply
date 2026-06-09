"""
Migration to add audit trail support.

This migration:
1. Adds the created_by field to the Rule model
2. Creates the RuleAuditLog model for tracking rule changes
"""
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='rule',
            name='created_by',
            field=models.CharField(default='system', max_length=255),
        ),
        migrations.CreateModel(
            name='RuleAuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(choices=[('CREATE', 'Created'), ('UPDATE', 'Updated'), ('ACTIVATE', 'Activated'), ('DEACTIVATE', 'Deactivated'), ('DELETE', 'Deleted')], max_length=20)),
                ('performed_by', models.CharField(default='system', max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('changes', models.JSONField(blank=True, default=dict)),
                ('description', models.TextField(blank=True)),
                ('rule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='monitoring.rule')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='ruleauditlog',
            index=models.Index(fields=['rule', 'timestamp'], name='monitoring_r_rule_id_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='ruleauditlog',
            index=models.Index(fields=['action', 'timestamp'], name='monitoring_r_action_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='ruleauditlog',
            index=models.Index(fields=['performed_by', 'timestamp'], name='monitoring_r_performed_by_timestamp_idx'),
        ),
    ]
