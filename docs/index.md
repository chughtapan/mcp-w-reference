# RESTful MCP: A Pattern for Scalable MCP Services

## The Problem

When you connect an LLM to multiple services through MCP (Model Context Protocol), you quickly run into scaling issues:

- **Tool Explosion**: Each service exposes dozens of tools. With 10 services, you have 400+ tools competing for the model's attention.
- **Context Bloat**: Every tool definition consumes precious context window space, leaving less room for actual work.
- **Service Confusion**: Models struggle to choose between similar tools from different services (`email_search`, `calendar_search`, `docs_search`...).
- **Poor Isolation**: One service's implementation details can interfere with another's, causing unexpected failures.

## The Solution

RESTful MCP introduces a simple pattern where services just implement resources and search, while a **gateway server** provides **five uniform operations** to interact with any service:

1. **LIST** - Discover what services are available
2. **VIEW** - Learn what a specific service can do
3. **GET** - Retrieve a specific resource by URI
4. **FIND** - Find resources matching a query
5. **POST** - Perform an action on a resource

Services remain simple (just resources + search), while the gateway server provides the consistent interface. Whether you have 1 service or 100 services, the interface remains exactly the same.

## Quick Example

### Traditional MCP Approach (Tool-Centric)
```javascript
// Each service exposes many custom tools
tools: [
  "email_list_inbox",
  "email_get_thread", 
  "email_search_threads",
  "email_send_message",
  "email_reply_to_thread",
  "email_forward_thread",
  "email_archive_thread",
  "email_mark_as_read",
  // ... 20 more email tools
  
  "calendar_list_events",
  "calendar_get_event",
  "calendar_search_events", 
  "calendar_create_event",
  "calendar_update_event",
  "calendar_delete_event",
  // ... 15 more calendar tools
]
// Total: 40+ tools for just 2 services!
```

### RESTful MCP Approach (Resource-Centric)
```javascript
// The gateway server provides 5 operations for all services
operations: ["LIST", "VIEW", "GET", "FIND", "POST"]

// Usage is uniform across all services:
LIST                                    // → ["email", "calendar", "docs", ...]
VIEW email                              // → Email service capabilities
GET mcpweb://email/thread/123          // → Specific email thread
FIND email "project update"            // → ["mcpweb://email/thread/123", ...]
POST mcpweb://email/thread/123/reply   // → Reply to thread (with prompt)
```

## How It Works

1. **Services** implement a simple pattern:
   - Register resources at logical endpoints (e.g., `/thread/{id}`)
   - Provide clear instructions in the MCP instructions field
   - Implement a search tool that returns resource URIs
   
2. **Gateway Server** provides the five operations:
   - Resolves `mcpweb://` URIs to actual service endpoints
   - Routes requests to appropriate services
   - Maintains service isolation
   - Provides a unified interface to all services
   - Currently supports MCP protocol with architecture ready for REST, A2A, and gateway protocols

3. **Resources** are first-class entities:
   - Everything has a URI: `mcpweb://service/resource`
   - Actions are resources too: `mcpweb://email/thread/123/reply`
   - URIs enable linking and discovery

## Benefits

- **Scales Infinitely**: 5 operations whether you have 1 or 1000 services
- **Context Efficient**: Minimal tool definitions leave more room for work
- **Clear Mental Model**: Resources and actions, not a grab bag of functions
- **Progressive Discovery**: Start with LIST, drill down as needed
- **Service Isolation**: Each service is independent and namespaced
- **Protocol Flexibility**: Same `mcpweb://` interface works with any backend protocol

## Getting Started

- **Service Developers**: Read [Building Services](developers/building-services.md) to implement the pattern
- **Consumers**: Read [Using RESTful MCP](consumers/usage.md) to interact with services
- **Concepts**: Read [The Pattern](concepts/pattern.md) for deeper understanding

## Quick Start

```bash
# Install RESTful MCP
git clone <repository>
cd restful-mcp
uv pip install -e .

# Start example services
uv run python examples/email/email.py    # Terminal 1
uv run python examples/calendar/calendar.py # Terminal 2

# Use the services
restful-mcp-agent  # Terminal 3

# Try these commands:
> LIST
> VIEW email
> FIND email "project"
> GET mcpweb://email/thread/thread_001
> POST mcpweb://email/thread/thread_001/reply
```

## Learn More

- [The RESTful MCP Pattern](concepts/pattern.md) - Detailed explanation of the five capabilities
- [Architecture Overview](concepts/architecture.md) - How services and the gateway work together
- [Building Services](developers/building-services.md) - Implement RESTful MCP-compliant services
- [Migration Guide](migration/from-tools.md) - Convert existing MCP servers

RESTful MCP isn't a framework—it's a pattern. It allows information to be organized as a middleware, providing a consistent interface layer between LLMs and services. Use it with any MCP implementation to build scalable, maintainable services.