from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from wechat_template import render_model_card, render_page


MODEL_CARD_BASE_URL = "https://raw.githubusercontent.com/duguBoss/daily-model-hub/main/"
TITLE_TEMPLATE = "Hugging Face \u70ed\u95e8\u6a21\u578b\u7cbe\u9009 | {date}"
SUBTITLE_TEMPLATE = "{date} \u00b7 Hugging Face \u70ed\u95e8\u6a21\u578b\u901f\u89c8"


def _build_card_image_url(card_path: str) -> str:
    return f"{MODEL_CARD_BASE_URL}{card_path}" if card_path else ""


def build_wechat_html(models: list[dict], title: str, date_str: str) -> str:
    """Build WeChat article HTML."""
    cards_html: list[str] = []
    for idx, model in enumerate(models, start=1):
        rank = model.get("rank", idx)
        cards_html.append(
            render_model_card(
                rank=rank,
                model_name=model.get("modelName", ""),
                model_desc=model.get("modelDescription", ""),
                model_url=model.get("modelUrl", ""),
                image_url=_build_card_image_url(model.get("modelCard", "")),
            )
        )

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_page(
        title=title,
        subtitle=SUBTITLE_TEMPLATE.format(date=date_str),
        cards_html="".join(cards_html),
        generated_at=generated_at,
    )


def generate_wechat_payload(models: list[dict], date_str: str) -> dict[str, Any]:
    """Generate the WeChat payload JSON."""
    if not models:
        raise ValueError("No models to generate payload")

    title = TITLE_TEMPLATE.format(date=date_str)

    covers = []
    for model in models:
        card_path = model.get("modelCard", "")
        if card_path:
            covers.append(_build_card_image_url(card_path))

    songs = []
    for model in models:
        model_name = model.get("modelName", "")
        songs.append(
            {
                "name": model_name.split("/")[-1],
                "artist": model_name.split("/")[0] if "/" in model_name else "Hugging Face",
            }
        )

    weixin_html = build_wechat_html(models, title, date_str)

    generation = {
        "ai_enabled": True,
        "ai_success": True,
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite-preview",
        "error": "",
        "fallback_used": False,
        "model_count": len(models),
        "generated_at": datetime.now().isoformat(),
    }

    source_top_urls = [model.get("modelUrl", "") for model in models if model.get("modelUrl")]
    new_urls = source_top_urls

    models_data = []
    for model in models:
        image_path = model.get("modelCard", "")
        models_data.append(
            {
                "id": f"hf-{date_str}-{model.get('rank', 0):02d}",
                "rank": model.get("rank", 0),
                "name": model.get("modelName", ""),
                "description": model.get("modelDescription", ""),
                "source_description": model.get("sourceDescription", ""),
                "url": model.get("modelUrl", ""),
                "card_summary": model.get("cardSummary", ""),
                "image_path": image_path,
                "cover_url": _build_card_image_url(image_path),
            }
        )

    return {
        "date": date_str,
        "title": title,
        "covers": covers,
        "songs": songs,
        "weixin_html": weixin_html,
        "generation": generation,
        "source_top_urls": source_top_urls,
        "new_urls": new_urls,
        "models": models_data,
    }


def save_wechat_json(payload: dict[str, Any], date_str: str) -> str:
    """Save the WeChat JSON file to data/daily."""
    from config import DAILY_DIR

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    json_file_name = DAILY_DIR / f"Daily_HF_Models_{date_str}.json"

    with open(json_file_name, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    print(f"Saved WeChat format JSON to {json_file_name}")
    return str(json_file_name)
