from playwright.sync_api import Page

from config import MODEL_LIMIT, RUN_IMAGE_DIR
from utils import slugify


CARD_SELECTORS = (
    "main .grid a[href^='/']",
    "main a[href^='/']:has(h4)",
)

CARD_HYDRATION_WAIT_MS = 1200
SCROLL_SETTLE_WAIT_MS = 300
PAGE_SETTLE_WAIT_MS = 5000

PAGE_CLEANUP_SCRIPT = """
() => {
  const style = document.createElement('style');
  style.setAttribute('data-hf-screenshot-cleanup', 'true');
  style.textContent = `
    * {
      animation: none !important;
      transition: none !important;
      caret-color: transparent !important;
    }
    [data-testid*="banner"],
    [data-testid*="popover"],
    [data-testid*="tooltip"],
    [role="dialog"],
    [aria-modal="true"],
    .sticky,
    .fixed,
    header,
    nav {
      display: none !important;
    }
  `;
  document.head.appendChild(style);
}
"""


def _prepare_page_for_capture(page: Page) -> None:
    page.wait_for_selector("main", timeout=30000)
    page.wait_for_timeout(PAGE_SETTLE_WAIT_MS)
    page.evaluate(PAGE_CLEANUP_SCRIPT)
    page.wait_for_timeout(CARD_HYDRATION_WAIT_MS)


def _find_card_locators(page: Page):
    for selector in CARD_SELECTORS:
        locator = page.locator(selector)
        if locator.count() > 0:
            return locator
    raise RuntimeError("No model cards found on trending page for screenshot.")


def _collect_cards(page: Page) -> list[dict]:
    locator = _find_card_locators(page)
    cards_data = []
    seen = set()

    total = locator.count()
    for idx in range(total):
        card = locator.nth(idx)
        href = (card.get_attribute("href") or "").split("?")[0]
        if not href.startswith("/") or href in seen:
            continue

        segments = [segment for segment in href.split("/") if segment]
        if not segments or len(segments) > 2:
            continue

        seen.add(href)
        cards_data.append(
            {
                "index": len(cards_data) + 1,
                "path": href,
                "name": "/".join(segments),
                "locator_index": idx,
            }
        )

        if len(cards_data) >= MODEL_LIMIT:
            break

    if not cards_data:
        raise RuntimeError("No valid model cards found on trending page for screenshot.")

    return cards_data


def capture_trending_screenshots(page: Page) -> list[dict]:
    """Capture top trending Hugging Face cards as isolated element screenshots."""
    _prepare_page_for_capture(page)
    card_locator = _find_card_locators(page)
    cards_data = _collect_cards(page)
    captured_cards = []

    print(f"Found {len(cards_data)} model cards to capture")

    for card_info in cards_data:
        file_name = f"{card_info['index']:02d}-{slugify(card_info['name'])}.png"
        image_path = RUN_IMAGE_DIR / file_name
        locator = card_locator.nth(card_info["locator_index"])

        print(f"Capturing {card_info['name']}...")

        try:
            locator.scroll_into_view_if_needed(timeout=30000)
            page.wait_for_timeout(SCROLL_SETTLE_WAIT_MS)

            # Element screenshots avoid neighboring overlays that leak into clip-based captures.
            locator.screenshot(path=str(image_path), type="png")

            captured_cards.append(
                {
                    "name": card_info["name"],
                    "path": card_info["path"],
                    "href": f"https://huggingface.co{card_info['path']}",
                    "image_path": image_path,
                }
            )
            print(f"Saved: {image_path.name}")
        except Exception as exc:
            print(f"Failed to capture screenshot for {card_info['name']}: {exc}")

    return captured_cards
