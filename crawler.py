import requests
import datetime
import os
import json
import re
import time

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
    "Other":[
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
    # 获取当天的日期字符串，例如 "2026-03-01"
    today_date = datetime.datetime.now(datetime.timezone.utc).date()
    today_str = today_date.strftime("%Y-%m-%d")
    
    # 自动创建日期文件夹
    os.makedirs(today_str, exist_ok=True)
    
    total_models_all_categories = 0
    print(f"🚀 开始抓取 {today_str} 在 HuggingFace 更新的模型...")

    for category_name, tasks in CATEGORIES.items():
        print(f"\n📂 正在处理大类: {category_name}")
        
        category_models_data =[] # 用于存放该分类下所有的模型数据
        
        for task in tasks:
            url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=100"
            
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                models = response.json()
            except Exception as e:
                print(f"  ❌ 获取任务 {task} 失败: {e}")
                continue
                
            for model in models:
                last_modified_str = model.get("lastModified")
                if not last_modified_str:
                    continue
                
                try:
                    model_date = datetime.datetime.strptime(last_modified_str[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue
                    
                # 筛选今天更新的模型
                if model_date == today_date:
                    model_id = model.get("id", "Unknown")
                    
                    # 适度防封延迟
                    time.sleep(0.1)
                    snippet = get_readme_snippet(model_id)
                    
                    # 构建结构化数据
                    model_info = {
                        "id": model_id,
                        "url": f"https://huggingface.co/{model_id}",
                        "task": task,
                        "downloads": model.get("downloads", 0),
                        "likes": model.get("likes", 0),
                        "description": snippet
                    }
                    category_models_data.append(model_info)
                    total_models_all_categories += 1
            
            # 简单打印日志
            updated_count = len([m for m in category_models_data if m['task'] == task])
            if updated_count > 0:
                print(f"  ✅ {task}: 找到 {updated_count} 个更新。")
            else:
                print(f"  ➖ {task}: 今日无更新。")

        # 如果该大类今天有更新，则保存为独立的 JSON 文件
        if category_models_data:
            # 组装完整的 JSON 结构
            json_output = {
                "date": today_str,
                "category": category_name,
                "total_updates": len(category_models_data),
                "models": category_models_data
            }
            
            filepath = os.path.join(today_str, f"{category_name}.json")
            
            # 写入 JSON，ensure_ascii=False 保证中文字符正常显示
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(json_output, f, ensure_ascii=False, indent=4)
                
            print(f"💾 已将 {category_name} 大类的 {len(category_models_data)} 个模型保存至 -> {filepath}")
        else:
            print(f"📭 {category_name} 大类今日暂无更新。")

    print(f"\n🎉 抓取结束！今日所有分类共计更新 {total_models_all_categories} 个模型。")

if __name__ == "__main__":
    main()
