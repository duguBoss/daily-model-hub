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

# 大类中文映射
CAT_CN = {
    "Multimodal": "多模态能力",
    "Computer_Vision": "计算机视觉",
    "Natural_Language_Processing": "自然语言处理",
    "Audio": "音频与语音",
    "Tabular": "结构化数据",
    "Reinforcement_Learning": "强化学习",
    "Other": "其他前沿领域"
}

async def html_to_image(html_content, output_path):
    """使用 Playwright 渲染高分辨率海报"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # 宽 640px 更有海报张力
        context = await browser.new_context(viewport={'width': 640, 'height': 1000}, device_scale_factor=2)
        page = await context.new_page()
        
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&family=JetBrains+Mono&display=swap');
                body {{ margin: 0; padding: 0; background: #000; color: #fff; font-family: 'Noto Sans SC', sans-serif; }}
                .poster {{ width: 100%; box-sizing: border-box; background: #08090a; padding-bottom: 60px; }}
                
                /* 头部：大幅强化中文说明 */
                .header {{ padding: 60px 30px 40px; background: linear-gradient(135deg, #1e40af 0%, #08090a 100%); position: relative; overflow: hidden; }}
                .header::after {{ content: 'AI RADAR'; position: absolute; right: -20px; top: 20px; font-size: 80px; font-weight: 900; color: rgba(255,255,255,0.03); font-style: italic; }}
                .tag {{ font-size: 14px; color: #3b82f6; font-weight: bold; letter-spacing: 2px; margin-bottom: 10px; }}
                .title {{ font-size: 42px; font-weight: 900; line-height: 1.2; margin-bottom: 15px; }}
                .subtitle {{ font-size: 16px; color: #94a3b8; max-width: 80%; line-height: 1.6; }}
                
                .meta-strip {{ margin: 30px 30px 0; padding-top: 20px; border-top: 1px solid #222; display: flex; gap: 30px; font-family: 'JetBrains Mono'; font-size: 12px; color: #555; }}

                /* 分类装饰 */
                .cat-title {{ margin: 50px 30px 20px; display: flex; align-items: center; gap: 15px; }}
                .cat-title .label {{ background: #2563eb; color: #fff; padding: 4px 12px; font-size: 18px; font-weight: 900; border-radius: 2px; }}
                .cat-title .line {{ flex: 1; height: 1px; background: linear-gradient(to right, #333, transparent); }}

                /* 双列网格 */
                .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 0 30px; }}

                /* 卡片：极致对齐 */
                .card {{ position: relative; background: #131416; border-radius: 8px; overflow: hidden; border: 1px solid #1f2937; transition: transform 0.2s; }}
                .img-box {{ width: 100%; aspect-ratio: 2 / 1; background: #000; position: relative; }}
                .model-img {{ width: 100%; height: 100%; object-fit: cover; }}
                
                /* 右上角标签：不遮挡核心信息 */
                .badge {{
                    position: absolute; top: 10px; right: 10px;
                    padding: 3px 8px; font-size: 11px; font-weight: 900;
                    border-radius: 4px; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.5);
                    backdrop-filter: blur(4px);
                }}
                .badge-new {{ background: rgba(16, 185, 129, 0.9); }}
                .badge-upd {{ background: rgba(59, 130, 246, 0.9); }}

                /* 卡片底部信息 */
                .info {{ padding: 12px 15px; }}
                .info-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
                .rank {{ font-family: 'JetBrains Mono'; font-size: 12px; color: #3b82f6; font-weight: bold; }}
                .likes {{ font-family: 'JetBrains Mono'; font-size: 12px; color: #f59e0b; font-weight: bold; }}
                .time {{ font-family: 'JetBrains Mono'; font-size: 10px; color: #444; }}
                .model-name {{ font-size: 10px; color: #222; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 5px; opacity: 0.5; }}

                .footer {{ text-align: center; padding: 80px 0 40px; color: #222; font-size: 11px; letter-spacing: 2px; }}
            </style>
        </head>
        <body>
            <div class="poster">
                {html_content}
                <div class="footer">情报来源：HUGGINGFACE HUB 全球同步更新</div>
            </div>
        </body>
        </html>
        """
        await page.set_content(full_html)
        # 等待所有图片加载完成，避免封面发白
        await page.wait_for_timeout(3000)
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

def format_full_time(iso_str):
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        # 转换为北京时间 (UTC+8) 看起来更亲切
        dt_bj = dt + datetime.timedelta(hours=8)
        return dt_bj.strftime("%Y-%m-%d %H:%M:%S")
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
        print(f"🎨 正在绘制【{CAT_CN.get(category_name)}】海报...")
        all_models = []
        
        for task in tasks:
            try:
                url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=10"
                models = session.get(url, timeout=10).json()
                for m in models:
                    m_mod_full = m.get("lastModified", "")
                    if m_mod_full[:10] == today_str or (m.get("createdAt") or "")[:10] == today_str:
                        status = "新发布" if (m.get("createdAt") or "")[:10] == today_str else "已更新"
                        all_models.append({
                            "id": m.get("id"),
                            "likes": m.get("likes", 0),
                            "status": status,
                            "time_full": format_full_time(m_mod_full),
                            "thumb": f"https://cdn-thumbnails.huggingface.co/social-thumbnails/models/{m['id']}.png"
                        })
            except: pass

        if all_models:
            # 排序：点赞数最高排第一
            all_models.sort(key=lambda x: x['likes'], reverse=True)
            
            html_parts = []
            cn_name = CAT_CN.get(category_name, category_name)
            # 1. 头部区域：强化中文吸引力
            html_parts.append(f'''
            <div class="header">
                <div class="tag">AI 开源情报雷达</div>
                <div class="title">{cn_name}<br>今日趋势发布</div>
                <div class="subtitle">实时追踪社区最活跃的模型动态。通过封面快速锁定前沿架构与大厂新作。</div>
            </div>
            <div class="meta-strip">
                <span>更新日期: {today_str}</span>
                <span>追踪数量: {len(all_models)} MODELS</span>
            </div>
            <div class="cat-title">
                <div class="label">热门模型精选</div>
                <div class="line"></div>
            </div>
            <div class="grid">
            ''')

            for i, m in enumerate(all_models):
                badge_class = "badge-new" if m['status'] == "新发布" else "badge-upd"
                html_parts.append(f'''
                <div class="card">
                    <div class="img-box">
                        <div class="badge {badge_class}">{m['status']}</div>
                        <img class="model-img" src="{m['thumb']}" onerror="this.src='https://huggingface.co/front/assets/huggingface_logo-noborder.svg'">
                    </div>
                    <div class="info">
                        <div class="info-top">
                            <span class="rank">#{i+1}</span>
                            <span class="likes">人气 {m['likes']}</span>
                        </div>
                        <div class="time">{m['time_full']}</div>
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
        json.dump(final_output, f, ensure_ascii=False, indent=4)
    print(f"\n✅ 海报已重新设计：中文引导 + 右上角标签。")

if __name__ == "__main__":
    asyncio.run(run_main())
