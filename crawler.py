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

# 任务中文名映射，用于子分类说明
TASK_CN = {
    "text-to-speech": "语音合成 / TTS",
    "automatic-speech-recognition": "自动语音识别 / ASR",
    "text-to-image": "文生图 / 图像生成",
    "image-to-text": "图像描述 / 多模态理解",
    "text-generation": "文本生成 / 大语言模型",
    "text-to-video": "文生视频 / 视频生成",
    "audio-text-to-text": "音频文本转换",
    "visual-question-answering": "视觉问答",
    "object-detection": "目标检测",
    "image-segmentation": "图像分割",
    "translation": "机器翻译",
    "summarization": "文本摘要"
}

CAT_CN = {
    "Multimodal": "多模态能力",
    "Computer_Vision": "计算机视觉",
    "Natural_Language_Processing": "自然语言处理",
    "Audio": "音频与语音",
    "Tabular": "结构化数据",
    "Reinforcement_Learning": "强化学习",
    "Other": "其他领域"
}

async def html_to_image(html_content, output_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 640, 'height': 1200}, device_scale_factor=2)
        page = await context.new_page()
        
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&family=JetBrains+Mono&display=swap');
                body {{ margin: 0; padding: 0; background: #08090a; color: #fff; font-family: 'Noto Sans SC', sans-serif; }}
                .poster {{ width: 100%; box-sizing: border-box; padding-bottom: 60px; }}
                
                /* 头部设计 */
                .header {{ padding: 60px 40px 40px; background: linear-gradient(135deg, #1e40af 0%, #08090a 100%); border-bottom: 1px solid #1f2937; }}
                .header .label {{ font-size: 14px; color: #3b82f6; font-weight: bold; letter-spacing: 2px; margin-bottom: 10px; text-transform: uppercase; }}
                .header .title {{ font-size: 40px; font-weight: 900; line-height: 1.2; margin-bottom: 15px; color: #fff; }}
                .header .subtitle {{ font-size: 16px; color: #94a3b8; line-height: 1.6; opacity: 0.8; }}
                
                .meta-strip {{ margin: 25px 40px 0; padding-top: 20px; border-top: 1px solid #222; display: flex; justify-content: space-between; font-family: 'JetBrains Mono'; font-size: 13px; color: #555; }}

                /* 子分类说明条 */
                .task-group {{ margin-top: 40px; }}
                .task-header {{ 
                    margin: 0 40px 20px; padding: 10px 0;
                    border-bottom: 1px solid #222;
                    display: flex; align-items: baseline; gap: 10px;
                }}
                .task-header .cn {{ font-size: 20px; font-weight: 900; color: #f8fafc; }}
                .task-header .en {{ font-size: 12px; font-family: 'JetBrains Mono'; color: #4b5563; text-transform: uppercase; }}

                /* 网格布局 */
                .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 0 40px; }}

                /* 模型卡片 */
                .card {{ position: relative; background: #111214; border-radius: 12px; overflow: hidden; border: 1px solid #1f2937; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
                .img-box {{ width: 100%; aspect-ratio: 2 / 1; background: #000; position: relative; }}
                .model-img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
                
                /* 右上角标签 */
                .badge {{
                    position: absolute; top: 12px; right: 12px;
                    padding: 3px 10px; font-size: 11px; font-weight: 900;
                    border-radius: 6px; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.5);
                    backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.1);
                }}
                .badge-new {{ background: rgba(16, 185, 129, 0.85); }}
                .badge-upd {{ background: rgba(59, 130, 246, 0.85); }}

                /* 数据与统计 */
                .info {{ padding: 15px; }}
                .info-stats {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
                .stat-box {{ display: flex; flex-direction: column; }}
                .stat-label {{ font-size: 9px; color: #4b5563; text-transform: uppercase; font-weight: bold; }}
                .stat-value {{ font-family: 'JetBrains Mono'; font-size: 13px; font-weight: bold; color: #f59e0b; }}
                .stat-value.dl {{ color: #94a3b8; }}

                .time-box {{ border-top: 1px solid #1a1b1e; padding-top: 10px; display: flex; align-items: center; justify-content: space-between; }}
                .time-label {{ font-size: 9px; color: #333; font-weight: bold; }}
                .time-val {{ font-family: 'JetBrains Mono'; font-size: 10px; color: #444; }}

                .footer {{ text-align: center; padding: 100px 0 50px; color: #222; font-size: 12px; letter-spacing: 4px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="poster">
                {html_content}
                <div class="footer">INTEL COLLECTED BY HUGGINGFACE OPEN-SOURCE RADAR</div>
            </div>
        </body>
        </html>
        """
        await page.set_content(full_html)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

def format_full_time(iso_str):
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
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
        print(f"📡 正在追踪【{CAT_CN.get(category_name)}】开源模型...")
        # 结构化存储：{ task: [models] }
        category_grouped_data = {}
        total_in_cat = 0
        
        for task in tasks:
            try:
                url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=10"
                models = session.get(url, timeout=10).json()
                task_list = []
                for m in models:
                    m_mod_full = m.get("lastModified", "")
                    if m_mod_full[:10] == today_str or (m.get("createdAt") or "")[:10] == today_str:
                        status = "新发布" if (m.get("createdAt") or "")[:10] == today_str else "已更新"
                        task_list.append({
                            "id": m.get("id"),
                            "likes": m.get("likes", 0),
                            "downloads": m.get("downloads", 0),
                            "status": status,
                            "time_full": format_full_time(m_mod_full),
                            "thumb": f"https://cdn-thumbnails.huggingface.co/social-thumbnails/models/{m['id']}.png"
                        })
                if task_list:
                    task_list.sort(key=lambda x: x['likes'], reverse=True)
                    category_grouped_data[task] = task_list
                    total_in_cat += len(task_list)
            except: pass

        if total_in_cat > 0:
            html_parts = []
            cn_cat = CAT_CN.get(category_name, category_name)
            
            # 1. 头部：包含“开源模型”标题和更新日期
            html_parts.append(f'''
            <div class="header">
                <div class="label">Daily Intelligence Radar</div>
                <div class="title">开源模型<br>{cn_cat}动态</div>
                <div class="subtitle">实时监控全球开源社区最前沿的模型发布与代码迭代。</div>
            </div>
            <div class="meta-strip">
                <span>更新日期: {today_str}</span>
                <span>追踪规模: {total_in_cat} MODELS</span>
            </div>
            ''')

            # 2. 遍历子分类说明
            for task_id, models in category_grouped_data.items():
                cn_task = TASK_CN.get(task_id, task_id.replace("-", " ").title())
                html_parts.append(f'''
                <div class="task-group">
                    <div class="task-header">
                        <span class="cn">📌 {cn_task}</span>
                        <span class="en">{task_id}</span>
                    </div>
                    <div class="grid">
                ''')

                for m in models:
                    badge_cls = "badge-new" if m['status'] == "新发布" else "badge-upd"
                    html_parts.append(f'''
                    <div class="card">
                        <div class="img-box">
                            <div class="badge {badge_cls}">{m['status']}</div>
                            <img class="model-img" src="{m['thumb']}" onerror="this.src='https://huggingface.co/front/assets/huggingface_logo-noborder.svg'">
                        </div>
                        <div class="info">
                            <div class="info-stats">
                                <div class="stat-box">
                                    <span class="stat-label">人气 Likes</span>
                                    <span class="stat-value">{m['likes']}</span>
                                </div>
                                <div class="stat-box" style="text-align:right;">
                                    <span class="stat-label">下载量 DLs</span>
                                    <span class="stat-value dl">{m['downloads']}</span>
                                </div>
                            </div>
                            <div class="time-box">
                                <span class="time-label">更新时刻</span>
                                <span class="time-val">{m['time_full']}</span>
                            </div>
                        </div>
                    </div>
                    ''')
                html_parts.append('</div></div>')

            img_filename = f"{category_name}.png"
            img_path = os.path.join(today_str, img_filename)
            await html_to_image("".join(html_parts), img_path)
            
            final_output["categories"][category_name] = {
                "image_url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{today_str}/{img_filename}",
                "count": total_in_cat
            }

    with open(os.path.join(today_str, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=4)
    print(f"\n✅ 海报已按子分类分组生成：开源模型动态 + 下载量 + 完整日期")

if __name__ == "__main__":
    asyncio.run(run_main())
