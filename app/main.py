"""Entry point for the MCP server.

Usage::

    python -m app.main

Or via the MCP CLI::

    mcp run app/server.py
"""

from __future__ import annotations

import logging

from app.server import mcp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
