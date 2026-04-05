from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import RUN_IMAGE_DIR, MODEL_LIMIT
from utils import slugify


def capture_trending_screenshots(page) -> list[dict]:
    """在 Trending 页面直接截取前5个模型卡片.

    使用 Playwright 的元素截图功能，类似 Puppeteer 的 element.screenshot()。
    确保元素完全可见后再截图，避免遮挡和截断问题。
    """
    captured_cards = []

    # 等待列表加载完成
    page.wait_for_selector("main", timeout=30000)
    page.wait_for_timeout(5000)  # 增加等待时间确保页面完全渲染

    # 获取前5个模型卡片的信息（路径和索引）
    cards_meta = page.evaluate(
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

    # 使用 XPath 定位每个元素并截图
    for card_info in cards_meta:
        file_name = f"{card_info['index']:02d}-{slugify(card_info['name'])}.png"
        image_path = RUN_IMAGE_DIR / file_name

        print(f"Capturing screenshot for {card_info['name']}...")

        try:
            # 使用 XPath 定位第 N 个模型卡片
            xpath = f"xpath=/html/body/div/main/div/div/section[2]/div[2]/div/article[{card_info['index']}]"

            # 等待元素可见并滚动到视图中
            element = page.locator(xpath).first
            element.wait_for(state="visible", timeout=10000)
            element.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)  # 等待滚动稳定

            # 确保元素在视口内完全可见
            page.evaluate("""(xpath) => {
                const element = document.evaluate(
                    xpath.replace('xpath=', ''),
                    document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                ).singleNodeValue;
                if (element) {
                    element.scrollIntoView({ behavior: 'instant', block: 'center' });
                }
            }""", xpath)
            page.wait_for_timeout(500)

            # 元素截图
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
            # 兜底：尝试用 CSS 选择器
            try:
                css_selector = f"main > div > div > section:nth-child(2) > div:nth-child(2) > div > article:nth-child({card_info['index']})"
                element = page.locator(css_selector).first
                element.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                element.screenshot(path=str(image_path), type="png")

                captured_cards.append({
                    "name": card_info['name'],
                    "path": card_info['path'],
                    "href": f"https://huggingface.co{card_info['path']}",
                    "image_path": image_path
                })
                print(f"Saved (fallback): {image_path.name}")
            except Exception as e2:
                print(f"Fallback also failed for {card_info['name']}: {e2}")
                continue

    return captured_cards
