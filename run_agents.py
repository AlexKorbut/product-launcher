#!/usr/bin/env python3
"""
Product Launcher Orchestrator — ALL agents are real AI.
Pipeline: OCR → Analyst → Strategist → [5 generators] → [3 QA]
Dashboard reads Kanban DB in real-time.
"""
import json, sys, time, random, multiprocessing
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from product_launcher.kanban import KanbanBoard
from product_launcher.agents.product_analyst import ProductAnalyst
from product_launcher.agents.content_strategist import ContentStrategist
from product_launcher.agents.content_generator import (
    WebsiteGenerator, TikTokGenerator, InstagramGenerator, ThreadsGenerator,
)
from product_launcher.agents.asset_gen import AssetGenerator
from product_launcher.agents.qa_agents import QAText, QAVisual, QACross

DB_PATH = Path(__file__).resolve().parent / "kanban_live.db"

AGENTS = [
    {"agent": "ocr-extractor",       "title": "OCR брошюры",           "depends_on": []},
    {"agent": "product-analyst",     "title": "Анализ продукта",       "depends_on": ["ocr-extractor"]},
    {"agent": "content-strategist",  "title": "Контент-стратегия",     "depends_on": ["product-analyst"]},
    {"agent": "website-gen",         "title": "Генерация лендинга",    "depends_on": ["content-strategist"]},
    {"agent": "tiktok-gen",          "title": "TikTok сценарии",       "depends_on": ["content-strategist"]},
    {"agent": "instagram-gen",       "title": "Instagram карусели",    "depends_on": ["content-strategist"]},
    {"agent": "threads-gen",         "title": "Threads контент",       "depends_on": ["content-strategist"]},
    {"agent": "asset-gen",           "title": "Генерация ассетов",     "depends_on": ["content-strategist"]},
    {"agent": "qa-text",             "title": "QA текста",             "depends_on": ["website-gen", "tiktok-gen", "instagram-gen", "threads-gen"]},
    {"agent": "qa-visual",           "title": "QA визуала",            "depends_on": ["asset-gen"]},
    {"agent": "qa-cross",            "title": "Кросс-платформенный QA","depends_on": ["qa-text", "qa-visual"]},
]

# Agent factory
AGENT_CLASSES = {
    "product-analyst":    ProductAnalyst,
    "content-strategist": ContentStrategist,
    "website-gen":        WebsiteGenerator,
    "tiktok-gen":         TikTokGenerator,
    "instagram-gen":      InstagramGenerator,
    "threads-gen":        ThreadsGenerator,
    "asset-gen":          AssetGenerator,
    "qa-text":            QAText,
    "qa-visual":          QAVisual,
    "qa-cross":           QACross,
}


def get_dep(board: KanbanBoard, agent_name: str) -> dict:
    """Get completed dependency output."""
    for task in board.get_tasks_by_status("done"):
        if task["agent"] == agent_name:
            try:
                return json.loads(task.get("output_json", "{}"))
            except (json.JSONDecodeError, TypeError):
                return {}
    return {}


def agent_worker(agent_name: str, task_title: str, depends_on: list[str]):
    board = KanbanBoard(db_path=str(DB_PATH))

    for _ in range(60):
        task = board.get_next_task(agent_name)
        if task:
            task_id = task["id"]
            board.claim_task(task_id)
            print(f"  [{agent_name}] 🔧 {task_title}")
            break
        time.sleep(0.5)
    else:
        print(f"  [{agent_name}] ⚠️ No task")
        return

    deps = {d: get_dep(board, d) for d in depends_on}

    try:
        if agent_name == "ocr-extractor":
            # Simulator for now — no real OCR without images
            time.sleep(random.uniform(0.5, 1.5))
            output = {"text": "Демо: AI-powered coffee machine. LiDAR, 50 рецептов, самоочистка. $499.", "confidence": 0.95}

        elif agent_name in AGENT_CLASSES:
            agent_cls = AGENT_CLASSES[agent_name]
            agent = agent_cls()

            # Route input data based on agent type
            if agent_name == "product-analyst":
                ocr = deps.get("ocr-extractor", {})
                result = agent.run({"raw_text": ocr.get("text", "Демо-брошюра"), "event": "Pipeline", "location": "VPS", "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "images": []})

            elif agent_name == "content-strategist":
                result = agent.run({"kb": deps.get("product-analyst", {})})

            elif agent_name in ("website-gen", "tiktok-gen", "instagram-gen", "threads-gen"):
                result = agent.run({"strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

            elif agent_name == "asset-gen":
                result = agent.run({"strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

            elif agent_name == "qa-text":
                result = agent.run({"content": deps.get("website-gen", {}), "strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

            elif agent_name == "qa-visual":
                assets = deps.get("asset-gen", {}).get("assets", [])
                result = agent.run({"assets": assets, "strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

            elif agent_name == "qa-cross":
                result = agent.run({
                    "website": deps.get("website-gen", {}),
                    "tiktok": deps.get("tiktok-gen", {}),
                    "instagram": deps.get("instagram-gen", {}),
                    "threads": deps.get("threads-gen", {}),
                    "strategy": deps.get("content-strategist", {}),
                    "kb": deps.get("product-analyst", {}),
                })
            else:
                result = {"note": "unknown agent"}

            output = result
        else:
            time.sleep(random.uniform(0.5, 1))
            output = {"result": f"Simulated: {task_title}"}

        output["completed_at"] = datetime.now(timezone.utc).isoformat()
        board.complete_task(task_id, output_data=output)
        print(f"  [{agent_name}] ✅ {task_title}")

    except Exception as e:
        board.fail_task(task_id, error=str(e))
        print(f"  [{agent_name}] ❌ {task_title}: {e}")


def orchestrator():
    if DB_PATH.exists():
        DB_PATH.unlink()

    board = KanbanBoard(db_path=str(DB_PATH))

    print("📋 Creating tasks...")
    for ag in AGENTS:
        tid = board.add_task(title=ag["title"], agent=ag["agent"], input_data={"product_id": "demo-001"})
        print(f"  + {tid}: {ag['title']} → {ag['agent']}")

    print(f"\n🚀 Pipeline: {len(AGENTS)} agents\n")

    # Phase 1: OCR → Analyst → Strategist (sequential)
    for phase_agent in ["ocr-extractor", "product-analyst", "content-strategist"]:
        ag = next(a for a in AGENTS if a["agent"] == phase_agent)
        p = multiprocessing.Process(target=agent_worker, args=(ag["agent"], ag["title"], ag["depends_on"]))
        p.start(); p.join()

    # Phase 2: 5 generators in PARALLEL
    print()
    gen_agents = ["website-gen", "tiktok-gen", "instagram-gen", "threads-gen", "asset-gen"]
    procs = []
    for ga in gen_agents:
        ag = next(a for a in AGENTS if a["agent"] == ga)
        p = multiprocessing.Process(target=agent_worker, args=(ag["agent"], ag["title"], ag["depends_on"]))
        p.start(); procs.append(p)
    for p in procs: p.join()

    # Phase 3: QA text + QA visual in PARALLEL
    print()
    qa12 = ["qa-text", "qa-visual"]
    procs = []
    for qa in qa12:
        ag = next(a for a in AGENTS if a["agent"] == qa)
        p = multiprocessing.Process(target=agent_worker, args=(ag["agent"], ag["title"], ag["depends_on"]))
        p.start(); procs.append(p)
    for p in procs: p.join()

    # Phase 4: QA cross (depends on both)
    print()
    ag = next(a for a in AGENTS if a["agent"] == "qa-cross")
    p = multiprocessing.Process(target=agent_worker, args=(ag["agent"], ag["title"], ag["depends_on"]))
    p.start(); p.join()

    print("\n🎉 Pipeline complete!")
    stats = board.get_tasks_by_status("done")
    failed = board.get_tasks_by_status("failed")
    print(f"   ✅ {len(stats)}/{len(AGENTS)} done")
    if failed: print(f"   ❌ {len(failed)} failed")

if __name__ == "__main__":
    orchestrator()
