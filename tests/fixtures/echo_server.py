from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo")


@mcp.tool()
def echo(text: str) -> str:
    """Return the text unchanged."""
    return text


if __name__ == "__main__":
    mcp.run()
