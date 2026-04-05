from __future__ import annotations

from datetime import datetime
from html import escape

from playwright.sync_api import BrowserContext

from config import ROOT_DIR, RUN_IMAGE_DIR
from utils import cleanup_text, slugify


CARD_WIDTH = 1120
CARD_HEIGHT = 760
CARD_VIEWPORT_HEIGHT = 900


def _format_number(value: int | None) -> str:
    if not value:
        return "0"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _format_parameters(value: int | None) -> str:
    if not value:
        return "Unknown"
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    return str(value)


def _provider_line(model: dict) -> str:
    providers = [item.get("provider", "") for item in model.get("availableInferenceProviders", []) if item.get("provider")]
    if not providers:
        return "Community release"
    unique = []
    seen = set()
    for provider in providers:
        if provider in seen:
            continue
        seen.add(provider)
        unique.append(provider.title())
        if len(unique) >= 3:
            break
    return " · ".join(unique)


def _tag_line(model: dict) -> str:
    pipeline_tag = cleanup_text(model.get("pipelineTag", "")).replace("-", " ").title() or "General AI"
    params = _format_parameters(model.get("numParameters"))
    return f"{pipeline_tag} | {params} params"


def _updated_line(model: dict) -> str:
    raw_value = model.get("lastModified", "")
    if not raw_value:
        return "Updated recently"
    try:
        moment = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        return f"Updated {moment.strftime('%Y-%m-%d')}"
    except ValueError:
        return "Updated recently"


def _summary_text(model: dict) -> str:
    summary = cleanup_text(model.get("modelDescription", "")) or cleanup_text(model.get("sourceDescription", ""))
    return escape(summary[:180])


def _metric_chip(label: str, value: str) -> str:
    return (
        f"<div class='metric'>"
        f"<span class='metric-label'>{escape(label)}</span>"
        f"<span class='metric-value'>{escape(value)}</span>"
        f"</div>"
    )


def _build_card_html(model: dict, rank: int) -> str:
    model_name = cleanup_text(model.get("modelName", "Unknown model"))
    title = model_name.split("/")[-1]
    author = model.get("author") or model_name.split("/")[0]
    initial = (author[:1] or "H").upper()
    provider_line = _provider_line(model)
    metrics = "".join(
        [
            _metric_chip("Downloads", _format_number(model.get("downloads"))),
            _metric_chip("Likes", _format_number(model.get("likes"))),
            _metric_chip("Task", cleanup_text(model.get("pipelineTag", "")).replace("-", " ").title() or "General"),
        ]
    )

    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
    :root {{
      --bg: linear-gradient(145deg, #fff7ed 0%, #ffedd5 32%, #ffffff 100%);
      --panel: rgba(255, 255, 255, 0.82);
      --panel-strong: rgba(255, 255, 255, 0.94);
      --text: #1f2937;
      --muted: #6b7280;
      --accent: #f97316;
      --accent-soft: rgba(249, 115, 22, 0.12);
      --border: rgba(251, 146, 60, 0.22);
      --shadow: 0 24px 60px rgba(194, 65, 12, 0.14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      width: {CARD_WIDTH}px;
      min-height: {CARD_HEIGHT}px;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(251, 146, 60, 0.22), transparent 36%),
        radial-gradient(circle at bottom right, rgba(251, 191, 36, 0.18), transparent 32%),
        var(--bg);
      color: var(--text);
    }}
    .card {{
      position: relative;
      width: {CARD_WIDTH}px;
      min-height: {CARD_HEIGHT}px;
      overflow: hidden;
      padding: 40px;
    }}
    .frame {{
      position: relative;
      min-height: {CARD_HEIGHT - 80}px;
      border-radius: 36px;
      padding: 34px;
      background: var(--panel);
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }}
    .hero {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 24px;
      margin-bottom: 28px;
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 16px;
      border-radius: 999px;
      background: #111827;
      color: #fff;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .eyebrow .dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #fb923c;
    }}
    .brand {{
      text-align: right;
      color: #9a3412;
      font-size: 18px;
      font-weight: 700;
    }}
    .title-row {{
      display: flex;
      align-items: center;
      gap: 18px;
      margin-bottom: 20px;
    }}
    .avatar {{
      width: 72px;
      height: 72px;
      border-radius: 22px;
      display: grid;
      place-items: center;
      background: linear-gradient(160deg, #fb923c, #ea580c);
      color: #fff;
      font-size: 34px;
      font-weight: 800;
      box-shadow: 0 16px 30px rgba(234, 88, 12, 0.25);
      flex: none;
    }}
    .title {{
      margin: 0;
      font-size: 54px;
      line-height: 1.06;
      font-weight: 800;
      letter-spacing: -0.03em;
      word-break: break-word;
    }}
    .subtitle {{
      margin: 8px 0 0;
      font-size: 24px;
      line-height: 1.4;
      color: var(--muted);
      font-weight: 600;
    }}
    .summary {{
      margin: 0 0 28px;
      padding: 24px 26px;
      border-radius: 26px;
      background: var(--panel-strong);
      border: 1px solid rgba(249, 115, 22, 0.16);
      font-size: 28px;
      line-height: 1.65;
      color: #374151;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
      margin-bottom: 26px;
    }}
    .metric {{
      padding: 20px 22px;
      border-radius: 24px;
      background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,247,237,0.95));
      border: 1px solid rgba(251, 146, 60, 0.18);
    }}
    .metric-label {{
      display: block;
      margin-bottom: 10px;
      color: #9a3412;
      font-size: 18px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 800;
    }}
    .metric-value {{
      display: block;
      color: #111827;
      font-size: 30px;
      line-height: 1.2;
      font-weight: 800;
      word-break: break-word;
    }}
    .footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding-top: 22px;
      border-top: 1px solid rgba(251, 146, 60, 0.16);
    }}
    .footer-left {{
      min-width: 0;
    }}
    .footer-right {{
      flex: none;
      padding: 12px 18px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #c2410c;
      font-size: 18px;
      font-weight: 700;
    }}
    .meta {{
      margin: 0;
      font-size: 18px;
      line-height: 1.45;
      color: var(--muted);
      font-weight: 600;
    }}
    .meta strong {{
      color: #111827;
    }}
  </style>
</head>
<body>
  <article class="card" data-card-root>
    <div class="frame">
      <div class="hero">
        <div class="eyebrow"><span class="dot"></span>Top {rank} Trending</div>
        <div class="brand">Hugging Face Daily</div>
      </div>
      <div class="title-row">
        <div class="avatar">{escape(initial)}</div>
        <div>
          <h1 class="title">{escape(title)}</h1>
          <p class="subtitle">{escape(author)} · {escape(_tag_line(model))}</p>
        </div>
      </div>
      <p class="summary">{_summary_text(model)}</p>
      <section class="grid">
        {metrics}
      </section>
      <div class="footer">
        <div class="footer-left">
          <p class="meta"><strong>{escape(provider_line)}</strong></p>
          <p class="meta">{escape(_updated_line(model))} · {escape(model_name)}</p>
        </div>
        <div class="footer-right">hf.co/{escape(title[:22])}</div>
      </div>
    </div>
  </article>
</body>
</html>
"""


def render_model_cards(browser_context: BrowserContext, models: list[dict]) -> list[dict]:
    page = browser_context.new_page(viewport={"width": CARD_WIDTH, "height": CARD_VIEWPORT_HEIGHT})
    rendered = []

    try:
        for index, model in enumerate(models, start=1):
            file_name = f"{index:02d}-{slugify(model.get('modelName', 'model'))}.png"
            image_path = RUN_IMAGE_DIR / file_name
            page.set_content(_build_card_html(model, index), wait_until="load")
            page.locator("[data-card-root]").screenshot(path=str(image_path), type="png")

            rendered_model = dict(model)
            rendered_model["rank"] = index
            rendered_model["modelCard"] = image_path.relative_to(ROOT_DIR).as_posix()
            rendered.append(rendered_model)
    finally:
        page.close()

    return rendered
