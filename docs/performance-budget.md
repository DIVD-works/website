# Static-site performance budget

The budget is intentionally small enough to run without a hosted CI service.
`python scripts/check_performance.py` is the local regression check.

## Budgets

| Asset class | Maximum per file |
| --- | ---: |
| HTML | 150 KiB |
| CSS | 100 KiB |
| JavaScript | 100 KiB |
| Raster/SVG image | 600 KiB |

The check covers core HTML routes and every checked-in CSS, JavaScript, and
image asset. Video and font assets are excluded from the per-file image budget;
they need a separate media review before any new large asset is added.

The check is a release gate for this static repository. A future CI workflow
can call the same script once GitHub Actions permissions are available.
