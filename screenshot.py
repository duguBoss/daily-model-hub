from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from PIL import Image

from config import RUN_IMAGE_DIR, MODEL_LIMIT
from utils import slugify


def capture_trending_screenshots(page) -> list[dict]:
    """在 Trending 页面直接截取前5个模型卡片.

    一次性获取所有元素坐标，整页截图后裁剪，避免多次滚动导致的遮挡问题。
    """
    captured_cards = []

    # 等待列表加载完成
    page.wait_for_selector("main", timeout=30000)
    page.wait_for_timeout(5000)  # 确保页面完全渲染

    # 一次性获取所有模型卡片的坐标信息
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

            // 获取元素的精确坐标
            const rect = anchor.getBoundingClientRect();
            // 获取视口滚动位置
            const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
            const scrollY = window.pageYOffset || document.documentElement.scrollTop;

            cards.push({
              index: index,
              path: pathname,
              name: segments.join("/"),
              // 计算相对于文档的绝对坐标
              left: Math.round(rect.left + scrollX),
              top: Math.round(rect.top + scrollY),
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

    # 计算整页截图的范围
    max_bottom = max(card['top'] + card['height'] for card in cards_data)
    page_width = page.evaluate("() => Math.max(document.body.scrollWidth, document.documentElement.scrollWidth, document.body.offsetWidth, document.documentElement.offsetWidth, document.body.clientWidth, document.documentElement.clientWidth)")

    # 整页截图
    full_page_path = RUN_IMAGE_DIR / "_temp_full_page.png"
    print(f"Capturing full page screenshot (width={page_width}, height={max_bottom})...")

    try:
        page.screenshot(
            path=str(full_page_path),
            type="png",
            full_page=True
        )

        # 打开整页截图并裁剪每个卡片
        with Image.open(full_page_path) as full_img:
            for card_info in cards_data:
                file_name = f"{card_info['index']:02d}-{slugify(card_info['name'])}.png"
                image_path = RUN_IMAGE_DIR / file_name

                print(f"Cropping {card_info['name']} from ({card_info['left']}, {card_info['top']}, {card_info['width']}, {card_info['height']})...")

                # 裁剪区域
                left = card_info['left']
                top = card_info['top']
                right = left + card_info['width']
                bottom = top + card_info['height']

                # 确保裁剪区域在图片范围内
                img_width, img_height = full_img.size
                left = max(0, min(left, img_width))
                top = max(0, min(top, img_height))
                right = max(0, min(right, img_width))
                bottom = max(0, min(bottom, img_height))

                if right > left and bottom > top:
                    card_img = full_img.crop((left, top, right, bottom))
                    card_img.save(image_path, "PNG")

                    captured_cards.append({
                        "name": card_info['name'],
                        "path": card_info['path'],
                        "href": f"https://huggingface.co{card_info['path']}",
                        "image_path": image_path
                    })
                    print(f"Saved: {image_path.name}")
                else:
                    print(f"Invalid crop region for {card_info['name']}")

        # 删除临时整页截图
        full_page_path.unlink(missing_ok=True)

    except Exception as e:
        print(f"Full page screenshot failed: {e}")
        # 兜底：逐个元素截图
        return _fallback_element_screenshot(page, cards_data)

    return captured_cards


def _fallback_element_screenshot(page, cards_data: list) -> list[dict]:
    """兜底方案：逐个元素截图."""
    captured_cards = []

    for card_info in cards_data:
        file_name = f"{card_info['index']:02d}-{slugify(card_info['name'])}.png"
        image_path = RUN_IMAGE_DIR / file_name

        try:
            xpath = f"xpath=/html/body/div/main/div/div/section[2]/div[2]/div/article[{card_info['index']}]"
            element = page.locator(xpath).first
            element.wait_for(state="visible", timeout=10000)
            element.screenshot(path=str(image_path), type="png")

            captured_cards.append({
                "name": card_info['name'],
                "path": card_info['path'],
                "href": f"https://huggingface.co{card_info['path']}",
                "image_path": image_path
            })
            print(f"Saved (fallback): {image_path.name}")
        except Exception as e:
            print(f"Fallback failed for {card_info['name']}: {e}")

    return captured_cards
