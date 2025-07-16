def test_init() -> None:
    import mcp_w
    import mcp_w.client as client
    import mcp_w.server as server
    import mcp_w.services as services

    assert hasattr(mcp_w, "__name__")
    assert hasattr(client, "__name__")
    assert hasattr(server, "__name__")
    assert hasattr(services, "__name__")
