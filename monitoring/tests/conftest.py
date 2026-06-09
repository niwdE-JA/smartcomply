"""
Test configuration and fixtures.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pytest
from django.conf import settings

pytest_plugins = ['pytest_django']
