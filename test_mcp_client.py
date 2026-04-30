"""Test the MCP server over stdio: list tools and call one."""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def venv_python() -> str:
    root = Path(__file__).parent
    if sys.platform == "win32":
        return str(root / ".venv" / "Scripts" / "python.exe")
    return str(root / ".venv" / "bin" / "python")


async def main() -> None:
    params = StdioServerParameters(
        command=venv_python(),
        args=["-m", "farshid_mcp_imageprocessing.server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Server exposes {len(tools.tools)} tools:")
            for t in tools.tools:
                print(f"  - {t.name}")
            print("\nCalling image_info on .farshid/test/sample.png ...")
            r = await session.call_tool(
                "image_info", {"path": ".farshid/test/sample.png"}
            )
            for c in r.content:
                print(getattr(c, "text", c))


if __name__ == "__main__":
    asyncio.run(main())
