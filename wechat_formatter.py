import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config import ROOT_DIR, RUN_STAMP, TRENDING_URL


def build_wechat_html(models: list[dict], title: str, date_str: str) -> str:
    """构建微信文章 HTML 内容."""
    # 构建模型卡片 HTML
    cards_html = []
    for idx, model in enumerate(models, start=1):
        model_name = model.get("modelName", "")
        model_desc = model.get("modelDescription", "")
        model_url = model.get("modelUrl", "")
        card_image = model.get("modelCard", "")
        rank = model.get("rank", idx)

        # 构建单个模型卡片
        card_html = f"""
        <section style="margin-bottom: 24px; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
          <section style="background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%); padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;">
            <span style="color: #ffffff; font-size: 14px; font-weight: bold;">#{rank} Trending Model</span>
            <span style="color: rgba(255,255,255,0.9); font-size: 12px;">Hugging Face</span>
          </section>
          <section style="padding: 0;">
            <img src="https://raw.githubusercontent.com/duguBoss/daily-model-hub/main/{card_image}" style="width: 100%; display: block;" alt="{model_name}" />
          </section>
          <section style="padding: 16px;">
            <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #1a1a1a; font-weight: 600; line-height: 1.4;">{model_name}</h3>
            <p style="margin: 0 0 16px 0; font-size: 14px; color: #4a4a4a; line-height: 1.6;">{model_desc}</p>
            <a href="{model_url}" style="display: inline-block; background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%); color: #ffffff; padding: 8px 20px; border-radius: 20px; text-decoration: none; font-size: 13px; font-weight: 500;">查看模型 →</a>
          </section>
        </section>
        """
        cards_html.append(card_html)

    # 构建完整 HTML
    html = f"""<section data-side-margin="0" style="margin:0;padding:0;box-sizing:border-box;">
  <section style="max-width: 100%; margin: 0 auto; box-sizing: border-box; padding: 16px; font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei UI', 'Microsoft YaHei', Arial, sans-serif; background-color: #f5f5f5; overflow: hidden; font-size: 15px; color: #333;">
    <section style="background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%); padding: 24px 20px; text-align: center; margin: -16px -16px 24px -16px;">
      <h1 style="margin: 0 0 8px 0; font-size: 22px; color: #ffffff; font-weight: bold;">{title}</h1>
      <p style="margin: 0; font-size: 13px; color: rgba(255,255,255,0.9);">{date_str} · Hugging Face 热门模型精选</p>
    </section>
    {''.join(cards_html)}
    <section style="text-align: center; padding: 20px; color: #999; font-size: 12px; border-top: 1px solid #e0e0e0; margin-top: 16px;">
      <p style="margin: 0;">数据来源: Hugging Face</p>
      <p style="margin: 8px 0 0 0;">自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </section>
  </section>
</section>"""
    return html


def generate_wechat_payload(models: list[dict], date_str: str) -> dict[str, Any]:
    """生成微信格式的 JSON 数据.

    参考 daily-nasa-hub 的格式，包含以下字段:
    - date: 日期
    - title: 标题
    - covers: 封面图片列表
    - songs: 歌曲/模型列表（用于展示）
    - weixin_html: 微信文章 HTML
    - generation: 生成元信息
    - source_top_urls: 来源 URL 列表
    - new_urls: 新模型 URL 列表
    - models: 模型详情列表
    """
    if not models:
        raise ValueError("No models to generate payload")

    # 生成标题
    title = f"Hugging Face 热门模型精选 | {date_str}"

    # 收集封面图片
    covers = []
    for model in models:
        card_path = model.get("modelCard", "")
        if card_path:
            cover_url = f"https://raw.githubusercontent.com/duguBoss/daily-model-hub/main/{card_path}"
            covers.append(cover_url)

    # 构建 songs（用于音乐播放器展示，这里用模型名替代）
    songs = []
    for model in models:
        songs.append({
            "name": model.get("modelName", "").split("/")[-1],  # 只取模型名部分
            "artist": model.get("modelName", "").split("/")[0] if "/" in model.get("modelName", "") else "Hugging Face"
        })

    # 构建微信 HTML
    weixin_html = build_wechat_html(models, title, date_str)

    # 构建生成元信息
    generation = {
        "ai_enabled": True,
        "ai_success": True,
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite-preview",
        "error": "",
        "fallback_used": False,
        "model_count": len(models),
        "generated_at": datetime.now().isoformat()
    }

    # 收集来源 URL
    source_top_urls = [model.get("modelUrl", "") for model in models if model.get("modelUrl")]
    new_urls = source_top_urls  # 对于每日新抓取的，所有都是新的

    # 构建模型详情列表
    models_data = []
    for model in models:
        models_data.append({
            "id": f"hf-{date_str}-{model.get('rank', 0):02d}",
            "rank": model.get("rank", 0),
            "name": model.get("modelName", ""),
            "description": model.get("modelDescription", ""),
            "source_description": model.get("sourceDescription", ""),
            "url": model.get("modelUrl", ""),
            "card_summary": model.get("cardSummary", ""),
            "image_path": model.get("modelCard", ""),
            "cover_url": f"https://raw.githubusercontent.com/duguBoss/daily-model-hub/main/{model.get('modelCard', '')}" if model.get("modelCard") else ""
        })

    return {
        "date": date_str,
        "title": title,
        "covers": covers,
        "songs": songs,
        "weixin_html": weixin_html,
        "generation": generation,
        "source_top_urls": source_top_urls,
        "new_urls": new_urls,
        "models": models_data
    }


def save_wechat_json(payload: dict[str, Any], date_str: str) -> str:
    """保存微信格式的 JSON 文件到 data/daily 目录."""
    from config import DAILY_DIR

    # 确保目录存在
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    # 保存为 Daily_HF_Models_YYYY-MM-DD.json 格式
    json_file_name = DAILY_DIR / f"Daily_HF_Models_{date_str}.json"

    with open(json_file_name, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    print(f"Saved WeChat format JSON to {json_file_name}")
    return str(json_file_name)
