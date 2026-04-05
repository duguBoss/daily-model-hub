from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import RUN_IMAGE_DIR, MODEL_LIMIT
from utils import slugify


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
        page.goto(card["href"], wait_until="networkidle", timeout=60000)

        page.wait_for_selector("main", timeout=30000)

        page.wait_for_selector("h1, h2, h3, h4", timeout=10000)

        page.wait_for_timeout(2000)

        header_locator = page.locator("header").first
        if header_locator.is_visible():
            header_locator.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            header_locator.screenshot(path=str(image_path), type="png")
        else:
            page.screenshot(path=str(image_path), type="png", full_page=False)

    finally:
        page.close()


def capture_all_screenshots(context, cards: list[dict]) -> list[dict]:
    """为所有卡片截图并返回更新后的卡片列表."""
    captured_cards = []
    for index, card in enumerate(cards, start=1):
        file_name = f"{index:02d}-{slugify(card['name'])}.png"
        image_path = RUN_IMAGE_DIR / file_name

        print(f"Capturing screenshot for {card['name']}...")
        capture_card_screenshot_4k(context, card, image_path)

        card["image_path"] = image_path
        captured_cards.append(card)
        print(f"Saved: {image_path.name}")

    return captured_cards
