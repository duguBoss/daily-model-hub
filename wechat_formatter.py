from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from wechat_template import render_model_card, render_page


MODEL_CARD_BASE_URL = "https://raw.githubusercontent.com/duguBoss/daily-model-hub/main/"
SUBTITLE_TEMPLATE = "{date} \u00b7 Hugging Face \u70ed\u95e8\u6a21\u578b\u901f\u89c8"


def _extract_model_display_name(model_name: str) -> str:
    """提取简洁的模型显示名称（无空格版本）.

    例如: google/gemma-4-31B-it -> Gemma4
          baidu/Qianfan-OCR -> QianfanOCR
    """
    # 取最后一部分
    name = model_name.split("/")[-1] if "/" in model_name else model_name

    # 移除常见的后缀参数
    suffixes = ["-it", "-gguf", "-mlx", "-nvfp4", "-awq", "-gptq", "-bnb", "-4bit", "-8bit"]
    for suffix in suffixes:
        if name.lower().endswith(suffix.lower()):
            name = name[:-len(suffix)]

    # 提取主要版本号，例如 gemma-4-31B -> Gemma4
    match = re.match(r'^([a-zA-Z]+[\d\.]*(?:\.\d+)?)', name)
    if match:
        base_name = match.group(1)
        # 如果有版本号如 gemma-4，保留它（去掉连字符）
        version_match = re.search(r'-([\d\.]+)(?:-[\d]+[a-zA-Z]*)?$', name)
        if version_match:
            return f"{base_name}{version_match.group(1)}".title()
        return base_name.title()

    # 清理连字符和下划线，但不添加空格
    name = re.sub(r'[-_]', '', name)
    return name.title()


def _generate_attractive_title(first_model: dict, date_str: str) -> str:
    """根据第一个模型的内容生成吸引人的微信标题（30字以内）.

    生成有宣传力、吸引人的标题，避免使用特殊符号。
    """
    model_name = first_model.get("modelName", "")
    description = first_model.get("modelDescription", "")

    # 提取简洁的模型名
    display_name = _extract_model_display_name(model_name)

    # 从描述中提取核心能力关键词（中文）
    # 匹配前几个中文字符作为能力描述
    desc_clean = re.sub(r"[^\u4e00-\u9fa5]", "", description)
    capability = desc_clean[:6] if len(desc_clean) >= 6 else desc_clean

    # 构建有吸引力的标题候选（无空格、无特殊符号）
    titles = [
        f"🔥{display_name}重磅发布{capability}能力再升级",
        f"今日AI热点{display_name}登顶HuggingFace",
        f"开发者必看{display_name}带来全新体验",
        f"最强{display_name}来袭多模态能力全面升级",
        f"HuggingFace热榜第一{display_name}究竟有多强",
        f"谷歌重磅{display_name}开源性能超越预期",
        f"🔥{display_name}今日登顶开发者都在关注",
    ]

    # 选择最合适且不超过30字的标题
    for title in titles:
        if len(title) <= 30:
            return title

    # 兜底：简洁标题（无空格）
    return f"🔥{display_name}登顶HuggingFace热榜"[:30]


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

    # 根据第一个模型生成吸引人的标题
    title = _generate_attractive_title(models[0], date_str)

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
