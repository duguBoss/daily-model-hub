import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT_DIR = Path(__file__).resolve().parent
TRENDING_URL = "https://huggingface.co/models?sort=trending"
OUTPUT_FILE = ROOT_DIR / "data" / "weekly_hf_models.json"
IMAGE_ROOT_DIR = ROOT_DIR / "assets" / "huggingface_model_cards"
RUN_STAMP = datetime.utcnow().strftime("%Y-%m-%d")
RUN_IMAGE_DIR = IMAGE_ROOT_DIR / RUN_STAMP
MODEL_LIMIT = int(os.environ.get("HF_MODEL_LIMIT", "10") or "10")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)


def normalize_limit(value: int, fallback: int = 10) -> int:
    return value if value > 0 else fallback


MODEL_LIMIT = normalize_limit(MODEL_LIMIT)


def ensure_dirs() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUN_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


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


def build_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": USER_AGENT})
    return session


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
    locator = page.locator(f'a[href="{model_path}"]').filter(has=page.locator("h4")).first
    locator.scroll_into_view_if_needed()
    locator.screenshot(path=str(image_path))


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
            "modelCard": card["image_path"].relative_to(ROOT_DIR).as_posix(),
            "modelName": card["name"],
            "modelDescription": description or "No description available.",
            "modelUrl": card["href"],
            "cardSummary": card["cardText"],
        }
    finally:
        page.close()


def main() -> None:
    ensure_dirs()
    session = build_session()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1600, "height": 2400},
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
                capture_card_screenshot(page, card["path"], image_path)
                card["image_path"] = image_path
                captured_cards.append(card)

            models = []
            for index, card in enumerate(captured_cards):
                try:
                    model = enrich_model(context, session, card, index)
                    models.append(model)
                    print(f"Collected {model['modelName']}")
                except PlaywrightTimeoutError as exc:
                    print(f"Timed out collecting {card['name']}: {exc}")

            OUTPUT_FILE.write_text(
                json.dumps(models, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Saved {len(models)} models to {OUTPUT_FILE}")
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
