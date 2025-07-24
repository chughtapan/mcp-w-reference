"""
RESTful MCP - A pattern for building scalable Model Context Protocol services.

This package provides a gateway server and service pattern for building
MCP services with automatic resource prefixing and unified interfaces.
"""

__version__ = "0.1.0"

from .config import PROTOCOL
from .mcpw import MCPWService
from .gateway import FastMCPGateway

__all__ = ["PROTOCOL", "MCPWService", "FastMCPGateway"]