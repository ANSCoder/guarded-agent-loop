from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("demo")


@mcp.tool()
def echo(text: str) -> str:
    """Return the text unchanged."""
    return text


@mcp.tool()
def fail() -> str:
    """Always fail, so the client's error path can be tested."""
    raise ToolError("boom")  # ToolError text reaches the client; other exceptions are hidden


if __name__ == "__main__":
    mcp.run()
