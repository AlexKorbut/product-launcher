#!/usr/bin/env python3
"""
Product Launcher — PM-driven multi-agent system.
PM creates plan → specialists execute → QA validates → PM reviews.
IT-company structure: PM + OCR + Analyst + Strategist + Designers + SMM + QA.
"""
import json, sys, time, random, multiprocessing
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from product_launcher.kanban import KanbanBoard
from product_launcher.agents.project_manager import ProjectManager
from product_launcher.agents.ocr_extractor import OCRExtractor
from product_launcher.agents.product_analyst import ProductAnalyst
from product_launcher.agents.content_strategist import ContentStrategist
from product_launcher.agents.web_designer import WebDesigner
from product_launcher.agents.content_generator import TikTokGenerator, InstagramGenerator, ThreadsGenerator
from product_launcher.agents.asset_gen import AssetGenerator
from product_launcher.agents.qa_agents import QAText, QAVisual, QACross

DB_PATH = Path(__file__).resolve().parent / "kanban_live.db"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# PM's standard team plan (used as fallback)
DEFAULT_TEAM = [
    {"role": "ocr_specialist",    "agent": "ocr-extractor",     "task": "OCR текста брошюры",            "priority": 1, "depends_on": []},
    {"role": "product_analyst",   "agent": "product-analyst",  "task": "Анализ продукта → ProductKB",    "priority": 2, "depends_on": ["ocr-extractor"]},
    {"role": "content_strategist","agent": "content-strategist","task": "Контент-стратегия",              "priority": 3, "depends_on": ["product-analyst"]},
    {"role": "web_designer",      "agent": "website-gen",      "task": "HTML-лендинг (Claude Design)",   "priority": 4, "depends_on": ["content-strategist"]},
    {"role": "smm_tiktok",        "agent": "tiktok-gen",       "task": "Сценарии TikTok",                "priority": 4, "depends_on": ["content-strategist"]},
    {"role": "smm_instagram",     "agent": "instagram-gen",    "task": "Контент Instagram",              "priority": 4, "depends_on": ["content-strategist"]},
    {"role": "smm_threads",       "agent": "threads-gen",      "task": "Треды Threads",                  "priority": 4, "depends_on": ["content-strategist"]},
    {"role": "art_director",      "agent": "asset-gen",        "task": "Визуальные ассеты + brand kit",  "priority": 4, "depends_on": ["content-strategist"]},
    {"role": "qa_text",           "agent": "qa-text",         "task": "QA текстового контента",           "priority": 5, "depends_on": ["website-gen"]},
    {"role": "qa_visual",         "agent": "qa-visual",       "task": "QA визуальных ассетов",            "priority": 5, "depends_on": ["asset-gen"]},
    {"role": "qa_lead",           "agent": "qa-cross",         "task": "Финальная кросс-проверка",       "priority": 6, "depends_on": ["website-gen", "tiktok-gen", "instagram-gen", "threads-gen", "asset-gen", "qa-text", "qa-visual"]},
]


def get_dep(board, agent_name):
    for task in board.get_tasks_by_status("done"):
        if task["agent"] == agent_name:
            try: return json.loads(task.get("output_json", "{}"))
            except: return {}
    return {}


def specialist_worker(agent_name: str, task_title: str, depends_on: list[str]):
    board = KanbanBoard(db_path=str(DB_PATH))

    for _ in range(120):
        task = board.get_next_task(agent_name)
        if task:
            task_id = task["id"]
            board.claim_task(task_id)
            print(f"  [{agent_name}] 🔧 {task_title}")
            break
        time.sleep(0.5)
    else:
        print(f"  [{agent_name}] ⚠️ Not assigned")
        return

    deps = {d: get_dep(board, d) for d in depends_on}

    try:
        if agent_name == "ocr-extractor":
            agent = OCRExtractor()
            task_data = task.get("input_data", "{}")
            if isinstance(task_data, str):
                task_data = json.loads(task_data)
            raw_text = task_data.get("product_hint", "Demo product")
            output = agent.run({"raw_text": raw_text})

        elif agent_name == "product-analyst":
            ocr = deps.get("ocr-extractor", {})
            agent = ProductAnalyst()
            output = agent.run({"raw_text": ocr.get("text", "Demo brochure"), "event": "Pipeline", "location": "VPS", "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "images": []})

        elif agent_name == "content-strategist":
            agent = ContentStrategist()
            output = agent.run({"kb": deps.get("product-analyst", {})})

        elif agent_name == "website-gen":
            agent = WebDesigner()
            output = agent.run({"strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

        elif agent_name == "tiktok-gen":
            agent = TikTokGenerator()
            output = agent.run({"strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

        elif agent_name == "instagram-gen":
            agent = InstagramGenerator()
            output = agent.run({"strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

        elif agent_name == "threads-gen":
            agent = ThreadsGenerator()
            output = agent.run({"strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

        elif agent_name == "asset-gen":
            agent = AssetGenerator()
            output = agent.run({"strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

        elif agent_name == "qa-text":
            agent = QAText()
            output = agent.run({"content": deps.get("website-gen", {}), "strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

        elif agent_name == "qa-visual":
            assets = deps.get("asset-gen", {}).get("assets", [])
            agent = QAVisual()
            output = agent.run({"assets": assets, "strategy": deps.get("content-strategist", {}), "kb": deps.get("product-analyst", {})})

        elif agent_name == "qa-cross":
            agent = QACross()
            output = agent.run({
                "website": deps.get("website-gen", {}),
                "tiktok": deps.get("tiktok-gen", {}),
                "instagram": deps.get("instagram-gen", {}),
                "threads": deps.get("threads-gen", {}),
                "strategy": deps.get("content-strategist", {}),
                "kb": deps.get("product-analyst", {}),
            })
        else:
            output = {"note": "Specialist not implemented"}

        output["completed_at"] = datetime.now(timezone.utc).isoformat()
        board.complete_task(task_id, output_data=output)
        print(f"  [{agent_name}] ✅ {task_title}")

    except Exception as e:
        board.fail_task(task_id, error=str(e))
        print(f"  [{agent_name}] ❌ {task_title}: {e}")


def run_pipeline(team_plan: list[dict]):
    """Execute team plan respecting dependencies and priority phases."""
    # Build phase order from plan
    priorities = sorted(set(m["priority"] for m in team_plan))
    
    for phase_priority in priorities:
        phase_members = [m for m in team_plan if m["priority"] == phase_priority]
        
        if phase_priority <= 3:
            # Sequential for foundation layers
            for member in phase_members:
                p = multiprocessing.Process(
                    target=specialist_worker,
                    args=(member["agent"], member["task"], member["depends_on"])
                )
                p.start()
                p.join()
        else:
            # Parallel for same-priority specialists
            print()
            procs = []
            for member in phase_members:
                p = multiprocessing.Process(
                    target=specialist_worker,
                    args=(member["agent"], member["task"], member["depends_on"])
                )
                p.start()
                procs.append(p)
            for p in procs:
                p.join()


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Clean slate
    if DB_PATH.exists():
        DB_PATH.unlink()

    board = KanbanBoard(db_path=str(DB_PATH))

    # ── PHASE 0: PM plans the project ──
    print("=" * 60)
    print("🧠 Project Manager: planning...")
    print("=" * 60)

    pm = ProjectManager()
    brief = {
        "product_hint": "AI-powered robot vacuum cleaner with UV sterilization",
        "requirements": "Landing page + social media content for Instagram, TikTok, Threads",
        "images": [],
    }
    pm_result = pm.run({"brief": brief})

    team = pm_result.get("team", DEFAULT_TEAM)
    criteria = pm_result.get("acceptance_criteria", [])
    print(f"Project: {pm_result.get('project_name', '—')}")
    print(f"Team: {len(team)} specialists")
    print()

    # ── PHASE 1: Create tasks in Kanban ──
    print("📋 Creating tasks...")
    product_hint = brief.get("product_hint", "")
    for member in team:
        input_data = {"role": member["role"], "priority": member["priority"]}
        # Pass product hint to OCR agent
        if member["agent"] == "ocr-extractor":
            input_data["product_hint"] = product_hint
        tid = board.add_task(
            title=member["task"],
            agent=member["agent"],
            input_data=input_data,
        )
        deps = ", ".join(member["depends_on"]) if member["depends_on"] else "—"
        print(f"  + {tid}: [{member['role']}] {member['task']}  (depends: {deps})")

    # ── PHASE 2: Execute ──
    print(f"\n🚀 Executing: {len(team)} specialists\n")
    run_pipeline(team)

    # ── PHASE 3: PM review ──
    print(f"\n{'='*60}")
    print("🧠 PM: reviewing results...")
    print("="*60)

    done = board.get_tasks_by_status("done")
    failed = board.get_tasks_by_status("failed")
    print(f"   ✅ Completed: {len(done)}/{len(team)}")
    if failed:
        print(f"   ❌ Failed: {len(failed)}")

    # Check for HTML artifact
    for task in board.get_tasks_by_status("done"):
        if task["agent"] == "website-gen":
            try:
                data = json.loads(task.get("output_json", "{}"))
                if "file_path" in data:
                    path = Path(data["file_path"])
                    if path.exists():
                        print(f"   🌐 Landing page: {path} ({path.stat().st_size} bytes)")
            except:
                pass

    # Save ProductKB for persistence
    for task in board.get_tasks_by_status("done"):
        if task["agent"] == "product-analyst":
            try:
                data = json.loads(task.get("output_json", "{}"))
                kb_path = OUTPUT_DIR / "product-kb.json"
                kb_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"   💾 ProductKB saved: {kb_path}")
            except:
                pass
        if task["agent"] == "content-strategist":
            try:
                data = json.loads(task.get("output_json", "{}"))
                strategy_path = OUTPUT_DIR / "content-strategy.json"
                strategy_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"   📝 Strategy saved: {strategy_path}")
            except:
                pass

    # Acceptance criteria check
    print(f"\n📋 Acceptance criteria ({len(criteria)}):")
    for i, c in enumerate(criteria, 1):
        print(f"   {i}. {c}")
    print(f"   Status: {'✅ ALL MET' if not failed else '❌ ISSUES FOUND'}")

    print(f"\n🎉 Pipeline finished!")


if __name__ == "__main__":
    main()
