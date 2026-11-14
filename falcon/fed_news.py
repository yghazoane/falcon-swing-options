from __future__ import annotations

from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import requests
import streamlit as st

FED_RSS_URL = "https://www.federalreserve.gov/feeds/press_all.xml"
USER_AGENT = "Falcon-Swing-Options-Educational-Research/1.0 (RSS reader)"


class FedFeedError(RuntimeError):
    """Raised when the official Fed endpoint does not return a readable feed."""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_fed_rss(xml_content: str | bytes) -> list[dict[str, str]]:
    """Parse RSS 2.0 or Atom content from the official Federal Reserve feed."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise FedFeedError(
            "استجابة موقع الفيدرالي ليست XML صالحاً. قد تكون صفحة HTML وسيطة أو استجابة حجب مؤقتة."
        ) from exc

    root_name = _local_name(root.tag)
    if root_name not in {"rss", "rdf", "feed"}:
        raise FedFeedError(
            f"صيغة غير متوقعة من مصدر الفيدرالي (نوع الجذر: {root_name or 'غير معروف'})."
        )

    items: list[dict[str, str]] = []
    entry_name = "entry" if root_name == "feed" else "item"

    for node in root.iter():
        if _local_name(node.tag) != entry_name:
            continue

        values: dict[str, str] = {}
        atom_link = ""
        for child in node:
            name = _local_name(child.tag)
            value = (child.text or "").strip()
            if name == "link":
                atom_link = child.attrib.get("href", "") or value
            elif name in {"title", "pubdate", "published", "updated", "description", "summary"}:
                values[name] = value

        title = values.get("title", "")
        link = values.get("link", "") or atom_link
        published = values.get("pubdate") or values.get("published") or values.get("updated", "")
        description = values.get("description") or values.get("summary", "")

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "published": published,
                "description": description,
            })

    return items


@st.cache_data(ttl=900, show_spinner=False)
def load_fed_news() -> dict[str, object]:
    """Fetch the official Fed feed and report upstream response failures clearly."""
    try:
        response = requests.get(
            FED_RSS_URL,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            },
            timeout=(8, 20),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FedFeedError(
            f"تعذر الاتصال بموجز الفيدرالي ("
            f"{type(exc).__name__}). تحقق من اتصال الاستضافة ثم أعد المحاولة."
        ) from exc

    content_type = response.headers.get("Content-Type", "غير محدد")
    items = parse_fed_rss(response.content)
    if not items:
        raise FedFeedError(
            "وصلت استجابة XML من المصدر لكنها لا تحتوي عناصر أخبار قابلة للعرض. "
            f"نوع المحتوى: {content_type}."
        )

    return {
        "items": items,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": FED_RSS_URL,
        "content_type": content_type,
        "status_code": response.status_code,
    }
