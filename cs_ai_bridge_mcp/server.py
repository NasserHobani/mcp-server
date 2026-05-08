"""CLI / Docker entry: re-export `mcp` for `fastmcp run ...:mcp` and run."""

from __future__ import annotations

from .app import mcp


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    mcp.run()


if __name__ == "__main__":
    main()
