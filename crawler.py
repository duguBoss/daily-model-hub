import requests
import datetime
import os
import json
import re
import time
from openai import OpenAI

# ---------------------------------------------------------
# 配置信息
# ---------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "your-username/your-repo")

# 初始化 OpenAI 客户端 (替换为你专属的 Base URL 和 Key)
client = OpenAI(
    api_key=OPENAI_API_KEY or "sk-xxxxxx", # 避免未配置环境变量时报错，也可以直接把你的key写死在这里测试
    base_url="http://43.160.201.19:3000/v1"
)
# 指定请求的模型名称
AI_MODEL_NAME = "gpt-5.3-codex"

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
    try:
        r = requests.get(f"https://huggingface.co/{model_id}", timeout=10)
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
    """双分支探测拉取原始 Markdown 文件，并增加伪装头防拦截"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    urls_to_try =[
        f"https://huggingface.co/{model_id}/raw/main/README.md",
        f"https://huggingface.co/{model_id}/raw/master/README.md",
        f"https://huggingface.co/{model_id}/raw/main/readme.md",
        f"https://huggingface.co/{model_id}/resolve/main/README.md"
    ]
    
    for url in urls_to_try:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                text = r.text
                if text.startswith('---'):
                    parts = text.split('---', 2)
                    if len(parts) >= 3:
                        text = parts[2]
                text = text.strip()
                if not text:
                    return "README 文件内容为空。"
                return text[:4000] # 截取前 4000 字符交给 AI
        except:
            continue
            
    return "未找到 README.md，该模型作者可能未提供详情文件。"

def generate_ai_content(model_id, mode="detailed"):
    """使用 OpenAI 库对模型进行纯中文分析"""
    if not OPENAI_API_KEY:
        return "⚠️ 未配置 OPENAI_API_KEY。"
        
    readme_content = get_raw_readme(model_id)
    
    # 优雅降级
    if "未找到 README.md" in readme_content or "文件内容为空" in readme_content:
        if mode == "detailed":
            return "作者暂未提供该模型的详细说明文档，建议前往 HuggingFace 仓库主页查看其配置文件。"
        else:
            return "暂无模型介绍文档。"
    
    if mode == "detailed":
        prompt = (
            f"请作为专业的AI算法工程师，对以下HuggingFace模型进行中文总结。\n"
            f"要求：1.必须纯中文；2.提取核心功能、架构参数和适用场景；3.字数200字左右；"
            f"4.语气生动，直接输出正文，禁止出现“摘要如下”等废话。\n\n"
            f"模型内容：\n{readme_content}"
        )
    else:
        prompt = (
            f"请用一句纯中文概括以下HuggingFace模型的作用。\n"
            f"要求：1.必须纯中文；2.字数限制在40字以内；3.直接输出，不加任何前缀。\n\n"
            f"模型内容：\n{readme_content}"
        )
        
    error_msg = ""
    # 失败重试 3 次
    for _ in range(3):
        try:
            response = client.chat.completions.create(
                model=AI_MODEL_NAME,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=20  # 设置超时防止卡死
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_msg = str(e)
            time.sleep(2)
            
    return f"⚠️ 抓到了 README，但 AI 摘要失败。报错详情: {error_msg}"

def compress_html(html_list):
    """将 HTML 列表合并，并极限压缩为单行无空格字符串"""
    raw_html = "".join(html_list)
    raw_html = raw_html.replace('\n', '').replace('\r', '')
    compressed_html = re.sub(r'>\s+<', '><', raw_html)
    return compressed_html.strip()

def main():
    today_date = datetime.datetime.now(datetime.timezone.utc).date()
    today_str = today_date.strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    
    total_models_all = 0
    final_output_data = {
        "date": today_str,
        "total_updates": 0,
        "categories": {}
    }
    
    print(f"🚀 开始抓取 {today_str} 模型...\n")

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
                            is_today, tags = True, tags +["🆕 新增"]
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
                
                print(f"   => 子类 [{task}] 找到 {len(task_models_list)} 个模型")
                
                for idx, m_data in enumerate(task_models_list):
                    if idx < 3:
                        m_data["is_top_3"] = True
                        m_data["icon_url"] = download_icon(m_data["id"], today_str)
                        m_data["summary"] = generate_ai_content(m_data["id"], mode="detailed")
                    else:
                        m_data["is_top_3"] = False
                        m_data["summary"] = generate_ai_content(m_data["id"], mode="brief")
                    
                    # 强力保护自定义 API 接口并发限制
                    time.sleep(3)
                        
                category_data[task] = task_models_list
                category_total_updates += len(task_models_list)
                total_models_all += len(task_models_list)

        # ---------------------------------------------------------
        # 构建当前大类的纯净无缝隙 HTML
        # ---------------------------------------------------------
        if category_total_updates > 0:
            cat_title = category_name.replace("_", " ")
            html_lines =[
                '<section style="max-width: 677px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; color: #333; line-height: 1.6; padding: 0; box-sizing: border-box; overflow-x: hidden; width: 100%;">',
                
                '<section style="margin: 0; padding: 0; line-height: 0;">',
                '<img src="https://mmbiz.qpic.cn/mmbiz_png/qHfXxy1pes10fIch7kKDnTcV7tJMdWticbFaZx6aXXLjxHFsQWCWr3TyiaVY11COWfF8yJnIQiasxfWKQ4dYAAvyFYZET5bT9PXJnuKzjVjEgM/640?wx_fmt=png" style="width: 100%; display: block; margin: 0; padding: 0; border: none;">',
                '</section>',
                
                '<section style="text-align: center; margin: 25px 0 25px 0; padding: 0 15px;">',
                f'<section style="font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 5px;">🤖 {cat_title} 更新风云榜</section>',
                f'<section style="font-size: 14px; color: #888;">📅 {today_str} | 该领域今日共收录 {category_total_updates} 款精选模型</section>',
                '</section>'
            ]
            
            for task_name, models_list in category_data.items():
                html_lines.append(f'''
                <section style="margin: 30px 0 20px 0; border-left: 5px solid #0052d9; background-color: #f4f8fe; padding: 12px 15px; box-sizing: border-box; width: 100%;">
                    <strong style="font-size: 17px; color: #0052d9;">📌 {task_name}</strong> 
                    <span style="font-size: 13px; color: #666;">(收录 {len(models_list)} 款)</span>
                </section>
                ''')
                
                for i, m in enumerate(models_list):
                    if m["is_top_3"]:
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
                                <strong style="color: #d35400;">💡 AI 解析：</strong>{m['summary']}
                            </section>
                        </section>
                        ''')
                    else:
                        if i == 3:
                            html_lines.append('<section style="margin: 0 0 20px 0; padding: 18px 15px; background-color: #fafafa; border-top: 1px dashed #ddd; border-bottom: 1px dashed #ddd; box-sizing: border-box; width: 100%;">')
                            html_lines.append('<section style="font-size: 15px; font-weight: bold; margin-bottom: 15px; color: #555;">🔹 其他热门模型直达</section>')
                        
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
            
            # 将提示移到图片上方，保证最后一张图彻底压在最底边
            html_lines.extend([
                '<section style="text-align: center; font-size: 12px; color: #bbb; margin: 30px 0; padding: 20px 15px; border-top: 1px solid #eee;">本文由 AI 自动聚合追踪，数据源自 HuggingFace</section>',
                '<section style="margin: 0; padding: 0; line-height: 0;">',
                '<img src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif" style="width: 100%; display: block; margin: 0; padding: 0; border: none;">',
                '</section>',
                '</section>'
            ])
            
            compressed_html = compress_html(html_lines)
            
            final_output_data["categories"][category_name] = {
                "total": category_total_updates,
                "html_content": compressed_html,
                "subcategories": category_data
            }

    # ===============================================
    # 💾 最后：把所有数据汇总保存到一个唯一的 JSON 文件里
    # ===============================================
    final_output_data["total_updates"] = total_models_all
    
    if total_models_all > 0:
        json_filepath = os.path.join(today_str, f"{today_str}_summary.json")
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(final_output_data, f, ensure_ascii=False, indent=4)
        print(f"\n🎉 完美收工！共计 {total_models_all} 个模型。所有数据和单行 HTML 已聚合保存至: {json_filepath}")
    else:
        print("\n📭 今日暂无任何模型更新。")

if __name__ == "__main__":
    main()
