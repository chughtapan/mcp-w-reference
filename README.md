# RESTful MCP

**RESTful MCP** (McpWeb Pattern) - A pattern for building scalable MCP services. Instead of exposing dozens of tools, every service implements just five core capabilities, creating a uniform interface that scales to any number of services.

## Overview

RESTful MCP solves the "tool explosion" problem in MCP by introducing a resource-centric pattern:

- **Problem**: Traditional MCP services expose 40+ tools each, causing context bloat and confusion
- **Solution**: Gateway server provides five operations (LIST, VIEW, GET, FIND, POST) for all services
- **Result**: 5 operations for 100 services instead of 4000+ tools

### Key Features

- **Five Core Operations**: LIST, VIEW, GET, FIND, POST - provided by the gateway server
- **Resource-Centric Design**: Everything has a URI (mcpweb://service/resource)
- **Progressive Discovery**: Start with LIST, drill down as needed
- **Context Efficient**: Minimal tool definitions leave more room for actual work
- **Service Isolation**: Each service operates independently

## Quick Start

### Installation

```bash
git clone <repository-url>
cd restful-mcp
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

2. **Start the RESTful MCP client (in another terminal):**
   ```bash
   restful-mcp-agent
   ```

   The client will automatically:
   - Connect to the router server which proxies to available services
   - Provide an interactive chat interface
   - Allow you to work with any connected MCP services

   > **Note**: After installation with `uv pip install -e .`, the `restful-mcp-agent` command will be available system-wide

### Try It Out

Once both components are running, you can interact with the services using the five operations:

```
# Discover available services
LIST
→ ["email", "calendar"]

# Learn about a service
VIEW email
→ Email service capabilities and resources

# Find content
FIND email "project update"
→ ["mcpweb://email/thread/thread_001", "mcpweb://email/thread/thread_042"]

# Get specific resource
GET mcpweb://email/thread/thread_001
→ Full email thread with messages

# Perform an action
POST mcpweb://email/thread/thread_001/reply
→ Interactive prompt to compose reply
```

### Example Workflows

**Email Workflow:**
```
VIEW email                              # See what email service offers
FIND email "budget"                    # Find budget-related emails
GET mcpweb://email/thread/thread_042    # Read specific thread
POST mcpweb://email/thread/thread_042/reply  # Reply with smart defaults
```

**Calendar Workflow:**
```
GET mcpweb://calendar/today             # See today's events
GET mcpweb://calendar/week              # See this week
FIND calendar "team meeting"           # Find specific events
POST mcpweb://calendar/event/evt_001/reschedule  # Reschedule event
```

### Troubleshooting

- **"Service not found"**: Make sure the services are running (email on port 3001, calendar on port 3002)
- **"Connection refused"**: Check that both terminals are running and there are no port conflicts
- **"Config not found"**: Make sure you've installed the project with `uv pip install -e .` and the `restful-mcp-agent` command is available
- **Check logs**: View `/tmp/fastagent.log` for detailed logging information

## Architecture

### Five Core Operations

1. **LIST**: Discover what services are available
2. **VIEW**: Learn what a specific service can do
3. **GET**: Retrieve specific resources by URI
4. **FIND**: Find resources matching a query
5. **POST**: Perform actions on resources

### Three-Component Architecture

**Core Components:**
- `agent.py`: Fast-agent client with MCP gateway integration
- `gateway.py`: Gateway server implementation for service aggregation
- `fastagent.config.yaml`: Unified configuration for agent and gateway
- `server.config.json`: Gateway service connections configuration

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

**RESTful MCP (Resource-Centric):**
- 5 core operations provided by gateway
- URI-based resource access
- Clear separation of concerns
- Better error handling

## Project Structure

```
src/restful_mcp/
├── __init__.py            # Package initialization
├── agent.py               # Fast-agent client implementation
├── gateway.py             # FastMCP gateway for service aggregation
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
The gateway (`gateway.py`) uses FastMCP's ProxyClient to forward requests:
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