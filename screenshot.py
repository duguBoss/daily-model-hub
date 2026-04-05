from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import RUN_IMAGE_DIR, MODEL_LIMIT
from utils import slugify


def capture_trending_screenshots(page) -> list[dict]:
    """在 Trending 页面直接截取前5个模型卡片.

    页面加载完成后，一次性获取5个元素的坐标，然后使用 clip 截图。
    """
    captured_cards = []

    # 等待列表加载完成
    page.wait_for_selector("main", timeout=30000)
    page.wait_for_timeout(5000)  # 确保页面完全渲染

    # 一次性获取所有模型卡片的坐标（相对于视口）
    cards_data = page.evaluate(
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

            // 获取元素相对于视口的坐标
            const rect = anchor.getBoundingClientRect();
            cards.push({
              index: index,
              path: pathname,
              name: segments.join("/"),
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              width: Math.round(rect.width),
              height: Math.round(rect.height)
            });

            if (cards.length >= limit) break;
          }
          return cards;
        }""",
        MODEL_LIMIT
    )

    if not cards_data:
        raise RuntimeError("No model cards found on trending page for screenshot.")

    print(f"Found {len(cards_data)} model cards to capture")

    # 按 Y 坐标排序，从顶部开始截图
    cards_data.sort(key=lambda c: c['y'])

    # 逐个截图，使用 clip 方式
    for card_info in cards_data:
        file_name = f"{card_info['index']:02d}-{slugify(card_info['name'])}.png"
        image_path = RUN_IMAGE_DIR / file_name

        print(f"Capturing {card_info['name']} at ({card_info['x']}, {card_info['y']}, {card_info['width']}, {card_info['height']})...")

        try:
            # 滚动到元素位置，确保在视口内
            page.evaluate(f"window.scrollTo(0, {card_info['y'] - 100})")
            page.wait_for_timeout(500)

            # 重新获取坐标（因为滚动后坐标可能变化）
            updated_rect = page.evaluate(
                """(xpath) => {
                    const element = document.evaluate(
                        xpath,
                        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                    ).singleNodeValue;
                    if (element) {
                        const rect = element.getBoundingClientRect();
                        return {
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        };
                    }
                    return null;
                }""",
                f"/html/body/div/main/div/div/section[2]/div[2]/div/article[{card_info['index']}]"
            )

            if updated_rect:
                # 使用 clip 截图
                page.screenshot(
                    path=str(image_path),
                    type="png",
                    clip={
                        "x": updated_rect['x'],
                        "y": updated_rect['y'],
                        "width": updated_rect['width'],
                        "height": updated_rect['height']
                    }
                )

                captured_cards.append({
                    "name": card_info['name'],
                    "path": card_info['path'],
                    "href": f"https://huggingface.co{card_info['path']}",
                    "image_path": image_path
                })
                print(f"Saved: {image_path.name}")
            else:
                print(f"Failed to get updated rect for {card_info['name']}")

        except Exception as e:
            print(f"Failed to capture screenshot for {card_info['name']}: {e}")
            continue

    return captured_cards
