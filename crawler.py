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
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # 宽度 600px 适合双列展示
        context = await browser.new_context(viewport={'width': 600, 'height': 1000}, device_scale_factor=2)
        page = await context.new_page()
        
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&family=Inter:wght@800&display=swap');
                body {{ margin: 0; padding: 0; background: #000; color: #fff; font-family: 'Inter', sans-serif; }}
                .poster {{ width: 100%; box-sizing: border-box; background: #000; padding-bottom: 50px; }}
                
                /* 头部 */
                .header {{ padding: 40px 20px; background: linear-gradient(180deg, #1e3a8a 0%, #000 100%); border-bottom: 1px solid #222; text-align: left; }}
                .tag {{ font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 3px; color: #3b82f6; text-transform: uppercase; margin-bottom: 8px; }}
                .title {{ font-size: 32px; font-weight: 800; line-height: 1.0; margin-bottom: 10px; }}
                .meta {{ font-family: 'JetBrains Mono'; font-size: 11px; color: #555; }}

                /* 分类条 */
                .cat-header {{ margin: 30px 20px 15px 20px; border-left: 4px solid #3b82f6; padding-left: 12px; font-size: 16px; font-weight: 800; color: #fff; text-transform: uppercase; }}

                /* 双列网格 */
                .grid {{ 
                    display: grid; 
                    grid-template-columns: 1fr 1fr; 
                    gap: 15px; 
                    padding: 0 20px; 
                }}

                /* 模型卡片：纯图设计 */
                .model-card {{ 
                    position: relative; 
                    background: #111; 
                    border-radius: 6px; 
                    overflow: hidden; 
                    border: 1px solid #222;
                    display: flex;
                    flex-direction: column;
                }}
                .model-img {{ 
                    width: 100%; 
                    aspect-ratio: 2 / 1; 
                    object-fit: cover; 
                    display: block;
                    background: #1a1a1a;
                }}
                
                /* 覆盖在图片上的状态信息 */
                .status-badge {{
                    position: absolute; top: 8px; left: 8px;
                    font-family: 'JetBrains Mono'; font-size: 9px; font-weight: bold;
                    padding: 2px 6px; border-radius: 2px; color: #fff;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.5);
                }}
                .new {{ background: #059669; }}
                .upd {{ background: #2563eb; }}

                /* 底部数据条：极简对齐 */
                .model-info {{ 
                    padding: 8px 10px; 
                    background: #0a0a0a;
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }}
                .time-full {{ font-family: 'JetBrains Mono'; font-size: 9px; color: #444; }}
                .stats {{ 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    font-family: 'JetBrains Mono'; 
                    font-size: 10px; 
                    color: #f59e0b; 
                    font-weight: bold;
                }}
                .model-id-tiny {{ font-size: 8px; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }}

                .footer {{ text-align: center; color: #222; font-family: 'JetBrains Mono'; font-size: 10px; margin-top: 60px; }}
            </style>
        </head>
        <body>
            <div class="poster">
                {html_content}
                <div class="footer">// HUGGINGFACE RADAR // END OF REPORT</div>
            </div>
        </body>
        </html>
        """
        await page.set_content(full_html)
        await page.wait_for_timeout(2000) # 等待图片加载
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

def format_full_time(iso_str):
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_str[:19].replace('T', ' ')

async def run_main():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    
    final_output = {"date": today_str, "categories": {}}

    for category_name, tasks in CATEGORIES.items():
        print(f"🎨 正在排版: {category_name}")
        all_models = []
        
        for task in tasks:
            try:
                # 抓取列表
                url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=10"
                models = session.get(url, timeout=10).json()
                for m in models:
                    m_mod_full = m.get("lastModified", "")
                    if m_mod_full[:10] == today_str or (m.get("createdAt") or "")[:10] == today_str:
                        status = "NEW" if (m.get("createdAt") or "")[:10] == today_str else "UPD"
                        all_models.append({
                            "id": m.get("id"),
                            "likes": m.get("likes", 0),
                            "status": status,
                            "time_full": format_full_time(m_mod_full),
                            "thumb": f"https://cdn-thumbnails.huggingface.co/social-thumbnails/models/{m['id']}.png"
                        })
            except: pass

        if all_models:
            # 全大类按点赞排序
            all_models.sort(key=lambda x: x['likes'], reverse=True)
            
            html_parts = []
            html_parts.append(f'''
            <div class="header">
                <div class="tag">HuggingFace Intelligence Radar</div>
                <div class="title">{category_name.replace("_"," ")}<br>今日更新</div>
                <div class="meta">PERIOD: {today_str} // TOTAL: {len(all_models)}</div>
            </div>
            <div class="cat-header">Trending Models</div>
            <div class="grid">
            ''')

            for m in all_models:
                cls = "new" if m['status'] == "NEW" else "upd"
                html_parts.append(f'''
                <div class="model-card">
                    <div class="status-badge {cls}">{m['status']}</div>
                    <img class="model-img" src="{m['thumb']}" onerror="this.src='https://huggingface.co/front/assets/huggingface_logo-noborder.svg'">
                    <div class="model-info">
                        <div class="stats">
                            <span>LIKES: {m['likes']}</span>
                            <span style="color:#333;">#{all_models.index(m)+1}</span>
                        </div>
                        <div class="time-full">{m['time_full']}</div>
                        <div class="model-id-tiny">{m['id']}</div>
                    </div>
                </div>
                ''')
            
            html_parts.append('</div>')

            img_filename = f"{category_name}.png"
            img_path = os.path.join(today_str, img_filename)
            await html_to_image("".join(html_parts), img_path)
            
            final_output["categories"][category_name] = {
                "image_url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{today_str}/{img_filename}",
                "count": len(all_models)
            }

    with open(os.path.join(today_str, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4)
    print(f"\n✅ 封面瀑布流海报已生成。")

if __name__ == "__main__":
    asyncio.run(run_main())
