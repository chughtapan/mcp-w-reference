# MCP-W Reference Implementation

A reference implementation for **ModelContextProtocol: Web Extension (MCP-W)** - a resource-centric approach to MCP that implements the four core capabilities pattern for building scalable, maintainable MCP servers.

## Overview

This project demonstrates a clean three-component architecture for MCP servers:

- **Client**: AI agent implementation using fast-agent framework
- **Server**: Routing infrastructure using FastMCP with proxy pattern
- **Services**: Individual service implementations following the MCP-W pattern

### Key Features

- **Resource-Centric Design**: Clear separation between data (resources) and actions (tools)
- **Four Core Capabilities**: LIST, GET, SEARCH, INVOKE operations
- **Router Pattern**: Single server proxying to multiple services
- **Service Isolation**: Better error handling and composability
- **Elicitation-Based Actions**: User-controlled workflows with smart defaults

## Quick Start

### Installation

```bash
git clone <repository-url>
cd mcp-w-reference
uv pip install -e .
```

### Running the Project

The project has two main components that need to be started:

1. **Start the services (each in a separate terminal):**
   
   Email service:
   ```bash
   uv run fastmcp run -t streamable-http examples.email.email --port 3001
   ```
   
   Calendar service:
   ```bash
   uv run fastmcp run -t streamable-http examples.calendar.calendar --port 3002
   ```

2. **Start the MCP-W client (in another terminal):**
   ```bash
   mcpw-agent
   ```

   The client will automatically:
   - Connect to the router server which proxies to available services
   - Provide an interactive chat interface
   - Allow you to work with any connected MCP services

   > **Note**: After installation with `uv pip install -e .`, the `mcpw-agent` command will be available system-wide

### Try It Out

Once both components are running, you can interact with the services:

**Email Service:**
- **"list email"** - See available email resources and capabilities
- **"search email project"** - Find email threads containing "project"
- **"get email://thread/thread_001"** - View details of a specific email thread
- **"invoke email reply_thread thread_001"** - Compose and send a reply

**Calendar Service:**
- **"list calendar"** - See available calendar resources and capabilities
- **"get calendar://today"** - View today's events
- **"get calendar://week"** - View this week's events
- **"search calendar lunch"** - Find events containing "lunch"
- **"invoke calendar create_event"** - Create a new calendar event
- **"invoke calendar reschedule_event evt_001"** - Reschedule an event

### Troubleshooting

- **"Service not found"**: Make sure the services are running (email on port 3001, calendar on port 3002)
- **"Connection refused"**: Check that both terminals are running and there are no port conflicts
- **"Config not found"**: Make sure you've installed the project with `uv pip install -e .` and the `mcpw-agent` command is available
- **Check logs**: View `/tmp/fastagent.log` for detailed logging information

## Architecture

### Four Core Capabilities

1. **LIST**: Discover service capabilities and available resources
2. **GET**: Retrieve specific resources by URI
3. **SEARCH**: Find resources using natural language queries
4. **INVOKE**: Perform actions through interactive elicitation

### Three-Component Architecture

**Core Components:**
- `agent.py`: Fast-agent client with MCP router integration
- `router.py`: FastMCP router using ProxyClient for service composition
- `fastagent.config.yaml`: Unified configuration for agent and router
- `server.config.json`: Router service connections configuration

**Example Services:**
- `examples/email/`: Standalone FastMCP email service example
- `examples/calendar/`: Standalone FastMCP calendar service example
- Additional services can be added as independent examples

### Technology Stack

- **FastMCP**: Server framework for building MCP servers
- **fast-agent**: Client framework for building AI agents
- **Pydantic**: Data validation and schema definitions
- **pytest**: Comprehensive testing framework

### Resource-Centric vs Tool-Centric

**Traditional MCP (Tool-Centric):**
- 40+ tools per service
- Complex tool signatures
- Poor service isolation
- Context window explosion

**MCP-W (Resource-Centric):**
- 4 core operations
- URI-based resource access
- Clear separation of concerns
- Better error handling

## Project Structure

```
src/mcp_w/
├── __init__.py            # Package initialization
├── agent.py               # Fast-agent client implementation
├── router.py              # FastMCP router for service composition
├── fastagent.config.yaml  # Agent and router configuration
└── service_schema.json    # Service validation schema

examples/
├── email/
│   └── email.py           # Example email service implementation
└── calendar/
    └── calendar.py        # Example calendar service implementation

# Configuration
server.config.json         # Router service configuration

# Testing
tests/
├── unit/                  # Unit tests
└── integration/           # Integration tests
```

## Implementation Details

### Router Architecture
The router (`router.py`) uses FastMCP's ProxyClient to forward requests:
- Single FastMCP server exposing unified interface
- Service name as first parameter for all operations
- Native MCP protocol communication via ProxyClient
- Full elicitation support preserved through Context forwarding
- Error handling and service isolation
- Configurable via `server.config.json`

### Service Architecture
Services are independent FastMCP servers (see `examples/email/`):
- Standard FastMCP tools: `list_resources()`, `get_resource()`, `search_resources()`, `invoke_action()`
- JSON response format for all operations
- Context-aware elicitation workflows
- Run via `uv run fastmcp run -t streamable-http`

### Client Architecture
The agent (`agent.py`) provides the user interface:
- Fast-agent based implementation
- Automatic router discovery via `fastagent.config.yaml`
- Interactive chat interface
- Configurable model selection

## Development

### Running Tests
```bash
pytest
```

### Code Quality
```bash
uv run black src/ tests/ examples/
uv run isort src/ tests/ examples/ --profile black
uv run mypy src/ --ignore-missing-imports
uv run flake8 src/ tests/ examples/
```

### Adding New Services

1. Implement the four core capabilities
2. Follow URI scheme conventions
3. Add elicitation workflows for actions
4. Update agent configuration

## Documentation

- **[CLAUDE.md](CLAUDE.md)**: Comprehensive development guide
- **[RFC Documentation](../rfc/)**: Protocol design and analysis
- **[FastMCP Docs](https://gofastmcp.com/)**: Server framework documentation
- **[fast-agent Docs](https://fast-agent.ai/)**: Agent framework documentation

## Contributing

This is a reference implementation for demonstrating the MCP-W pattern. Contributions should focus on:

- Improving the four capabilities implementation
- Adding new service examples
- Enhancing elicitation workflows
- Better error handling and recovery

## License

[License information to be added]

## Related Work

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP Framework](https://gofastmcp.com/)
- [fast-agent Framework](https://fast-agent.ai/)