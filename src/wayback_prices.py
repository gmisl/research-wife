"""Collect historical organic minced-meat price signals from Internet Archive snapshots."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

UA = "research-wife/1.0 (historical price research)"
ORGANIC = re.compile(r"organic|bio(?:[- ]?logisch)?|ekolog|ecolog|luomu|økolog|biologico|biologico|био", re.I)
MINCED = re.compile(r"minc|ground|hack|gehakt|hakkliha|hakkliha|mleté|mljeven|daralt|tocat|picad|macinat|köttfärs|farš|faršs|malt", re.I)
PRICE = re.compile(r"(?:€|EUR|\bDKK\b|\bSEK\b|\bPLN\b|\bCZK\b|\bHUF\b|\bRON\b|\bBGN\b|\bHRK\b|\bBAM\b)\s*([0-9]{1,4}(?:[.,][0-9]{1,2})?|[0-9]{1,4}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)|([0-9]{1,4}(?:[.,][0-9]{1,2})?)\s*(?:€|EUR|DKK|SEK|PLN|CZK|HUF|RON|BGN|HRK)", re.I)
CURRENCY = re.compile(r"€|EUR|DKK|SEK|PLN|CZK|HUF|RON|BGN|HRK", re.I)


def get(url: str, **kwargs):
    return requests.get(url, headers={"User-Agent": UA}, timeout=25, **kwargs)


def cdx_snapshots(website: str) -> list[dict]:
    host = urlparse(website).netloc or urlparse("https://" + website).netloc
    if not host:
        return []
    query = (
        "https://web.archive.org/cdx/search/cdx?"
        f"url={quote(host + '/*', safe='')}&from=2020&to=2026"
        "&output=json&filter=statuscode:200&filter=mimetype:text/html"
        "&fl=timestamp,original,statuscode,digest&collapse=digest&limit=40"
    )
    response = get(query)
    if response.status_code != 200:
        return []
    rows = response.json()
    if not isinstance(rows, list) or len(rows) < 2:
        return []
    header, values = rows[0], rows[1:]
    parsed = [dict(zip(header, row)) for row in values]
    # One early and one late snapshot gives a useful time span without hammering the archive.
    return [parsed[0], parsed[-1]] if len(parsed) > 1 else parsed


def normalise_number(value: str) -> float:
    value = value.replace(" ", "")
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")
    return float(value)


def extract(supplier: dict, snapshot: dict) -> dict | None:
    timestamp = snapshot.get("timestamp", "")
    original = snapshot.get("original", "")
    archived = f"https://web.archive.org/web/{timestamp}id_/{original}"
    response = get(archived)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    text = " ".join(soup.stripped_strings)
    if not ORGANIC.search(text) or not MINCED.search(text):
        return None

    for match in PRICE.finditer(text):
        start, end = max(0, match.start() - 220), min(len(text), match.end() + 220)
        context = text[start:end]
        if not ORGANIC.search(context) or not MINCED.search(context):
            continue
        raw = match.group(1) or match.group(2)
        if not raw:
            continue
        try:
            value = normalise_number(raw)
        except ValueError:
            continue
        if value <= 0 or value > 10000:
            continue
        currency_match = CURRENCY.search(match.group(0))
        currency = currency_match.group(0).upper() if currency_match else "EUR"
        unit = "EUR/kg" if re.search(r"/\s*kg|per\s*kg|kg\s*[-:]?", context, re.I) else "EUR/unit"
        return {
            "legal_name": supplier["legal_name"],
            "country_code": supplier["country_code"],
            "category_code": supplier.get("category_code", "minced_beef"),
            "description": "Historical organic minced-meat price extracted from archived page",
            "price": value,
            "currency": currency,
            "unit": unit,
            "date": f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}",
            "website": original,
            "archive_url": archived,
            "channel": "web_archive_reference",
            "is_wholesale": False,
            "price_status": "archived",
            "reason": "Automatically extracted from an Internet Archive snapshot; requires manual confirmation before wholesale statistics.",
        }
    return None


def process(supplier: dict) -> list[dict]:
    try:
        snapshots = cdx_snapshots(supplier.get("official_contact", {}).get("website", ""))
        results = []
        for snapshot in snapshots:
            row = extract(supplier, snapshot)
            if row:
                results.append(row)
        return results
    except Exception as exc:
        print(f"Wayback skipped {supplier.get('legal_name')}: {exc}")
        return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/initial_candidates.json")
    parser.add_argument("--output", default="data/history/price_observations.json")
    args = parser.parse_args()
    suppliers = json.loads(Path(args.input).read_text(encoding="utf-8"))
    output = Path(args.output)
    try:
        history = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        history = []
    if not isinstance(history, list):
        history = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(process, supplier) for supplier in suppliers]
        found = []
        for future in as_completed(futures):
            found.extend(future.result())

    keys = {(x.get("legal_name"), x.get("country_code"), x.get("date"), x.get("price"), x.get("currency"), x.get("archive_url")) for x in history}
    for row in found:
        key = (row.get("legal_name"), row.get("country_code"), row.get("date"), row.get("price"), row.get("currency"), row.get("archive_url"))
        if key not in keys:
            history.append(row)
            keys.add(key)
    history.sort(key=lambda x: (x.get("date", ""), x.get("country_code", ""), x.get("legal_name", "")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wayback found {len(found)} new observations; total observations {len(history)}")


if __name__ == "__main__":
    main()
