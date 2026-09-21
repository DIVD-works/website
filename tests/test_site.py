import functools
import html as html_module
import http.server
import json
import pathlib
import subprocess
import threading
import unittest
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import re
import csv


ROOT = pathlib.Path(__file__).resolve().parents[1]
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
CORE_ROUTES = [
    "/",
    "/about/",
    "/accessibility/",
    "/businesses/",
    "/company-information/",
    "/de/",
    "/es/",
    "/fr/",
    "/help/",
    "/jobs/",
    "/join/",
    "/nl/",
    "/privacy/policy/",
    "/programs/",
    "/projects/",
    "/safety/",
    "/students/",
    "/sustainability/",
    "/terms/",
    "/newsroom/",
    "/newsroom/p/loek-ota-chief-operating-officer/",
    "/newsroom/p/new-chief-creative-officer/",
    "/newsroom/p/divdworks-is-now-live/",
    "/resources/",
    "/resources/students/",
    "/resources/employers/",
    "/resources/schools/",
    "/students/opportunities/internships/",
    "/students/opportunities/graduation-projects/",
    "/students/opportunities/real-world-projects/",
    "/students/opportunities/early-career/",
]


def resource_paths(source):
    return [
        "/resources/",
        *[f"/resources/{audience.lower()}/" for audience in ("Students", "Employers", "Schools")],
        *[f"/resources/{item['slug']}/" for item in source["resources"]],
    ]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class SiteChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    @classmethod
    def fetch(cls, path):
        with urllib.request.urlopen(cls.base_url + path) as response:
            return response.status, response.read()

    def test_core_routes_return_success(self):
        for route in CORE_ROUTES:
            with self.subTest(route=route):
                self.assertEqual(self.fetch(route)[0], 200)

    def test_core_pages_have_one_h1_and_metadata(self):
        for route in CORE_ROUTES:
            with self.subTest(route=route):
                _, body = self.fetch(route)
                html = body.decode("utf-8")
                self.assertEqual(html.lower().count("<h1"), 1)
                self.assertIn("<title>", html.lower())
                self.assertIn('name="description"', html.lower())
                self.assertIn('rel="canonical"', html.lower())

    def test_robots_references_sitemap(self):
        status, body = self.fetch("/robots.txt")
        self.assertEqual(status, 200)
        robots = body.decode("utf-8")
        self.assertIn("User-agent: *", robots)
        self.assertIn("Sitemap: https://divd.works/sitemap.xml", robots)
        self.assertIn("Disallow: /join/confirmation/", robots)

    def test_sitemap_contains_only_successful_canonical_routes(self):
        status, body = self.fetch("/sitemap.xml")
        self.assertEqual(status, 200)
        root = ET.fromstring(body)
        locations = [
            node.text
            for node in root.findall("sm:url/sm:loc", SITEMAP_NS)
        ]
        self.assertEqual(len(locations), len(set(locations)))
        self.assertNotIn("https://divd.works/join/confirmation/", locations)

        for location in locations:
            parsed = urllib.parse.urlparse(location)
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "divd.works")
            self.assertFalse(parsed.query)
            with self.subTest(location=location):
                self.assertEqual(self.fetch(parsed.path)[0], 200)

    def test_jobs_build_is_deterministic_and_crawlable(self):
        result = subprocess.run(
            ["python", "scripts/build_jobs.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        jobs = json.loads((ROOT / "data" / "jobs.json").read_text(encoding="utf-8"))
        active_jobs = [job for job in jobs if job["status"] == "active"]
        index = (ROOT / "jobs" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(index.count("class=\"job-card\""), len(active_jobs))

        for job in jobs:
            path = ROOT / "jobs" / job["slug"] / "index.html"
            self.assertTrue(path.is_file())
            html = path.read_text(encoding="utf-8")
            canonical = f'https://divd.works/jobs/{job["slug"]}/'
            self.assertIn(f'<link rel="canonical" href="{canonical}"', html)
            self.assertIn(job["title"], html)
            self.assertNotIn("example.com", html)
            if job["status"] == "active":
                self.assertIn('"@type":"JobPosting"', html)
                self.assertNotIn('name="robots" content="noindex', html)
            else:
                self.assertNotIn('"@type":"JobPosting"', html)
                self.assertIn('name="robots" content="noindex,follow"', html)

        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        for job in active_jobs:
            self.assertIn(f"https://divd.works/jobs/{job['slug']}/", sitemap)

        for slug in ("internships", "graduation-projects", "real-world-projects", "early-career"):
            pathway = ROOT / "students" / "opportunities" / slug / "index.html"
            self.assertTrue(pathway.is_file())
            self.assertIn('"@type":"BreadcrumbList"', pathway.read_text(encoding="utf-8"))

    def test_jobs_index_has_server_rendered_links_and_no_placeholder_apply_urls(self):
        index = (ROOT / "jobs" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("Loading vacancies", index)
        self.assertNotIn("example.com", index)
        jobs = json.loads((ROOT / "data" / "jobs.json").read_text(encoding="utf-8"))
        for job in jobs:
            if job["status"] == "active":
                self.assertIn(f'href="/jobs/{job["slug"]}/"', index)

    def test_canonical_host_is_used_for_site_metadata_and_absolute_links(self):
        self.assertEqual((ROOT / "CNAME").read_text(encoding="utf-8").strip(), "divd.works")

        html_files = [
            html_file
            for html_file in ROOT.rglob("*.html")
            if ".worktrees" not in html_file.parts
        ]
        for html_file in html_files:
            with self.subTest(page=html_file.relative_to(ROOT)):
                html = html_file.read_text(encoding="utf-8")
                canonicals = re.findall(
                    r'<link\s+rel="canonical"\s+href="([^"]+)"',
                    html,
                    flags=re.IGNORECASE,
                )
                for canonical in canonicals:
                    parsed = urllib.parse.urlparse(canonical)
                    self.assertEqual(parsed.scheme, "https")
                    self.assertEqual(parsed.netloc, "divd.works")

                for href in re.findall(r'href="(https?://[^"]+)"', html):
                    parsed = urllib.parse.urlparse(href)
                    if parsed.netloc in {"divd.works", "www.divd.works", "my.divd.works"}:
                        self.assertEqual(parsed.netloc, "divd.works")

    def test_org_chart_has_no_vacant_positions_or_duplicate_ids(self):
        with (ROOT / "data" / "org-chart.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))

        ids = [row["id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        for row in rows:
            rendered_label = " ".join(
                [row["name"], row["lastName"], row["position"]]
            ).lower()
            self.assertNotIn("vacant", rendered_label)

    def test_company_information_contact_channels_are_current(self):
        html = (ROOT / "company-information" / "index.html").read_text(encoding="utf-8")
        contact_block = re.search(r"<h2>Contact</h2>(.*?)</section>", html, flags=re.DOTALL)
        self.assertIsNotNone(contact_block)
        block = contact_block.group(1)
        self.assertIn('mailto:hello@divd.works', block)
        self.assertIn('mailto:privacy@divd.works', block)
        self.assertIn('mailto:safety@divd.works', block)

    def test_newsroom_build_is_deterministic_and_source_backed(self):
        source = json.loads((ROOT / "data" / "newsroom.json").read_text(encoding="utf-8"))
        result = subprocess.run(
            ["python", "scripts/build_newsroom.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(source["articles"]), 3)

        for article in source["articles"]:
            path = ROOT / "newsroom" / "p" / article["slug"] / "index.html"
            html = path.read_text(encoding="utf-8")
            self.assertIn(f'<link rel="canonical" href="https://divd.works/newsroom/p/{article["slug"]}/"', html)
            self.assertIn('"@type":"NewsArticle"', html)
            self.assertIn(article["publishedISO"], html)
            source_url = article.get("legacyUrl") or article.get("sourceUrl")
            self.assertIn(source_url, html)
            if article.get("legacyUrl"):
                self.assertIn("Migrated from the former DIVD.works newsroom.", html)
            else:
                self.assertIn(html_module.escape(article["sourceLabel"]), html)
                self.assertNotIn("Migrated from the former DIVD.works newsroom.", html)

    def test_newsroom_feed_contains_all_articles_and_no_subscriber_form(self):
        status, body = self.fetch("/newsroom/feed.xml")
        self.assertEqual(status, 200)
        feed = body.decode("utf-8")
        self.assertIn("<rss version=\"2.0\"", feed)
        source = json.loads((ROOT / "data" / "newsroom.json").read_text(encoding="utf-8"))
        self.assertEqual(feed.count("<item>"), len(source["articles"]))
        for article in source["articles"]:
            self.assertIn(article["slug"], feed)
        index = self.fetch("/newsroom/")[1].decode("utf-8")
        self.assertNotIn("<form", index.lower())
        self.assertNotIn("subscribe", index.lower())

    def test_jobs_filter_script_has_no_stale_selector(self):
        script = (ROOT / "js" / "jobs.js").read_text(encoding="utf-8")
        self.assertNotIn("skillFilter", script)
        self.assertIn("skillToggle", script)
        self.assertIn("addEventListener('change', render)", script)

    def test_generated_resource_pages_are_source_backed_and_crawlable(self):
        source = json.loads((ROOT / "data" / "resources.json").read_text(encoding="utf-8"))
        result = subprocess.run(
            ["python", "scripts/build_resources.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(source["resources"]), 9)
        for resource in source["resources"]:
            path = ROOT / "resources" / resource["slug"] / "index.html"
            self.assertTrue(path.is_file())
            html = path.read_text(encoding="utf-8")
            self.assertIn(resource["title"], html)
            self.assertIn('name="description"', html)
            self.assertIn('property="og:url"', html)
            self.assertIn('"@type":"BreadcrumbList"', html)
            self.assertIn(resource["next_action"]["href"], html)
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        for resource in resource_paths(source):
            self.assertIn(f"https://divd.works{resource}", sitemap)

    def test_shared_navigation_handler_is_loaded_once_per_page(self):
        pages = [
            html_file
            for html_file in ROOT.rglob("*.html")
            if 'class="nav-toggle"' in html_file.read_text(encoding="utf-8")
        ]
        for html_file in pages:
            with self.subTest(page=html_file.relative_to(ROOT)):
                html = html_file.read_text(encoding="utf-8")
                self.assertEqual(html.count('/js/nav.js'), 1)
                self.assertNotIn("js/menu.js", html)
                self.assertNotIn("const toggle = document.querySelector('.nav-toggle')", html)

    def test_primary_navigation_links_to_newsroom(self):
        pages = [
            html_file
            for html_file in ROOT.rglob("*.html")
            if 'class="nav-toggle"' in html_file.read_text(encoding="utf-8")
        ]
        for html_file in pages:
            with self.subTest(page=html_file.relative_to(ROOT)):
                html = html_file.read_text(encoding="utf-8")
                self.assertIn('href="/newsroom/"', html)

    def test_legal_links_use_canonical_trailing_slash_routes(self):
        for html_file in ROOT.rglob("*.html"):
            with self.subTest(page=html_file.relative_to(ROOT)):
                html = html_file.read_text(encoding="utf-8")
                for route in ("/privacy/policy", "/accessibility", "/terms"):
                    self.assertNotIn(f'href="{route}"', html)

    def test_shared_navigation_script_is_the_only_page_nav_implementation(self):
        for script_file in (ROOT / "js").glob("*.js"):
            if script_file.name == "nav.js":
                continue
            with self.subTest(script=script_file.name):
                script = script_file.read_text(encoding="utf-8")
                self.assertNotIn("querySelector('.nav-toggle')", script)
                self.assertNotIn("querySelector('#primary-nav')", script)

    def test_homepage_communicates_category_and_audience(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("IT talent", html)
        self.assertIn("students", html.lower())
        self.assertIn("businesses", html.lower())
        self.assertIn("schools", html.lower())
        self.assertIn('href="/jobs/">Find an opportunity', html)

    def test_internal_html_links_resolve(self):
        html_files = ROOT.rglob("*.html")
        routes = {"/": ROOT / "index.html"}
        for html_file in html_files:
            relative = html_file.relative_to(ROOT)
            route = "/" + str(relative.parent).strip("./")
            routes[route.rstrip("/") + "/"] = html_file
            routes[route.rstrip("/")] = html_file
            routes["/" + str(relative)] = html_file

        for html_file in ROOT.rglob("*.html"):
            content = html_file.read_text(encoding="utf-8")
            for href in __import__("re").findall(r'href="([^"]+)"', content):
                if not href.startswith("/") or href.startswith(("//", "/#")):
                    continue
                path = urllib.parse.urlparse(href).path
                candidates = (
                    path,
                    path.rstrip("/") + "/",
                    path.rstrip("/") + "/index.html",
                )
                with self.subTest(source=html_file, href=href):
                    self.assertTrue(
                        any(candidate in routes or (ROOT / candidate.lstrip("/")).is_file()
                            for candidate in candidates)
                    )

    def test_mobile_navigation_is_loaded_on_localized_and_home_pages(self):
        for route in ["/", "/de/", "/es/", "/fr/", "/nl/", "/join/confirmation/"]:
            with self.subTest(route=route):
                _, body = self.fetch(route)
                self.assertIn(b"/js/nav.js", body)


if __name__ == "__main__":
    unittest.main()
