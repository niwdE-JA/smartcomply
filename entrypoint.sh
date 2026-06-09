#!/bin/bash

# Script to initialize the application

set -e

echo "Running database migrations..."
python manage.py migrate

echo "Creating default rules..."
python manage.py shell << END
from monitoring.models import Rule
from decimal import Decimal

# Large Transaction Rule
Rule.objects.get_or_create(
    name='Large Transaction Rule',
    defaults={
        'rule_type': 'LARGE_TRANSACTION',
        'amount_threshold': Decimal('10000.00'),
        'is_active': True,
        'description': 'Alerts when a transaction exceeds \$10,000'
    }
)
print("✓ Large Transaction Rule created/verified")

# High Frequency Rule
Rule.objects.get_or_create(
    name='High Frequency Rule',
    defaults={
        'rule_type': 'HIGH_FREQUENCY',
        'transaction_frequency_limit': 5,
        'time_window_minutes': 1440,
        'is_active': True,
        'description': 'Alerts when an account has more than 5 transactions in 24 hours'
    }
)
print("✓ High Frequency Rule created/verified")

print("\nAll rules ready!")
END

echo "Starting application..."
exec "$@"
