#!/usr/bin/env python3
"""Render deterministic, crawlable job pages from the reviewable job records."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "jobs.json"
INDEX = ROOT / "jobs" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
SITE_URL = "https://divd.works"
START_MARKER = "<!-- JOBS:GENERATED_CARDS_START -->"
END_MARKER = "<!-- JOBS:GENERATED_CARDS_END -->"
SOCIAL_IMAGE = f"{SITE_URL}/img/stock/divd-works.png"

# These pages are deliberately allow-listed. A new city or skill should not
# become an indexed page merely because one record happens to mention it.
LOCATION_PAGE_ALLOWLIST = {
    "amsterdam",
    "remote-eu",
    "utrecht",
}
SKILL_PAGE_ALLOWLIST = {
    "burp-suite",
    "cloud",
    "linux",
    "machine-learning",
    "networking",
    "osint",
    "prompt-security",
    "python",
    "research",
    "web-security",
}
SKILL_PAGE_MINIMUM_JOBS = 2

LOCATION_PAGE_DETAILS = {
    "amsterdam": {
        "label": "Amsterdam",
        "intro": "Browse active DIVD.Works opportunities listed in Amsterdam or with an Amsterdam hybrid arrangement.",
        "context": "The page is generated only while the public inventory contains an active Amsterdam opportunity. It is not a promise that new roles will always be available.",
    },
    "remote-eu": {
        "label": "Remote in the EU",
        "intro": "Browse active DIVD.Works opportunities that explicitly mention a remote EU arrangement.",
        "context": "Remote eligibility, time-zone expectations, and any in-person requirements are set per opportunity.",
    },
    "utrecht": {
        "label": "Utrecht",
        "intro": "Browse active DIVD.Works opportunities listed in Utrecht or with a Utrecht hybrid arrangement.",
        "context": "The page is generated only while the public inventory contains an active Utrecht opportunity. It is not a promise that new roles will always be available.",
    },
}

STUDENT_PATHWAYS = {
    "internships": {
        "label": "Internships",
        "title": "Internships for students",
        "intro": "A practical route into real IT work while you are still studying.",
        "context": "Compare the current internship listings with your programme requirements, timing, location, language, and supervision needs.",
        "pathway_note": "Check the live listing for its own requirements, then compare the Talent Program tiers if you want broader coaching context.",
        "matches": lambda job: job["type"] == "Internship",
        "fallback": "/jobs/",
        "fallback_label": "Browse all opportunities",
    },
    "graduation-projects": {
        "label": "Graduation projects",
        "title": "Graduation projects and thesis work",
        "intro": "A route for students looking for a defined graduation or thesis project in the public opportunity inventory.",
        "context": "A public thesis listing is a starting point, not a substitute for confirming your school’s assessment, supervision, and approval requirements.",
        "pathway_note": "Confirm the project and supervision fit with your school before proceeding; the Talent Program comparison is a separate orientation route.",
        "matches": lambda job: job["type"] == "Thesis",
        "fallback": "/jobs/",
        "fallback_label": "Browse all opportunities",
    },
    "real-world-projects": {
        "label": "Real-world projects",
        "title": "Real-world IT projects",
        "intro": "Explore practical project work and published examples that connect learning with real organisational needs.",
        "context": "The public jobs inventory does not currently label a dedicated project opening. Explore the project portfolio and browse the live opportunities for the current offer.",
        "pathway_note": "Project scope and access are agreed per project. Compare the Talent Program tiers for the broader support model.",
        "matches": lambda job: False,
        "fallback": "/projects/",
        "fallback_label": "Explore published projects",
    },
    "early-career": {
        "label": "Early-career opportunities",
        "title": "Early-career opportunities",
        "intro": "For graduates and early-career professionals ready to take a next step into practical IT work.",
        "context": "Read each live listing for its own requirements and working arrangement; this page does not promise eligibility or employment.",
        "pathway_note": "Use the live listing as the source of truth for fit, then compare the Talent Program tiers as a separate next step.",
        "matches": lambda job: job["type"] in {"Part-time", "Internship", "Thesis"},
        "fallback": "/jobs/",
        "fallback_label": "Browse all opportunities",
    },
}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def load_jobs() -> list[dict[str, Any]]:
    jobs = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(jobs, list):
        raise ValueError("data/jobs.json must contain a list")

    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    for job in jobs:
        for field in ("id", "slug", "title", "status", "date_posted", "valid_through",
                      "partner", "type", "employment_type", "domain", "location",
                      "language", "skills", "description", "application_status"):
            if field not in job:
                raise ValueError(f"{job.get('id', '<unknown>')} is missing {field}")
        if job["id"] in seen_ids:
            raise ValueError(f"duplicate job id: {job['id']}")
        if job["slug"] in seen_slugs:
            raise ValueError(f"duplicate job slug: {job['slug']}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", job["slug"]):
            raise ValueError(f"invalid job slug: {job['slug']}")
        if job["status"] not in {"active", "expired"}:
            raise ValueError(f"invalid job status for {job['id']}: {job['status']}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", job["date_posted"]):
            raise ValueError(f"invalid date_posted for {job['id']}: {job['date_posted']}")
        if job["valid_through"] is not None and not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", job["valid_through"]
        ):
            raise ValueError(f"invalid valid_through for {job['id']}: {job['valid_through']}")
        if not isinstance(job["skills"], list) or not job["skills"]:
            raise ValueError(f"{job['id']} must have at least one skill")
        if job.get("application_url") and "example.com" in job["application_url"]:
            raise ValueError(f"placeholder application URL remains for {job['id']}")
        seen_ids.add(job["id"])
        seen_slugs.add(job["slug"])
    return jobs


def job_url(job: dict[str, Any]) -> str:
    return f"{SITE_URL}/jobs/{job['slug']}/"


def local_job_url(job: dict[str, Any]) -> str:
    return f"/jobs/{job['slug']}/"


def is_active(job: dict[str, Any]) -> bool:
    return job["status"] == "active"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def location_slug(location: str) -> str:
    normalized = location.lower().replace("(", "").replace(")", "")
    if normalized.startswith("remote"):
        return "remote-eu"
    return slugify(location.split(" / ", 1)[0])


def social_meta(title: str, description: str, canonical: str) -> str:
    return f"""    <meta property="og:type" content="website" />
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
"""


def breadcrumb_data(items: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": name,
                "item": f"{SITE_URL}{path}" if path.startswith("/") else path,
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
    return '<nav class="job-breadcrumbs" aria-label="Breadcrumb">' + " <span aria-hidden=\"true\">/</span> ".join(links) + "</nav>"


def location_json_ld(job: dict[str, Any]) -> dict[str, Any]:
    location = job["location"]
    primary = location.split(" / ", 1)[0].strip()
    if primary.lower().startswith("remote"):
        return {
            "jobLocationType": "TELECOMMUTE",
            "applicantLocationRequirements": {
                "@type": "Country",
                "name": "European Union",
            },
        }
    return {
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": primary,
                "addressCountry": "NL",
            },
        }
    }


def structured_data(job: dict[str, Any]) -> dict[str, Any] | None:
    if not is_active(job):
        return None
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": job["title"],
        "description": job["description"],
        "datePosted": job["date_posted"],
        "employmentType": job["employment_type"],
        "hiringOrganization": {
            "@type": "Organization",
            "name": job["partner"],
        },
        "url": job_url(job),
    }
    data.update(location_json_ld(job))
    if job["valid_through"]:
        data["validThrough"] = job["valid_through"]
    if job.get("application_url"):
        data["directApply"] = True
    return data


def json_ld(value: dict[str, Any] | None) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


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
        <a class="is-active" href="/jobs/">Jobs</a>
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
    return """    <footer class="footer container">
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
          <h3>Programs</h3>
          <a href="/programs/">Starter</a>
          <a href="/programs/">Professional</a>
          <a href="/programs/">Elite</a>
        </div>
        <div>
          <h3>Company</h3>
          <a href="/company-information/">Company information</a>
          <a href="/sustainability/">Sustainability</a>
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


def job_card_link(job: dict[str, Any], *, detail: bool = True) -> str:
    """Render a compact card for generated landing pages."""
    return f"""        <article class="job-card" data-job-id="{esc(job['id'])}">
          <div class="job-card__top">
            <h2><a class="job-card__title-link" href="{local_job_url(job)}">{esc(job['title'])}</a></h2>
            <span class="job-card__type">{esc(job['type'])}</span>
          </div>
          <p class="job-card__partner">{esc(job['partner'])}</p>
          <dl class="job-card__details">
            <div><dt>Domain</dt><dd>{esc(job['domain'])}</dd></div>
            <div><dt>Location</dt><dd>{esc(job['location'])}</dd></div>
            <div><dt>Language</dt><dd>{esc(job['language'])}</dd></div>
          </dl>
          <div class="job-card__skills" aria-label="Skills">
            {"".join(f'<span class="job-card__skill">{esc(skill)}</span>' for skill in job["skills"])}
          </div>
          <a class="button button--small" href="{local_job_url(job)}">View opportunity <span aria-hidden="true">&#8594;</span></a>
        </article>"""


def active_jobs_by_location(jobs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for job in jobs:
        if not is_active(job):
            continue
        slug = location_slug(job["location"])
        if slug in LOCATION_PAGE_ALLOWLIST:
            grouped[slug].append(job)
    return grouped


def active_jobs_by_skill(jobs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for job in jobs:
        if not is_active(job):
            continue
        for skill in job["skills"]:
            slug = slugify(skill)
            if slug in SKILL_PAGE_ALLOWLIST:
                grouped[slug][job["id"]] = job
    return {
        slug: list(matching.values())
        for slug, matching in grouped.items()
        if len(matching) >= SKILL_PAGE_MINIMUM_JOBS
    }


def landing_page(
    *,
    kind: str,
    slug: str,
    label: str,
    intro: str,
    context: str,
    jobs: list[dict[str, Any]],
) -> str:
    if kind == "location":
        landing_path = f"/jobs/locations/{slug}/"
        parent_label = "Locations"
        kicker = "JOBS / LOCATION"
    else:
        landing_path = f"/jobs/skills/{slug}/"
        parent_label = "Skills"
        kicker = "JOBS / SKILL"
    canonical = f"{SITE_URL}{landing_path}"
    title = f"{label} opportunities | DIVD.Works Jobs"
    description = f"{intro} See the current public opportunity inventory from DIVD.Works."
    cards = "\n".join(job_card_link(job) for job in jobs)
    crumbs = [("Jobs", "/jobs/"), (parent_label, "/jobs/"), (label, landing_path)]
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": "DIVD.Works", "url": SITE_URL},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(jobs),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "url": job_url(job),
                    "name": job["title"],
                }
                for position, job in enumerate(jobs, start=1)
            ],
        },
    }
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="{esc(description)}" />
    <title>{esc(title)}</title>
    <link rel="stylesheet" href="/css/styles.css" />
    <link rel="canonical" href="{canonical}" />
{social_meta(title, description, canonical)}    <script type="application/ld+json">{json_ld(schema)}</script>
    <script type="application/ld+json">{json_ld(breadcrumb_data(crumbs))}</script>
  </head>
  <body class="job-landing-page">
{header()}
    <main>
      <section class="job-landing-hero" aria-labelledby="landing-title">
        <div class="narrow">
          {breadcrumbs(crumbs)}
          <p class="eyebrow">{kicker}</p>
          <h1 id="landing-title">{esc(label)} opportunities</h1>
          <p class="job-landing-hero__copy">{esc(intro)}</p>
        </div>
      </section>
      <section class="job-landing-content" aria-labelledby="inventory-title">
        <div class="container">
          <div class="job-landing-heading">
            <div>
              <p class="eyebrow">CURRENT INVENTORY</p>
              <h2 id="inventory-title">{len(jobs)} active {'opportunity' if len(jobs) == 1 else 'opportunities'}</h2>
            </div>
            <p>{esc(context)}</p>
          </div>
          <div class="jobs-grid">
{cards}
          </div>
          <p class="job-landing-footnote">Looking for a different path? <a href="/jobs/">Browse all opportunities</a> or <a href="/students/opportunities/">explore student pathways</a>.</p>
        </div>
      </section>
    </main>
{footer()}
  </body>
</html>
"""


def student_pathways_page() -> str:
    title = "Student opportunities by pathway | DIVD.Works"
    description = (
        "A clear starting point for students exploring internships, entry-level roles, "
        "and early-career opportunities with DIVD.Works."
    )
    canonical = f"{SITE_URL}/students/opportunities/"
    crumbs = [("Students", "/students/"), ("Opportunities", "/students/opportunities/")]
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": "DIVD.Works", "url": SITE_URL},
    }
    pathways = [
        (
            "internships",
            "Internships",
            "A practical starting point for students looking for a first placement or a way to build experience.",
            "Check each live listing for its own requirements and application route.",
        ),
        (
            "graduation-projects",
            "Graduation projects",
            "A route for students looking for a defined graduation or thesis project.",
            "Confirm the school’s assessment, supervision, and approval requirements.",
        ),
        (
            "real-world-projects",
            "Real-world projects",
            "Explore project work and published examples that connect learning with real organisational needs.",
            "Project scope, access, and review are agreed for the specific project.",
        ),
        (
            "early-career",
            "Early-career opportunities",
            "For graduates and early-career professionals ready to explore a next step into practical IT work.",
            "Read each live listing for its own requirements and working arrangement.",
        ),
    ]
    cards = "\n".join(
        f"""            <article class="pathway-card">
              <p class="eyebrow">PATHWAY {index:02d}</p>
              <h2>{esc(name)}</h2>
              <p>{esc(summary)}</p>
              <p class="pathway-card__note">{esc(note)}</p>
              <a class="text-link" href="/students/opportunities/{slug}/">Explore this pathway <span aria-hidden="true">→</span></a>
            </article>"""
        for index, (slug, name, summary, note) in enumerate(pathways, start=1)
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="{esc(description)}" />
    <title>{esc(title)}</title>
    <link rel="stylesheet" href="/css/styles.css" />
    <link rel="stylesheet" href="/css/jobs.css" />
    <link rel="canonical" href="{canonical}" />
{social_meta(title, description, canonical)}    <script type="application/ld+json">{json_ld(schema)}</script>
    <script type="application/ld+json">{json_ld(breadcrumb_data(crumbs))}</script>
  </head>
  <body class="job-landing-page">
{header()}
    <main>
      <section class="job-landing-hero" aria-labelledby="pathways-title">
        <div class="narrow">
          {breadcrumbs(crumbs)}
          <p class="eyebrow">STUDENTS / OPPORTUNITIES</p>
          <h1 id="pathways-title">Find your next opportunity.</h1>
          <p class="job-landing-hero__copy">{esc(description)}</p>
        </div>
      </section>
      <section class="job-landing-content" aria-labelledby="pathway-list-title">
        <div class="container">
          <div class="section-heading section-heading--left">
            <p class="eyebrow">CHOOSE A STARTING POINT</p>
            <h2 id="pathway-list-title">Explore by pathway</h2>
            <p>These are orientation routes, not guarantees of eligibility, placement, or employment. Read the live opportunity details for the facts that apply to each role.</p>
          </div>
          <div class="pathway-grid">
{cards}
          </div>
        </div>
      </section>
    </main>
{footer()}
  </body>
</html>
"""


def student_pathway_page(slug: str, jobs: list[dict[str, Any]]) -> str:
    pathway = STUDENT_PATHWAYS[slug]
    matching = [job for job in jobs if is_active(job) and pathway["matches"](job)]
    canonical = f"{SITE_URL}/students/opportunities/{slug}/"
    crumbs = [
        ("Students", "/students/"),
        ("Opportunities", "/students/opportunities/"),
        (pathway["label"], f"/students/opportunities/{slug}/"),
    ]
    title = f"{pathway['title']} | DIVD.Works"
    description = pathway["intro"]
    if matching:
        cards = "\n".join(job_card_link(job) for job in matching)
        inventory = f"{len(matching)} active {'opportunity' if len(matching) == 1 else 'opportunities'}"
    else:
        cards = ""
        inventory = "No dedicated opening is listed right now"
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": "DIVD.Works", "url": SITE_URL},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(matching),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "url": job_url(job),
                    "name": job["title"],
                }
                for position, job in enumerate(matching, start=1)
            ],
        },
    }
    empty = "" if matching else f"""
          <div class="job-pathway-empty">
            <h3>This route is useful even when the inventory is quiet.</h3>
            <p>Read the pathway context, then use the public projects and current jobs pages to decide what to explore next.</p>
            <a class="button button--small" href="{pathway['fallback']}">{pathway['fallback_label']} <span aria-hidden="true">→</span></a>
          </div>"""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="{esc(description)}" />
    <title>{esc(title)}</title>
    <link rel="stylesheet" href="/css/styles.css" />
    <link rel="stylesheet" href="/css/jobs.css" />
    <link rel="canonical" href="{canonical}" />
{social_meta(title, description, canonical)}    <script type="application/ld+json">{json_ld(schema)}</script>
    <script type="application/ld+json">{json_ld(breadcrumb_data(crumbs))}</script>
  </head>
  <body class="job-landing-page">
{header()}
    <main>
      <section class="job-landing-hero" aria-labelledby="pathway-title">
        <div class="narrow">
          {breadcrumbs(crumbs)}
          <p class="eyebrow">STUDENTS / PATHWAY</p>
          <h1 id="pathway-title">{esc(pathway["title"])}</h1>
          <p class="job-landing-hero__copy">{esc(pathway["intro"])}</p>
        </div>
      </section>
      <section class="job-landing-content" aria-labelledby="pathway-inventory-title">
        <div class="container">
          <div class="job-landing-heading">
            <div>
              <p class="eyebrow">CURRENT INVENTORY</p>
              <h2 id="pathway-inventory-title">{esc(inventory)}</h2>
            </div>
            <p>{esc(pathway["context"])}</p>
          </div>
          <div class="jobs-grid">
{cards}
          </div>
{empty}
          <p class="job-landing-footnote">{esc(pathway["pathway_note"])} <a href="/programs/">Compare Talent Program tiers</a>. Need a wider view? <a href="/students/opportunities/">Return to all student pathways</a> or <a href="/resources/students/">read student guidance</a>.</p>
        </div>
      </section>
    </main>
{footer()}
  </body>
</html>
"""


def card(job: dict[str, Any]) -> str:
    skills = "".join(
        f'<button class="job-card__skill" type="button" data-skill="{esc(skill)}" '
        f'aria-pressed="false">{esc(skill)}</button>'
        for skill in job["skills"]
    )
    return f"""          <article class="job-card" data-job-id="{esc(job['id'])}">
            <div class="job-card__top">
              <h3><a class="job-card__title-link" href="{local_job_url(job)}">{esc(job['title'])}</a></h3>
              <span class="job-card__type">{esc(job['type'])}</span>
            </div>
            <p class="job-card__partner">{esc(job['partner'])}</p>
            <dl class="job-card__details">
              <div><dt>Domain</dt><dd>{esc(job['domain'])}</dd></div>
              <div><dt>Location</dt><dd>{esc(job['location'])}</dd></div>
              <div><dt>Language</dt><dd>{esc(job['language'])}</dd></div>
              <div><dt>Stipend</dt><dd>{'Available' if job['stipend'] else 'Not specified'}</dd></div>
            </dl>
            <div class="job-card__skills" aria-label="Skills">{skills}</div>
            <a class="button button--small" href="{local_job_url(job)}">View opportunity <span aria-hidden="true">&#8594;</span></a>
          </article>"""


def render_index(source: str, jobs: list[dict[str, Any]]) -> str:
    active = [job for job in jobs if is_active(job)]
    generated = "\n".join(card(job) for job in active)
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{generated}\n          {END_MARKER}"
    rendered, count = pattern.subn(replacement, source)
    if count != 1:
        raise ValueError("jobs/index.html must contain exactly one generated-card marker block")
    rendered = re.sub(
        r'(<p class="jobs-count" id="jobs-count"[^>]*>).*?(</p>)',
        rf"\g<1>{len(active)} {'vacancy' if len(active) == 1 else 'vacancies'}\g<2>",
        rendered,
        count=1,
    )
    return rendered


def page(job: dict[str, Any]) -> str:
    active = is_active(job)
    robots = "" if active else '    <meta name="robots" content="noindex,follow" />\n'
    schema = json_ld(structured_data(job))
    schema_script = f'    <script type="application/ld+json">{schema}</script>\n' if schema else ""
    status = (
        '<p class="job-detail__status job-detail__status--open">Open opportunity</p>'
        if active
        else '<p class="job-detail__status job-detail__status--closed">This opportunity is no longer open</p>'
    )
    application = (
        f'<a class="button" href="{esc(job["application_url"])}" target="_blank" rel="noopener noreferrer">Apply now <span aria-hidden="true">&#8594;</span></a>'
        if job.get("application_url")
        else '<p class="job-detail__pending">Application destination pending confirmation. Please check back soon.</p>'
    )
    valid_through = (
        f'<div><dt>Application deadline</dt><dd>{esc(job["valid_through"])}</dd></div>'
        if job["valid_through"]
        else ""
    )
    skills = "".join(f'<li>{esc(skill)}</li>' for skill in job["skills"])
    canonical = job_url(job)
    crumbs = [("Jobs", "/jobs/"), (job["title"], local_job_url(job))]
    social = social_meta(
        f"{job['title']} | DIVD.Works Jobs",
        f"{job['title']} at {job['partner']} — {job['type']} opportunity with DIVD.Works.",
        canonical,
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="{esc(job['title'])} at {esc(job['partner'])} — {esc(job['type'])} opportunity with DIVD.Works." />
    <title>{esc(job['title'])} | DIVD.Works Jobs</title>
    <link rel="stylesheet" href="/css/styles.css" />
    <link rel="canonical" href="{canonical}" />
{social}    <script type="application/ld+json">{json_ld(breadcrumb_data(crumbs))}</script>
{robots}{schema_script}  </head>
  <body>
{header()}
    <main class="job-detail-page">
      <section class="job-detail-hero" aria-labelledby="job-title">
        <div class="narrow">
          {breadcrumbs(crumbs)}
          <p class="eyebrow">DIVD.WORKS / OPPORTUNITY</p>
          <h1 id="job-title">{esc(job['title'])}</h1>
          <p class="job-detail__partner">{esc(job['partner'])}</p>
          {status}
        </div>
      </section>
      <section class="job-detail-content" aria-label="Opportunity details">
        <div class="job-detail-content__main">
          <h2>About this opportunity</h2>
          <p>{esc(job['description'])}</p>
          <h2>Skills</h2>
          <ul class="job-detail__skills">{skills}</ul>
        </div>
        <aside class="job-detail-card">
          <h2>At a glance</h2>
          <dl>
            <div><dt>Type</dt><dd>{esc(job['type'])}</dd></div>
            <div><dt>Domain</dt><dd>{esc(job['domain'])}</dd></div>
            <div><dt>Location</dt><dd>{esc(job['location'])}</dd></div>
            <div><dt>Language</dt><dd>{esc(job['language'])}</dd></div>
            <div><dt>Posted</dt><dd>{esc(job['date_posted'])}</dd></div>
            {valid_through}
          </dl>
          <div class="job-detail-card__action">
            {application}
          </div>
        </aside>
      </section>
    </main>
{footer()}
  </body>
</html>
"""


def render_sitemap(source: str, jobs: list[dict[str, Any]]) -> str:
    lines = source.splitlines(keepends=True)
    job_line = re.compile(r"\s*<url><loc>https://divd\.works/jobs/[^<]+/</loc></url>\s*\n?")
    lines = [line for line in lines if not job_line.fullmatch(line)]
    marker = '  <url><loc>https://divd.works/jobs/</loc></url>\n'
    additions = "".join(
        f"  <url><loc>{job_url(job)}</loc></url>\n"
        for job in jobs
        if is_active(job)
    )
    if marker not in lines:
        raise ValueError("sitemap.xml is missing the canonical /jobs/ route")
    index = lines.index(marker) + 1
    lines[index:index] = [additions]
    return "".join(lines)


def generated_landing_outputs(jobs: list[dict[str, Any]]) -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    for slug, matching in active_jobs_by_location(jobs).items():
        details = LOCATION_PAGE_DETAILS[slug]
        outputs[ROOT / "jobs" / "locations" / slug / "index.html"] = landing_page(
            kind="location",
            slug=slug,
            label=details["label"],
            intro=details["intro"],
            context=details["context"],
            jobs=matching,
        )
    for slug, matching in active_jobs_by_skill(jobs).items():
        label = next(
            (skill for job in matching for skill in job["skills"] if slugify(skill) == slug),
            slug.replace("-", " ").title(),
        )
        outputs[ROOT / "jobs" / "skills" / slug / "index.html"] = landing_page(
            kind="skill",
            slug=slug,
            label=label,
            intro=f"Browse active DIVD.Works opportunities where {label} is one of the listed skills.",
            context="Skill pages are created only when the public inventory has enough active opportunities to make a useful hub; thin pages are not indexed.",
            jobs=matching,
        )
    # The student pathway hub is a stable editorial route, unlike the
    # inventory-driven location/skill pages above.
    outputs[ROOT / "students" / "opportunities" / "index.html"] = student_pathways_page()
    for slug in STUDENT_PATHWAYS:
        outputs[ROOT / "students" / "opportunities" / slug / "index.html"] = student_pathway_page(slug, jobs)
    return outputs


def update_sitemap_with_generated_pages(
    source: str,
    generated_paths: list[str],
) -> str:
    lines = source.splitlines(keepends=True)
    generated_markers = (
        "jobs/locations/",
        "jobs/skills/",
        "students/opportunities/",
    )
    lines = [
        line
        for line in lines
        if not (
            "<url><loc>" in line
            and any(marker in line for marker in generated_markers)
        )
    ]
    marker = '  <url><loc>https://divd.works/jobs/</loc></url>\n'
    additions = "".join(
        f"  <url><loc>{SITE_URL}{path if path.startswith('/') else '/' + path}</loc></url>\n"
        for path in sorted(generated_paths)
    )
    if marker not in lines:
        raise ValueError("sitemap.xml is missing the canonical /jobs/ route")
    index = lines.index(marker) + 1
    lines[index:index] = [additions]
    return "".join(lines)


def write_or_check(path: Path, expected: str, check: bool) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if check:
        return current == expected
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected, encoding="utf-8")
    return True


def build(*, check: bool) -> int:
    try:
        jobs = load_jobs()
        index_expected = render_index(INDEX.read_text(encoding="utf-8"), jobs)
        landing_outputs = generated_landing_outputs(jobs)
        generated_paths = [
            "/" + str(path.relative_to(ROOT)).removesuffix("/index.html").lstrip("/") + "/"
            for path in landing_outputs
        ]
        sitemap_expected = update_sitemap_with_generated_pages(
            render_sitemap(SITEMAP.read_text(encoding="utf-8"), jobs),
            generated_paths,
        )
        mismatches: list[str] = []
        if not write_or_check(INDEX, index_expected, check):
            mismatches.append(str(INDEX.relative_to(ROOT)))
        if not write_or_check(SITEMAP, sitemap_expected, check):
            mismatches.append(str(SITEMAP.relative_to(ROOT)))
        for job in jobs:
            path = ROOT / "jobs" / job["slug"] / "index.html"
            if not write_or_check(path, page(job), check):
                mismatches.append(str(path.relative_to(ROOT)))
        for path, content in landing_outputs.items():
            if not write_or_check(path, content, check):
                mismatches.append(str(path.relative_to(ROOT)))
        if mismatches:
            print("Generated jobs output is out of date:", file=sys.stderr)
            print("\n".join(f"- {item}" for item in mismatches), file=sys.stderr)
            return 1
        print(f"{'Checked' if check else 'Built'} {len(jobs)} job records.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"jobs build failed: {error}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated output is stale")
    args = parser.parse_args()
    return build(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
