from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import ensure_dirs, require_gemini_api_key, USER_AGENT, MODEL_LIMIT
from gemini_client import build_session, summarize_models_in_chinese, generate_weekly_selection
from scraper import scrape_trending_cards, enrich_model
from screenshot import capture_all_screenshots
from data_manager import (
    should_generate_weekly,
    load_recent_daily_records,
    build_weekly_candidates,
    save_daily_record,
    save_weekly_record,
)


def main() -> None:
    ensure_dirs()
    require_gemini_api_key()
    session = build_session(USER_AGENT)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 3840, "height": 2160},
            user_agent=USER_AGENT,
            device_scale_factor=2,
        )

        try:
            page = context.new_page()
            cards = scrape_trending_cards(page)

            captured_cards = capture_all_screenshots(context, cards)

            models = []
            for index, card in enumerate(captured_cards):
                try:
                    model = enrich_model(context, session, card, index)
                    models.append(model)
                    print(f"Collected {model['modelName']}")
                except PlaywrightTimeoutError as exc:
                    print(f"Timed out collecting {card['name']}: {exc}")

            models = summarize_models_in_chinese(session, models)
            save_daily_record(models)

            if should_generate_weekly():
                records = load_recent_daily_records(days=7)
                candidates = build_weekly_candidates(records)
                weekly_payload = generate_weekly_selection(session, candidates)
                save_weekly_record(weekly_payload)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
