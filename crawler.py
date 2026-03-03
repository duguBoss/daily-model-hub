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
    """使用 Playwright 渲染高质量清单图片"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # 针对列表，设置一个较宽的视图方便微信阅读 (450px)
        context = await browser.new_context(viewport={'width': 450, 'height': 100}, device_scale_factor=2)
        page = await context.new_page()
        # 强制设置背景色防止透明
        await page.set_content(f"<html><body style='margin:0;padding:0;background-color:#ffffff;'>{html_content}</body></html>")
        await page.wait_for_timeout(1000)
        # full_page=True 会根据内容高度自动伸缩
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

def compress_html(html_list):
    """HTML 极限压缩"""
    raw_html = "".join(html_list).replace('\n', '').replace('\r', '').replace('\t', '')
    return re.sub(r'>\s+<', '><', raw_html).strip()

def format_time(iso_str):
    """从 ISO 时间中提取 HH:mm"""
    try:
        # iso_str 格式: 2024-05-18T12:34:56.000Z
        t_part = iso_str.split('T')[1][:5]
        return t_part
    except:
        return "--:--"

async def run_main():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    
    final_output = {"date": today_str, "total_all": 0, "categories": {}}

    for category_name, tasks in CATEGORIES.items():
        print(f"📂 正在分析: {category_name}")
        category_sub_data, category_total = {}, 0
        
        for task in tasks:
            try:
                url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=20"
                models = session.get(url, timeout=10).json()
                task_list = []
                for m in models:
                    m_id = m.get("id")
                    m_mod_full = m.get("lastModified", "")
                    m_mod_day = m_mod_full[:10]
                    m_cre_day = (m.get("createdAt") or "")[:10]
                    
                    if m_mod_day == today_str or m_cre_day == today_str:
                        status_label = "NEW" if m_cre_day == today_str else "UPD"
                        task_list.append({
                            "id": m_id,
                            "url": f"https://huggingface.co/{m_id}",
                            "likes": m.get("likes", 0),
                            "downloads": m.get("downloads", 0),
                            "status": status_label,
                            "time": format_time(m_mod_full),
                            "tag": task
                        })
                
                if task_list:
                    task_list.sort(key=lambda x: x['likes'], reverse=True)
                    category_sub_data[task] = task_list
                    category_total += len(task_list)
            except: pass

        if category_total > 0:
            # --- 微信 100% 满宽极简清单 HTML 构建 ---
            html_lines = [
                '<section style="font-family:-apple-system,BlinkMacSystemFont,Arial,sans-serif;color:#333;padding:0;margin:0;width:100%;background-color:#fff;overflow-x:hidden;">',
                # 顶部图片
                '<section style="line-height:0;margin:0;padding:0;"><img src="https://mmbiz.qpic.cn/mmbiz_png/qHfXxy1pes10fIch7kKDnTcV7tJMdWticbFaZx6aXXLjxHFsQWCWr3TyiaVY11COWfF8yJnIQiasxfWKQ4dYAAvyFYZET5bT9PXJnuKzjVjEgM/640?wx_fmt=png" style="width:100%;display:block;margin:0;"></section>',
                # 标题
                f'<section style="padding:20px 15px;text-align:left;border-bottom:2px solid #333;margin-bottom:10px;"><section style="font-size:24px;font-weight:bold;letter-spacing:1px;">{category_name.replace("_"," ")} 更新一览</section><section style="font-size:13px;color:#888;margin-top:5px;">DATE: {today_str} | TOTAL: {category_total} MODELS</section></section>'
            ]
            
            for t_name, m_list in category_sub_data.items():
                # 子类的小标题条
                html_lines.append(f'<section style="background-color:#f0f0f0;padding:5px 15px;font-size:12px;font-weight:bold;color:#666;text-transform:uppercase;letter-spacing:1px;"># {t_name}</section>')
                
                for m in m_list:
                    # 状态颜色
                    color = "#10ad57" if m['status'] == "NEW" else "#0052d9"
                    
                    html_lines.append(f'''
                    <section style="display:flex;justify-content:space-between;align-items:center;padding:12px 15px;border-bottom:1px solid #eee;width:100%;box-sizing:border-box;">
                        <section style="flex:1;padding-right:10px;">
                            <section style="font-size:15px;font-weight:bold;color:#222;word-break:break-all;line-height:1.3;">{m['id']}</section>
                            <section style="font-size:11px;margin-top:4px;display:flex;align-items:center;">
                                <span style="color:{color};border:1px solid {color};padding:0px 4px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:8px;">{m['status']}</span>
                                <span style="color:#999;">🕙 {m['time']} 更新</span>
                            </section>
                        </section>
                        <section style="text-align:right;min-width:70px;">
                            <section style="font-size:13px;color:#444;font-weight:bold;">❤️ {m['likes']}</section>
                            <section style="font-size:11px;color:#aaa;">📥 {m['downloads']}</section>
                        </section>
                    </section>
                    ''')

            # 底部收尾
            html_lines.append('<section style="text-align:center;padding:20px 15px;font-size:11px;color:#ccc;letter-spacing:1px;">- DATA SOURCE: HUGGINGFACE HUB -</section>')
            html_lines.append('<section style="line-height:0;margin:0;"><img src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif" style="width:100%;display:block;margin:0;"></section>')
            html_lines.append('</section>')
            
            # 转图片并保存
            img_filename = f"{category_name}.png"
            img_path = os.path.join(today_str, img_filename)
            await html_to_image("".join(html_lines), img_path)
            
            final_output["categories"][category_name] = {
                "image_url": f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{today_str}/{img_filename}",
                "total": category_total,
                "html_compressed": compress_html(html_lines)
            }
            final_output["total_all"] += category_total

    if final_output["total_all"] > 0:
        json_path = os.path.join(today_str, "summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 极速清单模式完成！图片已存入日期文件夹。")

if __name__ == "__main__":
    asyncio.run(run_main())
