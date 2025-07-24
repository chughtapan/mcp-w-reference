"""
Email service implementation using MCPW pattern.

This service provides email management capabilities including:
- Viewing email threads and inbox
- Searching emails by subject or participants
- Replying to email threads with user interaction

The service uses relative resource paths that are automatically
prefixed by the router when mounted.
"""

from typing import Dict, List, Optional

from fastmcp import Context
from pydantic import BaseModel, Field

from src.mcp_w.mcpw import MCPWService

# ==================== Constants ====================

SERVICE_NAME = "Email Service"
SERVICE_INSTRUCTIONS = """Email management service with thread, search, and reply capabilities.

Resources:
- /inbox - View all email threads
- /thread/{thread_id} - View specific thread details

Tools:
- search_resources - Find threads by subject or participants
- invoke_action - Reply to threads (supports: reply_thread)
"""

# Error messages
ERROR_THREAD_NOT_FOUND = "Thread '{thread_id}' not found"
ERROR_UNKNOWN_ACTION = "Unknown action: {action}. Available: reply_thread"

# ==================== Data Models ====================

class ReplyDetails(BaseModel):
    """Schema for collecting reply details through user elicitation."""
    recipients: str = Field(description="Recipients (comma-separated)")
    content: str = Field(default="", description="Reply content")
    send_immediately: bool = Field(
        default=False, 
        description="Send now or save as draft"
    )


# ==================== Sample Data ====================
# In a real implementation, this would come from an email API

SAMPLE_THREADS = [
    {
        "thread_id": "thread_001",
        "subject": "Project Update Meeting",
        "participants": ["alice@company.com", "bob@company.com"],
        "last_updated": "2024-01-15T10:30:00Z",
        "unread_count": 2,
    },
    {
        "thread_id": "thread_002",
        "subject": "Budget Review Q1",
        "participants": ["manager@company.com", "finance@company.com"],
        "last_updated": "2024-01-14T15:45:00Z",
        "unread_count": 0,
    },
]

SAMPLE_THREAD_DETAILS = {
    "thread_001": {
        "content": "Can we schedule a meeting for next week to discuss the project updates? "
                   "I'd like to review the latest milestones."
    },
    "thread_002": {
        "content": "Please review the Q1 budget numbers and let me know if you have any questions. "
                   "The finance team needs feedback by Friday."
    },
}

# ==================== Service Setup ====================

mcp = MCPWService(SERVICE_NAME, instructions=SERVICE_INSTRUCTIONS)

# ==================== Resource Handlers ====================

@mcp.resource("/inbox")
async def get_inbox_resource() -> Dict:
    """
    Get all email threads from inbox.
    
    Returns a summary of all threads including subject, participants,
    last update time, and unread count.
    """
    threads_data = [
        {
            "thread_id": thread["thread_id"],
            "subject": thread["subject"],
            "participants": thread["participants"],
            "last_updated": thread["last_updated"],
            "unread_count": thread["unread_count"],
        }
        for thread in SAMPLE_THREADS
    ]
    
    return {
        "inbox": {
            "total_threads": len(threads_data),
            "threads": threads_data
        }
    }


@mcp.resource("/thread/{thread_id}")
async def get_thread_resource(thread_id: str) -> Dict:
    """
    Get detailed information about a specific email thread.
    
    Args:
        thread_id: The thread ID to retrieve
        
    Returns:
        Complete thread details including content, or error if not found
    """
    # Find the thread
    thread = next(
        (t for t in SAMPLE_THREADS if t["thread_id"] == thread_id),
        None
    )
    
    if not thread:
        return {"error": ERROR_THREAD_NOT_FOUND.format(thread_id=thread_id)}
    
    # Get thread content
    thread_details = SAMPLE_THREAD_DETAILS.get(
        thread_id, 
        {"content": "No content available"}
    )
    
    # Return complete thread information
    return {
        "thread_id": thread["thread_id"],
        "subject": thread["subject"],
        "participants": thread["participants"],
        "last_updated": thread["last_updated"],
        "unread_count": thread["unread_count"],
        "content": thread_details["content"],
    }

# ==================== Tool Implementations ====================

@mcp.tool
async def search_resources(query: str) -> List[str]:
    """
    Search email threads by subject or participants.
    
    Searches are case-insensitive and match partial strings.
    
    Args:
        query: Search string to match against subjects and participants
        
    Returns:
        List of relative resource paths for matching threads
        
    Example:
        >>> await search_resources("budget")
        ["/thread/thread_002"]
    """
    query_lower = query.lower()
    matching_threads = []
    
    for thread in SAMPLE_THREADS:
        # Check subject
        if query_lower in thread["subject"].lower():
            matching_threads.append(f"/thread/{thread['thread_id']}")
            continue
        
        # Check participants
        for participant in thread["participants"]:
            if query_lower in participant.lower():
                matching_threads.append(f"/thread/{thread['thread_id']}")
                break
    
    return matching_threads


@mcp.tool
async def invoke_action(action: str, resource_id: str, ctx: Context) -> Dict:
    """
    Perform actions on email resources.
    
    Currently supports:
    - reply_thread: Reply to an email thread with user elicitation
    
    Args:
        action: Action to perform
        resource_id: Full resource URI (e.g., "mcpweb://email/thread/001")
        ctx: Context for user interaction
        
    Returns:
        Action result or error message
    """
    if action == "reply_thread":
        return await _handle_reply_thread(ctx, resource_id)
    else:
        return {"error": ERROR_UNKNOWN_ACTION.format(action=action)}

# ==================== Action Handlers ====================

async def _handle_reply_thread(ctx: Context, resource_id: str) -> Dict:
    """
    Handle replying to an email thread with user elicitation.
    
    Extracts thread information and uses elicitation to collect
    reply details from the user.
    
    Args:
        ctx: FastMCP context for elicitation
        resource_id: Full resource URI (e.g., "mcpweb://email/thread/001")
        
    Returns:
        Reply result with status and details
    """
    # Extract thread ID from resource URI
    thread_id = resource_id.split("/")[-1]
    
    # Find the thread
    thread = next(
        (t for t in SAMPLE_THREADS if t["thread_id"] == thread_id),
        None
    )
    
    if not thread:
        return {"error": ERROR_THREAD_NOT_FOUND.format(thread_id=thread_id)}
    
    # Prepare default recipients
    default_recipients = ", ".join(thread["participants"])
    
    # Create dynamic schema with defaults
    class DynamicReplyDetails(BaseModel):
        recipients: str = Field(
            default=default_recipients,
            description=f"Recipients (comma-separated, default: {default_recipients})",
        )
        content: str = Field(
            default="",
            description="Your reply content"
        )
        send_immediately: bool = Field(
            default=False,
            description="Send immediately (True) or save as draft (False)"
        )
    
    # Elicit reply details from user
    reply_details = await ctx.elicit(
        f"Replying to: '{thread['subject']}'",
        DynamicReplyDetails
    )
    
    # Handle elicitation response
    if hasattr(reply_details, 'action'):
        if reply_details.action == "cancel":
            return {"status": "cancelled", "message": "Reply cancelled by user"}
        elif reply_details.action == "decline":
            return {"status": "declined", "message": "Reply declined by user"}
        elif reply_details.action == "accept":
            # Process accepted reply
            data = reply_details.data
            recipients = [r.strip() for r in data.recipients.split(",") if r.strip()]
            
            # Simulate sending or saving
            if data.send_immediately:
                return {
                    "status": "sent",
                    "thread_id": thread_id,
                    "recipients": recipients,
                    "content": data.content,
                    "message": f"Reply sent to {len(recipients)} recipient(s)"
                }
            else:
                return {
                    "status": "draft_saved",
                    "thread_id": thread_id,
                    "recipients": recipients,
                    "content": data.content,
                    "message": "Reply saved as draft"
                }
    
    # Direct response (no action field)
    recipients = [r.strip() for r in reply_details.recipients.split(",") if r.strip()]
    
    if reply_details.send_immediately:
        return {
            "status": "sent",
            "thread_id": thread_id,
            "recipients": recipients,
            "content": reply_details.content,
            "message": f"Reply sent to {len(recipients)} recipient(s)"
        }
    else:
        return {
            "status": "draft_saved",
            "thread_id": thread_id,
            "recipients": recipients,
            "content": reply_details.content,
            "message": "Reply saved as draft"
        }

# ==================== Main Entry Point ====================

if __name__ == "__main__":
    # For standalone testing, get the underlying FastMCP instance
    mcp.get_mcp_instance().run()