import requests
import datetime
import os
import json
import re
import time

# 从环境变量中获取 API Key 和 仓库名
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
    """
    抓取模型页面的 og:image 下载并返回 GitHub Raw URL。
    """
    default_icon = "https://huggingface.co/front/assets/huggingface_logo-noborder.svg"
    icon_url = default_icon
    
    try:
        html_url = f"https://huggingface.co/{model_id}"
        r = requests.get(html_url, timeout=10)
        if r.status_code == 200:
            match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', r.text)
            if match:
                icon_url = match.group(1)
        
        # 下载图片到本地 /icons 文件夹
        img_r = requests.get(icon_url, timeout=15)
        if img_r.status_code == 200:
            icons_dir = os.path.join(today_str, "icons")
            os.makedirs(icons_dir, exist_ok=True)
            
            ext = ".png"
            if "jpeg" in icon_url or "jpg" in icon_url: ext = ".jpg"
            elif "svg" in icon_url: ext = ".svg"
            
            safe_model_id = model_id.replace("/", "_")
            filename = f"{safe_model_id}{ext}"
            filepath = os.path.join(icons_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(img_r.content)
            
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{today_str}/icons/{filename}"
            return raw_url
    except Exception as e:
        print(f"      [警告] 下载图片失败 {model_id}: {e}")
        
    return icon_url

def generate_summary_with_ai(model_id):
    """
    [精读模式]：通过 Jina 读取并使用 Gemini 进行智能摘要
    """
    if not GEMINI_API_KEY:
        return "⚠️ 未配置 GEMINI_API_KEY，跳过 AI 摘要。"
        
    try:
        jina_url = f"https://r.jina.ai/https://huggingface.co/{model_id}"
        jina_r = requests.get(jina_url, timeout=20)
        content = jina_r.text[:8000] # 截取防超长
        
        prompt = (
            "请作为一名专业的AI算法工程师，总结以下HuggingFace模型的介绍。"
            "重点提取其：1.核心功能 2.主要参数/架构 3.效果表现/适用场景。"
            "字数严格控制在200字左右，语言生动、具有吸引力，让用户看完有想去体验或者尝试的冲动。"
            "请直接输出中文总结，不要包含诸如'这是一段总结'之类的废话。\n\n"
            f"网页内容：\n{content}"
        )
        
        gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents":[{"parts":[{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        
        gem_r = requests.post(gemini_endpoint, json=payload, headers=headers, timeout=30)
        if gem_r.status_code == 200:
            result = gem_r.json()
            summary = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return summary.strip()
        else:
            return f"❌ AI 总结失败 (HTTP {gem_r.status_code}): {gem_r.text[:100]}"
            
    except Exception as e:
        return f"获取详情或总结时发生异常: {e}"

def get_basic_snippet(model_id):
    """
    [降级模式]：普通正则提取 README 第一段文本 (用于排名 10 之后的模型)
    """
    url = f"https://huggingface.co/{model_id}/raw/main/README.md"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            lines = r.text.split('\n')
            if lines and lines[0].strip() == '---':
                try:
                    end_idx = lines.index('---', 1)
                    lines = lines[end_idx+1:]
                except ValueError:
                    pass
            snippet = ""
            for line in lines:
                line = line.strip()
                if line and not re.match(r'^(#|!\[|<|>|\||-)', line):
                    snippet += line + " "
                    if len(snippet) > 150:
                        break
            if snippet:
                return "[基础提取] " + snippet.strip()[:150] + "..."
    except Exception:
        pass
    return "暂无模型介绍（降级模式未获取到README）。"

def main():
    today_date = datetime.datetime.now(datetime.timezone.utc).date()
    today_str = today_date.strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    
    total_models_all_categories = 0
    print(f"🚀 开始抓取 {today_str} 更新与创建的模型...\n")

    for category_name, tasks in CATEGORIES.items():
        print(f"📂 正在处理大类: {category_name}")
        category_models_dict = {} 
        
        for task in tasks:
            for sort_type in ["lastModified", "createdAt"]:
                url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort={sort_type}&limit=50"
                try:
                    response = requests.get(url, timeout=15)
                    response.raise_for_status()
                    models = response.json()
                except Exception as e:
                    continue
                    
                for m in models:
                    m_id = m.get("id")
                    if not m_id: continue
                    
                    m_created = m.get("createdAt", "")[:10]
                    m_modified = m.get("lastModified", "")[:10]
                    
                    is_updated_today = False
                    status_tags =[]
                    
                    if m_created == today_str:
                        is_updated_today = True
                        status_tags.append("New")
                    if m_modified == today_str:
                        is_updated_today = True
                        status_tags.append("Updated")
                        
                    if is_updated_today:
                        if m_id not in category_models_dict:
                            category_models_dict[m_id] = {
                                "id": m_id,
                                "url": f"https://huggingface.co/{m_id}",
                                "task": task,
                                "downloads": m.get("downloads", 0),
                                "likes": m.get("likes", 0),
                                "status": " & ".join(set(status_tags))
                            }
                        else:
                            existing_tags = category_models_dict[m_id]["status"].split(" & ")
                            all_tags = set(existing_tags + status_tags)
                            category_models_dict[m_id]["status"] = " & ".join(all_tags)

        models_list = list(category_models_dict.values())
        if models_list:
            # 🌟 核心修改：按点赞数 (likes) 降序排列，优先处理最火的模型
            models_list.sort(key=lambda x: x.get("likes", 0), reverse=True)
            
            print(f"   => 发现 {len(models_list)} 个模型，正在生成详情...")
            
            final_models_data =[]
            for idx, m_data in enumerate(models_list):
                print(f"      [{idx+1}/{len(models_list)}] 正在处理: {m_data['id']} (Likes: {m_data['likes']})")
                
                # 图片依然为大家全部下载
                m_data["icon_url"] = download_icon(m_data["id"], today_str)
                
                # 🌟 核心修改：只对前 10 名进行 AI 精读
                if idx < 10:
                    m_data["summary"] = generate_summary_with_ai(m_data["id"])
                    time.sleep(4) # 保护 API 不被封
                else:
                    # 第 11 名以后走极速降级模式
                    m_data["summary"] = get_basic_snippet(m_data["id"])
                    
                final_models_data.append(m_data)
                
            json_output = {
                "date": today_str,
                "category": category_name,
                "total": len(final_models_data),
                "ai_summarized_count": min(len(final_models_data), 10),
                "models": final_models_data
            }
            filepath = os.path.join(today_str, f"{category_name}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(json_output, f, ensure_ascii=False, indent=4)
                
            total_models_all_categories += len(final_models_data)
        else:
            print(f"   ➖ 今日无更新。")

    print(f"\n🎉 抓取结束！今日共计收录 {total_models_all_categories} 个模型的数据。")

if __name__ == "__main__":
    main()
