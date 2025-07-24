# Building RESTful MCP Services

This guide shows you how to build MCP services that follow the RESTful MCP pattern. The beauty is that you only need to implement three simple requirements—the gateway server handles the rest.

## The Three Requirements

To build a RESTful MCP-compliant service, you need:

1. **Resources at logical endpoints** (using MCP's resource system)
2. **Clear service instructions** (in the MCP manifest)  
3. **A search tool** (that returns resource paths)

That's it. No need to implement LIST, VIEW, GET, FIND, or POST—those are handled by the gateway server.

## Quick Example

Here's a minimal RESTful MCP service:

```python
from mcp import MCP, Context

# 1. Create service with clear instructions
mcp = MCP(
    name="Notes Service",
    instructions="""
    Simple note-taking service.
    
    Resources:
    - /notes: List all notes
    - /note/{id}: Get specific note
    - /note/{id}/edit: Edit a note
    
    Search: Find notes by content
    """
)

# 2. Register resources at logical endpoints
@mcp.resource("/notes")
async def list_notes():
    return {"notes": get_all_notes()}

@mcp.resource("/note/{note_id}")
async def get_note(note_id: str):
    return get_note_by_id(note_id)

@mcp.resource("/note/{note_id}/edit")
async def edit_note(note_id: str, ctx: Context):
    # Action resources use prompts for user input
    changes = await ctx.prompt("What changes?", NoteEditSchema)
    return update_note(note_id, changes)

# 3. Implement search tool
@mcp.tool
async def search(query: str) -> list[str]:
    """Search notes by content"""
    results = search_notes(query)
    return [f"/note/{note.id}" for note in results]

# Run the service
mcp.run()
```

## Resource Design

### Data Resources

Data resources are read-only and return information:

```python
@mcp.resource("/inbox")
async def inbox():
    """Email inbox showing recent threads"""
    return {
        "threads": get_recent_threads(),
        "unread_count": count_unread()
    }

@mcp.resource("/thread/{thread_id}")
async def thread(thread_id: str):
    """Specific email thread with all messages"""
    return {
        "id": thread_id,
        "subject": get_subject(thread_id),
        "messages": get_messages(thread_id),
        "participants": get_participants(thread_id)
    }
```

### Action Resources

Action resources modify state and use prompts for user interaction:

```python
@mcp.resource("/thread/{thread_id}/reply")
async def reply(thread_id: str, ctx: Context):
    """Reply to email thread"""
    # Get context for smart defaults
    thread = get_thread(thread_id)
    
    # Define the prompt schema
    class ReplySchema(BaseModel):
        recipients: str = Field(
            default=format_recipients(thread.participants),
            description="Comma-separated email addresses"
        )
        subject: str = Field(
            default=f"Re: {thread.subject}",
            description="Email subject"
        )
        message: str = Field(description="Your reply")
        
    # Prompt user for input
    reply_data = await ctx.prompt(
        "Compose your reply",
        ReplySchema
    )
    
    # Perform the action
    return send_email(reply_data)
```

### Collection Resources

Collections provide filtered views of data:

```python
@mcp.resource("/calendar/today")
async def today():
    """Today's calendar events"""
    return {
        "date": date.today().isoformat(),
        "events": get_events_for_date(date.today())
    }

@mcp.resource("/calendar/{year}/{month}")
async def month_view(year: int, month: int):
    """Monthly calendar view"""
    return {
        "year": year,
        "month": month,
        "events": get_events_for_month(year, month)
    }
```

## Resource Patterns

### Hierarchical Resources
```
/projects                    # All projects
/project/{id}               # Specific project
/project/{id}/tasks         # Project's tasks
/project/{id}/task/{tid}    # Specific task
```

### Action Resources
```
/document/{id}/share        # Share document
/document/{id}/export       # Export document
/task/{id}/complete        # Mark task complete
/event/{id}/reschedule     # Reschedule event
```

### Filtered Views
```
/inbox                      # Default inbox
/inbox/unread              # Unread only
/calendar/today            # Today's events
/calendar/week             # This week
```

## Service Instructions

Your service instructions (in the MCP manifest) should clearly describe:

1. **What the service does**
2. **Available resources and their paths**
3. **What search returns**

Example:

```python
mcp = MCP(
    name="Task Manager",
    instructions="""
    Task management service with projects and tasks.
    
    Resources:
    - /projects: List all projects
    - /project/{id}: Get project details  
    - /project/{id}/tasks: List project tasks
    - /task/{id}: Get task details
    - /task/{id}/complete: Mark task as complete
    - /task/{id}/assign: Assign task to user
    
    Search: Find tasks by title, description, or assignee.
    Returns task resource paths.
    
    All paths return JSON data. Action resources (/complete, /assign)
    will prompt for confirmation or additional details.
    """
)
```

## Implementing Search

The search tool is the only required tool. It should:

1. Accept a query string
2. Search your service's data
3. Return resource paths (not full URIs)

```python
@mcp.tool
async def search(query: str) -> list[str]:
    """
    Search for resources matching the query.
    Returns a list of resource paths.
    """
    results = []
    
    # Search different resource types
    matching_projects = search_projects(query)
    matching_tasks = search_tasks(query)
    
    # Return paths, not full URIs
    results.extend([f"/project/{p.id}" for p in matching_projects])
    results.extend([f"/task/{t.id}" for t in matching_tasks])
    
    return results
```

## Smart Defaults in Actions

Use context to provide intelligent defaults in prompts:

```python
@mcp.resource("/event/{event_id}/reschedule")
async def reschedule(event_id: str, ctx: Context):
    # Get current event data
    event = get_event(event_id)
    
    class RescheduleSchema(BaseModel):
        new_date: str = Field(
            default=(event.date + timedelta(days=1)).isoformat(),
            description="New date (YYYY-MM-DD)"
        )
        new_time: str = Field(
            default=event.time,
            description="New time (HH:MM)"
        )
        notify_attendees: bool = Field(
            default=True,
            description="Send notifications?"
        )
    
    changes = await ctx.prompt(
        f"Reschedule '{event.title}'",
        RescheduleSchema
    )
    
    return reschedule_event(event_id, changes)
```

## Testing Your Service

Test each requirement:

### 1. Test Resources
```python
# Verify resources are accessible
response = await mcp.get_resource("/project/123")
assert response["id"] == "123"

# Test parameterized paths
response = await mcp.get_resource("/calendar/2024/03")
assert response["year"] == 2024
```

### 2. Test Search
```python
# Verify search returns paths
results = await mcp.call_tool("search", {"query": "budget"})
assert all(r.startswith("/") for r in results)
assert "/project/123" in results
```

### 3. Test Actions
```python
# Verify actions trigger prompts
response = await mcp.get_resource(
    "/task/123/complete",
    context=test_context
)
assert response["status"] == "completed"
```

## Best Practices

### 1. Resource Naming
- Use nouns for data: `/project/{id}`, `/user/{id}`
- Use verbs for actions: `/project/{id}/archive`, `/user/{id}/invite`
- Be consistent across your service

### 2. Error Handling
```python
@mcp.resource("/note/{note_id}")
async def get_note(note_id: str):
    note = find_note(note_id)
    if not note:
        return {
            "error": f"Note {note_id} not found",
            "status": 404
        }
    return note
```

### 3. Cross-References
```python
@mcp.resource("/project/{project_id}")
async def get_project(project_id: str):
    return {
        "id": project_id,
        "name": get_name(project_id),
        "tasks": f"/project/{project_id}/tasks",  # Link to related resources
        "members": f"/project/{project_id}/members",
        "actions": [
            f"/project/{project_id}/archive",
            f"/project/{project_id}/share"
        ]
    }
```

## Common Patterns

### Status Resources
```python
@mcp.resource("/status")
async def service_status():
    """Service health and statistics"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "total_resources": count_all_resources(),
        "last_updated": get_last_update_time()
    }
```

### Bulk Actions
```python
@mcp.resource("/tasks/complete")
async def bulk_complete(ctx: Context):
    """Complete multiple tasks at once"""
    class BulkCompleteSchema(BaseModel):
        task_ids: list[str] = Field(description="Task IDs to complete")
        notes: str = Field(default="", description="Completion notes")
    
    data = await ctx.prompt("Select tasks to complete", BulkCompleteSchema)
    return complete_tasks(data.task_ids, data.notes)
```


## Cross-Service Communication

When your service runs under the RESTful MCP gateway, it can interact with other services through the enhanced context. See the [Cross-Service Communication](../concepts/cross-service.md) guide for details.

### Basic Example

```python
@mcp.tool
async def process_with_calendar(thread_id: str, ctx: Context):
    # Get local data
    thread = await ctx.read_resource(f"/thread/{thread_id}")
    
    # Find related calendar events
    events = await ctx.request("FIND", "mcpweb://calendar", thread["subject"])
    
    # Trigger calendar action if needed
    if not events:
        event = await ctx.request("POST", "mcpweb://calendar/create")
        return {"thread": thread_id, "event": event}
    
    return {"thread": thread_id, "existing_events": events}
```

## Next Steps

1. Start with a simple service (3-5 resources)
2. Implement search that returns sensible results
3. Add action resources for state changes
4. Write clear service instructions
5. Test with the RESTful MCP gateway
6. Add cross-service features progressively

Remember: RESTful MCP services are just regular MCP servers with a consistent pattern. Keep it simple, and let the gateway handle the complexity of aggregation. Cross-service features are optional enhancements that can be added when needed.