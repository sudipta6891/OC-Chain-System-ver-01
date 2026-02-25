"""Serve generated HTML reports over HTTP."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from reporting.report_web_store import ReportWebStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve report viewer web pages")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent / "reports" / "web"
    base_dir.mkdir(parents=True, exist_ok=True)
    ReportWebStore.refresh_index()

    handler = partial(SimpleHTTPRequestHandler, directory=str(base_dir))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving reports at http://{args.host}:{args.port}")
    print(f"Root directory: {base_dir}")
    server.serve_forever()


if __name__ == "__main__":
    main()
