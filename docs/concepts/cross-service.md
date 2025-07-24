# Cross-Service Communication

Services in the RESTful MCP ecosystem can interact with each other through the gateway's enhanced context. This enables powerful workflows while maintaining loose coupling between services.

## Overview

When services run under the RESTful MCP gateway, they receive an enhanced context that provides access to other services through the same five operations (LIST, VIEW, GET, FIND, POST) used by clients.

## The Context Request API

### Basic Pattern

Within any service tool or resource that receives a context parameter:

```python
# Access another service through the gateway
result = await ctx.request(operation, uri, query)
```

### Parameters

- **operation**: One of `"LIST"`, `"VIEW"`, `"GET"`, `"FIND"`, `"POST"`
- **uri**: Full mcpweb:// URI for the target service or resource
- **query**: Optional query string (only used with FIND operation)

## Operations

### 1. LIST - Discover Services

```python
@mcp.tool
async def my_tool(ctx: Context):
    # List all available services
    services = await ctx.request("LIST", "mcpweb://")
    # Returns: ["email", "calendar", "documents", ...]
```

### 2. VIEW - Get Service Information

```python
@mcp.tool
async def check_calendar_features(ctx: Context):
    # Get information about the calendar service
    info = await ctx.request("VIEW", "mcpweb://calendar")
    # Returns service description, resources, and capabilities
```

### 3. FIND - Search Across Services

```python
@mcp.tool
async def find_related_items(query: str, ctx: Context):
    # Search in email service
    email_results = await ctx.request("FIND", "mcpweb://email", query)
    
    # Search in documents service
    doc_results = await ctx.request("FIND", "mcpweb://documents", query)
    
    return {
        "emails": email_results,
        "documents": doc_results
    }
```

### 4. GET - Retrieve Resources

```python
@mcp.tool
async def process_with_context(thread_id: str, ctx: Context):
    # Get email thread from another service
    thread = await ctx.request("GET", f"mcpweb://email/thread/{thread_id}")
    
    # Or use ctx.read_resource() which handles both local and cross-service
    thread = await ctx.read_resource(f"mcpweb://email/thread/{thread_id}")
```

### 5. POST - Trigger Actions

```python
@mcp.tool
async def schedule_from_email(thread_id: str, ctx: Context):
    # Get email details
    thread = await ctx.read_resource(f"/thread/{thread_id}")
    
    # Trigger calendar event creation
    # This will prompt the user with calendar service's prompts
    result = await ctx.request("POST", "mcpweb://calendar/create")
    
    return {"email": thread_id, "event": result.get("uri")}
```

## Real-World Examples

### Email to Calendar Integration

```python
# In email service
@mcp.tool
async def schedule_meeting_from_thread(thread_id: str, ctx: Context):
    """Create a calendar event from an email thread"""
    
    # Get thread details
    thread = await ctx.read_resource(f"/thread/{thread_id}")
    
    # Find related calendar events
    events = await ctx.request("FIND", "mcpweb://calendar", thread["subject"])
    
    # Create calendar event if needed
    if not events:
        event = await ctx.request("POST", "mcpweb://calendar/create")
    
        return {
            "thread": thread_id,
            "event": event.get("uri"),
            "scheduled": True
        }
    
    return {
        "thread": thread_id,
        "existing_events": events
    }
```

### Cross-Service Workflow

```python
# In document service
@mcp.tool
async def share_document(doc_id: str, ctx: Context):
    """Share a document via email"""
    
    # Get document details
    doc = await ctx.read_resource(f"/document/{doc_id}")
    
    # Use email service to share
    result = await ctx.request("POST", "mcpweb://email/compose")
    
    return {
        "document": doc_id,
        "shared": True,
        "email_sent": result.get("status") == "sent"
    }
```

## Best Practices

### 1. Use Full URIs

Always use complete mcpweb:// URIs for cross-service communication:

```python
# Good
await ctx.request("GET", "mcpweb://calendar/event/123")

# Bad - ambiguous
await ctx.request("GET", "/event/123")
```

### 2. Handle Service Unavailability

Services might not always be available:

```python
try:
    result = await ctx.request("FIND", "mcpweb://calendar", "meeting")
except Exception as e:
    # Gracefully handle unavailable service
    logger.warning(f"Calendar service unavailable: {e}")
    result = []
```

### 3. Avoid Circular Dependencies

Be careful not to create circular service calls:

```python
# email -> calendar -> email -> calendar ... (BAD)
```

### 4. Respect Service Boundaries

Services should remain loosely coupled:

```python
# Good: Use standard operations
events = await ctx.request("FIND", "mcpweb://calendar", "today")

# Bad: Don't assume internal structure
# calendar_db = ctx.request("GET", "mcpweb://calendar/internal/database")
```

## Gateway Context vs Standard Context

The gateway automatically enhances the standard FastMCP context:

| Feature | Standard Context | Gateway Context |
|---------|-----------------|-----------------|
| Local resources | ✓ `ctx.read_resource("/path")` | ✓ Same |
| Cross-service resources | ✗ Not available | ✓ `ctx.read_resource("mcpweb://...")` |
| Cross-service operations | ✗ Not available | ✓ `ctx.request("OP", "mcpweb://...")` |
| State management | ✓ Available | ✓ Same |
| Prompts/Elicitation | ✓ Available | ✓ Same |

## Technical Implementation

The gateway wraps the standard FastMCP context before passing it to services:

```python
# In the gateway
if 'ctx' in kwargs and kwargs['ctx'] is not None:
    # Replace with enhanced context
    kwargs['ctx'] = GatewayContext(kwargs['ctx'], self)
```

This means:
- Services work normally without the gateway
- When running under the gateway, they gain cross-service capabilities
- No code changes required in existing services

## Summary

Cross-service communication in RESTful MCP:
- Uses the same five operations as the main interface
- Maintains loose coupling between services
- Enables powerful multi-service workflows
- Works through the gateway's context enhancement
- Requires no changes to existing services

Services can progressively adopt cross-service features while remaining independently deployable and testable.