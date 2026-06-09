"""
Redis utilities for deduplication and rate limiting.

This module provides helper functions for:
- Alert deduplication (prevent duplicate alerts within time window)
- Rate limiting (limit API requests and async tasks)
- Key generation and expiration management
"""
import logging
import redis
from django.conf import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# Redis connection pool
def get_redis_connection():
    """Get Redis connection from configured settings."""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )


# ============================================================================
# DEDUPLICATION HELPERS
# ============================================================================

def get_alert_dedup_key(rule_id, account_id):
    """
    Generate Redis key for alert deduplication.
    
    Args:
        rule_id: UUID of the rule
        account_id: Account identifier
    
    Returns:
        Redis key string
    """
    return f"alert:dedup:{rule_id}:{account_id}"


def is_alert_duplicate(rule_id, account_id, time_window_minutes=60):
    """
    Check if alert for this rule+account already exists within time window.
    
    Args:
        rule_id: UUID of the rule
        account_id: Account identifier
        time_window_minutes: Deduplication window (default 60 minutes)
    
    Returns:
        True if duplicate found, False otherwise
    """
    try:
        redis_conn = get_redis_connection()
        key = get_alert_dedup_key(rule_id, account_id)
        
        exists = redis_conn.exists(key)
        return bool(exists)
    except Exception as e:
        logger.error(f"Redis dedup check error for {rule_id}:{account_id}: {str(e)}")
        return False  # On error, allow alert to proceed


def mark_alert_dedup(rule_id, account_id, time_window_minutes=60):
    """
    Mark alert as created (set Redis key with expiration).
    
    Args:
        rule_id: UUID of the rule
        account_id: Account identifier
        time_window_minutes: Deduplication window (default 60 minutes)
    
    Returns:
        True if key was set, False on error
    """
    try:
        redis_conn = get_redis_connection()
        key = get_alert_dedup_key(rule_id, account_id)
        ttl = time_window_minutes * 60  # Convert to seconds
        
        # Set key with expiration
        redis_conn.setex(key, ttl, '1')
        logger.info(f"Alert dedup marked for {rule_id}:{account_id} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.error(f"Redis dedup mark error for {rule_id}:{account_id}: {str(e)}")
        return False


def clear_alert_dedup(rule_id, account_id):
    """
    Clear deduplication flag for rule+account (used for testing).
    
    Args:
        rule_id: UUID of the rule
        account_id: Account identifier
    
    Returns:
        Number of keys deleted
    """
    try:
        redis_conn = get_redis_connection()
        key = get_alert_dedup_key(rule_id, account_id)
        deleted = redis_conn.delete(key)
        return deleted
    except Exception as e:
        logger.error(f"Redis dedup clear error for {rule_id}:{account_id}: {str(e)}")
        return 0


# ============================================================================
# RATE LIMITING HELPERS
# ============================================================================

def get_rate_limit_key(identifier, rate_type='api'):
    """
    Generate Redis key for rate limiting.
    
    Args:
        identifier: Unique identifier (user, IP, transaction_id, etc.)
        rate_type: Type of rate limit ('api', 'task', 'alert', etc.)
    
    Returns:
        Redis key string
    """
    return f"ratelimit:{rate_type}:{identifier}"


def check_rate_limit(identifier, rate_type='api', max_requests=100, window_seconds=60):
    """
    Check if identifier has exceeded rate limit.
    
    Args:
        identifier: Unique identifier (user ID, IP, etc.)
        rate_type: Type of rate limit ('api', 'task', 'alert', etc.)
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
    
    Returns:
        Tuple: (allowed: bool, remaining: int, reset_time: int)
        - allowed: True if request is allowed
        - remaining: Number of requests remaining in window
        - reset_time: Unix timestamp when rate limit resets
    """
    try:
        redis_conn = get_redis_connection()
        key = get_rate_limit_key(identifier, rate_type)
        
        # Get current count
        current = redis_conn.incr(key)
        
        # Set expiration on first request
        if current == 1:
            redis_conn.expire(key, window_seconds)
            ttl = window_seconds
        else:
            ttl = redis_conn.ttl(key)
        
        allowed = current <= max_requests
        remaining = max(0, max_requests - current)
        reset_time = int(datetime.now().timestamp()) + ttl
        
        return allowed, remaining, reset_time
    except Exception as e:
        logger.error(f"Rate limit check error for {identifier}:{rate_type}: {str(e)}")
        return True, max_requests, 0  # On error, allow request


def reset_rate_limit(identifier, rate_type='api'):
    """
    Reset rate limit for identifier (used for testing/manual override).
    
    Args:
        identifier: Unique identifier
        rate_type: Type of rate limit
    
    Returns:
        Number of keys deleted
    """
    try:
        redis_conn = get_redis_connection()
        key = get_rate_limit_key(identifier, rate_type)
        deleted = redis_conn.delete(key)
        return deleted
    except Exception as e:
        logger.error(f"Rate limit reset error for {identifier}:{rate_type}: {str(e)}")
        return 0


# ============================================================================
# BULK DEDUPLICATION (for checking multiple alerts)
# ============================================================================

def get_duplicate_alerts(rule_id, account_ids, time_window_minutes=60):
    """
    Check multiple account_ids for duplicate alerts in batch.
    
    Args:
        rule_id: UUID of the rule
        account_ids: List of account identifiers
        time_window_minutes: Deduplication window
    
    Returns:
        List of account_ids that already have active alerts
    """
    try:
        redis_conn = get_redis_connection()
        duplicates = []
        
        for account_id in account_ids:
            key = get_alert_dedup_key(rule_id, account_id)
            if redis_conn.exists(key):
                duplicates.append(account_id)
        
        return duplicates
    except Exception as e:
        logger.error(f"Bulk dedup check error for {rule_id}: {str(e)}")
        return []


def mark_multiple_alerts_dedup(rule_id, account_ids, time_window_minutes=60):
    """
    Mark multiple alerts as created in batch.
    
    Args:
        rule_id: UUID of the rule
        account_ids: List of account identifiers
        time_window_minutes: Deduplication window
    
    Returns:
        Number of keys set
    """
    try:
        redis_conn = get_redis_connection()
        ttl = time_window_minutes * 60  # Convert to seconds
        count = 0
        
        for account_id in account_ids:
            key = get_alert_dedup_key(rule_id, account_id)
            redis_conn.setex(key, ttl, '1')
            count += 1
        
        logger.info(f"Marked {count} alerts for dedup (rule: {rule_id}, TTL: {ttl}s)")
        return count
    except Exception as e:
        logger.error(f"Bulk dedup mark error for {rule_id}: {str(e)}")
        return 0


# ============================================================================
# CACHE HELPERS
# ============================================================================

def set_cache(key, value, timeout=3600):
    """
    Set value in Redis cache with expiration.
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON-serialized)
        timeout: Expiration time in seconds
    
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_conn = get_redis_connection()
        redis_conn.setex(f"cache:{key}", timeout, value)
        return True
    except Exception as e:
        logger.error(f"Cache set error for {key}: {str(e)}")
        return False


def get_cache(key):
    """
    Get value from Redis cache.
    
    Args:
        key: Cache key
    
    Returns:
        Cached value or None if not found
    """
    try:
        redis_conn = get_redis_connection()
        return redis_conn.get(f"cache:{key}")
    except Exception as e:
        logger.error(f"Cache get error for {key}: {str(e)}")
        return None


def delete_cache(key):
    """
    Delete value from Redis cache.
    
    Args:
        key: Cache key
    
    Returns:
        Number of keys deleted
    """
    try:
        redis_conn = get_redis_connection()
        return redis_conn.delete(f"cache:{key}")
    except Exception as e:
        logger.error(f"Cache delete error for {key}: {str(e)}")
        return 0
