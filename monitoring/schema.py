"""
OpenAPI Schema customization for drf-spectacular.
"""
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from rest_framework import serializers


def preprocessing_filter_hook(endpoints, **kwargs):
    """
    Preprocessing hook to customize the OpenAPI schema generation.
    This can be used to add custom parameters, tags, and descriptions.
    """
    filtered_endpoints = []
    
    for path, path_regex, method, view in endpoints:
        # Add custom tags to endpoints
        if 'transaction' in path.lower():
            view.tags = ['Transactions']
        elif 'rule' in path.lower():
            view.tags = ['Rules']
        elif 'alert' in path.lower():
            view.tags = ['Alerts']
        
        filtered_endpoints.append((path, path_regex, method, view))
    
    return filtered_endpoints
