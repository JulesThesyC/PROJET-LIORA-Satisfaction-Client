"""
Scraper Trustpilot (France) — infos entreprises, notes, avis et réponses.

Source : pages publiques fr.trustpilot.com/review/{domain}
Méthode : Playwright + extraction __NEXT_DATA__ (JSON embarqué) + distribution DOM.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)

BASE_URL = "https://fr.trustpilot.com"
REVIEWS_PER_PAGE = 20

STAR_LABELS = {
    "five": ("5", "Excellent"),
    "four": ("4", "Bien"),
    "three": ("3", "Moyen"),
    "two": ("2", "Médiocre"),
    "one": ("1", "Mauvais"),
}


@dataclass
class CompanyInfo:
    company_key: str
    name: str
    domain: str
    theme: str
    profile_url: str
    trustpilot_id: str
    display_name: str
    trust_score: float | None
    stars: float | None
    total_reviews: int
    website_url: str | None
    is_claimed: bool
    country: str | None
    categories: str
    description: str | None
    reply_percentage: float | None
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    pct_5_stars: float | None = None
    pct_4_stars: float | None = None
    pct_3_stars: float | None = None
    pct_2_stars: float | None = None
    pct_1_stars: float | None = None


@dataclass
class ReviewRecord:
    company_key: str
    company_name: str
    domain: str
    review_id: str
    title: str | None
    text: str
    rating: int
    language: str | None
    published_date: str | None
    experienced_date: str | None
    reviewer_name: str | None
    reviewer_country: str | None
    verified: bool
    likes: int
    has_company_reply: bool
    company_reply_text: str | None
    company_reply_date: str | None
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TrustpilotScraper:
    def __init__(self, headless: bool = True, delay_seconds: float = 1.5):
        self.headless = headless
        self.delay_seconds = delay_seconds

    def _page_props(self, page: Page) -> dict[str, Any]:
        page.wait_for_selector(
            "script#__NEXT_DATA__", state="attached", timeout=60000
        )
        raw = page.locator("script#__NEXT_DATA__").inner_text()
        data = json.loads(raw)
        return data["props"]["pageProps"]

    def _extract_distribution(self, page: Page) -> dict[str, float]:
        """Pourcentages par classe d'étoiles (barres de distribution)."""
        rows = page.evaluate(
            """() => {
            const container = document.querySelector('.styles_distributions__3hJ2W');
            if (!container) return [];
            return Array.from(container.querySelectorAll('[data-star-rating]')).map(row => {
                const key = row.getAttribute('data-star-rating');
                const bar = row.querySelector('.rating-distribution-row_barValue__iFje4');
                const style = bar ? bar.getAttribute('style') || '' : '';
                const m = style.match(/width:\\s*([\\d.]+)%/);
                return { key, percent: m ? parseFloat(m[1]) : null };
            });
        }"""
        )
        result: dict[str, float] = {}
        for row in rows:
            key = row.get("key")
            pct = row.get("percent")
            if key and pct is not None:
                result[key] = float(pct)
        return result

    def scrape_company_profile(
        self,
        company_key: str,
        name: str,
        domain: str,
        theme: str,
        slug: str,
    ) -> CompanyInfo:
        profile_url = f"{BASE_URL}/review/{slug}"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page.goto(profile_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(int(self.delay_seconds * 1000))
            props = self._page_props(page)
            distribution = self._extract_distribution(page)
            browser.close()

        bu = props["businessUnit"]
        sidebar = props.get("sidebarData", {}).get("infoBusinessUnitBox", {})
        activity = bu.get("activity") or {}
        reply = activity.get("replyBehavior") or {}
        categories = bu.get("categories") or []
        cat_names = ", ".join(c.get("name", "") for c in categories if c.get("name"))

        dist = distribution
        return CompanyInfo(
            company_key=company_key,
            name=name,
            domain=domain,
            theme=theme,
            profile_url=profile_url,
            trustpilot_id=bu.get("id", ""),
            display_name=bu.get("displayName", name),
            trust_score=bu.get("trustScore"),
            stars=bu.get("stars"),
            total_reviews=int(bu.get("numberOfReviews") or 0),
            website_url=bu.get("websiteUrl"),
            is_claimed=bool(bu.get("isClaimed")),
            country=(bu.get("contactInfo") or {}).get("country"),
            categories=cat_names,
            description=sidebar.get("descriptionTextPlain") or sidebar.get("descriptionText"),
            reply_percentage=reply.get("replyPercentage"),
            pct_5_stars=dist.get("five"),
            pct_4_stars=dist.get("four"),
            pct_3_stars=dist.get("three"),
            pct_2_stars=dist.get("two"),
            pct_1_stars=dist.get("one"),
        )

    def _parse_review(
        self, raw: dict[str, Any], company_key: str, company_name: str, domain: str
    ) -> ReviewRecord:
        consumer = raw.get("consumer") or {}
        dates = raw.get("dates") or {}
        reply = raw.get("reply") or {}
        labels = raw.get("labels") or {}
        return ReviewRecord(
            company_key=company_key,
            company_name=company_name,
            domain=domain,
            review_id=raw.get("id", ""),
            title=raw.get("title"),
            text=raw.get("text") or "",
            rating=int(raw.get("rating") or 0),
            language=raw.get("language"),
            published_date=dates.get("publishedDate"),
            experienced_date=dates.get("experiencedDate"),
            reviewer_name=consumer.get("displayName"),
            reviewer_country=consumer.get("countryCode"),
            verified=bool(labels.get("verified")),
            likes=int(raw.get("likes") or 0),
            has_company_reply=bool(reply),
            company_reply_text=reply.get("message") if reply else None,
            company_reply_date=(reply.get("publishedDate") if reply else None),
        )

    def scrape_reviews(
        self,
        company_key: str,
        company_name: str,
        domain: str,
        slug: str,
        max_reviews: int = 200,
        max_pages: int = 20,
    ) -> list[ReviewRecord]:
        profile_url = f"{BASE_URL}/review/{slug}"
        collected: list[ReviewRecord] = []
        seen_ids: set[str] = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            )

            page_num = 1
            while len(collected) < max_reviews and page_num <= max_pages:
                url = profile_url if page_num == 1 else f"{profile_url}?page={page_num}"
                logger.info("Scraping %s page %s", company_name, page_num)
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(int(self.delay_seconds * 1000))

                try:
                    props = self._page_props(page)
                except Exception as exc:
                    logger.warning("Page %s failed: %s", page_num, exc)
                    break

                reviews_raw = props.get("reviews") or []
                if not reviews_raw:
                    break

                new_on_page = 0
                for raw in reviews_raw:
                    rid = raw.get("id")
                    if not rid or rid in seen_ids:
                        continue
                    seen_ids.add(rid)
                    collected.append(
                        self._parse_review(raw, company_key, company_name, domain)
                    )
                    new_on_page += 1
                    if len(collected) >= max_reviews:
                        break

                if new_on_page == 0:
                    break
                page_num += 1
                time.sleep(self.delay_seconds)

            browser.close()

        return collected[:max_reviews]

    def scrape_category_companies(
        self, category_url: str, max_companies: int = 30
    ) -> list[dict[str, Any]]:
        """Liste d'entreprises depuis une page catégorie Trustpilot."""
        results: list[dict[str, Any]] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.goto(category_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3000)
            cards = page.evaluate(
                """() => {
                const links = document.querySelectorAll('a[href*="/review/"]');
                const seen = new Set();
                const out = [];
                links.forEach(a => {
                    const href = a.href;
                    if (!href.includes('/review/') || seen.has(href)) return;
                    seen.add(href);
                    const name = a.querySelector('p, span, h3')?.innerText || a.innerText;
                    if (name && name.length < 120) {
                        out.push({ name: name.trim().split('\\n')[0], profile_url: href });
                    }
                });
                return out;
            }"""
            )
            browser.close()

        for card in cards[:max_companies]:
            slug = card["profile_url"].split("/review/")[-1].split("?")[0]
            results.append(
                {
                    "name": card["name"],
                    "profile_url": card["profile_url"],
                    "domain": slug,
                    "category_source": category_url,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return results
