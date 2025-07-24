#!/usr/bin/env python
"""
Example multi-service server using the simplified router with MCPW pattern.

This demonstrates mounting multiple services with automatic resource prefixing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.restful_mcp.gateway import FastMCPGateway
from examples.email.email import mcp as email_service
from examples.calendar.calendar import mcp as calendar_service


def main():
    """Run a multi-service server with gateway."""
    # Create gateway
    gateway = FastMCPGateway(
        {"mcpServers": {}},
        name="Multi-Service Gateway",
        instructions="""Multi-service gateway demonstrating the McpWeb pattern.
        Includes email and calendar services with automatic resource prefixing."""
    )
    
    # Mount services
    gateway.mount_service("email", email_service)
    gateway.mount_service("calendar", calendar_service)
    
    print("Starting Multi-Service Gateway...")
    print("\nEmail Service Resources:")
    print("  - mcpweb://email/inbox")
    print("  - mcpweb://email/thread/{thread_id}")
    
    print("\nCalendar Service Resources:")
    print("  - mcpweb://calendar/today")
    print("  - mcpweb://calendar/week")
    print("  - mcpweb://calendar/calendars")
    print("  - mcpweb://calendar/event/{event_id}")
    print("  - mcpweb://calendar/calendar/{calendar_id}")
    
    print("\nGateway Operations:")
    print("  - list_services()")
    print("  - list_resources(service_name)")
    print("  - get_resource(resource_uri)")
    print("  - search_resources(path, query)")
    print("  - invoke_action(action, resource_id, ctx)")
    
    print("\nExample Usage:")
    print("  - search_resources('email/', 'budget')")
    print("  - search_resources('mcpweb://calendar/', 'standup')")
    print("  - get_resource('mcpweb://email/inbox')")
    print("  - invoke_action('reply_thread', 'mcpweb://email/thread/001', ctx)")
    
    # Run the gateway
    gateway.run()


if __name__ == "__main__":
    main()