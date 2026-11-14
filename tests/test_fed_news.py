from falcon.fed_news import parse_fed_press_html, parse_fed_rss


def test_parse_rss_items():
    xml = """<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <title>FOMC statement</title>
      <link>/newsevents/pressreleases/monetary20261028a.htm</link>
      <pubDate>Wed, 28 Oct 2026 14:00:00 GMT</pubDate>
    </item></channel></rss>"""
    items = parse_fed_rss(xml)
    assert len(items) == 1
    assert items[0]["title"] == "FOMC statement"
    assert items[0]["link"].startswith("https://www.federalreserve.gov/")


def test_parse_official_press_html_fallback_and_deduplicate():
    html = """
    <html><body>
      <a href="/newsevents/pressreleases/monetary20261028a.htm">FOMC statement</a>
      <a href="/newsevents/pressreleases/monetary20261028a.htm">FOMC statement</a>
      <a href="/other/page.htm">Ignore unrelated link</a>
    </body></html>
    """
    items = parse_fed_press_html(html)
    assert len(items) == 1
    assert items[0]["title"] == "FOMC statement"
    assert items[0]["link"].endswith("/newsevents/pressreleases/monetary20261028a.htm")


def test_parse_malformed_or_non_xml_rss_raises_clear_error():
    import pytest
    from falcon.fed_news import FedFeedError

    with pytest.raises(FedFeedError):
        parse_fed_rss("<html>Access denied</html>")
