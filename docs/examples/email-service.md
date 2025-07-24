# Email Service Example

This example walks through building a complete RESTful MCP-compliant email service. We'll implement the three requirements: resources at logical endpoints, clear service instructions, and a search tool.

## Service Overview

Our email service will provide:
- Thread-based email organization
- Inbox and thread views
- Search functionality
- Reply and forward actions

## Complete Implementation

```python
from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from mcp import MCP, Context

# Service setup with clear instructions
mcp = MCP(
    name="Email Service",
    instructions="""
    Email service with thread-based messaging.
    
    Resources:
    - /inbox: View all email threads
    - /inbox/unread: View unread threads only
    - /thread/{thread_id}: Get specific thread with all messages
    - /thread/{thread_id}/reply: Reply to a thread
    - /thread/{thread_id}/forward: Forward a thread
    
    Search: Full-text search across email subjects and content.
    Returns thread URIs matching the query.
    """
)

# Data models
class EmailMessage:
    def __init__(self, sender: str, content: str, timestamp: datetime):
        self.sender = sender
        self.content = content
        self.timestamp = timestamp

class EmailThread:
    def __init__(self, thread_id: str, subject: str, participants: List[str]):
        self.thread_id = thread_id
        self.subject = subject
        self.participants = participants
        self.messages: List[EmailMessage] = []
        self.unread = True
        self.last_updated = datetime.now()

# Sample data (in production, this would be a database)
THREADS = {
    "thread_001": EmailThread(
        "thread_001",
        "Q1 Budget Planning",
        ["alice@example.com", "bob@example.com", "cfo@example.com"]
    ),
    "thread_002": EmailThread(
        "thread_002", 
        "Project Alpha Update",
        ["pm@example.com", "dev@example.com"]
    ),
    "thread_003": EmailThread(
        "thread_003",
        "Team Meeting Notes",
        ["team@example.com"]
    )
}

# Add sample messages
THREADS["thread_001"].messages = [
    EmailMessage("alice@example.com", "Here's the initial budget draft", datetime(2024, 3, 10, 9, 0)),
    EmailMessage("cfo@example.com", "Thanks, I'll review and provide feedback", datetime(2024, 3, 10, 10, 30)),
    EmailMessage("bob@example.com", "I've added the marketing projections", datetime(2024, 3, 10, 14, 15))
]

THREADS["thread_002"].messages = [
    EmailMessage("pm@example.com", "Sprint 3 is complete. Demo on Friday?", datetime(2024, 3, 11, 11, 0)),
    EmailMessage("dev@example.com", "Sounds good. I'll prepare the demo", datetime(2024, 3, 11, 11, 30))
]

THREADS["thread_002"].unread = False  # Mark as read

# Resource implementations

@mcp.resource("/inbox")
async def get_inbox() -> Dict[str, Any]:
    """Get all email threads in inbox"""
    threads = []
    for thread in THREADS.values():
        threads.append({
            "uri": f"/thread/{thread.thread_id}",
            "subject": thread.subject,
            "participants": thread.participants,
            "unread": thread.unread,
            "last_updated": thread.last_updated.isoformat(),
            "preview": thread.messages[-1].content[:50] + "..." if thread.messages else ""
        })
    
    return {
        "total_threads": len(threads),
        "unread_count": sum(1 for t in threads if t["unread"]),
        "threads": sorted(threads, key=lambda t: t["last_updated"], reverse=True)
    }

@mcp.resource("/inbox/unread")
async def get_unread() -> Dict[str, Any]:
    """Get only unread email threads"""
    all_inbox = await get_inbox()
    unread_threads = [t for t in all_inbox["threads"] if t["unread"]]
    
    return {
        "total_threads": len(unread_threads),
        "threads": unread_threads
    }

@mcp.resource("/thread/{thread_id}")
async def get_thread(thread_id: str) -> Dict[str, Any]:
    """Get specific email thread with all messages"""
    if thread_id not in THREADS:
        return {"error": f"Thread {thread_id} not found", "status": 404}
    
    thread = THREADS[thread_id]
    
    # Mark as read when accessed
    thread.unread = False
    
    return {
        "uri": f"/thread/{thread_id}",
        "subject": thread.subject,
        "participants": thread.participants,
        "messages": [
            {
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in thread.messages
        ],
        "actions": [
            f"/thread/{thread_id}/reply",
            f"/thread/{thread_id}/forward"
        ]
    }

@mcp.resource("/thread/{thread_id}/reply")
async def reply_to_thread(thread_id: str, ctx: Context) -> Dict[str, Any]:
    """Reply to an email thread"""
    if thread_id not in THREADS:
        return {"error": f"Thread {thread_id} not found", "status": 404}
    
    thread = THREADS[thread_id]
    
    # Smart defaults from thread context
    class ReplySchema(BaseModel):
        recipients: str = Field(
            default=", ".join(thread.participants),
            description="Comma-separated email addresses"
        )
        subject: str = Field(
            default=f"Re: {thread.subject}",
            description="Email subject"
        )
        message: str = Field(
            description="Your reply message"
        )
        cc: str = Field(
            default="",
            description="CC recipients (optional)"
        )
    
    # Prompt user for reply details
    reply_data = await ctx.prompt(
        f"Reply to '{thread.subject}'",
        ReplySchema
    )
    
    # Simulate sending email
    new_message = EmailMessage(
        "you@example.com",
        reply_data.message,
        datetime.now()
    )
    thread.messages.append(new_message)
    thread.last_updated = datetime.now()
    
    return {
        "status": "sent",
        "recipients": reply_data.recipients.split(", "),
        "subject": reply_data.subject,
        "timestamp": new_message.timestamp.isoformat()
    }

@mcp.resource("/thread/{thread_id}/forward")
async def forward_thread(thread_id: str, ctx: Context) -> Dict[str, Any]:
    """Forward an email thread"""
    if thread_id not in THREADS:
        return {"error": f"Thread {thread_id} not found", "status": 404}
    
    thread = THREADS[thread_id]
    
    class ForwardSchema(BaseModel):
        recipients: str = Field(
            description="Forward to (comma-separated emails)"
        )
        subject: str = Field(
            default=f"Fwd: {thread.subject}",
            description="Email subject"
        )
        message: str = Field(
            default="",
            description="Additional message (optional)"
        )
    
    forward_data = await ctx.prompt(
        f"Forward '{thread.subject}'",
        ForwardSchema
    )
    
    # Simulate forwarding
    return {
        "status": "forwarded",
        "recipients": forward_data.recipients.split(", "),
        "subject": forward_data.subject,
        "original_thread": thread_id
    }

# Search implementation

@mcp.tool
async def search(query: str) -> List[str]:
    """
    Search emails by subject or content.
    Returns list of thread URIs matching the query.
    """
    query_lower = query.lower()
    matching_threads = []
    
    for thread_id, thread in THREADS.items():
        # Search in subject
        if query_lower in thread.subject.lower():
            matching_threads.append(f"/thread/{thread_id}")
            continue
            
        # Search in participants
        if any(query_lower in p.lower() for p in thread.participants):
            matching_threads.append(f"/thread/{thread_id}")
            continue
            
        # Search in message content
        for msg in thread.messages:
            if query_lower in msg.content.lower():
                matching_threads.append(f"/thread/{thread_id}")
                break
    
    return matching_threads

# Optional: Additional utility resources

@mcp.resource("/compose")
async def compose_email(ctx: Context) -> Dict[str, Any]:
    """Compose a new email"""
    class ComposeSchema(BaseModel):
        recipients: str = Field(description="To (comma-separated)")
        subject: str = Field(description="Email subject")
        message: str = Field(description="Email content")
        cc: str = Field(default="", description="CC (optional)")
    
    email_data = await ctx.prompt("Compose new email", ComposeSchema)
    
    # Create new thread
    thread_id = f"thread_{len(THREADS) + 1:03d}"
    new_thread = EmailThread(
        thread_id,
        email_data.subject,
        email_data.recipients.split(", ")
    )
    new_thread.messages.append(
        EmailMessage("you@example.com", email_data.message, datetime.now())
    )
    
    THREADS[thread_id] = new_thread
    
    return {
        "status": "sent",
        "thread_uri": f"/thread/{thread_id}",
        "subject": email_data.subject
    }

# Run the service
if __name__ == "__main__":
    mcp.run()
```

## Testing the Service

### 1. Service Discovery
```python
# VIEW returns service instructions
print(mcp.instructions)
```

### 2. Resource Access
```python
# Get inbox
inbox = await get_inbox()
assert inbox["total_threads"] == 3

# Get specific thread
thread = await get_thread("thread_001")
assert thread["subject"] == "Q1 Budget Planning"
assert len(thread["messages"]) == 3

# Get unread only
unread = await get_unread()
assert unread["total_threads"] == 2  # thread_002 is read
```

### 3. Search Functionality
```python
# Search by subject
results = await search("budget")
assert "/thread/thread_001" in results

# Search by participant
results = await search("alice")
assert "/thread/thread_001" in results

# Search by content
results = await search("sprint")
assert "/thread/thread_002" in results
```

### 4. Actions
```python
# Reply action
response = await reply_to_thread("thread_001", test_context)
assert response["status"] == "sent"

# Forward action
response = await forward_thread("thread_001", test_context)
assert response["status"] == "forwarded"
```

## Usage Examples

### Basic Workflow
```
# Discover inbox
GET /inbox
→ Shows all threads with previews

# Read a thread
GET /thread/thread_001
→ Shows full thread with all messages

# Reply to thread
POST /thread/thread_001/reply
→ Prompts for reply with smart defaults
```

### Search Workflow
```
# Find budget-related emails
FIND "budget"
→ ["/thread/thread_001"]

# Get the thread
GET /thread/thread_001
→ Full thread content

# Reply with context
POST /thread/thread_001/reply
→ Recipients pre-filled with thread participants
```

## Best Practices Demonstrated

1. **Clear Resource Hierarchy**
   - `/inbox` - Collection resource
   - `/inbox/unread` - Filtered view
   - `/thread/{id}` - Specific resource
   - `/thread/{id}/reply` - Action resource

2. **Smart Defaults in Actions**
   - Reply pre-fills recipients from thread
   - Reply pre-fills subject with "Re: "
   - Forward pre-fills subject with "Fwd: "

3. **Comprehensive Search**
   - Searches across subjects
   - Searches in participants
   - Searches in message content

4. **Error Handling**
   - Returns 404 for missing threads
   - Clear error messages

5. **Resource Linking**
   - Threads include action URIs
   - Inbox entries link to full threads

## Extension Ideas

1. **Additional Resources**
   - `/drafts` - Draft emails
   - `/sent` - Sent emails
   - `/thread/{id}/archive` - Archive action
   - `/thread/{id}/delete` - Delete action

2. **Advanced Search**
   - Date range filters
   - Sender filters
   - Attachment search

3. **Batch Operations**
   - `/threads/archive` - Archive multiple
   - `/threads/mark-read` - Mark multiple as read

4. **Integration Points**
   - Link to calendar events
   - Reference document URIs
   - Task creation from emails

This email service demonstrates how simple it is to build RESTful MCP-compliant services. With just resources, instructions, and search, you get a fully functional service that integrates seamlessly with the RESTful MCP ecosystem.