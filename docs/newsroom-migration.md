# DIVD.Works newsroom migration

The first-party newsroom is the canonical editorial surface for new DIVD.Works
stories. The source record lives in `data/newsroom.json`; generated HTML and RSS
are produced by `python scripts/build_newsroom.py`.

Migrated stories retain a `legacyUrl`; new source-derived stories use `sourceUrl`
and `sourceLabel` so the provenance shown on each article remains explicit.

## Migration inventory

The public Substack archive was checked on 2026-09-19. It exposed two public
posts through the homepage/archive at that time; both are migrated into the
first-party source record and rendered as static pages:

- `New Chief Creative Officer` — published 17 April 2025
- `DIVD.works is now live.` — published 4 April 2025

The first new story derived from a public LinkedIn announcement is:

- `Loek Ota steps into role as Chief Operating Officer` — published 20 March 2026

The two public hero images were copied into `img/newsroom/` from the image URLs
served by the original posts. Before production release, Loek/management must
confirm authorship, image permissions, copy approval, and any required
corrections. Every article retains a visible link to the source it was derived
from.

## URL map

| Former Substack URL | First-party URL | Status |
| --- | --- | --- |
| `https://newsroom.divd.works/p/new-chief-creative-officer` | `/newsroom/p/new-chief-creative-officer/` | Migrated; original publication date preserved |
| `https://newsroom.divd.works/p/divdworks-is-now-live` | `/newsroom/p/divdworks-is-now-live/` | Migrated; original publication date preserved |
| LinkedIn activity `7472274999538786304` | `/newsroom/p/loek-ota-chief-operating-officer/` | Source-derived; publication date set to 20 March 2026 |

The former Substack publication and DNS are intentionally unchanged by this
repository change. Retirement, redirects, or any external publication require a
separate approved release step.

The migration is website-first: no newsletter, email automation, subscriber-list
export, or subscriber migration is part of the newsroom.
