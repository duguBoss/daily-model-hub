import requests
import datetime
import os
import json
import re
import asyncio
from playwright.async_api import async_playwright

# ---------------------------------------------------------
# 配置信息
# ---------------------------------------------------------
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "your-username/your-repo")

CATEGORIES = {
    "Multimodal":["audio-text-to-text", "image-text-to-text", "image-text-to-image", "image-text-to-video", "visual-question-answering", "document-question-answering", "video-text-to-text", "visual-document-retrieval", "any-to-any"],
    "Computer_Vision":["depth-estimation", "image-classification", "object-detection", "image-segmentation", "text-to-image", "image-to-text", "image-to-image", "image-to-video", "unconditional-image-generation", "video-classification", "text-to-video", "zero-shot-image-classification", "mask-generation", "zero-shot-object-detection", "text-to-3d", "image-to-3d", "image-feature-extraction", "keypoint-detection", "video-to-video"],
    "Natural_Language_Processing":["text-classification", "token-classification", "table-question-answering", "question-answering", "zero-shot-classification", "translation", "summarization", "feature-extraction", "text-generation", "fill-mask", "sentence-similarity", "text-ranking"],
    "Audio":["text-to-speech", "text-to-audio", "automatic-speech-recognition", "audio-to-audio", "audio-classification", "voice-activity-detection"],
    "Tabular":["tabular-classification", "tabular-regression", "time-series-forecasting"],
    "Reinforcement_Learning":["reinforcement-learning", "robotics"],
    "Other":["graph-ml"]
}

async def html_to_image(html_content, output_path):
    """使用 Playwright 渲染高分辨率的海报图片"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # 450px 宽度，device_scale_factor=3 保证打印级的清晰度
        context = await browser.new_context(viewport={'width': 450, 'height': 800}, device_scale_factor=3)
        page = await context.new_page()
        # 将生成的 section 片段嵌入完整样式中
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ margin: 0; padding: 0; background: #0f172a; color: #f8fafc; font-family: -apple-system, system-ui, sans-serif; }}
                .poster-container {{ width: 100%; position: relative; }}
                .header-section {{ padding: 30px 20px; background: linear-gradient(180deg, rgba(30,58,138,0.3) 0%, rgba(15,23,42,0) 100%); text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }}
                .tag-line {{ font-size: 12px; color: #38bdf8; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }}
                .main-title {{ font-size: 28px; font-weight: 900; background: linear-gradient(to right, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1.2; }}
                .category-badge {{ display: inline-block; padding: 4px 12px; background: #3b82f6; color: #fff; font-size: 14px; font-weight: bold; border-radius: 99px; margin-top: 15px; }}
                
                .task-block {{ margin-top: 20px; }}
                .task-header {{ padding: 8px 20px; background: rgba(255,255,255,0.05); font-size: 13px; color: #94a3b8; border-left: 4px solid #3b82f6; font-weight: 600; }}
                
                .model-row {{ display: flex; justify-content: space-between; align-items: center; padding: 18px 20px; border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.3s; }}
                .model-info {{ flex: 1; min-width: 0; }}
                .model-id {{ font-size: 16px; font-weight: 700; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 6px; }}
                .model-meta {{ display: flex; align-items: center; font-size: 11px; gap: 10px; }}
                
                .badge-new {{ background: #10b981; color: #fff; padding: 1px 6px; border-radius: 4px; font-weight: 900; font-size: 10px; }}
                .badge-upd {{ background: #3b82f6; color: #fff; padding: 1px 6px; border-radius: 4px; font-weight: 900; font-size: 10px; }}
                .timestamp {{ color: #64748b; font-family: monospace; }}
                
                .stats-box {{ text-align: right; margin-left: 15px; border-left: 1px solid rgba(255,255,255,0.1); padding-left: 15px; }}
                .stat-item {{ display: block; font-size: 13px; font-weight: 600; color: #f59e0b; }}
                .stat-dl {{ font-size: 10px; color: #64748b; margin-top: 2px; }}
                
                .footer {{ text-align: center; padding: 40px 20px; font-size: 10px; color: #475569; letter-spacing: 1px; }}
                img.banner {{ width: 100%; display: block; border: none; }}
            </style>
        </head>
        <body>
            <div class="poster-container">
                {html_content}
            </div>
        </body>
        </html>
        """
        await page.set_content(full_html)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

def compress_html(html_list):
    raw_html = "".join(html_list).replace('\n', '').replace('\r', '').replace('\t', '')
    return re.sub(r'>\s+<', '><', raw_html).strip()

async def run_main():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    
    final_output = {"date": today_str, "total_all": 0, "categories": {}}

    for category_name, tasks in CATEGORIES.items():
        print(f"📂 正在设计海报: {category_name}")
        category_sub_data, category_total = {}, 0
        
        for task in tasks:
            try:
                url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=15"
                models = session.get(url, timeout=10).json()
                task_list = []
                for m in models:
                    m_mod_full = m.get("lastModified", "")
                    if m_mod_full[:10] == today_str or (m.get("createdAt") or "")[:10] == today_str:
                        status = "NEW" if (m.get("createdAt") or "")[:10] == today_str else "UPD"
                        task_list.append({
                            "id": m.get("id"),
                            "likes": m.get("likes", 0),
                            "downloads": m.get("downloads", 0),
                            "status": status,
                            "time": m_mod_full.split('T')[1][:5]
                        })
                if task_list:
                    task_list.sort(key=lambda x: x['likes'], reverse=True)
                    category_sub_data[task] = task_list
                    category_total += len(task_list)
            except: pass

        if category_total > 0:
            # --- 海报级 HTML 构建 ---
            html_content = []
            # 1. 顶部无缝 Banner
            html_content.append('<div style="line-height:0; margin:0;">')
            html_content.append('<img class="banner" src="https://mmbiz.qpic.cn/mmbiz_png/qHfXxy1pes10fIch7kKDnTcV7tJMdWticbFaZx6aXXLjxHFsQWCWr3TyiaVY11COWfF8yJnIQiasxfWKQ4dYAAvyFYZET5bT9PXJnuKzjVjEgM/640?wx_fmt=png">')
            html_content.append('<img class="banner" src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif">')
            html_content.append('</div>')

            # 2. 标题区
            html_content.append(f'''
            <div class="header-section">
                <div class="tag-line">DAILY TECH REPORT / HUGGINGFACE</div>
                <div class="main-title">模型更新<br>趋势一览</div>
                <div class="category-badge">{category_name.upper().replace("_", " ")}</div>
                <div style="font-size: 12px; color: #475569; margin-top: 10px; font-family: monospace;">TRACKED: {category_total} MODELS / {today_str}</div>
            </div>
            ''')

            # 3. 任务与模型区块
            for t_name, m_list in category_sub_data.items():
                html_content.append(f'<div class="task-block"><div class="task-header">{t_name.upper()}</div>')
                for m in m_list:
                    badge_class = "badge-new" if m['status'] == "NEW" else "badge-upd"
                    html_content.append(f'''
                    <div class="model-row">
                        <div class="model-info">
                            <div class="model-id">{m['id']}</div>
                            <div class="model-meta">
                                <span class="{badge_class}">{m['status']}</span>
                                <span class="timestamp">🕙 {m['time']}</span>
                            </div>
                        </div>
                        <div class="stats-box">
                            <span class="stat-item">🔥 {m['likes']}</span>
                            <span class="stat-dl">⬇️ {m['downloads']}</span>
                        </div>
                    </div>
                    ''')
                html_content.append('</div>')

            # 4. 底部
            html_content.append(f'''
            <div class="footer">
                <div style="margin-bottom: 20px;">HUGGINGFACE HUB REAL-TIME AGGREGATION</div>
                <img class="banner" src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif">
            </div>
            ''')

            # 转图片
            img_filename = f"{category_name}.png"
            img_path = os.path.join(today_str, img_filename)
            await html_to_image("".join(html_content), img_path)
            
            final_output["categories"][category_name] = {
                "image_url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{today_str}/{img_filename}",
                "total": category_total,
                "html_compressed": compress_html(html_content)
            }
            final_output["total_all"] += category_total

    if final_output["total_all"] > 0:
        with open(os.path.join(today_str, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 海报生成任务圆满完成！已存入 {today_str} 目录。")

if __name__ == "__main__":
    asyncio.run(run_main())
