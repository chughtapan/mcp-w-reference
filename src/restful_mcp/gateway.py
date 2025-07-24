"""
FastMCP Gateway Server implementation.

This gateway server provides the five core operations (LIST, VIEW, GET, FIND, POST)
and aggregates multiple MCP services into a unified interface.

Architecture:
- Services register resources with relative paths (e.g., "/inbox")
- Gateway transforms them to full URIs (e.g., "mcpweb://email/inbox")
- Standard tools are auto-generated from service metadata
- Supports both MCPW pattern services and legacy proxy services
"""

import importlib
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from fastmcp import Client, Context, FastMCP
from fastmcp.server.proxy import ProxyClient
from mcp.shared.exceptions import McpError

from .config import PROTOCOL
from .constants import (
    ERROR_INVALID_URI,
    ERROR_SERVICE_NOT_FOUND,
    ERROR_SERVICE_NOT_VALIDATED,
    ERROR_TOOL_NOT_IMPLEMENTED,
    SERVICE_TYPE_LEGACY,
    SERVICE_TYPE_MCPW,
    SERVICE_TYPE_PROXY,
    URI_SEPARATOR,
)
from .mcpw import MCPWService
from .types import (
    ClientFactory,
    ListResourcesResponse,
    ListServicesResponse,
    ResourceURI,
    ServiceInfo,
    ServiceName,
)

logger = logging.getLogger(__name__)


class GatewayContext:
    """
    Enhanced context that provides cross-service communication capabilities.
    
    Wraps the standard FastMCP Context to add gateway-specific operations,
    allowing services to interact with each other through the gateway.
    """
    
    def __init__(self, ctx: Context, gateway: "FastMCPGateway") -> None:
        """
        Initialize the gateway context.
        
        Args:
            ctx: The original FastMCP context
            gateway: Reference to the gateway for routing requests
        """
        self._ctx = ctx
        self._gateway = gateway
    
    # Delegate standard context methods
    async def read_resource(self, uri: str) -> Any:
        """
        Read any resource - local or cross-service.
        
        For mcpweb:// URIs, routes through the gateway.
        For relative URIs, uses the standard context.
        
        Args:
            uri: Resource URI (relative or absolute)
            
        Returns:
            Resource content
        """
        if uri.startswith(f"{PROTOCOL}{URI_SEPARATOR}"):
            # Route through gateway for cross-service resources
            return await self._gateway.get_resource(uri, self._ctx)
        # Local resource access
        return await self._ctx.read_resource(uri)
    
    async def request(self, operation: str, uri: str, query: Optional[str] = None) -> Any:
        """
        Make a request to any service through the gateway.
        
        Args:
            operation: One of LIST, VIEW, GET, FIND, POST
            uri: Target URI (e.g., "mcpweb://calendar", "mcpweb://email/thread/123")
            query: Query string for FIND operations only
            
        Returns:
            Operation result
            
        Examples:
            # List all services
            await ctx.request("LIST", "mcpweb://")
            
            # View a service
            await ctx.request("VIEW", "mcpweb://calendar")
            
            # Find resources
            await ctx.request("FIND", "mcpweb://email", "budget")
            
            # Get specific resource
            await ctx.request("GET", "mcpweb://email/thread/123")
            
            # Post to action resource (triggers prompts)
            await ctx.request("POST", "mcpweb://email/thread/123/reply")
        """
        # Extract service from URI
        if uri == f"{PROTOCOL}{URI_SEPARATOR}":
            service_name = None
        else:
            service_name = self._gateway._extract_service_from_uri(uri)
        
        if operation == "LIST":
            result = await self._gateway.list_services()
            return result.get("services", [])
        
        elif operation == "VIEW":
            if not service_name:
                raise ValueError("VIEW operation requires a service URI")
            result = await self._gateway.view_service(service_name)
            return result
        
        elif operation == "GET":
            return await self._gateway.get_resource(uri, self._ctx)
        
        elif operation == "FIND":
            if not query:
                raise ValueError("FIND operation requires a query")
            # Ensure URI ends with / for search_resources
            if not uri.endswith("/"):
                uri = uri + "/"
            return await self._gateway.search_resources(uri, query)
        
        elif operation == "POST":
            # Extract action from URI (last part after /)
            parts = uri.rstrip("/").split("/")
            if len(parts) < 2:
                raise ValueError("POST requires an action resource URI")
            
            # For now, we'll need to enhance invoke_action to work with URIs
            # This is a simplified version
            return {"status": "triggered", "uri": uri, "message": "Action triggered via gateway context"}
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    # Delegate other context methods
    async def set_state_value(self, key: str, value: Any) -> None:
        """Store a value in the request state."""
        return await self._ctx.set_state_value(key, value)
    
    async def get_state_value(self, key: str) -> Any:
        """Retrieve a value from the request state."""
        return await self._ctx.get_state_value(key)
    
    async def info(self, message: str) -> None:
        """Send an info message to the client."""
        return await self._ctx.info(message)
    
    async def prompt(self, message: str, schema: Any) -> Any:
        """Prompt the user for input."""
        return await self._ctx.prompt(message, schema)
    
    @property
    def fastmcp(self) -> Any:
        """Access the underlying FastMCP instance."""
        return self._ctx.fastmcp


class FastMCPGateway(FastMCP[Any]):
    """
    Gateway server that provides the five core operations and handles service aggregation.
    
    The gateway acts as a proxy, forwarding requests to mounted services while
    providing a consistent interface. It supports:
    - MCPW pattern services with automatic resource prefixing
    - Legacy FastMCP services
    - Proxy services configured via JSON
    """
    
    def __init__(self, config: Dict[str, Any], *args: Any, **kwargs: Any) -> None:
        """
        Initialize the router.
        
        Args:
            config: MCP configuration dictionary with mcpServers
            *args: Additional arguments for FastMCP
            **kwargs: Additional keyword arguments for FastMCP
        """
        super().__init__(*args, **kwargs)
        
        # Service registries
        self.client_factories: Dict[ServiceName, ClientFactory] = {}
        self.service_instances: Dict[ServiceName, Any] = {}
        self.service_resources: Dict[ServiceName, List[ResourceURI]] = {}
        self.mounted_services: Dict[ServiceName, MCPWService] = {}
        
        # Initialize router
        self._load_config(config)
        self._register_routing_tools()
    
    # ==================== Configuration ====================
    
    def _load_config(self, config: Dict[str, Any]) -> None:
        """Load proxy service configuration from JSON."""
        mcp_servers = config.get("mcpServers", {})
        
        for service_name, service_config in mcp_servers.items():
            self.client_factories[service_name] = self._create_client_factory(
                service_name, service_config
            )
            logger.info(f"Registered proxy service '{service_name}'")
    
    def _create_client_factory(
        self, name: str, config: Dict[str, Any]
    ) -> ClientFactory:
        """Create a client factory for a proxy service."""
        def factory() -> Client[Any]:
            return ProxyClient({"mcpServers": {name: config}})
        return factory
    
    # ==================== Service Mounting ====================
    
    def mount_service(
        self, service_name: ServiceName, service: Union[MCPWService, FastMCP]
    ) -> None:
        """
        Mount a service with automatic resource prefixing.
        
        For MCPW services, this will:
        1. Extract all resources with relative paths
        2. Transform them to full URIs with protocol and service prefix
        3. Register them with the router
        
        Args:
            service_name: Name to mount the service under
            service: MCPWService or FastMCP instance
            
        Example:
            >>> router.mount_service("email", email_service)
            # Transforms /inbox -> mcpweb://email/inbox
        """
        if isinstance(service, MCPWService):
            self._mount_mcpw_service(service_name, service)
        else:
            self._mount_legacy_service(service_name, service)
    
    def _mount_mcpw_service(self, service_name: ServiceName, service: MCPWService) -> None:
        """Mount an MCPW pattern service."""
        mcp_instance = service.get_mcp_instance()
        self.service_instances[service_name] = mcp_instance
        self.service_resources[service_name] = []
        self.mounted_services[service_name] = service
        
        # Register all resources with proper prefixing
        for resource_info in service.get_resource_paths():
            path = resource_info["path"]
            func = resource_info["func"]
            
            # Ensure path starts with /
            if not path.startswith("/"):
                path = "/" + path
                
            # Transform to full URI: /inbox -> mcpweb://email/inbox
            full_uri = f"{PROTOCOL}{URI_SEPARATOR}{service_name}{path}"
            
            # Register with router
            self.resource(full_uri)(func)
            self.service_resources[service_name].append(full_uri)
            
            logger.info(f"Mounted resource: {full_uri}")
    
    def _mount_legacy_service(self, service_name: ServiceName, service: FastMCP) -> None:
        """Mount a legacy FastMCP service."""
        self.service_instances[service_name] = service
        logger.info(f"Mounted legacy service '{service_name}'")
    
    # ==================== URI Parsing ====================
    
    def _extract_service_from_uri(self, uri: ResourceURI) -> ServiceName:
        """
        Extract service name from a resource URI.
        
        Args:
            uri: Resource URI (e.g., "mcpweb://email/inbox")
            
        Returns:
            Service name (e.g., "email")
            
        Raises:
            ValueError: If URI format is invalid
        """
        if uri.startswith(f"{PROTOCOL}{URI_SEPARATOR}"):
            # Parse mcpweb://service/path format
            remainder = uri[len(f"{PROTOCOL}{URI_SEPARATOR}"):]
            parts = remainder.split("/", 1)
            return parts[0]
        elif URI_SEPARATOR in uri:
            # Try other protocol formats for backward compatibility
            return uri.split(URI_SEPARATOR)[0]
        else:
            raise ValueError(ERROR_INVALID_URI.format(uri=uri))
    
    def _extract_service_from_path(self, path: str) -> ServiceName:
        """
        Extract service name from a path.
        
        Supports formats:
        - "email/" -> "email"
        - "mcpweb://email/" -> "email"
        
        Args:
            path: Service path
            
        Returns:
            Service name
        """
        if path.startswith(f"{PROTOCOL}{URI_SEPARATOR}"):
            return self._extract_service_from_uri(path.rstrip("/"))
        return path.rstrip("/")
    
    def _transform_to_full_uri(self, path: str, service_name: ServiceName) -> ResourceURI:
        """Transform a relative path to a full URI."""
        if path.startswith("/"):
            return f"{PROTOCOL}{URI_SEPARATOR}{service_name}{path}"
        elif path.startswith(f"{PROTOCOL}{URI_SEPARATOR}"):
            return path
        else:
            return f"{PROTOCOL}{URI_SEPARATOR}{service_name}/{path}"
    
    # ==================== Service Communication ====================
    
    async def _call_service_tool(
        self, service_name: ServiceName, tool_name: str, params: Dict[str, Any]
    ) -> Any:
        """Route a tool call to a proxy service."""
        if service_name not in self.client_factories:
            available = ", ".join(self.client_factories.keys())
            raise ValueError(
                ERROR_SERVICE_NOT_FOUND.format(
                    service_name=service_name, available=available
                )
            )
        
        try:
            client = self.client_factories[service_name]()
            async with client:
                return await client.call_tool(tool_name, params)
        except McpError as e:
            raise RuntimeError(
                f"Error calling {tool_name} on service '{service_name}': {str(e)}"
            )
    
    async def _call_mounted_service_tool(
        self, service_name: ServiceName, tool_name: str, **kwargs: Any
    ) -> Any:
        """Call a tool on a mounted MCPW service."""
        module_name = self.mounted_services[service_name].__module__
        module = importlib.import_module(module_name)
        
        tool = getattr(module, tool_name, None)
        if tool and hasattr(tool, 'fn'):
            # Check if there's a context in kwargs and wrap it
            if 'ctx' in kwargs and kwargs['ctx'] is not None:
                # Replace with gateway context
                kwargs['ctx'] = GatewayContext(kwargs['ctx'], self)
            
            return await tool.fn(**kwargs)
        else:
            raise ValueError(
                ERROR_TOOL_NOT_IMPLEMENTED.format(
                    service_name=service_name, tool_name=tool_name
                )
            )
    
    # ==================== Auto-Generated Tools ====================
    
    def _register_routing_tools(self) -> None:
        """Register the auto-generated routing tools."""
        
        @self.tool(name="list_services")
        async def list_services() -> ListServicesResponse:
            """
            List all available services in the router.
            
            Returns:
                Dictionary with service information including names, types, and resource counts
                
            Example:
                >>> await list_services()
                {
                    "services": [
                        {"name": "email", "type": "mcpw", "resources": 2},
                        {"name": "calendar", "type": "proxy"}
                    ],
                    "total": 2
                }
            """
            services_info: List[ServiceInfo] = []
            
            # Add mounted services
            for name in self.service_instances.keys():
                if name in self.mounted_services:
                    service_type = SERVICE_TYPE_MCPW
                else:
                    service_type = SERVICE_TYPE_LEGACY
                    
                services_info.append({
                    "name": name,
                    "type": service_type,
                    "resources": len(self.service_resources.get(name, []))
                })
            
            # Add proxy services
            for name in self.client_factories.keys():
                if name not in self.service_instances:
                    services_info.append({
                        "name": name,
                        "type": SERVICE_TYPE_PROXY,
                        "resources": 0
                    })
            
            return {"services": services_info, "total": len(services_info)}
        
        @self.tool(name="list_resources")
        async def list_resources(service_name: ServiceName) -> ListResourcesResponse:
            """
            Get service capabilities and available resources.
            
            For MCPW services, returns the service instructions and mounted resources.
            For proxy services, forwards the request.
            
            Args:
                service_name: Name of the service
                
            Returns:
                Service instructions and available resources
                
            Example:
                >>> await list_resources("email")
                {
                    "service": "email",
                    "instructions": "Email service for...",
                    "resources": ["mcpweb://email/inbox", "mcpweb://email/thread/{id}"]
                }
            """
            # Handle MCPW mounted services
            if service_name in self.mounted_services:
                service = self.mounted_services[service_name]
                return {
                    "service": service_name,
                    "instructions": service.instructions,
                    "resources": self.service_resources.get(service_name, [])
                }
            
            # Handle legacy mounted services
            elif service_name in self.service_instances:
                service = self.service_instances[service_name]
                return {
                    "service": service_name,
                    "instructions": getattr(service, 'instructions', f"Service '{service_name}'"),
                    "resources": self.service_resources.get(service_name, [])
                }
            
            # Handle proxy services
            else:
                try:
                    return await self._call_service_tool(service_name, "list_resources", {})
                except:
                    return {
                        "service": service_name,
                        "instructions": f"Service '{service_name}' (proxied)",
                        "resources": []
                    }
        
        @self.tool(name="get_resource")
        async def get_resource(resource_uri: ResourceURI, ctx: Optional[Context] = None) -> Any:
            """
            Retrieve a resource by its full URI.
            
            The service is automatically determined from the URI.
            For MCPW resources, they should be accessed directly via MCP's resource system.
            
            Args:
                resource_uri: Full resource URI (e.g., "mcpweb://email/inbox")
                ctx: Optional context for resource access
                
            Returns:
                Resource data
                
            Example:
                >>> await get_resource("mcpweb://email/inbox")
                {"inbox": {"total_threads": 2, "threads": [...]}}
            """
            # For MCPW resources, try direct access first
            if resource_uri.startswith(f"{PROTOCOL}{URI_SEPARATOR}"):
                if ctx:
                    try:
                        contents = await ctx.read_resource(resource_uri)
                        if contents and len(contents) > 0:
                            first_content = contents[0]
                            if hasattr(first_content, "content"):
                                return first_content.content
                            elif hasattr(first_content, "text"):
                                return first_content.text
                            else:
                                return str(first_content)
                    except Exception as e:
                        logger.debug(f"Direct resource access failed: {e}")
                
                # Extract service and forward to proxy if needed
                service_name = self._extract_service_from_uri(resource_uri)
                if service_name in self.client_factories and service_name not in self.mounted_services:
                    return await self._call_service_tool(
                        service_name, "get_resource", {"resource_uri": resource_uri}
                    )
                else:
                    raise ValueError(
                        f"Resource {resource_uri} should be accessed directly via MCP resource system"
                    )
            else:
                # Legacy format - forward to proxy
                service_name = self._extract_service_from_uri(resource_uri)
                return await self._call_service_tool(
                    service_name, "get_resource", {"resource_uri": resource_uri}
                )
        
        @self.tool(name="search_resources")
        async def search_resources(path: str, query: str) -> List[ResourceURI]:
            """
            Search for resources within a service.
            
            Args:
                path: Service path - either "service/" or "mcpweb://service/"
                query: Search query string
                
            Returns:
                List of matching resource URIs with full protocol
                
            Example:
                >>> await search_resources("email/", "budget")
                ["mcpweb://email/thread/thread_002"]
                
                >>> await search_resources("mcpweb://calendar/", "standup")
                ["mcpweb://calendar/event/evt_001"]
            """
            service_name = self._extract_service_from_path(path)
            
            # Handle MCPW mounted services
            if service_name in self.mounted_services:
                results = await self._call_mounted_service_tool(
                    service_name, "search_resources", query=query
                )
                
                # Transform results to full URIs
                full_results = []
                for result in results:
                    full_results.append(self._transform_to_full_uri(result, service_name))
                return full_results
            
            # Handle proxy services
            else:
                return await self._call_service_tool(
                    service_name, "search_resources", {"query": query}
                )
        
        @self.tool(name="invoke_action")
        async def invoke_action(
            action: str, resource_id: ResourceURI, ctx: Context
        ) -> Any:
            """
            Perform an action on a resource.
            
            The service is automatically determined from the resource URI.
            
            Args:
                action: Action to perform (e.g., "reply_thread", "create_event")
                resource_id: Full resource URI (e.g., "mcpweb://email/thread/123")
                ctx: MCP context for user interaction/elicitation
                
            Returns:
                Action result
                
            Example:
                >>> await invoke_action("reply_thread", "mcpweb://email/thread/001", ctx)
                {"status": "sent", "recipients": [...], ...}
            """
            service_name = self._extract_service_from_uri(resource_id)
            
            # Handle MCPW mounted services
            if service_name in self.mounted_services:
                return await self._call_mounted_service_tool(
                    service_name, "invoke_action",
                    action=action, resource_id=resource_id, ctx=ctx
                )
            
            # Handle proxy services
            else:
                return await self._call_service_tool(
                    service_name, "invoke_action",
                    {"action": action, "resource_id": resource_id}
                )
    
    # ==================== Properties ====================
    
    @property
    def services(self) -> List[ServiceName]:
        """Get list of all service names (mounted and proxy)."""
        all_services = set(self.service_instances.keys())
        all_services.update(self.client_factories.keys())
        return list(all_services)


# ==================== Main Entry Point ====================

def main() -> None:
    """
    Main entry point for running the router standalone.
    
    Looks for server.config.json in multiple locations and starts the router.
    """
    # Configuration file search paths
    possible_paths = [
        Path.cwd() / "server.config.json",
        Path.home() / ".mcpweb" / "server.config.json",
        Path("/etc/mcpweb/server.config.json"),
    ]
    
    # Check project root if running from package
    try:
        package_root = Path(__file__).parent.parent.parent
        project_config = package_root / "server.config.json"
        if project_config.exists():
            possible_paths.insert(0, project_config)
    except:
        pass
    
    # Find configuration file
    config_path = None
    for path in possible_paths:
        if path.exists():
            config_path = path
            break
    
    # Load configuration or use empty
    if config_path is None:
        print(
            "Warning: No server.config.json found. Starting router with no backend services."
        )
        print("Searched in:", [str(p) for p in possible_paths])
        config: Dict[str, Any] = {"mcpServers": {}}
    else:
        print(f"Loading configuration from: {config_path}")
        with open(config_path) as f:
            config = json.load(f)
    
    # Create and run gateway
    gateway = FastMCPGateway(
        config,
        name="McpWeb Gateway",
        instructions=(
            "Gateway server providing five core operations (LIST, VIEW, GET, FIND, POST) "
            "for aggregating MCP services with automatic resource prefixing."
        ),
    )
    gateway.run()


if __name__ == "__main__":
    main()