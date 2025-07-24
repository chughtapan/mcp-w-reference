"""
Type definitions for McpWeb implementation.

This module contains TypedDict definitions and type aliases used throughout
the McpWeb framework for type safety and better IDE support.
"""

from typing import Any, Callable, Dict, List, TypedDict, Union


class ResourceInfo(TypedDict):
    """Information about a registered resource."""
    path: str
    func: Callable
    name: str


class ServiceInfo(TypedDict):
    """Information about a mounted service."""
    name: str
    type: str
    resources: int


class ListResourcesResponse(TypedDict):
    """Response format for list_resources operation."""
    service: str
    instructions: str
    resources: List[str]


class ListServicesResponse(TypedDict):
    """Response format for list_services operation."""
    services: List[ServiceInfo]
    total: int


# Type aliases
ResourceURI = str
ServiceName = str
ResourcePath = str
ClientFactory = Callable[[], Any]