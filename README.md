# website

## Local checks

Run the static route, metadata, sitemap, robots, and jobs-filter checks with:

```bash
python -m unittest discover -s tests -v
```

The jobs board filters are intentionally client-side, so filtering does not
create parameterized URLs or additional crawlable pages.
