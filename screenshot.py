from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import RUN_IMAGE_DIR, MODEL_LIMIT
from utils import slugify


def capture_trending_screenshots(page) -> list[dict]:
    """在 Trending 页面直接截取前5个模型卡片.

    不需要点击进入每个模型详情页，直接在列表页面截图。
    """
    captured_cards = []

    # 等待列表加载完成
    page.wait_for_selector("main", timeout=30000)
    page.wait_for_timeout(3000)

    # 获取前5个模型卡片的元素句柄
    cards_data = page.evaluate(
        """(limit) => {
          const cards = [];
          // HF Trending 页面的模型卡片选择器
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
          for (const anchor of anchors) {
            const href = anchor.getAttribute("href") || "";
            const pathname = href.split("?")[0];
            if (!pathname.startsWith("/") || seen.has(pathname)) continue;

            const segments = pathname.split("/").filter(Boolean);
            if (segments.length < 1 || segments.length > 2) continue;

            seen.add(pathname);

            // 获取元素的位置信息用于截图
            const rect = anchor.getBoundingClientRect();
            cards.push({
              path: pathname,
              name: segments.join("/"),
              x: rect.x,
              y: rect.y,
              width: rect.width,
              height: rect.height
            });

            if (cards.length >= limit) break;
          }
          return cards;
        }""",
        MODEL_LIMIT
    )

    if not cards_data:
        raise RuntimeError("No model cards found on trending page for screenshot.")

    # 为每个卡片截图
    for index, card_info in enumerate(cards_data, start=1):
        file_name = f"{index:02d}-{slugify(card_info['name'])}.png"
        image_path = RUN_IMAGE_DIR / file_name

        print(f"Capturing screenshot for {card_info['name']}...")

        try:
            # 滚动到元素位置
            page.evaluate(f"window.scrollTo(0, {card_info['y'] - 100})")
            page.wait_for_timeout(500)

            # 截图指定区域
            page.screenshot(
                path=str(image_path),
                type="png",
                clip={
                    "x": card_info['x'],
                    "y": card_info['y'],
                    "width": card_info['width'],
                    "height": card_info['height']
                }
            )

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
