from pathlib import Path

import requests

from config import MODEL_LIMIT, RUN_STAMP
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


def scrape_trending_cards(session: requests.Session) -> list[dict]:
    response = session.get("https://huggingface.co/models-json?sort=trending&withCount=true", timeout=60)
    response.raise_for_status()
    payload = response.json()
    models = payload.get("models", [])

    cards = []
    for model in models:
        model_id = model.get("id", "")
        if not model_id:
            continue

        path = f"/{model_id}"
        cards.append(
            {
                "name": model_id,
                "href": f"https://huggingface.co{path}",
                "path": path,
                "author": model.get("author", ""),
                "downloads": model.get("downloads", 0),
                "likes": model.get("likes", 0),
                "pipelineTag": model.get("pipeline_tag", ""),
                "lastModified": model.get("lastModified", ""),
                "numParameters": model.get("numParameters"),
                "availableInferenceProviders": model.get("availableInferenceProviders", []),
            }
        )
        if len(cards) >= MODEL_LIMIT:
            break

    if not cards:
        raise RuntimeError("No model cards were returned by the trending models API.")

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
            "modelCard": card.get("modelCard", ""),
            "modelName": card["name"],
            "modelDescription": "",
            "sourceDescription": description or "No description available.",
            "modelUrl": card["href"],
            "cardSummary": "",
            "author": card.get("author", ""),
            "downloads": card.get("downloads", 0),
            "likes": card.get("likes", 0),
            "pipelineTag": card.get("pipelineTag", ""),
            "lastModified": card.get("lastModified", ""),
            "numParameters": card.get("numParameters"),
            "availableInferenceProviders": card.get("availableInferenceProviders", []),
        }
    finally:
        page.close()
