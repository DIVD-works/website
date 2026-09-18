# DIVD.Works website

This is a static site published from the `main` branch.

## Local checks

Run the static route, metadata, sitemap, robots, jobs-filter, homepage-copy,
legal-link, and shared-navigation checks with:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

The jobs board filters are intentionally client-side, so filtering does not
create parameterized URLs or additional crawlable pages.
