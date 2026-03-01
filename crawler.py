import requests
import datetime
import os
import re
import time

# 🎯 根据提取的 HTML 精心分类的任务字典
CATEGORIES = {
    "Multimodal":[
        "audio-text-to-text", "image-text-to-text", "image-text-to-image", 
        "image-text-to-video", "visual-question-answering", "document-question-answering", 
        "video-text-to-text", "visual-document-retrieval", "any-to-any"
    ],
    "Computer_Vision":[
        "depth-estimation", "image-classification", "object-detection", 
        "image-segmentation", "text-to-image", "image-to-text", "image-to-image", 
        "image-to-video", "unconditional-image-generation", "video-classification", 
        "text-to-video", "zero-shot-image-classification", "mask-generation", 
        "zero-shot-object-detection", "text-to-3d", "image-to-3d", 
        "image-feature-extraction", "keypoint-detection", "video-to-video"
    ],
    "Natural_Language_Processing":[
        "text-classification", "token-classification", "table-question-answering", 
        "question-answering", "zero-shot-classification", "translation", 
        "summarization", "feature-extraction", "text-generation", "fill-mask", 
        "sentence-similarity", "text-ranking"
    ],
    "Audio":[
        "text-to-speech", "text-to-audio", "automatic-speech-recognition", 
        "audio-to-audio", "audio-classification", "voice-activity-detection"
    ],
    "Tabular":[
        "tabular-classification", "tabular-regression", "time-series-forecasting"
    ],
    "Reinforcement_Learning": [
        "reinforcement-learning", "robotics"
    ],
    "Other": [
        "graph-ml"
    ]
}

def get_readme_snippet(model_id):
    """获取模型的 README.md 并提取第一段纯文本作为模型简介说明"""
    url = f"https://huggingface.co/{model_id}/raw/main/README.md"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            lines = r.text.split('\n')
            
            # 去除 YAML 元数据 (--- 包裹的部分)
            if lines and lines[0].strip() == '---':
                try:
                    end_idx = lines.index('---', 1)
                    lines = lines[end_idx+1:]
                except ValueError:
                    pass
            
            snippet = ""
            for line in lines:
                line = line.strip()
                # 过滤常见的非说明文本标签
                if line and not re.match(r'^(#|!\[|<|>|\||-)', line):
                    snippet += line + " "
                    if len(snippet) > 200:
                        break
            
            if snippet:
                return snippet.strip()[:200] + "..."
            else:
                return "作者未提供纯文本说明，或说明由纯图表构成。"
    except Exception:
        pass
        
    return "暂无模型介绍（可能为无 README 的私有/空白模型）。"

def main():
    today = datetime.datetime.now(datetime.timezone.utc).date()
    total_models_all_categories = 0
    
    print(f"🚀 开始抓取 {today} 在 HuggingFace 更新的模型...")

    # 遍历每个大类
    for category_name, tasks in CATEGORIES.items():
        print(f"\n📂 正在处理大类: {category_name}")
        
        category_total_models = 0
        report_lines =[
            f"# 🤖 {category_name.replace('_', ' ')} 领域模型每日更新追踪 ({today})",
            "> 本报告自动生成，为您盘点今日最新更新的模型及其简介说明。\n"
        ]
        
        # 遍历该大类下的每个子任务
        for task in tasks:
            # HuggingFace API, sort=lastModified 对应网页的 sort=modified
            url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=100"
            
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                models = response.json()
            except Exception as e:
                print(f"  ❌ 获取任务 {task} 失败: {e}")
                continue
                
            updated_today =[]
            for model in models:
                last_modified_str = model.get("lastModified")
                if not last_modified_str:
                    continue
                
                # 比较日期
                try:
                    model_date = datetime.datetime.strptime(last_modified_str[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue
                    
                if model_date == today:
                    updated_today.append(model)
            
            # 只有当该子任务今天有更新时，才写入报告
            if updated_today:
                report_lines.append(f"## 📌 子任务分类：`{task}`")
                
                for idx, model in enumerate(updated_today, 1):
                    model_id = model.get("id", "Unknown")
                    downloads = model.get("downloads", 0)
                    likes = model.get("likes", 0)
                    model_url = f"https://huggingface.co/{model_id}"
                    
                    # 为了防止触发反爬，稍微停顿一下
                    time.sleep(0.1) 
                    snippet = get_readme_snippet(model_id)
                    
                    report_lines.append(f"### {idx}. [{model_id}]({model_url})")
                    report_lines.append(f"- 📊 **数据**: 📥 {downloads} 次下载 | ❤️ {likes} 次点赞")
                    report_lines.append(f"- 📝 **模型说明**: {snippet}\n")
                    
                    category_total_models += 1
                    total_models_all_categories += 1
                    
                print(f"  ✅ {task}: 找到 {len(updated_today)} 个更新。")
            else:
                print(f"  ➖ {task}: 今日无更新。")
        
        # 如果该大类下今天有任何模型更新，就将其写入对应的 Markdown 文件
        if category_total_models > 0:
            filename = f"Report_{category_name}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
            print(f"💾 已保存 {category_name} 大类的报告至 -> {filename}")
        else:
            print(f"📭 {category_name} 大类今日暂无更新，不生成文件。")

    print(f"\n🎉 抓取结束！今日所有分类共计更新 {total_models_all_categories} 个模型。")

if __name__ == "__main__":
    main()
