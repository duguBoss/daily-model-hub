import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from config import DAILY_DIR, WEEK_DIR, DAILY_OUTPUT_FILE, RUN_DATE, RUN_STAMP, TRENDING_URL, MODEL_LIMIT
from utils import write_json


def should_generate_weekly() -> bool:
    return RUN_DATE.weekday() == 0 or os.environ.get("FORCE_WEEKLY_SUMMARY", "").lower() == "true"


def load_recent_daily_records(days: int = 7) -> list[dict]:
    records = []
    for offset in range(days):
        target_date = RUN_DATE - timedelta(days=offset)
        target_file = DAILY_DIR / f"{target_date.strftime('%Y-%m-%d')}.json"
        if not target_file.exists():
            continue
        try:
            records.append(json.loads(target_file.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            print(f"Skip invalid daily record {target_file}: {exc}")
    return records


def build_weekly_candidates(records: list[dict]) -> list[dict]:
    by_name = {}
    for record in records:
        record_date = record.get("recordDate", "")
        for model in record.get("models", []):
            name = model.get("modelName")
            if not name:
                continue
            item = by_name.setdefault(
                name,
                {
                    "modelName": name,
                    "modelUrl": model.get("modelUrl", ""),
                    "latestModelCard": model.get("modelCard", ""),
                    "latestDescription": model.get("modelDescription", ""),
                    "latestSourceDescription": model.get("sourceDescription", ""),
                    "latestCardSummary": model.get("cardSummary", ""),
                    "bestRank": model.get("rank", 999),
                    "appearances": 0,
                    "dates": [],
                },
            )
            item["appearances"] += 1
            if record_date and record_date not in item["dates"]:
                item["dates"].append(record_date)
            rank = model.get("rank", 999)
            if isinstance(rank, int) and rank < item["bestRank"]:
                item["bestRank"] = rank
            if record_date >= max(item["dates"], default=""):
                item["latestModelCard"] = model.get("modelCard", item["latestModelCard"])
                item["latestDescription"] = model.get("modelDescription", item["latestDescription"])
                item["latestSourceDescription"] = model.get("sourceDescription", item["latestSourceDescription"])
                item["latestCardSummary"] = model.get("cardSummary", item["latestCardSummary"])
                item["modelUrl"] = model.get("modelUrl", item["modelUrl"])

    candidates = list(by_name.values())
    candidates.sort(key=lambda item: (-item["appearances"], item["bestRank"], item["modelName"].lower()))
    return candidates[:20]


def save_daily_record(models: list[dict]) -> None:
    payload = {
        "recordDate": RUN_STAMP,
        "source": TRENDING_URL,
        "limit": MODEL_LIMIT,
        "models": models,
    }
    write_json(DAILY_OUTPUT_FILE, payload)
    print(f"Saved daily record to {DAILY_OUTPUT_FILE}")


def save_weekly_record(weekly_payload: dict | None) -> None:
    if not weekly_payload:
        print("No weekly selection generated.")
        return

    week_file = WEEK_DIR / f"{RUN_STAMP}.json"
    write_json(week_file, weekly_payload)
    print(f"Saved weekly selection to {week_file}")
