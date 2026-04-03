from __future__ import annotations

import argparse
import html
import http.cookiejar
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "https://real.kanachu.jp/pc/"
FROM_STOP_ID = "16240"
TO_STOP_ID = "16244"
FROM_STOP_NAME = "伊勢山（平塚市）"
TO_STOP_NAME = "大野農協前（平塚市）"
SITE_ERROR_TEXT = "以下のエラーが発生しました"
JOURNEY_START_RE = re.compile(r"^早い順\s+(\d+)$")
ACCESSIBILITY_LABELS = {
    "※": "ノンステップ",
    "★": "ワンステップ",
    "Ｔ": "TwinLiner",
}

IGNORED_LINES = {
    "トップ",
    "接近情報",
    "接近情報検索結果",
    "携帯へ送る",
    "再検索する",
    "時刻表",
    "地図情報",
    "入れ替えて検索",
    "前のページへ戻る",
}


@dataclass(frozen=True)
class RouteConfig:
    from_stop_id: str
    to_stop_id: str
    from_stop_name: str
    to_stop_name: str

    @property
    def source_url(self) -> str:
        query = urllib.parse.urlencode(
            {
                "fromToType": "0",
                "fNO": self.from_stop_id,
                "fNM": self.from_stop_name,
                "tNO": self.to_stop_id,
                "tNM": self.to_stop_name,
            }
        )
        return urllib.parse.urljoin(BASE_URL, f"displayapproachinfo?{query}")


ROUTE = RouteConfig(
    from_stop_id=FROM_STOP_ID,
    to_stop_id=TO_STOP_ID,
    from_stop_name=FROM_STOP_NAME,
    to_stop_name=TO_STOP_NAME,
)


def build_opener() -> urllib.request.OpenerDirector:
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    opener.addheaders = [("User-Agent", "bus-tracer/1.0 (+https://github.com/Npieju/bus-tracer)")]
    return opener


def fetch_page(route: RouteConfig) -> str:
    opener = build_opener()
    opener.open(urllib.parse.urljoin(BASE_URL, "searchapproachinfo"), timeout=30).read()
    with opener.open(route.source_url, timeout=30) as response:
        raw = response.read()
    return raw.decode("shift_jis", errors="replace")


def extract_first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    value = html.unescape(match.group(1))
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def extract_main_fragment(page_html: str) -> str:
    match = re.search(r'<div id="main">(.*?)<!-- /main -->', page_html, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else page_html


def compact_stop_name(name: str) -> str:
    compact = re.sub(r"（.*?）", "", name)
    compact = re.sub(r"\(.*?\)", "", compact)
    return compact.strip()


def html_to_lines(fragment: str) -> list[str]:
    cleaned = re.sub(r"<script.*?</script>", "", fragment, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<style.*?</style>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<form.*?</form>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<img[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</(p|li|tr|h1|h2|h3|h4|h5|h6|dt|dd|th|td|div|ul|ol)>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)

    lines: list[str] = []
    previous = ""
    for raw_line in cleaned.splitlines():
        normalized = re.sub(r"\s+", " ", raw_line).strip()
        if not normalized:
            continue
        if normalized in IGNORED_LINES:
            continue
        if normalized == previous:
            continue
        lines.append(normalized)
        previous = normalized
    return lines


def unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def extract_overview(details: list[str]) -> list[str]:
    overview: list[str] = []
    for line in details:
        if JOURNEY_START_RE.match(line):
            break
        if "接近情報です。" in line or "御利用下さい" in line:
            overview.append(line)
    return overview


def find_label(lines: list[str], label: str, start: int = 0) -> int:
    for index in range(start, len(lines)):
        if lines[index] == label:
            return index
    return -1


def parse_journey_block(lines: list[str]) -> tuple[dict[str, object], list[str]]:
    rank_match = JOURNEY_START_RE.match(lines[0])
    if not rank_match:
        raise RuntimeError("便ブロックの先頭を解釈できませんでした。")

    rank = int(rank_match.group(1))

    route_index = find_label(lines, "系統")
    destination_index = find_label(lines, "行き先")
    via_index = find_label(lines, "経由")
    vehicle_index = find_label(lines, "車両番号")
    duration_index = find_label(lines, "所要時分")
    cash_index = find_label(lines, "現金")
    ic_index = find_label(lines, "IC")
    updated_index = next((index for index, line in enumerate(lines) if "最終更新" in line), -1)

    vehicle_mark = None
    if vehicle_index != -1 and vehicle_index + 2 < len(lines) and lines[vehicle_index + 2] in ACCESSIBILITY_LABELS:
        vehicle_mark = lines[vehicle_index + 2]

    duration_note = None
    if duration_index != -1 and duration_index + 2 < len(lines) and lines[duration_index + 2].startswith("（"):
        duration_note = lines[duration_index + 2]

    notices_start = ic_index + 2 if ic_index != -1 else -1
    notices = unique_preserving_order(lines[notices_start:updated_index]) if notices_start != -1 and updated_index != -1 else []

    tail = lines[updated_index + 1 :] if updated_index != -1 else []
    headline = tail[0] if tail else None
    body_lines = tail[1:] if len(tail) > 1 else []

    arrival_scheduled = None
    if body_lines and "着予定" in body_lines[-1]:
        arrival_scheduled = body_lines[-1]
        body_lines = body_lines[:-1]

    def is_status_note(line: str) -> bool:
        return (
            line.startswith("（")
            or line.startswith("(")
            or "遅れ" in line
            or "運行中" in line
            or "発車します" in line
            or "発車から" in line
        )

    status_notes = [line for line in body_lines if is_status_note(line)]
    stop_list = [line for line in body_lines if not is_status_note(line)]

    journey = {
        "rank": rank,
        "route": lines[route_index + 1] if route_index != -1 and route_index + 1 < len(lines) else None,
        "destination": lines[destination_index + 1] if destination_index != -1 and destination_index + 1 < len(lines) else None,
        "via": lines[via_index + 1] if via_index != -1 and via_index + 1 < len(lines) else None,
        "vehicleNumber": lines[vehicle_index + 1] if vehicle_index != -1 and vehicle_index + 1 < len(lines) else None,
        "vehicleMark": vehicle_mark,
        "accessibilityLabel": ACCESSIBILITY_LABELS.get(vehicle_mark),
        "duration": lines[duration_index + 1] if duration_index != -1 and duration_index + 1 < len(lines) else None,
        "durationNote": duration_note,
        "cashFare": lines[cash_index + 1] if cash_index != -1 and cash_index + 1 < len(lines) else None,
        "icFare": lines[ic_index + 1] if ic_index != -1 and ic_index + 1 < len(lines) else None,
        "updatedAtText": lines[updated_index] if updated_index != -1 else None,
        "headline": headline,
        "statusNotes": status_notes,
        "stops": stop_list,
        "arrivalScheduled": arrival_scheduled,
    }
    return journey, notices


def parse_structured_details(details: list[str]) -> tuple[list[str], list[str], list[dict[str, object]]]:
    overview = extract_overview(details)

    blocks: list[list[str]] = []
    current: list[str] = []
    for line in details:
        if JOURNEY_START_RE.match(line):
            if current:
                blocks.append(current)
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        blocks.append(current)

    journeys: list[dict[str, object]] = []
    notices: list[str] = []
    for block in blocks:
        journey, block_notices = parse_journey_block(block)
        journeys.append(journey)
        if not notices and block_notices:
            notices = block_notices

    return overview, notices, journeys


def parse_payload(route: RouteConfig, page_html: str) -> dict[str, object]:
    if SITE_ERROR_TEXT in page_html:
        raise RuntimeError("神奈中サイトがエラーページを返しました。")

    page_title = extract_first(r"<title>(.*?)</title>", page_html)
    message = extract_first(r'<p class="color01">\s*<strong>(.*?)</strong>\s*</p>', page_html)
    main_fragment = extract_main_fragment(page_html)
    details = html_to_lines(main_fragment)
    overview, notices, journeys = parse_structured_details(details)

    if details and details[0].startswith("トップ >"):
        details = details[1:]

    payload: dict[str, object] = {
        "status": "ok",
        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "message": message or "接近情報を取得しました。",
        "hasLiveData": message != "該当する情報は現在ありません。",
        "route": {
            "fromStop": {"id": route.from_stop_id, "name": route.from_stop_name},
            "toStop": {"id": route.to_stop_id, "name": route.to_stop_name},
        },
        "source": {
            "name": "神奈中バスロケーション",
            "url": route.source_url,
            "pageTitle": page_title,
        },
        "overview": overview,
        "notices": notices,
        "journeys": journeys,
        "details": details,
    }
    return payload


def validate_payload(route: RouteConfig, payload: dict[str, object]) -> None:
    page_title = payload["source"]["pageTitle"]
    details = payload["details"]
    from_label = compact_stop_name(route.from_stop_name)
    to_label = compact_stop_name(route.to_stop_name)

    if not isinstance(page_title, str) or "接近情報検索結果" not in page_title:
        raise RuntimeError("接近情報ページのタイトルを確認できませんでした。")

    if not isinstance(details, list) or not details:
        raise RuntimeError("接近情報の明細を抽出できませんでした。")

    journeys = payload.get("journeys")
    if payload.get("hasLiveData") and (not isinstance(journeys, list) or not journeys):
        raise RuntimeError("運行情報ありなのに便一覧を構造化できませんでした。")

    joined = "\n".join(str(item) for item in details)
    if from_label not in joined or to_label not in joined:
        raise RuntimeError("対象停留所名を抽出結果から確認できませんでした。")


def build_error_payload(route: RouteConfig, exc: Exception) -> dict[str, object]:
    return {
        "status": "error",
        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "message": "データ取得に失敗しました。次回の自動更新を待ってください。",
        "hasLiveData": False,
        "route": {
            "fromStop": {"id": route.from_stop_id, "name": route.from_stop_name},
            "toStop": {"id": route.to_stop_id, "name": route.to_stop_name},
        },
        "source": {
            "name": "神奈中バスロケーション",
            "url": route.source_url,
            "pageTitle": None,
        },
        "overview": [],
        "notices": [],
        "journeys": [],
        "details": [str(exc)],
    }


def write_payload(output_path: Path, payload: dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Kanachu real-time bus approach info.")
    parser.add_argument(
        "--output",
        default="docs/data/status.json",
        help="Where to write the JSON snapshot.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    try:
        page_html = fetch_page(ROUTE)
        payload = parse_payload(ROUTE, page_html)
        validate_payload(ROUTE, payload)
    except Exception as exc:
        payload = build_error_payload(ROUTE, exc)

    write_payload(output_path, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())