import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from product_launcher.kanban import KanbanBoard

board = KanbanBoard(db_path=str(Path(__file__).resolve().parent / "kanban_live.db"))

out_dir = Path(__file__).resolve().parent / "output"

for task in board.get_tasks_by_status("done"):
    agent = task["agent"]
    output = json.loads(task.get("output_data", "{}"))
    
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"[{agent}] {task['title']}")
    print(f"Keys: {list(output.keys())}")
    
    # Show content
    if agent == "tiktok-gen":
        scripts = output.get("scripts", [])
        print(f"Scripts: {len(scripts)}")
        for s in scripts[:3]:
            title = s.get("title", "?")
            text = s.get("text", "")[:150]
            print(f"  - {title}: {text}...")
    elif agent == "instagram-gen":
        posts = output.get("posts", [])
        print(f"Posts: {len(posts)}")
        for p in posts[:3]:
            caption = p.get("caption", "")[:150]
            print(f"  - {caption}...")
    elif agent == "threads-gen":
        threads = output.get("threads", [])
        print(f"Threads: {len(threads)}")
        for t in threads[:3]:
            title = t.get("title", "?")
            text = t.get("text", "")[:150]
            print(f"  - {title}: {text}...")
    elif agent == "asset-gen":
        assets = output.get("assets", [])
        print(f"Assets: {len(assets)}")
        for a in assets[:5]:
            print(f"  - {a.get('name', '?')}: {a.get('description', '')[:100]}...")
    elif "qa" in agent:
        print(f"Score: {output.get('score', '?')}/100")
        issues = output.get("issues", [])
        print(f"Issues ({len(issues)}):")
        for i in issues[:5]:
            print(f"  - {i}")
        recommendations = output.get("recommendations", [])
        if recommendations:
            print(f"Recommendations:")
            for r in recommendations[:3]:
                print(f"  - {r}")
    elif agent == "website-gen":
        print(f"HTML length: {len(output.get('html', ''))}")
    elif agent == "content-strategist":
        strategy_name = output.get("strategy_name", "?")
        pillars = len(output.get("content_pillars", []))
        hooks = len(output.get("target_hooks", []))
        print(f"Strategy: {strategy_name}")
        print(f"Pillars: {pillars}, Hooks: {hooks}")
    elif agent == "product-analyst":
        product = output.get("product", {})
        print(f"Product: {product.get('name', '?')}")
        print(f"Features: {len(product.get('features', []))}")
    elif agent == "ocr-extractor":
        print(f"Text length: {len(output.get('text', ''))}")
        print(f"Confidence: {output.get('confidence', '?')}")
    else:
        out_str = json.dumps(output, ensure_ascii=False)
        print(f"Output: {out_str[:250]}...")
    
    # Save SMM content to files
    if agent in ("tiktok-gen", "instagram-gen", "threads-gen"):
        fname = out_dir / f"{agent}-content.json"
        fname.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  💾 Saved: {fname}")
