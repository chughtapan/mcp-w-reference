# Architecture Overview

## System Architecture

RESTful MCP uses a gateway-based architecture where all communication flows through a central gateway server:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Gateway   │────▶│  Services   │
│ (LLM Agent) │     │   Server    │     │(MCP Servers)│
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           │ Service-to-Service
                           ▼
                    ┌─────────────┐
                    │  Services   │
                    │(MCP Servers)│
                    └─────────────┘
```

1. **Client**: Any LLM agent that connects to the gateway
2. **Gateway Server**: Central server that provides the five operations and routes requests
3. **Services**: Standard MCP servers following the RESTful MCP pattern (resources + search)

### Key Architecture Features

- **All communication goes through the gateway** - no direct client-to-service connections
- **Services can communicate with each other** through the gateway's enhanced context
- **Gateway provides the five operations** (LIST, VIEW, GET, FIND, POST) for all services
- **Services remain independent** and can be developed/deployed separately

## Service Architecture

Each RESTful MCP service is just a regular MCP server with three requirements:

### 1. Resources at Logical Endpoints
```python
# Resources are registered with the MCP server
@mcp.resource("/inbox")
async def inbox():
    return {"threads": [...]}

@mcp.resource("/thread/{thread_id}")
async def thread(thread_id: str):
    return {"id": thread_id, "messages": [...]}

# Action resources trigger prompts
@mcp.resource("/thread/{thread_id}/reply")
async def reply_action(thread_id: str, ctx: Context):
    # This is an action resource - it modifies state
    reply_data = await ctx.prompt("Reply details", ReplySchema)
    return send_reply(thread_id, reply_data)
```

### 2. Service Instructions
```python
mcp = MCP(
    name="Email Service",
    instructions="""
    Email service providing thread-based messaging.
    
    Resources:
    - /inbox: List of email threads
    - /thread/{id}: Specific thread content
    - /thread/{id}/reply: Reply to a thread
    
    Search: Full-text search across all threads
    """
)
```

### 3. Search Tool
```python
@mcp.tool
async def search(query: str) -> list[str]:
    """Search emails and return matching thread URIs"""
    results = search_database(query)
    return [f"mcpweb://email/thread/{r.id}" for r in results]
```

That's it. The service doesn't need to implement LIST, VIEW, GET, FIND, or POST—those are provided by the gateway server.

## Gateway Server Architecture

The gateway server is the central component that enables the RESTful MCP pattern at scale:

### Gateway Responsibilities

1. **Service Aggregation**: Connects to multiple MCP servers
2. **URI Resolution**: Resolves `mcpweb://` URIs to actual service endpoints
3. **Protocol Handling**: Routes requests using appropriate protocol adapters
4. **Uniform Interface**: Provides the five operations (LIST, VIEW, GET, FIND, POST)
5. **Service Isolation**: Each service is independent

### Gateway Resolution Architecture

The gateway uses a two-part architecture for maximum flexibility:

#### 1. URL Resolver
Resolves `mcpweb://service/path` URIs to actual service endpoints:

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
```

#### 2. Protocol Adapters
Handle communication with different service types:

```
Resolution Result → Protocol Adapter → Service
                          ↓
                    MCPAdapter (current)
                    RESTAdapter (future)
                    GatewayAdapter (future)
                    A2AAdapter (future)
```

### How Gateway Works

```
Client Request: GET mcpweb://email/thread/123
                    ↓
Resolver:           service="email"
                    endpoint="http://email-service:3001/mcp"
                    protocol="mcp"
                    ↓
Adapter Selection:  MCPAdapter (based on protocol)
                    ↓
Adapter forwards:   MCP.get_resource("/thread/123")
                    ↓
Service responds:   {"subject": "Meeting Notes", ...}
                    ↓
Gateway returns:    Response to client
```

### Gateway Configuration

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

### Current Implementation

The gateway currently supports:
- **MCP Protocol**: Full support for MCP servers
- **Service Resolution**: Maps service names to endpoints
- **URI Routing**: Routes based on `mcpweb://` URIs

### Future Extensions

The architecture is designed to support additional protocols:

1. **REST Protocol Adapter** (planned)
   - Map REST APIs to the five operations
   - Example: `GET /api/emails` → `LIST` operation

2. **Gateway Protocol Adapter** (planned)
   - Route to other RESTful MCP gateways
   - Enables federation and distributed architectures

3. **A2A Protocol Adapter** (planned)
   - Support for Agent-to-Agent protocol
   - Real-time agent communication

These extensions will allow the same `mcpweb://` URIs to work with any backend protocol, maintaining a consistent interface for clients.

## URI Scheme

RESTful MCP uses a consistent URI scheme for all resources:

```
mcpweb://[service]/[resource_path]
```

### URI Resolution

The `mcpweb://` scheme is a **shortcut notation** that gets resolved by the gateway:

```
mcpweb://email/thread/123
         ↓
Gateway resolves to:
http://email-service:3001/mcp/thread/123
```

This abstraction provides:
- **Protocol Independence**: Services can use any supported protocol
- **Location Transparency**: Service endpoints can change without affecting clients
- **Simplified Usage**: Shorter, cleaner URIs for clients

### Examples
- `mcpweb://email/inbox` - Email inbox
- `mcpweb://email/thread/123` - Specific email thread
- `mcpweb://email/thread/123/reply` - Reply action for thread
- `mcpweb://calendar/event/evt_456` - Calendar event
- `mcpweb://calendar/2024/01/15` - Calendar date view

### URI Components
- **Protocol**: Always `mcpweb://`
- **Service**: Service identifier (e.g., `email`, `calendar`)
- **Resource Path**: Service-specific path

### Why URIs Matter

1. **Universally Addressable**: Every piece of data has a unique address
2. **Linkable**: Resources can reference other resources
3. **Discoverable**: GET on a resource returns links to related resources
4. **Cacheable**: URIs enable client-side caching
5. **Shareable**: URIs can be saved and shared
6. **Protocol Agnostic**: Same URI works regardless of underlying protocol

## The Five Operations in Detail

### 1. LIST Implementation
```python
# Gateway implementation
@gateway.tool
async def LIST() -> list[str]:
    """List all available services"""
    return ["email", "calendar", "documents"]
```

### 2. VIEW Implementation
```python
# Gateway implementation
@gateway.tool  
async def VIEW(service: str) -> dict:
    """Get service capabilities"""
    service_connection = get_service(service)
    return {
        "name": service,
        "description": service_connection.instructions,
        "resources": service_connection.list_resources()
    }
```

### 3. GET Implementation
```python
# Uses MCP's native resource system
# Client: ctx.get_resource("mcpweb://email/thread/123")
# Gateway: Forwards to email service's resource
```

### 4. FIND Implementation
```python
# Gateway implementation
@gateway.tool
async def FIND(service: str, query: str) -> list[str]:
    """Find resources within a service"""
    service_connection = get_service(service)
    paths = await service_connection.call_tool("search", {"query": query})
    # Transform paths to full URIs
    return [f"mcpweb://{service}{path}" for path in paths]
```

### 5. POST Implementation
```python
# Gateway implementation
@gateway.tool
async def POST(uri: str, ctx: Context) -> any:
    """Post to an action resource"""
    service, path = parse_uri(uri)
    service_connection = get_service(service)
    # Forward to action resource, preserving context for prompts
    return await service_connection.get_resource(path, ctx)
```

## Service Communication

### Gateway-Enhanced Context

When services run under the gateway, they receive an enhanced context that enables cross-service communication:

```python
# Service can access other services through the gateway
@mcp.tool
async def create_event_from_email(thread_id: str, ctx: Context):
    # Read local resource
    thread = await ctx.read_resource(f"/thread/{thread_id}")
    
    # Access another service
    calendar_slots = await ctx.request("FIND", "mcpweb://calendar", "available")
    
    # Trigger action in another service
    event = await ctx.request("POST", "mcpweb://calendar/create")
    
    return {"email": thread_id, "event": event}
```

### Context Flow

```
Service A Tool Call
       ↓
Gateway wraps Context → GatewayContext
       ↓
Service A receives enhanced context
       ↓
ctx.request("GET", "mcpweb://service-b/resource")
       ↓
Gateway routes to Service B
       ↓
Service B processes request
       ↓
Response returns through Gateway to Service A
```

## Service Isolation

Each service is completely independent:

1. **Namespace Isolation**: URIs prevent naming conflicts
2. **Failure Isolation**: One service failure doesn't affect others
3. **Version Independence**: Services can evolve independently
4. **Security Boundaries**: Services can have different access controls
5. **Communication Control**: All cross-service calls go through gateway

## Scaling Considerations

### With 10 Services (Traditional MCP)
- 400+ tool definitions
- 50KB+ of context window
- High cognitive load
- Naming conflicts

### With 10 Services (RESTful MCP)
- 5 operations total
- <1KB of context window  
- Consistent mental model
- No conflicts

### With 100 Services
- Still just 5 operations
- Services discovered progressively
- Context window remains minimal
- Pattern scales linearly

## Communication Flow

### Client-to-Service Communication
All client requests flow through the gateway:

```
Client Request (LIST/VIEW/GET/FIND/POST)
            ↓
    Gateway Server
            ↓
    Route to Service
            ↓
    Service Response
            ↓
    Gateway Server
            ↓
    Client Response
```

### Service-to-Service Communication
Services can communicate with each other through the gateway context:

```
Service A (Email)                    Service B (Calendar)
      ↓                                      ↑
ctx.request("FIND",                          ↑
  "mcpweb://calendar", "meeting")            ↑
      ↓                                      ↑
Gateway routes request ─────────────────────►↑
      ↓                                      
Gateway returns results ◄────────────────────
      ↓
Service A continues
with calendar data
```

Example flow:
1. Email service receives a request with gateway context
2. Email service calls `ctx.request("POST", "mcpweb://calendar/create")`
3. Gateway routes to calendar service
4. Calendar service shows prompt to user
5. Result returns through gateway to email service

## Implementation Technologies

RESTful MCP is protocol-agnostic. You can implement it with:

- **Python**: FastMCP, mcp-python
- **JavaScript**: @modelcontextprotocol/sdk
- **Go**: go-mcp
- **Any language**: That supports MCP

The pattern is independent of implementation technology.