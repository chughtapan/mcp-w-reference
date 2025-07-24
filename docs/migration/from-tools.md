# Migrating from Tool-Centric to RESTful MCP Pattern

This guide helps you convert existing MCP servers from the traditional tool-centric approach to the RESTful MCP resource-centric pattern. The migration can be done incrementally without breaking existing clients.

## Understanding the Shift

### From Tools to Resources

**Traditional Approach**: Everything is a tool
```python
@mcp.tool
async def get_email_thread(thread_id: str) -> str:
    # Fetch and return thread

@mcp.tool  
async def search_emails(query: str, folder: str = "inbox") -> str:
    # Search and return results

@mcp.tool
async def reply_to_email(thread_id: str, message: str, reply_all: bool = False) -> str:
    # Send reply
```

**RESTful MCP Approach**: Resources and actions
```python
@mcp.resource("/thread/{thread_id}")
async def thread_resource(thread_id: str) -> str:
    # Return thread data

@mcp.resource("/thread/{thread_id}/reply")
async def reply_action(thread_id: str, ctx: Context) -> str:
    # Reply with user prompt

@mcp.tool  # Only search remains a tool
async def search(query: str) -> list[str]:
    # Return resource paths
```

## Migration Strategy

### Step 1: Analyze Your Tools

Create an inventory of your existing tools and categorize them:

| Tool | Type | Maps To |
|------|------|---------|
| `get_inbox` | Data retrieval | Resource: `/inbox` |
| `get_thread` | Data retrieval | Resource: `/thread/{id}` |
| `list_folders` | Data retrieval | Resource: `/folders` |
| `search_emails` | Search | Tool: `search` |
| `send_email` | Action | Resource: `/compose` |
| `reply_to_thread` | Action | Resource: `/thread/{id}/reply` |
| `delete_thread` | Action | Resource: `/thread/{id}/delete` |

### Step 2: Design Your Resource Structure

Convert your flat tool namespace into a hierarchical resource structure:

```
Before (Tools):
- email_get_inbox
- email_get_thread
- email_get_folder
- email_search
- email_send
- email_reply
- email_forward
- email_delete

After (Resources):
/inbox
/folders
/folder/{name}
/thread/{id}
/thread/{id}/reply
/thread/{id}/forward
/thread/{id}/delete
/compose
```

### Step 3: Implement Resources

Convert each data retrieval tool to a resource:

**Before:**
```python
@mcp.tool
async def get_task_list(project_id: str, status: str = "all") -> str:
    tasks = fetch_tasks(project_id, status)
    return json.dumps(tasks)
```

**After:**
```python
@mcp.resource("/project/{project_id}/tasks")
async def project_tasks(project_id: str) -> str:
    tasks = fetch_tasks(project_id, "all")
    return json.dumps({
        "project_id": project_id,
        "tasks": tasks,
        "filter_options": ["/project/{project_id}/tasks/pending", 
                          "/project/{project_id}/tasks/completed"]
    })

# Optional filtered views
@mcp.resource("/project/{project_id}/tasks/pending")
async def pending_tasks(project_id: str) -> str:
    tasks = fetch_tasks(project_id, "pending")
    return json.dumps({"tasks": tasks, "filter": "pending"})
```

### Step 4: Convert Actions to Resource+Prompt

Transform action tools into resources that use prompts:

**Before:**
```python
@mcp.tool
async def create_task(
    project_id: str,
    title: str,
    description: str = "",
    assignee: str = "",
    due_date: str = ""
) -> str:
    task = create_new_task(project_id, title, description, assignee, due_date)
    return json.dumps({"created": task})
```

**After:**
```python
@mcp.resource("/project/{project_id}/tasks/create")
async def create_task_action(project_id: str, ctx: Context) -> str:
    # Get project context for smart defaults
    project = get_project(project_id)
    team_members = get_team_members(project_id)
    
    class CreateTaskSchema(BaseModel):
        title: str = Field(description="Task title")
        description: str = Field(default="", description="Task description")
        assignee: str = Field(
            default="",
            description=f"Assignee ({', '.join(team_members)})"
        )
        due_date: str = Field(
            default=(date.today() + timedelta(days=7)).isoformat(),
            description="Due date (YYYY-MM-DD)"
        )
    
    task_data = await ctx.prompt(
        f"Create task in '{project['name']}'",
        CreateTaskSchema
    )
    
    task = create_new_task(
        project_id,
        task_data.title,
        task_data.description,
        task_data.assignee,
        task_data.due_date
    )
    
    return json.dumps({
        "created": task,
        "uri": f"/task/{task['id']}"
    })
```

### Step 5: Implement Search

Consolidate search tools into a single search that returns paths:

**Before:**
```python
@mcp.tool
async def search_tasks(query: str, project_id: str = None) -> str:
    results = search_all_tasks(query, project_id)
    return json.dumps(results)  # Full task objects

@mcp.tool
async def search_by_assignee(assignee: str) -> str:
    results = find_tasks_by_assignee(assignee)
    return json.dumps(results)
```

**After:**
```python
@mcp.tool
async def search(query: str) -> list[str]:
    """Search across all resources"""
    paths = []
    
    # Search tasks
    task_results = search_all_tasks(query)
    paths.extend([f"/task/{t.id}" for t in task_results])
    
    # Search projects  
    project_results = search_projects(query)
    paths.extend([f"/project/{p.id}" for p in project_results])
    
    # Search by assignee if query looks like email
    if "@" in query:
        assignee_tasks = find_tasks_by_assignee(query)
        paths.extend([f"/task/{t.id}" for t in assignee_tasks])
    
    return paths
```

### Step 6: Update Service Instructions

Write clear instructions describing your resources:

**Before:**
```python
mcp = MCP(
    name="Task Manager",
    instructions="Task management with 15 tools for creating, updating, and organizing tasks"
)
```

**After:**
```python
mcp = MCP(
    name="Task Manager",
    instructions="""
    Task and project management service.
    
    Resources:
    - /projects: List all projects
    - /project/{id}: Project details
    - /project/{id}/tasks: Project tasks
    - /task/{id}: Task details
    - /task/{id}/complete: Mark task complete
    - /task/{id}/assign: Assign task
    - /project/{id}/tasks/create: Create new task
    
    Search: Find tasks and projects by title, description, or assignee.
    Returns resource paths for matching items.
    """
)
```

## Complete Migration Example

Here's a before/after comparison of a simple notes service:

### Before (Tool-Centric)

```python
from mcp import MCP
import json

mcp = MCP("Notes Service", instructions="Note-taking with CRUD operations")

NOTES = {}  # id -> {title, content, tags}

@mcp.tool
async def create_note(title: str, content: str, tags: str = "") -> str:
    note_id = generate_id()
    NOTES[note_id] = {
        "id": note_id,
        "title": title,
        "content": content,
        "tags": tags.split(",") if tags else []
    }
    return json.dumps({"created": note_id})

@mcp.tool
async def get_note(note_id: str) -> str:
    if note_id not in NOTES:
        return json.dumps({"error": "Note not found"})
    return json.dumps(NOTES[note_id])

@mcp.tool
async def list_notes() -> str:
    return json.dumps(list(NOTES.values()))

@mcp.tool
async def update_note(note_id: str, title: str = None, content: str = None) -> str:
    if note_id not in NOTES:
        return json.dumps({"error": "Note not found"})
    
    if title:
        NOTES[note_id]["title"] = title
    if content:
        NOTES[note_id]["content"] = content
    
    return json.dumps({"updated": note_id})

@mcp.tool
async def delete_note(note_id: str) -> str:
    if note_id not in NOTES:
        return json.dumps({"error": "Note not found"})
    
    del NOTES[note_id]
    return json.dumps({"deleted": note_id})

@mcp.tool
async def search_notes(query: str) -> str:
    results = []
    for note in NOTES.values():
        if query.lower() in note["title"].lower() or query.lower() in note["content"].lower():
            results.append(note)
    return json.dumps(results)

mcp.run()
```

### After (RESTful MCP Pattern)

```python
from mcp import MCP, Context
from pydantic import BaseModel, Field
import json

mcp = MCP(
    name="Notes Service",
    instructions="""
    Simple note-taking service.
    
    Resources:
    - /notes: List all notes
    - /note/{id}: Specific note
    - /note/{id}/edit: Edit a note
    - /note/{id}/delete: Delete a note
    - /create: Create new note
    
    Search: Find notes by title or content.
    """
)

NOTES = {}  # id -> {title, content, tags}

# Data Resources

@mcp.resource("/notes")
async def list_notes() -> str:
    notes_list = []
    for note_id, note in NOTES.items():
        notes_list.append({
            "uri": f"/note/{note_id}",
            "title": note["title"],
            "preview": note["content"][:100] + "..." if len(note["content"]) > 100 else note["content"],
            "tags": note["tags"]
        })
    
    return json.dumps({
        "total": len(notes_list),
        "notes": notes_list
    })

@mcp.resource("/note/{note_id}")
async def get_note(note_id: str) -> str:
    if note_id not in NOTES:
        return json.dumps({"error": f"Note {note_id} not found", "status": 404})
    
    note = NOTES[note_id]
    return json.dumps({
        "uri": f"/note/{note_id}",
        "title": note["title"],
        "content": note["content"],
        "tags": note["tags"],
        "actions": [
            f"/note/{note_id}/edit",
            f"/note/{note_id}/delete"
        ]
    })

# Action Resources

@mcp.resource("/create")
async def create_note(ctx: Context) -> str:
    class CreateNoteSchema(BaseModel):
        title: str = Field(description="Note title")
        content: str = Field(description="Note content")
        tags: str = Field(default="", description="Tags (comma-separated)")
    
    note_data = await ctx.prompt("Create new note", CreateNoteSchema)
    
    note_id = generate_id()
    NOTES[note_id] = {
        "id": note_id,
        "title": note_data.title,
        "content": note_data.content,
        "tags": note_data.tags.split(",") if note_data.tags else []
    }
    
    return json.dumps({
        "created": f"/note/{note_id}",
        "title": note_data.title
    })

@mcp.resource("/note/{note_id}/edit")
async def edit_note(note_id: str, ctx: Context) -> str:
    if note_id not in NOTES:
        return json.dumps({"error": f"Note {note_id} not found", "status": 404})
    
    note = NOTES[note_id]
    
    class EditNoteSchema(BaseModel):
        title: str = Field(default=note["title"], description="Note title")
        content: str = Field(default=note["content"], description="Note content")
        tags: str = Field(
            default=",".join(note["tags"]),
            description="Tags (comma-separated)"
        )
    
    edit_data = await ctx.prompt(f"Edit '{note['title']}'", EditNoteSchema)
    
    NOTES[note_id]["title"] = edit_data.title
    NOTES[note_id]["content"] = edit_data.content
    NOTES[note_id]["tags"] = edit_data.tags.split(",") if edit_data.tags else []
    
    return json.dumps({
        "updated": f"/note/{note_id}",
        "title": edit_data.title
    })

@mcp.resource("/note/{note_id}/delete")
async def delete_note(note_id: str, ctx: Context) -> str:
    if note_id not in NOTES:
        return json.dumps({"error": f"Note {note_id} not found", "status": 404})
    
    note = NOTES[note_id]
    
    class DeleteConfirmSchema(BaseModel):
        confirm: bool = Field(description=f"Delete '{note['title']}'?")
    
    confirm_data = await ctx.prompt("Confirm deletion", DeleteConfirmSchema)
    
    if not confirm_data.confirm:
        return json.dumps({"status": "cancelled"})
    
    del NOTES[note_id]
    return json.dumps({"deleted": note_id})

# Search Tool

@mcp.tool
async def search(query: str) -> list[str]:
    """Search notes by title or content"""
    results = []
    query_lower = query.lower()
    
    for note_id, note in NOTES.items():
        if (query_lower in note["title"].lower() or 
            query_lower in note["content"].lower() or
            any(query_lower in tag.lower() for tag in note["tags"])):
            results.append(f"/note/{note_id}")
    
    return results

mcp.run()
```

## Migration Benefits

### 1. Reduced Complexity
- **Before**: 6 tools with different signatures
- **After**: 1 tool + resources with consistent patterns

### 2. Better User Experience
- Interactive prompts with smart defaults
- Consistent navigation through URIs
- Clear action discovery

### 3. Improved Context Usage
- Fewer tool definitions in context
- Progressive discovery reduces noise
- Related resources are linked

### 4. Enhanced Composability
- Resources can reference each other
- Services can link across boundaries
- URIs enable bookmarking and sharing

## Incremental Migration

You don't have to migrate everything at once:

1. **Phase 1**: Add resources alongside existing tools
2. **Phase 2**: Implement search returning URIs
3. **Phase 3**: Convert actions to use prompts
4. **Phase 4**: Deprecate old tools
5. **Phase 5**: Remove deprecated tools

```python
# Temporary compatibility during migration
@mcp.tool
async def get_note_legacy(note_id: str) -> str:
    """DEPRECATED: Use GET /note/{id} instead"""
    return await get_note(note_id)
```

## Testing Your Migration

Ensure your migrated service works correctly:

```python
# Test resources are accessible
assert "/notes" in list_resources()
assert "/note/{note_id}" in list_resources()

# Test search returns paths
results = await search("important")
assert all(r.startswith("/note/") for r in results)

# Test actions trigger prompts
response = await invoke_action("/note/123/edit", test_context)
assert "updated" in response
```

## Common Patterns

### Filtering and Views
Convert filter parameters to separate resources:
- Before: `get_tasks(status="pending")`
- After: `/tasks/pending`

### Batch Operations
Convert bulk tools to collection actions:
- Before: `delete_multiple_tasks(task_ids)`
- After: `/tasks/delete` (with multi-select prompt)

### Relationships
Use URIs to express relationships:
- Before: `get_task_project(task_id)`
- After: Task includes `"project": "/project/123"`

## Summary

Migrating to RESTful MCP pattern:
1. Simplifies your API surface
2. Improves user experience
3. Reduces context window usage
4. Enables better service composition

The migration can be incremental, allowing you to maintain compatibility while modernizing your service architecture.