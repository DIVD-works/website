#!/usr/bin/env python3
"""Build the first-party DIVD.Works newsroom from its reviewable source data.

The website is intentionally dependency-free and GitHub-Pages compatible. The
JSON source is the editorial record; this script renders deterministic HTML and
RSS output checked into the static site.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "newsroom.json"
NEWSROOM = ROOT / "newsroom"
SITE_URL = "https://divd.works"
NEWSROOM_URL = f"{SITE_URL}/newsroom/"
LOGO_URL = f"{SITE_URL}/img/divd-works-logo-v2.svg"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def display_date(value: str) -> str:
    return parse_datetime(f"{value}T00:00:00Z").strftime("%d %B %Y")


def absolute_url(path: str) -> str:
    return f"{SITE_URL}{path}" if path.startswith("/") else path


def json_ld(value: dict[str, Any]) -> str:
    # Prevent a source value from prematurely closing the JSON-LD script tag.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def breadcrumb_data(items: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": name,
                "item": absolute_url(path),
            }
            for position, (name, path) in enumerate(items, start=1)
        ],
    }


def breadcrumbs(items: list[tuple[str, str]]) -> str:
    links = []
    for index, (name, path) in enumerate(items):
        if index == len(items) - 1:
            links.append(f"<span aria-current=\"page\">{esc(name)}</span>")
        else:
            links.append(f"<a href=\"{esc(path)}\">{esc(name)}</a>")
    return (
        '<nav class="newsroom-article__crumbs" aria-label="Breadcrumb">'
        + " <span aria-hidden=\"true\">/</span> ".join(links)
        + "</nav>"
    )


def header(active: str = "newsroom") -> str:
    newsroom_class = ' class="is-active"' if active == "newsroom" else ""
    return f"""    <header class="site-header" id="top">
      <div class="nav-shell">
        <a class="brand" href="/" aria-label="DIVD.Works home">
          <span class="brand__bubble">DIVD</span>
          <span class="brand__tag">WORKS</span>
        </a>
        <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="primary-nav" aria-label="Open navigation">
          <span></span><span></span><span></span>
        </button>
        <nav class="nav" id="primary-nav" aria-label="Primary navigation">
          <a href="/jobs/">Jobs</a>
          <a href="/students/">Students</a>
          <a href="/businesses/">Businesses</a>
          <a href="/programs/">Programs</a>
          <a{newsroom_class} href="/newsroom/">Newsroom</a>
        </nav>
        <div class="nav-actions">
          <a class="button button--small nav-cta" href="/join/">Join .Works</a>
        </div>
      </div>
    </header>"""


def footer() -> str:
    return """    <footer class="footer container newsroom-footer">
      <div class="footer__main">
        <div>
          <a class="footer-brand" href="/">DIVD.Works</a>
          <p>From first internship to first job.</p>
        </div>
        <div class="footer__links">
          <div>
            <h3>Platform</h3>
            <a href="/students/">For Students</a>
            <a href="/businesses/">For Businesses</a>
          </div>
          <div>
            <h3>Newsroom</h3>
            <a href="/newsroom/">All stories</a>
            <a href="/newsroom/feed.xml">RSS feed</a>
          </div>
          <div>
            <h3>Company</h3>
            <a href="/about/">About</a>
            <a href="/company-information/">Company information</a>
          </div>
        </div>
      </div>
      <div class="footer__bottom">
        <span>&copy; 2026 DIVD.Works</span>
        <nav aria-label="Legal">
          <a href="/privacy/policy/">Privacy</a>
          <a href="/accessibility/">Accessibility</a>
          <a href="/terms/">Terms</a>
        </nav>
      </div>
    </footer>
    <script src="/js/nav.js"></script>"""


def document(
    *,
    title: str,
    description: str,
    canonical: str,
    body: str,
    structured_data: dict[str, Any],
    extra_structured_data: list[dict[str, Any]] | None = None,
    og_type: str = "website",
    hero_image: str | None = None,
    article_published: str | None = None,
    article_modified: str | None = None,
) -> str:
    image_meta = (
        f'    <meta property="og:image" content="{esc(absolute_url(hero_image or "/img/stock/divd-works.png"))}" />\n'
        f'    <meta name="twitter:image" content="{esc(absolute_url(hero_image or "/img/stock/divd-works.png"))}" />\n'
    )
    article_meta = (
        f'    <meta property="article:published_time" content="{esc(article_published)}" />\n'
        f'    <meta property="article:modified_time" content="{esc(article_modified)}" />\n'
        if article_published and article_modified
        else ""
    )
    schemas = [structured_data, *(extra_structured_data or [])]
    schema_scripts = "\n".join(
        f'    <script type="application/ld+json">{json_ld(schema)}</script>'
        for schema in schemas
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="{esc(description)}" />
    <meta name="theme-color" content="#080808" />
    <title>{esc(title)}</title>
    <link rel="stylesheet" href="/css/styles.css" />
    <link rel="stylesheet" href="/css/newsroom.css" />
    <link rel="canonical" href="{esc(canonical)}" />
    <link rel="alternate" type="application/rss+xml" title="DIVD.Works Newsroom" href="{NEWSROOM_URL}feed.xml" />
    <meta property="og:type" content="{esc(og_type)}" />
    <meta property="og:title" content="{esc(title)}" />
    <meta property="og:description" content="{esc(description)}" />
    <meta property="og:url" content="{esc(canonical)}" />
    <meta property="og:site_name" content="DIVD.Works" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{esc(title)}" />
    <meta name="twitter:description" content="{esc(description)}" />
{image_meta}{article_meta}    <meta name="author" content="DIVD.works" />
{schema_scripts}
  </head>
  <body class="newsroom-page">
{header()}
{body}
{footer()}
  </body>
</html>
"""


def publisher() -> dict[str, Any]:
    return {
        "@type": "Organization",
        "name": "DIVD.Works",
        "url": SITE_URL,
        "logo": {"@type": "ImageObject", "url": LOGO_URL},
    }


def article_url(article: dict[str, Any]) -> str:
    return f"{NEWSROOM_URL}p/{article['slug']}/"


def article_card(article: dict[str, Any], *, featured: bool = False) -> str:
    class_name = "newsroom-card newsroom-card--featured" if featured else "newsroom-card"
    return f"""          <article class="{class_name}">
            <a class="newsroom-card__image-link" href="/newsroom/p/{esc(article['slug'])}/">
              <img src="{esc(article['hero'])}" alt="{esc(article['heroAlt'])}" loading="{'eager' if featured else 'lazy'}" />
            </a>
            <div class="newsroom-card__content">
              <p class="newsroom-meta"><span>{esc(article['topic'])}</span><time datetime="{esc(article['published'])}">{display_date(article['published'])}</time></p>
              <h2><a href="/newsroom/p/{esc(article['slug'])}/">{esc(article['title'])}</a></h2>
              <p class="newsroom-card__dek">{esc(article['dek'])}</p>
              <p class="newsroom-card__excerpt">{esc(article['excerpt'])}</p>
              <a class="newsroom-read-link" href="/newsroom/p/{esc(article['slug'])}/">Read story <span aria-hidden="true">→</span></a>
            </div>
          </article>"""


def index_page(data: dict[str, Any]) -> str:
    articles = sorted(data["articles"], key=lambda item: item["published"], reverse=True)
    featured = articles[0]
    archive = articles[1:]
    description = data["section"]["description"]
    cards = "\n".join(article_card(article) for article in archive)
    if not cards:
        cards = '<p class="newsroom-empty">New stories are on the way.</p>'
    body = f"""    <main>
      <section class="newsroom-hero" aria-labelledby="newsroom-title">
        <div class="newsroom-shell newsroom-hero__inner">
          <p class="newsroom-kicker">DIVD.WORKS / NEWSROOM</p>
          <h1 id="newsroom-title">{esc(data['section']['tagline'])}</h1>
          <p class="newsroom-hero__copy">{esc(description)}</p>
          <a class="newsroom-text-link" href="/newsroom/feed.xml">Follow the open RSS feed <span aria-hidden="true">↗</span></a>
        </div>
      </section>
      <section class="newsroom-shell newsroom-featured" aria-labelledby="latest-story-title">
        <div class="newsroom-section-heading">
          <div>
            <p class="newsroom-kicker">LATEST STORY</p>
            <h2 id="latest-story-title">What we are building</h2>
          </div>
          <p class="newsroom-section-heading__note">A first-party archive for news, people, and the work behind the work.</p>
        </div>
{article_card(featured, featured=True)}
      </section>
      <section class="newsroom-shell newsroom-archive" aria-labelledby="archive-title">
        <div class="newsroom-section-heading">
          <div>
            <p class="newsroom-kicker">ARCHIVE</p>
            <h2 id="archive-title">Earlier stories</h2>
          </div>
        </div>
        <div class="newsroom-grid">
{cards}
        </div>
      </section>
    </main>"""
    structured = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "DIVD.Works Newsroom",
        "description": description,
        "url": NEWSROOM_URL,
        "isPartOf": {"@type": "WebSite", "name": "DIVD.Works", "url": SITE_URL},
        "publisher": publisher(),
        "hasPart": [
            {"@type": "NewsArticle", "headline": article["title"], "url": article_url(article)}
            for article in articles
        ],
    }
    return document(
        title="Newsroom | DIVD.Works",
        description=description,
        canonical=NEWSROOM_URL,
        body=body,
        structured_data=structured,
    )


def article_page(article: dict[str, Any], all_articles: list[dict[str, Any]]) -> str:
    url = article_url(article)
    paragraphs = "\n".join(f"            <p>{esc(text)}</p>" for text in article["paragraphs"])
    related_links = "\n".join(
        f'              <a class="newsroom-related__link" href="{esc(item["href"])}">{esc(item["label"])} <span aria-hidden="true">→</span></a>'
        for item in article["related"]
    )
    more = [item for item in all_articles if item["slug"] != article["slug"]]
    more_cards = "\n".join(article_card(item) for item in more)
    if article.get("legacyUrl"):
        provenance = (
            "          <p><strong>Migrated from the former DIVD.works newsroom.</strong> "
            "The original publication date is preserved. "
            f'<a href="{esc(article["legacyUrl"])}" rel="noopener noreferrer">View the original source '
            '<span aria-hidden="true">↗</span></a></p>'
        )
    elif article.get("sourceUrl"):
        source_label = article.get("sourceLabel", "Based on a public announcement.")
        provenance = (
            f'          <p><strong>{esc(source_label)}</strong> '
            f'<a href="{esc(article["sourceUrl"])}" rel="noopener noreferrer">View the original source '
            '<span aria-hidden="true">↗</span></a></p>'
        )
    else:
        provenance = ""
    body = f"""    <main>
      <article class="newsroom-article newsroom-shell">
        {breadcrumbs([("Newsroom", "/newsroom/"), (article["topic"], url)])}
        <header class="newsroom-article__header">
          <p class="newsroom-kicker">{esc(article['topic'])}</p>
          <h1>{esc(article['title'])}</h1>
          <p class="newsroom-article__dek">{esc(article['dek'])}</p>
          <div class="newsroom-article__byline">
            <span>By {esc(article['author'])}</span>
            <span aria-hidden="true">·</span>
            <time datetime="{esc(article['publishedISO'])}">Published {display_date(article['published'])}</time>
          </div>
        </header>
        <figure class="newsroom-article__hero">
          <img src="{esc(article['hero'])}" alt="{esc(article['heroAlt'])}" />
        </figure>
        <div class="newsroom-article__layout">
          <div class="newsroom-article__body">
{paragraphs}
          </div>
          <aside class="newsroom-related" aria-label="Related links">
            <p class="newsroom-kicker">KEEP EXPLORING</p>
{related_links}
          </aside>
        </div>
        <div class="newsroom-provenance">
{provenance}
        </div>
      </article>
      <section class="newsroom-shell newsroom-more" aria-labelledby="more-title">
        <div class="newsroom-section-heading">
          <div>
            <p class="newsroom-kicker">FROM THE ARCHIVE</p>
            <h2 id="more-title">More from the newsroom</h2>
          </div>
        </div>
        <div class="newsroom-grid">
{more_cards}
        </div>
      </section>
    </main>"""
    structured = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "url": url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "headline": article["title"],
        "description": article["dek"],
        "image": [absolute_url(article["hero"])],
        "datePublished": article["publishedISO"],
        "dateModified": article["modifiedISO"],
        "isAccessibleForFree": True,
        "articleSection": article["topic"],
        "articleBody": "\n\n".join(article["paragraphs"]),
        "author": {"@type": "Organization", "name": article["author"], "url": SITE_URL},
        "publisher": publisher(),
    }
    breadcrumb_schema = breadcrumb_data(
        [("Newsroom", "/newsroom/"), (article["topic"], url)]
    )
    return document(
        title=f"{article['title']} | DIVD.Works Newsroom",
        description=article["dek"],
        canonical=url,
        body=body,
        structured_data=structured,
        extra_structured_data=[breadcrumb_schema],
        og_type="article",
        hero_image=article["hero"],
        article_published=article["publishedISO"],
        article_modified=article["modifiedISO"],
    )


def cdata(value: str) -> str:
    return f"<![CDATA[{value.replace(']]>', ']]]]><![CDATA[>')}]]>"


def feed(data: dict[str, Any]) -> str:
    articles = sorted(data["articles"], key=lambda item: item["publishedISO"], reverse=True)
    latest = parse_datetime(articles[0]["publishedISO"])
    items = []
    for article in articles:
        url = article_url(article)
        published = parse_datetime(article["publishedISO"])
        description = f"{article['dek']} {article['excerpt']}"
        items.append(
            f"""    <item>
      <title>{cdata(article['title'])}</title>
      <link>{esc(url)}</link>
      <guid isPermaLink="true">{esc(url)}</guid>
      <description>{cdata(description)}</description>
      <pubDate>{format_datetime(published, usegmt=True)}</pubDate>
      <dc:creator>{esc(article['author'])}</dc:creator>
      <category>{esc(article['topic'])}</category>
    </item>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>DIVD.Works Newsroom</title>
    <link>{NEWSROOM_URL}</link>
    <description>{esc(data['section']['description'])}</description>
    <language>en</language>
    <lastBuildDate>{format_datetime(latest, usegmt=True)}</lastBuildDate>
    <atom:link href="{NEWSROOM_URL}feed.xml" rel="self" type="application/rss+xml" xmlns:atom="http://www.w3.org/2005/Atom" />
{chr(10).join(items)}
  </channel>
</rss>
"""


def expected_outputs(data: dict[str, Any]) -> dict[Path, str]:
    output = {
        NEWSROOM / "index.html": index_page(data),
        NEWSROOM / "feed.xml": feed(data),
    }
    for article in data["articles"]:
        output[NEWSROOM / "p" / article["slug"] / "index.html"] = article_page(
            article, data["articles"]
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    outputs = expected_outputs(data)
    stale = []
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        print("Stale newsroom output:", ", ".join(stale), file=sys.stderr)
        return 1
    if not args.check:
        print(f"Generated {len(outputs)} newsroom files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
