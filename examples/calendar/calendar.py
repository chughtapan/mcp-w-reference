"""
Calendar service implementation for MCP-W.

This module provides calendar management capabilities through the four core operations:
LIST, GET, SEARCH, and INVOKE.

This is a standalone FastMCP service that runs independently via:
    fastmcp run -t streamable-http examples.calendar.calendar --port 3002
"""

from datetime import datetime, timedelta

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

# Sample calendar data (in a real implementation, this would come from a calendar API)
SAMPLE_EVENTS = [
    {
        "event_id": "evt_001",
        "title": "Team Standup",
        "start_time": "2024-01-15T09:00:00Z",
        "end_time": "2024-01-15T09:30:00Z",
        "location": "Conference Room A",
        "attendees": ["alice@company.com", "bob@company.com", "charlie@company.com"],
        "recurring": "daily",
        "description": "Daily team synchronization meeting",
    },
    {
        "event_id": "evt_002",
        "title": "Product Demo",
        "start_time": "2024-01-16T14:00:00Z",
        "end_time": "2024-01-16T15:00:00Z",
        "location": "Virtual - Zoom",
        "attendees": [
            "manager@company.com",
            "product@company.com",
            "client@external.com",
        ],
        "recurring": None,
        "description": "Q1 product features demonstration for key stakeholders",
    },
    {
        "event_id": "evt_003",
        "title": "Lunch with Sarah",
        "start_time": "2024-01-17T12:00:00Z",
        "end_time": "2024-01-17T13:00:00Z",
        "location": "Cafe Bistro",
        "attendees": ["user@company.com", "sarah@company.com"],
        "recurring": None,
        "description": "Monthly catch-up lunch",
    },
    {
        "event_id": "evt_004",
        "title": "Sprint Planning",
        "start_time": "2024-01-18T10:00:00Z",
        "end_time": "2024-01-18T12:00:00Z",
        "location": "Conference Room B",
        "attendees": ["dev-team@company.com"],
        "recurring": "biweekly",
        "description": "Sprint planning and backlog grooming session",
    },
]

# Sample calendar views
SAMPLE_CALENDARS = [
    {
        "calendar_id": "primary",
        "name": "Primary Calendar",
        "color": "#4285F4",
        "is_primary": True,
    },
    {
        "calendar_id": "team",
        "name": "Team Calendar",
        "color": "#0F9D58",
        "is_primary": False,
    },
]


class EventDetails(BaseModel):
    """Schema for collecting event details through elicitation"""

    title: str = Field(description="Event title")
    start_time: str = Field(
        description="Start time (ISO format, e.g., 2024-01-20T14:00:00Z)"
    )
    end_time: str = Field(
        description="End time (ISO format, e.g., 2024-01-20T15:00:00Z)"
    )
    location: str = Field(description="Location (optional)")
    attendees: str = Field(description="Attendees (comma-separated emails, optional)")
    description: str = Field(description="Event description (optional)")


class RescheduleDetails(BaseModel):
    """Schema for rescheduling events"""

    new_start_time: str = Field(description="New start time (ISO format)")
    new_end_time: str = Field(description="New end time (ISO format)")
    notify_attendees: bool = Field(description="Send notifications to attendees")


# Create FastMCP server instance
mcp = FastMCP(
    "Calendar Service",
    instructions="Calendar management service with event viewing, search, and scheduling capabilities. Resources are available natively via MCP resource system.",
)


@mcp.tool
async def list_resources() -> dict:
    """
    LIST operation - return calendar service capabilities.

    Returns dict with available resources, actions, and usage instructions.
    """
    # Get actual event IDs for specific resource URIs
    event_resources = [
        f"calendar://event/{event['event_id']}" for event in SAMPLE_EVENTS
    ]

    calendar_resources = [
        f"calendar://calendar/{cal['calendar_id']}" for cal in SAMPLE_CALENDARS
    ]

    return {
        "resources": {
            "static": ["calendar://today", "calendar://week", "calendar://calendars"],
            "dynamic": event_resources + calendar_resources,
            "patterns": [
                "calendar://event/{event_id}",
                "calendar://calendar/{calendar_id}",
                "calendar://date/{date}",
            ],
        },
        "actions": ["create_event", "reschedule_event", "cancel_event"],
        "capabilities": [
            "list_resources",
            "get_resource",
            "search_resources",
            "invoke_action",
        ],
        "instructions": {
            "usage": "Calendar service for managing events and schedules",
            "workflow": [
                "Access 'calendar://today' resource to see today's events",
                "Access 'calendar://week' resource to see this week's events",
                "Access 'calendar://calendars' to see all available calendars",
                "Use 'search_resources' to find events by title, attendee, or location",
                "Access 'calendar://event/{event_id}' resource to view event details",
                "Use 'invoke_action create_event' to create a new event",
                "Use 'invoke_action reschedule_event {event_id}' to reschedule an event",
                "Use 'invoke_action cancel_event {event_id}' to cancel an event",
            ],
            "note": "Resources can be accessed directly via MCP's native resource system or through the get_resource tool",
        },
    }


# Register MCP native resources
@mcp.resource("calendar://today")
async def get_today_resource() -> dict:
    """
    Get today's calendar events.

    Returns:
        Dict with today's events
    """
    today = datetime(2024, 1, 15)  # Fixed date for demo
    today_events = []

    for event in SAMPLE_EVENTS:
        event_date = datetime.fromisoformat(event["start_time"].replace("Z", "+00:00"))
        if event_date.date() == today.date():
            today_events.append(
                {
                    "event_id": event["event_id"],
                    "title": event["title"],
                    "start_time": event["start_time"],
                    "end_time": event["end_time"],
                    "location": event["location"],
                    "attendees": event["attendees"],
                }
            )

    return {
        "date": today.strftime("%Y-%m-%d"),
        "event_count": len(today_events),
        "events": today_events,
    }


@mcp.resource("calendar://week")
async def get_week_resource() -> dict:
    """
    Get this week's calendar events.

    Returns:
        Dict with week's events
    """
    week_start = datetime(2024, 1, 15)  # Monday of the week
    week_end = week_start + timedelta(days=6)
    week_events = []

    for event in SAMPLE_EVENTS:
        event_date = datetime.fromisoformat(event["start_time"].replace("Z", "+00:00"))
        # Compare only the dates to avoid timezone issues
        if week_start.date() <= event_date.date() <= week_end.date():
            week_events.append(
                {
                    "event_id": event["event_id"],
                    "title": event["title"],
                    "start_time": event["start_time"],
                    "end_time": event["end_time"],
                    "location": event["location"],
                    "day_of_week": event_date.strftime("%A"),
                }
            )

    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "event_count": len(week_events),
        "events": week_events,
    }


@mcp.resource("calendar://calendars")
async def get_calendars_resource() -> dict:
    """
    Get all available calendars.

    Returns:
        Dict with calendar list
    """
    return {"calendar_count": len(SAMPLE_CALENDARS), "calendars": SAMPLE_CALENDARS}


@mcp.resource("calendar://event/{event_id}")
async def get_event_resource(event_id: str) -> dict:
    """
    Get detailed information about a specific calendar event.

    Args:
        event_id: The event ID to retrieve

    Returns:
        Dict with event details
    """
    # Find the event
    event = next((e for e in SAMPLE_EVENTS if e["event_id"] == event_id), None)
    if not event:
        return {"error": f"Event '{event_id}' not found"}

    return event


@mcp.resource("calendar://calendar/{calendar_id}")
async def get_calendar_resource(calendar_id: str) -> dict:
    """
    Get information about a specific calendar.

    Args:
        calendar_id: The calendar ID to retrieve

    Returns:
        Dict with calendar details and its events
    """
    # Find the calendar
    calendar = next(
        (c for c in SAMPLE_CALENDARS if c["calendar_id"] == calendar_id), None
    )
    if not calendar:
        return {"error": f"Calendar '{calendar_id}' not found"}

    # Get events for this calendar (for demo, we'll show all events)
    calendar_events = [
        {
            "event_id": event["event_id"],
            "title": event["title"],
            "start_time": event["start_time"],
            "end_time": event["end_time"],
        }
        for event in SAMPLE_EVENTS
    ]

    return {**calendar, "events": calendar_events}


@mcp.tool
async def get_resource(resource_uri: str, ctx: Context) -> str:
    """
    GET operation - retrieve calendar resources by URI.

    This tool provides access to calendar resources. In practice, most LLMs will
    directly access the resources via MCP's native resource system, but this
    tool ensures compatibility with the MCP-W pattern.

    Args:
        resource_uri: The calendar resource URI to retrieve
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
    SEARCH operation - find calendar events using natural language queries.

    Searches through events by title, location, and attendees.

    Args:
        query: Natural language search query

    Returns:
        List of matching event URIs
    """
    query_lower = query.lower()
    matching_events = []

    for event in SAMPLE_EVENTS:
        # Search in title
        if query_lower in event["title"].lower():
            matching_events.append(f"calendar://event/{event['event_id']}")
            continue

        # Search in location
        if query_lower in event["location"].lower():
            matching_events.append(f"calendar://event/{event['event_id']}")
            continue

        # Search in attendees
        for attendee in event["attendees"]:
            if query_lower in attendee.lower():
                matching_events.append(f"calendar://event/{event['event_id']}")
                break

        # Search in description
        if query_lower in event["description"].lower():
            matching_events.append(f"calendar://event/{event['event_id']}")

    return matching_events


@mcp.tool
async def invoke_action(ctx: Context, action: str, resource_id: str = "") -> dict | str:
    """
    INVOKE operation - perform calendar actions with user interaction.

    Handles:
    - create_event - Create a new calendar event with elicitation
    - reschedule_event - Reschedule an existing event
    - cancel_event - Cancel an event

    Args:
        ctx: FastMCP context (automatically injected)
        action: The action to perform
        resource_id: The event ID for actions that require it (optional)

    Returns:
        Action result as dict or string
    """
    if action == "create_event":
        return await _handle_create_event(ctx)
    elif action == "reschedule_event":
        if not resource_id:
            raise ValueError("reschedule_event requires an event_id")
        return await _handle_reschedule_event(ctx, resource_id)
    elif action == "cancel_event":
        if not resource_id:
            raise ValueError("cancel_event requires an event_id")
        return await _handle_cancel_event(ctx, resource_id)
    else:
        raise ValueError(
            f"Unknown action: {action}. Available: create_event, reschedule_event, cancel_event"
        )


async def _handle_create_event(ctx: Context) -> dict | str:
    """
    Handle creating a new calendar event with elicitation.

    Args:
        ctx: FastMCP context for elicitation

    Returns:
        JSON string with creation result or error
    """
    # Use elicitation to get event details from user
    event_details = await ctx.elicit("Create new calendar event", EventDetails)

    # Handle user response
    if event_details.action == "cancel":
        return "Event creation cancelled by user"

    if event_details.action == "decline":
        return "Event creation declined by user"

    if event_details.action == "accept":
        data = event_details.data
        attendees = (
            [a.strip() for a in data.attendees.split(",") if a.strip()]
            if data.attendees
            else []
        )

        # Create new event (in real implementation, this would call calendar API)
        new_event_id = f"evt_{len(SAMPLE_EVENTS) + 1:03d}"

        result_message = f"Event '{data.title}' created successfully"

        # Return structured result data
        return {
            "result": result_message,
            "event_id": new_event_id,
            "title": data.title,
            "start_time": data.start_time,
            "end_time": data.end_time,
            "location": data.location,
            "attendees": attendees,
            "description": data.description,
        }

    return f"Unknown elicitation action: {event_details.action}"


async def _handle_reschedule_event(ctx: Context, event_id: str) -> dict | str:
    """
    Handle rescheduling a calendar event with elicitation.

    Args:
        ctx: FastMCP context for elicitation
        event_id: The event ID to reschedule

    Returns:
        JSON string with reschedule result or error
    """
    # Find the event
    event = next((e for e in SAMPLE_EVENTS if e["event_id"] == event_id), None)
    if not event:
        return f"Event '{event_id}' not found"

    # Use elicitation to get new time from user
    reschedule_details = await ctx.elicit(
        f"Reschedule event: '{event['title']}' (currently {event['start_time']} to {event['end_time']})",
        RescheduleDetails,
    )

    # Handle user response
    if reschedule_details.action == "cancel":
        return "Reschedule cancelled by user"

    if reschedule_details.action == "decline":
        return "Reschedule declined by user"

    if reschedule_details.action == "accept":
        data = reschedule_details.data

        # Simulate rescheduling
        notification_msg = (
            " with notifications" if data.notify_attendees else " without notifications"
        )
        result_message = f"Event '{event['title']}' rescheduled to {data.new_start_time}{notification_msg}"

        # Return structured result data
        return {
            "result": result_message,
            "event_id": event_id,
            "title": event["title"],
            "old_start_time": event["start_time"],
            "old_end_time": event["end_time"],
            "new_start_time": data.new_start_time,
            "new_end_time": data.new_end_time,
            "notified_attendees": data.notify_attendees,
        }

    return f"Unknown elicitation action: {reschedule_details.action}"


async def _handle_cancel_event(ctx: Context, event_id: str) -> dict | str:
    """
    Handle cancelling a calendar event.

    Args:
        ctx: FastMCP context
        event_id: The event ID to cancel

    Returns:
        JSON string with cancellation result or error
    """
    # Find the event
    event = next((e for e in SAMPLE_EVENTS if e["event_id"] == event_id), None)
    if not event:
        return f"Event '{event_id}' not found"

    # For cancellation, we might want a simple confirmation
    # In a real implementation, you might use elicitation for confirmation

    # Simulate cancellation
    result_message = f"Event '{event['title']}' has been cancelled"

    # Return structured result data
    return {
        "result": result_message,
        "event_id": event_id,
        "title": event["title"],
        "cancelled_time": event["start_time"],
        "attendees_notified": event["attendees"],
    }


# Run the FastMCP server when this module is executed directly
if __name__ == "__main__":
    mcp.run()
