"""Populate output subdirectories with readable content."""
import json, shutil
from pathlib import Path

OUT = Path("/home/cobra/myai/product-launcher/output")

# ── TikTok ──
with open(OUT / "tiktok-gen-content.json") as f:
    data = json.load(f)

md = "# SIBERT — TikTok Scripts\n\n"
for s in data.get("scripts", []):
    md += f'## {s.get("hook", "Сценарий")}\n'
    md += f'Длительность: {s.get("duration_sec", "?")}с | Хештеги: {" ".join(s.get("hashtags", []))}\n\n'
    for scene in s.get("scenes", []):
        md += f'### {scene.get("time", "?")}\n'
        md += f'- **Видео:** {scene.get("visual", "")}\n'
        md += f'- **Текст:** {scene.get("text", "")}\n'
        md += f'- **Звук:** {scene.get("sound", "")}\n\n'
    md += "---\n\n"

(OUT / "tiktok" / "scripts.md").write_text(md, encoding="utf-8")
print("TikTok: done")

# ── Instagram ──
with open(OUT / "instagram-gen-content.json") as f:
    data = json.load(f)

md = "# SIBERT — Instagram Content\n\n"
for c in data.get("carousels", []):
    md += f'## Карусель: {c.get("id", "?")}\n\n'
    for i, slide in enumerate(c.get("slides", []), 1):
        md += f"### Слайд {i}\n"
        md += f'- **Изображение:** {slide.get("image_desc", "")}\n'
        md += f'- **Текст:** {slide.get("text", "")}\n\n'
    md += f'**Caption:** {c.get("caption", "")}\n\n'
    md += f'**Хештеги:** {" ".join(c.get("hashtags", []))}\n\n'
    md += "---\n\n"

for r in data.get("reels", []):
    md += f'## Reels: {r.get("hook", "?")}\n'
    md += f'Длительность: {r.get("duration_sec", "?")}с\n'
    md += f'{r.get("description", "")}\n\n'

(OUT / "instagram" / "posts.md").write_text(md, encoding="utf-8")
print("Instagram: done")

# ── Threads ──
with open(OUT / "threads-gen-content.json") as f:
    data = json.load(f)

md = "# SIBERT — Threads Content\n\n"
for t in data.get("threads", []):
    md += f'## {t.get("title", "Тред")}\n\n'
    for post in t.get("posts", []):
        md += f"{post}\n\n"
    md += "---\n\n"

(OUT / "threads" / "threads.md").write_text(md, encoding="utf-8")
print("Threads: done")

# ── Website ──
shutil.copy(OUT / "sibert-tcm-robot-v1.html", OUT / "website" / "sibert-tcm-robot-v1.html")
shutil.copy(OUT / "product-v5.html", OUT / "website" / "product-v5.html")
print("Website: done")

# ── Assets ──
with open(OUT / f"../kanban_live.db", "rb") as f:
    pass  # just checking it exists

print("\nDone! All folders populated.")
