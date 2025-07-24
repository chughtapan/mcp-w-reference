"""
Constants used throughout the McpWeb implementation.

This module defines constant values for protocols, error messages, tool names,
and service types used across the McpWeb framework.
"""

# Protocol configuration
DEFAULT_PROTOCOL = "mcpweb"

# URI patterns
URI_SEPARATOR = "://"
PATH_SEPARATOR = "/"

# Error messages
ERROR_SERVICE_NOT_FOUND = "Service '{service_name}' not found. Available services: {available}"
ERROR_SERVICE_NOT_VALIDATED = "Service '{service_name}' failed validation and is not available"
ERROR_INVALID_URI = "Invalid URI format: {uri}"
ERROR_RESOURCE_NOT_FOUND = "Resource not found: {uri}"
ERROR_TOOL_NOT_IMPLEMENTED = "Service '{service_name}' does not implement {tool_name}"
ERROR_UNKNOWN_ACTION = "Unknown action: {action}"

# Tool names
TOOL_LIST_SERVICES = "list_services"
TOOL_LIST_RESOURCES = "list_resources"
TOOL_GET_RESOURCE = "get_resource"
TOOL_SEARCH_RESOURCES = "search_resources"
TOOL_INVOKE_ACTION = "invoke_action"

# Service types
SERVICE_TYPE_MCPW = "mcpw"
SERVICE_TYPE_LEGACY = "legacy"
SERVICE_TYPE_PROXY = "proxy"