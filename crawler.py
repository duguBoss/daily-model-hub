import requests
import datetime
import os
import json
import re
import time

# ---------------------------------------------------------
# 配置信息
# ---------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "your-username/your-repo")
MODEL_NAME = "gemini-3.1-pro-preview" 

CATEGORIES = {
    "Multimodal":["audio-text-to-text", "image-text-to-text", "image-text-to-image", "image-text-to-video", "visual-question-answering", "document-question-answering", "video-text-to-text", "visual-document-retrieval", "any-to-any"],
    "Computer_Vision":["depth-estimation", "image-classification", "object-detection", "image-segmentation", "text-to-image", "image-to-text", "image-to-image", "image-to-video", "unconditional-image-generation", "video-classification", "text-to-video", "zero-shot-image-classification", "mask-generation", "zero-shot-object-detection", "text-to-3d", "image-to-3d", "image-feature-extraction", "keypoint-detection", "video-to-video"],
    "Natural_Language_Processing":["text-classification", "token-classification", "table-question-answering", "question-answering", "zero-shot-classification", "translation", "summarization", "feature-extraction", "text-generation", "fill-mask", "sentence-similarity", "text-ranking"],
    "Audio":["text-to-speech", "text-to-audio", "automatic-speech-recognition", "audio-to-audio", "audio-classification", "voice-activity-detection"],
    "Tabular":["tabular-classification", "tabular-regression", "time-series-forecasting"],
    "Reinforcement_Learning":["reinforcement-learning", "robotics"],
    "Other":["graph-ml"]
}

def download_icon(model_id, today_str):
    """仅针对 Top 3 抓取社交分享图作为图标"""
    default_icon = "https://huggingface.co/front/assets/huggingface_logo-noborder.svg"
    try:
        # 直接拼接 HF 官方的社交分享缩略图地址（更快，不用解析网页）
        icon_url = f"https://cdn-thumbnails.huggingface.co/social-thumbnails/models/{model_id}.png"
        img_r = requests.get(icon_url, timeout=10)
        if img_r.status_code == 200:
            icons_dir = os.path.join(today_str, "icons")
            os.makedirs(icons_dir, exist_ok=True)
            filename = f"{model_id.replace('/', '_')}.png"
            filepath = os.path.join(icons_dir, filename)
            with open(filepath, "wb") as f: f.write(img_r.content)
            return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{today_str}/icons/{filename}"
    except: pass
    return default_icon

def generate_ai_summary(m_info, mode="detailed"):
    """基于列表元数据（ID、标签等）让 AI 进行智能化、硬核的总结"""
    if not GEMINI_API_KEY: return "未配置密钥"
    
    # 构造元数据背景，让 AI 即使不看 README 也能猜出大半
    metadata = f"模型ID: {m_info['id']}, 任务类型: {m_info['task']}, 标签: {m_info.get('tags', [])}"
    
    if mode == "detailed":
        prompt = (
            f"你是一名资深AI开源社区大V。请根据以下模型元数据，撰写一段120字左右的中文推介。\n"
            f"要求：1.直接点出它解决了什么问题或属于哪个系列；2.推测其应用场景；3.语言硬核、生动，具有吸引力；4.直接输出正文。\n\n"
            f"元数据：{metadata}"
        )
    else:
        prompt = f"请用一句话中文神评论总结该模型（25字以内）：{metadata}"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    payload = {"contents": [{"parts":[{"text": prompt}]}]}
    
    for _ in range(3):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=25)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            elif r.status_code == 429: time.sleep(10)
        except: time.sleep(2)
    return "点击主页查看详情。"

def compress_html(html_list):
    raw_html = "".join(html_list).replace('\n', '').replace('\r', '').replace('\t', '')
    return re.sub(r'>\s+<', '><', raw_html).strip()

def main():
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    final_output = {"date": today_str, "total_updates_all": 0, "categories": {}}

    for category_name, tasks in CATEGORIES.items():
        print(f"📂 处理大类: {category_name}")
        category_sub_data, category_total = {}, 0
        
        for task in tasks:
            task_dict = {}
            # 仅抓取列表，速度极快
            for sort_type in ["lastModified", "createdAt"]:
                try:
                    url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort={sort_type}&limit=30"
                    models = requests.get(url, timeout=10).json()
                    for m in models:
                        m_id = m.get("id")
                        if (m.get("lastModified") or "")[:10] == today_str or (m.get("createdAt") or "")[:10] == today_str:
                            task_dict[m_id] = {
                                "id": m_id, "url": f"https://huggingface.co/{m_id}",
                                "downloads": m.get("downloads", 0), "likes": m.get("likes", 0),
                                "task": task, "tags": m.get("tags", [])
                            }
                except: pass

            sorted_models = sorted(task_dict.values(), key=lambda x: x['likes'], reverse=True)[:10]
            if sorted_models:
                print(f"   => 子类 [{task}] {len(sorted_models)} 个")
                for idx, m_data in enumerate(sorted_models):
                    if idx < 3:
                        m_data["is_detailed"] = True
                        m_data["icon_url"] = download_icon(m_data["id"], today_str)
                        m_data["summary"] = generate_ai_summary(m_data, "detailed")
                        time.sleep(6) # 保护并发
                    else:
                        m_data["is_detailed"] = False
                        m_data["summary"] = generate_ai_summary(m_data, "brief")
                        time.sleep(4)
                category_sub_data[task] = sorted_models
                category_total += len(sorted_models)

        if category_total > 0:
            # 100% 满宽微信 HTML 构建
            html_lines =[
                '<section style="font-family:-apple-system,BlinkMacSystemFont,Arial,sans-serif;color:#333;line-height:1.6;padding:0;margin:0;width:100%;overflow-x:hidden;box-sizing:border-box;">',
                '<section style="line-height:0;margin:0;padding:0;">',
                '<img src="https://mmbiz.qpic.cn/mmbiz_png/qHfXxy1pes10fIch7kKDnTcV7tJMdWticbFaZx6aXXLjxHFsQWCWr3TyiaVY11COWfF8yJnIQiasxfWKQ4dYAAvyFYZET5bT9PXJnuKzjVjEgM/640?wx_fmt=png" style="width:100%;display:block;margin:0;border:none;">',
                '</section>',
                f'<section style="text-align:center;margin:25px 0;padding:0 15px;"><section style="font-size:22px;font-weight:bold;color:#2c3e50;">🤖 {category_name.replace("_"," ")} 今日速报</section><section style="font-size:14px;color:#888;margin-top:5px;">📅 {today_str} | 该领域追踪到 {category_total} 款动态</section></section>'
            ]
            for t_name, m_list in category_sub_data.items():
                html_lines.append(f'<section style="margin:30px 0 15px 0;border-left:5px solid #0052d9;background-color:#f4f8fe;padding:12px 15px;width:100%;box-sizing:border-box;"><strong style="font-size:17px;color:#0052d9;">📌 {t_name}</strong></section>')
                for i, m in enumerate(m_list):
                    if m["is_detailed"]:
                        html_lines.append(f'''<section style="margin:0 0 20px 0;border-top:1px solid #eee;border-bottom:1px solid #eee;padding:18px 15px;background-color:#fff;width:100%;box-sizing:border-box;"><section style="margin-bottom:12px;"><strong style="font-size:16px;color:#e96900;">🏅 Top {i+1}: {m['id']}</strong></section><section style="overflow:hidden;margin-bottom:15px;"><img src="{m['icon_url']}" style="width:50px;height:50px;border-radius:8px;float:left;margin-right:12px;object-fit:cover;border:1px solid #eee;"><section style="font-size:14px;color:#555;">📥 <strong>{m['downloads']}</strong> 下载 | ❤️ <strong>{m['likes']}</strong> 点赞</section></section><section style="clear:both;padding:12px;background-color:#fff9f5;border-radius:6px;font-size:15px;color:#444;border-left:3px solid #ff9900;line-height:1.7;"><strong style="color:#d35400;">💡 AI 解析：</strong>{m['summary']}</section></section>''')
                    else:
                        if i == 3: html_lines.append('<section style="margin:0 0 20px 0;padding:18px 15px;background-color:#fafafa;border-top:1px dashed #ddd;border-bottom:1px dashed #ddd;width:100%;box-sizing:border-box;"><section style="font-size:15px;font-weight:bold;color:#555;margin-bottom:15px;">🔹 其他潜力模型直达</section>')
                        html_lines.append(f'<section style="margin-bottom:12px;border-bottom:1px solid #eee;padding-bottom:12px;"><section style="font-size:15px;margin-bottom:6px;"><strong style="color:#0052d9;">{m["id"]}</strong> <span style="font-size:12px;color:#888;">(❤️ {m["likes"]})</span></section><section style="font-size:14px;color:#666;line-height:1.6;">{m["summary"]}</section></section>')
                        if i == len(m_list)-1: html_lines.append('</section>')
            html_lines.append('<section style="text-align:center;font-size:12px;color:#bbb;margin:30px 0;padding:20px 15px;border-top:1px solid #eee;">本文由 AI 机器人自动追踪整理</section>')
            html_lines.append('<section style="line-height:0;margin:0;padding:0;"><img src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif" style="width:100%;display:block;margin:0;border:none;"></section>')
            html_lines.append('</section>')
            final_output["categories"][category_name] = {"total": category_total, "html_content": compress_html(html_lines), "subcategories": category_sub_data}
            final_output["total_updates_all"] += category_total

    if final_output["total_updates_all"] > 0:
        with open(os.path.join(today_str, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 聚合任务完成！全量数据已存入 summary.json")

if __name__ == "__main__":
    main()
