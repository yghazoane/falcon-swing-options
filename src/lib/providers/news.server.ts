// News adapters: official RSS feeds (no key) + optional Finnhub market news (FINNHUB_API_KEY).
// Headlines are passed through verbatim from the publisher; nothing is generated.
import { cached, fetchWithTimeout, ProviderError } from "./cache.server";
import type { NewsCategory, NewsImportance, NewsItem } from "../market/types";

export interface FeedDef {
  id: string;
  name: string;
  publisher: string;
  url: string;
  homepage: string;
  defaultCategory: NewsCategory;
}

export const RSS_FEEDS: FeedDef[] = [
  {
    id: "fed_monetary",
    name: "Federal Reserve — Monetary Policy",
    publisher: "Federal Reserve Board",
    url: "https://www.federalreserve.gov/feeds/press_monetary.xml",
    homepage: "https://www.federalreserve.gov/newsevents/pressreleases.htm",
    defaultCategory: "monetary_policy",
  },
  {
    id: "fed_all",
    name: "Federal Reserve — All Press Releases",
    publisher: "Federal Reserve Board",
    url: "https://www.federalreserve.gov/feeds/press_all.xml",
    homepage: "https://www.federalreserve.gov/newsevents/pressreleases.htm",
    defaultCategory: "banking",
  },
  {
    id: "bea",
    name: "U.S. Bureau of Economic Analysis",
    publisher: "BEA",
    url: "https://apps.bea.gov/rss/rss.xml",
    homepage: "https://www.bea.gov/news",
    defaultCategory: "economic_data",
  },
  {
    id: "sec",
    name: "SEC — Press Releases",
    publisher: "U.S. Securities and Exchange Commission",
    url: "https://www.sec.gov/news/pressreleases.rss",
    homepage: "https://www.sec.gov/newsroom/press-releases",
    defaultCategory: "regulation",
  },
];

function decode(s: string): string {
  return s
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/\s+/g, " ")
    .trim();
}

function tag(block: string, name: string): string | null {
  const m = block.match(new RegExp(`<${name}\\b[^>]*>([\\s\\S]*?)</${name}>`, "i"));
  return m ? decode(m[1]) : null;
}

export function parseRss(xml: string): { title: string; link: string; description: string | null; pubDate: string | null; category: string | null }[] {
  const items: ReturnType<typeof parseRss> = [];
  const re = /<item\b[^>]*>([\s\S]*?)<\/item>/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(xml))) {
    const block = m[1];
    const title = tag(block, "title");
    const link = tag(block, "link");
    if (!title || !link) continue;
    items.push({
      title,
      link,
      description: tag(block, "description"),
      pubDate: tag(block, "pubDate"),
      category: tag(block, "category"),
    });
  }
  return items;
}

const HIGH_PATTERNS = [
  /fomc statement/i,
  /federal open market committee/i,
  /minutes of the federal open market committee/i,
  /federal funds/i,
  /gross domestic product/i,
  /\bgdp\b/i,
  /personal income and outlays/i,
  /\bpce\b/i,
  /consumer price index/i,
  /employment situation/i,
  /nonfarm/i,
  /monetary policy/i,
];
const LOW_PATTERNS = [/enforcement action/i, /approval of application/i, /termination of enforcement/i, /announces .*appointment/i];

export function classify(
  title: string,
  feedCategory: NewsCategory,
  rssCategory: string | null,
): { category: NewsCategory; importance: NewsImportance } {
  let category = feedCategory;
  if (/fomc|monetary policy|federal funds|discount rate|interest on reserve/i.test(title)) category = "monetary_policy";
  else if (rssCategory && /monetary/i.test(rssCategory)) category = "monetary_policy";
  else if (/enforcement|supervis|bank/i.test(title) && feedCategory === "banking") category = "banking";

  let importance: NewsImportance = "medium";
  if (HIGH_PATTERNS.some((p) => p.test(title))) importance = "high";
  else if (LOW_PATTERNS.some((p) => p.test(title))) importance = "low";
  else if (category === "banking" || category === "regulation") importance = "low";
  return { category, importance };
}

function toIso(date: string | null): string | null {
  if (!date) return null;
  // BEA uses "EDT"/"EST" abbreviations that some engines do not parse.
  const normalized = date.replace(/\bEDT\b/, "-0400").replace(/\bEST\b/, "-0500");
  const t = Date.parse(normalized);
  return Number.isFinite(t) ? new Date(t).toISOString() : null;
}

export function fetchFeed(feed: FeedDef): Promise<NewsItem[]> {
  return cached(`rss:${feed.id}`, 10 * 60 * 1000, async () => {
    const res = await fetchWithTimeout(feed.url, { headers: { Accept: "application/rss+xml, application/xml, text/xml" } });
    if (!res.ok) throw new ProviderError(feed.id, "http", `HTTP ${res.status}`);
    const items = parseRss(await res.text());
    return items.slice(0, 30).map((it, i) => {
      const { category, importance } = classify(it.title, feed.defaultCategory, it.category);
      const excerpt = it.description && it.description !== it.title ? it.description.slice(0, 320) : null;
      return {
        id: `${feed.id}:${i}:${it.link}`,
        title: it.title,
        url: it.link,
        publisher: feed.publisher,
        feedId: feed.id,
        publishedAt: toIso(it.pubDate),
        category,
        importance,
        excerpt,
      };
    });
  });
}

export function fetchFinnhubNews(apiKey: string): Promise<NewsItem[]> {
  return cached(`finnhub:general`, 5 * 60 * 1000, async () => {
    const res = await fetchWithTimeout(`https://finnhub.io/api/v1/news?category=general`, {
      headers: { "X-Finnhub-Token": apiKey },
    });
    if (res.status === 401 || res.status === 403) throw new ProviderError("finnhub", "auth", "Rejected key");
    if (res.status === 429) throw new ProviderError("finnhub", "rate_limit", "Rate limited");
    if (!res.ok) throw new ProviderError("finnhub", "http", `HTTP ${res.status}`);
    const json = (await res.json()) as {
      id: number;
      headline: string;
      url: string;
      source: string;
      datetime: number;
      summary?: string;
    }[];
    return json.slice(0, 40).map((n) => {
      const { category, importance } = classify(n.headline, "markets", null);
      return {
        id: `finnhub:${n.id}`,
        title: n.headline,
        url: n.url,
        publisher: n.source,
        feedId: "finnhub",
        publishedAt: n.datetime ? new Date(n.datetime * 1000).toISOString() : null,
        category: category === "banking" ? "markets" : category,
        importance: importance === "high" ? "high" : "medium",
        excerpt: n.summary ? n.summary.slice(0, 320) : null,
      };
    });
  });
}
