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

# 任务标识与中文简单说明的映射表
TASK_DESC = {
    "text-to-image": "文生图模型，通过文本提示语生成高质量图像。",
    "image-to-text": "图像转文本模型，如图像描述、图文问答等。",
    "text-generation": "文本生成模型，用于对话、写作、代码补全等。",
    "automatic-speech-recognition": "自动语音识别，将语音信号转为文字。",
    "text-to-speech": "语音合成模型，将文本转为自然的人类语音。",
    "audio-text-to-text": "音文双模态转换，多用于音频理解与翻译。",
    "object-detection": "目标检测，识别图像中的物体位置和类别。",
    "image-classification": "图像分类，对输入图像进行类别标注。",
    "translation": "机器翻译，支持多语种间的文本互译。",
    "summarization": "文本摘要，自动提取文章核心内容和要点。",
    "depth-estimation": "深度估计，从单幅图像推测场景深度信息。",
    "image-segmentation": "图像分割，像素级的物体区域划分。",
    "text-to-video": "文生视频，根据指令生成动态短视频。",
    "visual-question-answering": "视觉问答，基于图像内容进行对话问答。",
    "sentence-similarity": "句子相似度，计算文本间的语义契合度。",
    "feature-extraction": "特征提取，将原始数据转化为特征向量。",
    "any-to-any": "全能模态转换，支持跨多种媒体形式转换。",
    # ... 其余任务会自动 fallback 到默认描述
}

def get_simple_explanation(task_id, model_id):
    author = model_id.split('/')[0]
    base_desc = TASK_DESC.get(task_id, f"这是由 {author} 开发的 {task_id} 领域专业模型。")
    return f"该模型专注于 {task_id} 任务。{base_desc}"

async def html_to_image(html_content, output_path):
    """Playwright 满宽渲染长图"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 450, 'height': 800}, device_scale_factor=2)
        page = await context.new_page()
        await page.set_content(f"<html><body style='margin:0;padding:0;'>{html_content}</body></html>")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

def compress_html(html_list):
    raw_html = "".join(html_list).replace('\n', '').replace('\r', '').replace('\t', '')
    return re.sub(r'>\s+<', '><', raw_html).strip()

async def run_main():
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    
    final_output = {"date": today_str, "total_all": 0, "categories": {}}

    for category_name, tasks in CATEGORIES.items():
        print(f"📂 正在处理: {category_name}")
        category_sub_data, category_total = {}, 0
        
        for task in tasks:
            # 极速拉取列表，不再区分 modified/created，因为 lastModified 已经包含了两者
            try:
                url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=20"
                models = session.get(url, timeout=10).json()
                task_list = []
                for m in models:
                    m_id = m.get("id")
                    m_mod = (m.get("lastModified") or "")[:10]
                    m_cre = (m.get("createdAt") or "")[:10]
                    
                    if m_mod == today_str or m_cre == today_str:
                        status = "🆕 新增" if m_cre == today_str else "🔄 更新"
                        task_list.append({
                            "id": m_id,
                            "url": f"https://huggingface.co/{m_id}",
                            "downloads": m.get("downloads", 0),
                            "likes": m.get("likes", 0),
                            "status": status,
                            "task": task,
                            "summary": get_simple_explanation(task, m_id),
                            "icon": f"https://cdn-thumbnails.huggingface.co/social-thumbnails/models/{m_id}.png"
                        })
                
                if task_list:
                    # 按点赞数排个序
                    task_list.sort(key=lambda x: x['likes'], reverse=True)
                    category_sub_data[task] = task_list
                    category_total += len(task_list)
                    print(f"   => [{task}] 发现 {len(task_list)} 个动态")
            except: pass

        if category_total > 0:
            # 微信 HTML 无边距排版
            html_lines =[
                '<section style="font-family:-apple-system,BlinkMacSystemFont,Arial,sans-serif;color:#333;line-height:1.6;padding:0;margin:0;width:100%;overflow-x:hidden;">',
                '<section style="line-height:0;margin:0;"><img src="https://mmbiz.qpic.cn/mmbiz_png/qHfXxy1pes10fIch7kKDnTcV7tJMdWticbFaZx6aXXLjxHFsQWCWr3TyiaVY11COWfF8yJnIQiasxfWKQ4dYAAvyFYZET5bT9PXJnuKzjVjEgM/640?wx_fmt=png" style="width:100%;display:block;"></section>',
                f'<section style="text-align:center;margin:25px 0;"><section style="font-size:22px;font-weight:bold;color:#2c3e50;">{category_name.replace("_"," ")} 今日快讯</section></section>'
            ]
            
            for t_name, m_list in category_sub_data.items():
                html_lines.append(f'<section style="margin:25px 0 15px 0;border-left:5px solid #0052d9;background-color:#f4f8fe;padding:10px 15px;width:100%;box-sizing:border-box;"><strong style="font-size:16px;color:#0052d9;">📌 {t_name}</strong></section>')
                for i, m in enumerate(m_list):
                    html_lines.append(f'''
                    <section style="margin:0 0 15px 0;border-top:1px solid #eee;border-bottom:1px solid #eee;padding:15px;background-color:#fff;width:100%;box-sizing:border-box;">
                        <section style="margin-bottom:10px;"><strong style="font-size:15px;color:#e96900;">{m['id']}</strong> <span style="font-size:11px;color:#999;border:1px solid #ddd;padding:1px 4px;border-radius:3px;margin-left:5px;">{m['status']}</span></section>
                        <section style="overflow:hidden;margin-bottom:10px;">
                            <img src="{m['icon']}" style="width:40px;height:40px;border-radius:6px;float:left;margin-right:10px;object-fit:cover;border:1px solid #eee;">
                            <section style="font-size:13px;color:#666;">📥 {m['downloads']} 下载 | ❤️ {m['likes']} 点赞</section>
                        </section>
                        <section style="clear:both;font-size:14px;color:#444;line-height:1.5;">{m['summary']}</section>
                    </section>
                    ''')
            
            html_lines.append('<section style="line-height:0;margin-top:10px;"><img src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif" style="width:100%;display:block;"></section></section>')
            
            # 转图片
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
        with open(os.path.join(today_str, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 极速抓取完成！图片与汇总 JSON 已生成。")

if __name__ == "__main__":
    asyncio.run(run_main())
