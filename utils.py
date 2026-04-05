import json
import re


def slugify(value: str) -> str:
    text = (value or "model").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80] or "model"


def cleanup_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\xa0", " ")).strip()


def markdown_to_text(markdown: str) -> str:
    text = markdown or ""
    text = re.sub(r"^---[\s\S]*?---", " ", text, flags=re.M)
    text = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", text)
    text = re.sub(r"`{1,3}([^`]+)`{1,3}", r"\1", text)
    text = re.sub(r"^>\s?", "", text, flags=re.M)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"[*_~]", " ", text)
    return cleanup_text(text)


def extract_intro_from_markdown(markdown: str) -> str:
    sanitized = re.sub(r"^---[\s\S]*?---\n?", "", markdown or "", flags=re.M)
    paragraphs = [markdown_to_text(block) for block in re.split(r"\n\s*\n", sanitized)]
    blocked_prefixes = ("title ", "language ", "tags ", "tag ", "license ", "datasets ", "dataset ")

    for paragraph in paragraphs:
        if not paragraph:
            continue
        if paragraph.lower().startswith(blocked_prefixes):
            continue
        if len(paragraph) >= 60:
            return paragraph
    return ""


def pick_description(candidates: list[str]) -> str:
    blocked_patterns = [
        r"^updated\b",
        r"^downloads?\b",
        r"^likes?\b",
        r"^license\b",
        r"^files and versions\b",
        r"^model tree\b",
        r"^collections\b",
        r"^spaces using\b",
        r"^inference providers\b",
        r"^this model has no model card\b",
    ]

    for candidate in candidates:
        text = cleanup_text(candidate)
        if len(text) < 40:
            continue
        if any(re.search(pattern, text, flags=re.I) for pattern in blocked_patterns):
            continue
        return text
    return ""


def extract_json_string(raw_text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw_text or "", flags=re.S | re.I)
    if fenced:
        return fenced.group(1).strip()
    return (raw_text or "").strip()


def parse_json_response(raw_text: str) -> dict | list:
    text = extract_json_string(raw_text)
    decoder = json.JSONDecoder()

    for start, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[start:])
            return value
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("No valid JSON object found", text, 0)


def chunk_list(items: list, size: int) -> list[list]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def write_json(path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
