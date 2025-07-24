"""
MCPW wrapper for FastMCP services.

This module provides a wrapper around FastMCP that allows services to register
resources with relative paths (e.g., "/inbox") that get transformed to full
URIs (e.g., "mcpweb://email/inbox") when mounted by the router.

The MCPW pattern simplifies service development by:
- Allowing services to use simple relative paths
- Automatically handling protocol and service name prefixing
- Providing a clean separation between service logic and routing
"""

from typing import Any, Callable, List

from fastmcp import FastMCP

from .types import ResourceInfo


class MCPWService:
    """
    Wrapper around FastMCP that stores resource paths for later transformation.
    
    This allows services to register resources with relative paths that will be
    transformed to full URIs when the service is mounted by the router.
    
    Example:
        >>> service = MCPWService("Email Service", instructions="...")
        >>> 
        >>> @service.resource("/inbox")
        >>> async def get_inbox():
        >>>     return {"messages": [...]}
        >>>
        >>> # When mounted as "email", this becomes mcpweb://email/inbox
    """
    
    def __init__(self, name: str, instructions: str = "", **kwargs: Any) -> None:
        """
        Initialize MCPW service wrapper.
        
        Args:
            name: Service name (e.g., "Email Service")
            instructions: Service description and usage instructions
            **kwargs: Additional arguments passed to FastMCP
        """
        self.name = name
        self.instructions = instructions
        self.mcp = FastMCP(name, instructions=instructions, **kwargs)
        self.resource_paths: List[ResourceInfo] = []
    
    def resource(self, path: str) -> Callable:
        """
        Decorator to register a resource with a relative path.
        
        The path should start with "/" and can include parameters in curly braces.
        
        Args:
            path: Relative path for the resource (e.g., "/inbox", "/thread/{id}")
            
        Returns:
            Decorator function that registers the resource
            
        Example:
            >>> @service.resource("/thread/{thread_id}")
            >>> async def get_thread(thread_id: str):
            >>>     return {"id": thread_id, ...}
        """
        # Validate path format
        if not path.startswith("/"):
            raise ValueError(f"Resource path must start with '/': {path}")
            
        def decorator(func: Callable) -> Callable:
            # Store the resource info for later transformation
            resource_info: ResourceInfo = {
                "path": path,
                "func": func,
                "name": func.__name__
            }
            self.resource_paths.append(resource_info)
            
            # Return the original function (not registered with FastMCP yet)
            return func
            
        return decorator
    
    def tool(self, *args: Any, **kwargs: Any) -> Callable:
        """
        Pass-through to FastMCP's tool decorator.
        
        This allows services to register tools (like search_resources and invoke_action)
        using the standard FastMCP decorator.
        
        Example:
            >>> @service.tool
            >>> async def search_resources(query: str) -> List[str]:
            >>>     return ["/thread/123", "/thread/456"]
        """
        return self.mcp.tool(*args, **kwargs)
    
    def get_mcp_instance(self) -> FastMCP:
        """
        Get the underlying FastMCP instance.
        
        This is used by the router to access the service's FastMCP instance
        for tool registration and other operations.
        
        Returns:
            The wrapped FastMCP instance
        """
        return self.mcp
    
    def get_resource_paths(self) -> List[ResourceInfo]:
        """
        Get all registered resource paths.
        
        This is used by the router to transform relative paths to full URIs
        when mounting the service.
        
        Returns:
            List of resource information dictionaries
        """
        return self.resource_paths