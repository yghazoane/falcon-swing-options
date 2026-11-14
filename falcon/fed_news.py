from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin
import re
import xml.etree.ElementTree as ET

import requests
import streamlit as st

FED_RSS_URL = "https://www.federalreserve.gov/feeds/press_all.xml"
FED_PRESS_URL = "https://www.federalreserve.gov/newsevents/pressreleases.htm"
USER_AGENT = "Falcon-Swing-Options-Educational-Research/1.0 (RSS reader)"


class FedFeedError(RuntimeError):
    """Raised when the official Federal Reserve feed cannot be read."""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_fed_rss(xml_content: str | bytes) -> list[dict[str, str]]:
    """Parse RSS 2.0 or Atom content from the official Federal Reserve feed."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise FedFeedError(
            "استجابة موجز RSS ليست XML صالحاً؛ سيتم تجربة صفحة البيانات الصحفية الرسمية."
        ) from exc

    root_name = _local_name(root.tag)
    if root_name not in {"rss", "rdf", "feed"}:
        raise FedFeedError(
            "استجابة موجز RSS بصيغة غير متوقعة؛ سيتم تجربة صفحة البيانات الصحفية الرسمية."
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
                "link": urljoin(FED_PRESS_URL, link),
                "published": published,
                "description": description,
            })
    return items


class _PressReleaseHTMLParser(HTMLParser):
    """Extract article links from the Federal Reserve's official press listing."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._current_href = ""
        self._current_text: list[str] = []
        self.items: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._current_href = dict(attrs).get("href") or ""
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._current_href:
            return
        title = " ".join(part for part in self._current_text if part).strip()
        href = self._current_href
        if (
            title
            and re.search(r"/newsevents/pressreleases/[^?#]+\.htm$", href, re.IGNORECASE)
        ):
            self.items.append({
                "title": title,
                "link": urljoin(FED_PRESS_URL, href),
                "published": "",
                "description": "",
            })
        self._current_href = ""
        self._current_text = []


def parse_fed_press_html(html_content: str) -> list[dict[str, str]]:
    parser = _PressReleaseHTMLParser()
    parser.feed(html_content)
    parser.close()
    unique: dict[str, dict[str, str]] = {}
    for item in parser.items:
        unique[item["link"]] = item
    return list(unique.values())


def _get(url: str, accept: str) -> requests.Response:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept},
        timeout=(8, 20),
    )
    response.raise_for_status()
    return response


@st.cache_data(ttl=900, show_spinner=False)
def load_fed_news() -> dict[str, object]:
    """Try the official RSS feed, then fall back to the official HTML listing."""
    errors: list[str] = []

    try:
        rss_response = _get(
            FED_RSS_URL,
            "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        )
        items = parse_fed_rss(rss_response.content)
        if items:
            return {
                "items": items,
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "source": FED_RSS_URL,
                "source_label": "Federal Reserve RSS",
                "content_type": rss_response.headers.get("Content-Type", "غير محدد"),
            }
        errors.append("موجز RSS لم يتضمن عناصر قابلة للعرض.")
    except (requests.RequestException, FedFeedError) as exc:
        errors.append(str(exc))

    try:
        html_response = _get(FED_PRESS_URL, "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8")
        items = parse_fed_press_html(html_response.text)
        if not items:
            raise FedFeedError("لم يتم العثور على روابط بيانات صحفية في صفحة الفيدرالي.")
        return {
            "items": items,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": FED_PRESS_URL,
            "source_label": "Federal Reserve official press releases page (HTML fallback)",
            "content_type": html_response.headers.get("Content-Type", "غير محدد"),
            "notice": "تعذر تحليل موجز RSS؛ تم استخدام صفحة البيانات الصحفية الرسمية كبديل.",
        }
    except (requests.RequestException, FedFeedError) as exc:
        errors.append(str(exc))

    raise FedFeedError("تعذر تحميل أخبار الفيدرالي. " + " | ".join(errors))
