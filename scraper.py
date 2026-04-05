from pathlib import Path

import requests

from config import TRENDING_URL, MODEL_LIMIT, RUN_STAMP, ROOT_DIR
from utils import extract_intro_from_markdown, pick_description


def fetch_readme_description(session: requests.Session, model_path: str) -> str:
    urls = [
        f"https://huggingface.co/{model_path}/resolve/main/README.md",
        f"https://huggingface.co/{model_path}/raw/main/README.md",
    ]

    for url in urls:
        try:
            response = session.get(url, timeout=30)
            if not response.ok:
                continue
            intro = extract_intro_from_markdown(response.text)
            if intro:
                return intro
        except requests.RequestException as exc:
            print(f"Failed to fetch README for {model_path}: {exc}")
    return ""


def scrape_trending_cards(page) -> list[dict]:
    page.goto(TRENDING_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_selector("main", timeout=30000)
    page.wait_for_timeout(3000)

    cards = page.evaluate(
        """(limit) => {
          const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
          const selectorCandidates = [
            "a.flex.items-center.justify-between.gap-4.p-2[href^='/']",
            "main a[href^='/']"
          ];
          const anchorGroups = selectorCandidates
            .map((selector) => Array.from(document.querySelectorAll(selector)))
            .filter((group) => group.length > 0);
          const anchors = anchorGroups[0] || [];
          const seen = new Set();
          const rows = [];

          for (const anchor of anchors) {
            const href = anchor.getAttribute("href") || "";
            const heading = anchor.querySelector("h4");
            if (!heading || !href.startsWith("/")) continue;

            const pathname = href.split("?")[0];
            const segments = pathname.split("/").filter(Boolean);
            if (segments.length < 1 || segments.length > 2) continue;
            if (seen.has(pathname)) continue;

            seen.add(pathname);
            rows.push({
              name: normalize(heading.textContent),
              href: new URL(pathname, location.origin).toString(),
              path: pathname,
              cardText: normalize(anchor.textContent)
            });

            if (rows.length >= limit) break;
          }

          return rows;
        }""",
        MODEL_LIMIT,
    )

    if not cards:
        raise RuntimeError("No model cards were found on the trending page.")

    return cards


def extract_page_description(model_page) -> str:
    page_data = model_page.evaluate(
        """() => {
          const selectors = ["article p", "main .prose p", "main p"];
          const paragraphs = [];

          for (const selector of selectors) {
            for (const element of document.querySelectorAll(selector)) {
              const text = (element.textContent || "").replace(/\\s+/g, " ").trim();
              if (text) paragraphs.push(text);
            }
          }

          const metaDescription =
            document.querySelector('meta[property="og:description"]')?.getAttribute("content") ||
            document.querySelector('meta[name="description"]')?.getAttribute("content") ||
            "";

          return { paragraphs, metaDescription };
        }"""
    )
    return pick_description([*page_data["paragraphs"], page_data["metaDescription"]])


def enrich_model(browser_context, session: requests.Session, card: dict, index: int) -> dict:
    page = browser_context.new_page()
    try:
        page.goto(card["href"], wait_until="domcontentloaded", timeout=120000)
        page.wait_for_selector("main", timeout=30000)

        model_path = card["path"].lstrip("/")
        description = fetch_readme_description(session, model_path)
        if not description:
            description = extract_page_description(page)

        return {
            "rank": index + 1,
            "recordDate": RUN_STAMP,
            "modelCard": card["image_path"].relative_to(ROOT_DIR).as_posix(),
            "modelName": card["name"],
            "modelDescription": "",
            "sourceDescription": description or "No description available.",
            "modelUrl": card["href"],
            "cardSummary": "",
        }
    finally:
        page.close()
