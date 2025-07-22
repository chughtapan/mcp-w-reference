"""
Email service implementation for MCP-W.

This module provides email management capabilities through the four core operations:
LIST, GET, SEARCH, and INVOKE.

This is a standalone FastMCP service that runs independently via:
    fastmcp run -t streamable-http src.mcp_w.services.email --port 3001
"""

from fastmcp import Context, FastMCP

# No need to import MCP types - FastMCP handles conversion automatically
from pydantic import BaseModel, Field

# Sample email data (in a real implementation, this would come from an email API)
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

# Sample thread details (in a real implementation, this would be fetched from email API)
SAMPLE_THREAD_DETAILS = {
    "thread_001": {
        "content": "Can we schedule a meeting for next week to discuss the project updates? I'd like to review the latest milestones."
    },
    "thread_002": {
        "content": "Please review the Q1 budget numbers and let me know if you have any questions. The finance team needs feedback by Friday."
    },
}


class ReplyDetails(BaseModel):
    """Schema for collecting reply details through elicitation"""

    recipients: str = Field(description="Recipients (comma-separated)")
    content: str = Field(default="", description="Reply content")
    send_immediately: bool = Field(
        default=False, description="Send now or save as draft"
    )


# Create FastMCP server instance
mcp = FastMCP(
    "Email Service",
    instructions="Email management service with thread, search, and reply capabilities. Resources are available natively via MCP resource system.",
)


@mcp.tool
async def list_resources() -> dict:
    """
    LIST operation - return email service capabilities.

    Returns dict with available resources, actions, and usage instructions.
    """
    # Get actual thread IDs for specific resource URIs
    thread_resources = [
        f"email://thread/{thread['thread_id']}" for thread in SAMPLE_THREADS
    ]

    return {
        "resources": {
            "static": ["email://inbox"],
            "dynamic": thread_resources,
            "patterns": ["email://thread/{thread_id}"],
        },
        "actions": ["reply_thread"],
        "capabilities": [
            "list_resources",
            "get_resource",
            "search_resources",
            "invoke_action",
        ],
        "instructions": {
            "usage": "Email service for managing email threads and communications",
            "workflow": [
                "Access 'email://inbox' resource to see all email threads",
                "Use 'search_resources' to find specific threads by subject or participant",
                "Access 'email://thread/{thread_id}' resource to view thread details",
                "Use 'invoke_action reply_thread {thread_id}' to reply to a thread",
            ],
            "note": "Resources can be accessed directly via MCP's native resource system or through the get_resource tool",
        },
    }


# Register MCP native resources
@mcp.resource("email://inbox")
async def get_inbox_resource() -> dict:
    """
    Get all email threads from inbox.

    Returns:
        Dict with thread listing
    """
    threads_data = []
    for thread in SAMPLE_THREADS:
        threads_data.append(
            {
                "thread_id": thread["thread_id"],
                "subject": thread["subject"],
                "participants": thread["participants"],
                "last_updated": thread["last_updated"],
                "unread_count": thread["unread_count"],
            }
        )

    return {"inbox": {"total_threads": len(threads_data), "threads": threads_data}}


@mcp.resource("email://thread/{thread_id}")
async def get_thread_resource(thread_id: str) -> dict:
    """
    Get detailed information about a specific email thread.

    Args:
        thread_id: The thread ID to retrieve

    Returns:
        Dict with thread details
    """
    # Find the thread
    thread = next((t for t in SAMPLE_THREADS if t["thread_id"] == thread_id), None)
    if not thread:
        return {"error": f"Thread '{thread_id}' not found"}

    # Get thread details
    thread_details = SAMPLE_THREAD_DETAILS.get(
        thread_id, {"content": "No content available"}
    )

    return {
        "thread_id": thread["thread_id"],
        "subject": thread["subject"],
        "participants": thread["participants"],
        "last_updated": thread["last_updated"],
        "unread_count": thread["unread_count"],
        "content": thread_details["content"],
    }


@mcp.tool
async def get_resource(resource_uri: str, ctx: Context) -> str:
    """
    GET operation - retrieve email resources by URI.

    This tool provides access to email resources. In practice, most LLMs will
    directly access the resources via MCP's native resource system, but this
    tool ensures compatibility with the MCP-W pattern.

    Args:
        resource_uri: The email resource URI to retrieve
        ctx: FastMCP context (automatically injected)

    Returns:
        Resource data as string or error message
    """
    try:
        # Use the context to access the resource through MCP's native system
        resource_contents = await ctx.read_resource(resource_uri)

        if not resource_contents:
            raise ValueError(f"Resource not found: {resource_uri}")

        # The first content item contains our data
        # FastMCP returns ReadResourceContents object with 'content' attribute
        first_content = resource_contents[0]

        # The content attribute contains the actual data
        if hasattr(first_content, "content"):
            return first_content.content
        elif hasattr(first_content, "text"):
            return first_content.text
        elif isinstance(first_content, str):
            return first_content
        else:
            # If it's some other type, try to convert to string
            return str(first_content)
    except Exception as e:
        raise ValueError(f"Error retrieving resource '{resource_uri}': {str(e)}")


@mcp.tool
async def search_resources(query: str) -> list[str]:
    """
    SEARCH operation - find email threads using natural language queries.

    Searches through email threads by subject and participants.

    Args:
        query: Natural language search query

    Returns:
        List of matching thread URIs
    """
    query_lower = query.lower()
    matching_threads = []

    for thread in SAMPLE_THREADS:
        # Search in subject
        if query_lower in thread["subject"].lower():
            matching_threads.append(f"email://thread/{thread['thread_id']}")
            continue

        # Search in participants
        for participant in thread["participants"]:
            if query_lower in participant.lower():
                matching_threads.append(f"email://thread/{thread['thread_id']}")
                break

    return matching_threads


@mcp.tool
async def invoke_action(ctx: Context, action: str, resource_id: str) -> dict | str:
    """
    INVOKE operation - perform email actions with user interaction.

    Handles:
    - reply_thread - Reply to an email thread with elicitation

    Args:
        ctx: FastMCP context (automatically injected)
        action: The action to perform
        resource_id: The thread ID to perform action on

    Returns:
        Action result as dict or string
    """
    if action == "reply_thread":
        return await _handle_reply_thread(ctx, resource_id)
    else:
        raise ValueError(f"Unknown action: {action}. Available: reply_thread")


async def _handle_reply_thread(ctx: Context, thread_id: str) -> dict | str:
    """
    Handle replying to an email thread with elicitation.

    Args:
        ctx: FastMCP context for elicitation
        thread_id: The thread ID to reply to

    Returns:
        JSON string with reply result or error
    """
    # Find the thread
    thread = next((t for t in SAMPLE_THREADS if t["thread_id"] == thread_id), None)
    if not thread:
        return f"Thread '{thread_id}' not found"

    # Prepare smart defaults
    default_recipients = ", ".join(thread["participants"])

    # Create dynamic schema with defaults
    class DynamicReplyDetails(BaseModel):
        recipients: str = Field(
            default=default_recipients,
            description=f"Recipients (comma-separated, default: {default_recipients})",
        )
        content: str = Field(default="", description="Your reply content")
        send_immediately: bool = Field(
            default=False, description="Send immediately or save as draft"
        )

    # Use the injected context to elicit reply details from user
    reply_details = await ctx.elicit(
        f"Replying to: '{thread['subject']}'", DynamicReplyDetails
    )

    # Handle user response
    if reply_details.action == "cancel":
        return "Reply cancelled by user"

    if reply_details.action == "decline":
        return "Reply declined by user"

    if reply_details.action == "accept":
        data = reply_details.data
        recipients = [r.strip() for r in data.recipients.split(",") if r.strip()]

        # Simulate sending or saving reply
        if data.send_immediately:
            result_message = (
                f"Reply sent to {', '.join(recipients)}: {data.content[:50]}..."
            )
        else:
            result_message = f"Reply saved as draft for {', '.join(recipients)}: {data.content[:50]}..."

        # Return structured result data
        return {
            "result": result_message,
            "recipients": recipients,
            "content": data.content,
            "sent_immediately": data.send_immediately,
        }

    return f"Unknown elicitation action: {reply_details.action}"


# Run the FastMCP server when this module is executed directly
if __name__ == "__main__":
    mcp.run()
