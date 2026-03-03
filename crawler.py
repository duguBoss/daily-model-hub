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
    """抓取 og:image 并下载保存到 Github 仓库作为静态图床"""
    default_icon = "https://huggingface.co/front/assets/huggingface_logo-noborder.svg"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        r = requests.get(f"https://huggingface.co/{model_id}", headers=headers, timeout=10)
        icon_url = default_icon
        if r.status_code == 200:
            match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', r.text)
            if match: icon_url = match.group(1)
            
        img_r = requests.get(icon_url, timeout=15)
        if img_r.status_code == 200:
            icons_dir = os.path.join(today_str, "icons")
            os.makedirs(icons_dir, exist_ok=True)
            ext = ".png"
            if "jpeg" in icon_url or "jpg" in icon_url: ext = ".jpg"
            elif "svg" in icon_url: ext = ".svg"
            
            filename = f"{model_id.replace('/', '_')}{ext}"
            filepath = os.path.join(icons_dir, filename)
            with open(filepath, "wb") as f:
                f.write(img_r.content)
            return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{today_str}/icons/{filename}"
    except:
        pass
    return default_icon

def get_raw_readme(model_id):
    """拉取原始 Markdown 文件"""
    headers = {"User-Agent": "Mozilla/5.0"}
    for branch in ["main", "master"]:
        url = f"https://huggingface.co/{model_id}/raw/{branch}/README.md"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                text = r.text
                if text.startswith('---'):
                    parts = text.split('---', 2)
                    if len(parts) >= 3: text = parts[2]
                return text.strip()[:4000]
        except:
            continue
    return ""

def generate_ai_content(model_id, mode="detailed"):
    """使用 gemini-3-flash-preview 接口进行总结"""
    if not GEMINI_API_KEY: return "⚠️ 未配置 API Key。"
    
    readme_content = get_raw_readme(model_id)
    if not readme_content:
        return "作者暂未提供详细文档，建议直接访问主页查看。"

    if mode == "detailed":
        prompt = (
            f"你是一名资深的AI开源社区测评博主。请根据以下README，写一段简练、硬核的中文推介词。\n"
            f"要求：\n1. 核心亮点：第一句直接点明解决了什么痛点；\n"
            f"2. 技术特性：用极简语言描述其独特架构或参数；\n"
            f"3. 应用建议：告诉读者最适合拿它做什么；\n"
            f"4. 字数120字左右，必须纯中文，直接输出正文。\n\n"
            f"README内容：\n{readme_content}"
        )
    else:
        prompt = f"请用一句话神评论总结该模型核心卖点，30字以内，必须纯中文，直接输出：\n\n{readme_content}"
        
    # 🚀 使用最新的 gemini-3-flash-preview 模型
    gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"
    payload = {"contents": [{"parts":[{"text": prompt}]}]}
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    
    for _ in range(3):
        try:
            r = requests.post(gemini_endpoint, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            elif r.status_code == 429: time.sleep(5)
            else: break
        except: time.sleep(2)
    return "摘要生成失败，请查看主页详情。"

def compress_html(html_list):
    """HTML 极限压缩：删除所有换行、回车以及标签间的空白"""
    raw_html = "".join(html_list).replace('\n', '').replace('\r', '').replace('\t', '')
    return re.sub(r'>\s+<', '><', raw_html).strip()

def main():
    # 获取 UTC 时间
    now = datetime.datetime.now(datetime.timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    
    final_output = {
        "date": today_str,
        "total_updates_all": 0,
        "categories": {}
    }
    
    print(f"🚀 启动 HuggingFace 每日追踪 (模型: gemini-3-flash-preview)")

    for category_name, tasks in CATEGORIES.items():
        print(f"📂 正在分析大类: {category_name}")
        category_data = {}
        category_total_count = 0
        
        for task in tasks:
            task_dict = {}
            # 合并 Modified 和 Created 进行去重
            for sort_type in ["lastModified", "createdAt"]:
                try:
                    url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort={sort_type}&limit=40"
                    models = requests.get(url, timeout=15).json()
                    for m in models:
                        m_id = m.get("id")
                        m_mod = (m.get("lastModified") or "")[:10]
                        m_cre = (m.get("createdAt") or "")[:10]
                        if m_mod == today_str or m_cre == today_str:
                            task_dict[m_id] = {
                                "id": m_id, "url": f"https://huggingface.co/{m_id}",
                                "downloads": m.get("downloads", 0), "likes": m.get("likes", 0),
                                "task": task
                            }
                except: pass

            # 每个子类按 Likes 排序，取前 10
            sorted_models = sorted(task_dict.values(), key=lambda x: x['likes'], reverse=True)[:10]
            
            if sorted_models:
                print(f"   => 子类 [{task}] 发现 {len(sorted_models)} 个更新")
                for idx, m_data in enumerate(sorted_models):
                    if idx < 3:
                        m_data["is_detailed"] = True
                        m_data["icon_url"] = download_icon(m_data["id"], today_str)
                        m_data["summary"] = generate_ai_content(m_data["id"], mode="detailed")
                        time.sleep(5) # 频率限制保护
                    else:
                        m_data["is_detailed"] = False
                        m_data["summary"] = generate_ai_content(m_data["id"], mode="brief")
                        time.sleep(4)
                
                category_data[task] = sorted_models
                category_total_count += len(sorted_models)

        # ---------------------------------------------------------
        # 构建该大类的微信 100% 满宽 HTML 字符串
        # ---------------------------------------------------------
        if category_total_count > 0:
            html_lines =[
                # 外层容器：0 padding, 0 margin, 100% width
                '<section style="font-family:-apple-system,BlinkMacSystemFont,Arial,sans-serif;color:#333;line-height:1.6;padding:0;margin:0;box-sizing:border-box;width:100%;overflow-x:hidden;">',
                # 顶部图片
                '<section style="line-height:0;margin:0;padding:0;">',
                '<img src="https://mmbiz.qpic.cn/mmbiz_png/qHfXxy1pes10fIch7kKDnTcV7tJMdWticbFaZx6aXXLjxHFsQWCWr3TyiaVY11COWfF8yJnIQiasxfWKQ4dYAAvyFYZET5bT9PXJnuKzjVjEgM/640?wx_fmt=png" style="width:100%;display:block;margin:0;border:none;">',
                '<img src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif" style="width:100%;display:block;margin:0;border:none;">',
                '</section>',
                # 标题
                f'<section style="text-align:center;margin:25px 0;padding:0 15px;"><section style="font-size:22px;font-weight:bold;color:#2c3e50;">🤖 {category_name.replace("_"," ")} 今日榜</section><section style="font-size:14px;color:#888;margin-top:5px;">📅 {today_str} | 追踪 {category_total_count} 款精选模型</section></section>'
            ]
            
            for t_name, m_list in category_data.items():
                html_lines.append(f'<section style="margin:30px 0 15px 0;border-left:5px solid #0052d9;background-color:#f4f8fe;padding:12px 15px;width:100%;box-sizing:border-box;"><strong style="font-size:17px;color:#0052d9;">📌 {t_name}</strong></section>')
                for i, m in enumerate(m_list):
                    if m["is_detailed"]:
                        html_lines.append(f'''
                        <section style="margin:0 0 20px 0;border-top:1px solid #eee;border-bottom:1px solid #eee;padding:18px 15px;background-color:#fff;width:100%;box-sizing:border-box;">
                            <section style="margin-bottom:12px;"><strong style="font-size:16px;color:#e96900;">🏅 Top {i+1}: {m['id']}</strong></section>
                            <section style="overflow:hidden;margin-bottom:15px;">
                                <img src="{m['icon_url']}" style="width:50px;height:50px;border-radius:8px;float:left;margin-right:12px;object-fit:cover;border:1px solid #eee;">
                                <section style="font-size:14px;color:#555;">📥 <strong>{m['downloads']}</strong> 下载 | ❤️ <strong>{m['likes']}</strong> 点赞</section>
                            </section>
                            <section style="clear:both;padding:12px;background-color:#fff9f5;border-radius:6px;font-size:15px;color:#444;border-left:3px solid #ff9900;line-height:1.7;">{m['summary']}</section>
                        </section>
                        ''')
                    else:
                        if i == 3: html_lines.append('<section style="margin:0 0 20px 0;padding:18px 15px;background-color:#fafafa;border-top:1px dashed #ddd;border-bottom:1px dashed #ddd;width:100%;box-sizing:border-box;"><section style="font-size:15px;font-weight:bold;color:#555;margin-bottom:15px;">🔹 其他潜力模型直达</section>')
                        html_lines.append(f'<section style="margin-bottom:12px;border-bottom:1px solid #eee;padding-bottom:12px;"><section style="font-size:15px;font-weight:bold;color:#0052d9;margin-bottom:4px;">{m["id"]}</section><section style="font-size:14px;color:#666;line-height:1.6;">{m["summary"]}</section></section>')
                        if i == len(m_list)-1: html_lines.append('</section>')

            # 底部收尾
            html_lines.append('<section style="text-align:center;font-size:12px;color:#bbb;margin:30px 0;padding:20px 15px;border-top:1px solid #eee;">本文由 AI 机器人自动追踪整理，数据源自 HuggingFace</section>')
            html_lines.append('<section style="line-height:0;margin:0;padding:0;"><img src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif" style="width:100%;display:block;margin:0;border:none;"></section>')
            html_lines.append('</section>')
            
            final_output["categories"][category_name] = {
                "total": category_total_count,
                "html_content": compress_html(html_lines),
                "subcategories": category_data
            }
            final_output["total_updates_all"] += category_total_count

    # 最终汇总保存
    if final_output["total_updates_all"] > 0:
        json_path = os.path.join(today_str, f"{today_str}_summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 任务圆满完成！汇总文件已保存至: {json_path}")
    else:
        print("\n📭 今日无任何模型更新，未生成文件。")

if __name__ == "__main__":
    main()
