# Job indexing notifications

**Decision:** do not add an unsupported indexing API or submit URLs from the
static site at publish time.

The current site has no server-side publish event, authentication for a search
engine API, or monitored notification endpoint. The supported baseline is:

1. publish active opportunities as crawlable canonical detail pages;
2. include active opportunities in `sitemap.xml`;
3. remove expired opportunities from the sitemap and active index;
4. keep expired detail pages `noindex,follow`;
5. inspect Search Console coverage after a release.

`scripts/build_jobs.py` makes steps 1–4 deterministic. A future notification
integration needs an owner-approved account, endpoint, credentials, retry
policy, and failure monitoring before it can be implemented safely.
