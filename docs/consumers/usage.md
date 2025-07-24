# Using RESTful MCP Services

This guide shows you how to interact with RESTful MCP services as a consumer (user or LLM agent). Whether you're using a single service or hundreds through a gateway server, the interface is always the same five operations.

## The Five Operations

Every RESTful MCP service supports these operations:

1. **LIST** - What services are available?
2. **VIEW** - What can this service do?
3. **GET** - Show me this specific thing
4. **FIND** - Find things matching my query
5. **POST** - Do this action

## Quick Start

Here's a typical interaction flow:

```
You: Help me find emails about the budget proposal

Agent: I'll find emails about the budget proposal.

LIST
→ ["email", "calendar", "documents", "tasks"]

FIND email "budget proposal"
→ ["mcpweb://email/thread/thread_042", 
   "mcpweb://email/thread/thread_156"]

GET mcpweb://email/thread/thread_042
→ {
    "subject": "Q1 Budget Proposal Review",
    "participants": ["cfo@company.com", "you@company.com"],
    "last_message": "Please review the attached proposal...",
    "actions": ["mcpweb://email/thread/thread_042/reply"]
  }

You: Reply to that email

POST mcpweb://email/thread/thread_042/reply
→ [Prompt appears]
   Recipients: cfo@company.com (pre-filled)
   Subject: Re: Q1 Budget Proposal Review (pre-filled)
   Message: [your message here]
→ {"status": "sent"}
```

## Understanding Each Operation

### LIST - Discover Services

LIST shows you what services are available:

```
LIST
→ ["email", "calendar", "documents", "tasks", "contacts", "notes"]
```

Use LIST when:
- First connecting to a RESTful MCP system
- You want to see all available services
- You're not sure which service to use

### VIEW - Explore Service Capabilities

VIEW tells you what a specific service can do:

```
VIEW calendar
→ {
    "name": "calendar",
    "description": "Calendar service for managing events and schedules.
                    
                    Resources:
                    - /today: Today's events
                    - /week: This week's events  
                    - /event/{id}: Specific event details
                    - /event/{id}/reschedule: Reschedule an event
                    
                    Find: Search events by title, participants, or date range",
    "resources": [
        "mcpweb://calendar/today",
        "mcpweb://calendar/week",
        "mcpweb://calendar/event/{id}"
    ]
  }
```

Use VIEW when:
- You want to understand what a service offers
- You need to know available resources
- You're exploring a new service

### GET - Retrieve Resources

GET fetches specific resources by their URI:

```
GET mcpweb://calendar/today
→ {
    "date": "2024-03-15",
    "events": [
        {
            "id": "evt_001",
            "title": "Team Standup",
            "time": "09:00",
            "uri": "mcpweb://calendar/event/evt_001"
        },
        {
            "id": "evt_002", 
            "title": "Budget Review",
            "time": "14:00",
            "uri": "mcpweb://calendar/event/evt_002"
        }
    ]
  }
```

Use GET when:
- You have a specific URI to retrieve
- Following links from other resources
- Refreshing resource data

### FIND - Find Resources

FIND helps you find resources across a service:

```
FIND calendar "budget"
→ ["mcpweb://calendar/event/evt_002",
   "mcpweb://calendar/event/evt_045",
   "mcpweb://calendar/event/evt_089"]
```

Find tips:
- Returns URIs, not full data (use GET for details)
- Each service implements search differently
- Check VIEW to understand find capabilities

### POST - Perform Actions

POST executes actions on resources:

```
POST mcpweb://calendar/event/evt_002/reschedule
→ [Interactive prompt appears]
   Current: March 15, 2024 at 14:00
   New date: March 16, 2024 (pre-filled with tomorrow)
   New time: 14:00 (pre-filled with same time)
   Notify attendees? Yes
→ {"status": "rescheduled", "new_time": "2024-03-16T14:00"}
```

POST characteristics:
- Always on action resources (URIs ending with verbs)
- Triggers interactive prompts for user input
- Provides smart defaults based on context
- Returns action results

## Common Workflows

### Finding and Reading Information

```
# Find specific emails
FIND email "project deadline"
→ ["mcpweb://email/thread/123", "mcpweb://email/thread/456"]

# Read the first result
GET mcpweb://email/thread/123
→ {full thread content}
```

### Cross-Service Workflows

```
# Find an email
FIND email "meeting tomorrow"
→ ["mcpweb://email/thread/789"]

# Get email details
GET mcpweb://email/thread/789
→ {subject: "Planning Meeting", participants: [...]}

# Create calendar event based on email
POST mcpweb://calendar/create
→ [Prompt pre-filled with email subject and participants]
```

### Progressive Discovery

```
# Start broad
LIST
→ ["email", "calendar", "documents", ...]

# Explore a service  
VIEW documents
→ {description: "Document management...", resources: [...]}

# Find content
FIND documents "Q1 report"
→ ["mcpweb://documents/doc/abc123"]

# Get document
GET mcpweb://documents/doc/abc123
→ {title: "Q1 Financial Report", content: ...}

# Share document
POST mcpweb://documents/doc/abc123/share
→ [Sharing prompt]
```

## Working with Resources

### Understanding URIs

Every piece of data has a URI:
```
mcpweb://email/thread/123         # Email thread
mcpweb://calendar/event/evt_001   # Calendar event  
mcpweb://documents/folder/reports # Document folder
```

URIs are:
- **Permanent**: Save them for later use
- **Shareable**: Send to others
- **Linkable**: Resources can reference each other

### Following Links

Resources often include links to related resources:

```
GET mcpweb://email/inbox
→ {
    "threads": [
        {"uri": "mcpweb://email/thread/1", "subject": "..."},
        {"uri": "mcpweb://email/thread/2", "subject": "..."}
    ],
    "actions": ["mcpweb://email/compose"]
  }
```

### Action Resources

Actions are resources too, typically ending with a verb:

```
mcpweb://email/thread/123/reply      # Reply to email
mcpweb://document/doc456/share       # Share document
mcpweb://task/task789/complete       # Complete task
mcpweb://calendar/event/evt_001/cancel # Cancel event
```

## Error Handling

Services return clear errors:

```
GET mcpweb://email/thread/nonexistent
→ {"error": "Thread 'nonexistent' not found", "status": 404}

FIND invalidservice "query"
→ {"error": "Service 'invalidservice' not found",
   "available": ["email", "calendar", "documents"]}

POST mcpweb://email/thread/123/invalid_action
→ {"error": "Unknown action 'invalid_action'",
   "available_actions": ["reply", "forward", "archive"]}
```

## Best Practices

### 1. Start with Discovery
Always begin with LIST and VIEW to understand what's available:
```
LIST → VIEW email → FIND email "important"
```

### 2. Use Find Effectively
- Be specific with find queries
- Check VIEW to understand find capabilities
- Remember find returns URIs, not data

### 3. Save Important URIs
URIs are stable references:
```python
important_doc = "mcpweb://documents/doc/quarterly_report_q1_2024"
# Can GET this URI anytime
```

### 4. Check Available Actions
When you GET a resource, look for action links:
```
GET mcpweb://task/task_123
→ {
    "title": "Review budget",
    "status": "pending",
    "actions": [
        "mcpweb://task/task_123/complete",
        "mcpweb://task/task_123/assign",
        "mcpweb://task/task_123/defer"
    ]
  }
```

### 5. Let Context Guide You
POST operations often pre-fill forms with smart defaults:
```
# Getting email thread shows participants
GET mcpweb://email/thread/123
→ {participants: ["alice@example.com", "bob@example.com"]}

# Reply automatically includes those participants
POST mcpweb://email/thread/123/reply
→ Recipients: alice@example.com, bob@example.com (pre-filled)
```

## Advanced Usage

### Batch Operations
Some services support bulk actions:
```
POST mcpweb://email/threads/archive
→ [Select threads to archive]
→ {"archived": 5, "threads": [...]}
```

### Filtered Views
Many services offer filtered resource collections:
```
GET mcpweb://email/inbox/unread
GET mcpweb://calendar/week
GET mcpweb://tasks/assigned/me
```

### Cross-References
Resources can reference other services:
```
GET mcpweb://task/task_001
→ {
    "title": "Review document",
    "related": [
        "mcpweb://documents/doc/report_123",
        "mcpweb://email/thread/discussion_456"
    ]
  }
```

## Troubleshooting

### Service Not Found
```
Error: Service 'unknown' not found
Solution: Use LIST to see available services
```

### Resource Not Found  
```
Error: Resource 'mcpweb://email/thread/999' not found
Solution: Use FIND to find valid resources
```

### Action Failed
```
Error: Action failed - missing required fields
Solution: Fill in all required fields in the prompt
```

### Connection Issues
```
Error: Could not connect to service 'calendar'
Solution: Check service is running and accessible
```

## Summary

RESTful MCP makes interacting with services simple:
1. **LIST** to discover
2. **VIEW** to understand
3. **FIND** to find
4. **GET** to retrieve
5. **POST** to act

Whether you're working with one service or a hundred, these five operations remain the same. Start with discovery, find what you need, and post actions when ready.

The pattern is designed to be intuitive—you don't need to memorize complex tool signatures or parameters. Just remember the five operations and follow the links.