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


def parse_payload(route: RouteConfig, page_html: str) -> dict[str, object]:
    if SITE_ERROR_TEXT in page_html:
        raise RuntimeError("神奈中サイトがエラーページを返しました。")

    page_title = extract_first(r"<title>(.*?)</title>", page_html)
    message = extract_first(r'<p class="color01">\s*<strong>(.*?)</strong>\s*</p>', page_html)
    main_fragment = extract_main_fragment(page_html)
    details = html_to_lines(main_fragment)

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