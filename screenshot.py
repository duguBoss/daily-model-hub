from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import RUN_IMAGE_DIR, MODEL_LIMIT
from utils import slugify


def capture_trending_screenshots(page) -> list[dict]:
    """在 Trending 页面直接截取前5个模型卡片.

    页面加载完成后，使用 XPath 一次性获取5个元素并分别截图，无需重新加载页面。
    """
    captured_cards = []

    # 等待列表加载完成
    page.wait_for_selector("main", timeout=30000)
    page.wait_for_timeout(5000)  # 确保页面完全渲染

    # 获取前5个模型卡片的名称和序号
    cards_meta = page.evaluate(
        """(limit) => {
          const cards = [];
          const selectors = [
            "a.flex.items-center.justify-between.gap-4.p-2[href^='/']",
            "main .grid > a[href^='/']",
            "main a[href^='/']:has(h4)"
          ];

          let anchors = [];
          for (const selector of selectors) {
            anchors = document.querySelectorAll(selector);
            if (anchors.length > 0) break;
          }

          const seen = new Set();
          let index = 0;
          for (const anchor of anchors) {
            const href = anchor.getAttribute("href") || "";
            const pathname = href.split("?")[0];
            if (!pathname.startsWith("/") || seen.has(pathname)) continue;

            const segments = pathname.split("/").filter(Boolean);
            if (segments.length < 1 || segments.length > 2) continue;

            seen.add(pathname);
            index++;

            cards.push({
              index: index,
              path: pathname,
              name: segments.join("/")
            });

            if (cards.length >= limit) break;
          }
          return cards;
        }""",
        MODEL_LIMIT
    )

    if not cards_meta:
        raise RuntimeError("No model cards found on trending page for screenshot.")

    print(f"Found {len(cards_meta)} model cards to capture")

    # 页面已加载，直接用 XPath 获取每个元素并截图
    for card_info in cards_meta:
        file_name = f"{card_info['index']:02d}-{slugify(card_info['name'])}.png"
        image_path = RUN_IMAGE_DIR / file_name

        print(f"Capturing screenshot for {card_info['name']}...")

        try:
            # 使用 XPath 定位第 N 个模型卡片
            # HF Trending 页面结构: /html/body/div/main/div/div/section[2]/div[2]/div/article[n]
            xpath = f"xpath=/html/body/div/main/div/div/section[2]/div[2]/div/article[{card_info['index']}]"

            # 定位元素
            element = page.locator(xpath).first

            # 等待元素存在（不需要滚动，不需要重新加载）
            element.wait_for(state="attached", timeout=10000)

            # 直接截图元素
            element.screenshot(path=str(image_path), type="png")

            captured_cards.append({
                "name": card_info['name'],
                "path": card_info['path'],
                "href": f"https://huggingface.co{card_info['path']}",
                "image_path": image_path
            })
            print(f"Saved: {image_path.name}")

        except Exception as e:
            print(f"Failed to capture screenshot for {card_info['name']}: {e}")
            continue

    return captured_cards
