"""Wallapop API and web client for Hermes Agent.

Provides robust access to Wallapop using:
1. Playwright (Headless Browser) as primary engine: bypasses CloudFront WAF
   and renders client-side Next.js SPA listings, capturing rich data from
   `api/v3/search/section` and the DOM. Launched lazily on demand.
2. HTTP requests fallback: for environments without Playwright or when
   direct endpoints respond.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Playwright is optional - imported lazily without launching at import time
_PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

# Known coordinates for principal Spanish cities for fast, network-free resolution
SPANISH_CITIES_COORDS: Dict[str, Tuple[float, float]] = {
    "madrid": (40.4168, -3.7038),
    "barcelona": (41.3879, 2.1699),
    "valencia": (39.4699, -0.3763),
    "sevilla": (37.3891, -5.9845),
    "zaragoza": (41.6488, -0.8891),
    "malaga": (36.7213, -4.4214),
    "málaga": (36.7213, -4.4214),
    "murcia": (37.9922, -1.1307),
    "palma": (39.5696, 2.6502),
    "palma de mallorca": (39.5696, 2.6502),
    "las palmas": (28.1235, -15.4363),
    "bilbao": (43.2630, -2.9350),
    "bilbo": (43.2630, -2.9350),
    "alicante": (38.3452, -0.4810),
    "cordoba": (37.8882, -4.7794),
    "córdoba": (37.8882, -4.7794),
    "valladolid": (41.6523, -4.7245),
    "vigo": (42.2406, -8.7207),
    "gijon": (43.5357, -5.6615),
    "gijón": (43.5357, -5.6615),
    "vitoria": (42.8467, -2.6716),
    "vitoria-gasteiz": (42.8467, -2.6716),
    "donostia": (43.3183, -1.9812),
    "san sebastian": (43.3183, -1.9812),
    "san sebastián": (43.3183, -1.9812),
    "granada": (37.1773, -3.5986),
    "oviedo": (43.3619, -5.8494),
    "santander": (43.4623, -3.8099),
    "pamplona": (42.8125, -1.6458),
    "iruña": (42.8125, -1.6458),
    "almeria": (36.8381, -2.4597),
    "almería": (36.8381, -2.4597),
    "burgos": (42.3440, -3.6969),
    "salamanca": (40.9701, -5.6635),
    "toledo": (39.8628, -4.0273),
    "cadiz": (36.5271, -6.2886),
    "cádiz": (36.5271, -6.2886),
    "tarragona": (41.1189, 1.2445),
    "girona": (41.9794, 2.8214),
    "gerona": (41.9794, 2.8214),
    "badajoz": (38.8794, -6.9706),
}

# Category IDs mapping
CATEGORY_MAP: Dict[str, str] = {
    "movilidad": "1",
    "patinetes": "1",
    "coches": "2",
    "motor": "2",
    "motos": "3",
    "motor-y-accesorios": "12463",
    "motor y accesorios": "12463",
    "telefonia": "16",
    "telefonos": "16",
    "móviles": "16",
    "moviles": "16",
    "ordenadores": "4",
    "informatica": "4",
    "informática": "4",
    "electronica": "5",
    "electrónica": "5",
    "audio": "5",
    "tv": "5",
    "hogar": "8",
    "electrodomesticos": "8",
    "electrodomésticos": "8",
    "decoracion": "8",
    "decoración": "8",
    "moda": "14",
    "ropa": "14",
    "calzado": "14",
    "deporte": "16",
    "ocio": "16",
    "juguetes": "18",
    "bebes": "18",
    "bebés": "18",
    "libros": "20",
    "peliculas": "20",
    "películas": "20",
    "musica": "21",
    "música": "21",
    "instrumentos": "21",
    "videojuegos": "22",
    "consolas": "22",
    "belleza": "25",
    "mascotas": "26",
    "salud": "27",
    "herramientas": "28",
    "artesania": "33",
    "artesanía": "33",
    "inmobiliaria": "12",
}

# Condition values mapping
CONDITION_MAP: Dict[str, str] = {
    "nuevo": "new",
    "new": "new",
    "como nuevo": "as_good_as_new",
    "como_nuevo": "as_good_as_new",
    "as_good_as_new": "as_good_as_new",
    "good": "good",
    "buen estado": "good",
    "bueno": "good",
    "fair": "fair",
    "aceptable": "fair",
    "has_given_it_all": "has_given_it_all",
    "lo ha dado todo": "has_given_it_all",
    "lo_ha_dado_todo": "has_given_it_all",
    "para piezas": "has_given_it_all",
    "usado": "used",
    "used": "used",
}

# Sort order mapping
ORDER_MAP: Dict[str, str] = {
    "relevancia": "most_relevance",
    "relevance": "most_relevance",
    "most_relevance": "most_relevance",
    "price_low_to_high": "price_low_to_high",
    "precio_ascendente": "price_low_to_high",
    "price_high_to_low": "price_high_to_low",
    "precio_descendente": "price_high_to_low",
    "mas_recientes": "newest_first",
    "newest_first": "newest_first",
    "mas_cercanos": "closest",
    "closest": "closest",
}

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Origin": "https://es.wallapop.com",
    "Referer": "https://es.wallapop.com/",
    "DeviceOS": "0",
}


def _geocode_location(location: str) -> Tuple[Optional[float], Optional[float]]:
    """Geocode a location name using OpenStreetMap Nominatim with a fallback."""
    try:
        import urllib.request
        import urllib.parse

        url = (
            "https://nominatim.openstreetmap.org/search?format=json&q="
            f"{urllib.parse.quote(location)}&countrycodes=es&limit=1"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "HermesWallapopPlugin/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data and len(data) > 0:
                return float(data[0].get("lat")), float(data[0].get("lon"))
    except Exception as e:
        logger.debug(f"Geocoding failed for '{location}': {e}")

    return None, None


def resolve_coordinates(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Tuple[Optional[float], Optional[float]]:
    """Resolve latitude and longitude coordinates."""
    if latitude is not None and longitude is not None:
        try:
            return float(latitude), float(longitude)
        except (ValueError, TypeError):
            pass

    if not location or not isinstance(location, str):
        return None, None

    loc_clean = location.lower().strip()
    if loc_clean in SPANISH_CITIES_COORDS:
        return SPANISH_CITIES_COORDS[loc_clean]

    for city, coords in SPANISH_CITIES_COORDS.items():
        if city in loc_clean:
            return coords

    return _geocode_location(location)


def _normalize_condition(condition: Any, state: Optional[str] = None) -> Optional[str]:
    """Normalize condition/state filter to Wallapop condition values."""
    raw_val = condition if condition is not None else state
    if not raw_val:
        return None

    values: List[str] = []
    if isinstance(raw_val, list):
        items = raw_val
    elif "," in str(raw_val):
        items = str(raw_val).split(",")
    else:
        items = [str(raw_val)]

    for item in items:
        clean = str(item).strip().lower().replace("-", " ").replace("_", " ")
        if clean in CONDITION_MAP:
            mapped = CONDITION_MAP[clean]
            if mapped not in values:
                values.append(mapped)

    return ",".join(values) if values else None


def _format_search_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Format an item dictionary into a consistent search result schema."""
    item_id = str(raw.get("id") or "")
    web_slug = raw.get("web_slug") or raw.get("webSlug") or raw.get("slug") or ""
    if web_slug:
        url = f"https://es.wallapop.com/item/{web_slug}"
    elif item_id:
        url = f"https://es.wallapop.com/item/{item_id}"
    else:
        url = raw.get("url") or ""

    # Title
    raw_title = raw.get("title") or raw.get("name") or ""
    if isinstance(raw_title, dict):
        title = raw_title.get("original") or raw_title.get("translated") or ""
    else:
        title = str(raw_title)

    # Description
    raw_desc = raw.get("description") or ""
    if isinstance(raw_desc, dict):
        description = raw_desc.get("original") or raw_desc.get("translated") or ""
    else:
        description = str(raw_desc)

    # Normalize images
    raw_images = raw.get("images") or []
    images: List[str] = []
    if isinstance(raw_images, list):
        for img in raw_images:
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict):
                urls = img.get("urls") or {}
                src = (
                    urls.get("big")
                    or urls.get("medium")
                    or urls.get("small")
                    or img.get("original")
                    or img.get("url")
                    or img.get("medium")
                    or img.get("originalUrl")
                    or ""
                )
                if src:
                    images.append(src)
    elif isinstance(raw_images, dict):
        urls = raw_images.get("urls") or {}
        src = (
            urls.get("big")
            or urls.get("medium")
            or urls.get("small")
            or raw_images.get("original")
            or raw_images.get("url")
            or ""
        )
        if src:
            images.append(src)

    # Location
    loc_data = raw.get("location") or {}
    if isinstance(loc_data, dict):
        city = loc_data.get("city") or raw.get("city") or ""
        postal_code = loc_data.get("postal_code") or loc_data.get("postalCode") or loc_data.get("zip") or ""
        region = loc_data.get("region") or loc_data.get("region2") or ""
    else:
        city = str(loc_data)
        postal_code = ""
        region = ""

    # Shipping
    shipping_data = raw.get("shipping") or {}
    if isinstance(shipping_data, dict):
        shipping_available = (
            shipping_data.get("user_allows_shipping")
            or shipping_data.get("item_is_shippable")
            or shipping_data.get("isItemShippable")
            or shipping_data.get("isShippingAllowedByUser")
            or shipping_data.get("available")
            or False
        )
        shipping_cost = shipping_data.get("cost")
        free_shipping = shipping_data.get("free", False) or shipping_cost == 0
    else:
        shipping_available = bool(raw.get("shipping_available"))
        shipping_cost = None
        free_shipping = bool(raw.get("free_shipping"))

    # Seller
    user_data = raw.get("user") or raw.get("seller") or raw.get("itemSeller") or {}
    seller = {
        "id": str(user_data.get("id") or raw.get("userId") or ""),
        "name": user_data.get("micro_name") or user_data.get("microName") or user_data.get("name") or "",
        "verified": bool(user_data.get("verification", {}).get("phone") or user_data.get("verified")),
    }

    # Price
    price_val = raw.get("price")
    if isinstance(price_val, dict):
        if "cash" in price_val and isinstance(price_val["cash"], dict):
            price = price_val["cash"].get("amount") or price_val["cash"].get("value")
            currency = price_val["cash"].get("currency", "EUR")
        else:
            price = price_val.get("amount") or price_val.get("value")
            currency = price_val.get("currency", "EUR")
    else:
        price = price_val
        currency = raw.get("currency", "EUR")

    # Condition
    raw_cond = raw.get("condition")
    if isinstance(raw_cond, dict):
        condition = raw_cond.get("text") or raw_cond.get("title") or raw_cond.get("value") or "usado"
    elif raw_cond:
        condition = str(raw_cond)
    elif raw.get("characteristics"):
        condition = str(raw.get("characteristics"))
    else:
        condition = "nuevo" if raw.get("is_new") else "usado"

    return {
        "id": item_id,
        "url": url,
        "title": title,
        "price": price,
        "currency": currency,
        "description": description[:1000],
        "condition": condition,
        "images": images[:10],
        "location": {
            "city": city,
            "region": region,
            "postal_code": postal_code,
        },
        "shipping": {
            "available": shipping_available,
            "free": free_shipping,
        },
        "seller": seller,
    }


def _execute_playwright_search(
    url: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_label: Optional[str] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    community: str = "España",
) -> List[Dict[str, Any]]:
    """Execute search via Playwright with anti-detection args and API response interception."""
    if not _PLAYWRIGHT_AVAILABLE:
        return []

    intercepted_items: List[Dict[str, Any]] = []

    def handle_response(response):
        try:
            resp_url = response.url
            if "api/v3/search/section" in resp_url:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    data = response.json()
                    sec = data.get("data", {}).get("section", {})
                    items = sec.get("items", [])
                    if isinstance(items, list) and items:
                        for it in items:
                            if isinstance(it, dict):
                                intercepted_items.append(_format_search_item(it))
        except Exception:
            pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                timeout=25000,
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="es-ES",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.on("response", handle_response)

            # Establish initial session on homepage
            page.goto("https://es.wallapop.com", wait_until="domcontentloaded", timeout=20000)

            # Set location in localStorage if provided
            if latitude is not None and longitude is not None:
                label = location_label or (f"{city}, {province}, ESP" if city and province else "España")
                c_name = city or "Ciudad"
                page.evaluate(f"""
                    localStorage.setItem("searchLatitude", "{latitude}");
                    localStorage.setItem("searchLongitude", "{longitude}");
                    localStorage.setItem("searchLocationName", "{label}");
                    localStorage.setItem("savedSearchLocation", JSON.stringify({{
                        label: "{label}", title: "{c_name}", subtitle: "{community}, ESP",
                        latitude: {latitude}, longitude: {longitude}, city: "{c_name}"
                    }}));
                """)

            # Navigate to search URL
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)

            # If intercepted items via API, use them
            if intercepted_items:
                browser.close()
                return intercepted_items

            # Fallback: extract rendered cards from the DOM
            dom_items = page.evaluate("""() => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/item/"]');
                const seen = new Set();
                for (const link of links) {
                    const href = link.getAttribute('href');
                    if (!href || seen.has(href)) continue;
                    seen.add(href);
                    
                    const card = link.closest('article') || link.parentElement || link;
                    const text = card.innerText || '';
                    const img = card.querySelector('img');
                    const imgSrc = img ? (img.getAttribute('src') || img.getAttribute('data-src')) : null;
                    const priceMatch = text.match(/([0-9.,]+)\\s*€/);
                    const price = priceMatch ? priceMatch[1] : null;
                    const title = link.getAttribute('aria-label') || link.getAttribute('title') || (text.split('\\n')[0]);
                    
                    results.push({
                        url: 'https://es.wallapop.com' + href,
                        id: href.split('-').pop() || '',
                        title: title ? title.trim() : '',
                        price: price,
                        images: imgSrc ? [imgSrc] : []
                    });
                }
                return results;
            }""")

            browser.close()

            items = []
            for d in dom_items:
                items.append(_format_search_item(d))
            return items

    except Exception as e:
        logger.warning(f"Playwright search error: {e}")
        return []


def _fetch_api_search(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Query Wallapop's search API with requests."""
    import requests

    api_url = "https://api.wallapop.com/api/v3/general/search"
    try:
        resp = requests.get(api_url, params=params, headers=DEFAULT_HEADERS, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                return data
    except Exception as e:
        logger.debug(f"Wallapop API search failed: {e}")
    return None


def _fetch_html_search(params: Dict[str, Any]) -> Optional[str]:
    """Fetch search results page HTML via requests."""
    import requests

    html_url = "https://es.wallapop.com/search"
    html_headers = dict(DEFAULT_HEADERS)
    html_headers["Accept"] = (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    )

    try:
        resp = requests.get(html_url, params=params, headers=html_headers, timeout=8)
        if resp.status_code == 200 and resp.text:
            return resp.text
    except Exception as e:
        logger.debug(f"Wallapop HTML search failed: {e}")
    return None


def _parse_html_search_results(html: str) -> List[Dict[str, Any]]:
    """Extract search items from HTML via __NEXT_DATA__ or fallback tags."""
    items: List[Dict[str, Any]] = []

    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', html)
    if match:
        try:
            data = json.loads(match.group(1))
            page_props = data.get("props", {}).get("pageProps", {})
            for key in ["searchResults", "listings", "items", "products", "results", "searchResult"]:
                if key in page_props:
                    items_data = page_props[key]
                    if isinstance(items_data, dict) and "items" in items_data:
                        items_data = items_data["items"]
                    if isinstance(items_data, list):
                        for raw in items_data:
                            if isinstance(raw, dict):
                                items.append(_format_search_item(raw))
                        if items:
                            return items
        except (json.JSONDecodeError, TypeError):
            pass

    item_pattern = r'<a[^>]*href="(/item/([^"]+))"[^>]*aria-label="([^"]+)"[^>]*>'
    for m in re.finditer(item_pattern, html, re.DOTALL | re.IGNORECASE):
        item_path = m.group(1)
        item_slug = m.group(2)
        title = m.group(3)
        slug_parts = item_slug.split("-")
        item_id = slug_parts[-1] if slug_parts else ""
        if item_id:
            items.append({
                "id": item_id,
                "url": f"https://es.wallapop.com{item_path}",
                "title": title.strip(),
                "price": None,
                "currency": "EUR",
                "description": "",
                "condition": "usado",
                "images": [],
                "location": {"city": "", "region": "", "postal_code": ""},
                "shipping": {"available": False, "free": False},
                "seller": {"id": "", "name": "", "verified": False},
            })

    return items


def search_wallapop_api(
    query: Optional[str] = None,
    location: Optional[str] = None,
    items_per_page: int = 20,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    community: str = "España",
    radius_km: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    state: Optional[str] = None,
    shipping_available: Optional[bool] = None,
    free_shipping: Optional[bool] = None,
    category: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    time_filter: Optional[str] = None,
    condition: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Search Wallapop items with full filter support.
    Uses Playwright as primary engine when installed (required by Wallapop's WAF
    and client-side SPA rendering), with requests fallback.
    """
    if not query:
        return {"error": "Query parameter is required", "items": [], "total": 0}

    # Resolve coordinates
    resolved_lat, resolved_lng = resolve_coordinates(
        location=location or city,
        latitude=latitude,
        longitude=longitude,
    )

    # Build web parameters
    web_params: Dict[str, Any] = {
        "keywords": query,
    }

    if resolved_lat is not None and resolved_lng is not None:
        web_params["latitude"] = str(resolved_lat)
        web_params["longitude"] = str(resolved_lng)
        if radius_km:
            web_params["distance_in_km"] = str(radius_km)

    if min_price is not None:
        web_params["min_sale_price"] = str(min_price)
    if max_price is not None:
        web_params["max_sale_price"] = str(max_price)

    # Category
    if category:
        cat_key = category.lower().strip()
        cat_id = CATEGORY_MAP.get(cat_key, cat_key)
        web_params["category_ids"] = cat_id

    # Condition
    cond_val = _normalize_condition(condition, state)
    if cond_val:
        web_params["condition"] = cond_val

    # Shipping
    if free_shipping:
        web_params["shipping"] = "free"
    elif shipping_available is not None:
        web_params["shipping"] = "available" if shipping_available else "none"

    # Sort
    if sort:
        sort_clean = sort.lower().strip()
        web_params["order_by"] = ORDER_MAP.get(sort_clean, sort_clean)

    # Pagination
    offset = (max(page, 1) - 1) * items_per_page
    web_params["offset"] = str(offset)
    web_params["count"] = str(items_per_page)

    search_url = f"https://es.wallapop.com/search?{requests_quote_params(web_params)}"

    # 1. Primary Engine: Playwright (bypasses WAF and renders client-side Next.js SPA)
    if _PLAYWRIGHT_AVAILABLE:
        pw_items = _execute_playwright_search(
            url=search_url,
            latitude=resolved_lat,
            longitude=resolved_lng,
            location_label=location or city,
            city=city,
            province=province,
            community=community,
        )
        if pw_items:
            return {
                "items": pw_items[:items_per_page],
                "total": len(pw_items),
                "page": page,
                "has_more": len(pw_items) >= items_per_page,
                "engine": "playwright",
                "search_url": search_url,
            }

    # 2. Fallback: Internal API via requests
    api_params = dict(web_params)
    api_params["filters_source"] = "search_box"
    api_result = _fetch_api_search(api_params)
    if api_result:
        raw_items = api_result.get("search_objects") or api_result.get("items") or []
        items = [_format_search_item(item) for item in raw_items if isinstance(item, dict)]
        if items:
            total = api_result.get("total") or api_result.get("count") or len(items)
            return {
                "items": items[:items_per_page],
                "total": int(total),
                "page": page,
                "has_more": len(items) >= items_per_page,
                "engine": "api",
                "search_url": search_url,
            }

    # 3. Fallback: HTML scraping via requests
    html = _fetch_html_search(web_params)
    if html:
        items = _parse_html_search_results(html)
        if items:
            return {
                "items": items[:items_per_page],
                "total": len(items),
                "page": page,
                "has_more": len(items) >= items_per_page,
                "engine": "html_scraper",
                "search_url": search_url,
            }

    # If no results and Playwright not available, advise the user
    message = "No results found."
    if not _PLAYWRIGHT_AVAILABLE:
        message = (
            "No results returned. Wallapop requires client-side JavaScript rendering "
            "and browser validation. Install Playwright (`pip install playwright && playwright install chromium`) "
            "to enable full search functionality."
        )

    return {
        "items": [],
        "total": 0,
        "page": page,
        "has_more": False,
        "message": message,
        "search_url": search_url,
    }


def get_item_details_api(item_id: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
    """Get full item details by item ID or URL."""
    import requests

    if not item_id and not url:
        return {"error": "Either item_id or url is required"}

    # Extract ID from URL if item_id is missing
    clean_id = str(item_id).strip() if item_id else ""
    if not clean_id and url:
        m = re.search(r"/(?:item|a)/([a-zA-Z0-9_-]+)", url)
        if m:
            slug = m.group(1)
            parts = slug.split("-")
            clean_id = parts[-1] if parts else slug

    item_url = url or f"https://es.wallapop.com/item/{clean_id}"

    # 1. Try Playwright if available (best for full client-rendered details)
    if _PLAYWRIGHT_AVAILABLE:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                    timeout=20000,
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="es-ES",
                )
                page = context.new_page()
                page.goto("https://es.wallapop.com", wait_until="domcontentloaded", timeout=15000)
                page.goto(item_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)

                item_details = page.evaluate("""() => {
                    const nextScript = document.getElementById('__NEXT_DATA__');
                    if (nextScript) {
                        try {
                            const data = JSON.parse(nextScript.innerText);
                            const props = data.props && data.props.pageProps ? data.props.pageProps : {};
                            for (const key of ['item', 'listing', 'product']) {
                                if (props[key]) {
                                    const it = Object.assign({}, props[key]);
                                    if (props.itemSeller) it.user = props.itemSeller;
                                    return it;
                                }
                            }
                        } catch(e) {}
                    }
                    
                    // DOM extraction fallback
                    const titleEl = document.querySelector('h1') || document.querySelector('[class*="item-detail_ItemDetail__title"]');
                    const priceEl = document.querySelector('[class*="item-detail_ItemDetail__price"]') || document.querySelector('[class*="price"]');
                    const descEl = document.querySelector('[class*="item-detail_ItemDetail__description"]') || document.querySelector('p');
                    const imgs = Array.from(document.querySelectorAll('img')).map(i => i.src).filter(s => s && s.includes('wallapop.com/images'));
                    
                    return {
                        title: titleEl ? titleEl.innerText : '',
                        price: priceEl ? priceEl.innerText : null,
                        description: descEl ? descEl.innerText : '',
                        images: imgs
                    };
                }""")
                browser.close()

                if item_details and (item_details.get("title") or item_details.get("price") or item_details.get("id")):
                    res = _format_search_item(item_details)
                    res["id"] = clean_id or res.get("id", "")
                    res["url"] = item_url
                    res["status"] = item_details.get("status", "disponible")
                    return res
        except Exception as e:
            logger.debug(f"Playwright get_item error: {e}")

    # 2. Try internal API endpoint via requests
    if clean_id:
        try:
            api_url = f"https://api.wallapop.com/api/v3/items/{clean_id}"
            resp = requests.get(api_url, params={"language": "es"}, headers=DEFAULT_HEADERS, timeout=8)
            if resp.status_code == 200:
                item_data = resp.json()
                if isinstance(item_data, dict):
                    res = _format_search_item(item_data)
                    res["description"] = item_data.get("description") or ""
                    res["status"] = item_data.get("status", "disponible")
                    return res
        except Exception as e:
            logger.debug(f"API get item failed: {e}")

    # 3. Try HTML scraping with requests
    try:
        html_headers = dict(DEFAULT_HEADERS)
        html_headers["Accept"] = (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        )
        resp = requests.get(item_url, headers=html_headers, timeout=8)
        if resp.status_code == 200 and resp.text:
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', resp.text)
            if match:
                data = json.loads(match.group(1))
                page_props = data.get("props", {}).get("pageProps", {})
                for key in ["item", "listing", "product"]:
                    if key in page_props and isinstance(page_props[key], dict):
                        item_data = page_props[key]
                        res = _format_search_item(item_data)
                        res["description"] = item_data.get("description") or ""
                        res["status"] = item_data.get("status", "disponible")
                        return res
    except Exception as e:
        logger.debug(f"HTML get item failed: {e}")

    return {
        "error": "Could not retrieve item details",
        "item_id": clean_id,
        "url": item_url,
    }


def requests_quote_params(params: Dict[str, Any]) -> str:
    """Helper to encode params dictionary to URL query string."""
    parts = []
    for k, v in params.items():
        if v is not None:
            parts.append(f"{quote(str(k))}={quote(str(v))}")
    return "&".join(parts)
