"""Deepnight Companion launcher.

Run:  python run_companion.py   (or double-click the packaged .exe)

Starts the local server and opens http://localhost:8010/ in your default
browser. Campaign state is stored in a ``state/`` folder created next to
this file (or next to the .exe) — delete it to reset the campaign.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

PORT = int(os.environ.get("DEEPNIGHT_PORT", "8010"))
URL = f"http://localhost:{PORT}/"


def main() -> None:
    if getattr(sys, "frozen", False):        # running as a PyInstaller bundle
        app_dir = Path(sys.executable).resolve().parent
    else:
        app_dir = Path(__file__).resolve().parent
    os.environ.setdefault("DEEPNIGHT_STATE_DIR", str(app_dir / "state"))
    os.environ.setdefault("DEEPNIGHT_GM_TOKEN_FILE", str(app_dir / "gm_token.txt"))

    # server already running? just open the browser
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", PORT)) == 0:
            webbrowser.open(URL)
            return

    import uvicorn

    from companion.server import app

    threading.Timer(1.2, lambda: webbrowser.open(URL)).start()
    print(f"Deepnight Companion — {URL}  (close this window to stop the server)")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
