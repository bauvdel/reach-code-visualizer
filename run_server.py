#!/usr/bin/env python3
"""REACH Code Visualizer - Web Server Launcher.

Run with: python run_server.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.server.app import create_app

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="REACH Code Visualizer Web Server")
    parser.add_argument("--host", "-H", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", "-p", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--project", default="F:/Reach", help="Project root to scan")
    args = parser.parse_args()

    print(f"""
╔════════════════════════════════════════════════════════╗
║       REACH Code Visualizer - Web Server               ║
╠════════════════════════════════════════════════════════╣
║  URL:     http://{args.host}:{args.port:<5}                          ║
║  Project: {args.project:<43} ║
║                                                        ║
║  Press Ctrl+C to stop                                  ║
╚════════════════════════════════════════════════════════╝
""")

    app = create_app(args.project)
    # Disable reloader due to Python 3.13 watchdog compatibility issue
    app.run(host=args.host, port=args.port, debug=True, threaded=True, use_reloader=False)
