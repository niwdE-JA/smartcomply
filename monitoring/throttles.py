"""
Custom throttle classes for rate limiting specific API endpoints.

This module provides throttle classes that use Redis for distributed rate limiting.
"""
import logging
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.exceptions import Throttled
from .redis_utils import check_rate_limit

logger = logging.getLogger(__name__)


class RedisRateThrottle(SimpleRateThrottle):
    """
    Base class for Redis-backed rate throttling.
    
    Provides granular control over which endpoints and identifiers to throttle.
    """
    
    def throttle_success(self):
        """Record successful request."""
        self.history = self.cache.get(self.key, [])
        self.now = self.timer()
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)
        return True
    
    def throttle_failure(self):
        """Handle throttle failure."""
        return False


class TransactionCreateThrottle(SimpleRateThrottle):
    """
    Rate limit for transaction creation endpoint.
    
    Allows 50 transactions per account per minute to prevent overwhelming the system.
    """
    scope = 'transaction_create'
    
    def get_cache_key(self):
        """Use account_id as the throttle key."""
        request = self.request
        
        # Try to get account_id from request data
        account_id = request.data.get('account_id')
        
        if account_id:
            return f'throttle_txn_{account_id}'
        
        # Fall back to user ID if authenticated
        if request.user and request.user.is_authenticated:
            return f'throttle_txn_user_{request.user.id}'
        
        # Fall back to IP address
        return self.get_ident(request)


class RuleManagementThrottle(SimpleRateThrottle):
    """
    Rate limit for rule management endpoints (create, update, delete).
    
    Prevents abuse of rule management endpoints.
    """
    scope = 'rule_management'
    
    def get_cache_key(self):
        """Use user ID or IP address as the throttle key."""
        if self.request.user and self.request.user.is_authenticated:
            return f'throttle_rule_{self.request.user.id}'
        return self.get_ident(self.request)


class AlertDismissalThrottle(SimpleRateThrottle):
    """
    Rate limit for alert dismissal/review endpoints.
    
    Prevents rapid bulk operations on alerts.
    """
    scope = 'alert_dismissal'
    
    def get_cache_key(self):
        """Use user ID or IP address as the throttle key."""
        if self.request.user and self.request.user.is_authenticated:
            return f'throttle_alert_{self.request.user.id}'
        return self.get_ident(self.request)


class RedisTaskThrottle:
    """
    Task-level rate limiting using Redis.
    
    Used in Celery tasks to prevent runaway task execution.
    """
    
    @staticmethod
    def check_task_execution(task_name, identifier, max_per_minute=100):
        """
        Check if a task can be executed based on rate limit.
        
        Args:
            task_name: Name of the task
            identifier: Unique identifier (transaction_id, account_id, etc.)
            max_per_minute: Maximum executions per minute
        
        Returns:
            Tuple: (allowed: bool, remaining: int, reset_time: int)
        """
        allowed, remaining, reset_time = check_rate_limit(
            identifier=f"{task_name}:{identifier}",
            rate_type='task',
            max_requests=max_per_minute,
            window_seconds=60
        )
        
        if not allowed:
            logger.warning(
                f"Task rate limit exceeded: {task_name} for {identifier} "
                f"(reset in {reset_time - int(time.time())} seconds)"
            )
        
        return allowed, remaining, reset_time


class APIEndpointRateLimiter:
    """
    Helper class for checking rate limits at API endpoints.
    
    Can be used in view methods to enforce custom rate limits.
    """
    
    @staticmethod
    def check_endpoint(endpoint_name, identifier, max_requests=100, window_seconds=60):
        """
        Check if an endpoint can be accessed based on rate limit.
        
        Args:
            endpoint_name: Name of the endpoint
            identifier: Unique identifier (user_id, IP, account_id, etc.)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            Tuple: (allowed: bool, remaining: int, reset_time: int)
        """
        allowed, remaining, reset_time = check_rate_limit(
            identifier=f"{endpoint_name}:{identifier}",
            rate_type='endpoint',
            max_requests=max_requests,
            window_seconds=window_seconds
        )
        
        return allowed, remaining, reset_time
