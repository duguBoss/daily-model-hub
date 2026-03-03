import requests
import datetime
import os
import json
import re
import time

# ---------------------------------------------------------
# 配置信息 (请确保环境变量中已配置密钥)
# ---------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "your-username/your-repo")

# 【极速测试专属配置】：只测试 1 个大类，1 个子类
CATEGORIES = {
    "Test_Vision": ["text-to-image"]
}

def download_icon(model_id, today_str):
    default_icon = "https://huggingface.co/front/assets/huggingface_logo-noborder.svg"
    try:
        r = requests.get(f"https://huggingface.co/{model_id}", timeout=5)
        icon_url = default_icon
        if r.status_code == 200:
            match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', r.text)
            if match: icon_url = match.group(1)
            
        img_r = requests.get(icon_url, timeout=5)
        if img_r.status_code == 200:
            icons_dir = os.path.join(today_str, "icons")
            os.makedirs(icons_dir, exist_ok=True)
            ext = ".png"
            if "jpeg" in icon_url or "jpg" in icon_url: ext = ".jpg"
            elif "svg" in icon_url: ext = ".svg"
            
            filename = f"test_{model_id.replace('/', '_')}{ext}"
            filepath = os.path.join(icons_dir, filename)
            with open(filepath, "wb") as f:
                f.write(img_r.content)
            return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{today_str}/icons/{filename}"
    except:
        pass
    return default_icon

def get_raw_readme(model_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    urls_to_try =[
        f"https://huggingface.co/{model_id}/raw/main/README.md",
        f"https://huggingface.co/{model_id}/raw/master/README.md"
    ]
    for url in urls_to_try:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                text = r.text
                if text.startswith('---'):
                    parts = text.split('---', 2)
                    if len(parts) >= 3:
                        text = parts[2]
                text = text.strip()
                if text:
                    return text[:4000]
        except:
            continue
    return "未找到 README.md，该模型作者可能未提供详情文件。"

def generate_ai_content(model_id, mode="detailed"):
    if not GEMINI_API_KEY:
        return "⚠️ 测试中止：未检测到 GEMINI_API_KEY"
        
    readme_content = get_raw_readme(model_id)
    if "未找到 README.md" in readme_content or "文件内容为空" in readme_content:
        return "作者暂未提供该模型的详细说明文档。" if mode == "detailed" else "暂无说明。"
    
    if mode == "detailed":
        prompt = (
            f"请作为专业的AI算法工程师，对以下HuggingFace模型进行中文总结。\n"
            f"要求：1.必须纯中文；2.提取核心功能、架构参数和适用场景；3.字数200字左右；"
            f"4.语气生动，直接输出正文，禁止废话。\n\n"
            f"模型内容：\n{readme_content}"
        )
    else:
        prompt = (
            f"请用一句纯中文概括以下HuggingFace模型的作用。\n"
            f"要求：1.必须纯中文；2.字数限制在40字以内；3.直接输出，不加任何前缀。\n\n"
            f"模型内容：\n{readme_content}"
        )
        
    # 强制指定 gemini-3-flash-preview
    gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"
    payload = {"contents":[{"parts":[{"text": prompt}]}]}
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    
    error_msg = "未知网络异常"
    for attempt in range(2): # 测试版减少重试次数
        try:
            r = requests.post(gemini_endpoint, json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except KeyError:
                    return f"⚠️ 解析失败，原始返回: {str(data)[:100]}"
            elif r.status_code == 429:
                error_msg = f"HTTP 429 (限流)"
                time.sleep(2)
            else:
                error_msg = f"HTTP {r.status_code}: {r.text[:100]}"
                break
        except Exception as e:
            error_msg = f"请求异常: {repr(e)}"
            time.sleep(1)
            
    return f"⚠️ AI 测试失败。报错: {error_msg}"

def compress_html(html_list):
    raw_html = "".join(html_list).replace('\n', '').replace('\r', '')
    return re.sub(r'>\s+<', '><', raw_html).strip()

def main():
    today_date = datetime.datetime.now(datetime.timezone.utc).date()
    today_str = today_date.strftime("%Y-%m-%d")
    os.makedirs(today_str, exist_ok=True)
    
    print("====================================")
    print(f"🛠️  启动极速测试模式 ({today_str})")
    print("====================================\n")
    
    final_output_data = {"date": today_str, "total_updates": 0, "categories": {}}
    
    for category_name, tasks in CATEGORIES.items():
        category_data = {}
        category_total_updates = 0
        
        for task in tasks:
            task_dict = {} 
            # 极速测试：只拉取 lastModified，且 limit 设置为 5
            try:
                url = f"https://huggingface.co/api/models?pipeline_tag={task}&sort=lastModified&limit=5"
                models = requests.get(url, timeout=5).json()
                for m in models:
                    m_id = m.get("id")
                    if m_id:
                        task_dict[m_id] = {
                            "id": m_id, "url": f"https://huggingface.co/{m_id}",
                            "downloads": m.get("downloads", 0), "likes": m.get("likes", 0),
                            "status": "🔄 测试更新"
                        }
            except Exception as e:
                print(f"拉取列表失败: {e}")

            task_models_list = list(task_dict.values())
            if task_models_list:
                task_models_list.sort(key=lambda x: x.get("likes", 0), reverse=True)
                # 极速测试：只处理前 3 个模型 (1个精读，2个简读)
                task_models_list = task_models_list[:3] 
                
                print(f"⚡ 开始处理 [{task}] 的 {len(task_models_list)} 个测试模型...")
                
                for idx, m_data in enumerate(task_models_list):
                    print(f"   -> 正在测试模型: {m_data['id']}")
                    if idx < 1: # 第1个深度测试
                        m_data["is_top_3"] = True
                        m_data["icon_url"] = download_icon(m_data["id"], today_str)
                        m_data["summary"] = generate_ai_content(m_data["id"], mode="detailed")
                    else: # 后2个简略测试
                        m_data["is_top_3"] = False
                        m_data["summary"] = generate_ai_content(m_data["id"], mode="brief")
                        
                category_data[task] = task_models_list
                category_total_updates += len(task_models_list)

        if category_total_updates > 0:
            html_lines =[
                '<section style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; color: #333; line-height: 1.6; padding: 0; margin: 0; box-sizing: border-box; overflow-x: hidden; width: 100%;">',
                '<section style="margin: 0; padding: 0; line-height: 0;">',
                '<img src="https://mmbiz.qpic.cn/mmbiz_png/qHfXxy1pes10fIch7kKDnTcV7tJMdWticbFaZx6aXXLjxHFsQWCWr3TyiaVY11COWfF8yJnIQiasxfWKQ4dYAAvyFYZET5bT9PXJnuKzjVjEgM/640?wx_fmt=png" style="width: 100%; display: block; margin: 0; padding: 0; border: none;">',
                '</section>',
                '<section style="text-align: center; margin: 25px 0; padding: 0 15px;">',
                f'<section style="font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 5px;">🤖 {category_name} 测试排版</section>',
                f'<section style="font-size: 14px; color: #888;">📅 {today_str} | 测试模型数量：{category_total_updates}</section>',
                '</section>'
            ]
            
            for task_name, models_list in category_data.items():
                html_lines.append(f'''
                <section style="margin: 30px 0 20px 0; border-left: 5px solid #0052d9; background-color: #f4f8fe; padding: 12px 15px; box-sizing: border-box; width: 100%;">
                    <strong style="font-size: 17px; color: #0052d9;">📌 {task_name} (测试)</strong>
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
                                <section style="font-size: 14px; color: #555;">📥 <strong>{m['downloads']}</strong> 下载 | ❤️ <strong>{m['likes']}</strong> 点赞</section>
                            </section>
                            <section style="clear: both;"></section>
                            <section style="padding: 12px; background-color: #fff9f5; border-radius: 6px; font-size: 15px; color: #444; border-left: 3px solid #ff9900; line-height: 1.7;">
                                <strong style="color: #d35400;">💡 AI 解析：</strong>{m['summary']}
                            </section>
                        </section>
                        ''')
                    else:
                        if i == 1:
                            html_lines.append('<section style="margin: 0 0 20px 0; padding: 18px 15px; background-color: #fafafa; border-top: 1px dashed #ddd; border-bottom: 1px dashed #ddd; box-sizing: border-box; width: 100%;">')
                            html_lines.append('<section style="font-size: 15px; font-weight: bold; margin-bottom: 15px; color: #555;">🔹 其他测试模型</section>')
                        
                        html_lines.append(f'''
                        <section style="margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 12px;">
                            <section style="font-size: 15px; margin-bottom: 6px;">
                                <strong style="color: #0052d9;">{m['id']}</strong> <span style="font-size: 12px; color: #888;">(❤️ {m['likes']})</span>
                            </section>
                            <section style="font-size: 14px; color: #666; line-height: 1.6;">{m['summary']}</section>
                        </section>
                        ''')
                        if i == len(models_list) - 1:
                            html_lines.append('</section>')
            
            html_lines.extend([
                '<section style="text-align: center; font-size: 12px; color: #bbb; margin: 30px 0; padding: 20px 15px; border-top: 1px solid #eee;">测试数据</section>',
                '<section style="margin: 0; padding: 0; line-height: 0;">',
                '<img src="https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif" style="width: 100%; display: block; margin: 0; padding: 0; border: none;">',
                '</section></section>'
            ])
            
            final_output_data["categories"][category_name] = {
                "total": category_total_updates,
                "html_content": compress_html(html_lines),
                "subcategories": category_data
            }
            final_output_data["total_updates"] = category_total_updates

    if final_output_data["total_updates"] > 0:
        json_filepath = os.path.join(today_str, "test_summary.json")
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(final_output_data, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 测试完成！请检查 {json_filepath} 文件看报错与排版情况。")
    else:
        print("\n📭 测试失败：未抓取到任何数据。")

if __name__ == "__main__":
    main()
