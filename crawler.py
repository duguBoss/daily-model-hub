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
    """使用 Playwright 渲染高分辨率海报"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 500, 'height': 800}, device_scale_factor=2)
        page = await context.new_page()
        
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ margin: 0; padding: 0; background: #050505; color: #fff; font-family: 'Inter', -apple-system, system-ui, sans-serif; }}
                .poster {{ width: 100%; box-sizing: border-box; background: #050505; padding-bottom: 40px; }}
                
                /* 头部设计 */
                .header {{ padding: 40px 25px; background: linear-gradient(135deg, #1e40af 0%, #000 70%); border-bottom: 1px solid #333; }}
                .tag {{ font-size: 11px; letter-spacing: 2px; color: #60a5fa; font-weight: bold; text-transform: uppercase; margin-bottom: 10px; }}
                .title {{ font-size: 32px; font-weight: 800; line-height: 1.1; margin-bottom: 15px; }}
                .meta-bar {{ font-size: 12px; color: #888; font-family: monospace; display: flex; justify-content: space-between; }}
                
                /* 分类标题 */
                .cat-badge {{ margin: 30px 20px 10px 20px; padding: 6px 15px; background: #2563eb; color: #fff; display: inline-block; border-radius: 4px; font-weight: bold; font-size: 14px; }}
                
                /* 任务组 */
                .task-section {{ margin: 15px 20px; }}
                .task-name {{ font-size: 12px; color: #555; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; border-bottom: 1px solid #222; padding-bottom: 4px; }}
                
                /* 模型卡片重构 */
                .model-card {{ 
                    background: #111; border: 1px solid #222; border-radius: 12px; padding: 15px; margin-bottom: 15px;
                    display: flex; align-items: center; position: relative; overflow: hidden;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
                }}
                .model-icon {{ width: 48px; height: 48px; border-radius: 10px; object-fit: cover; margin-right: 15px; background: #222; border: 1px solid #333; }}
                
                .model-body {{ flex: 1; min-width: 0; }}
                .model-id {{ font-size: 15px; font-weight: 700; color: #eee; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
                
                .model-footer {{ display: flex; align-items: center; gap: 10px; }}
                .badge {{ font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px; color: #fff; }}
                .badge-new {{ background: #10b981; }}
                .badge-upd {{ background: #3b82f6; }}
                .time {{ font-size: 11px; color: #555; font-family: monospace; }}
                
                .model-stats {{ text-align: right; margin-left: 10px; }}
                .stat-val {{ display: block; font-size: 14px; font-weight: 800; color: #f59e0b; }}
                .stat-lab {{ font-size: 9px; color: #444; text-transform: uppercase; }}

                .footer-text {{ text-align: center; color: #333; font-size: 10px; margin-top: 50px; letter-spacing: 1px; }}
            </style>
        </head>
        <body>
            <div class="poster">
                {html_content}
                <div class="footer-text">HUGGINGFACE REAL-TIME MONITORING SYSTEM</div>
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
        print(f"🎨 设计海报: {category_name}")
        category_sub_data, category_total = {}, 0
        
        for task in tasks:
            try:
                url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=15"
                models = session.get(url, timeout=10).json()
                task_list = []
                for m in models:
                    m_id = m.get("id")
                    m_mod = m.get("lastModified", "")
                    if m_mod[:10] == today_str or (m.get("createdAt") or "")[:10] == today_str:
                        status = "NEW" if (m.get("createdAt") or "")[:10] == today_str else "UPD"
                        task_list.append({
                            "id": m_id,
                            "likes": m.get("likes", 0),
                            "downloads": m.get("downloads", 0),
                            "status": status,
                            "time": m_mod.split('T')[1][:5],
                            # 每一个模型都生成对应的 Logo 地址
                            "icon": f"https://cdn-thumbnails.huggingface.co/social-thumbnails/models/{m_id}.png"
                        })
                if task_list:
                    task_list.sort(key=lambda x: x['likes'], reverse=True)
                    category_sub_data[task] = task_list
                    category_total += len(task_list)
            except: pass

        if category_total > 0:
            # --- 纯内容 HTML 构建 (无首尾图) ---
            html_parts = []
            
            # 1. 头部
            html_parts.append(f'''
            <div class="header">
                <div class="tag">AI Model Hub / Dashboard</div>
                <div class="title">模型更新<br>趋势洞察</div>
                <div class="meta-bar">
                    <span>DATE: {today_str}</span>
                    <span>TRACKED: {category_total} MODELS</span>
                </div>
            </div>
            <div class="cat-badge">{category_name.upper().replace("_", " ")}</div>
            ''')

            # 2. 任务区块
            for t_name, m_list in category_sub_data.items():
                html_parts.append(f'<div class="task-section"><div class="task-name">// {t_name}</div>')
                for m in m_list:
                    badge_cls = "badge-new" if m['status'] == "NEW" else "badge-upd"
                    html_parts.append(f'''
                    <div class="model-card">
                        <img class="model-icon" src="{m['icon']}" onerror="this.src='https://huggingface.co/front/assets/huggingface_logo-noborder.svg'">
                        <div class="model-body">
                            <div class="model-id">{m['id']}</div>
                            <div class="model-footer">
                                <span class="badge {badge_cls}">{m['status']}</span>
                                <span class="time">{m['time']} UPDATED</span>
                            </div>
                        </div>
                        <div class="model-stats">
                            <span class="stat-val">{m['likes']}</span>
                            <span class="stat-lab">LIKES</span>
                        </div>
                    </div>
                    ''')
                html_parts.append('</div>')

            # 生成图片并保存
            img_filename = f"{category_name}.png"
            img_path = os.path.join(today_str, img_filename)
            await html_to_image("".join(html_parts), img_path)
            
            final_output["categories"][category_name] = {
                "image_url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{today_str}/{img_filename}",
                "total": category_total,
                "html_compressed": compress_html(html_parts)
            }
            final_output["total_all"] += category_total

    if final_output["total_all"] > 0:
        with open(os.path.join(today_str, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 高端海报版任务完成！")

if __name__ == "__main__":
    asyncio.run(run_main())
