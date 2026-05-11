#!/usr/bin/env python3
"""
Product Launcher Orchestrator — spawns agent processes that do real work.
Each agent: claims task → does work → completes task → updates Kanban.
Dashboard reads the same Kanban DB in real-time.
"""
import json
import sqlite3
import time
import random
import multiprocessing
from pathlib import Path
from datetime import datetime, timezone

sys_path = Path(__file__).resolve().parent.parent / "src"
import sys
sys.path.insert(0, str(sys_path))

from product_launcher.kanban import KanbanBoard

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "kanban_live.db"

AGENTS = [
    {"agent": "ocr-extractor",       "title": "OCR брошюры",           "duration": 3},
    {"agent": "product-analyst",     "title": "Анализ продукта",       "duration": 4},
    {"agent": "content-strategist",  "title": "Контент-стратегия",     "duration": 5},
    {"agent": "website-gen",         "title": "Генерация лендинга",    "duration": 6},
    {"agent": "tiktok-gen",          "title": "TikTok сценарии",       "duration": 4},
    {"agent": "instagram-gen",       "title": "Instagram карусели",    "duration": 4},
    {"agent": "threads-gen",         "title": "Threads контент",       "duration": 3},
    {"agent": "asset-gen",           "title": "Генерация ассетов",     "duration": 5},
    {"agent": "qa-text",             "title": "QA текста",             "duration": 2},
    {"agent": "qa-visual",           "title": "QA визуала",            "duration": 2},
    {"agent": "qa-cross",            "title": "Кросс-платформенный QA","duration": 3},
]

def agent_worker(agent_name: str, task_title: str, duration: int):
    """Simulate one agent doing real work."""
    board = KanbanBoard(db_path=str(DB_PATH))

    # Wait for task to appear in kanban
    for _ in range(30):
        task = board.get_next_task(agent_name)
        if task:
            task_id = task["id"]
            board.claim_task(task_id)
            print(f"  [{agent_name}] 🔧 {task_title} — started")
            break
        time.sleep(1)
    else:
        print(f"  [{agent_name}] ⚠️ No task found, exiting")
        return

    # Simulate work
    for i in range(duration):
        time.sleep(1)

    # Complete
    output = {
        "agent": agent_name,
        "result": f"Completed: {task_title}",
        "tokens_used": random.randint(500, 5000),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    board.complete_task(task_id, output_data=output)
    print(f"  [{agent_name}] ✅ {task_title} — done")


def orchestrator():
    """Create tasks and spawn agent workers."""
    # Clean slate
    if DB_PATH.exists():
        DB_PATH.unlink()

    board = KanbanBoard(db_path=str(DB_PATH))

    # Create all tasks
    print("📋 Creating tasks...")
    tasks_created = []
    for ag in AGENTS:
        task_id = board.add_task(
            title=ag["title"],
            agent=ag["agent"],
            input_data={"phase": "demo", "product_id": "test-001"},
        )
        tasks_created.append((task_id, ag))
        print(f"  + {task_id}: {ag['title']} → {ag['agent']}")

    print(f"\n🚀 Spawning {len(AGENTS)} agents...")
    processes = []
    for task_id, ag in tasks_created:
        p = multiprocessing.Process(
            target=agent_worker,
            args=(ag["agent"], ag["title"], ag["duration"]),
        )
        p.start()
        processes.append(p)

    # Wait for all agents
    for p in processes:
        p.join()

    print("\n🎉 All agents finished!")
    stats = board.get_tasks_by_status("done")
    print(f"   Completed: {len(stats)}/{len(AGENTS)}")


if __name__ == "__main__":
    orchestrator()
