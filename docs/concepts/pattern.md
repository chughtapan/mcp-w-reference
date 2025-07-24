# The RESTful MCP Pattern

## Overview

The RESTful MCP pattern separates concerns: services simply provide resources and implement search, while a gateway server provides five uniform operations to interact with any service. This creates a scalable architecture where adding new services doesn't increase complexity for agents.

## The Five Core Capabilities

### 1. LIST - Service Discovery
**Purpose**: Discover what services are available in the system  
**Returns**: List of available service names  
**Example**:
```
LIST
→ ["email", "calendar", "documents", "tasks", "contacts"]
```

This is your entry point. When connecting to a RESTful MCP router, LIST tells you what's available.

### 2. VIEW - Service Capabilities
**Purpose**: Learn what a specific service can do  
**Returns**: Service description and available resources  
**Example**:
```
VIEW email
→ {
  "name": "email",
  "description": "Email management service with thread-based organization",
  "resources": [
    "mcpweb://email/inbox",
    "mcpweb://email/thread/{thread_id}",
    "mcpweb://email/thread/{thread_id}/reply"
  ],
  "search": "Full-text search across all email threads"
}
```

VIEW returns the service's MCP instructions field, which should describe available resources and capabilities.

### 3. GET - Resource Retrieval
**Purpose**: Retrieve a specific resource by its URI  
**Implementation**: Maps directly to MCP's resource system  
**Example**:
```
GET mcpweb://email/thread/thread_001
→ {
  "uri": "mcpweb://email/thread/thread_001",
  "subject": "Q1 Planning Meeting",
  "participants": ["alice@example.com", "bob@example.com"],
  "messages": [...],
  "actions": [
    "mcpweb://email/thread/thread_001/reply",
    "mcpweb://email/thread/thread_001/forward"
  ]
}
```

Resources include links to available actions, enabling progressive discovery.

### 4. FIND - Resource Discovery
**Purpose**: Find resources matching a query  
**Returns**: List of resource URIs  
**Example**:
```
FIND email "budget proposal"
→ [
  "mcpweb://email/thread/thread_042",
  "mcpweb://email/thread/thread_156",
  "mcpweb://email/thread/thread_203"
]
```

FIND always returns URIs, which can then be retrieved with GET.

### 5. POST - Action Execution
**Purpose**: Perform an action on a resource  
**Implementation**: Triggers MCP prompts/elicitation  
**Example**:
```
POST mcpweb://email/thread/thread_001/reply
→ [Triggers elicitation prompt]
   "Please provide reply details:"
   - Recipients: alice@example.com, bob@example.com (pre-filled)
   - Subject: Re: Q1 Planning Meeting (pre-filled)
   - Message: [user provides]
→ {"status": "sent", "message_id": "msg_789"}
```

Actions are resources that modify state. They use MCP's prompt system for user interaction.

## Resource-Centric Design

### Everything is a Resource
In RESTful MCP, everything has a URI:
- **Data resources**: `mcpweb://email/inbox`, `mcpweb://calendar/event/evt_123`
- **Action resources**: `mcpweb://email/thread/123/reply`, `mcpweb://calendar/event/evt_123/reschedule`
- **Collection resources**: `mcpweb://email/inbox`, `mcpweb://calendar/today`

### URI Structure
```
mcpweb://[service]/[resource_path]
```
- **Protocol**: Always `mcpweb://`
- **Service**: The service name (e.g., `email`, `calendar`)
- **Resource Path**: Service-specific path (e.g., `/thread/123`, `/event/evt_456`)

### URL Resolution

The `mcpweb://` scheme is a **shortcut notation** that simplifies service access:

```
User provides:     mcpweb://email/thread/123
                          ↓
Gateway resolves:  Service: "email"
                   Endpoint: "http://email-service:3001/mcp"
                   Path: "/thread/123"
                          ↓
Gateway routes:    MCP request to email service
```

This abstraction:
- **Hides service locations**: Clients don't need to know actual endpoints
- **Enables flexibility**: Services can move without breaking clients
- **Supports multiple protocols**: Same URI works regardless of backend protocol

### Actions as Resources
Actions are just resources that trigger prompts when invoked:
```
mcpweb://email/thread/123/reply    # Reply action for thread 123
mcpweb://calendar/event/456/reschedule  # Reschedule action for event 456
mcpweb://document/doc789/share     # Share action for document 789
```

This unifies the model—there's no distinction between "getting data" and "performing actions" at the protocol level.

## Progressive Discovery

The pattern enables natural exploration:

1. **Start broad**: LIST shows available services
2. **Explore service**: VIEW shows what a service offers
3. **Find relevant data**: FIND locates specific resources
4. **Examine details**: GET retrieves full resource data
5. **Take action**: POST performs modifications

Example workflow:
```
User: "Schedule a meeting about the budget proposal"

LIST                                  # What services exist?
→ ["email", "calendar", ...]

VIEW calendar                         # What can calendar do?
→ "Calendar service with event management..."

FIND email "budget proposal"          # Find relevant context
→ ["mcpweb://email/thread/thread_042"]

GET mcpweb://email/thread/thread_042  # Get email details
→ {participants: ["alice@example.com", "cfo@example.com"], ...}

POST mcpweb://calendar/create         # Create event with context
→ [Elicitation with smart defaults from email participants]
```

## Comparison with Tool-Centric Approach

### Traditional MCP (Tool-Centric)
```javascript
// Each service defines custom tools
email_service.tools = [
  search_emails(query, folder, from, to, subject, has_attachment, ...),
  get_email(email_id),
  send_email(to, cc, bcc, subject, body, attachments, ...),
  reply_to_email(email_id, body, reply_all, ...),
  forward_email(email_id, to, comment, ...),
  // ... 20+ more tools with complex signatures
]
```

Problems:
- Each tool has a unique signature to learn
- Parameter names and types vary between services
- No consistent pattern for discovery
- Context window fills with tool definitions

### RESTful MCP (Resource-Centric)
```javascript
// Gateway server provides 5 operations for all services
operations = ["LIST", "VIEW", "GET", "FIND", "POST"]

// Consistent usage pattern
FIND email "budget"                          # Find resources
GET mcpweb://email/thread/123               # Get specific resource
POST mcpweb://email/thread/123/reply        # Perform action
```

Benefits:
- Same interface for all services
- Progressive discovery through URIs
- Minimal context window usage
- Clear separation of data and actions

## Implementation Requirements

For a service to be RESTful MCP-compliant, it needs just three things:

1. **Resources at logical endpoints**
   ```python
   @mcp.resource("/thread/{thread_id}")
   async def get_thread(thread_id: str):
       return thread_data
   ```

2. **Clear instructions in MCP manifest**
   ```python
   mcp = FastMCP(
       name="Email Service",
       instructions="Email service with resources at /inbox and /thread/{id}..."
   )
   ```

3. **Search tool returning URIs**
   ```python
   @mcp.tool
   async def search(query: str) -> list[str]:
       results = search_emails(query)
       return [f"mcpweb://email/thread/{r.id}" for r in results]
   ```

The gateway server handles the rest—LIST, VIEW, GET, FIND, and POST operations.

## Why This Works

1. **Cognitive Load**: Learning 5 operations is easier than learning 500 tools
2. **Composability**: Services can link to each other through URIs
3. **Flexibility**: Services can expose any resources they want
4. **Simplicity**: No complex tool signatures or parameter validation
5. **Scalability**: Pattern works identically for 1 or 1000 services

## RESTful MCP as Middleware

RESTful MCP allows information to be organized as a middleware layer between LLMs and services. The gateway server acts as this middleware, providing:

1. **Uniform Interface**: All services are accessed through the same five operations, regardless of their internal implementation
2. **Service Abstraction**: The complexity of individual services is hidden behind a consistent resource-based interface  
3. **Protocol Independence**: Services can use different protocols (MCP, REST, A2A) behind the same interface
4. **Cross-Service Integration**: Services can reference and interact with each other through the middleware layer
5. **Scalable Architecture**: New services can be added without changing the interface or increasing complexity

### Protocol Flexibility

The middleware design enables protocol flexibility:

```
Client uses:       mcpweb://calendar/event/123
                          ↓
Gateway resolves and routes based on protocol:
  - MCP:          Forward to MCP server
  - REST (future): Map to REST API calls
  - Gateway (future): Route to another gateway
  - A2A (future):  Connect via Agent-to-Agent protocol
```

Currently, only MCP protocol is implemented, but the architecture supports future extensions without changing the client interface.

This middleware approach transforms how LLMs interact with services—instead of learning hundreds of tool-specific APIs, they interact with a single, consistent interface that scales to any number of services.

The RESTful MCP pattern transforms MCP from a tool protocol into a resource protocol, making it suitable for building large-scale service ecosystems.