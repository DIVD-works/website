# DIVD.Works public domain policy

Status checked: 2026-09-20

## Canonical public host

`https://divd.works/` is the canonical public website host. The repository
contract is expressed by:

- `CNAME` containing `divd.works`;
- canonical tags, Open Graph URLs, structured data, robots, and the sitemap
  using `https://divd.works`; and
- internal absolute links using the same host.

The site must not introduce `www.divd.works` or `my.divd.works` as alternate
public content hosts.

## Legacy and subdomain status

- `www.divd.works` currently has no resolving DNS record. No redirect can be
  verified from the public internet.
- `my.divd.works` currently has no resolving DNS record and is offline. It is
  not a live public application surface and must not be added to the sitemap,
  canonical tags, or navigation.

The repository can enforce canonical metadata, sitemap entries, and internal
links. DNS records and HTTP redirects are hosting-provider responsibilities and
cannot be completed by a static GitHub Pages commit alone. Before closing the
legacy-domain backlog, the DNS/hosting owner must configure permanent
path-preserving redirects for any host that is intentionally retained, then
verify there are no redirect chains or loops.

## Verification checklist

1. `https://divd.works/` returns `200`.
2. Every indexable page has a self-canonical URL on `https://divd.works`.
3. The sitemap contains only `https://divd.works` URLs.
4. `www.divd.works` and `my.divd.works` are not linked as public content hosts.
5. Once DNS is configured, test the final status, destination, path, query
   string, and canonical alignment for every retained legacy URL.
