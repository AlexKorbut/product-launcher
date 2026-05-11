#!/usr/bin/env python3
"""Product Launcher AI — Dashboard Server.
Serves a real-time visual dashboard showing agents as animated avatars
and Kanban task board. Data pulled from Hermes Kanban SQLite DB.
"""
import json
import sqlite3
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone

KANBAN_DB = os.path.expanduser("~/.hermes/kanban.db")
DASHBOARD_HTML = Path(__file__).parent / "product-launcher-dashboard.html"
PORT = 8765

AGENTS = {
    "orchestrator": {"emoji": "🎭", "name": "Оркестратор", "color": "#fbbf24"},
    "ocr-extractor": {"emoji": "👁️", "name": "OCR Extractor", "color": "#22d3ee"},
    "product-analyst": {"emoji": "🔍", "name": "Product Analyst", "color": "#a78bfa"},
    "content-strategist": {"emoji": "🎯", "name": "Content Strategist", "color": "#34d399"},
    "website-gen": {"emoji": "🌐", "name": "Website Gen", "color": "#60a5fa"},
    "tiktok-gen": {"emoji": "🎵", "name": "TikTok Gen", "color": "#f472b6"},
    "instagram-gen": {"emoji": "📷", "name": "Instagram Gen", "color": "#fb923c"},
    "threads-gen": {"emoji": "🧵", "name": "Threads Gen", "color": "#c084fc"},
    "asset-gen": {"emoji": "🎨", "name": "Asset Gen", "color": "#facc15"},
    "qa-text": {"emoji": "📝", "name": "Text QA", "color": "#fb7185"},
    "qa-visual": {"emoji": "🎬", "name": "Visual QA", "color": "#e879f9"},
    "qa-cross": {"emoji": "🌍", "name": "Cross QA", "color": "#2dd4bf"},
}

STATUS_MAP = {
    "todo": "📋",
    "ready": "🟡",
    "in_progress": "🟢",
    "done": "✅",
    "blocked": "🔴",
}


def get_board_data():
    """Pull current Kanban state from SQLite."""
    conn = sqlite3.connect(KANBAN_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get tasks
    cur.execute("""
        SELECT id, title, status, assignee, created_at, updated_at
        FROM tasks
        WHERE archived = 0
        ORDER BY created_at DESC
        LIMIT 50
    """)
    tasks = []
    for row in cur.fetchall():
        tasks.append({
            "id": row["id"],
            "title": row["title"],
            "status": row["status"],
            "assignee": row["assignee"] or "—",
            "created": row["created_at"],
            "updated": row["updated_at"],
        })

    # Get recent events
    cur.execute("""
        SELECT task_id, event_type, payload, created_at
        FROM task_events
        ORDER BY created_at DESC
        LIMIT 20
    """)
    events = []
    for row in cur.fetchall():
        try:
            payload = json.loads(row["payload"]) if row["payload"] else {}
        except (json.JSONDecodeError, TypeError):
            payload = {}
        events.append({
            "task_id": row["task_id"],
            "type": row["event_type"],
            "payload": payload,
            "time": row["created_at"],
        })

    conn.close()

    # Count by status
    status_counts = {}
    for t in tasks:
        s = t["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "tasks": tasks,
        "events": events,
        "status_counts": status_counts,
        "agents": AGENTS,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/board":
            data = get_board_data()
            body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/" or self.path == "/index.html":
            html = DASHBOARD_HTML.read_text(encoding="utf-8")
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # silent


def main():
    print(f"🚀 Product Launcher Dashboard")
    print(f"   http://localhost:{PORT}")
    print(f"   API: http://localhost:{PORT}/api/board")
    print(f"   Press Ctrl+C to stop")
    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")


if __name__ == "__main__":
    main()
