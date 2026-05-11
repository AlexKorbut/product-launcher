#!/usr/bin/env python3
"""
Product Launcher Orchestrator — spawns agents that do real AI work.
Agents: OCR → ProductAnalyst → ContentStrategy → Parallel Generation → QA.
Dashboard reads the same Kanban DB in real-time.
"""
import json
import sys
import time
import random
import multiprocessing
from pathlib import Path
from datetime import datetime, timezone

sys_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(sys_path))

from product_launcher.kanban import KanbanBoard
from product_launcher.agents import LLMClient
from product_launcher.agents.product_analyst import ProductAnalyst
from product_launcher.agents.content_strategist import ContentStrategist

PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "kanban_live.db"

AGENTS = [
    {"agent": "ocr-extractor",       "title": "OCR брошюры",           "real": False, "depends_on": []},
    {"agent": "product-analyst",     "title": "Анализ продукта",       "real": True,  "depends_on": ["ocr-extractor"]},
    {"agent": "content-strategist",  "title": "Контент-стратегия",     "real": True,  "depends_on": ["product-analyst"]},
    {"agent": "website-gen",         "title": "Генерация лендинга",    "real": False, "depends_on": ["content-strategist"]},
    {"agent": "tiktok-gen",          "title": "TikTok сценарии",       "real": False, "depends_on": ["content-strategist"]},
    {"agent": "instagram-gen",       "title": "Instagram карусели",    "real": False, "depends_on": ["content-strategist"]},
    {"agent": "threads-gen",         "title": "Threads контент",       "real": False, "depends_on": ["content-strategist"]},
    {"agent": "asset-gen",           "title": "Генерация ассетов",     "real": False, "depends_on": ["product-analyst"]},
    {"agent": "qa-text",             "title": "QA текста",             "real": False, "depends_on": ["website-gen", "tiktok-gen", "instagram-gen", "threads-gen"]},
    {"agent": "qa-visual",           "title": "QA визуала",            "real": False, "depends_on": ["asset-gen"]},
    {"agent": "qa-cross",            "title": "Кросс-платформенный QA","real": False, "depends_on": ["qa-text", "qa-visual"]},
]


def get_dependency_output(board: KanbanBoard, agent_name: str) -> dict | None:
    """Get the output of a completed dependency task."""
    tasks = board.get_tasks_by_status("done")
    for task in tasks:
        if task["agent"] == agent_name:
            try:
                return json.loads(task.get("output_json", "{}"))
            except (json.JSONDecodeError, TypeError):
                return {}
    return None


def agent_worker(agent_name: str, task_title: str, is_real: bool, depends_on: list[str]):
    """Run one agent — real AI or simulated."""
    board = KanbanBoard(db_path=str(DB_PATH))

    # Wait for task to appear
    task = None
    for _ in range(60):
        task = board.get_next_task(agent_name)
        if task:
            task_id = task["id"]
            board.claim_task(task_id)
            print(f"  [{agent_name}] 🔧 {task_title} — started")
            break
        time.sleep(0.5)
    else:
        print(f"  [{agent_name}] ⚠️ No task found, exiting")
        return

    # Collect dependency outputs
    dep_outputs = {}
    for dep in depends_on:
        dep_outputs[dep] = get_dependency_output(board, dep)

    try:
        if is_real and agent_name == "product-analyst":
            # ── REAL: Product Analyst ──
            ocr_data = dep_outputs.get("ocr-extractor", {})
            raw_text = ocr_data.get("text", "Демо-брошюра: AI-Powered Coffee Machine. Идеальный кофе каждое утро.")
            
            analyst = ProductAnalyst()
            result = analyst.run({
                "raw_text": raw_text,
                "event": "Demo Pipeline",
                "location": "VPS",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "images": [],
            })
            output = result
            
        elif is_real and agent_name == "content-strategist":
            # ── REAL: Content Strategist ──
            analyst_output = dep_outputs.get("product-analyst", {})
            
            strategist = ContentStrategist()
            result = strategist.run({"kb": analyst_output})
            output = result
        else:
            # ── SIMULATED: placeholder ──
            time.sleep(random.uniform(1, 3))
            output = {
                "agent": agent_name,
                "result": f"Simulated: {task_title}",
                "tokens_used": random.randint(500, 5000),
            }

        output["completed_at"] = datetime.now(timezone.utc).isoformat()
        board.complete_task(task_id, output_data=output)
        print(f"  [{agent_name}] ✅ {task_title} — done")

    except Exception as e:
        output = {
            "agent": agent_name,
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        board.fail_task(task_id, error=str(e))
        print(f"  [{agent_name}] ❌ {task_title} — FAILED: {e}")


def orchestrator():
    """Create tasks and spawn agents (respects dependency order)."""
    if DB_PATH.exists():
        DB_PATH.unlink()

    board = KanbanBoard(db_path=str(DB_PATH))

    # Phase 1: Create all tasks upfront
    print("📋 Creating tasks...")
    for ag in AGENTS:
        task_id = board.add_task(
            title=ag["title"],
            agent=ag["agent"],
            input_data={"phase": "production", "product_id": "demo-001"},
        )
        print(f"  + {task_id}: {ag['title']} → {ag['agent']}")

    # Phase 2: Run sequentially to respect dependencies
    # (Parallel within phases — simulators run concurrently where possible)
    print(f"\n🚀 Spawning {len(AGENTS)} agents...")
    
    # Phase 2a: OCR (no deps)
    ocr_agents = [ag for ag in AGENTS if not ag["depends_on"]]
    for ag in ocr_agents:
        p = multiprocessing.Process(
            target=agent_worker,
            args=(ag["agent"], ag["title"], ag["real"], ag["depends_on"]),
        )
        p.start()
        p.join()  # Wait for OCR before analyst

    # Phase 2b: Product Analyst (depends on OCR)
    analyst_agents = [ag for ag in AGENTS if "ocr-extractor" in ag["depends_on"]]
    for ag in analyst_agents:
        p = multiprocessing.Process(
            target=agent_worker,
            args=(ag["agent"], ag["title"], ag["real"], ag["depends_on"]),
        )
        p.start()
        p.join()

    # Phase 2c: Content Strategist (depends on analyst)
    strat_agents = [ag for ag in AGENTS if "product-analyst" in ag["depends_on"] and ag["agent"] == "content-strategist"]
    for ag in strat_agents:
        p = multiprocessing.Process(
            target=agent_worker,
            args=(ag["agent"], ag["title"], ag["real"], ag["depends_on"]),
        )
        p.start()
        p.join()

    # Phase 2d: Parallel generation (depends on strategist or analyst)
    gen_agents = [ag for ag in AGENTS if ag["agent"] in ("website-gen", "tiktok-gen", "instagram-gen", "threads-gen", "asset-gen")]
    procs = []
    for ag in gen_agents:
        p = multiprocessing.Process(
            target=agent_worker,
            args=(ag["agent"], ag["title"], ag["real"], ag["depends_on"]),
        )
        p.start()
        procs.append(p)
    for p in procs:
        p.join()

    # Phase 2e: QA (depends on generation)
    qa_agents = [ag for ag in AGENTS if ag["agent"].startswith("qa-")]
    procs = []
    for ag in qa_agents:
        p = multiprocessing.Process(
            target=agent_worker,
            args=(ag["agent"], ag["title"], ag["real"], ag["depends_on"]),
        )
        p.start()
        procs.append(p)
    for p in procs:
        p.join()

    print("\n🎉 Pipeline complete!")
    stats = board.get_tasks_by_status("done")
    failed = board.get_tasks_by_status("failed")
    print(f"   ✅ Done: {len(stats)}/{len(AGENTS)}")
    if failed:
        print(f"   ❌ Failed: {len(failed)}")


if __name__ == "__main__":
    orchestrator()
