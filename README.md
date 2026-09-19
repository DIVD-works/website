# DIVD.Works website

This is a static site published from the `main` branch.

## Local checks

Run the static route, metadata, sitemap, robots, jobs-filter, homepage-copy,
legal-link, and shared-navigation checks with:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

The first-party newsroom is generated from the reviewable source record in
`data/newsroom.json`:

```bash
python scripts/build_newsroom.py
python scripts/build_newsroom.py --check
```

The generator creates the newsroom index, migrated article pages, and RSS feed
without a runtime or hosted CMS dependency.

The jobs board filters are intentionally client-side, so filtering does not
create parameterized URLs or additional crawlable pages.
