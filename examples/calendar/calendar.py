"""
Calendar service implementation using MCPW pattern.

This service provides calendar management capabilities including:
- Viewing events by day, week, or specific dates
- Searching events by title, location, attendees, or description
- Creating, rescheduling, and canceling events with user interaction

The service uses relative resource paths that are automatically
prefixed by the router when mounted.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastmcp import Context
from pydantic import BaseModel, Field

from src.mcp_w.mcpw import MCPWService

# ==================== Constants ====================

SERVICE_NAME = "Calendar Service"
SERVICE_INSTRUCTIONS = """Calendar management service with event viewing, search, and scheduling capabilities.

RESOURCES:
- /today - Today's events
- /week - This week's events  
- /calendars - List of available calendars
- /event/{event_id} - Specific event details
- /calendar/{calendar_id} - Specific calendar info
- /date/{date} - Events for a specific date

ACTIONS:
- create_event - Create a new calendar event
- reschedule_event - Reschedule an existing event
- cancel_event - Cancel an event

USAGE:
1. Access resources to see events (e.g., /today, /week)
2. Use search_resources to find events by title, attendee, or location
3. Use invoke_action with 'create_event', 'reschedule_event', or 'cancel_event'"""

# Error messages
ERROR_EVENT_NOT_FOUND = "Event '{event_id}' not found"
ERROR_CALENDAR_NOT_FOUND = "Calendar '{calendar_id}' not found"
ERROR_UNKNOWN_ACTION = "Unknown action: {action}"

# ==================== Data Models ====================

class EventDetails(BaseModel):
    """Schema for creating new events."""
    title: str = Field(description="Event title")
    start_time: str = Field(description="Start time (ISO format, e.g., 2024-01-15T14:00:00Z)")
    end_time: str = Field(description="End time (ISO format)")
    location: str = Field(default="", description="Event location")
    attendees: str = Field(default="", description="Attendees (comma-separated emails)")
    description: str = Field(default="", description="Event description")


class RescheduleDetails(BaseModel):
    """Schema for rescheduling existing events."""
    new_start_time: str = Field(description="New start time (ISO format)")
    new_end_time: str = Field(description="New end time (ISO format)")
    notify_attendees: bool = Field(description="Send notifications to attendees")


# ==================== Sample Data ====================
# In a real implementation, this would come from a calendar API

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
        "attendees": ["manager@company.com", "product@company.com", "client@external.com"],
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
]

SAMPLE_CALENDARS = [
    {
        "calendar_id": "cal_personal",
        "name": "Personal",
        "color": "#4285f4",
        "type": "personal",
    },
    {
        "calendar_id": "cal_work",
        "name": "Work",
        "color": "#34a853",
        "type": "work",
    },
]

# ==================== Service Setup ====================

mcp = MCPWService(SERVICE_NAME, instructions=SERVICE_INSTRUCTIONS)

# ==================== Resource Handlers ====================

@mcp.resource("/today")
async def get_today_events() -> Dict:
    """
    Get today's calendar events.
    
    Returns all events scheduled for the current date.
    """
    # In production, filter by actual date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Mock: return first two events
    today_events = SAMPLE_EVENTS[:2]
    
    return {
        "date": today,
        "event_count": len(today_events),
        "events": today_events
    }


@mcp.resource("/week")
async def get_week_events() -> Dict:
    """
    Get this week's calendar events.
    
    Returns all events for the current week (Monday to Sunday).
    """
    # Calculate week boundaries
    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Mock: return all sample events
    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "event_count": len(SAMPLE_EVENTS),
        "events": SAMPLE_EVENTS
    }


@mcp.resource("/calendars")
async def get_calendars_resource() -> Dict:
    """
    Get list of available calendars.
    
    Returns all calendars the user has access to.
    """
    return {
        "calendar_count": len(SAMPLE_CALENDARS),
        "calendars": SAMPLE_CALENDARS
    }


@mcp.resource("/event/{event_id}")
async def get_event_resource(event_id: str) -> Dict:
    """
    Get detailed information about a specific event.
    
    Args:
        event_id: The event ID to retrieve
        
    Returns:
        Complete event details or error if not found
    """
    event = next(
        (e for e in SAMPLE_EVENTS if e["event_id"] == event_id),
        None
    )
    
    if not event:
        return {"error": ERROR_EVENT_NOT_FOUND.format(event_id=event_id)}
    
    return event


@mcp.resource("/calendar/{calendar_id}")
async def get_calendar_resource(calendar_id: str) -> Dict:
    """
    Get information about a specific calendar.
    
    Args:
        calendar_id: The calendar ID to retrieve
        
    Returns:
        Calendar details with event count
    """
    calendar = next(
        (c for c in SAMPLE_CALENDARS if c["calendar_id"] == calendar_id),
        None
    )
    
    if not calendar:
        return {"error": ERROR_CALENDAR_NOT_FOUND.format(calendar_id=calendar_id)}
    
    # Count events for this calendar (mock)
    calendar_events = [
        e for e in SAMPLE_EVENTS 
        if calendar["type"] == "work"  # Simplified logic
    ]
    
    return {
        **calendar,
        "event_count": len(calendar_events),
        "events": calendar_events
    }

# ==================== Tool Implementations ====================

@mcp.tool
async def search_resources(query: str) -> List[str]:
    """
    Search calendar events by title, location, attendees, or description.
    
    Searches are case-insensitive and match partial strings.
    
    Args:
        query: Search string to match against event properties
        
    Returns:
        List of relative resource paths for matching events
        
    Example:
        >>> await search_resources("standup")
        ["/event/evt_001"]
    """
    query_lower = query.lower()
    matching_events = []
    
    for event in SAMPLE_EVENTS:
        # Check title
        if query_lower in event["title"].lower():
            matching_events.append(f"/event/{event['event_id']}")
            continue
        
        # Check location
        if query_lower in event.get("location", "").lower():
            matching_events.append(f"/event/{event['event_id']}")
            continue
        
        # Check attendees
        for attendee in event.get("attendees", []):
            if query_lower in attendee.lower():
                matching_events.append(f"/event/{event['event_id']}")
                break
        
        # Check description
        if query_lower in event.get("description", "").lower():
            matching_events.append(f"/event/{event['event_id']}")
    
    return matching_events


@mcp.tool
async def invoke_action(action: str, resource_id: str, ctx: Context) -> Dict:
    """
    Perform actions on calendar resources.
    
    Supported actions:
    - create_event: Create a new calendar event
    - reschedule_event: Reschedule an existing event
    - cancel_event: Cancel an event
    
    Args:
        action: Action to perform
        resource_id: Full resource URI (e.g., "mcpweb://calendar/event/001")
        ctx: Context for user interaction
        
    Returns:
        Action result or error message
    """
    action_handlers = {
        "create_event": _handle_create_event,
        "reschedule_event": _handle_reschedule_event,
        "cancel_event": _handle_cancel_event,
    }
    
    handler = action_handlers.get(action)
    if handler:
        return await handler(ctx, resource_id)
    else:
        return {"error": ERROR_UNKNOWN_ACTION.format(action=action)}

# ==================== Action Handlers ====================

async def _handle_create_event(ctx: Context, resource_id: str) -> Dict:
    """
    Create a new calendar event with user elicitation.
    
    Args:
        ctx: Context for elicitation
        resource_id: Resource URI (not used for creation)
        
    Returns:
        Created event details
    """
    # Elicit event details from user
    event_data = await ctx.elicit(
        "Create a new calendar event",
        EventDetails
    )
    
    # Handle elicitation response
    if hasattr(event_data, 'action'):
        if event_data.action in ["cancel", "decline"]:
            return {
                "status": "cancelled",
                "message": "Event creation cancelled by user"
            }
        event_data = event_data.data
    
    # Parse attendees
    attendees = [
        a.strip() for a in event_data.attendees.split(",") 
        if a.strip()
    ] if event_data.attendees else []
    
    # Create new event (mock)
    new_event_id = f"evt_{datetime.now().timestamp():.0f}"
    
    return {
        "status": "created",
        "event": {
            "event_id": new_event_id,
            "title": event_data.title,
            "start_time": event_data.start_time,
            "end_time": event_data.end_time,
            "location": event_data.location,
            "attendees": attendees,
            "description": event_data.description,
        },
        "message": f"Event '{event_data.title}' created successfully"
    }


async def _handle_reschedule_event(ctx: Context, resource_id: str) -> Dict:
    """
    Reschedule an existing event with user elicitation.
    
    Args:
        ctx: Context for elicitation
        resource_id: Full resource URI of the event
        
    Returns:
        Rescheduling result
    """
    # Extract event ID from resource URI
    event_id = resource_id.split("/")[-1]
    
    # Find the event
    event = next(
        (e for e in SAMPLE_EVENTS if e["event_id"] == event_id),
        None
    )
    
    if not event:
        return {"error": ERROR_EVENT_NOT_FOUND.format(event_id=event_id)}
    
    # Elicit new schedule from user
    reschedule_data = await ctx.elicit(
        f"Reschedule event '{event['title']}'",
        RescheduleDetails
    )
    
    # Handle elicitation response
    if hasattr(reschedule_data, 'action'):
        if reschedule_data.action in ["cancel", "decline"]:
            return {
                "status": "cancelled",
                "message": "Rescheduling cancelled by user"
            }
        reschedule_data = reschedule_data.data
    
    # Process rescheduling (mock)
    notification_message = (
        "Attendees notified" if reschedule_data.notify_attendees 
        else "Attendees not notified"
    )
    
    return {
        "status": "rescheduled",
        "event_id": event_id,
        "title": event["title"],
        "old_time": {
            "start": event["start_time"],
            "end": event["end_time"]
        },
        "new_time": {
            "start": reschedule_data.new_start_time,
            "end": reschedule_data.new_end_time
        },
        "message": f"Event rescheduled. {notification_message}"
    }


async def _handle_cancel_event(ctx: Context, resource_id: str) -> Dict:
    """
    Cancel an event.
    
    Args:
        ctx: Context (not used for cancellation)
        resource_id: Full resource URI of the event
        
    Returns:
        Cancellation result
    """
    # Extract event ID from resource URI
    event_id = resource_id.split("/")[-1]
    
    # Find the event
    event = next(
        (e for e in SAMPLE_EVENTS if e["event_id"] == event_id),
        None
    )
    
    if not event:
        return {"error": ERROR_EVENT_NOT_FOUND.format(event_id=event_id)}
    
    # Cancel event (mock)
    return {
        "status": "cancelled",
        "event_id": event_id,
        "title": event["title"],
        "cancelled_time": event["start_time"],
        "attendees_notified": event.get("attendees", []),
        "message": f"Event '{event['title']}' has been cancelled"
    }

# ==================== Main Entry Point ====================

if __name__ == "__main__":
    # For standalone testing, get the underlying FastMCP instance
    mcp.get_mcp_instance().run()