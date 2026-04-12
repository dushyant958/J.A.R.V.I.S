"""
Friday MCP Server — Entry Point
Run with: python server.py
"""

from mcp.server.fastmcp import FastMCP
from friday.tools import register_all_tools
from friday.prompts import register_all_prompts
from friday.resources import register_all_resources
from friday.config import config

# Create the MCP server instance
mcp = FastMCP(
    name=config.SERVER_NAME,
    instructions=(
        f"You are J.A.R.V.I.S, the personal AI of {config.USER_NAME}. "
        "You have full access to his desktop, browser, web, and system. "
        "Be concise, sharp, and a little dry. Act, then report."
    ),
    port=config.MCP_PORT,
)

# Register tools, prompts, and resources
register_all_tools(mcp)
register_all_prompts(mcp)
register_all_resources(mcp)

def main():
    mcp.run(transport='sse')

if __name__ == "__main__":
    main()