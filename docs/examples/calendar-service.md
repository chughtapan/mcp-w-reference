# Calendar Service Example

This example demonstrates a RESTful MCP-compliant calendar service with event management, different views, and scheduling capabilities. It showcases different resource patterns and cross-service integration possibilities.

## Service Overview

Our calendar service provides:
- Multiple calendar views (today, week, month)
- Event management (create, reschedule, cancel)
- Participant management
- Search across events

## Complete Implementation

```python
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from mcp import MCP, Context

# Service setup
mcp = MCP(
    name="Calendar Service",
    instructions="""
    Calendar service for managing events and schedules.
    
    Resources:
    - /today: Today's events
    - /week: This week's events
    - /month: This month's events
    - /date/{yyyy}/{mm}/{dd}: Events for specific date
    - /event/{event_id}: Specific event details
    - /event/{event_id}/reschedule: Reschedule an event
    - /event/{event_id}/cancel: Cancel an event
    - /create: Create a new event
    
    Search: Find events by title, participant, or date range.
    Returns event URIs matching the query.
    """
)

# Data models
class CalendarEvent:
    def __init__(
        self,
        event_id: str,
        title: str,
        date: date,
        time: str,
        duration_minutes: int,
        participants: List[str],
        location: Optional[str] = None,
        description: Optional[str] = None
    ):
        self.event_id = event_id
        self.title = title
        self.date = date
        self.time = time
        self.duration_minutes = duration_minutes
        self.participants = participants
        self.location = location
        self.description = description
        self.created_at = datetime.now()
        self.status = "scheduled"

# Sample data
EVENTS = {
    "evt_001": CalendarEvent(
        "evt_001",
        "Team Standup",
        date.today(),
        "09:00",
        30,
        ["team@example.com"],
        location="Conference Room A",
        description="Daily team sync"
    ),
    "evt_002": CalendarEvent(
        "evt_002",
        "Budget Review",
        date.today(),
        "14:00",
        60,
        ["cfo@example.com", "finance@example.com"],
        location="Zoom",
        description="Q1 budget review meeting"
    ),
    "evt_003": CalendarEvent(
        "evt_003",
        "Project Planning",
        date.today() + timedelta(days=1),
        "10:00",
        90,
        ["pm@example.com", "dev@example.com", "design@example.com"],
        location="Main Office",
        description="Sprint planning for Project Alpha"
    ),
    "evt_004": CalendarEvent(
        "evt_004",
        "Client Demo",
        date.today() + timedelta(days=2),
        "15:00",
        45,
        ["sales@example.com", "client@external.com"],
        location="Client Office",
        description="Product demo for potential client"
    ),
    "evt_005": CalendarEvent(
        "evt_005",
        "Team Lunch",
        date.today() + timedelta(days=7),
        "12:00",
        90,
        ["team@example.com"],
        location="Local Restaurant"
    )
}

# Utility functions
def format_event(event: CalendarEvent) -> Dict[str, Any]:
    """Format event for API response"""
    return {
        "uri": f"/event/{event.event_id}",
        "title": event.title,
        "date": event.date.isoformat(),
        "time": event.time,
        "duration_minutes": event.duration_minutes,
        "participants": event.participants,
        "location": event.location,
        "status": event.status
    }

def get_events_for_date(target_date: date) -> List[CalendarEvent]:
    """Get all events for a specific date"""
    return [e for e in EVENTS.values() if e.date == target_date and e.status == "scheduled"]

def get_events_for_range(start_date: date, end_date: date) -> List[CalendarEvent]:
    """Get all events within a date range"""
    return [
        e for e in EVENTS.values()
        if start_date <= e.date <= end_date and e.status == "scheduled"
    ]

# Resource implementations

@mcp.resource("/today")
async def get_today() -> Dict[str, Any]:
    """Get today's calendar events"""
    today = date.today()
    events = get_events_for_date(today)
    
    return {
        "date": today.isoformat(),
        "day_name": today.strftime("%A"),
        "event_count": len(events),
        "events": [format_event(e) for e in sorted(events, key=lambda e: e.time)]
    }

@mcp.resource("/week")
async def get_week() -> Dict[str, Any]:
    """Get this week's calendar events"""
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    events = get_events_for_range(start_of_week, end_of_week)
    
    # Group by day
    events_by_day = {}
    for event in events:
        day_key = event.date.isoformat()
        if day_key not in events_by_day:
            events_by_day[day_key] = []
        events_by_day[day_key].append(format_event(event))
    
    return {
        "week_start": start_of_week.isoformat(),
        "week_end": end_of_week.isoformat(),
        "total_events": len(events),
        "events_by_day": events_by_day
    }

@mcp.resource("/month")
async def get_month() -> Dict[str, Any]:
    """Get this month's calendar events"""
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    
    # Calculate end of month
    if today.month == 12:
        end_of_month = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    events = get_events_for_range(start_of_month, end_of_month)
    
    return {
        "month": today.strftime("%B %Y"),
        "month_start": start_of_month.isoformat(),
        "month_end": end_of_month.isoformat(),
        "total_events": len(events),
        "events": [format_event(e) for e in sorted(events, key=lambda e: (e.date, e.time))]
    }

@mcp.resource("/date/{year}/{month}/{day}")
async def get_specific_date(year: int, month: int, day: int) -> Dict[str, Any]:
    """Get events for a specific date"""
    try:
        target_date = date(year, month, day)
    except ValueError:
        return {"error": f"Invalid date: {year}-{month}-{day}", "status": 400}
    
    events = get_events_for_date(target_date)
    
    return {
        "date": target_date.isoformat(),
        "day_name": target_date.strftime("%A"),
        "event_count": len(events),
        "events": [format_event(e) for e in sorted(events, key=lambda e: e.time)]
    }

@mcp.resource("/event/{event_id}")
async def get_event(event_id: str) -> Dict[str, Any]:
    """Get specific event details"""
    if event_id not in EVENTS:
        return {"error": f"Event {event_id} not found", "status": 404}
    
    event = EVENTS[event_id]
    
    return {
        "uri": f"/event/{event_id}",
        "title": event.title,
        "date": event.date.isoformat(),
        "time": event.time,
        "duration_minutes": event.duration_minutes,
        "participants": event.participants,
        "location": event.location,
        "description": event.description,
        "status": event.status,
        "created_at": event.created_at.isoformat(),
        "actions": [
            f"/event/{event_id}/reschedule",
            f"/event/{event_id}/cancel"
        ]
    }

@mcp.resource("/event/{event_id}/reschedule")
async def reschedule_event(event_id: str, ctx: Context) -> Dict[str, Any]:
    """Reschedule a calendar event"""
    if event_id not in EVENTS:
        return {"error": f"Event {event_id} not found", "status": 404}
    
    event = EVENTS[event_id]
    
    # Smart defaults based on current event
    tomorrow = date.today() + timedelta(days=1)
    
    class RescheduleSchema(BaseModel):
        new_date: str = Field(
            default=tomorrow.isoformat(),
            description="New date (YYYY-MM-DD)"
        )
        new_time: str = Field(
            default=event.time,
            description="New time (HH:MM)"
        )
        notify_participants: bool = Field(
            default=True,
            description="Send update to participants?"
        )
        reason: str = Field(
            default="",
            description="Reason for rescheduling (optional)"
        )
    
    reschedule_data = await ctx.prompt(
        f"Reschedule '{event.title}'",
        RescheduleSchema
    )
    
    # Update event
    event.date = date.fromisoformat(reschedule_data.new_date)
    event.time = reschedule_data.new_time
    
    return {
        "status": "rescheduled",
        "event_id": event_id,
        "new_date": reschedule_data.new_date,
        "new_time": reschedule_data.new_time,
        "participants_notified": reschedule_data.notify_participants
    }

@mcp.resource("/event/{event_id}/cancel")
async def cancel_event(event_id: str, ctx: Context) -> Dict[str, Any]:
    """Cancel a calendar event"""
    if event_id not in EVENTS:
        return {"error": f"Event {event_id} not found", "status": 404}
    
    event = EVENTS[event_id]
    
    class CancelSchema(BaseModel):
        confirm: bool = Field(
            description=f"Confirm cancellation of '{event.title}'?"
        )
        notify_participants: bool = Field(
            default=True,
            description="Send cancellation notice?"
        )
        reason: str = Field(
            default="",
            description="Cancellation reason (optional)"
        )
    
    cancel_data = await ctx.prompt(
        f"Cancel '{event.title}' on {event.date}?",
        CancelSchema
    )
    
    if not cancel_data.confirm:
        return {"status": "cancelled", "message": "Cancellation aborted"}
    
    # Cancel event
    event.status = "cancelled"
    
    return {
        "status": "cancelled",
        "event_id": event_id,
        "participants_notified": cancel_data.notify_participants
    }

@mcp.resource("/create")
async def create_event(ctx: Context) -> Dict[str, Any]:
    """Create a new calendar event"""
    class CreateEventSchema(BaseModel):
        title: str = Field(description="Event title")
        date: str = Field(
            default=date.today().isoformat(),
            description="Event date (YYYY-MM-DD)"
        )
        time: str = Field(
            default="09:00",
            description="Start time (HH:MM)"
        )
        duration_minutes: int = Field(
            default=60,
            description="Duration in minutes"
        )
        participants: str = Field(
            description="Participants (comma-separated emails)"
        )
        location: str = Field(
            default="",
            description="Location (optional)"
        )
        description: str = Field(
            default="",
            description="Event description (optional)"
        )
    
    event_data = await ctx.prompt("Create new event", CreateEventSchema)
    
    # Generate event ID
    event_id = f"evt_{len(EVENTS) + 1:03d}"
    
    # Create event
    new_event = CalendarEvent(
        event_id,
        event_data.title,
        date.fromisoformat(event_data.date),
        event_data.time,
        event_data.duration_minutes,
        event_data.participants.split(", "),
        location=event_data.location or None,
        description=event_data.description or None
    )
    
    EVENTS[event_id] = new_event
    
    return {
        "status": "created",
        "event_uri": f"/event/{event_id}",
        "title": event_data.title,
        "date": event_data.date,
        "time": event_data.time
    }

# Search implementation

@mcp.tool
async def search(
    query: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> List[str]:
    """
    Search calendar events by title, participant, or description.
    Optionally filter by date range.
    Returns list of event URIs.
    """
    query_lower = query.lower()
    matching_events = []
    
    # Parse date filters if provided
    start_date = date.fromisoformat(date_from) if date_from else date.min
    end_date = date.fromisoformat(date_to) if date_to else date.max
    
    for event_id, event in EVENTS.items():
        # Skip cancelled events
        if event.status != "scheduled":
            continue
            
        # Check date range
        if not (start_date <= event.date <= end_date):
            continue
        
        # Search in title
        if query_lower in event.title.lower():
            matching_events.append(f"/event/{event_id}")
            continue
        
        # Search in participants
        if any(query_lower in p.lower() for p in event.participants):
            matching_events.append(f"/event/{event_id}")
            continue
        
        # Search in location
        if event.location and query_lower in event.location.lower():
            matching_events.append(f"/event/{event_id}")
            continue
        
        # Search in description
        if event.description and query_lower in event.description.lower():
            matching_events.append(f"/event/{event_id}")
    
    return matching_events

# Run the service
if __name__ == "__main__":
    mcp.run()
```

## Testing the Service

### 1. Calendar Views
```python
# Today's events
today = await get_today()
assert today["date"] == date.today().isoformat()

# This week
week = await get_week()
assert "events_by_day" in week

# This month
month = await get_month()
assert month["month"] == date.today().strftime("%B %Y")

# Specific date
specific = await get_specific_date(2024, 3, 15)
assert specific["date"] == "2024-03-15"
```

### 2. Event Management
```python
# Get event details
event = await get_event("evt_001")
assert event["title"] == "Team Standup"
assert "/event/evt_001/reschedule" in event["actions"]

# Create new event
new_event = await create_event(test_context)
assert new_event["status"] == "created"
```

### 3. Search Functionality
```python
# Search by title
results = await search("standup")
assert "/event/evt_001" in results

# Search by participant
results = await search("cfo")
assert "/event/evt_002" in results

# Search with date range
results = await search("meeting", date_from="2024-03-01", date_to="2024-03-31")
```

## Usage Examples

### Daily Planning
```
# Check today's schedule
GET /today
→ Shows all events for today

# Look at specific event
GET /event/evt_002
→ Budget Review at 14:00

# Need to reschedule
POST /event/evt_002/reschedule
→ Prompts with smart defaults
```

### Weekly Overview
```
# View entire week
GET /week
→ Events grouped by day

# Find lunch meetings
FIND "lunch"
→ ["/event/evt_005"]

# Check details
GET /event/evt_005
→ Team Lunch next week
```

### Creating Events
```
# Create new meeting
POST /create
→ Interactive form for event details
→ Returns new event URI

# Invite participants from email
GET mcpweb://email/thread/123
→ Get participant list

POST /create
→ Paste participants from email thread
```

## Integration Patterns

### 1. Email to Calendar
```python
# From email service, extract meeting request
email_thread = await email_service.get_thread("thread_123")
participants = email_thread["participants"]
subject = email_thread["subject"]

# Create calendar event with email context
await create_event(ctx, defaults={
    "title": f"Meeting: {subject}",
    "participants": ", ".join(participants)
})
```

### 2. Task to Calendar
```python
# From task service, schedule time for task
task = await task_service.get_task("task_456")
deadline = task["due_date"]

# Create calendar reminder
await create_event(ctx, defaults={
    "title": f"Work on: {task['title']}",
    "date": deadline,
    "duration_minutes": 120
})
```

### 3. Calendar to Document
```python
# From calendar event, create meeting notes
event = await get_event("evt_001")

# Create document with event context
document_uri = await document_service.create(ctx, defaults={
    "title": f"Notes: {event['title']}",
    "content": f"Meeting on {event['date']}\nParticipants: {event['participants']}"
})
```

## Best Practices Demonstrated

1. **Multiple View Resources**
   - `/today` - Current day view
   - `/week` - Week view with grouping
   - `/month` - Month overview
   - `/date/{y}/{m}/{d}` - Arbitrary date

2. **Flexible Search**
   - Text search across multiple fields
   - Optional date range filtering
   - Excludes cancelled events

3. **Smart Action Defaults**
   - Reschedule defaults to tomorrow
   - Keeps same time when rescheduling
   - Notification options included

4. **Status Management**
   - Events have status (scheduled/cancelled)
   - Cancelled events excluded from views
   - Clear status in responses

5. **Cross-Service Design**
   - Participant lists compatible with email
   - Dates/times in standard formats
   - URIs enable linking between services

## Extension Ideas

1. **Recurring Events**
   - `/event/{id}/make-recurring`
   - `/recurring/{pattern_id}`
   - Special handling in views

2. **Availability**
   - `/availability/{date}`
   - `/find-time` - Find common free slots
   - Integration with other calendars

3. **Reminders**
   - `/event/{id}/add-reminder`
   - `/reminders/upcoming`
   - Notification preferences

4. **Categories**
   - `/categories` - Event categories
   - `/category/{name}` - Filtered view
   - Color coding support

This calendar service shows how RESTful MCP patterns enable rich functionality while maintaining simplicity. The service integrates naturally with email, tasks, and documents through the shared URI system.