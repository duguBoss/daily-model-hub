from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import RUN_IMAGE_DIR, MODEL_LIMIT
from utils import slugify


def capture_card_screenshot_4k(context, card: dict, image_path: Path) -> None:
    """在4K分辨率下打开模型页面并截图模型卡片.

    根据XPath /html/body/div/main/div/div/section[2]/div[2]/div/article
    定位到模型卡片区域并截图.
    """
    page = context.new_page()
    try:
        page.goto(card["href"], wait_until="networkidle", timeout=60000)

        # 等待主内容加载
        page.wait_for_selector("main", timeout=30000)
        page.wait_for_timeout(2000)

        # 尝试多种选择器定位模型卡片
        # 优先使用 article 标签（对应 XPath 中的 article）
        card_selectors = [
            "main article",  # main 下的 article
            "article",  # 任意 article
            "[data-target='ModelCard']",  # HF 特定的 model card 属性
            ".model-card",  # 可能的 class
            "main .container article",  # 更具体的路径
        ]

        card_element = None
        for selector in card_selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=3000):
                    card_element = locator
                    print(f"Found card element with selector: {selector}")
                    break
            except Exception:
                continue

        if card_element:
            # 滚动到视图中并截图
            card_element.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            card_element.screenshot(path=str(image_path), type="png")
        else:
            # 兜底：尝试使用 XPath 定位
            try:
                xpath_locator = page.locator("xpath=/html/body/div/main/div/div/section[2]/div[2]/div/article")
                if xpath_locator.is_visible(timeout=5000):
                    xpath_locator.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)
                    xpath_locator.screenshot(path=str(image_path), type="png")
                    print(f"Found card element with XPath")
                else:
                    # 最后兜底：截图整个页面顶部区域
                    page.screenshot(path=str(image_path), type="png", full_page=False)
                    print(f"Warning: Using full page screenshot for {card['name']}")
            except Exception as e:
                page.screenshot(path=str(image_path), type="png", full_page=False)
                print(f"Error with XPath, using full page: {e}")

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
