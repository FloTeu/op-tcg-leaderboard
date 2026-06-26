"""
Async Crawl4AI crawler for Cardmarket sealed products (booster boxes, cases, starter decks).

Uses Playwright via Crawl4AI for Cloudflare bypass. Supports residential proxy rotation
via the SCRAPER_PROXY env var. Not a Scrapy spider — run via asyncio directly from the CLI.
"""
import logging
import os
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from op_tcg.backend.models.cards import OPTcgLanguage, OPTcgMarketplace, CardCurrency
from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.sealed import SealedProduct, SealedProductPrice, SealedProductType, SealedPriceType, sealed_product_gcs_path

logger = logging.getLogger(__name__)

CARDMARKET_BASE = "https://www.cardmarket.com"

ITEMS_PER_SITE = 200

# Gallery URLs per product type. perSite=100 maximises items per page.
PRODUCT_TYPE_URLS: dict[SealedProductType, str] = {
    SealedProductType.BOOSTER_BOX: (
        f"{CARDMARKET_BASE}/en/OnePiece/Products/Booster-Boxes"
        f"?mode=gallery&searchMode=v1&idCategory=1624&idExpansion=0&sortBy=date_desc&perSite={ITEMS_PER_SITE}"
    ),
    SealedProductType.SEALED: (
        f"{CARDMARKET_BASE}/en/OnePiece/Products/Promo-Products"
        f"?searchMode=v1&idCategory=1628&idExpansion=0&sortBy=date_desc&perSite={ITEMS_PER_SITE}"
    ),
}

# Language keywords to detect in product names (case-insensitive).
# JP pattern covers:
#   - "OP10-JPRoyal" → lookbehind for [-\s(], JP followed by uppercase (country-code prefix)
#   - standalone (JP), JPN, "Japanese"
#   - "(Non-English)" explicit marker
# EN pattern is checked second, so "Non-English" (which contains "English") correctly
# returns JP because the JP pattern fires first.
_LANG_PATTERNS: list[tuple[re.Pattern, OPTcgLanguage]] = [
    # JP: match "JP" as a country-code prefix after hyphen/space/paren (e.g. "OP10-JPRoyal"),
    # standalone JPN/JP words, "Japanese", or the explicit "(Non-English)" marker.
    # Checked before EN so "Non-English" (which contains "English") correctly returns JP.
    (re.compile(
        r'(?<=[-\s(])JP(?=[A-Z\s),.])'   # -JPRoyal  or  (JP)  or  -JP followed by space
        r'|\bJPN?\b'                       # standalone JP or JPN
        r'|\bJapanese\b'
        r'|\bNon-English\b',
        re.IGNORECASE,
    ), OPTcgLanguage.JP),
    (re.compile(r"\b(?:english|en)\b", re.IGNORECASE), OPTcgLanguage.EN),
]

# Cardmarket shows prices as "1.299,99 €" (DE) or "1,299.99 €" (EN) — normalise both
_PRICE_RE = re.compile(r"[\d.,]+")


def _is_cloudflare_challenge(html: str) -> bool:
    """Detect Cloudflare's 'Just a moment...' challenge page."""
    return "challenges.cloudflare.com" in html


def _build_proxy_config(proxy_url: str | None) -> dict | None:
    """
    Parse a proxy URL like http://user:pass@host:port into the dict format
    Playwright requires. Returns None if no proxy is configured.
    """
    if not proxy_url:
        return None
    parsed = urlparse(proxy_url)
    config: dict = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        config["username"] = parsed.username
    if parsed.password:
        config["password"] = parsed.password
    return config


def extract_product_id(url: str) -> str:
    """Extract a stable ID from the product page URL slug."""
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1]
    return slug.lower()


_PRICE_SUFFIX_RE = re.compile(r'\s+(?:From|Trend)\s+\d[\d.,]*\s*€.*$', re.IGNORECASE)


def _strip_price_suffix(text: str) -> str:
    """Remove trailing price info like ' From 999,95 €' or ' Trend 92,50 €' from a name."""
    return _PRICE_SUFFIX_RE.sub("", text).strip()


def detect_language(name: str) -> OPTcgLanguage:
    for pattern, lang in _LANG_PATTERNS:
        if pattern.search(name):
            return lang
    return OPTcgLanguage.EN


def parse_price(price_text: str) -> float | None:
    """Parse a Cardmarket price string like '89,99 €' or '1.299,99 €' → float."""
    text = price_text.replace("\xa0", "").strip()
    has_comma = "," in text
    has_dot = "." in text

    if has_comma and has_dot:
        # Whichever separator appears last is the decimal separator
        last_comma = text.rfind(",")
        last_dot = text.rfind(".")
        if last_comma > last_dot:
            # European: 1.299,99 → remove dots, replace comma with dot
            text = text.replace(".", "").replace(",", ".")
        else:
            # US: 1,299.99 → just remove commas
            text = text.replace(",", "")
    elif has_comma:
        text = text.replace(",", ".")

    raw = re.sub(r"[^\d.]", "", text)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_gallery_page(html: str, product_type: SealedProductType) -> list[tuple[SealedProduct, list[SealedProductPrice]]]:
    """
    Parse a Cardmarket gallery page and return (product, price) pairs.

    Cardmarket gallery mode renders a grid of product tiles. Each tile contains:
    - An anchor link to the product page (href contains the product URL slug)
    - The product name (link text or title attribute)
    - Price rows labelled "From" and "Trend"

    The exact CSS classes may change; the parsing is written in layers so the
    selector constants at the top can be adjusted without rewriting the logic.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[tuple[SealedProduct, list[SealedProductPrice]]] = []

    # Cardmarket gallery: each product is in an <article> or a grid-col <div> that
    # wraps a product card. We locate product anchors and walk up to find their price siblings.
    product_links: list[Tag] = soup.select(
        "a[href*='/Products/Booster-Box'], "
        "a[href*='/Products/Booster-Case'], "
        "a[href*='/Products/Starter-Deck'], "
        "a[href*='/Products/Promo-Products']"
    )

    # De-duplicate by href
    seen_hrefs: set[str] = set()
    for anchor in product_links:
        href = anchor.get("href", "")
        if not href or href in seen_hrefs:
            continue
        # Skip pagination / category links (they end in the category, not a specific product)
        if href.rstrip("/").endswith(("Booster-Boxes", "Booster-Cases", "Starter-Decks", "Promo-Products")):
            continue
        seen_hrefs.add(href)

        full_url = href if href.startswith("http") else f"{CARDMARKET_BASE}{href}"
        product_id = extract_product_id(full_url)

        # Product name: prefer title attribute (clean), fall back to anchor text.
        # separator=" " ensures child elements are joined with spaces, not concatenated.
        # _strip_price_suffix removes trailing "From X €" / "Trend X €" that leaks in
        # when the anchor wraps the entire tile including price elements.
        raw_name = anchor.get("title") or anchor.get_text(separator=" ", strip=True)
        name = _strip_price_suffix(raw_name).strip()
        if not name:
            continue

        language = detect_language(name)

        # Walk up the DOM to find the enclosing tile that also contains image and prices
        tile = anchor.find_parent(["article", "div"], class_=re.compile(r"(col|card|product)", re.IGNORECASE))
        trend_price: float | None = None
        image_url: str | None = None

        if tile:
            trend_price = _extract_labeled_price(tile, "trend")
            from_price = _extract_labeled_price(tile, "from")
            image_url = _extract_image_url(tile)

        # Products without an image are navigation/category links, not real products — skip them
        if not image_url:
            logger.debug("No image found for %s — skipping (likely not a real product)", product_id)
            continue

        if trend_price is None and from_price is None:
            logger.debug("No prices found for %s", product_id)

        product = SealedProduct(
            id=product_id,
            marketplace=OPTcgMarketplace.CARDMARKET,
            name=name,
            product_type=product_type,
            language=language,
            url=full_url,
            image_url=image_url,
        )

        prices: list[SealedProductPrice] = []
        for price_value, price_type in [(trend_price, SealedPriceType.TREND), (from_price, SealedPriceType.FROM)]:
            if price_value is not None:
                prices.append(SealedProductPrice(
                    product_id=product_id,
                    marketplace=OPTcgMarketplace.CARDMARKET,
                    price_type=price_type,
                    price=price_value,
                    currency=CardCurrency.EURO,
                    source=DataSource.CARDMARKET,
                ))

        results.append((product, prices))

    return results


def _extract_labeled_price(tile: Tag, label: str) -> float | None:
    """
    Find a price labelled *label* (e.g. 'trend' or 'from') within a product tile.

    Cardmarket renders prices as labelled rows, e.g.:
        <dt>Trend</dt><dd>92,50 €</dd>  or  <dt>From</dt><dd>89,99 €</dd>
    or inline spans like:
        <span>Trend: </span><span class="color-primary">92,50 €</span>
    """
    text = tile.get_text(" ", strip=True)

    # Strategy 1: look for a matching <dt> / <dd> pair
    dt_tags = tile.find_all("dt")
    for dt in dt_tags:
        if label in dt.get_text(strip=True).lower():
            dd = dt.find_next_sibling("dd")
            if dd:
                return parse_price(dd.get_text(strip=True))

    # Strategy 2: look for the label word followed by a price span/sibling
    for span in tile.find_all(["span", "div"]):
        span_text = span.get_text(strip=True).lower()
        if span_text == label or span_text.startswith(label):
            sibling = span.find_next_sibling()
            if sibling:
                price = parse_price(sibling.get_text(strip=True))
                if price is not None:
                    return price

    # Strategy 3: parse inline "Label: 92,50 €" from full tile text
    m = re.search(rf"{re.escape(label)}[:\s]+([0-9.,]+\s*€)", text, re.IGNORECASE)
    if m:
        return parse_price(m.group(1))

    return None


def _extract_image_url(tile: Tag) -> str | None:
    """
    Find the product image URL within a Cardmarket product tile.

    Cardmarket uses standard <img src="..."> tags or lazy-loading via data-src.
    Only absolute https:// URLs pointing to Cardmarket's CDN are accepted.
    """
    for attr in ("src", "data-src", "data-lazy-src", "data-echo"):
        img = tile.find("img", attrs={attr: re.compile(r"^https://", re.IGNORECASE)})
        if img:
            url = img.get(attr, "")
            if url:
                return url
    return None


def _upload_image_to_gcs(image_bytes: bytes, blob_path: str, bucket_name: str, gcs_client) -> str:
    """Upload raw image bytes to GCS and return the public https URL."""
    ext = blob_path.rsplit(".", 1)[-1].lower()
    bucket = gcs_client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(image_bytes, content_type=f"image/{ext}")
    return f"https://storage.googleapis.com/{bucket_name}/{blob_path}"


class CloudflareBlockedError(RuntimeError):
    """Raised when Cloudflare's challenge did not resolve within the timeout.

    Propagating this as an exception (rather than returning empty results) ensures
    the Cloud Run Job exits with a non-zero status code, making the failure visible
    in Cloud Run monitoring instead of silently succeeding with 0 data.
    """


async def _fetch_with_retry(
    browser, url: str, max_retries: int = 3, cf_wait_ms: int = 30_000,
    skip_image_urls: set[str] | None = None,
) -> tuple[str, dict[str, bytes]]:
    """
    Fetch *url* via a fresh browser page, retrying up to *max_retries* times on
    CloudflareBlockedError. Each retry opens a new page so the rotating proxy
    assigns a different exit IP.

    When *skip_image_urls* is provided (not None), image responses from the Cardmarket
    CDN are intercepted and returned alongside the HTML — except for URLs already in
    *skip_image_urls* (already uploaded to GCS with the same source URL).

    Returns (html, image_bytes_map) where image_bytes_map is empty when
    skip_image_urls is None.
    """
    capture_images = skip_image_urls is not None
    last_exc: CloudflareBlockedError | None = None
    for attempt in range(1, max_retries + 1):
        image_bytes_map: dict[str, bytes] = {}
        page = await browser.new_page()

        if capture_images:
            async def _on_response(response, _map=image_bytes_map, _skip=skip_image_urls):
                if "product-images.s3.cardmarket.com" in response.url:
                    if response.url in _skip:
                        return
                    try:
                        body = await response.body()
                        if body:
                            _map[response.url] = body
                    except Exception as exc:
                        logger.debug("image capture failed %s: %s", response.url, exc)
            page.on("response", _on_response)

        try:
            html = await _fetch_page_html(page, url, cf_wait_ms=cf_wait_ms)
            if capture_images:
                # Scroll gradually so Intersection Observer triggers lazy-loaded images.
                # Page height grows as images load, so we scroll until the height has
                # been stable rather than targeting a fixed endpoint calculated upfront.
                await page.evaluate("""
                    async () => {
                        const step = 600;
                        const delay = ms => new Promise(r => setTimeout(r, ms));
                        while (true) {
                            window.scrollBy(0, step);
                            await delay(1500);
                            const atBottom =
                                window.scrollY + window.innerHeight >= document.body.scrollHeight - 10;
                            if (atBottom) {
                                const heightBefore = document.body.scrollHeight;
                                await delay(1500);
                                if (document.body.scrollHeight === heightBefore) break;
                            }
                        }
                    }
                """)
                await page.wait_for_load_state("networkidle", timeout=10_000)
            return html, image_bytes_map
        except CloudflareBlockedError as exc:
            last_exc = exc
            logger.warning("CF blocked (attempt %d/%d) for %s — rotating IP", attempt, max_retries, url)
        finally:
            await page.close()
    raise last_exc  # type: ignore[misc]


async def _fetch_page_html(browser_page, url: str, cf_wait_ms: int = 30_000) -> str:
    """
    Navigate to *url* using an already-open Camoufox page, wait for Cloudflare's
    managed challenge to auto-resolve, and return the final rendered HTML.

    Raises CloudflareBlockedError if the challenge is still present after cf_wait_ms.
    """
    await browser_page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    poll_interval = 2_000
    elapsed = 0
    while elapsed < cf_wait_ms:
        html = await browser_page.content()
        if not _is_cloudflare_challenge(html):
            return html
        logger.debug("Cloudflare challenge active, waiting... (%dms elapsed)", elapsed)
        await browser_page.wait_for_timeout(poll_interval)
        elapsed += poll_interval
    try:
        page_title = await browser_page.title()
    except Exception as title_exc:  # noqa: BLE001
        page_title = f"<error: {title_exc}>"
    raise CloudflareBlockedError(
        f"Cloudflare challenge was not resolved within {cf_wait_ms / 1000:.0f}s for {url}. "
        f"Page title at timeout: '{page_title}'. "
        f"Ensure SCRAPER_PROXY is set to a residential proxy with valid credentials."
    )


async def crawl_cardmarket_sealed(
    product_types: list[SealedProductType] | None = None,
    upload_images: bool = False,
) -> list[tuple[SealedProduct, list[SealedProductPrice]]]:
    """
    Crawl Cardmarket gallery pages for the given product types and return
    (SealedProduct, [SealedProductPrice, ...]) pairs. Each product yields up to two
    price rows: one TREND and one FROM. Either may be absent.

    Uses Camoufox (anti-fingerprint Firefox) + residential proxy (SCRAPER_PROXY env var)
    to bypass Cloudflare's Managed Challenge. Camoufox must be installed:

        poetry add camoufox[geoip]
        python -m camoufox fetch

    Args:
        upload_images: If True, download each product image via the browser session and
            upload to GCS. Only downloads when the image_url has changed since the last run
            (detected via URL hash in the GCS blob name). Requires GOOGLE_CLOUD_PROJECT.
    """
    from camoufox.async_api import AsyncCamoufox

    if product_types is None:
        product_types = list(PRODUCT_TYPE_URLS.keys())

    proxy_url = os.environ.get("SCRAPER_PROXY")
    proxy_config = _build_proxy_config(proxy_url)
    headless = os.environ.get("CAMOUFOX_HEADLESS", "true").lower() != "false"

    if proxy_config:
        logger.info("Proxy configured: %s | username: %s", proxy_config.get("server"), proxy_config.get("username"))
    else:
        logger.warning("No SCRAPER_PROXY set — Cloudflare will likely block requests")

    # Pre-load existing gcs_image_url values so we can skip unchanged images
    existing_gcs_urls: dict[str, str] = {}
    already_uploaded_image_urls: set[str] = set()
    gcs_client = None
    bucket_name: str = ""
    if upload_images:
        from google.cloud import bigquery as _bq
        from google.cloud import storage as _gcs
        _bq_client = _bq.Client(location="europe-west1")
        bucket_name = f"{_bq_client.project}-public"
        gcs_client = _gcs.Client()
        table_ref = f"{_bq_client.project}.{SealedProduct.get_dataset_id()}.{SealedProduct.__tablename__}"
        try:
            df = _bq_client.query_and_wait(
                f"SELECT id, marketplace, language, image_url, gcs_image_url FROM `{table_ref}` WHERE gcs_image_url IS NOT NULL"
            ).to_dataframe()
            for _, row in df.iterrows():
                key = f"{row['id']}_{row['marketplace']}_{row['language']}"
                gcs_url = row["gcs_image_url"] or ""
                src_url = row["image_url"] or ""
                existing_gcs_urls[key] = gcs_url
                # Mark this source URL as already uploaded if the hash still matches
                if src_url and gcs_url:
                    expected_path = sealed_product_gcs_path(row["id"], src_url)
                    if expected_path in gcs_url:
                        already_uploaded_image_urls.add(src_url)
            logger.info(
                "Loaded %d existing GCS URLs; %d source URLs already current — will skip their captures",
                len(existing_gcs_urls), len(already_uploaded_image_urls),
            )
        except Exception as exc:
            logger.warning("Could not load existing gcs_image_url values: %s", exc)

    all_results: list[tuple[SealedProduct, list[SealedProductPrice]]] = []

    async with AsyncCamoufox(
        headless=headless,
        proxy=proxy_config,
        os=["windows", "macos", "linux"],
        geoip=True,
    ) as browser:
        for product_type in product_types:
            base_url = PRODUCT_TYPE_URLS.get(product_type)
            if not base_url:
                logger.warning("No URL configured for product type %s", product_type)
                continue

            page_num = 0
            seen_ids: set[str] = set()
            while True:
                url = f"{base_url}&site={page_num + 1}" if page_num > 0 else base_url
                logger.info("Crawling %s (page %d)", product_type, page_num + 1)

                try:
                    html, image_bytes_map = await _fetch_with_retry(
                        browser, url,
                        skip_image_urls=already_uploaded_image_urls if upload_images else None,
                    )
                except CloudflareBlockedError:
                    raise  # all retries exhausted — Cloud Run Job must exit non-zero
                except Exception as exc:
                    logger.error("Crawl failed for %s page %d: %s", product_type, page_num + 1, exc)
                    break

                page_results = parse_gallery_page(html, product_type)

                # Filter to products not yet seen — prevents infinite loops when Cardmarket
                # repeats the same page (e.g. beyond the last page of results).
                new_results = [(p, pr) for p, pr in page_results if p.id not in seen_ids]
                if not new_results:
                    logger.info(
                        "No new products on page %d for %s — stopping pagination",
                        page_num + 1, product_type,
                    )
                    break

                for product, _ in new_results:
                    seen_ids.add(product.id)

                if upload_images:
                    await _process_images(new_results, existing_gcs_urls, image_bytes_map, gcs_client, bucket_name)

                all_results.extend(new_results)
                logger.info("Found %d new products on page %d for %s", len(new_results), page_num + 1, product_type)

                page_num += 1

    logger.info("Total products scraped: %d", len(all_results))
    return all_results


async def _process_images(
    results: list[tuple[SealedProduct, list[SealedProductPrice]]],
    existing_gcs_urls: dict[str, str],
    image_bytes_map: dict[str, bytes],
    gcs_client,
    bucket_name: str,
) -> None:
    """Upload product images captured during page load to GCS.

    Images are pre-captured via network interception in _fetch_with_retry so that
    the browser's Referer header (cardmarket.com) satisfies the CDN access policy.
    Skips products whose image_url has not changed since the last run.
    """
    uploaded = skipped = missing = 0
    for product, _ in results:
        if not product.image_url:
            continue
        blob_path = sealed_product_gcs_path(product.id, product.image_url)
        cache_key = f"{product.id}_{product.marketplace}_{product.language}"
        existing = existing_gcs_urls.get(cache_key, "")

        if existing and blob_path in existing:
            product.gcs_image_url = existing
            skipped += 1
            continue

        image_bytes = image_bytes_map.get(product.image_url)
        if not image_bytes:
            logger.warning("no captured bytes for %s (%s) — image may be lazy-loaded off-screen", product.id, product.image_url)
            missing += 1
            continue

        try:
            gcs_url = _upload_image_to_gcs(image_bytes, blob_path, bucket_name, gcs_client)
            product.gcs_image_url = gcs_url
            existing_gcs_urls[cache_key] = gcs_url
            uploaded += 1
            logger.info("uploaded image %s → %s", product.id, gcs_url)
        except Exception as exc:
            logger.error("failed to upload image for %s: %s", product.id, exc)
    logger.info("images: %d uploaded, %d skipped (unchanged), %d missing from capture", uploaded, skipped, missing)
