# Gateway Server Implementation

The RESTful MCP gateway server is the core component that aggregates multiple MCP services and provides the five core operations (LIST, VIEW, GET, FIND, POST) as a unified interface. The gateway enables scaling to hundreds of services by providing a consistent interface to all services.

## What the Gateway Does

The gateway server acts as an intermediary that:
1. **Resolves URIs** - Maps `mcpweb://` URIs to actual service endpoints
2. **Connects to services** - Manages connections to remote MCP services
3. **Provides the five operations** - Uniform interface (LIST, VIEW, GET, FIND, POST)
4. **Routes requests** - Directs requests to appropriate services
5. **Maintains service isolation** - Each service is independent

## Gateway Architecture

### Two-Part Design

The gateway uses a resolver + adapter architecture:

1. **URL Resolver**: Maps `mcpweb://service/path` to service endpoints
2. **Protocol Adapters**: Handle communication with different service types

### Service Resolution

When a request comes in:
```
mcpweb://email/thread/123
         ↓
Resolver extracts:
  - Service: "email" 
  - Path: "/thread/123"
         ↓
Lookup configuration:
  - Endpoint: "http://email-service:3001/mcp"
  - Protocol: "mcp"
         ↓
Adapter handles request
```

## Gateway Configuration

### Current Implementation

The gateway currently supports MCP protocol services:

```json
{
  "services": {
    "email": {
      "endpoint": "http://email-service:3001/mcp",
      "protocol": "mcp"
    },
    "calendar": {
      "endpoint": "http://calendar-service:3002/mcp",
      "protocol": "mcp"
    }
  }
}
```

### Future Protocol Support

The architecture is designed to support additional protocols:

```json
{
  "services": {
    // REST API (future)
    "legacy-api": {
      "endpoint": "https://api.example.com/v1",
      "protocol": "rest"
    },
    // Another gateway (future)
    "remote-docs": {
      "endpoint": "https://docs-gateway.partner.com",
      "protocol": "gateway"
    },
    // A2A Protocol (future)
    "assistant": {
      "endpoint": "wss://assistant.example.com/a2a",
      "protocol": "a2a"
    }
  }
}
```

These additional protocols are not yet implemented but demonstrate the extensibility of the architecture.

## The Five Operations

### 1. LIST - Service Discovery

```python
@gateway.tool
async def LIST() -> list[str]:
    """List all available services"""
    return list(configured_services.keys())
```

Example:
```
LIST
→ ["email", "calendar", "documents", "tasks", "contacts"]
```

### 2. VIEW - Service Information

```python
@gateway.tool  
async def VIEW(service: str) -> dict:
    """Get information about a specific service"""
    if service not in configured_services:
        return {"error": f"Service '{service}' not found"}
    
    # Get service connection
    connection = get_service_connection(service)
    
    # Return service instructions and capabilities
    return {
        "name": service,
        "description": connection.instructions,
        "resources": list_service_resources(service),
        "find": "Supported" if has_search_tool(service) else "Not supported"
    }
```

Example:
```
VIEW email
→ {
    "name": "email",
    "description": "Email service with thread-based messaging...",
    "resources": [
        "mcpweb://email/inbox",
        "mcpweb://email/thread/{id}",
        "mcpweb://email/thread/{id}/reply"
    ],
    "find": "Supported"
}
```

### 3. GET - Resource Retrieval

GET is special—it uses MCP's native resource system rather than tools:

```python
# Gateway registers resources with full URIs
@gateway.resource("mcpweb://email/inbox")
async def get_email_inbox():
    # Forward to email service
    email_service = get_service_connection("email")
    return await email_service.get_resource("/inbox")
```

The gateway:
1. Receives resource requests with full URIs
2. Parses the service name from the URI
3. Forwards the request to the appropriate service
4. Returns the response unchanged

### 4. FIND - Resource Discovery

```python
@gateway.tool
async def FIND(service: str, query: str) -> list[str]:
    """Find resources within a specific service"""
    if service not in configured_services:
        return {"error": f"Service '{service}' not found"}
    
    # Get service connection
    connection = get_service_connection(service)
    
    # Call the service's search tool
    paths = await connection.call_tool("search", {"query": query})
    
    # Transform paths to full URIs
    return [f"mcpweb://{service}{path}" for path in paths]
```

Example:
```
FIND email "budget proposal"
→ [
    "mcpweb://email/thread/thread_042",
    "mcpweb://email/thread/thread_156"
]
```

### 5. POST - Action Execution

```python
@gateway.tool
async def POST(uri: str, ctx: Context) -> any:
    """Post to an action resource"""
    # Parse URI to get service and path
    service, path = parse_mcpweb_uri(uri)
    
    if service not in configured_services:
        return {"error": f"Service '{service}' not found"}
    
    # Get service connection
    connection = get_service_connection(service)
    
    # Forward to action resource, preserving context for prompts
    return await connection.get_resource(path, ctx)
```

Example:
```
POST mcpweb://email/thread/thread_001/reply
→ [Triggers prompt in email service]
→ {"status": "sent", "message_id": "msg_789"}
```

## URI Transformation

The gateway handles URI transformation between relative paths and full URIs:

### Service → Gateway
- Service registers: `/inbox`
- Gateway transforms to: `mcpweb://email/inbox`

### Client → Gateway → Service  
- Client requests: `mcpweb://email/thread/123`
- Gateway extracts: service=`email`, path=`/thread/123`
- Forwards to service: `/thread/123`

## Implementation Architecture

### Resolver Component

The resolver maps URIs to service endpoints:

```python
class ServiceResolver:
    def __init__(self, config):
        self.services = config["services"]
    
    def resolve(self, uri: str) -> dict:
        """Resolve mcpweb:// URI to service endpoint"""
        if not uri.startswith("mcpweb://"):
            raise ValueError(f"Invalid URI: {uri}")
        
        # Extract service and path
        parts = uri[9:].split("/", 1)
        service = parts[0]
        path = "/" + parts[1] if len(parts) > 1 else "/"
        
        if service not in self.services:
            raise ValueError(f"Unknown service: {service}")
        
        config = self.services[service]
        return {
            "service": service,
            "endpoint": config["endpoint"],
            "protocol": config["protocol"],
            "path": path
        }
```

### Protocol Adapters

Adapters handle protocol-specific communication:

```python
class MCPAdapter:
    """Adapter for MCP protocol services"""
    
    async def list(self) -> list[str]:
        # MCP services don't have a list operation
        # Return empty or use service registry
        return []
    
    async def view(self, endpoint: str) -> dict:
        # Connect and get service info
        async with MCPClient(endpoint) as client:
            return {
                "description": client.instructions,
                "resources": client.list_resources()
            }
    
    async def get(self, endpoint: str, path: str, ctx: Context):
        # Forward resource request
        async with MCPClient(endpoint) as client:
            return await client.get_resource(path, ctx)
    
    async def find(self, endpoint: str, query: str) -> list[str]:
        # Call search tool
        async with MCPClient(endpoint) as client:
            return await client.call_tool("search", {"query": query})
    
    async def post(self, endpoint: str, path: str, ctx: Context):
        # Forward to action resource
        async with MCPClient(endpoint) as client:
            return await client.get_resource(path, ctx)
```

### Gateway Implementation

```python
class RestfulMcpGateway:
    def __init__(self, config):
        self.resolver = ServiceResolver(config)
        self.adapters = {
            "mcp": MCPAdapter()
            # Future: "rest": RESTAdapter()
            # Future: "gateway": GatewayAdapter()
        }
        self._register_operations()
    
    async def get_resource(self, uri: str, ctx: Context):
        # Resolve URI
        resolution = self.resolver.resolve(uri)
        
        # Get appropriate adapter
        adapter = self.adapters[resolution["protocol"]]
        
        # Forward request
        return await adapter.get(
            resolution["endpoint"],
            resolution["path"],
            ctx
        )
```

## Service Registration

Services are registered in the gateway configuration:

```json
{
  "services": {
    "newservice": {
      "endpoint": "http://newservice:3004/mcp",
      "protocol": "mcp"
    }
  }
}
```

The gateway will:
1. Add the service to its resolver
2. Route `mcpweb://newservice/*` requests to the endpoint
3. Use the MCP adapter for communication

## Error Handling

The gateway should handle common errors gracefully:

```python
@gateway.tool
async def FIND(service: str, query: str) -> list[str]:
    """Find with error handling"""
    if service not in self.services:
        return {"error": f"Service '{service}' not found",
                "available": list(self.services.keys())}
    
    try:
        async with self._connect(service) as conn:
            paths = await conn.call_tool("search", {"query": query})
            return [f"mcpweb://{service}{path}" for path in paths]
    except ConnectionError:
        return {"error": f"Service '{service}' is unavailable"}
    except ToolNotFoundError:
        return {"error": f"Service '{service}' doesn't support find"}
```

## Performance Considerations

### Connection Pooling
```python
class RestfulMcpGateway:
    def __init__(self, config):
        self.connection_pool = {}
    
    async def _get_connection(self, service: str):
        if service not in self.connection_pool:
            self.connection_pool[service] = MCPClient(
                self.services[service]["url"],
                keepalive=True
            )
        return self.connection_pool[service]
```

### Caching
```python
@cache(ttl=60)  # Cache for 1 minute
async def VIEW(service: str) -> dict:
    """Cached service information"""
    # VIEW results rarely change
    ...

# Don't cache FIND or GET - they need fresh data
```

### Parallel Operations
```python
async def find_all_services(query: str) -> dict:
    """Find resources across all services in parallel"""
    tasks = []
    for service in self.services:
        task = asyncio.create_task(
            FIND(service, query)
        )
        tasks.append((service, task))
    
    results = {}
    for service, task in tasks:
        try:
            results[service] = await task
        except Exception as e:
            results[service] = {"error": str(e)}
    
    return results
```

## Security Considerations

1. **Service Isolation**: Each service connection is independent
2. **URI Validation**: Validate URIs before routing
3. **Access Control**: Can implement per-service permissions
4. **Rate Limiting**: Prevent service overload

```python
@rate_limit(requests_per_minute=100)
async def FIND(service: str, query: str) -> list[str]:
    ...
```

## Deployment Options

### 1. Standalone Process
```bash
# Run gateway as separate process
python gateway.py --config services.json --port 8000
```

### 2. Embedded in Application
```python
# Include gateway in your application
gateway = RestfulMcpGateway(config)
app.include_gateway(gateway)
```

### 3. Cloud Function
```python
# Deploy as serverless function
def handler(event, context):
    gateway = RestfulMcpGateway(load_config())
    return gateway.handle_request(event)
```

## Monitoring and Observability

```python
@instrument
async def FIND(service: str, query: str) -> list[str]:
    """Instrumented find with metrics"""
    with timer(f"find.{service}"):
        results = await _find_service(service, query)
    
    metrics.increment(f"find.{service}.count")
    metrics.gauge(f"find.{service}.results", len(results))
    
    return results
```

## Benefits of Using a Gateway

1. **Single Connection Point**: Clients connect to one service instead of many
2. **Service Discovery**: LIST and VIEW provide dynamic discovery
3. **URI Resolution**: Abstract service locations behind `mcpweb://` URIs
4. **Protocol Flexibility**: Support different protocols with same interface
5. **Failure Isolation**: One service failure doesn't affect others
6. **Evolution**: Services can change endpoints without affecting clients
7. **Future Extensibility**: Add REST, A2A, or gateway protocols later

## Future Extensions

### Remote Gateway Support

Route requests to other gateways:
```json
{
  "services": {
    "partner-docs": {
      "endpoint": "https://partner-gateway.com",
      "protocol": "gateway"
    }
  }
}
```

This enables:
- Federation across organizations
- Geographic distribution
- Service marketplace integration

### REST API Support

Map REST APIs to the five operations:
```json
{
  "services": {
    "legacy-api": {
      "endpoint": "https://api.example.com/v1",
      "protocol": "rest",
      "mapping": {
        "LIST": "GET /services",
        "FIND": "GET /search?q={query}"
      }
    }
  }
}
```

The gateway is designed for extensibility while maintaining a simple, consistent interface for clients.