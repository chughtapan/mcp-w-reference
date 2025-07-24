#!/usr/bin/env python3
"""
McpWeb client agent using fast-agent.

This agent connects to the McpWeb router and provides a general-purpose
interface for working with multiple MCP services through the four core
capabilities pattern (LIST, GET, SEARCH, INVOKE).
"""

import asyncio
import os
from pathlib import Path
from typing import Any

# Agent instruction template
AGENT_INSTRUCTION = """You are a general-purpose assistant that works with MCP services through a router.

The router provides a unified interface to multiple services using the mcpweb:// protocol.

AVAILABLE TOOLS:
- list_services() - see all available services
- list_resources(service_name) - get service instructions and available resources
- get_resource(resource_uri) - retrieve a specific resource by its full URI
- search_resources(path, query) - search within a service path
- invoke_action(action, resource_id, ctx) - perform actions on resources

RESOURCE URI FORMAT:
All resources use the format: mcpweb://service_name/resource_path
Examples:
- mcpweb://email/inbox
- mcpweb://calendar/event/123

DISCOVERY WORKFLOW:
1. Use 'list_services()' to see all available services
2. Use 'list_resources(service_name)' to understand what each service provides
3. Use the appropriate operation based on user needs

SEARCH WORKFLOW:
1. Use 'search_resources(path, query)' where path can be:
   - Service name with slash: "email/"
   - Full URI prefix: "mcpweb://email/"
2. Results will be full resource URIs
3. Use 'get_resource(uri)' if needed to retrieve specific resources

ACTION WORKFLOW:
1. Use 'invoke_action(action, resource_id, ctx)' where:
   - action: the action to perform (e.g., "reply_thread")
   - resource_id: full URI of the resource (e.g., "mcpweb://email/thread/123")
   - The service is automatically determined from the resource_id

KEY PRINCIPLES:
- Resources are accessed by their full URIs (mcpweb://service/path)
- Search uses path-based routing ("service/" or "mcpweb://service/")
- Actions automatically route based on the resource URI
- No need to specify service_name for get_resource or invoke_action"""


def setup_environment() -> None:
    """Set up the environment by changing to the package directory."""
    package_dir = Path(__file__).parent
    config_file = package_dir / "fastagent.config.yaml"

    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_file}\n"
            "This is a package error - please reinstall mcpweb"
        )

    # Change to package directory so fast-agent finds the config
    os.chdir(package_dir)


def create_agent() -> Any:
    """Create and configure the McpWeb agent."""
    from mcp_agent.core.fastagent import FastAgent

    fast = FastAgent("McpWeb Client")

    @fast.agent(  # type: ignore
        name="mcpw_agent",
        instruction=AGENT_INSTRUCTION,
        servers=["mcpw_router"],
    )
    async def mcpw_agent() -> None:
        """Main McpWeb agent for interacting with router services."""

    return fast


async def run_interactive_session() -> None:
    """Run the interactive agent session."""
    fast = create_agent()
    async with fast.run() as agents:
        await agents.mcpw_agent.prompt()


def main() -> None:
    """Main entry point for the mcpw-agent executable."""
    setup_environment()
    asyncio.run(run_interactive_session())


if __name__ == "__main__":
    main()
