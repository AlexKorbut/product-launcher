"""
Web Designer Agent — creates standalone HTML landing pages using Claude Design approach.
Produces self-contained HTML/CSS artifacts, not just section descriptions.
v2: Generates raw HTML directly (LLMs struggle with JSON+HTML escaping).
"""
import json, os, re
from pathlib import Path
from . import BaseAgent, LLMClient


DESIGNER_PROMPT = """Ты — веб-дизайнер. Создай самодостаточный HTML-лендинг для продукта.

Напиши ПОЛНЫЙ HTML-файл (CSS в <style>, JS в <script>), который:
- Открывается в браузере и выглядит законченным
- Тёмная тема (dark theme)
- Минимум 4 секции: hero, features, social-proof, cta
- Реальные тексты из брифа (не lorem ipsum)
- Адаптивный дизайн (mobile-first)
- Без внешних зависимостей (никаких CDN)
- Светлая тема #f4f2ed, швейцарский брутализм (сетка, геометрия, 1 акцент #d4532a)
- Запрещено: стекломорфизм, rainbow, SaaS-карточки, stock-photo

Выдай ТОЛЬКО HTML код. Никаких пояснений, никакого markdown-форматирования.
Начинай сразу с <!DOCTYPE html> и заканчивай </html>.
Не оборачивай в ```html``` или JSON."""


class WebDesigner(BaseAgent):
    """Creates standalone HTML landing pages using Claude Design principles."""

    agent_name = "website-gen"
    description = "Веб-дизайнер: создаёт самодостаточные HTML-лендинги (Claude Design подход)"

    def run(self, input_data: dict) -> dict:
        strategy = input_data.get("strategy", {})
        kb = input_data.get("kb", {})

        product = kb.get("product", {})
        self.log(f"Дизайню лендинг для: {product.get('name', 'Продукт')}")

        prompt = self._build_brief(strategy, kb)
        messages = [
            {"role": "system", "content": DESIGNER_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.chat(messages, temperature=0.7, max_tokens=8192)
        html = self._extract_html(response)

        if not html or len(html) < 200:
            self.log("⚠️ LLM не сгенерировал HTML, fallback")
            result = self._fallback_html(strategy, kb)
            html = result["html"]

        meta = self._extract_meta(html, strategy, kb)

        # Save to file
        file_path = self._save_html(html, kb)

        sections = len(meta.get("sections", []))
        self.log(f"✓ Лендинг: {file_path} ({sections} секций, {len(html)} символов)")
        
        return {"html": html, "meta": meta, "file_path": str(file_path)}

    def _extract_html(self, response: str) -> str:
        """Extract HTML from LLM response, handling various wrappers."""
        # Try to find <!DOCTYPE html>... </html>
        m = re.search(r'(<!DOCTYPE\s+html[^>]*>.*?</html>)', response, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1)
        
        # Try to find <html>...</html>
        m = re.search(r'(<html[^>]*>.*?</html>)', response, re.DOTALL | re.IGNORECASE)
        if m:
            return f"<!DOCTYPE html>\n{m.group(1)}"
        
        # Try to strip markdown code blocks
        m = re.search(r'```(?:html)?\s*\n(.*?)\n```', response, re.DOTALL)
        if m:
            inner = m.group(1)
            return self._extract_html(inner)  # Recursive
        
        # Try JSON with "html" key
        try:
            data = json.loads(response)
            if "html" in data:
                return data["html"]
        except:
            pass
        
        return ""

    def _extract_meta(self, html: str, strategy: dict, kb: dict) -> dict:
        """Extract metadata from generated HTML."""
        meta = {"title": "", "description": "", "sections": [], "colors_used": []}
        
        # Extract title
        m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if m:
            meta["title"] = m.group(1)
        
        # Extract description
        m = re.search(r'<meta\s+name="description"\s+content="(.*?)"', html, re.IGNORECASE)
        if m:
            meta["description"] = m.group(1)
        
        # Detect sections from class names or IDs
        section_patterns = [
            (r'class="([^"]*hero[^"]*)"', "hero"),
            (r'id="([^"]*hero[^"]*)"', "hero"),
            (r'class="([^"]*featur[^"]*)"', "features"),
            (r'id="([^"]*featur[^"]*)"', "features"),
            (r'class="([^"]*social[^"]*)"', "social_proof"),
            (r'class="([^"]*proof[^"]*)"', "social_proof"),
            (r'class="([^"]*testimonial[^"]*)"', "social_proof"),
            (r'class="([^"]*cta[^"]*)"', "cta"),
            (r'id="([^"]*cta[^"]*)"', "cta"),
            (r'class="([^"]*pric[^"]*)"', "pricing"),
            (r'class="([^"]*model[^"]*)"', "models"),
            (r'class="([^"]*faq[^"]*)"', "faq"),
        ]
        
        seen = set()
        for pattern, name in section_patterns:
            if re.search(pattern, html, re.IGNORECASE) and name not in seen:
                meta["sections"].append(name)
                seen.add(name)
        
        # If no sections detected, count <section> tags
        if not meta["sections"]:
            count = len(re.findall(r'<section[^>]*>', html, re.IGNORECASE))
            if count:
                meta["sections"] = [f"section_{i}" for i in range(1, count + 1)]
        
        # Extract colors
        colors = set()
        for m in re.finditer(r'#[0-9A-Fa-f]{6}', html):
            colors.add(m.group(0))
        meta["colors_used"] = list(colors)[:10]
        
        meta["typography"] = "System font stack"
        return meta

    def _build_brief(self, strategy: dict, kb: dict) -> str:
        """Build design brief from strategy + KB."""
        product = kb.get("product", {})
        brand = kb.get("brand", {})
        colors = brand.get("colors", {})
        tone = strategy.get("tone_of_voice", {})

        parts = [
            "## Дизайн-бриф",
            f"Продукт: {product.get('name', '—')}",
            f"УТП: {product.get('usp', '—')}",
            f"Описание: {product.get('description', '—')}",
        ]

        features = product.get("features", [])
        if features:
            parts.append(f"Фичи: {', '.join(features)}")

        specs = product.get("specs", {})
        if specs:
            parts.append(f"Характеристики: {json.dumps(specs, ensure_ascii=False)}")

        part = "## Требования к дизайну"
        part += "\n- Светлая тема, фон #f4f2ed, швейцарский брутализм"
        part += "\n- 1 акцентный цвет #d4532a (тёплый оранжево-красный)"
        part += "\n- Геометрическая сетка, чёткая иерархия, минимум украшений"
        part += "\n- НИКАКОГО стекломорфизма, rainbow, SaaS-карточек, стоковых фото"
        part += "\n- Шрифты системные (без CDN)"
        part += "\n- Минимум 4 секции"
        parts.append(part)

        hooks = strategy.get("target_hooks", [])
        if hooks:
            parts.append("\n## Ключевые сообщения")
            for h in hooks[:5]:
                parts.append(f"- {h}")

        ws = strategy.get("platforms", {}).get("website", {})
        if ws:
            sections = ws.get("sections", ["Hero", "Features", "CTA"])
            parts.append(f"\n## Структура лендинга")
            parts.append(f"Секции: {', '.join(sections)}")
            parts.append(f"Тон: {ws.get('tone_notes', 'Продающий, доверительный')}")

        return "\n".join(parts)

    def _fallback_html(self, strategy: dict, kb: dict) -> dict:
        """Standalone HTML when LLM unavailable."""
        product = kb.get("product", {})
        name = product.get("name", "Продукт")
        usp = product.get("usp", "Инновационное решение")
        features = product.get("features", ["Фича 1", "Фича 2", "Фича 3"])

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — {usp}</title>
<style>
:root {{
  --bg: #f4f2ed;
  --surface: #ffffff;
  --accent: #d4532a;
  --text: #1a1a1a;
  --muted: #6b6b6b;
  --border: #d9d7d2;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  line-height: 1.6;
}}
.container {{ max-width: 1100px; margin: 0 auto; padding: 0 24px; }}
.hero {{
  padding: 120px 0 80px;
  border-bottom: 2px solid var(--accent);
}}
.hero h1 {{ font-size: clamp(36px, 8vw, 64px); margin-bottom: 16px; font-weight: 900; }}
.hero p {{ font-size: 20px; color: var(--muted); max-width: 600px; }}
.btn {{
  display: inline-block; margin-top: 32px;
  padding: 14px 40px;
  background: var(--accent);
  color: #fff; border: none;
  font-size: 16px; font-weight: 700;
  cursor: pointer; text-decoration: none;
  transition: transform .15s;
}}
.btn:hover {{ transform: translateY(-2px); }}
.features {{ padding: 80px 0; }}
.features h2 {{ font-size: 32px; margin-bottom: 48px; font-weight: 800; }}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}}
.card {{
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 32px;
}}
.card h3 {{ font-size: 18px; margin-bottom: 8px; font-weight: 700; }}
.card p {{ color: var(--muted); font-size: 14px; }}
.cta {{
  padding: 80px 0;
  text-align: center;
  background: var(--text);
  color: var(--bg);
  margin-top: 40px;
}}
.cta h2 {{ font-size: 32px; margin-bottom: 16px; }}
.cta p {{ color: #aaa; margin-bottom: 32px; }}
.cta .btn {{ background: var(--accent); }}
@media (prefers-reduced-motion: reduce) {{
  * {{ transition: none !important; animation: none !important; }}
}}
</style>
</head>
<body>
<section class="hero">
  <div class="container">
    <h1>{name}</h1>
    <p>{usp}</p>
    <a href="#" class="btn">Получить консультацию</a>
  </div>
</section>
<section class="features">
  <div class="container">
    <h2>Ключевые возможности</h2>
    <div class="grid">
      {''.join(f'<div class="card"><h3>{f}</h3><p>{f} — автоматизировано с точностью ИИ</p></div>' for f in features)}
    </div>
  </div>
</section>
<section class="cta">
  <div class="container">
    <h2>Готовы оптимизировать клинику?</h2>
    <p>5 специалистов в одном устройстве • 10 пациентов в день • Окупаемость за 3 месяца</p>
    <a href="#" class="btn">Запросить демо</a>
  </div>
</section>
</body>
</html>"""

        return {
            "html": html,
            "meta": {
                "title": f"{name} | Официальный сайт",
                "description": usp,
                "sections": ["hero", "features", "cta"],
                "colors_used": ["#f4f2ed", "#d4532a", "#1a1a1a"],
                "typography": "System font stack",
            },
        }

    def _save_html(self, html: str, kb: dict) -> str:
        """Save HTML to file, return path."""
        product_name = kb.get("product", {}).get("name", "product")
        safe_name = "".join(c if c.isalnum() else "-" for c in product_name).lower()

        output_dir = Path(__file__).resolve().parent.parent.parent.parent / "output"
        output_dir.mkdir(exist_ok=True)

        counter = 1
        while True:
            path = output_dir / f"{safe_name}-v{counter}.html"
            if not path.exists():
                break
            counter += 1

        path.write_text(html, encoding="utf-8")
        return str(path)
