"""Run the laboratory on localhost."""

import argparse
import sys

import uvicorn

from ai_alchemist import __version__


def main() -> None:
    """Parse CLI arguments and serve the app."""
    parser = argparse.ArgumentParser(description="AI Alchemist laboratory")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address. Defaults to loopback.")
    parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    parser.add_argument("--version", action="store_true", help="Print the version and exit.")
    args = parser.parse_args()
    if args.version:
        print(__version__)
        return
    if args.host in {"0.0.0.0", "::"}:
        print(
            "Warning: binding beyond loopback exposes settings and experiment history "
            "to anyone who can reach this port.",
            file=sys.stderr,
        )
    uvicorn.run("ai_alchemist.app:create_app", factory=True, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
