#!/usr/bin/env python3
"""Render deterministic, crawlable job pages from the reviewable job records."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "jobs.json"
INDEX = ROOT / "jobs" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
SITE_URL = "https://divd.works"
START_MARKER = "<!-- JOBS:GENERATED_CARDS_START -->"
END_MARKER = "<!-- JOBS:GENERATED_CARDS_END -->"


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
  </footer>"""


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
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="{esc(job['title'])} at {esc(job['partner'])} — {esc(job['type'])} opportunity with DIVD.Works." />
    <title>{esc(job['title'])} | DIVD.Works Jobs</title>
    <link rel="stylesheet" href="/css/styles.css" />
    <link rel="canonical" href="{canonical}" />
{robots}{schema_script}  </head>
  <body>
{header()}
    <main class="job-detail-page">
      <section class="job-detail-hero" aria-labelledby="job-title">
        <div class="narrow">
          <a class="job-detail__back" href="/jobs/">&#8592; All opportunities</a>
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
    <script src="/js/nav.js"></script>
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
        sitemap_expected = render_sitemap(SITEMAP.read_text(encoding="utf-8"), jobs)
        mismatches: list[str] = []
        if not write_or_check(INDEX, index_expected, check):
            mismatches.append(str(INDEX.relative_to(ROOT)))
        if not write_or_check(SITEMAP, sitemap_expected, check):
            mismatches.append(str(SITEMAP.relative_to(ROOT)))
        for job in jobs:
            path = ROOT / "jobs" / job["slug"] / "index.html"
            if not write_or_check(path, page(job), check):
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
