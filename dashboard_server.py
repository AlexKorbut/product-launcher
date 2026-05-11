#!/usr/bin/env python3
"""
Kanban Dashboard Server — serves dashboard HTML + JSON API.
The dashboard reads real task/agent data from the Kanban SQLite DB.
"""
import http.server
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "kanban_live.db"
DASHBOARD_PATH = PROJECT_DIR / "agent-dashboard.html"
PORT = 8080


def get_kanban_data() -> dict:
    """Read real kanban state from SQLite."""
    if not DB_PATH.exists():
        return {"agents": [], "kanban": {}, "log": []}

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Tasks grouped by status
    kanban = {"todo": [], "in_progress": [], "done": [], "failed": []}
    tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at").fetchall()
    for t in tasks:
        t_dict = dict(t)
        status = t_dict["status"]
        if status in kanban:
            kanban[status].append(t_dict)

    # Agent summary
    agents = conn.execute("""
        SELECT agent, 
               COUNT(*) as total,
               SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END) as active,
               SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done,
               SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
        FROM tasks GROUP BY agent
    """).fetchall()
    agent_list = [dict(a) for a in agents]

    conn.close()

    return {
        "agents": agent_list,
        "kanban": kanban,
        "total_tasks": len(tasks),
    }


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/kanban":
            data = get_kanban_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
        elif self.path == "/" or self.path == "/dashboard":
            self.path = "/agent-dashboard.html"
            super().do_GET()
        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass  # quiet


def main():
    print(f"🚀 Kanban Dashboard: http://localhost:{PORT}")
    print(f"   DB: {DB_PATH}")
    server = http.server.HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
