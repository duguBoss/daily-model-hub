import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT_DIR = Path(__file__).resolve().parent
TRENDING_URL = "https://huggingface.co/models?sort=trending"
DATA_DIR = ROOT_DIR / "data"
DAILY_DIR = DATA_DIR / "daily"
WEEK_DIR = DATA_DIR / "week"
IMAGE_ROOT_DIR = ROOT_DIR / "assets" / "huggingface_model_cards"
RUN_DATE = datetime.now().date()
RUN_STAMP = RUN_DATE.strftime("%Y-%m-%d")
DAILY_OUTPUT_FILE = DAILY_DIR / f"{RUN_STAMP}.json"
RUN_IMAGE_DIR = IMAGE_ROOT_DIR / RUN_STAMP
MODEL_LIMIT = int(os.environ.get("HF_MODEL_LIMIT", "5") or "5")
WEEKLY_PICK_LIMIT = int(os.environ.get("HF_WEEKLY_PICK_LIMIT", "6") or "6")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)


def normalize_limit(value: int, fallback: int) -> int:
    return value if value > 0 else fallback


MODEL_LIMIT = normalize_limit(MODEL_LIMIT, 30)
WEEKLY_PICK_LIMIT = normalize_limit(WEEKLY_PICK_LIMIT, 6)


def ensure_dirs() -> None:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    WEEK_DIR.mkdir(parents=True, exist_ok=True)
    RUN_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def require_gemini_api_key() -> None:
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY. This workflow requires Gemini to generate Chinese summaries.")


def slugify(value: str) -> str:
    text = (value or "model").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80] or "model"


def cleanup_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\xa0", " ")).strip()


def markdown_to_text(markdown: str) -> str:
    text = markdown or ""
    text = re.sub(r"^---[\s\S]*?---", " ", text, flags=re.M)
    text = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", text)
    text = re.sub(r"`{1,3}([^`]+)`{1,3}", r"\1", text)
    text = re.sub(r"^>\s?", "", text, flags=re.M)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"[*_~]", " ", text)
    return cleanup_text(text)


def extract_intro_from_markdown(markdown: str) -> str:
    sanitized = re.sub(r"^---[\s\S]*?---\n?", "", markdown or "", flags=re.M)
    paragraphs = [markdown_to_text(block) for block in re.split(r"\n\s*\n", sanitized)]
    blocked_prefixes = ("title ", "language ", "tags ", "tag ", "license ", "datasets ", "dataset ")

    for paragraph in paragraphs:
        if not paragraph:
            continue
        if paragraph.lower().startswith(blocked_prefixes):
            continue
        if len(paragraph) >= 60:
            return paragraph
    return ""


def pick_description(candidates: list[str]) -> str:
    blocked_patterns = [
        r"^updated\b",
        r"^downloads?\b",
        r"^likes?\b",
        r"^license\b",
        r"^files and versions\b",
        r"^model tree\b",
        r"^collections\b",
        r"^spaces using\b",
        r"^inference providers\b",
        r"^this model has no model card\b",
    ]

    for candidate in candidates:
        text = cleanup_text(candidate)
        if len(text) < 40:
            continue
        if any(re.search(pattern, text, flags=re.I) for pattern in blocked_patterns):
            continue
        return text
    return ""


def extract_json_string(raw_text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw_text or "", flags=re.S | re.I)
    if fenced:
        return fenced.group(1).strip()
    return (raw_text or "").strip()


def parse_json_response(raw_text: str) -> dict | list:
    text = extract_json_string(raw_text)
    decoder = json.JSONDecoder()

    for start, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[start:])
            return value
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("No valid JSON object found", text, 0)


def chunk_list(items: list, size: int) -> list[list]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def build_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def call_gemini_json(session: requests.Session, prompt: str) -> dict:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    response = session.post(GEMINI_API_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return parse_json_response(text)


def summarize_models_in_chinese(session: requests.Session, models: list[dict]) -> list[dict]:
    if not models:
        return models

    summary_map = {}

    for batch in chunk_list(list(enumerate(models)), 8):
        payload = [
            {
                "index": index,
                "model_name": model["modelName"],
                "source_description": model["sourceDescription"],
                "card_summary": model["cardSummary"],
                "model_url": model["modelUrl"],
            }
            for index, model in batch
        ]

        prompt = (
            "You are an AI editor writing for a Chinese audience. "
            "For each model in the input, write one concise and accurate summary in Simplified Chinese. "
            "Do not invent facts. Do not use marketing language. "
            "Keep the original index for each item. "
            "Each `model_description` must be 70 to 140 Chinese characters and explain the model's positioning, capabilities, and likely use cases. "
            "Return JSON only, using this format: "
            '{"items":[{"index":0,"model_description":"..."}]}'
            "\nInput:\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )

        result = call_gemini_json(session, prompt)
        for item in result.get("items", []):
            index = item.get("index")
            description = cleanup_text(item.get("model_description", ""))
            if isinstance(index, int) and description:
                summary_map[index] = description

    for index, model in enumerate(models):
        fallback = cleanup_text(model.get("sourceDescription", "")) or "No description available."
        model["modelDescription"] = summary_map.get(index, fallback)

    return models


def fetch_readme_description(session: requests.Session, model_path: str) -> str:
    urls = [
        f"https://huggingface.co/{model_path}/resolve/main/README.md",
        f"https://huggingface.co/{model_path}/raw/main/README.md",
    ]

    for url in urls:
        try:
            response = session.get(url, timeout=30)
            if not response.ok:
                continue
            intro = extract_intro_from_markdown(response.text)
            if intro:
                return intro
        except requests.RequestException as exc:
            print(f"Failed to fetch README for {model_path}: {exc}")
    return ""


def scrape_trending_cards(page) -> list[dict]:
    page.goto(TRENDING_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_selector("main", timeout=30000)
    page.wait_for_timeout(3000)

    cards = page.evaluate(
        """(limit) => {
          const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
          const selectorCandidates = [
            "a.flex.items-center.justify-between.gap-4.p-2[href^='/']",
            "main a[href^='/']"
          ];
          const anchorGroups = selectorCandidates
            .map((selector) => Array.from(document.querySelectorAll(selector)))
            .filter((group) => group.length > 0);
          const anchors = anchorGroups[0] || [];
          const seen = new Set();
          const rows = [];

          for (const anchor of anchors) {
            const href = anchor.getAttribute("href") || "";
            const heading = anchor.querySelector("h4");
            if (!heading || !href.startsWith("/")) continue;

            const pathname = href.split("?")[0];
            const segments = pathname.split("/").filter(Boolean);
            if (segments.length < 1 || segments.length > 2) continue;
            if (seen.has(pathname)) continue;

            seen.add(pathname);
            rows.push({
              name: normalize(heading.textContent),
              href: new URL(pathname, location.origin).toString(),
              path: pathname,
              cardText: normalize(anchor.textContent)
            });

            if (rows.length >= limit) break;
          }

          return rows;
        }""",
        MODEL_LIMIT,
    )

    if not cards:
        raise RuntimeError("No model cards were found on the trending page.")

    return cards


def capture_card_screenshot(page, model_path: str, image_path: Path) -> None:
    """捕获模型卡片截图，确保使用4K分辨率以获得清晰图片."""
    # 构建精确的选择器来定位模型卡片
    locator = page.locator(f'a[href="{model_path}"]').filter(has=page.locator("h4")).first

    # 等待元素可见并滚动到视图中
    locator.wait_for(state="visible", timeout=10000)
    locator.scroll_into_view_if_needed()

    # 额外等待确保图片和文字渲染完成
    page.wait_for_timeout(500)

    # 截图
    locator.screenshot(path=str(image_path), type="png")


def capture_card_screenshot_4k(context, card: dict, image_path: Path) -> None:
    """在4K分辨率下打开模型页面并截图模型卡片.

    为了确保截图清晰，我们：
    1. 在4K分辨率下打开新页面
    2. 等待页面完全加载
    3. 找到模型卡片元素
    4. 滚动到视图中
    5. 等待图片渲染完成
    6. 截图保存
    """
    page = context.new_page()
    try:
        # 在4K分辨率下打开模型页面
        page.goto(card["href"], wait_until="networkidle", timeout=60000)

        # 等待页面主要内容加载
        page.wait_for_selector("main", timeout=30000)

        # 等待模型卡片区域加载（通常包含模型名称和描述）
        page.wait_for_selector("h1, h2, h3, h4", timeout=10000)

        # 额外等待确保所有图片加载完成
        page.wait_for_timeout(2000)

        # 尝试找到模型卡片区域（通常是包含模型名称的第一个主要区域）
        # 先尝试找 header 区域
        header_locator = page.locator("header").first
        if header_locator.is_visible():
            header_locator.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            header_locator.screenshot(path=str(image_path), type="png")
        else:
            # 如果找不到 header，截取整个页面顶部区域（包含模型信息）
            page.screenshot(path=str(image_path), type="png", full_page=False)

    finally:
        page.close()


def extract_page_description(model_page) -> str:
    page_data = model_page.evaluate(
        """() => {
          const selectors = ["article p", "main .prose p", "main p"];
          const paragraphs = [];

          for (const selector of selectors) {
            for (const element of document.querySelectorAll(selector)) {
              const text = (element.textContent || "").replace(/\\s+/g, " ").trim();
              if (text) paragraphs.push(text);
            }
          }

          const metaDescription =
            document.querySelector('meta[property="og:description"]')?.getAttribute("content") ||
            document.querySelector('meta[name="description"]')?.getAttribute("content") ||
            "";

          return { paragraphs, metaDescription };
        }"""
    )
    return pick_description([*page_data["paragraphs"], page_data["metaDescription"]])


def enrich_model(browser_context, session: requests.Session, card: dict, index: int) -> dict:
    page = browser_context.new_page()
    try:
        page.goto(card["href"], wait_until="domcontentloaded", timeout=120000)
        page.wait_for_selector("main", timeout=30000)

        model_path = card["path"].lstrip("/")
        description = fetch_readme_description(session, model_path)
        if not description:
            description = extract_page_description(page)

        return {
            "rank": index + 1,
            "recordDate": RUN_STAMP,
            "modelCard": card["image_path"].relative_to(ROOT_DIR).as_posix(),
            "modelName": card["name"],
            "modelDescription": "",
            "sourceDescription": description or "No description available.",
            "modelUrl": card["href"],
            "cardSummary": card["cardText"],
        }
    finally:
        page.close()


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_daily_record(models: list[dict]) -> None:
    payload = {
        "recordDate": RUN_STAMP,
        "source": TRENDING_URL,
        "limit": MODEL_LIMIT,
        "models": models,
    }
    write_json(DAILY_OUTPUT_FILE, payload)
    print(f"Saved daily record to {DAILY_OUTPUT_FILE}")


def should_generate_weekly() -> bool:
    return RUN_DATE.weekday() == 0 or os.environ.get("FORCE_WEEKLY_SUMMARY", "").lower() == "true"


def load_recent_daily_records(days: int = 7) -> list[dict]:
    records = []
    for offset in range(days):
        target_date = RUN_DATE - timedelta(days=offset)
        target_file = DAILY_DIR / f"{target_date.strftime('%Y-%m-%d')}.json"
        if not target_file.exists():
            continue
        try:
            records.append(json.loads(target_file.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            print(f"Skip invalid daily record {target_file}: {exc}")
    return records


def build_weekly_candidates(records: list[dict]) -> list[dict]:
    by_name = {}
    for record in records:
        record_date = record.get("recordDate", "")
        for model in record.get("models", []):
            name = model.get("modelName")
            if not name:
                continue
            item = by_name.setdefault(
                name,
                {
                    "modelName": name,
                    "modelUrl": model.get("modelUrl", ""),
                    "latestModelCard": model.get("modelCard", ""),
                    "latestDescription": model.get("modelDescription", ""),
                    "latestSourceDescription": model.get("sourceDescription", ""),
                    "latestCardSummary": model.get("cardSummary", ""),
                    "bestRank": model.get("rank", 999),
                    "appearances": 0,
                    "dates": [],
                },
            )
            item["appearances"] += 1
            if record_date and record_date not in item["dates"]:
                item["dates"].append(record_date)
            rank = model.get("rank", 999)
            if isinstance(rank, int) and rank < item["bestRank"]:
                item["bestRank"] = rank
            if record_date >= max(item["dates"], default=""):
                item["latestModelCard"] = model.get("modelCard", item["latestModelCard"])
                item["latestDescription"] = model.get("modelDescription", item["latestDescription"])
                item["latestSourceDescription"] = model.get("sourceDescription", item["latestSourceDescription"])
                item["latestCardSummary"] = model.get("cardSummary", item["latestCardSummary"])
                item["modelUrl"] = model.get("modelUrl", item["modelUrl"])

    candidates = list(by_name.values())
    candidates.sort(key=lambda item: (-item["appearances"], item["bestRank"], item["modelName"].lower()))
    return candidates[:20]


def generate_weekly_selection(session: requests.Session, records: list[dict]) -> dict | None:
    candidates = build_weekly_candidates(records)
    if not candidates:
        return None

    weekly_end = RUN_DATE
    weekly_start = RUN_DATE - timedelta(days=6)
    prompt = (
        "You are an AI editor preparing a weekly Chinese roundup of trending Hugging Face models. "
        "Select the most worth-sharing models from the last 7 days. "
        "Prioritize repeat appearances, strong ranking, meaningful capability differences, and shareability. "
        f"Select exactly {WEEKLY_PICK_LIMIT} models if possible. "
        "Write all returned text in Simplified Chinese. "
        "Each `pick_reason` should be 50 to 100 Chinese characters. "
        "Return JSON only, using this format: "
        '{"week_title":"...","summary":"...","items":[{"model_name":"...","pick_reason":"..."}]}'
        "\nCandidates:\n"
        f"{json.dumps(candidates, ensure_ascii=False)}"
    )

    result = call_gemini_json(session, prompt)
    selected = []
    candidate_map = {item["modelName"]: item for item in candidates}
    for item in result.get("items", []):
        name = item.get("model_name")
        if name not in candidate_map:
            continue
        candidate = candidate_map[name]
        selected.append(
            {
                "modelName": name,
                "modelUrl": candidate["modelUrl"],
                "modelCard": candidate["latestModelCard"],
                "modelDescription": candidate["latestDescription"] or candidate["latestSourceDescription"],
                "pickReason": cleanup_text(item.get("pick_reason", "")),
                "appearances": candidate["appearances"],
                "bestRank": candidate["bestRank"],
                "dates": candidate["dates"],
            }
        )

    if not selected:
        return None

    return {
        "weekRange": {
            "start": weekly_start.strftime("%Y-%m-%d"),
            "end": weekly_end.strftime("%Y-%m-%d"),
        },
        "weekTitle": cleanup_text(result.get("week_title", "Weekly Hugging Face Picks")),
        "summary": cleanup_text(result.get("summary", "Weekly selection based on the last 7 days of trending models.")),
        "items": selected[:WEEKLY_PICK_LIMIT],
    }


def save_weekly_record(session: requests.Session) -> None:
    records = load_recent_daily_records(days=7)
    weekly_payload = generate_weekly_selection(session, records)
    if not weekly_payload:
        print("No weekly selection generated.")
        return

    week_file = WEEK_DIR / f"{RUN_STAMP}.json"
    write_json(week_file, weekly_payload)
    print(f"Saved weekly selection to {week_file}")


def main() -> None:
    ensure_dirs()
    require_gemini_api_key()
    session = build_session()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 3840, "height": 2160},  # 4K分辨率
            user_agent=USER_AGENT,
            device_scale_factor=2,
        )

        try:
            page = context.new_page()
            cards = scrape_trending_cards(page)

            captured_cards = []
            for index, card in enumerate(cards, start=1):
                file_name = f"{index:02d}-{slugify(card['name'])}.png"
                image_path = RUN_IMAGE_DIR / file_name

                # 在4K分辨率下重新加载页面并截图，确保图片清晰
                print(f"Capturing screenshot for {card['name']}...")
                capture_card_screenshot_4k(context, card, image_path)

                card["image_path"] = image_path
                captured_cards.append(card)
                print(f"Saved: {image_path.name}")

            models = []
            for index, card in enumerate(captured_cards):
                try:
                    model = enrich_model(context, session, card, index)
                    models.append(model)
                    print(f"Collected {model['modelName']}")
                except PlaywrightTimeoutError as exc:
                    print(f"Timed out collecting {card['name']}: {exc}")

            models = summarize_models_in_chinese(session, models)
            save_daily_record(models)
            if should_generate_weekly():
                save_weekly_record(session)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
