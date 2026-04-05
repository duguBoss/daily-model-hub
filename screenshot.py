from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import RUN_IMAGE_DIR, MODEL_LIMIT
from utils import slugify


def capture_trending_screenshots(page) -> list[dict]:
    """在 Trending 页面直接截取前5个模型卡片.

    一次性获取元素句柄并截图，避免多次查询导致的遮挡问题。
    """
    captured_cards = []

    # 等待列表加载完成
    page.wait_for_selector("main", timeout=30000)
    page.wait_for_timeout(3000)

    # 一次性获取所有模型卡片的元素句柄和数据
    cards_info = page.evaluate(
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
              x: Math.max(0, rect.x),
              y: Math.max(0, rect.y),
              width: rect.width,
              height: rect.height
            });

            if (cards.length >= limit) break;
          }
          return cards;
        }""",
        MODEL_LIMIT
    )

    if not cards_info:
        raise RuntimeError("No model cards found on trending page for screenshot.")

    print(f"Found {len(cards_info)} model cards to capture")

    # 一次性截图所有卡片，不进行滚动操作
    for index, card_info in enumerate(cards_info, start=1):
        file_name = f"{index:02d}-{slugify(card_info['name'])}.png"
        image_path = RUN_IMAGE_DIR / file_name

        print(f"Capturing screenshot for {card_info['name']} at ({card_info['x']}, {card_info['y']})...")

        try:
            # 直接截图指定区域，不滚动
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
