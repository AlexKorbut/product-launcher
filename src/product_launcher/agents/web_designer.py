"""
Web Designer Agent — creates standalone HTML landing pages using Claude Design approach.
Produces self-contained HTML/CSS artifacts, not just section descriptions.
"""
import json, os
from pathlib import Path
from . import BaseAgent, LLMClient


DESIGNER_PROMPT = """Ты — веб-дизайнер. Создай самодостаточный HTML-лендинг для продукта.

Твоя задача — написать ПОЛНЫЙ HTML-файл (CSS в <style>, JS в <script>), который:
- Открывается в браузере и выглядит законченным
- Использует современный CSS (grid, variables, container queries)
- Тёмная тема (dark theme) по умолчанию
- Минимум 4 секции: hero, features, social-proof, cta
- Реальные тексты из брифа (не lorem ipsum)
- Адаптивный дизайн (mobile-first)
- Без внешних зависимостей (никаких CDN)

Дизайн-правила:
- Никаких градиентов без причины
- Никакого glassmorphism по умолчанию
- Типографика как иерархия (не добавляй иконки без смысла)
- Минимум эмодзи (только если бренд их использует)
- Настоящие hover/focus состояния
- Уважай prefers-reduced-motion

Верни ТОЛЬКО валидный JSON с HTML внутри:

{
  "html": "<!DOCTYPE html>\\n<html lang=\\"ru\\">\\n...полный HTML...\\n</html>",
  "meta": {
    "title": "SEO title",
    "description": "SEO description",
    "sections": ["hero", "features", "social_proof", "cta"],
    "colors_used": ["#hex1", "#hex2"],
    "typography": "Название шрифта"
  }
}

ВАЖНО: Весь HTML должен быть внутри поля "html" как одна строка с экранированными кавычками.
Используй \\n для переносов строк, \\" для кавычек внутри HTML.
"""


class WebDesigner(BaseAgent):
    """Creates standalone HTML landing pages using Claude Design principles."""

    agent_name = "website-gen"
    description = "Веб-дизайнер: создаёт самодостаточные HTML-лендинги (Claude Design подход)"

    def run(self, input_data: dict) -> dict:
        """
        Args:
            input_data: {"strategy": ..., "kb": ...}

        Returns:
            {"html": "...", "meta": {...}, "file_path": "..."}
        """
        strategy = input_data.get("strategy", {})
        kb = input_data.get("kb", {})

        product = kb.get("product", {})
        brand = kb.get("brand", {})
        colors = brand.get("colors", {})
        tone = strategy.get("tone_of_voice", {})

        self.log(f"Дизайню лендинг для: {product.get('name', 'Продукт')}")

        prompt = self._build_brief(strategy, kb)
        messages = [
            {"role": "system", "content": DESIGNER_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.chat(messages, temperature=0.8, max_tokens=8192)
        result = self._parse(response)

        if not result or "html" not in result:
            self.log("⚠️ Fallback HTML")
            result = self._fallback_html(strategy, kb)

        # Save to file
        file_path = self._save_html(result.get("html", ""), kb)

        result["file_path"] = file_path
        result.setdefault("meta", {})
        
        sections = len(result.get("meta", {}).get("sections", []))
        self.log(f"✓ Лендинг: {file_path} ({sections} секций)")
        return result

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

        if product.get("price_range"):
            parts.append(f"Цена: {product['price_range']}")

        parts.append(f"\n## Бренд")
        parts.append(f"Тон: {tone.get('primary', 'professional')}")
        parts.append(f"Основной цвет: {colors.get('primary', '#1A1A2E')}")
        parts.append(f"Вторичный: {colors.get('secondary', '#16213E')}")
        parts.append(f"Акцентный: {colors.get('accent', '#E94560')}")

        hooks = strategy.get("target_hooks", [])
        if hooks:
            parts.append(f"\n## Ключевые сообщения")
            for h in hooks[:5]:
                parts.append(f"- {h}")

        ws = strategy.get("platforms", {}).get("website", {})
        if ws:
            sections = ws.get("sections", ["Hero", "Features", "CTA"])
            parts.append(f"\n## Структура лендинга")
            parts.append(f"Секции: {', '.join(sections)}")
            parts.append(f"Тон: {ws.get('tone_notes', 'Продающий, доверительный')}")

        return "\n".join(parts)

    def _parse(self, response: str) -> dict | None:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find("{")
            end = response.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end + 1])
                except json.JSONDecodeError:
                    pass
        return None

    def _fallback_html(self, strategy: dict, kb: dict) -> dict:
        """Standalone HTML when LLM unavailable."""
        product = kb.get("product", {})
        brand = kb.get("brand", {})
        colors = brand.get("colors", {})
        c1 = colors.get("primary", "#0d1117")
        c2 = colors.get("secondary", "#161b22")
        c3 = colors.get("accent", "#58a6ff")

        name = product.get("name", "Продукт")
        usp = product.get("usp", "Инновационное решение")
        features = product.get("features", ["Фича 1", "Фича 2", "Фича 3"])
        price = product.get("price_range", "Узнать цену")

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — {usp}</title>
<style>
:root {{
  --bg: {c1};
  --surface: {c2};
  --accent: {c3};
  --text: #c9d1d9;
  --muted: #8b949e;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  line-height: 1.6;
}}
.container {{ max-width: 1100px; margin: 0 auto; padding: 0 24px; }}

/* Hero */
.hero {{
  padding: 120px 0 80px;
  text-align: center;
  background: linear-gradient(180deg, var(--bg) 0%, var(--surface) 100%);
}}
.hero h1 {{ font-size: clamp(36px, 8vw, 64px); margin-bottom: 16px; }}
.hero p {{ font-size: 20px; color: var(--muted); max-width: 600px; margin: 0 auto 32px; }}
.btn {{
  display: inline-block;
  padding: 14px 40px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: transform .15s, box-shadow .15s;
}}
.btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,.3); }}
.btn:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 2px; }}

/* Features */
.features {{
  padding: 80px 0;
}}
.features h2 {{
  text-align: center;
  font-size: 32px;
  margin-bottom: 48px;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}}
.card {{
  background: var(--surface);
  border: 1px solid rgba(255,255,255,.06);
  border-radius: 12px;
  padding: 32px;
  transition: transform .15s;
}}
.card:hover {{ transform: translateY(-4px); }}
.card h3 {{ font-size: 18px; margin-bottom: 8px; }}
.card p {{ color: var(--muted); font-size: 14px; }}

/* CTA */
.cta {{
  padding: 80px 0;
  text-align: center;
  background: var(--surface);
  border-radius: 16px;
  margin: 0 24px 80px;
}}
.cta h2 {{ font-size: 32px; margin-bottom: 16px; }}
.cta p {{ color: var(--muted); margin-bottom: 32px; }}

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
    <a href="#" class="btn">Предзаказать</a>
  </div>
</section>

<section class="features">
  <div class="container">
    <h2>Ключевые возможности</h2>
    <div class="grid">
      {''.join(f'<div class="card"><h3>{f}</h3><p>Описание фичи</p></div>' for f in features)}
    </div>
  </div>
</section>

<section class="cta">
  <div class="container">
    <h2>Готовы попробовать?</h2>
    <p>{price} • Доставка по всей России</p>
    <a href="#" class="btn">Оформить предзаказ</a>
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
                "colors_used": [c1, c2, c3],
                "typography": "System font stack",
            },
        }

    def _save_html(self, html: str, kb: dict) -> str:
        """Save HTML to file, return path."""
        product_name = kb.get("product", {}).get("name", "product")
        safe_name = "".join(c if c.isalnum() else "-" for c in product_name).lower()

        # Ensure output directory
        output_dir = Path(__file__).resolve().parent.parent.parent.parent / "output"
        output_dir.mkdir(exist_ok=True)

        # Find next available filename
        counter = 1
        while True:
            path = output_dir / f"{safe_name}-v{counter}.html"
            if not path.exists():
                break
            counter += 1

        # Escape unicode in HTML for proper writing
        if isinstance(html, str):
            path.write_text(html, encoding="utf-8")
        else:
            path.write_text(str(html), encoding="utf-8")

        return str(path)
