from __future__ import annotations

from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import requests
import streamlit as st

FED_RSS_URL = "https://www.federalreserve.gov/feeds/press_all.xml"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_fed_rss(xml_text: str) -> list[dict[str, str]]:
    """Parse official Federal Reserve press-release RSS items."""
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []
    for node in root.iter():
        if _local_name(node.tag) != "item":
            continue
        values = {_local_name(child.tag): (child.text or "").strip() for child in node}
        title, link = values.get("title", ""), values.get("link", "")
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "published": values.get("pubdate", ""),
                "description": values.get("description", ""),
            })
    return items


@st.cache_data(ttl=900, show_spinner=False)
def load_fed_news() -> dict[str, object]:
    """Fetch official Fed press RSS; never substitute fabricated headlines."""
    response = requests.get(
        FED_RSS_URL,
        headers={"User-Agent": "Falcon Swing Options educational research"},
        timeout=20,
    )
    response.raise_for_status()
    return {
        "items": parse_fed_rss(response.text),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": FED_RSS_URL,
    }
