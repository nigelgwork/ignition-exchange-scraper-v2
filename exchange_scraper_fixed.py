# exchange_scraper_fixed.py
import json
import re
import time
import os
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Callable, Optional, Dict, List

# Adelaide timezone
ADELAIDE_TZ = ZoneInfo("Australia/Adelaide")

BASE_URL = "https://inductiveautomation.com/exchange/"
OUTPUT_FILE = Path("all_exchange_resources.json")
DEBUG_DIR = Path("debug_samples")
DEBUG_DIR.mkdir(exist_ok=True)

# Toggle this while debugging. If pages keep timing out, set HEADLESS=False
HEADLESS = True

# Use a modern Chrome user agent to avoid trivial bot detection
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0.0.0 Safari/537.36")

# How many candidate Load more clicks to attempt (increased for full site)
LOAD_MORE_ATTEMPTS = 100

# Timeout values (ms)
NAV_TIMEOUT = 60000
SELECTOR_TIMEOUT = 15000


class ScraperEngine:
    """Main scraper engine with progress callback support"""

    def __init__(self, headless=True, progress_callback: Optional[Callable] = None):
        self.headless = headless
        self.progress_callback = progress_callback
        self.should_stop = False
        self.is_paused = False

    def log(self, message: str, level: str = "info"):
        """Send log message via callback"""
        if self.progress_callback:
            self.progress_callback({
                "type": "log",
                "message": message,
                "level": level,
                "timestamp": datetime.now(ADELAIDE_TZ).isoformat()
            })
        print(message)

    def update_progress(self, current: int, total: int, current_item: str = ""):
        """Update progress via callback"""
        if self.progress_callback:
            self.progress_callback({
                "type": "progress",
                "current": current,
                "total": total,
                "current_item": current_item,
                "timestamp": datetime.now(ADELAIDE_TZ).isoformat()
            })

    def stop(self):
        """Signal scraper to stop"""
        self.should_stop = True
        self.log("Stop requested", "warning")

    def pause(self):
        """Pause scraper"""
        self.is_paused = True
        self.log("Paused", "warning")

    def resume(self):
        """Resume scraper"""
        self.is_paused = False
        self.log("Resumed", "info")

    def check_pause_stop(self):
        """Check if we should pause or stop"""
        while self.is_paused and not self.should_stop:
            time.sleep(1)
        return self.should_stop

    def format_version(self, version_str):
        """Convert version numbers like 100030000 to 1.3.0 format."""
        if not version_str or not str(version_str).isdigit():
            return version_str

        version_num = str(version_str)

        # Handle different version number patterns
        if len(version_num) == 9:  # e.g., 100030000 -> 1.3.0
            major_str = version_num[1:3].lstrip('0') or '1'
            major = int(major_str)
            minor = int(version_num[3:5])
            patch = int(version_num[5:8])
            major = max(1, major)
            return f"{major}.{minor}.{patch}"
        elif len(version_num) == 8:  # e.g., 10003000 -> 1.0.3
            major_str = version_num[0:1] if version_num[0] != '0' else version_num[1:2]
            major = max(1, int(major_str))
            minor = int(version_num[2:4])
            patch = int(version_num[4:7])
            return f"{major}.{minor}.{patch}"
        elif len(version_num) >= 6:
            try:
                if version_num.startswith('100'):
                    major = int(version_num[1:3].lstrip('0') or '1')
                    minor = int(version_num[3:5]) if len(version_num) > 4 else 0
                    patch = int(version_num[5:8]) if len(version_num) > 6 else 0
                else:
                    major = int(version_num[0:1])
                    minor = int(version_num[1:3]) if len(version_num) > 2 else 0
                    patch = int(version_num[3:6]) if len(version_num) > 4 else 0
                major = max(1, major)
                return f"{major}.{minor}.{patch}"
            except:
                return version_str

        try:
            if version_num.isdigit() and int(version_num) == 0:
                return "1.0.0"
            elif version_num.isdigit():
                return str(max(1, int(version_num)))
        except:
            pass

        return version_str

    def find_in_json(self, obj, key_substrings):
        """Yield values from nested JSON where the key contains any substring."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                kl = k.lower()
                if any(sub in kl for sub in key_substrings):
                    yield v
                yield from self.find_in_json(v, key_substrings)
        elif isinstance(obj, list):
            for item in obj:
                yield from self.find_in_json(item, key_substrings)

    def extract_from_json_matches(self, json_matches):
        """Try to pull title/developer_id/version/updated_date/tagline/contributor from captured JSON responses."""
        keys_title = ["title", "name", "resource_title"]
        keys_dev = ["author", "developer", "owner", "contributor", "created_by", "user"]
        keys_ver = ["version", "latest", "latest_release", "release"]
        keys_updated = ["updated", "modified", "last_updated", "updated_at", "modified_at"]
        keys_tagline = ["tagline", "summary", "brief", "subtitle", "short_description"]
        keys_contributor = ["contributor", "contributor_name", "author_name", "developer_name", "username", "display_name"]

        title = developer_id = version = updated_date = tagline = contributor = None

        for m in json_matches:
            j = m.get("json")
            if not j:
                continue

            if title is None:
                for val in self.find_in_json(j, keys_title):
                    if isinstance(val, str) and val.strip():
                        title = val.strip()
                        break
            if developer_id is None:
                for val in self.find_in_json(j, keys_dev):
                    if isinstance(val, (str, int)) and str(val).strip().isdigit():
                        developer_id = str(val).strip()
                        break
            if version is None:
                for val in self.find_in_json(j, keys_ver):
                    if isinstance(val, (str, int)) and str(val).strip():
                        version = str(val).strip()
                        break
            if updated_date is None:
                for val in self.find_in_json(j, keys_updated):
                    if isinstance(val, str) and val.strip():
                        updated_date = val.strip()
                        break
            if tagline is None:
                for val in self.find_in_json(j, keys_tagline):
                    if isinstance(val, str) and val.strip():
                        tagline = val.strip()
                        break
            if contributor is None:
                for val in self.find_in_json(j, keys_contributor):
                    if isinstance(val, str) and val.strip() and not val.isdigit():
                        contributor = val.strip()
                        break

            if title and developer_id and version and updated_date and tagline and contributor:
                break

        return title, developer_id, version, updated_date, tagline, contributor

    def extract_resource_details(self, context, resource_url, debug_index):
        """Visit a resource page and extract details"""
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        json_matches = []

        def on_response(resp):
            try:
                ct = resp.headers.get("content-type", "")
                url = resp.url
                if "application/json" in ct.lower():
                    if "exchange" in url.lower() or "resource" in url.lower() or "/api/" in url.lower() or "/resources" in url.lower():
                        try:
                            j = resp.json()
                            json_matches.append({"url": url, "json": j})
                        except Exception:
                            try:
                                txt = resp.text()
                                j = json.loads(txt)
                                json_matches.append({"url": url, "json": j})
                            except Exception:
                                pass
            except Exception:
                pass

        page.on("response", on_response)

        try:
            page.goto(resource_url, wait_until="networkidle")
        except Exception as e:
            self.log(f"   Navigation warning: {e}", "warning")

        time.sleep(1.2)

        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        title = None
        developer_id = None
        version = None
        updated_date = None
        tagline = None
        contributor = None

        # Title candidates
        title_candidates = [
            "h1.exchange-resource__title", "h1.page-title", "h1.resource-title", "h1",
            ".resource-header h1", ".exchange-header h1"
        ]
        for sel in title_candidates:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                title = el.get_text(strip=True)
                break

        # Developer ID
        dev_candidates = [
            "a.exchange-resource__author", "div.exchange-resource__author a",
            ".resource-author a", ".byline a", ".author a", ".resource-author"
        ]
        for sel in dev_candidates:
            el = soup.select_one(sel)
            if el:
                href = el.get('href', '')
                id_match = re.search(r'/user/(\d+)', href)
                if id_match:
                    developer_id = id_match.group(1)
                    break
                text = el.get_text(strip=True)
                if text and text.isdigit():
                    developer_id = text
                    break

        # Version
        ver_candidates = [
            "div.exchange-release__version", ".resource-version", ".version",
            ".latest-release", ".release-version"
        ]
        for sel in ver_candidates:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                version = el.get_text(strip=True)
                break

        # Updated date
        date_candidates = [
            ".exchange-resource__updated", ".resource-updated", ".last-updated",
            ".updated-date", "time[datetime]", ".release-date"
        ]
        for sel in date_candidates:
            el = soup.select_one(sel)
            if el:
                datetime_attr = el.get('datetime')
                if datetime_attr:
                    updated_date = datetime_attr
                    break
                text = el.get_text(strip=True)
                if text:
                    updated_date = text
                    break

        # Tagline
        tagline_candidates = [
            ".exchange-resource__tagline", ".resource-tagline", ".resource-summary",
            ".tagline", ".summary", ".description", "meta[name='description']"
        ]
        for sel in tagline_candidates:
            if sel.startswith("meta"):
                el = soup.select_one(sel)
                if el:
                    content = el.get('content', '').strip()
                    if content:
                        tagline = content
                        break
            else:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    tagline = el.get_text(strip=True)
                    break

        # Contributor name
        contributor_candidates = [
            "a.exchange-resource__author", "div.exchange-resource__author a",
            ".resource-author a", ".byline a", ".author a", ".resource-author",
            ".contributor-name", ".author-name"
        ]
        for sel in contributor_candidates:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text and not text.isdigit() and len(text) > 1:
                    contributor = text
                    break

        # Try JSON fallback
        if (not title) or (not developer_id) or (not version) or (not updated_date) or (not tagline) or (not contributor):
            j_title, j_dev_id, j_ver, j_updated, j_tagline, j_contributor = self.extract_from_json_matches(json_matches)
            title = title or j_title
            developer_id = developer_id or j_dev_id
            version = version or j_ver
            updated_date = updated_date or j_updated
            tagline = tagline or j_tagline
            contributor = contributor or j_contributor

        # Format version
        if version:
            version = self.format_version(version)

        # Fallback to page title
        if not title:
            try:
                doc_title = soup.title.string if soup.title else None
                if doc_title:
                    title = doc_title.strip()
            except Exception:
                pass

        res = {
            "url": resource_url,
            "title": title,
            "developer_id": developer_id,
            "version": version,
            "updated_date": updated_date,
            "tagline": tagline,
            "contributor": contributor
        }

        try:
            page.close()
        except Exception:
            pass

        return res

    def scrape_all_resources(self) -> List[Dict]:
        """Scrape all resources from the Exchange"""
        results = []
        self.log("Starting full Exchange scrape...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="en-US",
                viewport={"width": 1280, "height": 900},
            )

            page = context.new_page()
            page.set_default_navigation_timeout(NAV_TIMEOUT)
            page.goto(BASE_URL, wait_until="networkidle")
            time.sleep(2)

            # Handle modal popups
            self.log("Checking for modal popups...")
            try:
                modal_close_selectors = [
                    "button:has-text('Accept')", "button:has-text('OK')",
                    "button:has-text('Continue')", "button:has-text('Close')",
                    "button:has-text('Dismiss')", ".modal button",
                    ".ReactModal__Content button", "[data-testid='close-button']",
                    "[aria-label='Close']", ".close-button", "button[class*='close']"
                ]

                for selector in modal_close_selectors:
                    try:
                        modal_btn = page.query_selector(selector)
                        if modal_btn and modal_btn.is_visible():
                            self.log(f"  Found modal button: {selector}")
                            modal_btn.click()
                            time.sleep(1)
                            break
                    except:
                        continue

                page.keyboard.press("Escape")
                time.sleep(1)
            except Exception as e:
                self.log(f"  Error handling modal: {e}", "warning")

            self.log("Loading all resources by clicking 'Load more'...")
            load_more_count = 0
            consecutive_no_change = 0
            max_no_change = 3

            while load_more_count < LOAD_MORE_ATTEMPTS and consecutive_no_change < max_no_change:
                if self.check_pause_stop():
                    self.log("Scrape stopped by user", "warning")
                    break

                try:
                    current_links = len(page.query_selector_all("a[href*='/exchange/'][href*='/overview']"))

                    btn = None
                    button_selectors = [
                        "button:has-text('Load more')", "button:has-text('Load More')",
                        "button:has-text('Show more')", "button:has-text('Show More')",
                        "button[class*='load']", "button[class*='more']",
                        ".load-more", "#load-more"
                    ]

                    for selector in button_selectors:
                        btn = page.query_selector(selector)
                        if btn and btn.is_visible():
                            break

                    if btn and btn.is_visible() and btn.is_enabled():
                        self.log(f"  Clicking Load more... (attempt {load_more_count + 1}, current resources: {current_links})")

                        btn.scroll_into_view_if_needed()
                        time.sleep(0.5)

                        try:
                            btn.click(timeout=5000)
                        except:
                            try:
                                btn.click(force=True, timeout=5000)
                            except:
                                pass

                        time.sleep(3)

                        new_links = len(page.query_selector_all("a[href*='/exchange/'][href*='/overview']"))

                        if new_links > current_links:
                            self.log(f"    Loaded {new_links - current_links} new resources (total: {new_links})")
                            consecutive_no_change = 0
                        else:
                            consecutive_no_change += 1
                            self.log(f"    No new resources loaded (attempt {consecutive_no_change}/{max_no_change})")

                        load_more_count += 1

                        if new_links > 400:
                            time.sleep(2)
                    else:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(2)

                        after_scroll_links = len(page.query_selector_all("a[href*='/exchange/'][href*='/overview']"))
                        if after_scroll_links > current_links:
                            consecutive_no_change = 0
                            continue
                        else:
                            consecutive_no_change += 1
                            if consecutive_no_change >= max_no_change:
                                break

                except Exception as e:
                    self.log(f"  Error during loading: {e}", "error")
                    consecutive_no_change += 1
                    if consecutive_no_change >= max_no_change:
                        break
                    time.sleep(2)

            total_loaded = len(page.query_selector_all("a[href*='/exchange/'][href*='/overview']"))
            self.log(f"Finished loading. Total resources found: {total_loaded}")

            # Collect resource links
            resource_links = []
            for a in page.query_selector_all("a[href*='/exchange/']"):
                href = a.get_attribute("href") or ""
                if re.match(r"^/exchange/\d+/overview$", href):
                    full = "https://inductiveautomation.com" + href
                    resource_links.append(full)

            resource_links = list(dict.fromkeys(resource_links))
            self.log(f"Found {len(resource_links)} total resources to scrape")
            self.update_progress(0, len(resource_links), "Starting...")

            # Scrape each resource
            for idx, url in enumerate(resource_links, start=1):
                if self.check_pause_stop():
                    self.log("Scrape stopped by user", "warning")
                    break

                try:
                    r = self.extract_resource_details(context, url, debug_index=idx)
                    results.append(r)

                    title = r.get('title', 'Unknown')
                    version = r.get('version', '')
                    self.log(f"✓ Scraped: {title} (v{version})")
                    self.update_progress(idx, len(resource_links), title)

                    time.sleep(0.5)

                except Exception as e:
                    self.log(f"  ERROR scraping {url}: {e}", "error")

            try:
                page.close()
            except Exception:
                pass
            context.close()
            browser.close()

        return results


# Standalone function for backward compatibility
def scrape_all_resources():
    """Scrape all resources (backward compatible)"""
    engine = ScraperEngine()
    return engine.scrape_all_resources()


if __name__ == "__main__":
    import sys

    print("Starting full Exchange scrape (all resources)...")
    print("This may take several hours depending on the number of resources.")
    print()

    out = scrape_all_resources()
    print()
    print("="*50)
    print("SCRAPING COMPLETE!")
    print("="*50)
    print(f"Total resources scraped: {len(out)}")

    OUTPUT_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Results saved to: {OUTPUT_FILE.absolute()}")
