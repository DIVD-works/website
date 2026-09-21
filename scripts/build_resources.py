#!/usr/bin/env python3
"""Render source-backed audience resources for the static DIVD.Works site."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "resources.json"
SITE_URL = "https://divd.works"
RESOURCE_ROOT = ROOT / "resources"
SOCIAL_IMAGE = f"{SITE_URL}/img/stock/divd-works.png"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def absolute_url(path: str) -> str:
    return f"{SITE_URL}{path}" if path.startswith("/") else path


def json_ld(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


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
    return '<nav class="resource-breadcrumbs" aria-label="Breadcrumb">' + \
        ' <span aria-hidden="true">/</span> '.join(links) + "</nav>"


def header() -> str:
    return """    <header class="site-header" id="top">
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
          <a href="/newsroom/">Newsroom</a>
        </nav>
        <div class="nav-actions">
          <a class="button button--small nav-cta" href="/join/">Join .Works</a>
        </div>
      </div>
    </header>"""


def footer() -> str:
    return """    <footer class="footer container resource-footer">
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
            <h3>Resources</h3>
            <a href="/resources/">All resources</a>
            <a href="/newsroom/">Newsroom</a>
          </div>
          <div>
            <h3>Company</h3>
            <a href="/about/">About</a>
            <a href="/safety/">Safety</a>
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
    schemas: list[dict[str, Any]],
) -> str:
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
    <link rel="stylesheet" href="/css/resources.css" />
    <link rel="canonical" href="{esc(canonical)}" />
    <meta property="og:type" content="article" />
    <meta property="og:title" content="{esc(title)}" />
    <meta property="og:description" content="{esc(description)}" />
    <meta property="og:url" content="{esc(canonical)}" />
    <meta property="og:site_name" content="DIVD.Works" />
    <meta property="og:image" content="{SOCIAL_IMAGE}" />
    <meta property="og:image:alt" content="DIVD.Works" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{esc(title)}" />
    <meta name="twitter:description" content="{esc(description)}" />
    <meta name="twitter:image" content="{SOCIAL_IMAGE}" />
{schema_scripts}
  </head>
  <body class="resources-page">
{header()}
{body}
{footer()}
  </body>
</html>
"""


def resource_url(resource: dict[str, Any]) -> str:
    return f"{SITE_URL}/resources/{resource['slug']}/"


def resource_path(resource: dict[str, Any]) -> Path:
    return RESOURCE_ROOT / resource["slug"] / "index.html"


def audience_path(audience: str) -> str:
    return {
        "Students": "/resources/students/",
        "Employers": "/resources/employers/",
        "Schools": "/resources/schools/",
    }[audience]


def audience_slug(audience: str) -> str:
    return audience.lower()


def resource_card(resource: dict[str, Any]) -> str:
    return f"""          <article class="resource-card">
            <p class="resource-card__kicker">{esc(resource["kicker"])}</p>
            <h3><a href="/resources/{esc(resource["slug"])}/">{esc(resource["title"])}</a></h3>
            <p>{esc(resource["description"])}</p>
            <a class="resource-card__link" href="/resources/{esc(resource["slug"])}/">Read guide <span aria-hidden="true">→</span></a>
          </article>"""


def index_page(resources: list[dict[str, Any]]) -> str:
    description = "Practical, source-backed guidance for students, employers, and schools working towards better IT placements."
    canonical = f"{SITE_URL}/resources/"
    groups = []
    for audience in ("Students", "Employers", "Schools"):
        matching = [item for item in resources if item["audience"] == audience]
        cards = "\n".join(resource_card(item) for item in matching)
        groups.append(
            f"""        <section class="resource-group" aria-labelledby="{audience_slug(audience)}-resources">
          <div class="resource-group__heading">
            <p class="resource-kicker">{audience.upper()} / GUIDES</p>
            <h2 id="{audience_slug(audience)}-resources">{esc(audience)} resources</h2>
          </div>
          <div class="resource-grid">
{cards}
          </div>
        </section>"""
        )
    body = f"""    <main>
      <section class="resource-hero" aria-labelledby="resources-title">
        <div class="resource-shell">
          <p class="resource-kicker">DIVD.WORKS / RESOURCES</p>
          <h1 id="resources-title">Practical guidance for the path into IT.</h1>
          <p class="resource-hero__copy">{esc(description)}</p>
          <p class="resource-hero__note">These guides separate practical advice from measured outcomes. They do not promise eligibility, placement, employment, or a particular result.</p>
        </div>
      </section>
{chr(10).join(groups)}
    </main>"""
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "DIVD.Works resources",
        "description": description,
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": "DIVD.Works", "url": SITE_URL},
    }
    return document(
        title="Resources | DIVD.Works",
        description=description,
        canonical=canonical,
        body=body,
        schemas=[schema],
    )


def resource_sitemap_paths(resources: list[dict[str, Any]]) -> list[str]:
    return [
        "/resources/",
        *[f"/resources/{audience.lower()}/" for audience in ("Students", "Employers", "Schools")],
        *[f"/resources/{item['slug']}/" for item in resources],
    ]


def update_sitemap(source: str, paths: list[str]) -> str:
    lines = source.splitlines(keepends=True)
    lines = [
        line
        for line in lines
        if not ("<url><loc>" in line and "resources/" in line)
    ]
    marker = '  <url><loc>https://divd.works/newsroom/</loc></url>\n'
    additions = "".join(
        f"  <url><loc>{SITE_URL}{path}</loc></url>\n"
        for path in sorted(paths)
    )
    if marker not in lines:
        raise ValueError("sitemap.xml is missing the canonical /newsroom/ route")
    index = lines.index(marker) + 1
    lines[index:index] = [additions]
    return "".join(lines)


def audience_page(audience: str, resources: list[dict[str, Any]]) -> str:
    matching = [item for item in resources if item["audience"] == audience]
    label = audience.lower()
    title = f"Resources for {label} | DIVD.Works"
    description = f"Practical DIVD.Works guidance for {label} planning internships, projects, supervision, and progression."
    canonical = f"{SITE_URL}/resources/{label}/"
    cards = "\n".join(resource_card(item) for item in matching)
    body = f"""    <main>
      <section class="resource-hero resource-hero--compact" aria-labelledby="audience-title">
        <div class="resource-shell">
          {breadcrumbs([("Resources", "/resources/"), (audience, f"/resources/{label}/")])}
          <p class="resource-kicker">{audience.upper()} / GUIDES</p>
          <h1 id="audience-title">Resources for {esc(label)}.</h1>
          <p class="resource-hero__copy">{esc(description)}</p>
        </div>
      </section>
      <section class="resource-list" aria-labelledby="resource-list-title">
        <div class="resource-shell">
          <div class="resource-list__heading">
            <p class="resource-kicker">CURRENT GUIDES</p>
            <h2 id="resource-list-title">{len(matching)} practical {label} guides</h2>
          </div>
          <div class="resource-grid">
{cards}
          </div>
        </div>
      </section>
    </main>"""
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": "DIVD.Works", "url": SITE_URL},
    }
    crumb_schema = breadcrumb_data(
        [("Resources", "/resources/"), (audience, f"/resources/{label}/")]
    )
    return document(
        title=title,
        description=description,
        canonical=canonical,
        body=body,
        schemas=[schema, crumb_schema],
    )


def resource_page(resource: dict[str, Any]) -> str:
    canonical = resource_url(resource)
    audience = resource["audience"]
    label = audience.lower()
    sections = []
    for section in resource["sections"]:
        bullets = "".join(f"<li>{esc(item)}</li>" for item in section.get("bullets", []))
        sections.append(
            f"""          <section class="resource-article__section">
            <h2>{esc(section["title"])}</h2>
{''.join(f'            <p>{esc(paragraph)}</p>\\n' for paragraph in section["paragraphs"])}            <ul>{bullets}</ul>
          </section>"""
        )
    context_links = "\n".join(
        f'              <a href="{esc(item["href"])}">{esc(item["label"])} <span aria-hidden="true">→</span></a>'
        for item in resource["source_context"]
    )
    related_links = "\n".join(
        f'              <a href="{esc(item["href"])}">{esc(item["label"])} <span aria-hidden="true">→</span></a>'
        for item in resource["related"]
    )
    body = f"""    <main>
      <article class="resource-article resource-shell">
        {breadcrumbs([("Resources", "/resources/"), (audience, audience_path(audience)), (resource["title"], canonical.replace(SITE_URL, ""))])}
        <header class="resource-article__header">
          <p class="resource-kicker">{esc(resource["kicker"])}</p>
          <h1>{esc(resource["title"])}</h1>
          <p class="resource-article__intro">{esc(resource["intro"])}</p>
          <p class="resource-article__meta">For {esc(label)} · Practical guidance · Updated 21 September 2026</p>
        </header>
        <div class="resource-article__layout">
          <div class="resource-article__body">
{chr(10).join(sections)}
            <div class="resource-article__cta">
              <p class="resource-kicker">NEXT STEP</p>
              <h2>Keep moving with DIVD.Works.</h2>
              <a class="button" href="{esc(resource["next_action"]["href"])}">{esc(resource["next_action"]["label"])} <span aria-hidden="true">→</span></a>
            </div>
          </div>
          <aside class="resource-article__aside">
            <div>
              <p class="resource-kicker">USEFUL CONTEXT</p>
{context_links}
            </div>
            <div>
              <p class="resource-kicker">RELATED GUIDES</p>
{related_links}
            </div>
          </aside>
        </div>
        <p class="resource-article__disclaimer">This guide is general information, not a promise of eligibility, placement, employment, or a specific outcome. Confirm the details for your programme, organisation, and opportunity directly.</p>
      </article>
    </main>"""
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": resource["title"],
        "description": resource["description"],
        "url": canonical,
        "dateModified": "2026-09-21",
        "isAccessibleForFree": True,
        "author": {"@type": "Organization", "name": "DIVD.Works", "url": SITE_URL},
        "publisher": {"@type": "Organization", "name": "DIVD.Works", "url": SITE_URL},
        "articleSection": audience,
    }
    crumb_schema = breadcrumb_data(
        [
            ("Resources", "/resources/"),
            (audience, audience_path(audience)),
            (resource["title"], canonical.replace(SITE_URL, "")),
        ]
    )
    return document(
        title=f"{resource['title']} | DIVD.Works",
        description=resource["description"],
        canonical=canonical,
        body=body,
        schemas=[schema, crumb_schema],
    )


def expected_outputs(data: dict[str, Any]) -> dict[Path, str]:
    resources = data["resources"]
    output: dict[Path, str] = {
        RESOURCE_ROOT / "index.html": index_page(resources),
    }
    for audience in ("Students", "Employers", "Schools"):
        output[RESOURCE_ROOT / audience.lower() / "index.html"] = audience_page(audience, resources)
    for resource in resources:
        output[resource_path(resource)] = resource_page(resource)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    outputs = expected_outputs(data)
    sitemap = ROOT / "sitemap.xml"
    expected_sitemap = update_sitemap(
        sitemap.read_text(encoding="utf-8"),
        resource_sitemap_paths(data["resources"]),
    )
    stale = []
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if args.check:
        if sitemap.read_text(encoding="utf-8") != expected_sitemap:
            stale.append("sitemap.xml")
    else:
        sitemap.write_text(expected_sitemap, encoding="utf-8")
    if stale:
        print("Stale resource output:", ", ".join(stale), file=sys.stderr)
        return 1
    if not args.check:
        print(f"Generated {len(outputs)} resource files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
