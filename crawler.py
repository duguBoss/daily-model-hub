import requests
import datetime
import os
import json
import re
import time

# 获取 Gemini API Key 和 Github Repo
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "duguBoss/daily-model-hub")

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
    """抓取 og:image 并下载保存为图床"""
    default_icon = "https://huggingface.co/front/assets/huggingface_logo-noborder.svg"
    icon_url = default_icon
    try:
        r = requests.get(f"https://huggingface.co/{model_id}", timeout=10)
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
    except Exception:
        pass
    return icon_url

def generate_summary_with_ai(model_id):
    """使用 Gemini API 进行模型精读摘要"""
    if not GEMINI_API_KEY:
        return "⚠️ 未配置 GEMINI_API_KEY，跳过摘要。"
        
    try:
        jina_url = f"https://r.jina.ai/https://huggingface.co/{model_id}"
        jina_r = requests.get(jina_url, timeout=20)
        content = jina_r.text[:8000] # 截取前 8000 字
        
        prompt = (
            "请作为一名专业的AI算法工程师，总结以下HuggingFace模型的介绍。\n"
            "重点提取其：1.核心功能 2.主要参数/架构 3.效果表现/适用场景。\n"
            "字数严格控制在200字左右，语言生动、具有吸引力，让用户看完有想体验的冲动。\n"
            "直接输出中文总结正文，不要包含废话。\n\n"
            f"网页内容：\n{content}"
        )
        
        gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents":[{"parts":[{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        
        gem_r = requests.post(gemini_endpoint, json=payload, headers=headers, timeout=30)
        if gem_r.status_code == 200:
            result = gem_r.json()
            summary = result.get("candidates", [{}])[0].get("content", {}).get("parts",[{}])[0].get("text", "")
            return summary.strip()
        else:
            return f"❌ AI总结失败 (HTTP {gem_r.status_code})"
    except Exception as e:
        return f"获取详情发生异常: {e}"

def get_basic_snippet(model_id):
    """降级模式：正则提取 README 第一段"""
    url = f"https://huggingface.co/{model_id}/raw/main/README.md"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            lines = r.text.split('\n')
            if lines and lines[0].strip() == '---':
                try: lines = lines[lines.index('---', 1)+1:]
                except ValueError: pass
            snippet = ""
            for line in lines:
                line = line.strip()
                if line and not re.match(r'^(#|!\[|<|>|\||-)', line):
                    snippet += line + " "
                    if len(snippet) > 120: break
            if snippet: return snippet.strip()[:120] + "..."
    except: pass
    return "该模型暂无详细介绍。"

def main():
    today_date = datetime.datetime.now(datetime.timezone.utc).date()
    today_str = today_date.strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    
    total_models_all = 0
    print(f"🚀 开始抓取 {today_str} 更新与创建的模型...\n")

    for category_name, tasks in CATEGORIES.items():
        print(f"📂 正在处理大类: {category_name}")
        
        category_data = {}
        category_total_updates = 0
        
        for task in tasks:
            task_dict = {} 
            for sort_type in ["lastModified", "createdAt"]:
                try:
                    url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort={sort_type}&limit=50"
                    models = requests.get(url, timeout=15).json()
                    
                    for m in models:
                        m_id = m.get("id")
                        if not m_id: continue
                        
                        c_date = m.get("createdAt", "")[:10]
                        m_date = m.get("lastModified", "")[:10]
                        is_today, tags = False,[]
                        
                        if c_date == today_str:
                            is_today, tags = True, tags + ["🆕 新增"]
                        if m_date == today_str:
                            is_today, tags = True, tags + ["🔄 更新"]
                            
                        if is_today:
                            if m_id not in task_dict:
                                task_dict[m_id] = {
                                    "id": m_id, "url": f"https://huggingface.co/{m_id}",
                                    "downloads": m.get("downloads", 0),
                                    "likes": m.get("likes", 0), "status": " | ".join(set(tags))
                                }
                            else:
                                task_dict[m_id]["status"] = " | ".join(set(task_dict[m_id]["status"].split(" | ") + tags))
                except Exception:
                    pass

            task_models_list = list(task_dict.values())
            if task_models_list:
                task_models_list.sort(key=lambda x: x.get("likes", 0), reverse=True)
                task_models_list = task_models_list[:10] 
                
                print(f"   => 子类 [{task}] 发现 {len(task_models_list)} 个模型")
                
                for idx, m_data in enumerate(task_models_list):
                    if idx < 3:
                        m_data["is_ai_analyzed"] = True
                        m_data["icon_url"] = download_icon(m_data["id"], today_str)
                        m_data["summary"] = generate_summary_with_ai(m_data["id"])
                        time.sleep(4) 
                    else:
                        m_data["is_ai_analyzed"] = False
                        m_data["summary"] = get_basic_snippet(m_data["id"])
                        
                category_data[task] = task_models_list
                category_total_updates += len(task_models_list)
                total_models_all += len(task_models_list)

        # ---------------------------------------------------------
        # 📰 保存 JSON 与 微信极简 100% 宽 HTML
        # ---------------------------------------------------------
        if category_total_updates > 0:
            json_filepath = os.path.join(today_str, f"{category_name}.json")
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "date": today_str, 
                    "category": category_name, 
                    "total_updates": category_total_updates, 
                    "subcategories": category_data
                }, f, ensure_ascii=False, indent=4)
                
            cat_title = category_name.replace("_", " ")
            html_lines =[
                # 微信公众号最外层容器（严格去除 padding，使得内部元素可以 100% 贴边）
                '<section style="max-width: 677px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; color: #333; line-height: 1.6; padding: 0; box-sizing: border-box; overflow-x: hidden; width: 100%;">',
                
                # 🖼️ 插入指定的顶部图片（line-height:0 消灭上下缝隙，width:100% 占满全屏）
                '<section style="margin: 0; padding: 0; line-height: 0;">',
                '<img src="https://mmbiz.qpic.cn/mmbiz_png/qHfXxy1pes10fIch7kKDnTcV7tJMdWticbFaZx6aXXLjxHFsQWCWr3TyiaVY11COWfF8yJnIQiasxfWKQ4dYAAvyFYZET5bT9PXJnuKzjVjEgM/640?wx_fmt=png" style="width: 100%; display: block; margin: 0; padding: 0; border: none;">',
                '<img src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif" style="width: 100%; display: block; margin: 0; padding: 0; border: none;">',
                '</section>',
                
                # 大标题区域 (给内部文字留边距，但容器本身 0 margin)
                '<section style="text-align: center; margin: 25px 0 25px 0; padding: 0 15px;">',
                f'<section style="font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 5px;">🤖 {cat_title} 每日风云榜</section>',
                f'<section style="font-size: 14px; color: #888;">📅 {today_str} | 该领域今日共计追踪 {category_total_updates} 款模型</section>',
                '</section>'
            ]
            
            for task_name, models_list in category_data.items():
                # 子类标题 (同样是全屏宽度的设计，只控制左边框)
                html_lines.append(f'''
                <section style="margin: 30px 0 20px 0; border-left: 5px solid #0052d9; background-color: #f4f8fe; padding: 12px 15px; box-sizing: border-box; width: 100%;">
                    <strong style="font-size: 17px; color: #0052d9;">📌 {task_name}</strong> 
                    <span style="font-size: 13px; color: #666;">(收录 {len(models_list)} 款)</span>
                </section>
                ''')
                
                for i, m in enumerate(models_list):
                    if m["is_ai_analyzed"]:
                        # 👑 前 3 名精读卡片 (取消左右圆角，上下加上轻微边框线，实现完美的满宽视觉)
                        html_lines.append(f'''
                        <section style="margin: 0 0 20px 0; border-top: 1px solid #eaeaea; border-bottom: 1px solid #eaeaea; padding: 18px 15px; background-color: #ffffff; box-sizing: border-box; width: 100%;">
                            <section style="margin-bottom: 12px;">
                                <strong style="font-size: 16px; color: #e96900;">🏅 Top {i+1}: {m['id']}</strong>
                                <span style="font-size: 12px; color: #fff; background-color: #e96900; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">{m['status']}</span>
                            </section>
                            <section style="overflow: hidden; margin-bottom: 15px;">
                                <img src="{m.get('icon_url', '')}" style="width: 50px; height: 50px; border-radius: 8px; float: left; margin-right: 12px; object-fit: cover; border: 1px solid #eee;">
                                <section style="font-size: 14px; color: #555;">
                                    📥 <strong>{m['downloads']}</strong> 下载<br>
                                    ❤️ <strong>{m['likes']}</strong> 点赞
                                </section>
                            </section>
                            <section style="clear: both;"></section>
                            <section style="padding: 12px; background-color: #fff9f5; border-radius: 6px; font-size: 15px; color: #444; border-left: 3px solid #ff9900; line-height: 1.7;">
                                <strong style="color: #d35400;">💡 AI 总结：</strong>{m['summary']}
                            </section>
                        </section>
                        ''')
                    else:
                        # 💡 第 4 到 10 名列表 (采用通栏背景)
                        if i == 3:
                            html_lines.append('<section style="margin: 0 0 20px 0; padding: 18px 15px; background-color: #fafafa; border-top: 1px dashed #ddd; border-bottom: 1px dashed #ddd; box-sizing: border-box; width: 100%;">')
                            html_lines.append('<section style="font-size: 15px; font-weight: bold; margin-bottom: 15px; color: #555;">🔹 其他潜力模型直达</section>')
                        
                        border_style = "border-bottom: 1px solid #eee; padding-bottom: 12px;" if i < len(models_list)-1 else "border-bottom: none; padding-bottom: 0;"
                        
                        html_lines.append(f'''
                        <section style="margin-bottom: 12px; {border_style}">
                            <section style="font-size: 15px; margin-bottom: 6px;">
                                <strong style="color: #0052d9;">{m['id']}</strong> 
                                <span style="font-size: 12px; color: #888;">(❤️ {m['likes']})</span>
                            </section>
                            <section style="font-size: 14px; color: #666; line-height: 1.6;">{m['summary']}</section>
                        </section>
                        ''')
                        
                        if i == len(models_list) - 1:
                            html_lines.append('</section>')
            
            html_lines.append('<section style="text-align: center; font-size: 12px; color: #bbb; margin: 30px 0; padding: 20px 15px; border-top: 1px solid #eee;">本文由 AI 自动聚合追踪，数据源自 HuggingFace</section>')
            html_lines.append('</section>')
            
            html_filepath = os.path.join(today_str, f"{category_name}.html")
            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(html_lines))
                
            print(f"   📰 已生成专属 HTML 报告: {html_filepath}")

    print(f"\n🎉 全部抓取结束！今日全网总计追踪 {total_models_all} 个模型。")

if __name__ == "__main__":
    main()
