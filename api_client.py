"""Wallapop API and web client for Hermes Agent.

Provides robust access to Wallapop via:
1. Direct internal API (requests) - fast, reliable, no browser overhead.
2. Web scraping fallback (requests + BeautifulSoup + Next.js __NEXT_DATA__).
3. Optional Playwright fallback if installed and JavaScript rendering is needed.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

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
    web_slug = raw.get("web_slug") or raw.get("webSlug") or ""
    if web_slug:
        url = f"https://es.wallapop.com/item/{web_slug}"
    elif item_id:
        url = f"https://es.wallapop.com/item/{item_id}"
    else:
        url = raw.get("url") or ""

    # Normalize images
    raw_images = raw.get("images") or []
    images: List[str] = []
    if isinstance(raw_images, list):
        for img in raw_images:
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict):
                src = img.get("original") or img.get("url") or img.get("medium") or ""
                if src:
                    images.append(src)
    elif isinstance(raw_images, dict):
        src = raw_images.get("original") or raw_images.get("url") or ""
        if src:
            images.append(src)

    # Location
    loc_data = raw.get("location") or {}
    if isinstance(loc_data, dict):
        city = loc_data.get("city") or raw.get("city") or ""
        postal_code = loc_data.get("postal_code") or loc_data.get("postalCode") or ""
        region = loc_data.get("region") or ""
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
    user_data = raw.get("user") or raw.get("seller") or {}
    seller = {
        "id": str(user_data.get("id") or ""),
        "name": user_data.get("micro_name") or user_data.get("name") or "",
        "verified": bool(user_data.get("verification", {}).get("phone") or user_data.get("verified")),
    }

    price_val = raw.get("price")
    if isinstance(price_val, dict):
        price = price_val.get("amount") or price_val.get("value")
        currency = price_val.get("currency", "EUR")
    else:
        price = price_val
        currency = raw.get("currency", "EUR")

    return {
        "id": item_id,
        "url": url,
        "title": raw.get("title") or raw.get("name") or "",
        "price": price,
        "currency": currency,
        "description": (raw.get("description") or "")[:500],
        "condition": raw.get("condition") or ("nuevo" if raw.get("is_new") else "usado"),
        "images": images[:5],
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


def _fetch_api_search(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Query Wallapop's internal search API."""
    import requests

    api_url = "https://api.wallapop.com/api/v3/general/search"
    try:
        resp = requests.get(api_url, params=params, headers=DEFAULT_HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                return data
    except Exception as e:
        logger.debug(f"Wallapop API search failed: {e}")
    return None


def _fetch_html_search(params: Dict[str, Any]) -> Optional[str]:
    """Fetch search results page HTML."""
    import requests

    html_url = "https://es.wallapop.com/search"
    html_headers = dict(DEFAULT_HEADERS)
    html_headers["Accept"] = (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    )

    try:
        resp = requests.get(html_url, params=params, headers=html_headers, timeout=12)
        if resp.status_code == 200 and resp.text:
            return resp.text
    except Exception as e:
        logger.debug(f"Wallapop HTML search failed: {e}")
    return None


def _parse_html_search_results(html: str) -> List[Dict[str, Any]]:
    """Extract search items from HTML via __NEXT_DATA__ or fallback tags."""
    items: List[Dict[str, Any]] = []

    # 1. Try __NEXT_DATA__ script
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

    # 2. Try link matching regex for items
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


def _fetch_with_playwright(
    url: str,
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    community: str = "España",
) -> str:
    """Fetch page using Playwright when JavaScript rendering is needed."""
    if not _PLAYWRIGHT_AVAILABLE:
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, timeout=15000)
            context = browser.new_context()
            page = context.new_page()
            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            })

            if latitude is not None and longitude is not None:
                label = f"{city}, {province}, ESP" if city and province else (location or "España")
                page.goto("https://es.wallapop.com", wait_until="domcontentloaded", timeout=15000)
                page.evaluate(f"""
                    localStorage.setItem("searchLatitude", "{latitude}");
                    localStorage.setItem("searchLongitude", "{longitude}");
                    localStorage.setItem("searchLocationName", "{label}");
                """)

            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.debug(f"Playwright execution failed: {e}")
        return ""


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
    """Search Wallapop items with full filter support."""
    if not query:
        return {"error": "Query parameter is required", "items": [], "total": 0}

    # Resolve coordinates
    resolved_lat, resolved_lng = resolve_coordinates(
        location=location or city,
        latitude=latitude,
        longitude=longitude,
    )

    # Build API and web parameters
    api_params: Dict[str, Any] = {
        "keywords": query,
        "filters_source": "search_box",
    }
    web_params: Dict[str, Any] = {
        "keywords": query,
    }

    if resolved_lat is not None and resolved_lng is not None:
        api_params["latitude"] = str(resolved_lat)
        api_params["longitude"] = str(resolved_lng)
        web_params["latitude"] = str(resolved_lat)
        web_params["longitude"] = str(resolved_lng)
        if radius_km:
            api_params["distance_in_km"] = str(radius_km)
            web_params["distance_in_km"] = str(radius_km)

    if min_price is not None:
        api_params["min_sale_price"] = str(min_price)
        web_params["min_sale_price"] = str(min_price)
    if max_price is not None:
        api_params["max_sale_price"] = str(max_price)
        web_params["max_sale_price"] = str(max_price)

    # Category
    if category:
        cat_key = category.lower().strip()
        cat_id = CATEGORY_MAP.get(cat_key, cat_key)
        api_params["category_ids"] = cat_id
        web_params["category_ids"] = cat_id

    # Condition
    cond_val = _normalize_condition(condition, state)
    if cond_val:
        api_params["condition"] = cond_val
        web_params["condition"] = cond_val

    # Shipping
    if free_shipping:
        api_params["shipping"] = "free"
        web_params["shipping"] = "free"
    elif shipping_available is not None:
        val = "available" if shipping_available else "none"
        api_params["shipping"] = val
        web_params["shipping"] = val

    # Sort
    if sort:
        sort_clean = sort.lower().strip()
        order_by = ORDER_MAP.get(sort_clean, sort_clean)
        api_params["order_by"] = order_by
        web_params["order_by"] = order_by

    # Pagination
    offset = (max(page, 1) - 1) * items_per_page
    api_params["offset"] = str(offset)
    api_params["step"] = str(items_per_page)
    web_params["offset"] = str(offset)
    web_params["count"] = str(items_per_page)

    search_url = f"https://es.wallapop.com/search?{requests_quote_params(web_params)}"

    # 1. Try internal API
    api_result = _fetch_api_search(api_params)
    if api_result:
        raw_items = api_result.get("search_objects") or api_result.get("items") or []
        items = [_format_search_item(item) for item in raw_items if isinstance(item, dict)]
        total = api_result.get("total") or api_result.get("count") or len(items)
        return {
            "items": items[:items_per_page],
            "total": int(total),
            "page": page,
            "has_more": len(items) >= items_per_page,
            "search_url": search_url,
        }

    # 2. Try HTML scraping fallback
    html = _fetch_html_search(web_params)
    if html:
        items = _parse_html_search_results(html)
        if items:
            return {
                "items": items[:items_per_page],
                "total": len(items),
                "page": page,
                "has_more": len(items) >= items_per_page,
                "search_url": search_url,
            }

    # 3. Try Playwright fallback if available
    if _PLAYWRIGHT_AVAILABLE:
        pw_html = _fetch_with_playwright(
            search_url,
            location=location,
            latitude=resolved_lat,
            longitude=resolved_lng,
            city=city,
            province=province,
            community=community,
        )
        if pw_html:
            items = _parse_html_search_results(pw_html)
            if items:
                return {
                    "items": items[:items_per_page],
                    "total": len(items),
                    "page": page,
                    "has_more": len(items) >= items_per_page,
                    "search_url": search_url,
                }

    # If all returned no items, return clean empty result
    return {
        "items": [],
        "total": 0,
        "page": page,
        "has_more": False,
        "message": "No results found or endpoint temporarily unavailable",
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

    # 1. Try internal API endpoint
    if clean_id:
        try:
            api_url = f"https://api.wallapop.com/api/v3/items/{clean_id}"
            resp = requests.get(api_url, params={"language": "es"}, headers=DEFAULT_HEADERS, timeout=12)
            if resp.status_code == 200:
                item_data = resp.json()
                if isinstance(item_data, dict):
                    res = _format_search_item(item_data)
                    res["description"] = item_data.get("description") or ""
                    res["status"] = item_data.get("status", "disponible")
                    if "images" in item_data and isinstance(item_data["images"], list):
                        res["images"] = [
                            img.get("original") or img.get("url") if isinstance(img, dict) else str(img)
                            for img in item_data["images"]
                        ]
                    return res
        except Exception as e:
            logger.debug(f"API get item failed: {e}")

    # 2. Try HTML scraping with requests
    try:
        html_headers = dict(DEFAULT_HEADERS)
        html_headers["Accept"] = (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        )
        resp = requests.get(item_url, headers=html_headers, timeout=12)
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

    # 3. Try Playwright fallback if available
    if _PLAYWRIGHT_AVAILABLE:
        pw_html = _fetch_with_playwright(item_url)
        if pw_html:
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', pw_html)
            if match:
                try:
                    data = json.loads(match.group(1))
                    page_props = data.get("props", {}).get("pageProps", {})
                    for key in ["item", "listing", "product"]:
                        if key in page_props and isinstance(page_props[key], dict):
                            item_data = page_props[key]
                            res = _format_search_item(item_data)
                            res["description"] = item_data.get("description") or ""
                            res["status"] = item_data.get("status", "disponible")
                            return res
                except Exception:
                    pass

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
