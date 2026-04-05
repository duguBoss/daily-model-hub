import json

import requests

from config import GEMINI_API_URL, MODEL_LIMIT, WEEKLY_PICK_LIMIT, RUN_DATE, RUN_STAMP
from utils import chunk_list, cleanup_text, parse_json_response
from datetime import timedelta


def build_session(user_agent: str) -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": user_agent})
    return session


def call_gemini_json(session: requests.Session, prompt: str) -> dict:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    response = session.post(GEMINI_API_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return parse_json_response(text)


def summarize_models_in_chinese(session: requests.Session, models: list[dict]) -> list[dict]:
    if not models:
        return models

    summary_map = {}

    for batch in chunk_list(list(enumerate(models)), 8):
        payload = [
            {
                "index": index,
                "model_name": model["modelName"],
                "source_description": model["sourceDescription"],
                "card_summary": model["cardSummary"],
                "model_url": model["modelUrl"],
            }
            for index, model in batch
        ]

        prompt = (
            "You are an AI editor writing for a Chinese audience. "
            "For each model in the input, write one concise and accurate summary in Simplified Chinese. "
            "Do not invent facts. Do not use marketing language. "
            "Keep the original index for each item. "
            "Each `model_description` must be 70 to 140 Chinese characters and explain the model's positioning, capabilities, and likely use cases. "
            "Return JSON only, using this format: "
            '{"items":[{"index":0,"model_description":"..."}]}'
            "\nInput:\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )

        result = call_gemini_json(session, prompt)
        for item in result.get("items", []):
            index = item.get("index")
            description = cleanup_text(item.get("model_description", ""))
            if isinstance(index, int) and description:
                summary_map[index] = description

    for index, model in enumerate(models):
        fallback = cleanup_text(model.get("sourceDescription", "")) or "No description available."
        model["modelDescription"] = summary_map.get(index, fallback)

    return models


def generate_weekly_selection(session: requests.Session, candidates: list[dict]) -> dict | None:
    if not candidates:
        return None

    weekly_end = RUN_DATE
    weekly_start = RUN_DATE - timedelta(days=6)
    prompt = (
        "You are an AI editor preparing a weekly Chinese roundup of trending Hugging Face models. "
        "Select the most worth-sharing models from the last 7 days. "
        "Prioritize repeat appearances, strong ranking, meaningful capability differences, and shareability. "
        f"Select exactly {WEEKLY_PICK_LIMIT} models if possible. "
        "Write all returned text in Simplified Chinese. "
        "Each `pick_reason` should be 50 to 100 Chinese characters. "
        "Return JSON only, using this format: "
        '{"week_title":"...","summary":"...","items":[{"model_name":"...","pick_reason":"..."}]}'
        "\nCandidates:\n"
        f"{json.dumps(candidates, ensure_ascii=False)}"
    )

    result = call_gemini_json(session, prompt)
    selected = []
    candidate_map = {item["modelName"]: item for item in candidates}
    for item in result.get("items", []):
        name = item.get("model_name")
        if name not in candidate_map:
            continue
        candidate = candidate_map[name]
        selected.append(
            {
                "modelName": name,
                "modelUrl": candidate["modelUrl"],
                "modelCard": candidate["latestModelCard"],
                "modelDescription": candidate["latestDescription"] or candidate["latestSourceDescription"],
                "pickReason": cleanup_text(item.get("pick_reason", "")),
                "appearances": candidate["appearances"],
                "bestRank": candidate["bestRank"],
                "dates": candidate["dates"],
            }
        )

    if not selected:
        return None

    return {
        "weekRange": {
            "start": weekly_start.strftime("%Y-%m-%d"),
            "end": weekly_end.strftime("%Y-%m-%d"),
        },
        "weekTitle": cleanup_text(result.get("week_title", "Weekly Hugging Face Picks")),
        "summary": cleanup_text(result.get("summary", "Weekly selection based on the last 7 days of trending models.")),
        "items": selected[:WEEKLY_PICK_LIMIT],
    }
