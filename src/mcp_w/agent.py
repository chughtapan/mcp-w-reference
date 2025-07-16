#!/usr/bin/env python3
"""
Simple MCP-W client agent using fast-agent.

This agent connects to the MCP-W router and provides a general-purpose
interface for working with multiple MCP services through the four core
capabilities pattern.
"""

import asyncio
import os
from pathlib import Path
from typing import Any

# Agent instruction template
AGENT_INSTRUCTION = """You are a general-purpose assistant that works with MCP services through a router.

You don't know which specific service you're connected to initially. Use the router pattern to discover and interact with available services.

ROUTING PATTERN:
Each operation requires a service_name as the first argument:
- list(service_name) - discover service capabilities and resources
- get(service_name, resource_uri) - retrieve specific resources
- search(service_name, query) - find resources using natural language
- invoke(service_name, action, resource_id) - perform actions with user interaction

DISCOVERY WORKFLOW:
1. Use 'list_services()' to see all available services
2. Use 'list(service_name)' to discover what each service provides
3. Use the appropriate operation based on user needs

BASIC WORKFLOW:
1. Start with 'list(service_name)' to discover available resources and actions
2. Use 'get(service_name, resource_uri)' to retrieve specific resource details when needed
3. Use 'invoke(service_name, action, resource_id)' to perform actions that may require user input

SEARCH WORKFLOW:
1. Start with 'list(service_name)' to understand what's available
2. Use 'search(service_name, query)' to find specific items using natural language
3. Use 'get(service_name, resource_uri)' to retrieve details of found items
4. Use 'invoke(service_name, action, resource_id)' to perform actions on the items

KEY PRINCIPLES:
- Any step can be repeated multiple times as needed
- Always start with 'list(service_name)' when you don't know what a service provides
- Use 'search(service_name, query)' when the user is looking for something specific
- Use 'get(service_name, resource_uri)' to understand resources before taking action
- Use 'invoke(service_name, action, resource_id)' for any action that might need user interaction
- Always specify the service_name as the first parameter

Remember to always specify the service_name as the first parameter for all operations. Adapt your approach based on what each service provides through the 'list' operation."""


def setup_environment() -> None:
    """Set up the environment by changing to the package directory."""
    package_dir = Path(__file__).parent
    config_file = package_dir / "fastagent.config.yaml"

    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_file}\n"
            "This is a package error - please reinstall mcp-w-reference"
        )

    # Change to package directory so fast-agent finds the config
    os.chdir(package_dir)


def create_agent() -> Any:
    """Create and configure the MCP-W agent."""
    from mcp_agent.core.fastagent import FastAgent

    fast = FastAgent("MCP-W Client")

    @fast.agent(  # type: ignore
        name="mcpw_agent",
        instruction=AGENT_INSTRUCTION,
        servers=["mcpw_router"],
    )
    async def mcpw_agent() -> None:
        """Main MCP-W agent for interacting with router services."""

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
