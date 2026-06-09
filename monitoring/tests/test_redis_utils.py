"""
Tests for Redis deduplication and rate limiting functionality.
"""
import pytest
import time
from decimal import Decimal
from django.utils import timezone
from monitoring.models import Transaction, Rule, Alert
from monitoring.redis_utils import (
    get_redis_connection,
    is_alert_duplicate,
    mark_alert_dedup,
    clear_alert_dedup,
    check_rate_limit,
    reset_rate_limit,
    get_duplicate_alerts,
    mark_multiple_alerts_dedup,
    set_cache,
    get_cache,
    delete_cache
)


class TestAlertDeduplication:
    """Tests for alert deduplication using Redis."""
    
    @pytest.mark.django_db
    def test_mark_and_check_alert_dedup(self):
        """Test marking and checking alert deduplication."""
        rule_id = '550e8400-e29b-41d4-a716-446655440000'
        account_id = 'ACC123'
        
        # Initially should not be duplicate
        is_dup = is_alert_duplicate(rule_id, account_id, time_window_minutes=60)
        assert is_dup is False
        
        # Mark as deduplicated
        marked = mark_alert_dedup(rule_id, account_id, time_window_minutes=60)
        assert marked is True
        
        # Now should be duplicate
        is_dup = is_alert_duplicate(rule_id, account_id, time_window_minutes=60)
        assert is_dup is True
    
    @pytest.mark.django_db
    def test_clear_alert_dedup(self):
        """Test clearing deduplication flag."""
        rule_id = '550e8400-e29b-41d4-a716-446655440001'
        account_id = 'ACC124'
        
        # Mark as deduplicated
        mark_alert_dedup(rule_id, account_id)
        
        # Verify it's duplicate
        is_dup = is_alert_duplicate(rule_id, account_id)
        assert is_dup is True
        
        # Clear dedup
        cleared = clear_alert_dedup(rule_id, account_id)
        assert cleared > 0
        
        # Should no longer be duplicate
        is_dup = is_alert_duplicate(rule_id, account_id)
        assert is_dup is False
    
    @pytest.mark.django_db
    def test_dedup_expiration(self):
        """Test that dedup flags expire after time window."""
        rule_id = '550e8400-e29b-41d4-a716-446655440002'
        account_id = 'ACC125'
        
        # Mark with short TTL (1 second)
        mark_alert_dedup(rule_id, account_id, time_window_minutes=0.016)  # ~1 second
        assert is_alert_duplicate(rule_id, account_id) is True
        
        # Wait for expiration
        time.sleep(2)
        
        # Should no longer be duplicate
        is_dup = is_alert_duplicate(rule_id, account_id)
        assert is_dup is False
    
    @pytest.mark.django_db
    def test_get_duplicate_alerts_batch(self):
        """Test batch checking of duplicate alerts."""
        rule_id = '550e8400-e29b-41d4-a716-446655440003'
        accounts = ['ACC201', 'ACC202', 'ACC203']
        
        # Mark first two as duplicate
        mark_alert_dedup(rule_id, accounts[0])
        mark_alert_dedup(rule_id, accounts[1])
        
        # Check batch
        duplicates = get_duplicate_alerts(rule_id, accounts)
        
        assert len(duplicates) == 2
        assert accounts[0] in duplicates
        assert accounts[1] in duplicates
        assert accounts[2] not in duplicates
    
    @pytest.mark.django_db
    def test_mark_multiple_alerts_dedup(self):
        """Test marking multiple alerts as deduplicated."""
        rule_id = '550e8400-e29b-41d4-a716-446655440004'
        accounts = ['ACC301', 'ACC302', 'ACC303']
        
        # Mark all as deduplicated
        count = mark_multiple_alerts_dedup(rule_id, accounts, time_window_minutes=60)
        assert count == len(accounts)
        
        # Verify all are duplicates
        for account_id in accounts:
            assert is_alert_duplicate(rule_id, account_id) is True


class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    def test_rate_limit_initial_request(self):
        """Test rate limit on initial request."""
        identifier = 'test_user_1'
        allowed, remaining, reset_time = check_rate_limit(
            identifier=identifier,
            rate_type='api',
            max_requests=5,
            window_seconds=60
        )
        
        assert allowed is True
        assert remaining == 4  # 5 allowed, 1 used
        assert reset_time > 0
        
        # Cleanup
        reset_rate_limit(identifier, 'api')
    
    def test_rate_limit_exceeded(self):
        """Test rate limit when exceeded."""
        identifier = 'test_user_2'
        max_requests = 3
        
        # Make requests up to limit
        for i in range(max_requests):
            allowed, remaining, _ = check_rate_limit(
                identifier=identifier,
                rate_type='api',
                max_requests=max_requests,
                window_seconds=60
            )
            assert allowed is True
        
        # Next request should be denied
        allowed, remaining, _ = check_rate_limit(
            identifier=identifier,
            rate_type='api',
            max_requests=max_requests,
            window_seconds=60
        )
        assert allowed is False
        assert remaining == 0
        
        # Cleanup
        reset_rate_limit(identifier, 'api')
    
    def test_rate_limit_reset(self):
        """Test resetting rate limit."""
        identifier = 'test_user_3'
        max_requests = 2
        
        # Make requests to exceed limit
        for i in range(max_requests + 1):
            check_rate_limit(
                identifier=identifier,
                rate_type='api',
                max_requests=max_requests,
                window_seconds=60
            )
        
        # Should be limited
        allowed, _, _ = check_rate_limit(
            identifier=identifier,
            rate_type='api',
            max_requests=max_requests,
            window_seconds=60
        )
        assert allowed is False
        
        # Reset
        reset_rate_limit(identifier, 'api')
        
        # Should be allowed again
        allowed, _, _ = check_rate_limit(
            identifier=identifier,
            rate_type='api',
            max_requests=max_requests,
            window_seconds=60
        )
        assert allowed is True
        
        # Cleanup
        reset_rate_limit(identifier, 'api')
    
    def test_rate_limit_different_types(self):
        """Test that different rate limit types are separate."""
        identifier = 'test_user_4'
        max_requests = 2
        
        # Fill up 'api' limit
        for i in range(max_requests + 1):
            check_rate_limit(
                identifier=identifier,
                rate_type='api',
                max_requests=max_requests,
                window_seconds=60
            )
        
        # 'api' should be limited
        allowed_api, _, _ = check_rate_limit(
            identifier=identifier,
            rate_type='api',
            max_requests=max_requests,
            window_seconds=60
        )
        assert allowed_api is False
        
        # 'task' should still be allowed
        allowed_task, _, _ = check_rate_limit(
            identifier=identifier,
            rate_type='task',
            max_requests=max_requests,
            window_seconds=60
        )
        assert allowed_task is True
        
        # Cleanup
        reset_rate_limit(identifier, 'api')
        reset_rate_limit(identifier, 'task')


class TestCaching:
    """Tests for Redis caching functionality."""
    
    def test_set_and_get_cache(self):
        """Test setting and getting cache values."""
        key = 'test_cache_key'
        value = 'test_value_123'
        
        # Set cache
        success = set_cache(key, value, timeout=60)
        assert success is True
        
        # Get cache
        cached_value = get_cache(key)
        assert cached_value == value
        
        # Cleanup
        delete_cache(key)
    
    def test_cache_expiration(self):
        """Test cache key expiration."""
        key = 'test_cache_expire'
        value = 'expire_test'
        
        # Set cache with 1 second timeout
        set_cache(key, value, timeout=1)
        
        # Should exist initially
        assert get_cache(key) == value
        
        # Wait for expiration
        time.sleep(2)
        
        # Should not exist
        assert get_cache(key) is None
    
    def test_delete_cache(self):
        """Test deleting cache entries."""
        key = 'test_cache_delete'
        value = 'delete_test'
        
        # Set cache
        set_cache(key, value, timeout=60)
        assert get_cache(key) == value
        
        # Delete cache
        deleted = delete_cache(key)
        assert deleted > 0
        
        # Should not exist
        assert get_cache(key) is None


class TestRedisConnection:
    """Tests for Redis connection functionality."""
    
    def test_redis_connection(self):
        """Test that Redis connection works."""
        redis_conn = get_redis_connection()
        assert redis_conn is not None
        
        # Test basic operations
        redis_conn.set('test_key', 'test_value')
        value = redis_conn.get('test_key')
        assert value == 'test_value'
        
        # Cleanup
        redis_conn.delete('test_key')
